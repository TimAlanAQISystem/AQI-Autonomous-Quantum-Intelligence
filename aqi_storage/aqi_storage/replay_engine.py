# replay_engine.py
import json
import os

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def replay_run(run_id):
    base = f"aqi_storage/runs/{run_id}"

    packets_dir = f"{base}/packets"
    deltas_dir = f"{base}/deltas"
    decisions_dir = f"{base}/decisions"

    packets = []
    deltas = []
    decisions = []

    # Load in stage order
    for fname in sorted(os.listdir(packets_dir)):
        packets.append(load_json(f"{packets_dir}/{fname}"))

    for fname in sorted(os.listdir(deltas_dir)):
        deltas.append(load_json(f"{deltas_dir}/{fname}"))

    for fname in sorted(os.listdir(decisions_dir)):
        decisions.append(load_json(f"{decisions_dir}/{fname}"))

    # Reconstruct state
    reconstructed_state = {}
    for packet in packets:
        stage = packet["stage"]
        reconstructed_state[stage] = packet["payload"]

    return {
        "run_id": run_id,
        "packets": packets,
        "deltas": deltas,
        "decisions": decisions,
        "reconstructed_state": reconstructed_state
    }