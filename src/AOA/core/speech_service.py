from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import subprocess
import tempfile
import threading
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from urllib import request


@dataclass(frozen=True)
class SpeechRequest:
    text: str
    engine: str = "Auto"
    voice_name: str = ""
    rate: int = -1
    volume: int = 92
    voicebox_url: str = ""
    voicebox_voice: str = "female"


class AliceSpeechService:
    """Non-blocking ALICE speech with online and offline fallbacks."""

    def __init__(self, *, cache_size: int = 8) -> None:
        self._lock = threading.RLock()
        self._generation = 0
        self._active_process: subprocess.Popen[str] | None = None
        self._cache_size = max(0, int(cache_size))
        self._google_cache: OrderedDict[str, bytes] = OrderedDict()

    def speak_async(
        self,
        speech: SpeechRequest,
        *,
        on_started: Callable[[], None] | None = None,
        on_finished: Callable[[str], None] | None = None,
        on_error: Callable[[str], None] | None = None,
    ) -> None:
        text = str(speech.text or "").strip()
        if not text:
            return
        request_snapshot = SpeechRequest(
            text=text,
            engine=speech.engine,
            voice_name=speech.voice_name,
            rate=speech.rate,
            volume=speech.volume,
            voicebox_url=speech.voicebox_url,
            voicebox_voice=speech.voicebox_voice,
        )
        with self._lock:
            self._generation += 1
            token = self._generation
            self._terminate_active_locked()

        def _worker() -> None:
            if not self._is_current(token):
                return
            if on_started:
                on_started()
            try:
                used_engine = self._run_request(request_snapshot, token)
            except Exception as exc:
                if self._is_current(token) and on_error:
                    on_error(str(exc))
                return
            if not self._is_current(token):
                return
            if used_engine:
                if on_finished:
                    on_finished(used_engine)
            elif on_error:
                on_error("Nie udalo sie uruchomic zadnego silnika glosu.")

        threading.Thread(target=_worker, name="alice-speech", daemon=True).start()

    def stop(self) -> None:
        with self._lock:
            self._generation += 1
            self._terminate_active_locked()

    def _run_request(self, speech: SpeechRequest, token: int) -> str | None:
        engine = speech.engine.strip().casefold()
        if engine in {"auto", "google", "gtts"}:
            if self._speak_google(speech, token):
                return "Google"
            if not self._is_current(token):
                return None
            if self._speak_windows(speech, token):
                return "Windows (fallback)" if engine == "auto" else "Windows (po bledzie Google)"
            return None
        if engine == "voicebox":
            if self._speak_voicebox(speech, token):
                return "Voicebox"
            if not self._is_current(token):
                return None
            if self._speak_windows(speech, token):
                return "Windows (fallback)"
            return None
        return "Windows" if self._speak_windows(speech, token) else None

    def _speak_google(self, speech: SpeechRequest, token: int) -> bool:
        if not self._is_current(token):
            return False
        cache_key = hashlib.sha256(f"pl\0{speech.text}".encode()).hexdigest()
        with self._lock:
            audio = self._google_cache.get(cache_key)
            if audio is not None:
                self._google_cache.move_to_end(cache_key)
        if audio is None:
            try:
                from gtts import gTTS

                buffer = io.BytesIO()
                gTTS(
                    text=speech.text,
                    lang="pl",
                    slow=False,
                    lang_check=False,
                    timeout=(3.05, 8),
                ).write_to_fp(buffer)
                audio = buffer.getvalue()
            except Exception:
                return False
            if not audio or not self._is_current(token):
                return False
            self._remember_google_audio(cache_key, audio)
        return self._play_audio_bytes(audio, ".mp3", speech.volume, token)

    def _speak_voicebox(self, speech: SpeechRequest, token: int) -> bool:
        url = speech.voicebox_url.strip()
        if not url or not self._is_current(token):
            return False
        payload = {
            "text": speech.text,
            "voice": speech.voicebox_voice.strip() or "female",
            "voice_id": speech.voicebox_voice.strip() or "female",
            "format": "wav",
        }
        req = request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "User-Agent": "AOA-ALICE/1.0"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=20) as response:
                content_type = response.headers.get("Content-Type", "")
                audio = response.read()
        except Exception:
            return False
        if "audio" not in content_type.casefold() or not audio or not self._is_current(token):
            return False
        suffix = ".mp3" if "mpeg" in content_type.casefold() else ".wav"
        return self._play_audio_bytes(audio, suffix, speech.volume, token)

    def _speak_windows(self, speech: SpeechRequest, token: int) -> bool:
        if not self._is_current(token):
            return False
        encoded_text = self._powershell_base64(speech.text)
        encoded_voice = self._powershell_base64(speech.voice_name)
        rate = max(-10, min(10, int(speech.rate)))
        volume = max(0, min(100, int(speech.volume)))
        script = (
            "Add-Type -AssemblyName System.Speech; "
            f"$speech = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{encoded_text}')); "
            f"$chosenName = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{encoded_voice}')); "
            "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            "$voices = $s.GetInstalledVoices() | Where-Object { $_.Enabled } | "
            "ForEach-Object { $_.VoiceInfo }; "
            "$chosen = $voices | Where-Object { $_.Name -eq $chosenName } | Select-Object -First 1; "
            "$femalePl = $voices | Where-Object { $_.Culture.Name -like 'pl*' -and "
            "$_.Gender -eq 'Female' } | Select-Object -First 1; "
            "$femaleAny = $voices | Where-Object { $_.Gender -eq 'Female' } | Select-Object -First 1; "
            "$selected = if ($chosen) { $chosen } elseif ($femalePl) { $femalePl } "
            "elseif ($femaleAny) { $femaleAny } else { $null }; "
            "if ($selected) { $s.SelectVoice($selected.Name) }; "
            f"$s.Rate = {rate}; $s.Volume = {volume}; $s.Speak($speech);"
        )
        return self._run_process(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                script,
            ],
            token,
            timeout=75,
        )

    def _play_audio_bytes(self, audio: bytes, suffix: str, volume: int, token: int) -> bool:
        descriptor, temporary_name = tempfile.mkstemp(prefix="aoa_alice_", suffix=suffix)
        os.close(descriptor)
        temporary = Path(temporary_name)
        try:
            temporary.write_bytes(audio)
            return self._play_audio_file(temporary, volume, token)
        finally:
            temporary.unlink(missing_ok=True)

    def _play_audio_file(self, path: Path, volume: int, token: int) -> bool:
        if not self._is_current(token):
            return False
        encoded_path = self._powershell_base64(str(path))
        safe_volume = max(0, min(100, int(volume)))
        script = (
            "Add-Type -AssemblyName PresentationCore; "
            f"$audioPath = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{encoded_path}')); "
            "$player = New-Object System.Windows.Media.MediaPlayer; "
            "$player.Open([Uri]::new($audioPath)); "
            f"$player.Volume = {safe_volume / 100:.2f}; "
            "$player.Play(); $waited = 0; "
            "while (-not $player.NaturalDuration.HasTimeSpan -and $waited -lt 100) { "
            "Start-Sleep -Milliseconds 50; $waited++ }; "
            "if ($player.NaturalDuration.HasTimeSpan) { "
            "$duration = [Math]::Ceiling($player.NaturalDuration.TimeSpan.TotalMilliseconds) + 250; "
            "Start-Sleep -Milliseconds $duration } else { Start-Sleep -Seconds 30 }; "
            "$player.Stop(); $player.Close();"
        )
        return self._run_process(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                script,
            ],
            token,
            timeout=75,
        )

    def _run_process(self, command: list[str], token: int, *, timeout: int) -> bool:
        if not self._is_current(token):
            return False
        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except Exception:
            return False
        with self._lock:
            if token != self._generation:
                self._terminate_process(process)
                return False
            self._active_process = process
        try:
            process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            self._terminate_process(process)
            return False
        finally:
            with self._lock:
                if self._active_process is process:
                    self._active_process = None
        return process.returncode == 0 and self._is_current(token)

    def _remember_google_audio(self, key: str, audio: bytes) -> None:
        if self._cache_size <= 0:
            return
        with self._lock:
            self._google_cache[key] = audio
            self._google_cache.move_to_end(key)
            while len(self._google_cache) > self._cache_size:
                self._google_cache.popitem(last=False)

    @staticmethod
    def _powershell_base64(value: str) -> str:
        return base64.b64encode(str(value).encode()).decode("ascii")

    def _is_current(self, token: int) -> bool:
        with self._lock:
            return token == self._generation

    def _terminate_active_locked(self) -> None:
        process = self._active_process
        self._active_process = None
        if process is not None:
            self._terminate_process(process)

    @staticmethod
    def _terminate_process(process: subprocess.Popen[str]) -> None:
        try:
            process.terminate()
            process.wait(timeout=2)
        except Exception:
            try:
                process.kill()
            except Exception:
                pass
