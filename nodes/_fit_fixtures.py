"""Test-only FIT binary fixture builder for christiangeorgelucas/fit-tools.

Builds real, byte-correct, CRC-valid .FIT files from scratch using only the
public FIT SDK wire-format spec (header layout, definition/data message
framing, base-type identifiers, the CRC-16 table algorithm) — NOT by calling
python-fitparse or any part of this package's own node code. This is the
package's independent oracle: `_fit_fixtures.EXPECTED_*` dicts below state
what each fixture SHOULD decode to, computed directly from the raw values we
encode via the documented scale/offset/semicircle formulas, entirely
separately from nodes/_fit.py's implementation of those same formulas. If a
bug crept into either the encoder here or nodes/_fit.py, the two would very
likely disagree, which is exactly what these tests check for.

Field numbers and base-type identifiers are the FIT SDK's public message
profile (the same spec python-fitparse's own profile.py is mechanically
generated from) — using them to construct a spec-conformant file is not the
same as relying on python-fitparse's *decode* implementation, which is what
is actually under test here (indirectly, via this package's node code).

Not part of the runtime code path — imported only by *_test.py files.
"""
import struct

# --- FIT CRC-16 (verbatim per the public FIT SDK documentation) -----------
_CRC_TABLE = (
    0x0000, 0xCC01, 0xD801, 0x1400, 0xF001, 0x3C00, 0x2800, 0xE401,
    0xA001, 0x6C00, 0x7800, 0xB401, 0x5000, 0x9C01, 0x8801, 0x4400,
)


def crc16(data: bytes, crc: int = 0) -> int:
    for byte in data:
        tmp = _CRC_TABLE[crc & 0xF]
        crc = (crc >> 4) & 0x0FFF
        crc = crc ^ tmp ^ _CRC_TABLE[byte & 0xF]
        tmp = _CRC_TABLE[crc & 0xF]
        crc = (crc >> 4) & 0x0FFF
        crc = crc ^ tmp ^ _CRC_TABLE[(byte >> 4) & 0xF]
    return crc & 0xFFFF


# FIT's date_time epoch: UTC 1989-12-31T00:00:00Z, per the FIT SDK spec.
FIT_EPOCH = 631065600


def fit_ts(unix_ts: int) -> int:
    return unix_ts - FIT_EPOCH


# --- Base type identifiers + wire sizes/struct formats (FIT SDK spec) -----
ENUM, SINT8, UINT8, SINT16, UINT16, SINT32, UINT32, UINT32Z = (
    0x00, 0x01, 0x02, 0x83, 0x84, 0x85, 0x86, 0x8C,
)
_SIZE = {ENUM: 1, SINT8: 1, UINT8: 1, SINT16: 2, UINT16: 2, SINT32: 4, UINT32: 4, UINT32Z: 4}
_FMT = {ENUM: "B", SINT8: "b", UINT8: "B", SINT16: "h", UINT16: "H", SINT32: "i", UINT32: "I", UINT32Z: "I"}

# Semicircle -> degree conversion, per the FIT SDK spec (independent literal
# restatement of the formula nodes/_fit.py also implements).
SEMI_TO_DEG = 180.0 / (2 ** 31)


def definition_message(local_num: int, global_num: int, fields) -> bytes:
    """fields: list of (def_num, base_type)."""
    body = bytearray()
    body.append(0x40 | local_num)  # record header: definition message
    body.append(0)                  # reserved
    body.append(0)                  # architecture: 0 = little endian
    body += struct.pack("<H", global_num)
    body.append(len(fields))
    for def_num, base_type in fields:
        body.append(def_num)
        body.append(_SIZE[base_type])
        body.append(base_type)
    return bytes(body)


def data_message(local_num: int, fields, values) -> bytes:
    """fields: list of (def_num, base_type) in the SAME order as the
    preceding definition_message; values: matching raw values."""
    body = bytearray()
    body.append(0x00 | local_num)  # record header: data message
    for (def_num, base_type), value in zip(fields, values):
        body += struct.pack("<" + _FMT[base_type], value)
    return bytes(body)


def assemble(body: bytes) -> bytes:
    header = bytearray()
    header.append(12)          # header_size
    header.append(0x10)        # protocol_version 1.0
    header += struct.pack("<H", 2132)   # profile_version, arbitrary
    header += struct.pack("<I", len(body))  # data_size
    header += b".FIT"
    header = bytes(header)
    crc = crc16(header + body)
    return header + body + struct.pack("<H", crc)


# ---------------------------------------------------------------------------
# The activity fixture: file_id + 2 records (one fully populated, one with
# every optional field set to its FIT "invalid" sentinel) + session + lap +
# device_info (with an unmapped product id, to exercise the raw-id fallback
# branch distinct from file_id's mapped-name branch).
# ---------------------------------------------------------------------------

