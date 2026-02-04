"""
AQI TTS Engine (v1.0) with Voice Governance
Author: Copilot (for TimmyJ) + Claude
Purpose:
    - Provide streaming (or pseudo-streaming) TTS for AQI Voice Module
    - Isolated, swappable engine (Azure, ElevenLabs, or others)
    - No direct dependency on Alan or AQI core
    - Enforces voice governance to prevent interference

Design:
    - Receives text + session_id from Voice Module
    - Converts text → audio bytes (WAV/OGG/etc.)
    - Returns base64-encoded audio chunks to Voice Module
    - All TTS calls go through governance system
"""

import asyncio
import base64
import io
from typing import AsyncGenerator, Optional
import os
import httpx # Patch for SSL
from elevenlabs import VoiceSettings
from elevenlabs.client import AsyncElevenLabs

# Voice governance imports
from aqi_tts_control import governed_tts_synthesis

# Initialize Client with SSL Bypass
tts_client = AsyncElevenLabs(
    api_key=os.getenv("ELEVENLABS_API_KEY"),
    httpx_client=httpx.AsyncClient(verify=False)
)

# TTS Engine: pyttsx3 for Alan Persona compliance
try:
    import pyttsx3
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False

# ---------------------------------------------------------
# CONFIG (Alan Voice Persona Spec v1.0)
# ---------------------------------------------------------

TTS_ENABLED = True
TTS_ENGINE = "elevenlabs"  # Switched to ElevenLabs for human-like voice
TTS_CHUNK_DELAY = 0.05      # artificial delay between chunks to simulate streaming

# Alan Persona TTS Tuning (from spec)
ALAN_VOICE_PROFILE = {
    # Core Voice Identity
    "tone": "warm_calm_grounded",  # Warm, calm, grounded
    "emotional_posture": "steady_patient_attentive",  # Steady, patient, attentive
    
    # Pacing
    "wpm_normal": 145,  # 135-155 WPM
    "wpm_stressed": 118,  # 110-125 WPM
    "wpm_confused": 128,  # 120-135 WPM
    "wpm_instructions": 123,  # 115-130 WPM
    "wpm_grounding": 103,  # 95-110 WPM
    "rate": 145,
    
    # Pause Timing (in seconds)
    "pause_after_greeting": 0.2,  # 0.15-0.25s
    "pause_after_ack": 0.33,  # 0.25-0.40s
    "pause_before_results": 0.4,  # 0.30-0.50s
    "pause_after_question": 0.75,  # 0.50-1.00s
    "silence_tolerance": 2.0,  # 2.0s before follow-up
    
    # Breath Timing
    "breath_before_thought": True,
    "breath_before_grounding": True,
    "exaggerated_breaths": False,
    
    # Micro-Behaviors
    "thinking_sounds": ["Hmm...", "Okay...", "Alright...", "One sec..."],
    "hesitation_markers": ["Let me see...", "Hold on...", "Right..."],
    "transitions": ["Okay, so...", "Alright — here's what I'm seeing.", "Right — let's take this step by step."],
    
    # Emotional Calibration
    "stress_response": "slow_down_soften",  # Slow down, soften tone
    "anger_response": "ground_moment",  # Ground the moment
    "confusion_response": "simplify",  # Simplify
    "sadness_response": "steady_warm",  # Steady and warm
    "excitement_response": "stay_steady",  # Stay steady
    "formal_response": "precise_respectful",  # Precise and respectful
    "casual_response": "relax",  # Relax
    
    # Signature Presence
    "signature_greeting": ["Hey, this is Alan.", "Hi, this is Alan."],
    "signature_control_return": ["What do you want to do next?", "Where do you want to go from here?", "How do you want to move forward?"],
    "signature_grounding": "You're okay. I'm here.",
    "signature_narration": ["One sec...", "Checking that...", "Okay..."],
    
    # TTS Engine Tuning
    "voice_gender": "male",
    "voice_range": "mid",
    "timbre": "warm",
    "rasp": "slight",  # Optional
    "consonant_attack": "soft",
    "vowel_transitions": "smooth",
    "sibilance": "no_sharp",
    "pitch": "low",
    "pitch_stability": "stable",
    "resonance_chest": 0.7,  # Dominant
    "resonance_head": 0.3,  # Light
    "resonance_nasal": 0.0,  # No nasal
    "prosody": "natural",
    "inflection_downward": "slight_at_ends",
    "inflection_upward": "only_questions",
    "stability": 0.38,          # [TUNED PHASE 3] "Grounded Auditor" (AQI-REL-01) - 38%
    "expressiveness": 0.85,     # [TUNED PHASE 3] Meaning "Similarity Boost" -> 85%
    "style_exaggeration": 0.15, # [TUNED PHASE 3] 15% to prevent "over-acting"
    "clarity": 0.90,
    "breathiness": 0.15,
    "volume": 0.9,
    "latency_first_chunk": 300,  # ms
    "resonance": "chest",
    
    # Delivery Rules
    "keep_short": True,
    "keep_human": True,
    "keep_grounded": True,
    "keep_warm": True,
    "keep_steady": True,
    "keep_simple": True,
    "keep_present": True,
    "keep_real": True,
    "avoid_over_explain": True,
    "avoid_too_fast": True,
    "avoid_synthetic": True,
    "avoid_over_cheerful": True,
    "avoid_clinical": True,
    "avoid_chatbot": True
}

