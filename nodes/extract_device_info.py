from gen.messages_pb2 import FitInput, ExtractDeviceInfoOutput, DeviceInfo
from gen.axiom_context import AxiomContext
from nodes._common import FitDecodeError, err_from_exc, raw_bytes
from nodes._fit import open_fit, extract_device_info as _extract_device_info


def extract_device_info(ax: AxiomContext, input: FitInput) -> ExtractDeviceInfoOutput:
    """Extract every FIT `device_info` message: the recording device and any
    paired ANT+/Bluetooth sensors that contributed data.
    """
    try:
        data = raw_bytes(input)
        fitfile = open_fit(data)
        infos = _extract_device_info(fitfile)
    except FitDecodeError as exc:
        return ExtractDeviceInfoOutput(error=err_from_exc(exc))

    return ExtractDeviceInfoOutput(device_infos=[DeviceInfo(**d) for d in infos], ok=True)
