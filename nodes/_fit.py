"""FIT-decode helpers for christiangeorgelucas/fit-tools, wrapping
python-fitparse (MIT). One place that knows how to (a) safely open a FIT
byte buffer and (b) shape fitparse's message/field objects into the plain
Python dicts the nodes turn into protobuf messages.

python-fitparse applies each field's scale/offset and maps the FIT
"invalid value" sentinel (e.g. 0xFF for a uint8, 0xFFFFFFFF for a uint32) to
None, and resolves enum-typed fields (sport, manufacturer, battery_status,
...) to their profile name automatically. We rely on all of that rather than
re-deriving it — see the module docstring rule against reimplementing what
the library already gets right. What this module adds: semicircle -> degree
conversion (FIT's default processor deliberately leaves position fields in
raw semicircles; only the opt-in StandardUnitsDataProcessor converts them,
and it also rescales distance/speed to km / km/h, which we do NOT want —
this package's contract is meters and meters/second), ISO 8601 timestamp
formatting, and the has_/optional-field shaping our proto uses throughout.
"""
from __future__ import annotations

import io
from datetime import datetime, timezone

from fitparse import FitFile
from fitparse.utils import FitEOFError, FitCRCError, FitHeaderError, FitParseError

from nodes._common import FitDecodeError, MAX_MESSAGES_ITERATED, MAX_SUMMARY_MESSAGES

_SEMICIRCLE_TO_DEG = 180.0 / (2 ** 31)


def open_fit(data: bytes) -> FitFile:
    """Open a validated `bytes` buffer as a FitFile. NEVER pass a `str` here
    (see nodes._common.raw_bytes for why). Raises FitDecodeError on anything
    that isn't a well-formed, CRC-valid FIT file."""
    if not isinstance(data, (bytes, bytearray)):
        raise FitDecodeError("INVALID_INPUT", "internal error: FIT payload must be bytes")
    try:
        return FitFile(io.BytesIO(data), check_crc=True)
    except (FitParseError, FitEOFError, FitCRCError, FitHeaderError) as exc:
        raise FitDecodeError("INVALID_INPUT", f"not a valid FIT file: {exc}")
    except Exception as exc:  # defensive: any other parse-time failure
        raise FitDecodeError("INVALID_INPUT", f"failed to open FIT file: {exc}")


def _iso(value) -> str:
    """Format a fitparse date_time field value (already converted to a naive
    UTC datetime by the library's default processor) as ISO 8601 with a Z
    suffix. Returns "" for a missing value."""
    if value is None:
        return ""
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return str(value)


def _last_value(msg, name):
    """Return the value of the LAST field on `msg` named `name`, or None.

    Deliberately NOT `msg.get_value(name)`: some fields (record.altitude,
    record.speed) declare a `components` decomposition that makes fitparse
    synthesize a SECOND, duplicate-named FieldData ('enhanced_altitude',
    'enhanced_speed') derived from the base field's raw bits — and
    `get_value` returns the FIRST field matching a name. In a file encoded
    with fields in ascending def_num order (the standard/SDK-generated
    order, and what every device we've inspected does), that derived
    duplicate sorts BEFORE the message's real, independently-transmitted
    'enhanced_*' field (def_num 78 / 73), so `get_value('enhanced_altitude')`
    would silently return the derived duplicate of the low-resolution value
    instead of the genuine high-resolution one whenever a device sends both.
    Taking the LAST match returns the real field in that (standard) order.
    """
    value = None
    for field_data in msg.fields:
        if field_data.is_named(name):
            value = field_data.value
    return value


def _num(msg, *names):
    """Return the first non-None value among `names` looked up on `msg` (via
    `_last_value`, see its docstring), or None. Used to prefer an
    'enhanced_*' (higher-resolution) field over its standard-resolution
    counterpart when both are present."""
    for name in names:
        v = _last_value(msg, name)
        if v is not None:
            return v
    return None


def _str(msg, name) -> str:
    v = msg.get_value(name)
    return "" if v is None else str(v)


