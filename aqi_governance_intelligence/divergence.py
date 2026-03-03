# divergence.py
import json
import os

BASE = "aqi_storage"

def _load(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def compare_runs(run_a, run_b):
    def load_packets(run_id):
        path = f"{BASE}/runs/{run_id}/packets"
        packets = []
        for fname in sorted(os.listdir(path)):
            packets.append(_load(f"{path}/{fname}"))
        return packets

    a_packets = load_packets(run_a)
    b_packets = load_packets(run_b)

    diffs = []
    for i, (pa, pb) in enumerate(zip(a_packets, b_packets)):
        if pa["payload"] != pb["payload"]:
            diffs.append({
                "stage_index": i,
                "stage": pa["stage"],
                "run_a": pa["payload"],
                "run_b": pb["payload"]
            })

    return diffs

def detect_drift(run_a, run_b):
    diffs = compare_runs(run_a, run_b)
    return {"run_a": run_a, "run_b": run_b, "differences": diffs}