FILE_ID_FIELDS = [(0, ENUM), (1, UINT16), (2, UINT16), (3, UINT32Z), (4, UINT32)]
RECORD_FIELDS = [
    (253, UINT32),  # timestamp
    (0, SINT32),    # position_lat
    (1, SINT32),    # position_long
    (2, UINT16),    # altitude
    (78, UINT32),   # enhanced_altitude
    (3, UINT8),     # heart_rate
    (4, UINT8),     # cadence
    (5, UINT32),    # distance
    (6, UINT16),    # speed
    (73, UINT32),   # enhanced_speed
    (7, UINT16),    # power
    (13, SINT8),    # temperature
]
SESSION_FIELDS = [
    (2, UINT32), (5, ENUM), (6, ENUM), (7, UINT32), (8, UINT32), (9, UINT32),
    (11, UINT16), (14, UINT16), (15, UINT16), (16, UINT8), (17, UINT8),
    (18, UINT8), (20, UINT16), (21, UINT16), (22, UINT16), (23, UINT16), (26, UINT16),
]
LAP_FIELDS = [
    (2, UINT32), (7, UINT32), (8, UINT32), (9, UINT32), (11, UINT16),
    (13, UINT16), (14, UINT16), (15, UINT8), (16, UINT8), (17, UINT8),
    (19, UINT16), (20, UINT16), (21, UINT16), (22, UINT16), (24, ENUM),
]
DEVICE_INFO_FIELDS = [
    (0, UINT8), (2, UINT16), (3, UINT32Z), (4, UINT16), (5, UINT16),
    (11, UINT8), (25, ENUM),
]

_T0 = 1704067200  # 2024-01-01T00:00:00Z

_INVALID = {
    SINT32: 0x7FFFFFFF, UINT16: 0xFFFF, UINT32: 0xFFFFFFFF,
    UINT8: 0xFF, SINT8: 0x7F,
}

_body = bytearray()

# file_id (local 0): activity, garmin, product=1 -> resolves to 'hrm1'
_body += definition_message(0, 0, FILE_ID_FIELDS)
_body += data_message(0, FILE_ID_FIELDS, [4, 1, 1, 123456789, fit_ts(_T0)])

# record #1 (local 1): fully populated, enhanced_* fields DIFFER from their
# standard-resolution counterparts so a test can prove the enhanced field is
# preferred.
_body += definition_message(1, 20, RECORD_FIELDS)
_LAT_RAW, _LON_RAW = 447440855, -1323752980
_body += data_message(1, RECORD_FIELDS, [
    fit_ts(_T0), _LAT_RAW, _LON_RAW,
    3500, 17500,   # altitude=200.0m (unused), enhanced_altitude=3000.0m (used)
    150, 85,
    250000,        # distance = 2500.0 m
    3000, 4500,    # speed=3.0 m/s (unused), enhanced_speed=4.5 m/s (used)
    220, 25,
])

# record #2 (local 1, same definition): every optional field at its FIT
# "invalid" sentinel -> every has_* must come back False.
_body += data_message(1, RECORD_FIELDS, [
    fit_ts(_T0 + 1),
    _INVALID[SINT32], _INVALID[SINT32],
    _INVALID[UINT16], _INVALID[UINT32],
    _INVALID[UINT8], _INVALID[UINT8],
    _INVALID[UINT32],
    _INVALID[UINT16], _INVALID[UINT32],
    _INVALID[UINT16], _INVALID[SINT8],
])

# session (local 2)
_body += definition_message(2, 18, SESSION_FIELDS)
_body += data_message(2, SESSION_FIELDS, [
    fit_ts(_T0), 1, 0,          # start_time, sport=running, sub_sport=generic
    3661000, 3600000, 1000000,  # elapsed=3661.0s, timer=3600.0s, distance=10000.0m
    650,                         # calories
    2778, 4200,                  # avg_speed=2.778, max_speed=4.2
    140, 175, 80,                # avg_hr, max_hr, avg_cadence
    200, 350,                    # avg_power, max_power
    120, 115,                    # ascent, descent
    5,                            # num_laps
])

# lap (local 3)
_body += definition_message(3, 19, LAP_FIELDS)
_body += data_message(3, LAP_FIELDS, [
    fit_ts(_T0), 610000, 600000, 200000,
    130,
    3333, 4500,
    145, 160, 82,
    210, 300,
    20, 18,
    0,  # lap_trigger = manual
])

# device_info (local 4): product id NOT in the garmin_product table, so it
# must come back as a raw id, not a resolved name (the opposite branch from
# file_id's product=1 above).
_body += definition_message(4, 23, DEVICE_INFO_FIELDS)
_body += data_message(4, DEVICE_INFO_FIELDS, [
    0, 1, 987654321, 65000, 1050, 2, 5,
])

