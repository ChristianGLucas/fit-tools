from gen.messages_pb2 import FitInput
from nodes._test_helpers import _TestContext
from nodes.extract_sessions import extract_sessions
from nodes._fit_fixtures import ACTIVITY_FIXTURE, EXPECTED_SESSION, NOT_A_FIT_FILE


def test_extract_sessions_matches_hand_computed_oracle():
    ax = _TestContext()
    out = extract_sessions(ax, FitInput(data=ACTIVITY_FIXTURE))
    assert out.ok is True
    assert len(out.sessions) == 1
    s = out.sessions[0]
    assert s.sport == EXPECTED_SESSION["sport"]
    assert s.sub_sport == EXPECTED_SESSION["sub_sport"]
    assert s.start_time == EXPECTED_SESSION["start_time"]
    assert abs(s.total_elapsed_time - EXPECTED_SESSION["total_elapsed_time"]) < 1e-6
    assert abs(s.total_timer_time - EXPECTED_SESSION["total_timer_time"]) < 1e-6
    assert abs(s.total_distance - EXPECTED_SESSION["total_distance"]) < 1e-6
    assert s.total_calories == EXPECTED_SESSION["total_calories"]
    assert abs(s.avg_speed - EXPECTED_SESSION["avg_speed"]) < 1e-6
    assert abs(s.max_speed - EXPECTED_SESSION["max_speed"]) < 1e-6
    assert s.avg_heart_rate == EXPECTED_SESSION["avg_heart_rate"]
    assert s.max_heart_rate == EXPECTED_SESSION["max_heart_rate"]
    assert s.avg_power == EXPECTED_SESSION["avg_power"]
    assert s.max_power == EXPECTED_SESSION["max_power"]
    assert s.avg_cadence == EXPECTED_SESSION["avg_cadence"]
    assert abs(s.total_ascent - EXPECTED_SESSION["total_ascent"]) < 1e-6
    assert abs(s.total_descent - EXPECTED_SESSION["total_descent"]) < 1e-6
    assert s.num_laps == EXPECTED_SESSION["num_laps"]
    assert s.index == 0


def test_extract_sessions_empty_list_when_no_sessions():
    ax = _TestContext()
    from nodes._fit_fixtures import build_records_only_fixture
    out = extract_sessions(ax, FitInput(data=build_records_only_fixture(3)))
    assert out.ok is True
    assert len(out.sessions) == 0


def test_extract_sessions_error_on_garbage():
    ax = _TestContext()
    out = extract_sessions(ax, FitInput(data=NOT_A_FIT_FILE))
    assert out.ok is False
    assert out.error.code == "INVALID_INPUT"
