"""
AQI Voice Module (v1.0)
Author: Copilot (for TimmyJ)
Purpose:
    - Add real-time voice capability to AQI/Alan
    - 100% isolated from AQI core logic
    - Safe, reversible, future-proof
    - Supports streaming STT and streaming TTS
    - Provides a stable interface for Grok or any backend dev

This module NEVER touches:
    - Alan’s memory
    - Alan’s governance logic
    - Alan’s identity
    - AQI’s relational kernel

It only handles:
    - Audio in
    - Audio out
    - Session management
    - Streaming pipelines
"""

import asyncio
import uuid
import time
import logging
import base64
import audioop
from typing import Callable, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import Response

import aqi_stt_engine
import aqi_tts_engine

# Voice governance imports
from aqi_voice_governance import get_voice_governor, core_heartbeat, SpeakerRole, governed_speech, governed_speech_sync
from aqi_voice_negproof_tests import get_neg_proof_suite

# ---------------------------------------------------------
# LOGGING
# ---------------------------------------------------------
logger = logging.getLogger("AQI_VOICE")
logger.setLevel(logging.INFO)

# ---------------------------------------------------------
# CONFIG FLAGS (safe defaults)
# ---------------------------------------------------------

VOICE_REALTIME_ENABLED = True
VOICE_STREAMING_STT_ENABLED = True
VOICE_STREAMING_TTS_ENABLED = True

# ---------------------------------------------------------
# INTERNAL SESSION STORE
# ---------------------------------------------------------

# [CLEAN PIPES] RAM Greeting DISABLED - Fresh audio only
# Keep variable defined to prevent NameError, but always empty (no cached audio)
GLOBAL_RAM_GREETING = []  # PERMANENTLY EMPTY - Clean pipes only
# [ATTEMPT 49] GLOBAL AUDIO CACHE (The Bypass)
GLOBAL_AUDIO_CACHE = {}

