from gen.messages_pb2 import FitInput
from nodes._test_helpers import _TestContext
from nodes.list_message_types import list_message_types
from nodes._fit_fixtures import (
    ACTIVITY_FIXTURE, EXPECTED_MESSAGE_TYPE_COUNTS, NOT_A_FIT_FILE,
    truncated_fixture, bad_crc_fixture,
)


def test_list_message_types_matches_hand_built_fixture():
    ax = _TestContext()
    out = list_message_types(ax, FitInput(data=ACTIVITY_FIXTURE))
    assert out.ok is True
    got = {mt.name: mt.count for mt in out.message_types}
    assert got == EXPECTED_MESSAGE_TYPE_COUNTS
    assert out.total_messages == sum(EXPECTED_MESSAGE_TYPE_COUNTS.values())


def test_list_message_types_sorted_by_descending_count():
    ax = _TestContext()
    out = list_message_types(ax, FitInput(data=ACTIVITY_FIXTURE))
    counts = [mt.count for mt in out.message_types]
    assert counts == sorted(counts, reverse=True)


def test_list_message_types_error_on_garbage():
    ax = _TestContext()
    out = list_message_types(ax, FitInput(data=NOT_A_FIT_FILE))
    assert out.ok is False
    assert out.error.code == "INVALID_INPUT"


def test_list_message_types_error_on_truncated_file():
    # Unlike GetFileInfo, this node reads every message through EOF, so a
    # file cut off mid-body is caught here.
    ax = _TestContext()
    out = list_message_types(ax, FitInput(data=truncated_fixture()))
    assert out.ok is False
    assert out.error.code == "INVALID_INPUT"


def test_list_message_types_error_on_bad_crc():
    ax = _TestContext()
    out = list_message_types(ax, FitInput(data=bad_crc_fixture()))
    assert out.ok is False
    assert out.error.code == "INVALID_INPUT"
