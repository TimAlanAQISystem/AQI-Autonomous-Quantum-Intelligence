"""
Phase 5 Test Harness — Prosody + Quantum Stress Test
=====================================================
Feeds synthetic turn sequences through the PersonalityEngine,
validates prosody bias bands, quantum state evolution, and
non-commutativity. Writes results to phase5_test_output.jsonl.

Usage:
    .venv\\Scripts\\python.exe tools/test_harness_phase5.py
"""

import sys
import os
import json
import time

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from personality_engine import PersonalityEngine
import numpy as np


# ─── CANONICAL COLOR MAP ──────────────────────────────────────────────────
MODE_COLORS = {
    "wit":       "#E86A5F",
    "empathy":   "#F5A623",
    "precision": "#4A90E2",
    "patience":  "#7B4F9D",
    "entropy":   "#50C878",
}

# ─── SYNTHETIC PROMPT SETS ────────────────────────────────────────────────

SET_A_EMOTION_SHIFTS = [
    ("positive", "I'm excited to get started."),
    ("negative", "That's disappointing."),
    ("negative", "I'm not sure this is worth my time."),
    ("positive", "Actually, tell me more."),
    ("neutral",  "I'll think about it."),
]

SET_B_TEMPO_EXTREMES = [
    ("neutral",  "Wait, what?"),
    ("positive", "How soon?"),
    ("neutral",  "Well, considering the various factors involved, including the "
                 "overall market conditions, seasonal trends, and the specific "
                 "needs of our customer base, I would say that we need to think "
                 "carefully about this before committing."),
    ("positive", "OK, let's do it."),
]

SET_C_POLITENESS_VS_FIRMNESS = [
    ("positive", "I completely understand, and here's what I can do."),
    ("neutral",  "I hear you, but I disagree for this reason."),
    ("negative", "No, that won't work for us."),
    ("positive", "Fair enough, let's find a middle ground."),
]

# ─── ACCEPTANCE BANDS ──────────────────────────────────────────────────────

SPEED_MOD_MIN = -0.08
SPEED_MOD_MAX = 0.08
SILENCE_MOD_MIN = -3
SILENCE_MOD_MAX = 3
ENTROPY_MIN = 0.3
ENTROPY_MAX = 1.7


def run_sequence(pe, sequence, label):
    """Run a turn sequence through PE and collect results."""
    results = []
    for i, (sentiment, text) in enumerate(sequence):
        state_before = pe.quantum_state.state.tolist()
        result = pe.process_turn(sentiment, text)
        state_after = pe.quantum_state.state.tolist()

        record = {
            "sequence": label,
            "turn": i,
            "sentiment": sentiment,
            "user_text": text,
            "state_vector_before": state_before,
            "state_vector_after": state_after,
            "quantum_event": result["quantum_event"],
            "quantum_dominant": result["quantum_dominant"],
            "quantum_dominant_prob": result["quantum_dominant_prob"],
            "quantum_entropy": result["quantum_entropy"],
            "quantum_evolutions": result["quantum_evolutions"],
            "persona": result["persona"],
            "mood_score": result["mood_score"],
            "relationship_depth": result["relationship_depth"],
            "flare": result["flare"],
            "prosody_bias": result["prosody_bias"],
        }
        results.append(record)
    return results


def validate_prosody(records):
    """Check prosody bias stays within acceptance bands."""
    violations = []
    for r in records:
        pb = r["prosody_bias"]
        speed = pb.get("speed_mod", 0)
        silence = pb.get("silence_mod", 0)
        if speed < SPEED_MOD_MIN or speed > SPEED_MOD_MAX:
            violations.append(
                f"[{r['sequence']}] Turn {r['turn']}: speed_mod={speed:.4f} "
                f"outside [{SPEED_MOD_MIN}, {SPEED_MOD_MAX}]"
            )
        if silence < SILENCE_MOD_MIN or silence > SILENCE_MOD_MAX:
            violations.append(
                f"[{r['sequence']}] Turn {r['turn']}: silence_mod={silence} "
                f"outside [{SILENCE_MOD_MIN}, {SILENCE_MOD_MAX}]"
            )
    return violations


