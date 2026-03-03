"""Utility script to execute the calibrated AQI voice governance sweep."""

from __future__ import annotations

import logging
import os
import tempfile
import threading
import wave
from typing import Callable

from aqi_voice_qpc_wrapper import VoiceQPCWrapper
from aqi_daily_governance_runner import run_daily_governance


_WHISPER_MODEL = None
_WHISPER_MODEL_LOCK = threading.Lock()


def _load_whisper_model():
    global _WHISPER_MODEL
    if _WHISPER_MODEL is not None:
        return _WHISPER_MODEL

    model_size = os.environ.get("AQI_WHISPER_MODEL", "medium")
    device = os.environ.get("AQI_WHISPER_DEVICE", "auto")
    compute_type = os.environ.get("AQI_WHISPER_COMPUTE", os.environ.get("AQI_WHISPER_COMPUTE_TYPE", "int8"))

    with _WHISPER_MODEL_LOCK:
        if _WHISPER_MODEL is None:
            try:
                from faster_whisper import WhisperModel
            except ImportError as exc:  # pragma: no cover - configuration issue
                raise RuntimeError("faster-whisper is not installed in this environment") from exc

            logging.getLogger(__name__).info(
                "Loading Whisper model",
                extra={"model_size": model_size, "device": device, "compute_type": compute_type},
            )
            _WHISPER_MODEL = WhisperModel(model_size, device=device, compute_type=compute_type)

    return _WHISPER_MODEL


def _resolve_transcribe_fn() -> Callable[[bytes], str]:
    try:
        from aqi_stt_engine import transcribe_audio as resolved
        return resolved
    except (ImportError, AttributeError):

        def resolved(audio_bytes: bytes) -> str:
            model = _load_whisper_model()

            sample_rate = int(os.environ.get("AQI_AUDIO_SAMPLE_RATE", "16000"))
            num_channels = int(os.environ.get("AQI_AUDIO_CHANNELS", "1"))
            sample_width = int(os.environ.get("AQI_AUDIO_SAMPLE_WIDTH", "2"))

            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_audio:
                audio_path = tmp_audio.name

            try:
                with wave.open(audio_path, "wb") as wav_file:
                    wav_file.setnchannels(num_channels)
                    wav_file.setsampwidth(sample_width)
                    wav_file.setframerate(sample_rate)
                    wav_file.writeframes(audio_bytes)

                segments, _ = model.transcribe(audio_path, beam_size=5)
                transcript = " ".join(segment.text.strip() for segment in segments).strip()
                return transcript
            finally:
                try:
                    os.remove(audio_path)
                except OSError:
                    logging.getLogger(__name__).warning("Failed to remove temp audio", exc_info=True)

    return resolved


_ELEVEN_CLIENT = None
_ELEVEN_CLIENT_LOCK = threading.Lock()


def _load_elevenlabs_client():
    global _ELEVEN_CLIENT
    if _ELEVEN_CLIENT is not None:
        return _ELEVEN_CLIENT

    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        raise RuntimeError("ELEVENLABS_API_KEY environment variable is not set")

    with _ELEVEN_CLIENT_LOCK:
        if _ELEVEN_CLIENT is None:
            try:
                from elevenlabs import ElevenLabs
            except ImportError as exc:  # pragma: no cover - configuration issue
                raise RuntimeError("elevenlabs package is not installed in this environment") from exc

            logging.getLogger(__name__).info("Initializing ElevenLabs client")
            _ELEVEN_CLIENT = ElevenLabs(api_key=api_key)

    return _ELEVEN_CLIENT


def _resolve_tts_fn() -> Callable[[str], bytes]:
    try:
        from aqi_tts_engine import synthesize_text as resolved
        return resolved
    except (ImportError, AttributeError):

        def resolved(text: str) -> bytes:
            client = _load_elevenlabs_client()
            voice_id = os.environ.get("ELEVENLABS_VOICE_ID")
            if not voice_id:
                raise RuntimeError("ELEVENLABS_VOICE_ID environment variable is not set")

            model_id = os.environ.get("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2")
            audio_stream = client.text_to_speech.convert(
                voice_id=voice_id,
                model_id=model_id,
                text=text,
            )
            return b"".join(audio_stream)

    return resolved


def main() -> None:
    wrapper = VoiceQPCWrapper(
        transcribe_fn=_resolve_transcribe_fn(),
        synthesize_fn=_resolve_tts_fn(),
    )
    run_daily_governance(wrapper)


if __name__ == "__main__":
    main()