class VoiceSession:

    """
    Represents a single real-time voice session.
    Each session is isolated and cannot affect AQI core.
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.websocket: Optional[WebSocket] = None
        self.partial_transcript = ""
        self.active = True
        self.last_message_time = time.time()
        self.silence_follow_up_sent = False
        self.metadata = {}
        self.current_tts_task = None # Track active TTS for cancellation
        
        # [ATTEMPT 45] STATE-LOCK
        self.greeting_completed = False
        self.turns_since_greeting = 0

        # [ATTEMPT 55] DUAL-TRACK SUBSTRATE & INTRO SHIELD
        self.call_start_time = time.time()
        self.is_shadow_primed = False
        self.active_track = "PRIMARY"  # PRIMARY (Live AI) or SHADOW (RAM Cache)
        self.track_volumes = {"PRIMARY": 1.0, "SHADOW": 0.0}
        self.INTRO_SHIELD_DURATION = 3.0 # SEO-01-26: Greeting Shield (3.0s)

        # [PHASE 1] TURN-TAKING GOVERNOR FLAGS
        self.agent_speaking = False
        self.user_speaking = False
        self.awaiting_user = False
        self.closing_state = False
        
        # [PHASE 5/8] GOVERNANCE LOCKS
        self.response_locked = False
        self.last_response_hash = "" # Drift Guard
        self.consecutive_drifts = 0
        self.closing_spoken = False # [PHASE 7]
        self.last_user_speech_time = 0.0 # [PHASE 3]
        self.speech_start_time = 0.0 # [PHASE 9] Echo Shield

    def close(self):
        self.active = False
        if self.current_tts_task:
            self.current_tts_task.cancel()
        # Clean buffer
        self.audio_buffer = []

    # [ATTEMPT 13] Audio Buffer for Pre-Generation
    def append_buffer(self, chunk):
        if not hasattr(self, "audio_buffer"):
            self.audio_buffer = []
        self.audio_buffer.append(chunk)

voice_sessions = {}  # session_id → VoiceSession

# ---------------------------------------------------------
# PUBLIC INTERFACE (THIS IS WHAT ALAN USES)
# ---------------------------------------------------------

async def preload_text_to_cache(key: str, text: str):
    """
    [ATTEMPT 49] Pre-generate specific audio clips into Named Cache.
    """
    if not VOICE_REALTIME_ENABLED: return
    logger.info(f"[CACHE] Generating '{key}': '{text}'")
    
    buffer = []
    try:
        async for audio_chunk in aqi_tts_engine.stream_tts_audio(text):
            b64_audio = aqi_tts_engine.encode_audio_chunk(audio_chunk)
            payload = {"type": "tts_audio_chunk", "data": b64_audio}
            buffer.append(payload)
        
        GLOBAL_AUDIO_CACHE[key] = buffer
        logger.info(f"[CACHE] '{key}' populated with {len(buffer)} chunks.")
    except Exception as e:
        logger.error(f"[CACHE] Failed to populate '{key}': {e}")

async def play_from_cache(key: str, session_id: str) -> bool:
    """
    [ATTEMPT 49] Instant Replay from Cache (Bypass Logic)
    Returns True if played, False if missing.
    """
    if key not in GLOBAL_AUDIO_CACHE:
        logger.warning(f"[CACHE] Miss: '{key}' not found.")
        return False
    
    session = voice_sessions.get(session_id)
    if not session or not session.websocket: return False
    
    # [Barge-In Safety]
    if session.current_tts_task and session.current_tts_task != asyncio.current_task():
        session.current_tts_task.cancel()
        await asyncio.sleep(0.01)
    session.current_tts_task = asyncio.current_task()

    logger.info(f"[BYPASS] Playing Cached Audio: '{key}' ({len(GLOBAL_AUDIO_CACHE[key])} chunks)")
    
    try:
        for payload in GLOBAL_AUDIO_CACHE[key]:
            if not session.active: break
            if asyncio.iscoroutinefunction(session.websocket.send_json):
                await session.websocket.send_json(payload)
            else:
                session.websocket.send_json(payload)
            await asyncio.sleep(0.02) # Pacer
        return True
    except Exception as e:
        logger.error(f"[BYPASS] Playback Failed: {e}")
        return False
    finally:
        session.current_tts_task = None

async def preload_text_to_voice(text: str, session_id: str):
    """
    [ATTEMPT 13] Generate audio immediately and store in memory.
    """
    if not VOICE_REALTIME_ENABLED: return
    
    # [CLEAN PIPES] RAM Warmup DISABLED - No cached greeting generation
    # No RAM greeting cache - fresh TTS for every call ensures clean pipes
    if session_id == "GLOBAL_WARMUP":
        logger.info(f"[CLEAN PIPES] RAM warmup disabled - Fresh TTS only")
        return  # Skip RAM cache generation

    session = voice_sessions.get(session_id)
    if not session: return

    logger.info(f"[PRELOAD] Generating greeting: '{text}' for Session {session_id}")
    
    # We use a separate task or just generate here. 
    # Since we want it ready, we'll await the generation loop.
    try:
        count = 0
        async for audio_chunk in aqi_tts_engine.stream_tts_audio(text):
            if not session.active: break
            b64_audio = aqi_tts_engine.encode_audio_chunk(audio_chunk)
            payload = {
                "type": "tts_audio_chunk",
                "format": "audio/pcm", 
                "data": b64_audio
            }
            session.append_buffer(payload)
            
            # Record audio path for negative proof testing
            get_neg_proof_suite().record_audio_path(
                source="aqi_voice_module",
                destination="twilio", 
                audio_size=len(b64_audio),
                session_id=session_id
            )
            
            count += 1
        logger.info(f"[PRELOAD] Buffered {count} chunks for Session {session_id}")
    except Exception as e:
        logger.error(f"[PRELOAD] Failed: {e}")


def cancel_speech(session_id: str):
    """
    Stops the current TTS output for a session immediately.
    Used for Barge-In.
    """
    session = voice_sessions.get(session_id)
    if session:
        # [PHASE 6] FORCE FLAGS ON INTERRUPT
        session.agent_speaking = False
        session.awaiting_user = False # If cancelled, we likely heard user, or just stopped.
        
        if session.current_tts_task:
            session.current_tts_task.cancel()
            logger.info(f"Speech cancelled for session {session_id}")

async def send_hybrid_greeting(short_text: str, long_text: str, session_id: str, force: bool = False):
    """
    [ATTEMPT 19] Raw Reflex (RAM Dump)
    Ignores arguments if GLOBAL_RAM_GREETING is populated.
    Dumps the memory buffer directly to the socket.
    """
    if not VOICE_REALTIME_ENABLED: return
    session = voice_sessions.get(session_id)
    if not session or not session.websocket: return

    # [Barge-In Safety]
    if session.current_tts_task and session.current_tts_task != asyncio.current_task():
        session.current_tts_task.cancel()
        await asyncio.sleep(0.01)
    
    # [PURIFIED SOURCE] Single-Shot Flag Check
    # If the greeting has already been sent for this session, DO NOT send it again.
    # [FIX] Added 'force' override for the Ignition system which locks BEFORE calling.
    if getattr(session, "greeting_fully_sent", False) and not force:
        logger.warning(f"[PURIFIED SOURCE] Greeting Blocked. Already Sent for {session_id}")
        return

    session.current_tts_task = asyncio.current_task()

    # [PURIFIED SOURCE] Buffer Drain
    # Ensure no lingering packets from previous attempts are in the queue.
    if hasattr(session, "audio_buffer"):
        if session.audio_buffer:
             logger.warning(f"[PURIFIED SOURCE] Draining {len(session.audio_buffer)} stale chunks from session buffer.")
             session.audio_buffer = []

    # [FIX] STATE-LOCK ENGAGED (Moved Up)
    # Once we start the hybrid greeting, the intro is officially "Done".
    session.greeting_completed = True
    session.turns_since_greeting = 0
    session.greeting_fully_sent = True # [PURIFIED SOURCE] Lock the flag immediately

    # [SHORT-CIRCUIT FIXED] Check Session Buffer (Pre-Flight Result)
    # If the Pre-Flight generator finished, the audio is already here.
    if hasattr(session, "audio_buffer") and session.audio_buffer:
        logger.info(f"[SHORT-CIRCUIT] Dumping {len(session.audio_buffer)} buffered chunks to socket.")
        try:
            for payload in session.audio_buffer:
                if not session.active: break
                if asyncio.iscoroutinefunction(session.websocket.send_json):
                    await session.websocket.send_json(payload)
                else:
                    session.websocket.send_json(payload)
                await asyncio.sleep(0.01) # Low jitter spacer
            
            # Clear and Exit
            session.audio_buffer = []
            logger.info("[SHORT-CIRCUIT] Complete. Bypassed TTS generation.")
            return
        except Exception as e:
            logger.error(f"[SHORT-CIRCUIT] Failed: {e}")

    # [CLEAN PIPES] RAM DOOR KICK DISABLED - No cached audio residue
    # Fresh TTS generation only - prevents duplicate greetings and stale audio
    ram_dumped = False
    
    # [CLEAN PIPES] HYBRID DISABLED - Direct TTS only, no cached audio
    # Professional greeting comes from WebSocket in control_api.py
    # This hybrid system caused "Hello?" duplication - now disabled
    logger.info(f"[CLEAN PIPES] Hybrid system disabled - Direct TTS: '{long_text}'")

    # Stream ONLY the full text directly (no short/long split)
    try:
        async for audio_chunk in aqi_tts_engine.stream_tts_audio(long_text):
            if not session.active: break
            b64 = aqi_tts_engine.encode_audio_chunk(audio_chunk)
            payload = {"type": "tts_audio_chunk", "data": b64}
            if asyncio.iscoroutinefunction(session.websocket.send_json):
                await session.websocket.send_json(payload)
            else:
                session.websocket.send_json(payload)
                
    except asyncio.CancelledError:
        logger.info(f"[HYBRID] Cancelled for {session_id}")
        prefetch_task.cancel()
        if asyncio.iscoroutinefunction(session.websocket.send_json):
            await session.websocket.send_json({"type": "clear_buffer"})
    finally:
        session.current_tts_task = None
        prefetch_task.cancel()


async def send_text_to_voice(text: str, session_id: str):
    """
    Alan calls this to speak with voice governance enforcement.
    """
    if not VOICE_REALTIME_ENABLED:
        return

    # GOVERNANCE CHECK: Request permission to speak
    try:
        permission_granted = governed_speech_sync(
            text=text,
            caller_id="aqi_voice_module",
            role=SpeakerRole.CONVERSATIONAL_CORE
        )
        if not permission_granted:
            logger.warning(f"[GOVERNANCE] Speech denied for session {session_id}")
            return
    except Exception as e:
        logger.error(f"[GOVERNANCE] Speech request failed: {e}")
        return

    # Record for negative proof testing
    get_neg_proof_suite().record_tts_call(text, session_id)
    
    # Signal that core is healthy
    core_heartbeat()

    session = voice_sessions.get(session_id)
    if not session:
        logger.warning(f"[TTS] No session found for {session_id}")
        return
        
    # Stream stability check to prevent service crashes
    if not session.websocket:
        logger.error(f"[TTS] ❌ No websocket for session {session_id}")
        return
        
    # Check if websocket is still connected
    try:
        if hasattr(session.websocket, 'client_state') and session.websocket.client_state.name != 'OPEN':
            logger.error(f"[TTS] ❌ WebSocket not in OPEN state for session {session_id}")
            return
    except Exception as ws_check_error:
        logger.error(f"[TTS] ❌ WebSocket state check failed: {ws_check_error}")
        return
    
    # -------------------------------------------------------------
    # [PHASE 4-8] TURN-TAKING GOVERNOR ENFORCEMENT
    # -------------------------------------------------------------
    
    # [PHASE 7] CLOSING STATE GUARD
    if session.closing_state:
        if session.closing_spoken:
            logger.info(f"[GOVERNOR BLOCKED] Closing State Active. Dropping: '{text}'")
            return
        else:
            session.closing_spoken = True
            logger.info(f"[GOVERNOR] Allowing FINAL response (Closing State).")
    
    # [PHASE 8] DRIFT GUARD (Duplicate Prevention)
    norm_text = text.strip().lower()
    if norm_text == session.last_response_hash:
        logger.warning(f"[GOVERNOR BLOCKED] Drift Guard (Duplicate): '{text}'")
        return
    session.last_response_hash = norm_text

    # [PHASE 4] THE GOLDEN RULE
    if session.agent_speaking:
        logger.warning(f"[GOVERNOR BLOCKED] Overlap (Agent Speaking): '{text}'")
        return
    
    if session.user_speaking:
        # [PHASE 3] SILENCE WINDOW CHECK
        # If user hasn't spoken for 0.5s (Fast Commit), assume they are done.
        silence_window = 0.5
        if time.time() - session.last_user_speech_time > silence_window:
             session.user_speaking = False
             logger.info(f"[GOVERNOR] Auto-cleared 'user_speaking' flag after {silence_window}s silence.")
        else:
             logger.warning(f"[GOVERNOR BLOCKED] Interruption (User Speaking): '{text}'")
             return
        
    if session.awaiting_user:
        logger.warning(f"[GOVERNOR BLOCKED] Runaway (Awaiting User): '{text}'")
        return

    # [PHASE 5] ONE-RESPONSE LOCK
    if session.response_locked:
        logger.warning(f"[GOVERNOR BLOCKED] Locked (One-Per-Turn): '{text}'")
        return
        
    # LOCK & ENGAGE
    session.response_locked = True
    session.agent_speaking = True
    session.awaiting_user = False
    session.speech_start_time = time.time() # [PHASE 9] Echo Shield: Start Timer
    
    # -------------------------------------------------------------

    # [Barge-In Safety] Cancel any existing speech before starting new
    if session.current_tts_task and session.current_tts_task != asyncio.current_task():
        session.current_tts_task.cancel()
        await asyncio.sleep(0.01) # Yield to let cancellation propagate

    # Log what Alan is saying
    logger.info(f"Alan said: {text}")
    tts_start_time = time.time() # [Latency Logger] Start Timer
    first_chunk_sent = False

    # Optional: send text with error handling
    try:
        payload_text = { "type": "tts_text", "text": text.strip() }
        if asyncio.iscoroutinefunction(session.websocket.send_json):
             await session.websocket.send_json(payload_text)
        else:
             session.websocket.send_json(payload_text)
    except Exception as text_send_error:
        logger.error(f"[TTS] ❌ Failed to send text payload: {text_send_error}")
        # Don't crash service - continue with TTS
        
    # [ATTEMPT 13] Check Buffer First with error handling
    if hasattr(session, "audio_buffer") and session.audio_buffer:
        logger.info(f"[BUFFER] Releasing {len(session.audio_buffer)} preloaded chunks for {session_id}")
        try:
            for payload in session.audio_buffer:
                if asyncio.iscoroutinefunction(session.websocket.send_json):
                    await session.websocket.send_json(payload)
                else:
                    session.websocket.send_json(payload)
        except Exception as buffer_send_error:
            logger.error(f"[TTS] ❌ Failed to send buffer chunks: {buffer_send_error}")
            # Continue with live TTS generation
            
        # Clear buffer after sending ?? Or keep it? 
        # Usually one-shot.
        session.audio_buffer = [] 
        
        # [PHASE 2] GOVERNOR RESET (Buffered Path)
        session.agent_speaking = False
        session.awaiting_user = True
        return

    # Stream audio via TTS engine
    session.current_tts_task = asyncio.current_task()
    
    try:
        async for audio_chunk in aqi_tts_engine.stream_tts_audio(text):
            if not session.active: break 
            
            # [Latency Logger] Measure TTFB
            if not first_chunk_sent:
                ttfb_ms = (time.time() - tts_start_time) * 1000
                logger.info(f"[LATENCY] TTFB for session {session_id}: {ttfb_ms:.2f}ms")
                
                # [WATCHDOG] Latency Alert
                if ttfb_ms > 1200:
                    logger.warning(f"[WATCHDOG] HIGH LATENCY ALERT: {ttfb_ms:.2f}ms exceeds 1200ms threshold.")
                
                first_chunk_sent = True

            b64_audio = aqi_tts_engine.encode_audio_chunk(audio_chunk)
            payload = {
                "type": "tts_audio_chunk",
                "format": "audio/pcm", 
                "data": b64_audio
            }
            
            # Send audio chunk with error handling to prevent crashes
            try:
                if asyncio.iscoroutinefunction(session.websocket.send_json):
                    await session.websocket.send_json(payload)
                else:
                    session.websocket.send_json(payload)
            except Exception as chunk_send_error:
                logger.error(f"[TTS] ❌ Failed to send audio chunk: {chunk_send_error}")
                # Break the loop to prevent further errors
                break
            else:
                session.websocket.send_json(payload)
    except asyncio.CancelledError:
        logger.info(f"TTS streaming cancelled for session {session_id} (Barge-in)")
        # Send Clear Buffer signal to Bridge with error handling
        try:
            if asyncio.iscoroutinefunction(session.websocket.send_json):
                await session.websocket.send_json({"type": "clear_buffer"})
            else:
                session.websocket.send_json({"type": "clear_buffer"})
        except Exception as clear_error:
            logger.error(f"[TTS] ❌ Failed to send clear buffer: {clear_error}")
            # Continue - don't crash service
    finally:
        # [FIX] Send MARK to ensure bridge flushes buffer
        if session.active and session.websocket:
             try:
                 mark_payload = {"type": "mark", "name": "end_of_turn"}
                 if asyncio.iscoroutinefunction(session.websocket.send_json):
                     await session.websocket.send_json(mark_payload)
                 else:
                     session.websocket.send_json(mark_payload)
             except Exception:
                 pass

        # [PHASE 2] GOVERNOR RESET (Stream Path)
        session.agent_speaking = False
        session.awaiting_user = True
        session.current_tts_task = None


def register_stt_callback(callback: Callable[[str, str], None]):
    """
    Alan registers here. We forward the callback into the STT engine.
    """
    aqi_stt_engine.register_stt_callback(callback)


stt_callback = None  # Will be set by AQI core
connect_callback: Optional[Callable[[str], None]] = None
session_start_callback: Optional[Callable[[str], None]] = None # [ATTEMPT 13]

def register_connect_callback(callback: Callable[[str], None]):
    """
    Register a callback to be fired when a voice session connects (VAD).
    """
    global connect_callback
    connect_callback = callback

def register_session_start_callback(callback: Callable[[str], None]):
    """
    [ATTEMPT 13] Fire when session is created (Pre-Flight).
    """
    global session_start_callback
    session_start_callback = callback


# ---------------------------------------------------------
# FASTAPI ROUTER (SAFE TO MOUNT ANYWHERE)
# ---------------------------------------------------------

router = APIRouter()

@router.get("/test-simple")
async def test_simple_route():
    """
    Simple test route to isolate request handling issues
    """
    return {"status": "ok", "message": "Simple route working"}

@router.post("/twilio/voice")
async def twilio_voice_webhook(request: Request):
    """
    Twilio voice webhook endpoint - entry point for all calls
    Returns TwiML to establish WebSocket connection for real-time audio
    """
    try:
        # Parse Twilio webhook data
        form_data = await request.form()
        call_sid = form_data.get('CallSid', 'unknown')
        from_number = form_data.get('From', 'unknown')
        to_number = form_data.get('To', 'unknown')
        
        logger.info(f"[TWILIO] Incoming call: {call_sid} from {from_number} to {to_number}")
        
        # Create new voice session for this call
        session_id = str(uuid.uuid4())
        session = VoiceSession(session_id)
        session.metadata = {
            'call_sid': call_sid,
            'from': from_number,
            'to': to_number,
            'call_type': 'twilio_inbound'
        }
        voice_sessions[session_id] = session
        
        # Generate TwiML response to connect Twilio to our WebSocket
        # This tells Twilio to stream audio to our WebSocket endpoint
        tunnel_url = "https://hierodulic-unfacaded-gemma.ngrok-free.dev"
        twiml_response = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Connect>
        <Stream url="{tunnel_url.replace('https://', 'wss://')}/voice-session/ws/{session_id}" />
    </Connect>
    <Say>Please wait while we connect you to Alan.</Say>
</Response>"""
        
        return Response(content=twiml_response, media_type="application/xml")
        
    except Exception as e:
        logger.error(f"[TWILIO] Webhook error: {e}")
        # Return basic TwiML response if error
        error_response = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say>I'm sorry, there was an error connecting your call. Please try again later.</Say>
    <Hangup/>
