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
import struct
import time
from typing import Callable, Dict, Optional
from openai import OpenAI
from pydub import AudioSegment

# ---------------------------------------------------------
# CONFIG
# ---------------------------------------------------------

STT_ENABLED = True

# [GROQ UPGRADE] Groq Whisper — 200-400ms vs OpenAI's 1-2s
# Groq runs Whisper on LPU hardware, 3-5x faster than OpenAI.
# Falls back to OpenAI Whisper if Groq fails.
_cached_groq_client = None
_cached_openai_client = None

def _get_groq_client():
    """Return a cached Groq client for fast Whisper STT."""
    global _cached_groq_client
    if _cached_groq_client is not None:
        return _cached_groq_client
    
    api_key = os.getenv("GROQ_API_KEY")
    
    # [FIX] If key not in env (PowerShell session may not have it),
    # try loading from .env file directly via dotenv
    if not api_key:
        try:
            from dotenv import dotenv_values
            _env_vals = dotenv_values(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
            api_key = _env_vals.get("GROQ_API_KEY")
            if api_key:
                logger.info("[STT] GROQ_API_KEY loaded from .env file (not in environment)")
        except Exception as _dotenv_err:
            logger.debug(f"[STT] dotenv fallback failed: {_dotenv_err}")
    
    # [FIX] Also try agent_alan_config.json as last resort
    if not api_key:
        try:
            import json as _json
            _cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "agent_alan_config.json")
            with open(_cfg_path, "r") as _f:
                api_key = _json.load(_f).get("groq_api_key")
            if api_key:
                logger.info("[STT] GROQ_API_KEY loaded from agent_alan_config.json")
        except Exception:
            pass
    
    if not api_key:
        logger.warning("No GROQ_API_KEY found. Will fall back to OpenAI Whisper.")
        return None
    
    _cached_groq_client = OpenAI(
        api_key=api_key,
        base_url="https://api.groq.com/openai/v1",
        timeout=10.0  # [TIMING AUDIT] Prevent infinite hangs on Groq API
    )
    logger.info("[STT] Groq Whisper client initialized (fast mode)")
    return _cached_groq_client

def _get_stt_client():
    """Return a cached OpenAI client for Whisper STT (fallback)."""
    global _cached_openai_client
    if _cached_openai_client is not None:
        return _cached_openai_client
    
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
        return None
    
    _cached_openai_client = OpenAI(
        api_key=api_key,
        base_url="https://api.openai.com/v1",
        timeout=15.0  # [TIMING AUDIT] Prevent infinite hangs on OpenAI STT
    )
    return _cached_openai_client
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


# Known Whisper hallucination patterns on silence/noise
# CRITICAL: Only include phrases that Whisper FABRICATES from noise/silence.
# These are YouTube-trained artifacts that appear when there is NO real speech.
# NEVER filter real human words here — "thank you", "yeah", "bye", "um" etc.
# are LEGITIMATE speech that Alan MUST hear. Filtering them makes Alan deaf.
WHISPER_HALLUCINATIONS = {
    "thank you for watching",
    "thanks for watching",
    "please subscribe",
    "like and subscribe",
    "subscribe to my channel",
    "don't forget to subscribe",
    "the end",
    "...",
    # Echo hallucinations — Whisper generates these from Alan's own echo audio
    "for more information visit www.signaturecard.com",
    "for more information visit www signaturecard com",
    "visit www.signaturecard.com",
    "signaturecard.com",
    "signature card services",
}

# Minimum audio duration (seconds) to bother sending to Whisper
STT_MIN_AUDIO_DURATION = 0.3

# Minimum RMS energy to consider audio as actual speech (not noise/silence)
# Lowered from 300 — phone audio has attenuated energy, quiet speakers exist
STT_MIN_RMS_ENERGY = 150


