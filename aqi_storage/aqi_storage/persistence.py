# persistence.py
import os
import json
from datetime import datetime

BASE_DIR = "aqi_storage"

def ensure_dirs(run_id):
    paths = [
        f"{BASE_DIR}/packets",
        f"{BASE_DIR}/deltas",
        f"{BASE_DIR}/decisions",
        f"{BASE_DIR}/snapshots",
        f"{BASE_DIR}/runs/{run_id}/packets",
        f"{BASE_DIR}/runs/{run_id}/deltas",
        f"{BASE_DIR}/runs/{run_id}/decisions",
    ]
    for p in paths:
        os.makedirs(p, exist_ok=True)

def _write_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def persist_packet(packet, run_id, stage_index):
    ensure_dirs(run_id)
    ts = packet["timestamp"]
    stage = packet["stage"]

    global_path = f"{BASE_DIR}/packets/{ts}_{stage}.json"
    run_path = f"{BASE_DIR}/runs/{run_id}/packets/{stage_index}_{stage}.json"

    _write_json(global_path, packet)
    _write_json(run_path, packet)

def persist_delta(delta, run_id, stage_index):
    ensure_dirs(run_id)
    ts = delta["timestamp"]
    stage = delta["stage"]

    global_path = f"{BASE_DIR}/deltas/{ts}_{stage}.json"
    run_path = f"{BASE_DIR}/runs/{run_id}/deltas/{stage_index}_{stage}.json"

    _write_json(global_path, delta)
    _write_json(run_path, delta)

def persist_decision(decision, run_id, stage_index):
    ensure_dirs(run_id)
    ts = decision["timestamp"]
    stage = decision["stage"]

    global_path = f"{BASE_DIR}/decisions/{ts}_{stage}.json"
    run_path = f"{BASE_DIR}/runs/{run_id}/decisions/{stage_index}_{stage}.json"

    _write_json(global_path, decision)
    _write_json(run_path, decision)

def persist_snapshot(snapshot):
    run_id = snapshot["run_id"]
    ensure_dirs(run_id)
    path = f"{BASE_DIR}/snapshots/{run_id}_snapshot.json"
    _write_json(path, snapshot)

    # Also store inside the run folder
    run_path = f"{BASE_DIR}/runs/{run_id}/summary.json"
    _write_json(run_path, snapshot)