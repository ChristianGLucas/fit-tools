from gen.messages_pb2 import FitInput
from nodes._test_helpers import _TestContext
from nodes.extract_device_info import extract_device_info
from nodes._fit_fixtures import ACTIVITY_FIXTURE, EXPECTED_DEVICE_INFO, NOT_A_FIT_FILE


def test_extract_device_info_matches_hand_computed_oracle():
    # Independent oracle covering the OPPOSITE branch from get_file_info's
    # test: product=65000 is not in the FIT profile's garmin_product table,
    # so it must come back as a raw numeric id, never a resolved name.
    ax = _TestContext()
    out = extract_device_info(ax, FitInput(data=ACTIVITY_FIXTURE))
    assert out.ok is True
    assert len(out.device_infos) == 1
    d = out.device_infos[0]
    assert d.device_index == EXPECTED_DEVICE_INFO["device_index"]
    assert d.manufacturer == EXPECTED_DEVICE_INFO["manufacturer"]
    assert d.product == EXPECTED_DEVICE_INFO["product"]
    assert d.product_id == EXPECTED_DEVICE_INFO["product_id"]
    assert d.has_product_id == EXPECTED_DEVICE_INFO["has_product_id"]
    assert d.serial_number == EXPECTED_DEVICE_INFO["serial_number"]
    assert d.software_version == EXPECTED_DEVICE_INFO["software_version"]
    assert d.battery_status == EXPECTED_DEVICE_INFO["battery_status"]
    assert d.source_type == EXPECTED_DEVICE_INFO["source_type"]


def test_extract_device_info_error_on_garbage():
    ax = _TestContext()
    out = extract_device_info(ax, FitInput(data=NOT_A_FIT_FILE))
    assert out.ok is False
    assert out.error.code == "INVALID_INPUT"