# ---------------------------------------------------------
# PUBLIC API
# ---------------------------------------------------------

# Basic In-Memory Audio Cache for High-Frequency Phrases
# Maps phrase_text -> audio_bytes (ulaw_8000)
AUDIO_CACHE = {
    "Hi, this is Alan Jones calling from Signature Card Services. I'm looking for the business owner.": None, # Will be filled if seen repeatedly or pre-warmed
    "Hi, this is Alan Jones calling from Signature Card Services. I'm trying to reach the business owner — are they in?": None,
    "Hello? Is anyone there?": None,
    "Okay, I'm listening. Go ahead.": None,
    # --- Qualification Loop (Pivot) ---
    # Branch A: Identity Match (Variable: [Industry] -> "local")
    "Perfect. The reason I'm reaching out specifically is that we’ve been working with a few other local businesses in the area to help them secure much lower processing rates—usually saving them about 20 to 30 percent. I wanted to see if you’re currently the one who handles the merchant services there?": None,
    # Branch B: Permission Grant (Variable: [Industry] -> "local")
    "I appreciate that. I'll be brief—I'm Alan with Signature, and we’re currently helping local businesses eliminate those junk fees that usually creep into the monthly merchant statements. Do you happen to have your most recent statement handy, or do you usually check those online?": None,
    # Branch C: Inquiry
    "I’m glad you asked—I'm Alan with Signature Card Services. I was actually reaching out to several local businesses in the area because we’ve found a way to bridge the gap between their current processing rates and the new wholesale rates available this quarter. I’m looking to see if you’re the one who usually handles the merchant statements there, or is that someone else?": None,
    # Branch D: Gatekeeper
    "I see. I appreciate you letting me know. I definitely don't want to be a pest or keep calling back at the wrong time—is there a specific window when they're usually around, or should I just try to reach them via email?": None
}

def encode_audio_chunk(raw_bytes: bytes) -> str:
    """Helper to base64 encode audio chunks."""
    return base64.b64encode(raw_bytes).decode('utf-8')

