"""
AQI STT Engine (v1.0)
Author: Copilot (for TimmyJ)
Purpose:
    - Provide streaming speech-to-text for AQI Voice Module
    - Isolated, swappable engine (Whisper or cloud)
    - No direct dependency on Alan or AQI core

Design:
    - Receives audio chunks from Voice Module
    - Buffers audio per session
    - Periodically transcribes buffered audio
    - Calls stt_callback(text, session_id) when new text is available
"""

import asyncio
import base64
import io
import os
import logging
import audioop # Optimized decoding
from typing import Callable, Dict, Optional
from openai import OpenAI
from pydub import AudioSegment

# ---------------------------------------------------------
# CONFIG
# ---------------------------------------------------------

STT_ENABLED = True
STT_ENGINE = "cloud"  # Changed to cloud for real STT
STT_MIN_BUFFER_MS = 500 # [ATTEMPT 11] Aggressive reduction from 2500ms to 500ms for "Snap"

logger = logging.getLogger("AQI_STT")
logger.setLevel(logging.INFO)

# ---------------------------------------------------------
# STATE
# ---------------------------------------------------------

class STTSessionBuffer:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.audio_segments = []  # list[AudioSegment]
        self.lock = asyncio.Lock()
        self.last_transcribed_ms = 0


stt_sessions: Dict[str, STTSessionBuffer] = {}
stt_callback: Optional[Callable[[str, str], None]] = None

# ---------------------------------------------------------
# PUBLIC API
# ---------------------------------------------------------


def register_stt_callback(callback: Callable[[str, str], None]):
    """
    AQI Voice Module calls this so the STT engine can deliver text to Alan.
    """
    global stt_callback
    stt_callback = callback


def create_stt_session(session_id: str):
    """
    Called when a new voice session starts.
    """
    stt_sessions[session_id] = STTSessionBuffer(session_id)


def close_stt_session(session_id: str):
    """
    Called when a voice session ends.
    """
    if session_id in stt_sessions:
        del stt_sessions[session_id]


def clear_buffer(session_id: str):
    """
    [ATTEMPT 12] Nuclear Pounce - Clear STT Buffer
    Drops all accumulated audio to prevent 'Hello Queue' processing.
    """
    session = stt_sessions.get(session_id)
    if session:
        # No lock needed for simple list clear if we don't mind race conditions on append, 
        # but technically safer with lock. For speed, just reassign.
        session.audio_segments = []
        # Reset tracker so next check starts fresh output
        session.last_transcribed_ms = 0
        logger.info(f"STT Buffer Cleared for {session_id}")


async def finalize_and_clear(session_id: str):
    """
    [ATTEMPT 46] Server-Side VAD - Finalize Turn
    Transcribe whatever is in the buffer, emit it, then nukes the buffer.
    This ensures we don't re-transcribe old audio, preventing the 40s lag.
    """
    session = stt_sessions.get(session_id)
    if not session or not session.audio_segments:
        return

    async with session.lock:
        if not session.audio_segments: return None
        merged = sum(session.audio_segments)
        text = await _transcribe_and_emit(session, merged)
        
        # [CLEAN-CUT] Nuke the buffer for the next turn
        session.audio_segments = []
        session.last_transcribed_ms = 0
        logger.info(f"[STT] Finalized Turn for {session_id}. Buffer Cleared.")
        return text

async def process_audio_chunk(session_id: str, b64_data: str, fmt: str):
    """
    Main entry point for audio chunks from the Voice Module.
    """
    if not STT_ENABLED:
        return

    session = stt_sessions.get(session_id)
    if not session:
        return

    raw_bytes = base64.b64decode(b64_data)

    try:
        pcm_data = audioop.ulaw2lin(raw_bytes, 2)
        audio_segment = AudioSegment(
            data=pcm_data,
            sample_width=2,
            frame_rate=8000,
            channels=1
        )
    except Exception as e:
        logger.error(f"Error decoding audio chunk: {e}")
        return

    async with session.lock:
        session.audio_segments.append(audio_segment)
        # [ATTEMPT 46] No auto-transcribe. Wait for "Commit" signal from VAD.
        # This prevents "Partial Hallucinations" and saves API costs/latency.



