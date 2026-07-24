from gen.messages_pb2 import FitInput
from nodes._test_helpers import _TestContext
from nodes.parse_activity import parse_activity
from nodes._fit_fixtures import (
    ACTIVITY_FIXTURE, EXPECTED_FILE_ID, EXPECTED_SESSION, EXPECTED_LAP,
    EXPECTED_DEVICE_INFO, NOT_A_FIT_FILE, build_records_only_fixture,
    truncated_fixture, bad_crc_fixture,
)


def test_parse_activity_combines_every_section():
    ax = _TestContext()
    out = parse_activity(ax, FitInput(data=ACTIVITY_FIXTURE))
    assert out.ok is True
    assert out.file_id.type == EXPECTED_FILE_ID["type"]
    assert len(out.sessions) == 1
    assert out.sessions[0].sport == EXPECTED_SESSION["sport"]
    assert len(out.laps) == 1
    assert out.laps[0].lap_trigger == EXPECTED_LAP["lap_trigger"]
    assert len(out.device_infos) == 1
    assert out.device_infos[0].serial_number == EXPECTED_DEVICE_INFO["serial_number"]
    assert len(out.records) == 2
    assert out.total_records == 2
    assert out.truncated is False


def test_parse_activity_no_file_id_is_error():
    ax = _TestContext()
    # A well-formed FIT file (valid header/CRC) whose body has no messages
    # at all, therefore no file_id.
    from nodes._fit_fixtures import assemble
    out = parse_activity(ax, FitInput(data=assemble(b"")))
    assert out.ok is False
    assert out.error.code == "INVALID_INPUT"


def test_parse_activity_returns_every_record_no_crash_on_large_file():
    # No record cap -- ParseActivity returns every record; response size is
    # the platform's concern, not this node's.
    ax = _TestContext()
    n = 1200
    fixture = build_records_only_fixture(n)
    out = parse_activity(ax, FitInput(data=fixture))
    assert out.ok is True
    assert len(out.records) == n
    assert out.total_records == n
    assert out.truncated is False


def test_parse_activity_error_on_garbage():
    ax = _TestContext()
    out = parse_activity(ax, FitInput(data=NOT_A_FIT_FILE))
    assert out.ok is False
    assert out.error.code == "INVALID_INPUT"


def test_parse_activity_error_on_truncated_file():
    ax = _TestContext()
    out = parse_activity(ax, FitInput(data=truncated_fixture()))
    assert out.ok is False
    assert out.error.code == "INVALID_INPUT"


def test_parse_activity_error_on_bad_crc():
    ax = _TestContext()
    out = parse_activity(ax, FitInput(data=bad_crc_fixture()))
    assert out.ok is False
    assert out.error.code == "INVALID_INPUT"
