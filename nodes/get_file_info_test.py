from gen.messages_pb2 import FitInput
from nodes._test_helpers import _TestContext
from nodes.get_file_info import get_file_info
from nodes._fit_fixtures import ACTIVITY_FIXTURE, EXPECTED_FILE_ID, NOT_A_FIT_FILE


def test_get_file_info_matches_hand_computed_oracle():
    # Independent oracle: EXPECTED_FILE_ID is derived directly from the raw
    # bytes _fit_fixtures.py encodes (product=1 under manufacturer=garmin
    # resolves to the profile name "hrm1"), not from running this node.
    ax = _TestContext()
    out = get_file_info(ax, FitInput(data=ACTIVITY_FIXTURE))
    assert out.ok is True
    assert out.error.code == ""
    fi = out.file_id
    assert fi.type == EXPECTED_FILE_ID["type"]
    assert fi.manufacturer == EXPECTED_FILE_ID["manufacturer"]
    assert fi.product == EXPECTED_FILE_ID["product"]
    assert fi.has_product_id == EXPECTED_FILE_ID["has_product_id"]
    assert fi.serial_number == EXPECTED_FILE_ID["serial_number"]
    assert fi.has_serial_number is True
    assert fi.time_created == EXPECTED_FILE_ID["time_created"]
    assert fi.has_time_created is True


def test_get_file_info_no_data_no_url_error():
    ax = _TestContext()
    out = get_file_info(ax, FitInput())
    assert out.ok is False
    assert out.error.code == "INVALID_INPUT"


def test_get_file_info_not_a_fit_file_error():
    ax = _TestContext()
    out = get_file_info(ax, FitInput(data=NOT_A_FIT_FILE))
    assert out.ok is False
    assert out.error.code == "INVALID_INPUT"


def test_get_file_info_truncated_before_header_complete_error():
    # GetFileInfo deliberately stops after the first message (see its
    # axiom.yaml description) and therefore does NOT validate the file's
    # trailing CRC or later bytes -- a truncation/corruption AFTER a
    # complete, well-formed file_id message legitimately still succeeds
    # here (that tradeoff is covered by list_message_types_test.py, which
    # reads to EOF). What GetFileInfo must still reject is a file that
    # doesn't even have a complete 12-byte header.
    ax = _TestContext()
    out = get_file_info(ax, FitInput(data=ACTIVITY_FIXTURE[:8]))
    assert out.ok is False
    assert out.error.code == "INVALID_INPUT"


def test_get_file_info_bad_magic_bytes_error():
    ax = _TestContext()
    corrupted = bytearray(ACTIVITY_FIXTURE)
    corrupted[8:12] = b"XXXX"  # was b".FIT"
    out = get_file_info(ax, FitInput(data=bytes(corrupted)))
    assert out.ok is False
    assert out.error.code == "INVALID_INPUT"


def test_get_file_info_is_deterministic():
    ax = _TestContext()
    out1 = get_file_info(ax, FitInput(data=ACTIVITY_FIXTURE))
    out2 = get_file_info(ax, FitInput(data=ACTIVITY_FIXTURE))
    assert out1.file_id == out2.file_id