# ---------------------------------------------------------


# INTERNAL TRANSCRIPTION LOGIC
# ---------------------------------------------------------


async def _transcribe_and_emit(session: STTSessionBuffer, merged: AudioSegment) -> Optional[str]:
    """
    Runs STT on the buffered audio and emits text via stt_callback.
    """
    global stt_callback

    # For Whisper, we need a WAV/PCM-like format
    wav_io = io.BytesIO()
    # Pydub export can be slow, run in executor if possible, but it's CPU bound. 
    # For now, keep it here or offload. Optimallyオフload.
    await asyncio.to_thread(merged.export, wav_io, format="wav")
    wav_io.seek(0)
    
    # [ATTEMPT 47] NON-BLOCKING API CALL
    # Run the synchronous API call in a separate thread to avoid blocking the event loop.
    if STT_ENGINE == "whisper_local":
        text = await _run_whisper_local(wav_io)
    else:
        text = await asyncio.to_thread(_run_cloud_stt_sync, wav_io)

    if text and text.strip():
        # Clean text
        text = text.strip()
        
        # [ATTEMPT 49] ASYNC CALLBACK SUPPORT
        try:
            if stt_callback:
                if asyncio.iscoroutinefunction(stt_callback):
                    await stt_callback(text, session.session_id)
                else:
                    stt_callback(text, session.session_id)
        except Exception as e:
            logger.warning(f"STT Callback failed (harmless): {e}")
            
        # Update last_transcribed_ms to total buffer duration
        session.last_transcribed_ms = merged.duration_seconds * 1000
        
        return text
    return None

# Wrapper for synchronous cloud call
def _run_cloud_stt_sync(wav_io: io.BytesIO) -> str:
    # Re-use _run_cloud_stt logic but sync
    return asyncio.run(_run_cloud_stt(wav_io)) if asyncio.iscoroutinefunction(_run_cloud_stt) else _run_cloud_stt_internal(wav_io)

def _run_cloud_stt_internal(wav_io: io.BytesIO) -> str:
    """
    Internal Sync Logic for Cloud STT
    """
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            try:
                import json
                with open("agent_alan_config.json", "r") as f:
                    cfg = json.load(f)
                    api_key = cfg.get("openai_api_key")
            except Exception:
                pass

        if not api_key:
            logger.error("No OPENAI_API_KEY found for STT.")
            return ""

        # Explicitly ignore any tunnel URL in environment
        # logger.info("Connecting to OpenAI (api.openai.com) for STT...")
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.openai.com/v1" 
        )
        
        wav_io.name = "audio.wav"
        
        transcript = client.audio.transcriptions.create(
            model="whisper-1", 
            file=wav_io,
            prompt="Hello, this is a business call related to merchant services." 
        )
        
        text = transcript.text
        if text:
            logger.info(f"TRANSCRIPT: {text}")
        return text

    except Exception as e:
        logger.error(f"STT Error: {e}")
        return ""

async def inject_transcript(session_id: str, text: str):
    """
    [DEBUG] Inject a text transcript directly as if users spoke it.
    Used for verifying the Agent Logic Layer without needing audio.
    """
    if stt_callback:
        logger.info(f"[INJECT] Injecting debug transcript for {session_id}: '{text}'")
        if asyncio.iscoroutinefunction(stt_callback):
            await stt_callback(text, session_id)
        else:
            stt_callback(text, session_id)

async def _run_cloud_stt(wav_io: io.BytesIO) -> str:
    # Deprecated async wrapper, keeping for interface compat if needed
    return await asyncio.to_thread(_run_cloud_stt_internal, wav_io)
