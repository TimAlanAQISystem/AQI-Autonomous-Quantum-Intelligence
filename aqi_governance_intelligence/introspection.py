# introspection.py
import json
import os

BASE = "aqi_storage"

def _load(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def time_travel(run_id, stage):
    path = f"{BASE}/runs/{run_id}/packets"
    for fname in sorted(os.listdir(path)):
        packet = _load(f"{path}/{fname}")
        if packet["stage"] == stage:
            return packet
    return None

def authority_history(run_id):
    path = f"{BASE}/runs/{run_id}/decisions"
    history = []

    for fname in sorted(os.listdir(path)):
        decision = _load(f"{path}/{fname}")
        history.append({
            "stage": decision["stage"],
            "authority": decision["authority"],
            "decision": decision["decision"],
            "reason": decision.get("reason", "")
        })

    return history