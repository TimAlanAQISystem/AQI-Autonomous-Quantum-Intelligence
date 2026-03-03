"""
+==============================================================================+
|   ORGAN 36 — DTMF REFLEX                                                     |
|                                                                               |
|   PURPOSE:                                                                    |
|   Generate and stream DTMF (Dual-Tone Multi-Frequency) tones through the     |
|   Twilio Media Streams WebSocket. This gives Alan the ability to "press       |
|   buttons" on phone calls — navigating IVR menus, responding to spam          |
|   blockers, and interacting with any tone-based phone system.                 |
|                                                                               |
|   ARCHITECTURE:                                                               |
|   - Pure audio generation: no TwiML changes, no API calls required            |
|   - Generates standard ITU-T DTMF tones as mulaw 8kHz audio                  |
|   - Streams through the same WebSocket path as TTS audio                      |
|   - Pre-generates all 16 tones at module load for zero-latency               |
|                                                                               |
|   DTMF STANDARD (ITU-T Q.23 / RFC 4733):                                     |
|     Each button = sum of one LOW freq + one HIGH freq                         |
|     Minimum tone duration: 65ms (we use 120ms for reliability)                |
|     Minimum inter-digit gap: 65ms (we use 80ms)                              |
|                                                                               |
|   CONSTITUTIONAL CONSTRAINTS:                                                 |
|   - Never send DTMF speculatively — only from parsed menu options or          |
|     predefined route maps                                                     |
|   - Never send more than 10 digits without an explicit route plan             |
|   - Log every digit sent with timestamp and context                           |
|   - No digit inference or hallucination                                       |
|                                                                               |
|   LINEAGE: Organ 36. Created 2026-02-26.                                      |
|   DIRECTIVE: "Finding a way for Alan to reach these businesses" — Tim         |
+==============================================================================+
"""

import math
import struct
import audioop
import base64
import json
import time
import asyncio
import logging
import os
from typing import Optional, List, Dict
from dataclasses import dataclass, field

logger = logging.getLogger("DTMF_REFLEX")

# ======================================================================
#  TWILIO REST API DTMF (out-of-band fallback)
# ======================================================================
# In-band DTMF tones may not survive codec transcoding or noise gates.
# The REST API method uses Twilio's signaling layer (RFC 2833) which is
# more reliable. We try in-band first, then fall back to REST API.

_TWILIO_CLIENT = None  # Lazy-loaded

def _get_twilio_client():
    """Lazy-load Twilio client for REST API DTMF fallback."""
    global _TWILIO_CLIENT
    if _TWILIO_CLIENT:
        return _TWILIO_CLIENT
    try:
        from twilio.rest import Client
        account_sid = os.environ.get('TWILIO_ACCOUNT_SID', '')
        auth_token = os.environ.get('TWILIO_AUTH_TOKEN', '')
        if account_sid and auth_token:
            _TWILIO_CLIENT = Client(account_sid, auth_token)
            logger.info("[ORGAN 36] Twilio REST client loaded for DTMF fallback")
        else:
            logger.warning("[ORGAN 36] Twilio credentials not found — REST API DTMF fallback unavailable")
    except ImportError:
        logger.warning("[ORGAN 36] twilio package not installed — REST API DTMF fallback unavailable")
    return _TWILIO_CLIENT


async def _send_dtmf_via_rest_api(call_sid: str, digits: str) -> bool:
    """Send DTMF via Twilio REST API (out-of-band, RFC 2833).
    
    Uses calls(sid).update() with Play digits TwiML to send DTMF
    through Twilio's signaling layer rather than as in-band audio.
    This is more reliable for IVR systems that use RFC 2833 detection.
    
    Args:
        call_sid: The Twilio Call SID
        digits: Digits to send (e.g., '1', '0w0')
        
    Returns:
        True if the API call succeeded.
    """
    client = _get_twilio_client()
    if not client or not call_sid:
        return False
    
    try:
        # Convert 'w' to 'w' (Twilio Play digits uses 'w' for 0.5s pause)
        # Clean to only valid Play digits chars: 0-9, #, *, w
        clean_digits = ''.join(c for c in digits if c in '0123456789*#wW')
        if not clean_digits:
            return False
        
        # Use send_digits parameter on the call
        # This sends DTMF tones through the signaling layer
        twiml = f'<Response><Play digits="{clean_digits}"/><Pause length="60"/></Response>'
        
        # Run the blocking API call in a thread to not block the event loop
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: client.calls(call_sid).update(twiml=twiml)
        )
        
        logger.info(f"[ORGAN 36] REST API DTMF sent: '{clean_digits}' for call {call_sid[:20]}...")
        return True
        
    except Exception as e:
        logger.error(f"[ORGAN 36] REST API DTMF failed: {e}")
        return False