</Response>"""
        return Response(content=error_response, media_type="application/xml")

@router.post("/voice-session/start")
async def start_voice_session(request: Request):
    """
    Creates a new voice session.
    Returns a session_id for the client to open a WebSocket.
    """
    try:
        data = await request.json()
    except:
        data = {}

    session_id = str(uuid.uuid4())
    session = VoiceSession(session_id)
    session.metadata = data
    
    voice_sessions[session_id] = session
    aqi_stt_engine.create_stt_session(session_id)
    
    # [ATTEMPT 19] - PRE-LOAD RAM GREETING ON STARTUP IF EMPTY
    # We hijack the first session start to ensure our RAM buffer is ready.
    # Text: "Hi Tim, this is Alan..."
    global GLOBAL_RAM_GREETING
    if not GLOBAL_RAM_GREETING:
        # Define the target greeting
        # [ATTEMPT 42] SEQUENTIAL BUFFER (Local "Hello" Only)
        target_text = "Hello, this is Alan."
        logger.info(f"[ATTEMPT 42] initializing RAM buffer with: '{target_text}'")
        
        async def populate_ram():
            try:
                count = 0
                async for audio_chunk in aqi_tts_engine.stream_tts_audio(target_text):
                    b64 = aqi_tts_engine.encode_audio_chunk(audio_chunk)
                    payload = {"type": "tts_audio_chunk", "data": b64}
                    GLOBAL_RAM_GREETING.append(payload)
                    count += 1
                logger.info(f"[ATTEMPT 19] RAM Buffer Populated. Size: {count} chunks.")
            except Exception as e:
                logger.error(f"[ATTEMPT 19] Failed to populate RAM: {e}")

        # Run immediately (awaiting to ensure it's ready for *this* call if possible, or background)
        # Since this is an HTTP endpoint, we shouldn't block too long, but generation is fast.
        # Let's fire and forget, but hopefully it finishes before the WebSocket connects (which takes >200ms)
        asyncio.create_task(populate_ram())

    # [ATTEMPT 13] Trigger Pre-Flight Callback to start TTS Generation
    if session_start_callback:
        # Run in background to not block response
        asyncio.create_task(session_start_callback(session_id))
        
    return {"session_id": session_id}


@router.get("/voice-session/{session_id}/metadata")
async def get_session_metadata(session_id: str):
    session = voice_sessions.get(session_id)
    if session:
        return session.metadata
    return {}



@router.websocket("/voice-session/ws/{session_id}")
async def voice_session_ws(websocket: WebSocket, session_id: str):
    """
    Main WebSocket for real-time audio/text streaming.
    """
    await websocket.accept()

    session = voice_sessions.get(session_id)
    if not session:
        await websocket.close()
        return

    session.websocket = websocket
    
    # [IGNITION] WAITING FOR TRIGGER (VAD or TIMEOUT)
    # We do NOT fire the connect callback immediately anymore.
    # We wait for the Bridge to send a 'trigger_opener' event.
    logger.info(f"[IGNITION] WebSocket Connected for Session {session_id}. Waiting for VAD Trigger or Timeout.")

    try:
        while session.active:
            # Check for silence follow-up (Removed generic prompt to let Agent logic handle it)
            # if (time.time() - session.last_message_time > 2.0 ...
            
            # Simple keepalive or silence check can go here if needed
            
            try:
                message = await websocket.receive_json()
            except (StopAsyncIteration, RuntimeError, Exception) as e:
                # [Graceful Exit] Bridge closed or client disconnected
                logger.info(f"[SHUTDOWN] WebSocket Stream Ended for {session_id} ({e.__class__.__name__})")
                break

            session.last_message_time = time.time()
            session.silence_follow_up_sent = False

            msg_type = message.get("type")

            if msg_type == "trigger_opener":
                reason = message.get("reason", "vad") # Default to 'vad' if missing
                
                # [PURIFIED SOURCE] SYNCHRONOUS LOCK
                # We check AND set the flag here, in the main thread/loop.
                # This prevents a second task from ever being spun up, killing the Race Condition dead.
                if getattr(session, "greeting_fully_sent", False):
                    logger.warning(f"[IGNITION] Duplicate Trigger Blocked by Synchronous Lock. Reason: {reason}")
                    continue
                session.greeting_fully_sent = True

                # [POUNCE] The Bridge detected "Hello" (or silence timeout)
                logger.info(f"[IGNITION] Trigger Opener Signal Received for {session_id} (Reason: {reason})")
                
                # [ATTEMPT 12] Clear STT Buffer to kill the "Hello Queue"
                logger.info(f"[NUKE] Clearing STT Buffer for {session_id} to ensure fresh start.")
                aqi_stt_engine.clear_buffer(session_id)
                
                # [CLEAN PIPES] LIMBIC BYPASS DISABLED - No RAM greeting dump
                # Fresh TTS generation only - prevents duplicate greetings
                if False:  # Disabled - was: if GLOBAL_RAM_GREETING
                     logger.info("[CLEAN PIPES] LIMBIC BYPASS disabled - Fresh TTS only")
                     # RAM dump disabled - professional greeting comes from WebSocket in control_api.py
                else:
                     # Fire connect_callback to generate fresh greeting
                     logger.info("[CLEAN PIPES] Using fresh greeting generation")
                     if connect_callback:
                        try:
                            asyncio.create_task(connect_callback(session_id, reason=reason))
                        except TypeError:
                             asyncio.create_task(connect_callback(session_id))
            
            elif msg_type == "flush_buffer":
                # [ATTEMPT 39] FLASH-FLUSH
                logger.info(f"[ATTEMPT 39] FLASH-FLUSH: Sending Nuke to STT Engine.")
                aqi_stt_engine.clear_buffer(session_id)

            elif msg_type == "trigger_nudge":
                # [ATTEMPT 43] SECONDARY FALLBACK (The Nudge)
                logger.info(f"[NUDGE] Triggered for session {session_id}. Reason: {message.get('reason')}")
                nudge_text = "I might have a bad connection, let me try that again—I'm looking at your processing rates."
                # Fire the fallback directly
                await send_text_to_voice(nudge_text, session_id)


            elif msg_type == "session_update":
                # [ATTEMPT 44] INTELLIGENCE BINDING HANDSHAKE
                state = message.get("input_audio_transcription", "Unknown")
                logger.info(f"[SOVEREIGN] Intelligence Binding Handshake Received. Transcription State: {state}")
                # Ensure buffer is clear for fresh input
                aqi_stt_engine.clear_buffer(session_id)

            elif msg_type == "commit_turn":
                # [ATTEMPT 46] SERVER-SIDE VAD COMMIT
                # The bridge says "User stopped talking". Finalize STT now.
                logger.info(f"[VAD] Commit Signal Received for {session_id}. Finalizing STT.")
                await aqi_stt_engine.finalize_and_clear(session_id)

            elif msg_type == "debug_text_input":
                # [DEBUG] Manually inject text for testing
                text = message.get("text", "")
                logger.info(f"[DEBUG] Injecting text: '{text}'")
                await aqi_stt_engine.inject_transcript(session_id, text)

            elif msg_type == "audio_chunk":
                # [ATTEMPT 57] ENERGY-SOVEREIGN SNAP
                # Directive 57: Trigger on Raw Physics, not Text
                try:
                    # 1. Decode & Measure Physics
                    raw_audio = base64.b64decode(message.get("data", ""))
                    # Assume u-law (Twilio standard)
                    pcm_data = audioop.ulaw2lin(raw_audio, 2)
                    rms = audioop.rms(pcm_data, 2)
                    
                    # 2. Check Governance Gates 
                    elapsed = time.time() - session.call_start_time
                    shield_down = elapsed > session.INTRO_SHIELD_DURATION
                    
                    # [PHASE 9] ECHO SHIELD (500ms Grace Window on any speech start)
                    echo_shield_active = False
                    if session.agent_speaking:
                         if (time.time() - session.speech_start_time) < 0.5:
                             echo_shield_active = True
                             # logger.debug(f"[ECHO SHIELD] Ignored potential self-interruption (RMS={rms})")

                    # [TUNING] Sensitivity Adjusted (Forensics-Backed) -> Threshold optimized to 1000 (Speech=1158, Noise=385)
                    # Only trigger if: Shield Down + High Energy + First Turn + Not Triggered + Not Echo
                    if shield_down and rms > 1000 and session.turns_since_greeting == 0 and not echo_shield_active:
                         if not getattr(session, "energy_bypass_triggered", False):
                             logger.info(f"[ENERGY SNAP] RMS={rms} > 1000 at T+{elapsed:.2f}s. Executing PHYSICS BYPASS.")
                             
                             session.energy_bypass_triggered = True
                             
                             # [DIRECTIVE 58] ATOMIC FLUSH
                             if session.websocket:
                                 await session.websocket.send_json({"type": "clear_buffer"})
                                 
                             # 2. Cancel Generation (Stop adding fuel)
                             cancel_speech(session_id)
                             
                             # [DIRECTIVE 60] LISTEN MODE
                             logger.info(f"[LISTEN_MODE] Entering listening state for {session_id}")
                             
                             # 3. Lock State
                             session.turns_since_greeting += 1
                except Exception:
                    pass 

                # Placeholder for streaming STT
                if VOICE_STREAMING_STT_ENABLED:
                    # [PHASE 2] Barge-In Trigger
                    # If we receive audio volume > threshold (proxy), we could cancel TTS
                    # But for now, we rely on the STT engine to tell us there is text.
                    # The ACTUAL interruption happens when stt_callback fires.
                
                    b64_data = message.get("data")
                    fmt = message.get("format", "audio/webm")
                    await aqi_stt_engine.process_audio_chunk(session_id, b64_data, fmt)
            elif message["type"] == "interrupt":
                # [BARGE-IN] Explicit interruption signal from Bridge
                logger.info(f"[INTERRUPT] Received interrupt signal for session {session_id}")
                cancel_speech(session_id)
            elif message["type"] == "end_session":
                session.close()

    except WebSocketDisconnect:
        # [GRACEFUL EXIT] Don't log error for normal disconnect
        logger.info(f"[SHUTDOWN] WebSocket Disconnected for {session_id}")
        session.close()

    finally:
        # [ATTEMPT 58] DEATH-RATTLE CAPTURE
        # Ensure we capture the final words before destroying the session.
        # This fixes the "Perception Gap" where short calls leave no transcript.
        logger.info(f"[SHUTDOWN] Attempting Final STT Capture for {session_id}...")
        try:
             # We await this to ensure the callback fires while voice_sessions[session_id] is still valid.
             await aqi_stt_engine.finalize_and_clear(session_id)
        except Exception as e:
             logger.error(f"[SHUTDOWN] Finalize STT Failed: {e}")

        if session_id in voice_sessions:
            del voice_sessions[session_id]
        aqi_stt_engine.close_stt_session(session_id)