async def finalize_and_clear(session_id: str):
    """
    [ATTEMPT 46] Server-Side VAD - Finalize Turn
    Transcribe whatever is in the buffer, emit it, then nukes the buffer.
    This ensures we don't re-transcribe old audio, preventing the 40s lag.
    
    [FIX] Added minimum energy/duration checks and hallucination filtering
    to prevent phantom transcripts from noise/silence.
    """
    session = stt_sessions.get(session_id)
    if not session or not session.audio_segments:
        return

    async with session.lock:
        if not session.audio_segments: return None
        merged = sum(session.audio_segments)
        
        # [SPEED FIX] Cap audio length sent to Groq — longer audio = slower transcription.
        # Groq takes ~200ms for 2s audio but ~1500ms for 10s+ audio.
        # Phone speech rarely exceeds 8 seconds per turn. If it does,
        # keep only the last 8 seconds — the start is usually noise/silence anyway.
        MAX_STT_DURATION = 6.0  # seconds — shorter = faster Groq transcription
        if merged.duration_seconds > MAX_STT_DURATION:
            trim_ms = int((merged.duration_seconds - MAX_STT_DURATION) * 1000)
            merged = merged[trim_ms:]
            logger.info(f"[STT] Trimmed audio from {merged.duration_seconds + trim_ms/1000:.1f}s to {merged.duration_seconds:.1f}s for faster transcription")
        
        # [FIX 1] Skip audio too short to be real speech
        if merged.duration_seconds < STT_MIN_AUDIO_DURATION:
            logger.info(f"[STT] Audio too short ({merged.duration_seconds:.2f}s). Skipping transcription.")
            session.audio_segments = []
            session.last_transcribed_ms = 0
            return None
        
        # [FIX 2] Skip audio with too little energy (silence/background noise)
        try:
            rms = merged.rms
            if rms < STT_MIN_RMS_ENERGY:
                logger.info(f"[STT] Audio RMS too low ({rms}). Likely silence/noise. Skipping.")
                session.audio_segments = []
                session.last_transcribed_ms = 0
                return None
        except Exception:
            pass  # If RMS check fails, continue with transcription
        
        text = await _transcribe_and_emit(session, merged)
        
        # [FIX 3] Filter known Whisper hallucination patterns
        if text and text.strip().lower().rstrip('.!?,') in WHISPER_HALLUCINATIONS:
            logger.warning(f"[STT] Filtered Whisper hallucination: '{text}'. Discarding.")
            session.audio_segments = []
            session.last_transcribed_ms = 0
            return None
        
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
    
    stt_start = time.time()

    # [LAG FIX] Direct WAV construction — bypasses pydub's ffmpeg subprocess
    # Pydub export() launches an ffmpeg process which adds 200-800ms latency.
    # Instead, construct a valid WAV header manually from raw PCM data.
    # The merged AudioSegment already has raw PCM data in the correct format.
    raw_pcm = merged.raw_data
    sample_rate = merged.frame_rate
    sample_width = merged.sample_width
    channels = merged.channels
    wav_io = io.BytesIO()
    # Write WAV header (44 bytes) + raw PCM data
    data_size = len(raw_pcm)
    wav_io.write(b'RIFF')
    wav_io.write(struct.pack('<I', 36 + data_size))  # File size - 8
    wav_io.write(b'WAVE')
    wav_io.write(b'fmt ')
    wav_io.write(struct.pack('<I', 16))  # Chunk size
    wav_io.write(struct.pack('<H', 1))   # PCM format
    wav_io.write(struct.pack('<H', channels))
    wav_io.write(struct.pack('<I', sample_rate))
    wav_io.write(struct.pack('<I', sample_rate * channels * sample_width))  # Byte rate
    wav_io.write(struct.pack('<H', channels * sample_width))  # Block align
    wav_io.write(struct.pack('<H', sample_width * 8))  # Bits per sample
    wav_io.write(b'data')
    wav_io.write(struct.pack('<I', data_size))
    wav_io.write(raw_pcm)
    wav_io.seek(0)
    
    wav_ms = 1000 * (time.time() - stt_start)
    logger.info(f"[STT] WAV constructed in {wav_ms:.0f}ms ({len(raw_pcm)} bytes, {merged.duration_seconds:.1f}s audio)")
    
    # [ATTEMPT 47] NON-BLOCKING API CALL
    # Run the synchronous API call in a separate thread to avoid blocking the event loop.
    if STT_ENGINE == "whisper_local":
        text = await _run_whisper_local(wav_io)
    else:
        try:
            text = await asyncio.wait_for(
                asyncio.to_thread(_run_cloud_stt_sync, wav_io),
                timeout=12.0  # [TIMING AUDIT] Hard cap — if STT takes >12s, something is very wrong
            )
        except asyncio.TimeoutError:
            logger.error("[STT] Cloud STT TIMED OUT after 12s — returning empty to keep call alive")
            text = None

    if text and text.strip():
        # Clean text
        text = text.strip()
        
        total_stt_ms = 1000 * (time.time() - stt_start)
        logger.info(f"[STT] Total transcription time: {total_stt_ms:.0f}ms for '{text[:60]}'")
        
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
    # [LAG FIX] Direct call — old code did asyncio.run(_run_cloud_stt()) which created
    # a new event loop + spawned another thread inside the thread. 2 hops for nothing.
    return _run_cloud_stt_internal(wav_io)

