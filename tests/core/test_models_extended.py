import pytest

from AOA.core.models import _emit_progress


def test_emit_progress_supports_three_argument_callback():
    calls = []

    def callback(model_name, percent, detail):
        calls.append((model_name, percent, detail))

    _emit_progress(callback, "Quality", 12.5, "step")

    assert calls == [("Quality", 12.5, "step")]


def test_emit_progress_supports_two_argument_callback():
    calls = []

    def callback(model_name, percent):
        calls.append((model_name, percent))

    _emit_progress(callback, "Quality", 12.5, "step")

    assert calls == [("Quality", 12.5)]


def test_emit_progress_supports_single_argument_callback():
    calls = []

    def callback(percent):
        calls.append(percent)

    _emit_progress(callback, "Quality", 12.5, "step")

    assert calls == [12.5]


def test_emit_progress_does_not_swallow_internal_type_error():
    def callback(model_name, percent, detail):
        return 1 + "x"

    with pytest.raises(TypeError):
        _emit_progress(callback, "Quality", 12.5, "step")


def test_emit_progress_raises_for_unsupported_signature():
    def callback():
        return None

    with pytest.raises(TypeError, match="Progress callback must accept"):
        _emit_progress(callback, "Quality", 12.5, "step")