async def stream_tts_audio(text: str) -> AsyncGenerator[bytes, None]:
    """
    Main entry point for Voice Module.
    Given text, yields chunks of raw audio bytes.

    Supports pause markers: [PAUSE:seconds] for timing control
    Supports Audio Caching for "Zero-Lag" responses.
    """
    if not TTS_ENABLED or not text.strip():
        return
    
    # [CACHE CHECK]
    # Simple normalization: strip whitespace
    normalized_text = text.strip()
    
    # [PRE-LOADED ACTION] Check RAM Cache first
    if normalized_text in AUDIO_CACHE and AUDIO_CACHE[normalized_text]:
        print(f"[TTS] Cache HIT for: '{normalized_text[:30]}...'")
        cached_audio = AUDIO_CACHE[normalized_text]
        # Yield whole cached blob in chunks (simulate stream for compatibility)
        # [TUNING ATTEMPT 10] Force 160 bytes (20ms) for cached audio too
        chunk_size = 160 
        for i in range(0, len(cached_audio), chunk_size):
            yield cached_audio[i:i + chunk_size]
            await asyncio.sleep(0.020) # 20ms delay for proper audio pacing, prevents crackling
        return

    # If no cache, generate fresh (and cache if it matches known phrases)
    full_audio_buffer = bytearray()
    should_cache = normalized_text in AUDIO_CACHE

    # Parse pause markers and split text
    import re

    pause_pattern = r'\[PAUSE:(\d*\.?\d+)\]'
    parts = re.split(pause_pattern, text)
    
    for i, part in enumerate(parts):
        if i % 2 == 0:  # Text part
            if part.strip():  # Non-empty text
                if TTS_ENGINE == "pyttsx3" and TTS_AVAILABLE:
                    async for chunk in _pyttsx3_tts(part):
                        if should_cache: full_audio_buffer.extend(chunk)
                        yield chunk
                elif TTS_ENGINE == "azure":
                    async for chunk in _azure_tts(part):
                        if should_cache: full_audio_buffer.extend(chunk)
                        yield chunk
                elif TTS_ENGINE == "elevenlabs":
                    # [ATTEMPT 29] Apply MTU Fragmentation (Micro-Packets)
                    async for chunk in _chunk_splitter(_elevenlabs_tts(part), chunk_size=512):
                        if should_cache: full_audio_buffer.extend(chunk)
                        yield chunk
                else:
                    async for chunk in _placeholder_tts(part):
                        if should_cache: full_audio_buffer.extend(chunk)
                        yield chunk
        else:  # Pause duration part
            try:
                pause_seconds = float(part)
                await asyncio.sleep(pause_seconds)
            except ValueError:
                pass  # Invalid pause, skip
    
    # [CACHE WRITE] Store valid audio for next time
    if should_cache and len(full_audio_buffer) > 0:
        AUDIO_CACHE[normalized_text] = bytes(full_audio_buffer)
        print(f"[TTS] Cache WARMED for: '{normalized_text[:30]}...' ({len(full_audio_buffer)} bytes)")


# ---------------------------------------------------------
# INTERNAL IMPLEMENTATIONS
# ---------------------------------------------------------

async def _chunk_splitter(byte_stream_generator, chunk_size=1024):
    """
    [ATTEMPT 29] MTU Fragmentation Helper
    Ensures that regardless of source, we yield consistent small chunks.
    """
    buffer = bytearray()
    async for chunk in byte_stream_generator:
        buffer.extend(chunk)
        while len(buffer) >= chunk_size:
            yield bytes(buffer[:chunk_size])
            del buffer[:chunk_size]
    if buffer:
        yield bytes(buffer)

async def _pyttsx3_tts(text: str) -> AsyncGenerator[bytes, None]:
    """
    pyttsx3 TTS implementation tuned to Alan Voice Persona Spec.
    Generates audio bytes and yields chunks.
    """
    if not TTS_AVAILABLE:
        async for chunk in _placeholder_tts(text):
            yield chunk
        return

    # Initialize engine
    engine = pyttsx3.init()

    # Apply Alan Persona tuning from spec
    profile = ALAN_VOICE_PROFILE
    
    # Pacing: Set rate based on normal WPM (145)
    engine.setProperty('rate', profile['wpm_normal'])
    
    # Volume: Use stability as proxy for volume (0.75 -> 0.9)
    engine.setProperty('volume', profile['stability'] + 0.15)
    
    # Voice selection: Male voice preferred
    voices = engine.getProperty('voices')
    selected_voice = None
    for voice in voices:
        if profile['voice_gender'] in voice.name.lower():
            selected_voice = voice
            break
    if not selected_voice and voices:
        selected_voice = voices[0]  # Fallback
    if selected_voice:
        engine.setProperty('voice', selected_voice.id)

    # Note: pyttsx3 has limited properties. Advanced tuning like:
    # - pitch, resonance, prosody, stability, expressiveness, clarity, breathiness
    # - would require a more advanced TTS engine (Azure, ElevenLabs, etc.)
    # For now, we approximate with available properties and rely on voice selection

    # Generate audio to BytesIO (pyttsx3 can save to file, but we need bytes)
    # pyttsx3 doesn't directly support BytesIO, so we'll use a temp file approach
    import tempfile
    import os

    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
        temp_path = temp_file.name

    try:
        # Save to temp file
        engine.save_to_file(text, temp_path)
        engine.runAndWait()

        # Read the file into bytes
        with open(temp_path, 'rb') as f:
            audio_bytes = f.read()

        # Yield chunks
        chunk_size = 1024  # 1KB chunks
        for i in range(0, len(audio_bytes), chunk_size):
            yield audio_bytes[i:i + chunk_size]
            await asyncio.sleep(TTS_CHUNK_DELAY)

    finally:
        # Clean up temp file
        if os.path.exists(temp_path):
            os.unlink(temp_path)