ACTIVITY_FIXTURE = assemble(bytes(_body))

# What the fixture above SHOULD decode to, computed directly from the raw
# values and the documented formulas — independent of nodes/_fit.py.
EXPECTED_FILE_ID = {
    "type": "activity",
    "manufacturer": "garmin",
    "product": "hrm1",
    "product_id": 0,
    "has_product_id": False,
    "serial_number": 123456789,
    "has_serial_number": True,
    "time_created": "2024-01-01T00:00:00Z",
    "has_time_created": True,
}

EXPECTED_RECORD_1 = {
    "timestamp": "2024-01-01T00:00:00Z",
    "has_timestamp": True,
    "lat": _LAT_RAW * SEMI_TO_DEG,
    "lon": _LON_RAW * SEMI_TO_DEG,
    "has_position": True,
    "altitude": 17500 / 5 - 500,   # 3000.0 -- enhanced, NOT 3500/5-500=200.0
    "has_altitude": True,
    "heart_rate": 150,
    "has_heart_rate": True,
    "cadence": 85,
    "has_cadence": True,
    "speed": 4500 / 1000.0,        # 4.5 -- enhanced, NOT 3000/1000=3.0
    "has_speed": True,
    "power": 220,
    "has_power": True,
    "temperature": 25.0,
    "has_temperature": True,
    "distance": 250000 / 100.0,    # 2500.0
    "has_distance": True,
}

EXPECTED_RECORD_2_HAS_FLAGS_FALSE = {
    "has_position", "has_altitude", "has_heart_rate", "has_cadence",
    "has_speed", "has_power", "has_temperature", "has_distance",
}

EXPECTED_SESSION = {
    "sport": "running",
    "sub_sport": "generic",
    "start_time": "2024-01-01T00:00:00Z",
    "total_elapsed_time": 3661.0,
    "total_timer_time": 3600.0,
    "total_distance": 10000.0,
    "total_calories": 650,
    "avg_speed": 2.778,
    "max_speed": 4.2,
    "avg_heart_rate": 140,
    "max_heart_rate": 175,
    "avg_cadence": 80,
    "avg_power": 200,
    "max_power": 350,
    "total_ascent": 120.0,
    "total_descent": 115.0,
    "num_laps": 5,
}

EXPECTED_LAP = {
    "start_time": "2024-01-01T00:00:00Z",
    "total_elapsed_time": 610.0,
    "total_timer_time": 600.0,
    "total_distance": 2000.0,
    "total_calories": 130,
    "avg_speed": 3.333,
    "max_speed": 4.5,
    "avg_heart_rate": 145,
    "max_heart_rate": 160,
    "avg_cadence": 82,
    "avg_power": 210,
    "max_power": 300,
    "total_ascent": 20.0,
    "total_descent": 18.0,
    "lap_trigger": "manual",
}

EXPECTED_DEVICE_INFO = {
    "device_index": 0,
    "manufacturer": "garmin",
    "product": "",
    "product_id": 65000,
    "has_product_id": True,
    "serial_number": 987654321,
    "has_serial_number": True,
    "software_version": "10.5",
    "battery_status": "good",
    "source_type": "local",
}

EXPECTED_MESSAGE_TYPE_COUNTS = {
    "file_id": 1, "record": 2, "session": 1, "lap": 1, "device_info": 1,
}


def build_records_only_fixture(n: int) -> bytes:
    """A minimal FIT file with `n` bare `record` messages (timestamp only) —
    used to test ExtractRecords' limit/truncation behavior without the
    overhead of the full multi-message fixture."""
    fields = [(253, UINT32)]
    body = bytearray()
    body += definition_message(0, 0, FILE_ID_FIELDS)
    body += data_message(0, FILE_ID_FIELDS, [4, 1, 1, 1, fit_ts(_T0)])
    body += definition_message(1, 20, fields)
    for i in range(n):
        body += data_message(1, fields, [fit_ts(_T0 + i)])
    return assemble(bytes(body))


def truncated_fixture() -> bytes:
    """A byte-truncated (cut mid-body) copy of ACTIVITY_FIXTURE — a
    malformed-but-plausible input (e.g. an interrupted download)."""
    return ACTIVITY_FIXTURE[: len(ACTIVITY_FIXTURE) // 2]


def bad_crc_fixture() -> bytes:
    """ACTIVITY_FIXTURE with its trailing CRC corrupted."""
    return ACTIVITY_FIXTURE[:-2] + b"\x00\x00"


NOT_A_FIT_FILE = b"this is definitely not a FIT file, just plain text bytes"
