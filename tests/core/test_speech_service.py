from __future__ import annotations

import threading
from pathlib import Path

import gtts

from AOA.core import speech_service as speech_module
from AOA.core.speech_service import AliceSpeechService, SpeechRequest


def _active_service() -> tuple[AliceSpeechService, int]:
    service = AliceSpeechService()
    service._generation = 1
    return service, 1


def test_auto_voice_uses_windows_when_google_is_unavailable(monkeypatch) -> None:
    service, token = _active_service()
    monkeypatch.setattr(service, "_speak_google", lambda _speech, _token: False)
    monkeypatch.setattr(service, "_speak_windows", lambda _speech, _token: True)

    used_engine = service._run_request(SpeechRequest("Test", engine="Auto"), token)

    assert used_engine == "Windows (fallback)"


def test_google_voice_uses_polish_mp3_cache_and_removes_temporary_file(monkeypatch) -> None:
    service, token = _active_service()
    calls: list[dict[str, object]] = []
    temporary_paths: list[Path] = []

    class FakeGtts:
        def __init__(self, **kwargs) -> None:
            calls.append(kwargs)

        def write_to_fp(self, buffer) -> None:
            buffer.write(b"fake-mp3")

    def fake_play(path: Path, volume: int, received_token: int) -> bool:
        assert path.exists()
        assert path.suffix == ".mp3"
        assert volume == 88
        assert received_token == token
        temporary_paths.append(path)
        return True

    monkeypatch.setattr(gtts, "gTTS", FakeGtts)
    monkeypatch.setattr(service, "_play_audio_file", fake_play)
    speech = SpeechRequest("Dzien dobry", engine="Google", volume=88)

    assert service._speak_google(speech, token)
    assert service._speak_google(speech, token)
    assert len(calls) == 1
    assert calls[0]["lang"] == "pl"
    assert calls[0]["lang_check"] is False
    assert calls[0]["timeout"] == (3.05, 8)
    assert temporary_paths and all(not path.exists() for path in temporary_paths)


def test_voicebox_rejects_non_audio_response_instead_of_silently_succeeding(
    monkeypatch,
) -> None:
    service, token = _active_service()

    class FakeResponse:
        headers = {"Content-Type": "application/json"}

        def __enter__(self):
            return self

        def __exit__(self, *_args) -> None:
            return None

        @staticmethod
        def read() -> bytes:
            return b'{"status": "ok"}'

    monkeypatch.setattr(speech_module.request, "urlopen", lambda *_args, **_kwargs: FakeResponse())

    assert not service._speak_voicebox(
        SpeechRequest("Test", voicebox_url="http://127.0.0.1:17493/speak"), token
    )


def test_windows_voice_passes_full_text_as_base64_instead_of_split_arguments(
    monkeypatch,
) -> None:
    service, token = _active_service()
    commands: list[list[str]] = []

    def capture(command: list[str], _token: int, *, timeout: int) -> bool:
        commands.append(command)
        assert timeout == 75
        return True

    monkeypatch.setattr(service, "_run_process", capture)
    speech = SpeechRequest("Ala ma kota i psa.", voice_name="Polski glos")

    assert service._speak_windows(speech, token)
    assert len(commands) == 1
    assert len(commands[0]) == 6
    assert "Ala ma kota i psa." not in commands[0][-1]
    assert service._powershell_base64("Ala ma kota i psa.") in commands[0][-1]


def test_speak_async_reports_selected_engine(monkeypatch) -> None:
    service = AliceSpeechService()
    finished = threading.Event()
    result: list[str] = []
    monkeypatch.setattr(service, "_run_request", lambda _speech, _token: "Google")

    def record_finished(engine: str) -> None:
        result.append(engine)
        finished.set()

    service.speak_async(
        SpeechRequest("Test"),
        on_finished=record_finished,
    )

    assert finished.wait(2)
    assert result == ["Google"]