def validate_entropy(records):
    """Check quantum entropy stays in healthy range."""
    violations = []
    for r in records:
        ent = r["quantum_entropy"]
        if ent < ENTROPY_MIN or ent > ENTROPY_MAX:
            violations.append(
                f"[{r['sequence']}] Turn {r['turn']}: entropy={ent:.3f} "
                f"outside [{ENTROPY_MIN}, {ENTROPY_MAX}]"
            )
    return violations


def test_non_commutativity():
    """
    Verify that different operator orderings produce different states.
    This is the core mathematical invariant of the quantum layer.
    """
    pe_forward = PersonalityEngine()
    pe_reverse = PersonalityEngine()

    forward_turns = [
        ("positive", "Great news!"),
        ("negative", "That's terrible."),
        ("neutral",  "OK."),
    ]
    reverse_turns = list(reversed(forward_turns))

    for sentiment, text in forward_turns:
        pe_forward.process_turn(sentiment, text)
    for sentiment, text in reverse_turns:
        pe_reverse.process_turn(sentiment, text)

    state_fwd = pe_forward.quantum_state.state
    state_rev = pe_reverse.quantum_state.state
    diff = np.linalg.norm(state_fwd - state_rev)

    return {
        "state_forward": state_fwd.tolist(),
        "state_reverse": state_rev.tolist(),
        "l2_difference": float(diff),
        "non_commutative": diff > 1e-6,
    }


def test_state_normalization(pe):
    """Verify state vector remains normalized after processing."""
    norm = float(np.linalg.norm(pe.quantum_state.state))
    return {
        "norm": norm,
        "normalized": abs(norm - 1.0) < 0.001,
    }


def test_dimension_count(pe):
    """Verify state vector is 5-dimensional."""
    dim = len(pe.quantum_state.state)
    return {
        "dimensions": dim,
        "correct": dim == 5,
    }


def test_return_keys():
    """Verify process_turn returns all expected keys."""
    pe = PersonalityEngine()
    result = pe.process_turn("positive", "Hello")
    expected_keys = [
        "state", "persona", "mood_score", "relationship_depth",
        "flare", "system_instruction", "prosody_bias",
        "turns_processed", "quantum_event", "quantum_dominant",
        "quantum_dominant_prob", "quantum_entropy", "quantum_evolutions",
    ]
    missing = [k for k in expected_keys if k not in result]
    return {
        "expected_keys": expected_keys,
        "missing_keys": missing,
        "pass": len(missing) == 0,
    }


