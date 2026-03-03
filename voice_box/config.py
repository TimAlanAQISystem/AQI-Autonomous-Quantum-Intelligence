import os
import logging

# [LOGGING]
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("VoiceBox")

# [ENV]
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
PUBLIC_TUNNEL_URL = os.getenv("PUBLIC_TUNNEL_URL")

# [AQI CONNECTION]
AQI_BACKEND_BASE_URL = "http://127.0.0.1:8777"
AQI_VOICE_SESSION_START = "/voice-session/start"
AQI_VOICE_WS_URL = "ws://127.0.0.1:8777/voice-session/ws"

# [CONSTANTS]
VAD_THRESHOLD = 2500

# [BUDGET & GOVERNANCE]
DAILY_LEAD_BUDGET = 2000         # Authorization to Reload (Founder Grade)
MAX_RETRIES_PER_LEAD = 5         # Increased Aggression
NEW_LEAD_DAILY_BUDGET = 1500     # Budget for fresh leads
RETRY_LEAD_DAILY_BUDGET = 500    # Budget for retries
MIN_CONTACT_GOAL = 1             # Minimum transcripts desired

# [FOUNDER-GRADE TIMING - PHASE 4 CALIBRATION]
# "The mismatch is latency. The fix is tightening detection."
VAD_START_THRESHOLD = 0.100       # 100ms (Detect intentional speech)
VAD_END_THRESHOLD = 0.150         # 150ms (Wait for micro-utterance end)
OPENER_DISPATCH_DELAY = 0.150     # 150ms (Human-grade response time)
INITIAL_SILENCE_WINDOW = 0.400    # 400ms (Don't talk over ringback)
MAX_SILENCE_BEFORE_OPENER = 10.0  # 10s (Disabled - WebSocket greeting handles this)
FALLBACK_SILENCE_TIMER = 3.0      # 3000ms (Re-engagement)
POST_OPENER_LISTEN_WINDOW = 0.750 # 750ms (Wait for reply)
INTERRUPTION_WINDOW = 0.150       # 150ms (Barge-in)
RMS_THRESHOLD = 500               # Sensitivity (Noise Floor)