def _run_cloud_stt_internal(wav_io: io.BytesIO) -> str:
    """
    Internal Sync Logic for Cloud STT
    [GROQ UPGRADE] Primary: Groq Whisper (200-400ms). Fallback: OpenAI Whisper (1-2s).
    """
    # Whisper Prompt Engineering — Full Human Range
    # [FIX 2026-02-24] Removed hallucination-prone phrases.  Whisper fabricates
    # prompt text as user speech when audio is ambiguous/silent.  Four phrases
    # were hallucinated across 70+ calls:
    #   "We process about fifty thousand a month"  (22 calls)
    #   "What company did you say? Signature Card, SCS Direct"  (32 calls)
    #   "What are your monthly volumes"  (10 calls)
    # [FIX 2026-02-24 v2] Removed "Visa, Mastercard, American Express" as a
    # contiguous phrase — appeared as hallucinated Turn 1 in Pool Cleaning LA.
    # [FIX 2026-02-24 v3] Removed "We do about, a month, per month, monthly" —
    # appeared as hallucinated Turn 0 in Townhomes For Rent Florence SC.
    # Rule: NO proper nouns, NO brand names, NO dollar amounts, NO complete
    # sentences that could be fabricated as synthetic user speech.
    # Only short conversational fragments and vocabulary tokens.
    whisper_prompt = (
        "Hello, hi, hey there. "
        "Who is this? What's this about? What's this regarding? "
        "Oh okay, hold on, let me get the owner. Sure, take your time. "
        "Yeah, this is the owner speaking. "
        "No thanks, not interested. We're good. We already have someone for that. "
        "How much can you save us? What are your rates? "
        "Send me some information. Can you call back later? I'm busy right now. "
        "Uh-huh, okay, sure, yeah, go ahead, tell me more, right, mm-hmm. "
        "What company are you with? "
        "credit card, debit card, processing fees, terminal, statement."
    )
    
    wav_io.name = "audio.wav"
    
    # [PRIMARY] Try Groq Whisper first — 3-5x faster
    groq_client = _get_groq_client()
    if groq_client:
        try:
            groq_start = time.time()
            transcript = groq_client.audio.transcriptions.create(
                model="whisper-large-v3-turbo",
                file=wav_io,
                prompt=whisper_prompt,
                language="en",
                response_format="text"
            )
            groq_ms = 1000 * (time.time() - groq_start)
            # Groq returns plain text when response_format="text"
            text = transcript if isinstance(transcript, str) else transcript.text
            if text and text.strip():
                logger.info(f"[STT-GROQ] Transcribed in {groq_ms:.0f}ms: '{text.strip()[:60]}'")
                return text.strip()
            else:
                logger.info(f"[STT-GROQ] Empty result in {groq_ms:.0f}ms")
                return ""
        except Exception as e:
            logger.warning(f"[STT-GROQ] Failed ({e}). Falling back to OpenAI Whisper.")
            wav_io.seek(0)  # Reset for fallback
    
    # [FALLBACK] OpenAI Whisper
    try:
        client = _get_stt_client()
        if not client:
            return ""
        
        transcript = client.audio.transcriptions.create(
            model="whisper-1", 
            file=wav_io,
            prompt=whisper_prompt
        )
        
        text = transcript.text
        if text:
            logger.info(f"[STT-OPENAI] TRANSCRIPT: {text}")
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
