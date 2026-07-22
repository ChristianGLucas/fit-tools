import pytest

from gen.messages_pb2 import FitInput
from nodes._common import FitDecodeError, MAX_FIT_BYTES, raw_bytes


def test_raw_bytes_prefers_data_over_url():
    assert raw_bytes(FitInput(data=b"\x01\x02", url="http://example.com/x.fit")) == b"\x01\x02"


def test_raw_bytes_empty_input_error():
    with pytest.raises(FitDecodeError) as exc:
        raw_bytes(FitInput())
    assert exc.value.code == "INVALID_INPUT"


def test_raw_bytes_oversized_data_error():
    with pytest.raises(FitDecodeError) as exc:
        raw_bytes(FitInput(data=b"\x00" * (MAX_FIT_BYTES + 1)))
    assert exc.value.code == "LIMIT_EXCEEDED"


@pytest.mark.parametrize("url", [
    "http://127.0.0.1/x.fit",        # loopback
    "http://localhost/x.fit",        # resolves loopback
    "http://169.254.169.254/latest", # link-local / cloud metadata
    "http://10.0.0.5/x.fit",         # private
    "http://192.168.1.1/x.fit",      # private
    "ftp://example.com/x.fit",       # disallowed scheme
    "file:///etc/passwd",            # disallowed scheme
])
def test_raw_bytes_ssrf_guard_rejects(url):
    with pytest.raises(FitDecodeError) as exc:
        raw_bytes(FitInput(url=url))
    assert exc.value.code == "INVALID_ARGUMENT"
