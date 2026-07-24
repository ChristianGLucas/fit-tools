from gen.messages_pb2 import (
    FitInput, ParseActivityOutput, FileId, Session, Lap, DeviceInfo, Record,
)
from gen.axiom_context import AxiomContext
from nodes._common import FitDecodeError, err, err_from_exc, raw_bytes
from nodes._fit import (
    open_fit,
    get_file_info as _get_file_info,
    extract_sessions as _extract_sessions,
    extract_laps as _extract_laps,
    extract_device_info as _extract_device_info,
    extract_records as _extract_records,
)


def parse_activity(ax: AxiomContext, input: FitInput) -> ParseActivityOutput:
    """The general-purpose decode: file identity, every session, every lap,
    every recording device, and every one of the activity's per-sample
    records, all in one call.
    """
    try:
        data = raw_bytes(input)
        fitfile = open_fit(data)
        file_id = _get_file_info(fitfile)

        if file_id is None:
            return ParseActivityOutput(error=err("INVALID_INPUT", "FIT file has no file_id message"))

        # python-fitparse parses LAZILY, so a corrupt/truncated body or a bad
        # trailing CRC only surfaces once these later passes actually walk
        # that far into the file -- which is why they must stay INSIDE this
        # same try block rather than after it (a file_id-only error check
        # would miss corruption located later in the file).
        sessions = _extract_sessions(fitfile)
        laps = _extract_laps(fitfile)
        device_infos = _extract_device_info(fitfile)
        records, total_records, truncated = _extract_records(fitfile, None)
    except FitDecodeError as exc:
        return ParseActivityOutput(error=err_from_exc(exc))

    return ParseActivityOutput(
        file_id=FileId(**file_id),
        sessions=[Session(**s) for s in sessions],
        laps=[Lap(**l) for l in laps],
        device_infos=[DeviceInfo(**d) for d in device_infos],
        records=[Record(**r) for r in records],
        truncated=truncated,
        total_records=total_records,
        ok=True,
    )