# ======================================================================
#  DTMF FREQUENCY TABLE (ITU-T Q.23)
# ======================================================================
#
#          1209 Hz   1336 Hz   1477 Hz   1633 Hz
# 697 Hz     1         2         3         A
# 770 Hz     4         5         6         B
# 852 Hz     7         8         9         C
# 941 Hz     *         0         #         D
#
# ======================================================================

DTMF_FREQUENCIES = {
    '1': (697, 1209), '2': (697, 1336), '3': (697, 1477), 'A': (697, 1633),
    '4': (770, 1209), '5': (770, 1336), '6': (770, 1477), 'B': (770, 1633),
    '7': (852, 1209), '8': (852, 1336), '9': (852, 1477), 'C': (852, 1633),
    '*': (941, 1209), '0': (941, 1336), '#': (941, 1477), 'D': (941, 1633),
}

# Audio parameters — must match Twilio Media Streams
SAMPLE_RATE = 8000       # 8 kHz mulaw
TONE_DURATION_MS = 120   # 120ms tone (well above 65ms minimum)
GAP_DURATION_MS = 80     # 80ms inter-digit silence
TONE_AMPLITUDE = 0.25    # -12 dBFS — loud enough for PSTN, not clipping
CHUNK_SIZE = 160         # 20ms frames (8000 Hz * 0.020s = 160 samples)


# ======================================================================
#  TONE GENERATION (Pre-computed at module load)
# ======================================================================

def _generate_dtmf_tone(low_freq: int, high_freq: int) -> bytes:
    """Generate a single DTMF tone as mulaw 8kHz audio.
    
    Each DTMF digit = sum of two sine waves at the specified frequencies.
    Output is raw mulaw bytes ready for Twilio Media Streams.
    """
    n_samples = int(SAMPLE_RATE * TONE_DURATION_MS / 1000)
    pcm_samples = []
    
    for i in range(n_samples):
        t = i / SAMPLE_RATE
        # Sum of two sine waves, each at half amplitude
        sample = (
            TONE_AMPLITUDE * 0.5 * math.sin(2 * math.pi * low_freq * t) +
            TONE_AMPLITUDE * 0.5 * math.sin(2 * math.pi * high_freq * t)
        )
        # Convert to 16-bit PCM
        pcm_val = int(sample * 32767)
        pcm_val = max(-32768, min(32767, pcm_val))
        pcm_samples.append(pcm_val)
    
    # Pack as 16-bit little-endian PCM, then convert to mulaw
    pcm_bytes = struct.pack(f'<{len(pcm_samples)}h', *pcm_samples)
    mulaw_bytes = audioop.lin2ulaw(pcm_bytes, 2)
    return mulaw_bytes


def _generate_silence(duration_ms: int) -> bytes:
    """Generate silence as mulaw 8kHz audio."""
    n_samples = int(SAMPLE_RATE * duration_ms / 1000)
    # Mulaw silence = 0xFF (mu-law encoding of 0)
    return b'\xFF' * n_samples


# Pre-generate all 16 DTMF tones + silence gap
_TONE_CACHE: Dict[str, bytes] = {}
_SILENCE_GAP: bytes = b''

def _init_tone_cache():
    """Pre-generate all DTMF tones at module load."""
    global _TONE_CACHE, _SILENCE_GAP
    for digit, (low, high) in DTMF_FREQUENCIES.items():
        _TONE_CACHE[digit] = _generate_dtmf_tone(low, high)
    _SILENCE_GAP = _generate_silence(GAP_DURATION_MS)
    logger.info(f"[ORGAN 36] Pre-generated {len(_TONE_CACHE)} DTMF tones "
                f"({TONE_DURATION_MS}ms tone + {GAP_DURATION_MS}ms gap)")

