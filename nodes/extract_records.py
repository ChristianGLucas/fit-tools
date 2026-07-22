from gen.messages_pb2 import ExtractRecordsInput, ExtractRecordsOutput, Record
from gen.axiom_context import AxiomContext
from nodes._common import DEFAULT_RECORD_LIMIT, MAX_RECORD_LIMIT, FitDecodeError, err, err_from_exc, raw_bytes
from nodes._fit import open_fit, extract_records as _extract_records


def extract_records(ax: AxiomContext, input: ExtractRecordsInput) -> ExtractRecordsOutput:
    """Extract the FIT `record` messages — the per-sample activity time
    series (timestamp, position, altitude, heart rate, power, cadence,
    speed, temperature, cumulative distance) — as a flat, time-ordered
    array, capped at `limit` (default 1000, max 1500 — sized to stay under
    the platform's deployed-invocation payload limit).
    """
    limit = input.limit if input.limit > 0 else DEFAULT_RECORD_LIMIT
    if limit > MAX_RECORD_LIMIT:
        return ExtractRecordsOutput(error=err("INVALID_ARGUMENT", f"limit {limit} exceeds the {MAX_RECORD_LIMIT} maximum"))

    try:
        data = raw_bytes(input.fit)
        fitfile = open_fit(data)
        records, total, truncated = _extract_records(fitfile, limit)
    except FitDecodeError as exc:
        return ExtractRecordsOutput(error=err_from_exc(exc))

    return ExtractRecordsOutput(
        records=[Record(**r) for r in records],
        truncated=truncated,
        total_available=total,
        ok=True,
    )
