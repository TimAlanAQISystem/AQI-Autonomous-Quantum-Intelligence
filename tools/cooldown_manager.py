import time
import json
from pathlib import Path
import os
import sys

# [TIMING CONFIG] Import centralized timing values
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from timing_loader import TIMING

# Constants
# Adjusted path to match workspace structure relative to this file or runtime
# Using absolute path for safety in this environment
WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_FILE = Path(os.path.join(WORKSPACE_ROOT, "state", "call_state.json"))
COOLDOWN_SECONDS = TIMING.campaign_cooldown  # [TIMING CONFIG] Loaded from timing_config.json

def load_call_state():
    if not STATE_FILE.exists():
        return {"call_active": False, "last_call_timestamp": 0}

    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except Exception:
        # Corrupted state file -> fail safe
        return {"call_active": False, "last_call_timestamp": 0}


def save_call_state(state):
    try:
        # Ensure directory exists just in case
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(STATE_FILE, "w") as f:
            json.dump(state, f)
    except Exception as e:
        print(f"Error saving call state: {e}")


def cooldown_gate():
    """
    Enforces the invariant:
    Alan may NEVER dial unless:
      - call_active == False
      - AND (now - last_call_timestamp) >= COOLDOWN_SECONDS
    """

    state = load_call_state()
    now = time.time()

    # Hard block if system thinks a call is active
    if state.get("call_active", False):
        print("CooldownGate: Call already active. Blocking dial.")
        return False

    last_ts = state.get("last_call_timestamp", 0)
    elapsed = now - last_ts

    if elapsed < COOLDOWN_SECONDS:
        remaining = int(COOLDOWN_SECONDS - elapsed)
        # Avoid spamming logs if checked frequently, but required for debugging
        # print(f"CooldownGate: Cooldown active. {remaining} seconds remaining.")
        return False

    return True


def mark_call_started():
    state = load_call_state()
    state["call_active"] = True
    save_call_state(state)


def mark_call_ended():
    state = load_call_state()
    state["call_active"] = False
    state["last_call_timestamp"] = time.time()
    save_call_state(state)

def force_reset_state():
    """Emergency reset of state"""
    state = {
        "call_active": False,
        "last_call_timestamp": 0
    }
    save_call_state(state)
    print("CooldownGate: State forcefully reset.")
