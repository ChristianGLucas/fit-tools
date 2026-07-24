"""Shared helpers for christiangeorgelucas/fit-tools nodes.

Centralizes structured Error construction, the SSRF-guarded URL fetch (for
FitInput.url), and input-bound validation shared by every node.
"""
from __future__ import annotations

import http.client
import ipaddress
import socket
import ssl
from urllib.parse import urljoin, urlparse

from gen.messages_pb2 import FitError

# Timeout for a URL fetch, in seconds.
_FETCH_TIMEOUT = 20
# Max redirect hops to follow (each re-validated). Bounding this isn't a
# payload/memory guard -- it's what makes a redirect-following fetch
# terminate at all (the same reason every HTTP client library has a
# max-redirects setting), part of this input-driven fetch's capability-safety
# story alongside the SSRF/DNS-rebinding guards below.
_MAX_REDIRECTS = 5

# Default number of `record` messages ExtractRecords/ParseActivity return
# when the caller doesn't specify `limit` -- a sensible default page size,
# not a hard ceiling; a caller can request more via `limit`.
DEFAULT_RECORD_LIMIT = 1000


class FitDecodeError(Exception):
    """A structured, caller-facing failure. Nodes turn this into an `error`
    field on their output message rather than letting it propagate as a crash."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def err(code: str, message: str) -> FitError:
    """Build a structured FitError. `code` is one of: INVALID_INPUT,
    INVALID_ARGUMENT, LIMIT_EXCEEDED, COMPUTE_ERROR."""
    return FitError(code=code, message=message)


def err_from_exc(exc: FitDecodeError) -> FitError:
    return err(exc.code, exc.message)


def _is_disallowed_ip(ip: str) -> bool:
    """True if `ip` is not a normal public address (loopback, private,
    link-local, reserved, multicast, or unspecified) — the SSRF block list."""
    addr = ipaddress.ip_address(ip)
    return (
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_reserved
        or addr.is_multicast
        or addr.is_unspecified
    )


def _validate_url(url: str):
    """Validate a URL for fetching and resolve it to a safe, pinned IP.

    Rejects non-http(s) schemes and any host that resolves to a private,
    loopback, link-local, reserved, multicast, or unspecified address.
    Returns (scheme, host, port, ip) where `ip` is a validated address we
    then connect to DIRECTLY — so the address checked is the address
    contacted, closing the DNS-rebinding window. Called on the initial URL
    AND on every redirect hop. Raises FitDecodeError on anything disallowed.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise FitDecodeError("INVALID_ARGUMENT", "url must be an http or https URL")
    host = parsed.hostname
    if not host:
        raise FitDecodeError("INVALID_ARGUMENT", "url has no host")
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        infos = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
    except socket.gaierror:
        raise FitDecodeError("INVALID_ARGUMENT", "could not resolve url host")
    pinned = None
    for info in infos:
        cand = info[4][0]
        if _is_disallowed_ip(cand):
            raise FitDecodeError("INVALID_ARGUMENT", "url host resolves to a non-public address")
        if pinned is None:
            pinned = cand
    if pinned is None:
        raise FitDecodeError("INVALID_ARGUMENT", "could not resolve url host")
    return parsed.scheme, host, port, pinned


class _PinnedHTTPConnection(http.client.HTTPConnection):
    """HTTPConnection that dials a pre-validated IP instead of re-resolving the
    host (so the address we vetted is the address we actually contact)."""

    def __init__(self, host, pinned_ip, **kwargs):
        super().__init__(host, **kwargs)
        self._pinned_ip = pinned_ip

    def connect(self):
        self.sock = socket.create_connection((self._pinned_ip, self.port), self.timeout)
        if self._tunnel_host:
            self._tunnel()


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    """HTTPSConnection that dials a pre-validated IP while still using the
    original hostname for TLS SNI and certificate verification."""

    def __init__(self, host, pinned_ip, *, context, **kwargs):
        super().__init__(host, context=context, **kwargs)
        self._pinned_ip = pinned_ip

    def connect(self):
        sock = socket.create_connection((self._pinned_ip, self.port), self.timeout)
        if self._tunnel_host:
            self.sock = sock
            self._tunnel()
            sock = self.sock
        self.sock = self._context.wrap_socket(sock, server_hostname=self.host)


def _fetch(url: str) -> bytes:
    """Fetch a FIT file over http/https with an SSRF guard enforced on the
    initial URL AND re-enforced on every redirect hop, connecting only to
    the validated, pinned address. Follows at most `_MAX_REDIRECTS`
    redirects.
    """
    current = url
    for _ in range(_MAX_REDIRECTS + 1):
        scheme, host, port, ip = _validate_url(current)
        if scheme == "https":
            conn = _PinnedHTTPSConnection(
                host, ip, port=port, timeout=_FETCH_TIMEOUT,
                context=ssl.create_default_context(),
            )
        else:
            conn = _PinnedHTTPConnection(host, ip, port=port, timeout=_FETCH_TIMEOUT)
        try:
            parsed = urlparse(current)
            path = parsed.path or "/"
            if parsed.query:
                path += "?" + parsed.query
            conn.request("GET", path, headers={"User-Agent": "axiom-fit-tools/0.1"})
            resp = conn.getresponse()
            if resp.status in (301, 302, 303, 307, 308):
                loc = resp.getheader("Location")
                resp.read()  # drain before reusing the connection for the next hop
                if not loc:
                    raise FitDecodeError("INVALID_INPUT", "redirect without a Location header")
                current = urljoin(current, loc)
                continue
            if resp.status != 200:
                raise FitDecodeError("INVALID_INPUT", f"fetch failed with HTTP {resp.status}")
            raw = resp.read()
        except FitDecodeError:
            raise
        except Exception as exc:  # network / TLS / HTTP error -> structured failure
            raise FitDecodeError("INVALID_INPUT", f"failed to fetch url: {type(exc).__name__}")
        finally:
            conn.close()
        return raw
    raise FitDecodeError("INVALID_INPUT", "too many redirects")


def raw_bytes(fit_input) -> bytes:
    """Resolve a `FitInput` envelope to raw FIT bytes (inline `data`, else
    fetch `url`). Raises FitDecodeError on empty input. Always returns a
    plain `bytes` object — NEVER a `str` — because python-fitparse's
    file-open helper treats a `str` argument as a filesystem PATH
    (open(path)), not file contents; passing it a string would be a
    path-traversal / arbitrary-local-file-read vector. Callers must wrap
    this in io.BytesIO before handing it to fitparse, never pass it as-is."""
    data = bytes(fit_input.data)
    if data:
        return data
    if fit_input.url:
        return _fetch(fit_input.url)
    raise FitDecodeError("INVALID_INPUT", "input has neither `data` nor `url`")
