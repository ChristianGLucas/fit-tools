from gen.messages_pb2 import FitInput, ExtractSessionsOutput, Session
from gen.axiom_context import AxiomContext
from nodes._common import FitDecodeError, err_from_exc, raw_bytes
from nodes._fit import open_fit, extract_sessions as _extract_sessions


def extract_sessions(ax: AxiomContext, input: FitInput) -> ExtractSessionsOutput:
    """Extract every FIT `session` message: sport, start time, duration,
    distance, calories, heart rate, speed, power, cadence, and
    ascent/descent — the whole-activity summary view.
    """
    try:
        data = raw_bytes(input)
        fitfile = open_fit(data)
        sessions = _extract_sessions(fitfile)
    except FitDecodeError as exc:
        return ExtractSessionsOutput(error=err_from_exc(exc))

    return ExtractSessionsOutput(sessions=[Session(**s) for s in sessions], ok=True)
