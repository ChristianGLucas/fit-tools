from gen.messages_pb2 import FitInput, ExtractRecordsInput
from nodes._test_helpers import _TestContext
from nodes.extract_records import extract_records
from nodes._common import MAX_RECORD_LIMIT
from nodes._fit_fixtures import (
    ACTIVITY_FIXTURE, EXPECTED_RECORD_1, EXPECTED_RECORD_2_HAS_FLAGS_FALSE,
    NOT_A_FIT_FILE, build_records_only_fixture, truncated_fixture, bad_crc_fixture,
)


def test_extract_records_matches_hand_computed_oracle():
    # Independent oracle: EXPECTED_RECORD_1 is computed directly from the
    # raw semicircle/scale/offset values encoded in _fit_fixtures.py using
    # the FIT SDK's documented formulas, restated independently of
    # nodes/_fit.py. This also proves the enhanced_altitude/enhanced_speed
    # fields (deliberately encoded with DIFFERENT raw values from their
    # standard-resolution counterparts) are the ones actually returned.
    ax = _TestContext()
    out = extract_records(ax, ExtractRecordsInput(fit=FitInput(data=ACTIVITY_FIXTURE)))
    assert out.ok is True
    assert len(out.records) == 2
    r1 = out.records[0]
    assert r1.timestamp == EXPECTED_RECORD_1["timestamp"]
    assert abs(r1.lat - EXPECTED_RECORD_1["lat"]) < 1e-9
    assert abs(r1.lon - EXPECTED_RECORD_1["lon"]) < 1e-9
    assert r1.has_position is True
    assert abs(r1.altitude - EXPECTED_RECORD_1["altitude"]) < 1e-9
    assert r1.heart_rate == EXPECTED_RECORD_1["heart_rate"]
    assert r1.cadence == EXPECTED_RECORD_1["cadence"]
    assert abs(r1.speed - EXPECTED_RECORD_1["speed"]) < 1e-9
    assert r1.power == EXPECTED_RECORD_1["power"]
    assert abs(r1.temperature - EXPECTED_RECORD_1["temperature"]) < 1e-9
    assert abs(r1.distance - EXPECTED_RECORD_1["distance"]) < 1e-9


def test_extract_records_missing_fields_have_flags_false():
    ax = _TestContext()
    out = extract_records(ax, ExtractRecordsInput(fit=FitInput(data=ACTIVITY_FIXTURE)))
    r2 = out.records[1]
    assert r2.has_timestamp is True  # timestamp itself IS present on record 2
    for flag_name in EXPECTED_RECORD_2_HAS_FLAGS_FALSE:
        assert getattr(r2, flag_name) is False, flag_name
    assert r2.lat == 0.0 and r2.lon == 0.0
    assert r2.heart_rate == 0
    assert r2.power == 0


def test_extract_records_limit_and_truncation():
    ax = _TestContext()
    fixture = build_records_only_fixture(25)
    out = extract_records(ax, ExtractRecordsInput(fit=FitInput(data=fixture), limit=10))
    assert out.ok is True
    assert len(out.records) == 10
    assert out.total_available == 25
    assert out.truncated is True


def test_extract_records_default_limit_no_truncation_when_under():
    ax = _TestContext()
    fixture = build_records_only_fixture(3)
    out = extract_records(ax, ExtractRecordsInput(fit=FitInput(data=fixture)))
    assert out.ok is True
    assert len(out.records) == 3
    assert out.total_available == 3
    assert out.truncated is False


def test_extract_records_limit_over_max_is_rejected():
    ax = _TestContext()
    out = extract_records(ax, ExtractRecordsInput(fit=FitInput(data=ACTIVITY_FIXTURE), limit=MAX_RECORD_LIMIT + 1))
    assert out.ok is False
    assert out.error.code == "INVALID_ARGUMENT"


def test_extract_records_records_are_time_ordered():
    ax = _TestContext()
    fixture = build_records_only_fixture(5)
    out = extract_records(ax, ExtractRecordsInput(fit=FitInput(data=fixture)))
    timestamps = [r.timestamp for r in out.records]
    assert timestamps == sorted(timestamps)


def test_extract_records_error_on_garbage():
    ax = _TestContext()
    out = extract_records(ax, ExtractRecordsInput(fit=FitInput(data=NOT_A_FIT_FILE)))
    assert out.ok is False
    assert out.error.code == "INVALID_INPUT"


def test_extract_records_error_on_truncated_file():
    # Regression test: this must return a structured error, not crash. The
    # record definition + first record are intact; the corruption is only
    # detected partway through iteration (python-fitparse parses lazily),
    # which previously escaped this node's try/except entirely.
    ax = _TestContext()
    out = extract_records(ax, ExtractRecordsInput(fit=FitInput(data=truncated_fixture())))
    assert out.ok is False
    assert out.error.code == "INVALID_INPUT"


def test_extract_records_error_on_bad_crc():
    ax = _TestContext()
    out = extract_records(ax, ExtractRecordsInput(fit=FitInput(data=bad_crc_fixture())))
    assert out.ok is False
    assert out.error.code == "INVALID_INPUT"


def test_extract_records_is_deterministic():
    ax = _TestContext()
    out1 = extract_records(ax, ExtractRecordsInput(fit=FitInput(data=ACTIVITY_FIXTURE)))
    out2 = extract_records(ax, ExtractRecordsInput(fit=FitInput(data=ACTIVITY_FIXTURE)))
    assert list(out1.records) == list(out2.records)
