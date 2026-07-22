from gen.messages_pb2 import FitInput, ListMessageTypesOutput, MessageTypeCount
from gen.axiom_context import AxiomContext
from nodes._common import FitDecodeError, err_from_exc, raw_bytes
from nodes._fit import open_fit, list_message_types as _list_message_types


def list_message_types(ax: AxiomContext, input: FitInput) -> ListMessageTypesOutput:
    """Inventory every distinct FIT message type present in the file and how
    many of each, without materializing any message's fields.
    """
    try:
        data = raw_bytes(input)
        fitfile = open_fit(data)
        types, total = _list_message_types(fitfile)
    except FitDecodeError as exc:
        return ListMessageTypesOutput(error=err_from_exc(exc))

    return ListMessageTypesOutput(
        message_types=[MessageTypeCount(**t) for t in types],
        total_messages=total,
        ok=True,
    )