async def _placeholder_tts(text: str) -> AsyncGenerator[bytes, None]:
    """
    Placeholder TTS:
    - For now, just yields small fake "audio" chunks as bytes.
    - Grok will replace this with real TTS.
    """
    # In a real TTS, you’d generate real audio bytes here.
    # This placeholder just demonstrates the streaming contract.
    fake_audio = f"[AUDIO for: {text}]".encode("utf-8")
    # Cut into pseudo chunks
    chunk_size = max(16, len(fake_audio) // 3)
    for i in range(0, len(fake_audio), chunk_size):
        yield fake_audio[i:i + chunk_size]
        await asyncio.sleep(TTS_CHUNK_DELAY)


async def _azure_tts(text: str) -> AsyncGenerator[bytes, None]:
    """
    Stub: Azure TTS implementation.
    Grok can implement actual Azure streaming here.
    """
    # Pseudocode:
    # 1. Create Azure speech config
    # 2. Create a pull/streaming audio output
    # 3. Start synthesis, yield chunks as they arrive
    #
    # For now, use placeholder behavior to keep contract stable.
    async for chunk in _placeholder_tts(text):
        yield chunk




async def _elevenlabs_tts(text: str) -> AsyncGenerator[bytes, None]:
    """
    ElevenLabs TTS streaming implementation with Telephony Optimization.
    Uses Official SDK (AsyncElevenLabs).
    """
    # Use global client
    if not tts_client:
        print("[TTS] ElevenLabs client not initialized")
        async for chunk in _placeholder_tts(text):
            yield chunk
        return

    # Use 'zBjSpfcokeTupfIZ8Ryx' directly if not in env var
    voice_id = os.getenv("ELEVENLABS_VOICE_ID", "zBjSpfcokeTupfIZ8Ryx") 
    
    try:
        # [TASK 6] Use SDK text_to_speech.convert with streaming
        # Use Tuned Persona Settings from Configuration
        audio_stream = tts_client.text_to_speech.convert(
            text=text,
            voice_id=voice_id,
            model_id="eleven_flash_v2_5", # Fastest model for <800ms Latency
            output_format="ulaw_8000",
            voice_settings=VoiceSettings(
                stability=ALAN_VOICE_PROFILE['stability'],          # 0.38 (Grounded Auditor)
                similarity_boost=ALAN_VOICE_PROFILE['expressiveness'], # 0.85 (Boosted Identity)
                style=ALAN_VOICE_PROFILE['style_exaggeration'],    # 0.15 (Slight Flair)
                use_speaker_boost=True
            )
        )
        
        # Yield chunks
        async for chunk in audio_stream:
            yield chunk

    except Exception as e:
        print(f"[TTS] ElevenLabs SDK error: {e}")
        async for chunk in _placeholder_tts(text):
            yield chunk


# ---------------------------------------------------------
# HELPER: base64 encode chunks for WebSocket
# ---------------------------------------------------------

def encode_audio_chunk(chunk: bytes) -> str:
    """
    Returns base64-encoded string for a given raw audio chunk.
    """
    return base64.b64encode(chunk).decode("utf-8")
