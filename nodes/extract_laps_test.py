from gen.messages_pb2 import FitInput
from nodes._test_helpers import _TestContext
from nodes.extract_laps import extract_laps
from nodes._fit_fixtures import ACTIVITY_FIXTURE, EXPECTED_LAP, NOT_A_FIT_FILE


def test_extract_laps_matches_hand_computed_oracle():
    ax = _TestContext()
    out = extract_laps(ax, FitInput(data=ACTIVITY_FIXTURE))
    assert out.ok is True
    assert len(out.laps) == 1
    lap = out.laps[0]
    assert lap.start_time == EXPECTED_LAP["start_time"]
    assert abs(lap.total_elapsed_time - EXPECTED_LAP["total_elapsed_time"]) < 1e-6
    assert abs(lap.total_timer_time - EXPECTED_LAP["total_timer_time"]) < 1e-6
    assert abs(lap.total_distance - EXPECTED_LAP["total_distance"]) < 1e-6
    assert lap.total_calories == EXPECTED_LAP["total_calories"]
    assert abs(lap.avg_speed - EXPECTED_LAP["avg_speed"]) < 1e-6
    assert abs(lap.max_speed - EXPECTED_LAP["max_speed"]) < 1e-6
    assert lap.avg_heart_rate == EXPECTED_LAP["avg_heart_rate"]
    assert lap.max_heart_rate == EXPECTED_LAP["max_heart_rate"]
    assert lap.avg_power == EXPECTED_LAP["avg_power"]
    assert lap.max_power == EXPECTED_LAP["max_power"]
    assert lap.avg_cadence == EXPECTED_LAP["avg_cadence"]
    assert abs(lap.total_ascent - EXPECTED_LAP["total_ascent"]) < 1e-6
    assert abs(lap.total_descent - EXPECTED_LAP["total_descent"]) < 1e-6
    assert lap.lap_trigger == EXPECTED_LAP["lap_trigger"]
    assert lap.index == 0


def test_extract_laps_error_on_garbage():
    ax = _TestContext()
    out = extract_laps(ax, FitInput(data=NOT_A_FIT_FILE))
    assert out.ok is False
    assert out.error.code == "INVALID_INPUT"
