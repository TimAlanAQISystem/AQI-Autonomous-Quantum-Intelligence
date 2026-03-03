# alan_config.py

WAKE_WORD = "alan"
STOP_LISTENING_PHRASE = "alan stop listening"
END_SESSION_PHRASES = [
    "thank you alan",
    "ok alan",
    "that is all alan",
    "we are done alan"
]

# Memory paths
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
LOGS_DIR = os.path.join(DATA_DIR, "logs")
JSON_MEMORY_PATH = os.path.join(DATA_DIR, "memory.json")
SQLITE_DB_PATH = os.path.join(DATA_DIR, "sessions.db")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)