"""
Classifier Audit Script -- Post-Campaign Analysis
===================================================
Retroactively classifies all CDC calls and shows distribution.
Run after each campaign to validate classifier behavior.

Usage:
    python classifier_audit.py                  # Classify last 50 calls
    python classifier_audit.py --all            # All calls in CDC
    python classifier_audit.py --edges          # Only edge cases
    python classifier_audit.py --last 20        # Last N calls

Author: Claude Opus 4.6 - AQI System Expert
Date: February 18, 2026
"""

import os
import sys
import json
import sqlite3
from collections import Counter
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from call_type_classifier import CallTypeClassifier
from call_feature_aggregator import CallFeatureAggregator
from classifier_config_loader import ClassifierConfigLoader


def load_calls(db_path="data/call_capture.db", limit=50, all_calls=False):
    """Load call records from CDC."""
    if not os.path.exists(db_path):
        print(f"CDC database not found: {db_path}")
        return [], {}

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    if all_calls:
        calls = conn.execute(
            "SELECT * FROM calls ORDER BY start_time DESC"
        ).fetchall()
    else:
        calls = conn.execute(
            "SELECT * FROM calls ORDER BY start_time DESC LIMIT ?",
            (limit,)
        ).fetchall()

    # Build turns lookup
    turns_by_call = {}
    all_sids = [c["call_sid"] for c in calls]
    for sid in all_sids:
        turns = conn.execute(
            "SELECT * FROM turns WHERE call_sid = ? ORDER BY turn_number",
            (sid,)
        ).fetchall()
        turns_by_call[sid] = [dict(t) for t in turns]

    conn.close()
    return [dict(c) for c in calls], turns_by_call


def classify_all(calls, turns_by_call, classifier, aggregator):
    """Classify all calls and return results."""
    results = []
    for call in calls:
        sid = call["call_sid"]
        turns = turns_by_call.get(sid, [])

        if turns:
            features = aggregator.aggregate_from_cdc_turns(sid, turns)
            classification = classifier.classify(features)
        else:
            classification = classifier.classify_from_cdc(call)

        results.append({
            "call_sid": sid,
            "business_name": call.get("business_name", "Unknown"),
            "duration": call.get("duration_seconds", 0) or 0,
            "turns": call.get("total_turns", 0) or 0,
            "merchant_words": call.get("merchant_words", 0) or 0,
            "alan_words": call.get("alan_words", 0) or 0,
            "cdc_outcome": call.get("final_outcome", "unknown"),
            "classifier_type": classification["call_type"],
            "confidence": classification["confidence"],
            "override_flags": classification["override_flags"],
            "reasoning": classification.get("reasoning", ""),
            "raw_scores": classification["raw_scores"],
            "probabilities": classification["probabilities"],
            "start_time": call.get("start_time", ""),
        })

    return results


def print_distribution(results):
    """Print call type distribution."""
    print("\n" + "=" * 70)
    print("CALL TYPE DISTRIBUTION")
    print("=" * 70)

    type_counts = Counter(r["classifier_type"] for r in results)
    total = len(results)
    for ct, count in type_counts.most_common():
        pct = 100 * count / max(total, 1)
        bar = "#" * int(pct / 2)
        print(f"  {ct:<25s} {count:>4d} ({pct:5.1f}%) {bar}")

    print(f"\n  Total: {total}")


def print_confidence_bands(results):
    """Print confidence distribution by band."""
    print("\n" + "-" * 70)
    print("CONFIDENCE BANDS")
    print("-" * 70)

    bands = {"high (>=0.9)": 0, "medium (0.7-0.9)": 0, "low (<0.7)": 0}
    for r in results:
        c = r["confidence"]
        if c >= 0.9:
            bands["high (>=0.9)"] += 1
        elif c >= 0.7:
            bands["medium (0.7-0.9)"] += 1
        else:
            bands["low (<0.7)"] += 1

    for band, count in bands.items():
        pct = 100 * count / max(len(results), 1)
        print(f"  {band:<20s} {count:>4d} ({pct:5.1f}%)")


def print_overrides(results):
    """Print override usage."""
    print("\n" + "-" * 70)
    print("OVERRIDE USAGE")
    print("-" * 70)

    override_counts = Counter()
    for r in results:
        for flag in r["override_flags"]:
            override_counts[flag] += 1

    calls_with_overrides = sum(1 for r in results if r["override_flags"])
    print(f"  Calls with overrides: {calls_with_overrides} / {len(results)}")
    for flag, count in override_counts.most_common():
        print(f"  {flag:<35s} {count:>4d}")


