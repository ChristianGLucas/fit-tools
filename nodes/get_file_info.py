from gen.messages_pb2 import FitInput, GetFileInfoOutput, FileId
from gen.axiom_context import AxiomContext
from nodes._common import FitDecodeError, err, err_from_exc, raw_bytes
from nodes._fit import open_fit, get_file_info as _get_file_info


def get_file_info(ax: AxiomContext, input: FitInput) -> GetFileInfoOutput:
    """Decode just the FIT file's `file_id` message: file type, manufacturer,
    product, serial number, and creation time. Cheapest node to call first
    when a file's exact contents aren't yet known — stops after the first
    message.
    """
    try:
        data = raw_bytes(input)
        fitfile = open_fit(data)
        info = _get_file_info(fitfile)
    except FitDecodeError as exc:
        return GetFileInfoOutput(error=err_from_exc(exc))

    if info is None:
        return GetFileInfoOutput(error=err("INVALID_INPUT", "FIT file has no file_id message"))

    return GetFileInfoOutput(file_id=FileId(**info), ok=True)