def main():
    print("=" * 60)
    print("  PHASE 5 TEST HARNESS")
    print("  Prosody + Quantum Stress Test")
    print("=" * 60)

    all_records = []
    all_violations = []
    test_results = {}

    # ── Test 1: Return keys ──────────────────────────────────────────
    print("\n[TEST 1] Verifying process_turn() return keys...")
    keys_result = test_return_keys()
    test_results["return_keys"] = keys_result
    status = "PASS" if keys_result["pass"] else "FAIL"
    print(f"  Result: {status}")
    if keys_result["missing_keys"]:
        print(f"  Missing: {keys_result['missing_keys']}")

    # ── Test 2: Set A — Emotion shifts ───────────────────────────────
    print("\n[TEST 2] Running Set A — Emotion Shifts...")
    pe_a = PersonalityEngine()
    records_a = run_sequence(pe_a, SET_A_EMOTION_SHIFTS, "SetA_EmotionShifts")
    all_records.extend(records_a)
    print(f"  Turns processed: {len(records_a)}")
    print(f"  Final dominant: {records_a[-1]['quantum_dominant']}")
    print(f"  Final persona: {records_a[-1]['persona']}")

    # ── Test 3: Set B — Tempo extremes ───────────────────────────────
    print("\n[TEST 3] Running Set B — Tempo Extremes...")
    pe_b = PersonalityEngine()
    records_b = run_sequence(pe_b, SET_B_TEMPO_EXTREMES, "SetB_TempoExtremes")
    all_records.extend(records_b)
    print(f"  Turns processed: {len(records_b)}")
    print(f"  Final dominant: {records_b[-1]['quantum_dominant']}")
    print(f"  Final persona: {records_b[-1]['persona']}")

    # ── Test 4: Set C — Politeness vs Firmness ───────────────────────
    print("\n[TEST 4] Running Set C — Politeness vs Firmness...")
    pe_c = PersonalityEngine()
    records_c = run_sequence(pe_c, SET_C_POLITENESS_VS_FIRMNESS, "SetC_Politeness")
    all_records.extend(records_c)
    print(f"  Turns processed: {len(records_c)}")
    print(f"  Final dominant: {records_c[-1]['quantum_dominant']}")
    print(f"  Final persona: {records_c[-1]['persona']}")

    # ── Test 5: Prosody band validation ──────────────────────────────
    print("\n[TEST 5] Validating prosody bands...")
    prosody_violations = validate_prosody(all_records)
    all_violations.extend(prosody_violations)
    if prosody_violations:
        print(f"  VIOLATIONS: {len(prosody_violations)}")
        for v in prosody_violations:
            print(f"    {v}")
    else:
        print("  All prosody values within acceptance bands. PASS")

    # ── Test 6: Entropy validation ───────────────────────────────────
    print("\n[TEST 6] Validating quantum entropy range...")
    entropy_violations = validate_entropy(all_records)
    all_violations.extend(entropy_violations)
    if entropy_violations:
        print(f"  VIOLATIONS: {len(entropy_violations)}")
        for v in entropy_violations:
            print(f"    {v}")
    else:
        print("  All entropy values within range. PASS")

    # ── Test 7: Non-commutativity ────────────────────────────────────
    print("\n[TEST 7] Testing non-commutativity...")
    nc_result = test_non_commutativity()
    test_results["non_commutativity"] = nc_result
    status = "PASS" if nc_result["non_commutative"] else "FAIL"
    print(f"  L2 difference: {nc_result['l2_difference']:.6f}")
    print(f"  Non-commutative: {status}")

    # ── Test 8: State normalization ──────────────────────────────────
    print("\n[TEST 8] Verifying state normalization...")
    norm_result = test_state_normalization(pe_a)
    test_results["normalization"] = norm_result
    status = "PASS" if norm_result["normalized"] else "FAIL"
    print(f"  Norm: {norm_result['norm']:.6f}")
    print(f"  Normalized: {status}")

    # ── Test 9: Dimension count ──────────────────────────────────────
    print("\n[TEST 9] Verifying state vector dimensions...")
    dim_result = test_dimension_count(pe_a)
    test_results["dimensions"] = dim_result
    status = "PASS" if dim_result["correct"] else "FAIL"
    print(f"  Dimensions: {dim_result['dimensions']}")
    print(f"  Correct: {status}")

    # ── Write output ─────────────────────────────────────────────────
    output_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "phase5_test_output.jsonl"
    )
    with open(output_path, "w", encoding="utf-8") as f:
        for record in all_records:
            f.write(json.dumps(record) + "\n")
    print(f"\n  Output written to: {output_path}")
    print(f"  Total records: {len(all_records)}")

    # ── Summary ──────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)

    total_tests = 9
    passed = 0

    checks = [
        ("Return keys", keys_result["pass"]),
        ("Set A runs", len(records_a) == len(SET_A_EMOTION_SHIFTS)),
        ("Set B runs", len(records_b) == len(SET_B_TEMPO_EXTREMES)),
        ("Set C runs", len(records_c) == len(SET_C_POLITENESS_VS_FIRMNESS)),
        ("Prosody bands", len(prosody_violations) == 0),
        ("Entropy range", len(entropy_violations) == 0),
        ("Non-commutativity", nc_result["non_commutative"]),
        ("Normalization", norm_result["normalized"]),
        ("Dimensions", dim_result["correct"]),
    ]

    for name, result in checks:
        status = "PASS" if result else "FAIL"
        symbol = "✓" if result else "✗"
        print(f"  {symbol} {name}: {status}")
        if result:
            passed += 1

    print(f"\n  Result: {passed}/{total_tests} tests passed")
    if passed == total_tests:
        print("  STATUS: ALL CLEAR — Phase 5 harness green.")
    else:
        print("  STATUS: FAILURES DETECTED — review before proceeding.")

    return 0 if passed == total_tests else 1


if __name__ == "__main__":
    sys.exit(main())