# Initialize at import
_init_tone_cache()


# ======================================================================
#  DTMF EVENT LOG (per-call lineage)
# ======================================================================

@dataclass
class DTMFEvent:
    """A single DTMF event — sent or received."""
    digit: str
    direction: str  # 'sent' or 'received'
    timestamp: float
    context: str = ""  # Why this digit was sent (e.g., "IVR menu: press 1 for sales")
    
    def to_dict(self) -> dict:
        return {
            'digit': self.digit,
            'direction': self.direction,
            'timestamp': self.timestamp,
            'context': self.context,
        }


# ======================================================================
#  DTMF REFLEX ENGINE (per-call instance)
# ======================================================================

class DTMFReflex:
    """Per-call DTMF reflex — generates tones and tracks digit history.
    
    Usage:
        reflex = DTMFReflex()
        
        # Send a single digit
        await reflex.send_digit(websocket, stream_sid, '1', context='IVR: press 1 for sales')
        
        # Send a sequence (e.g., extension number)
        await reflex.send_sequence(websocket, stream_sid, '1w0', context='IVR: press 1 then 0')
        
        # Record a received digit (from inbound DTMF detection)
        reflex.record_received('5', context='caller pressed 5')
    """
    
    # Safety: maximum digits per call
    MAX_DIGITS_PER_CALL = 20
    
    def __init__(self):
        self.events: List[DTMFEvent] = []
        self.digits_sent: int = 0
        self.digits_received: int = 0
        self._active = True
    
    async def send_digit(
        self,
        websocket,
        stream_sid: str,
        digit: str,
        context: str = "",
        call_sid: str = "",
    ) -> bool:
        """Send a single DTMF digit — tries in-band audio first, REST API fallback.
        
        Strategy:
        1. Send in-band DTMF tone through WebSocket (works if IVR uses audio detection)
        2. Simultaneously send via REST API (works if IVR uses RFC 2833 / out-of-band)
        Both methods are attempted for maximum compatibility.
        
        Args:
            websocket: The Twilio Media Streams WebSocket connection
            stream_sid: The Twilio stream SID for media framing
            digit: The digit to send ('0'-'9', '*', '#', 'A'-'D')
            context: Why this digit is being sent (for audit trail)
            call_sid: The Twilio Call SID (for REST API fallback)
            
        Returns:
            True if sent successfully via either method, False if both failed.
        """
        digit = str(digit).upper()
        
        # Safety: validate digit
        if digit not in _TONE_CACHE:
            logger.warning(f"[ORGAN 36] Invalid DTMF digit: '{digit}' — blocked")
            return False
        
        # Safety: per-call limit
        if self.digits_sent >= self.MAX_DIGITS_PER_CALL:
            logger.warning(f"[ORGAN 36] Per-call digit limit ({self.MAX_DIGITS_PER_CALL}) reached — blocked")
            return False
        
        if not self._active:
            logger.warning(f"[ORGAN 36] DTMF reflex deactivated — blocked")
            return False
        
        inband_ok = False
        rest_ok = False
        
        # METHOD 1: In-band audio DTMF
        tone_audio = _TONE_CACHE[digit]
        try:
            await _stream_raw_audio(websocket, tone_audio, stream_sid)
            await _stream_raw_audio(websocket, _SILENCE_GAP, stream_sid)
            inband_ok = True
            logger.info(f"[ORGAN 36] In-band DTMF sent: '{digit}'")
        except Exception as e:
            logger.warning(f"[ORGAN 36] In-band DTMF failed for '{digit}': {e}")
        
        # METHOD 2: REST API DTMF (out-of-band, more reliable)
        if call_sid:
            try:
                rest_ok = await _send_dtmf_via_rest_api(call_sid, digit)
                if rest_ok:
                    logger.info(f"[ORGAN 36] REST API DTMF sent: '{digit}'")
            except Exception as e:
                logger.warning(f"[ORGAN 36] REST API DTMF failed for '{digit}': {e}")
        
        success = inband_ok or rest_ok
        
        if success:
            # Record event
            self.digits_sent += 1
            method = []
            if inband_ok:
                method.append('inband')
            if rest_ok:
                method.append('rest_api')
            event = DTMFEvent(
                digit=digit,
                direction='sent',
                timestamp=time.time(),
                context=f"{context} [via {'+'.join(method)}]",
            )
            self.events.append(event)
            logger.info(f"[ORGAN 36] DTMF SENT: '{digit}' ({context}) via {'+'.join(method)} — total sent: {self.digits_sent}")
        else:
            logger.error(f"[ORGAN 36] DTMF FAILED: '{digit}' — both in-band and REST API failed")
        
        return success
    
    async def send_sequence(
        self,
        websocket,
        stream_sid: str,
        sequence: str,
        context: str = "",
        call_sid: str = "",
        inter_digit_delay_ms: int = 0,
    ) -> int:
        """Send a sequence of DTMF digits.
        
        Supports 'w' for a 500ms wait (standard DTMF convention).
        
        Args:
            sequence: String of digits, e.g., "1w0" (press 1, wait, press 0)
            context: Audit trail context
            call_sid: Twilio Call SID for REST API fallback
            inter_digit_delay_ms: Extra delay between digits (0 = standard gap only)
            
        Returns:
            Number of digits successfully sent.
        """
        sent = 0
        for char in sequence:
            if char.lower() == 'w':
                # 'w' = 500ms wait
                await asyncio.sleep(0.5)
                continue
            
            success = await self.send_digit(websocket, stream_sid, char, context=context, call_sid=call_sid)
            if success:
                sent += 1
            else:
                logger.warning(f"[ORGAN 36] Sequence aborted at position {sent} (digit='{char}')")
                break
            
            # Extra inter-digit delay if requested
            if inter_digit_delay_ms > 0:
                await asyncio.sleep(inter_digit_delay_ms / 1000.0)
        
        logger.info(f"[ORGAN 36] Sequence complete: sent {sent}/{len(sequence.replace('w', ''))} digits")
        return sent
    
    def record_received(self, digit: str, context: str = ""):
        """Record a DTMF digit received from the far end."""
        self.digits_received += 1
        event = DTMFEvent(
            digit=digit,
            direction='received',
            timestamp=time.time(),
            context=context,
        )
        self.events.append(event)
        logger.info(f"[ORGAN 36] DTMF RECEIVED: '{digit}' ({context})")
    
    def deactivate(self):
        """Deactivate DTMF sending (safety kill switch)."""
        self._active = False
        logger.info("[ORGAN 36] DTMF reflex deactivated")
    
    def get_history(self) -> List[dict]:
        """Get the full DTMF event history for this call."""
        return [e.to_dict() for e in self.events]
    
    def get_digits_sent_string(self) -> str:
        """Get all sent digits as a compact string."""
        return ''.join(e.digit for e in self.events if e.direction == 'sent')
    
    def get_digits_received_string(self) -> str:
        """Get all received digits as a compact string."""
        return ''.join(e.digit for e in self.events if e.direction == 'received')