def _messages(fitfile: FitFile, name=None):
    """Iterate a FitFile's data messages, defensively capped so a
    pathologically constructed file (many tiny compressed-timestamp record
    headers referencing one definition) cannot make a single decode pass
    iterate unboundedly. A real activity file never approaches this cap.

    python-fitparse parses LAZILY: only the file header is parsed
    synchronously in FitFile.__init__ (what open_fit's try/except covers).
    Everything else -- including the trailing CRC check, which only runs
    once the LAST byte of the body has been consumed -- happens as this
    generator is pulled. A malformed or truncated file whose header is
    intact but whose body or trailing CRC is corrupt therefore raises
    FitParseError/FitEOFError/FitCRCError/FitHeaderError from `next()`
    partway through iteration, not from open_fit. Every node that walks
    past the first message must see that as a structured error too, not an
    unhandled crash -- hence catching it here, at the single choke point
    every node's iteration goes through.
    """
    n = 0
    it = fitfile.get_messages(name)
    while True:
        try:
            msg = next(it)
        except StopIteration:
            return
        except (FitParseError, FitEOFError, FitCRCError, FitHeaderError) as exc:
            raise FitDecodeError("INVALID_INPUT", f"FIT file is corrupt or truncated: {exc}")
        n += 1
        if n > MAX_MESSAGES_ITERATED:
            raise FitDecodeError("LIMIT_EXCEEDED", f"FIT file has more than {MAX_MESSAGES_ITERATED} messages")
        yield msg


def get_file_info(fitfile: FitFile) -> dict | None:
    """Decode just the first `file_id` message. Returns None if the file has
    none (not a valid FIT file, per the FIT spec's mandatory-first-message
    rule)."""
    for msg in _messages(fitfile, "file_id"):
        product_id = msg.get_value("product")
        serial = msg.get_value("serial_number")
        created = msg.get_value("time_created")
        return {
            "type": _str(msg, "type"),
            "manufacturer": _str(msg, "manufacturer"),
            # get_value("product") returns the resolved enum NAME when the
            # manufacturer/product pair is a known Garmin device, else the
            # raw numeric id (int) — the `product` string field wants the
            # name form only.
            "product": product_id if isinstance(product_id, str) else "",
            "product_id": int(product_id) if isinstance(product_id, int) else 0,
            "has_product_id": isinstance(product_id, int),
            "serial_number": int(serial) if serial is not None else 0,
            "has_serial_number": serial is not None,
            "time_created": _iso(created),
            "has_time_created": created is not None,
        }
    return None


def list_message_types(fitfile: FitFile) -> tuple[list[dict], int]:
    """Count every distinct message type in the file. Returns
    ([{name, count}, ...] sorted by descending count, total_messages)."""
    counts: dict[str, int] = {}
    total = 0
    for msg in _messages(fitfile):
        name = msg.name if msg.name else f"unknown_{msg.mesg_num}"
        counts[name] = counts.get(name, 0) + 1
        total += 1
    ordered = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return [{"name": n, "count": c} for n, c in ordered], total


def _record_dict(msg) -> dict:
    lat_raw = msg.get_value("position_lat")
    lon_raw = msg.get_value("position_long")
    has_pos = lat_raw is not None and lon_raw is not None
    altitude = _num(msg, "enhanced_altitude", "altitude")
    speed = _num(msg, "enhanced_speed", "speed")
    hr = msg.get_value("heart_rate")
    cadence = msg.get_value("cadence")
    power = msg.get_value("power")
    temperature = msg.get_value("temperature")
    distance = msg.get_value("distance")
    ts = msg.get_value("timestamp")
    return {
        "timestamp": _iso(ts),
        "has_timestamp": ts is not None,
        "lat": lat_raw * _SEMICIRCLE_TO_DEG if has_pos else 0.0,
        "lon": lon_raw * _SEMICIRCLE_TO_DEG if has_pos else 0.0,
        "has_position": has_pos,
        "altitude": float(altitude) if altitude is not None else 0.0,
        "has_altitude": altitude is not None,
        "heart_rate": int(hr) if hr is not None else 0,
        "has_heart_rate": hr is not None,
        "cadence": int(cadence) if cadence is not None else 0,
        "has_cadence": cadence is not None,
        "speed": float(speed) if speed is not None else 0.0,
        "has_speed": speed is not None,
        "power": int(power) if power is not None else 0,
        "has_power": power is not None,
        "temperature": float(temperature) if temperature is not None else 0.0,
        "has_temperature": temperature is not None,
        "distance": float(distance) if distance is not None else 0.0,
        "has_distance": distance is not None,
    }


def extract_records(fitfile: FitFile, limit: int) -> tuple[list[dict], int, bool]:
    """Extract `record` messages up to `limit`, but keep counting past it to
    report the true total. Returns (records, total_available, truncated)."""
    records = []
    total = 0
    for msg in _messages(fitfile, "record"):
        total += 1
        if len(records) < limit:
            records.append(_record_dict(msg))
    return records, total, total > len(records)


