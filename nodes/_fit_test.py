import pytest

from nodes._common import FitDecodeError
from nodes._fit import open_fit


def test_open_fit_rejects_non_bytes_input():
    # python-fitparse's file-open helper treats a `str` argument as a
    # filesystem PATH, not file contents (see nodes._common.raw_bytes'
    # docstring) -- open_fit must refuse anything that isn't already
    # `bytes`/`bytearray` rather than ever forwarding a str to FitFile().
    with pytest.raises(FitDecodeError) as exc:
        open_fit("/etc/passwd")
    assert exc.value.code == "INVALID_INPUT"


def test_open_fit_rejects_empty_bytes():
    with pytest.raises(FitDecodeError):
        open_fit(b"")
