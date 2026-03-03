# integrity.py
import json
import os
import hashlib

BASE = "aqi_storage"

def _hash_json(obj):
    data = json.dumps(obj, sort_keys=True).encode("utf-8")
    return hashlib.sha256(data).hexdigest()

def _load(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def compute_hash_chain(run_id):
    run_dir = f"{BASE}/runs/{run_id}/packets"
    hashes = []

    for fname in sorted(os.listdir(run_dir)):
        packet = _load(f"{run_dir}/{fname}")
        h = _hash_json(packet)
        hashes.append(h)

    return hashes

def compute_merkle_root(run_id):
    hashes = compute_hash_chain(run_id)

    if not hashes:
        return None

    layer = hashes
    while len(layer) > 1:
        next_layer = []
        for i in range(0, len(layer), 2):
            left = layer[i]
            right = layer[i+1] if i+1 < len(layer) else left
            combined = hashlib.sha256((left + right).encode("utf-8")).hexdigest()
            next_layer.append(combined)
        layer = next_layer

    return layer[0]

def verify_integrity(run_id):
    root = compute_merkle_root(run_id)
    return {"run_id": run_id, "merkle_root": root}