def _summary_dict(msg, *, with_sport: bool, with_trigger: bool) -> dict:
    start = msg.get_value("start_time")
    total_distance = msg.get_value("total_distance")
    calories = msg.get_value("total_calories")
    avg_speed = _num(msg, "enhanced_avg_speed", "avg_speed")
    max_speed = _num(msg, "enhanced_max_speed", "max_speed")
    avg_hr = msg.get_value("avg_heart_rate")
    max_hr = msg.get_value("max_heart_rate")
    avg_power = msg.get_value("avg_power")
    max_power = msg.get_value("max_power")
    avg_cadence = msg.get_value("avg_cadence")
    ascent = msg.get_value("total_ascent")
    descent = msg.get_value("total_descent")
    elapsed = msg.get_value("total_elapsed_time")
    timer = msg.get_value("total_timer_time")
    d = {
        "start_time": _iso(start),
        "has_start_time": start is not None,
        "total_elapsed_time": float(elapsed) if elapsed is not None else 0.0,
        "total_timer_time": float(timer) if timer is not None else 0.0,
        "total_distance": float(total_distance) if total_distance is not None else 0.0,
        "has_total_distance": total_distance is not None,
        "total_calories": int(calories) if calories is not None else 0,
        "has_total_calories": calories is not None,
        "avg_speed": float(avg_speed) if avg_speed is not None else 0.0,
        "has_avg_speed": avg_speed is not None,
        "max_speed": float(max_speed) if max_speed is not None else 0.0,
        "has_max_speed": max_speed is not None,
        "avg_heart_rate": int(avg_hr) if avg_hr is not None else 0,
        "has_avg_heart_rate": avg_hr is not None,
        "max_heart_rate": int(max_hr) if max_hr is not None else 0,
        "has_max_heart_rate": max_hr is not None,
        "avg_power": int(avg_power) if avg_power is not None else 0,
        "has_avg_power": avg_power is not None,
        "max_power": int(max_power) if max_power is not None else 0,
        "has_max_power": max_power is not None,
        "avg_cadence": int(avg_cadence) if avg_cadence is not None else 0,
        "has_avg_cadence": avg_cadence is not None,
        "total_ascent": float(ascent) if ascent is not None else 0.0,
        "has_total_ascent": ascent is not None,
        "total_descent": float(descent) if descent is not None else 0.0,
        "has_total_descent": descent is not None,
    }
    if with_sport:
        d["sport"] = _str(msg, "sport")
        d["sub_sport"] = _str(msg, "sub_sport")
        num_laps = msg.get_value("num_laps")
        d["num_laps"] = int(num_laps) if num_laps is not None else 0
    if with_trigger:
        d["lap_trigger"] = _str(msg, "lap_trigger")
    return d


def extract_sessions(fitfile: FitFile) -> list[dict]:
    out = []
    for i, msg in enumerate(_messages(fitfile, "session")):
        if i >= MAX_SUMMARY_MESSAGES:
            break
        d = _summary_dict(msg, with_sport=True, with_trigger=False)
        d["index"] = i
        out.append(d)
    return out


def extract_laps(fitfile: FitFile) -> list[dict]:
    out = []
    for i, msg in enumerate(_messages(fitfile, "lap")):
        if i >= MAX_SUMMARY_MESSAGES:
            break
        d = _summary_dict(msg, with_sport=False, with_trigger=True)
        d["index"] = i
        out.append(d)
    return out


def extract_device_info(fitfile: FitFile) -> list[dict]:
    out = []
    for i, msg in enumerate(_messages(fitfile, "device_info")):
        if i >= MAX_SUMMARY_MESSAGES:
            break
        product_id = msg.get_value("product")
        serial = msg.get_value("serial_number")
        sw = msg.get_value("software_version")
        idx = msg.get_value("device_index")
        out.append({
            "device_index": int(idx) if isinstance(idx, int) else 0,
            "manufacturer": _str(msg, "manufacturer"),
            "product": product_id if isinstance(product_id, str) else "",
            "product_id": int(product_id) if isinstance(product_id, int) else 0,
            "has_product_id": isinstance(product_id, int),
            "serial_number": int(serial) if serial is not None else 0,
            "has_serial_number": serial is not None,
            "software_version": str(sw) if sw is not None else "",
            "has_software_version": sw is not None,
            "battery_status": _str(msg, "battery_status"),
            "has_battery_status": msg.get_value("battery_status") is not None,
            "source_type": _str(msg, "source_type"),
        })
    return out
