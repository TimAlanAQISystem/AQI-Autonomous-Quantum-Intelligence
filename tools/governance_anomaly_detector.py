"""
Governance Anomaly Detector
=============================
Analyzes Phase 5 cycle JSONL data for governance anomalies:
  - Stuck modes (same dominant > N consecutive turns)
  - Wild swings (dominant changes every turn)
  - Prosody inversions (mismatched affect)
  - Entropy explosions (near-uniform distribution)
  - Entropy collapse (single-mode lock)

Usage:
    .venv\\Scripts\\python.exe tools/governance_anomaly_detector.py <jsonl_path> [output_json]
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ─── THRESHOLDS ───────────────────────────────────────────────────────────
STUCK_THRESHOLD = 5          # Same dominant for N+ consecutive turns
ENTROPY_HIGH = 1.4           # Near-uniform — Alan has no personality
ENTROPY_LOW = 0.5            # Single-mode lock — Alan is rigid
SPEED_MOD_LIMIT = 0.08       # Prosody band limit
SILENCE_MOD_LIMIT = 3        # Prosody band limit


def detect_stuck_modes(records):
    """Find runs of identical dominant mode exceeding threshold."""
    anomalies = []
    if not records:
        return anomalies

    current_mode = records[0].get("quantum_dominant", "")
    run_start = 0
    run_length = 1

    for i in range(1, len(records)):
        mode = records[i].get("quantum_dominant", "")
        if mode == current_mode:
            run_length += 1
        else:
            if run_length >= STUCK_THRESHOLD:
                anomalies.append({
                    "type": "stuck_mode",
                    "mode": current_mode,
                    "start_turn": run_start,
                    "end_turn": i - 1,
                    "duration": run_length,
                    "severity": "high" if run_length >= 8 else "medium",
                })
            current_mode = mode
            run_start = i
            run_length = 1

    # Check final run
    if run_length >= STUCK_THRESHOLD:
        anomalies.append({
            "type": "stuck_mode",
            "mode": current_mode,
            "start_turn": run_start,
            "end_turn": len(records) - 1,
            "duration": run_length,
            "severity": "high" if run_length >= 8 else "medium",
        })

    return anomalies


def detect_wild_swings(records):
    """Find rapid mode oscillation (change every turn for 4+ turns)."""
    anomalies = []
    if len(records) < 4:
        return anomalies

    changes = []
    for i in range(1, len(records)):
        prev = records[i - 1].get("quantum_dominant", "")
        curr = records[i].get("quantum_dominant", "")
        changes.append(prev != curr)

    # Find runs of True (changes) of length >= 3
    run_start = None
    run_length = 0

    for i, changed in enumerate(changes):
        if changed:
            if run_start is None:
                run_start = i
            run_length += 1
        else:
            if run_length >= 3:
                anomalies.append({
                    "type": "wild_swing",
                    "start_turn": run_start,
                    "end_turn": run_start + run_length,
                    "duration": run_length,
                    "severity": "medium",
                })
            run_start = None
            run_length = 0

    if run_length >= 3 and run_start is not None:
        anomalies.append({
            "type": "wild_swing",
            "start_turn": run_start,
            "end_turn": run_start + run_length,
            "duration": run_length,
            "severity": "medium",
        })

    return anomalies


def detect_entropy_anomalies(records):
    """Find turns where entropy is outside healthy range."""
    anomalies = []
    for i, r in enumerate(records):
        ent = r.get("quantum_entropy", 1.0)
        if ent > ENTROPY_HIGH:
            anomalies.append({
                "type": "entropy_explosion",
                "turn": i,
                "entropy": ent,
                "threshold": ENTROPY_HIGH,
                "severity": "medium",
            })
        elif ent < ENTROPY_LOW:
            anomalies.append({
                "type": "entropy_collapse",
                "turn": i,
                "entropy": ent,
                "threshold": ENTROPY_LOW,
                "severity": "low",
            })
    return anomalies


def detect_prosody_inversions(records):
    """Find turns where prosody bias contradicts sentiment."""
    anomalies = []
    for i, r in enumerate(records):
        sentiment = r.get("sentiment", "neutral")
        pb = r.get("prosody_bias", {})
        speed = pb.get("speed_mod", 0)
        intent = pb.get("preferred_intent", "")

        # Positive sentiment but negative prosody intent
        if sentiment == "positive" and intent in ("somber", "stern", "cold"):
            anomalies.append({
                "type": "prosody_inversion",
                "turn": i,
                "sentiment": sentiment,
                "preferred_intent": intent,
                "severity": "high",
            })
        # Negative sentiment but overly upbeat prosody
        if sentiment == "negative" and intent in ("playful", "excited", "bright"):
            anomalies.append({
                "type": "prosody_inversion",
                "turn": i,
                "sentiment": sentiment,
                "preferred_intent": intent,
                "severity": "high",
            })

        # Out-of-band prosody values
        if abs(speed) > SPEED_MOD_LIMIT:
            anomalies.append({
                "type": "prosody_out_of_band",
                "turn": i,
                "speed_mod": speed,
                "limit": SPEED_MOD_LIMIT,
                "severity": "medium",
            })

        silence = pb.get("silence_mod", 0)
        if abs(silence) > SILENCE_MOD_LIMIT:
            anomalies.append({
                "type": "prosody_out_of_band",
                "turn": i,
                "silence_mod": silence,
                "limit": SILENCE_MOD_LIMIT,
                "severity": "medium",
            })

    return anomalies


def load_records(jsonl_path):
    """Load records from JSONL."""
    records = []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def main():
    if len(sys.argv) < 2:
        print("Usage: python tools/governance_anomaly_detector.py <jsonl_path> [output_json]")
        return 1

    jsonl_path = sys.argv[1]
    if not os.path.exists(jsonl_path):
        print(f"ERROR: File not found: {jsonl_path}")
        return 1

    if len(sys.argv) >= 3:
        output_path = sys.argv[2]
    else:
        base = os.path.splitext(jsonl_path)[0]
        output_path = base + "_anomalies.json"

    records = load_records(jsonl_path)
    if not records:
        print("ERROR: No records in JSONL file.")
        return 1

    print(f"  Loaded {len(records)} records from {jsonl_path}")

    all_anomalies = []
    all_anomalies.extend(detect_stuck_modes(records))
    all_anomalies.extend(detect_wild_swings(records))
    all_anomalies.extend(detect_entropy_anomalies(records))
    all_anomalies.extend(detect_prosody_inversions(records))

    # Summary
    by_type = {}
    for a in all_anomalies:
        t = a["type"]
        by_type[t] = by_type.get(t, 0) + 1

    report = {
        "source": jsonl_path,
        "total_turns": len(records),
        "total_anomalies": len(all_anomalies),
        "by_type": by_type,
        "anomalies": all_anomalies,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"  Anomalies detected: {len(all_anomalies)}")
    for t, count in by_type.items():
        print(f"    {t}: {count}")
    print(f"  Report saved to: {output_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
