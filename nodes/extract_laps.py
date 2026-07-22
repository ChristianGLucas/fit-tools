from gen.messages_pb2 import FitInput, ExtractLapsOutput, Lap
from gen.axiom_context import AxiomContext
from nodes._common import FitDecodeError, err_from_exc, raw_bytes
from nodes._fit import open_fit, extract_laps as _extract_laps


def extract_laps(ax: AxiomContext, input: FitInput) -> ExtractLapsOutput:
    """Extract every FIT `lap` message: the same summary metrics as
    ExtractSessions scoped to one lap, plus the trigger that ended it
    (manual, distance, time, session_end, ...).
    """
    try:
        data = raw_bytes(input)
        fitfile = open_fit(data)
        laps = _extract_laps(fitfile)
    except FitDecodeError as exc:
        return ExtractLapsOutput(error=err_from_exc(exc))

    return ExtractLapsOutput(laps=[Lap(**l) for l in laps], ok=True)