def print_calls_by_type(results, call_type, max_show=20):
    """Print calls of a specific type."""
    filtered = [r for r in results if r["classifier_type"] == call_type]
    if not filtered:
        return

    print(f"\n{'-' * 70}")
    print(f"{call_type.upper()} ({len(filtered)} calls)")
    print(f"{'-' * 70}")
    print(f"{'SID':<18s} {'Business':<25s} {'Dur':>5s} {'Trn':>4s} {'Words':>5s} "
          f"{'Conf':>5s} {'CDC Outcome':<20s} {'Overrides'}")

    for r in filtered[:max_show]:
        sid_short = r["call_sid"][:16] + ".." if len(r["call_sid"]) > 16 else r["call_sid"]
        biz = (r["business_name"] or "Unknown")[:24]
        overrides = ",".join(r["override_flags"]) if r["override_flags"] else "-"
        print(
            f"  {sid_short:<18s} {biz:<25s} {r['duration']:>5.0f} {r['turns']:>4d} "
            f"{r['merchant_words']:>5d} {r['confidence']:>5.2f} "
            f"{r['cdc_outcome']:<20s} {overrides}"
        )

    if len(filtered) > max_show:
        print(f"  ... and {len(filtered) - max_show} more")


def print_edge_cases(results, max_show=30):
    """Print low-confidence or overridden calls."""
    edges = [r for r in results if r["confidence"] < 0.8 or r["override_flags"]]
    edges.sort(key=lambda r: r["confidence"])

    print(f"\n{'=' * 70}")
    print(f"EDGE CASES (low confidence or overridden): {len(edges)} calls")
    print(f"{'=' * 70}")
    print(f"{'SID':<18s} {'Business':<25s} {'Dur':>5s} {'Type':<20s} "
          f"{'Conf':>5s} {'CDC':<16s} {'Overrides'}")

    for r in edges[:max_show]:
        sid_short = r["call_sid"][:16] + ".." if len(r["call_sid"]) > 16 else r["call_sid"]
        biz = (r["business_name"] or "Unknown")[:24]
        overrides = ",".join(r["override_flags"]) if r["override_flags"] else "-"
        print(
            f"  {sid_short:<18s} {biz:<25s} {r['duration']:>5.0f} "
            f"{r['classifier_type']:<20s} {r['confidence']:>5.2f} "
            f"{r['cdc_outcome']:<16s} {overrides}"
        )

    if len(edges) > max_show:
        print(f"  ... and {len(edges) - max_show} more")


def print_mismatches(results, max_show=20):
    """Print calls where classifier disagrees with CDC outcome."""
    HUMAN_OUTCOMES = {"kept_engaged", "warm_transfer", "appointment_set", "sale_closed",
                      "callback_scheduled", "interested", "information_sent"}
    MACHINE_OUTCOMES = {"voicemail_ivr", "ivr_transcript_kill", "ivr_timeout_kill",
                        "silence_kill", "air_call_kill", "max_duration_kill", "dead_end_exit"}

    mismatches = []
    for r in results:
        cdc = r["cdc_outcome"]
        clf = r["classifier_type"]

        if cdc in HUMAN_OUTCOMES and clf not in ("human_conversation", "ambiguous_human_like"):
            mismatches.append((r, "CDC=human, clf=machine"))
        elif cdc in MACHINE_OUTCOMES and clf in ("human_conversation",):
            mismatches.append((r, "CDC=machine, clf=human"))

    if not mismatches:
        print(f"\n[OK] No mismatches between classifier and CDC outcomes")
        return

    print(f"\n{'=' * 70}")
    print(f"MISMATCHES ({len(mismatches)} calls)")
    print(f"{'=' * 70}")

    for r, reason in mismatches[:max_show]:
        sid_short = r["call_sid"][:16] + ".."
        biz = (r["business_name"] or "Unknown")[:24]
        print(
            f"  {reason:<30s} | {sid_short} | {biz:<24s} | "
            f"dur={r['duration']:.0f}s | words={r['merchant_words']} | "
            f"turns={r['turns']} | clf={r['classifier_type']} | "
            f"cdc={r['cdc_outcome']}"
        )


def main():
    limit = 50
    all_calls = "--all" in sys.argv
    edges_only = "--edges" in sys.argv

    for i, arg in enumerate(sys.argv):
        if arg == "--last" and i + 1 < len(sys.argv):
            limit = int(sys.argv[i + 1])

    # Load config
    config_loader = ClassifierConfigLoader()
    config = config_loader.get_or_default(CallTypeClassifier.DEFAULT_CONFIG)
    classifier = CallTypeClassifier(config)
    aggregator = CallFeatureAggregator()

    print("=" * 70)
    print("CALL TYPE CLASSIFIER AUDIT")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Mode: {'ALL calls' if all_calls else f'Last {limit} calls'}")
    print("=" * 70)

    calls, turns_by_call = load_calls(limit=limit, all_calls=all_calls)
    if not calls:
        print("No calls found in CDC.")
        return

    print(f"Loaded {len(calls)} calls, {sum(len(t) for t in turns_by_call.values())} turns")

    results = classify_all(calls, turns_by_call, classifier, aggregator)

    if edges_only:
        print_edge_cases(results, max_show=50)
    else:
        print_distribution(results)
        print_confidence_bands(results)
        print_overrides(results)
        print_mismatches(results)

        print_calls_by_type(results, "human_conversation")
        print_calls_by_type(results, "voicemail")
        print_calls_by_type(results, "ivr")
        print_calls_by_type(results, "ambiguous_human_like")
        print_calls_by_type(results, "ambiguous_machine_like")

        print_edge_cases(results)

    print(f"\n{'=' * 70}")
    print("AUDIT COMPLETE")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