# ======================================================================
#  AUDIO STREAMING HELPER
# ======================================================================

async def _stream_raw_audio(websocket, audio_bytes: bytes, stream_sid: str):
    """Stream raw mulaw audio through the Twilio Media Streams WebSocket.
    
    Frames audio into 20ms chunks (160 bytes) with proper JSON wrapping.
    Uses the same format as the relay server's TTS streaming.
    """
    offset = 0
    while offset < len(audio_bytes):
        end = min(offset + CHUNK_SIZE, len(audio_bytes))
        frame = audio_bytes[offset:end]
        offset = end
        
        # Pad short final frame
        if len(frame) < CHUNK_SIZE:
            frame = frame + b'\xFF' * (CHUNK_SIZE - len(frame))
        
        b64_data = base64.b64encode(frame).decode('utf-8')
        payload = {
            "event": "media",
            "streamSid": stream_sid,
            "media": {"payload": b64_data}
        }
        
        try:
            if hasattr(websocket, 'send_text'):
                await websocket.send_text(json.dumps(payload))
            else:
                await websocket.send(json.dumps(payload))
        except Exception:
            raise
        
        # Pacing: ~20ms per frame to match real-time audio rate
        await asyncio.sleep(0.018)


# ======================================================================
#  MODULE-LEVEL FACTORY
# ======================================================================

def create_dtmf_reflex() -> DTMFReflex:
    """Factory: create a new per-call DTMFReflex instance."""
    return DTMFReflex()
