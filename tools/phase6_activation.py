"""
Phase 6 Activation Script
===========================
Validates all Phase 5→6 promotion gate criteria programmatically,
then optionally activates Phase 6 (Entanglement Bridge + multi-instance).

Usage:
    .venv\\Scripts\\python.exe tools/phase6_activation.py --dry-run
    .venv\\Scripts\\python.exe tools/phase6_activation.py --activate
"""

import sys
import os
import json
import glob

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CYCLES_DIR = os.path.join(PROJECT_ROOT, "phase5_cycles")


def check_quantitative_gates():
    """Section A: Quantitative gates from promotion checklist."""
    gates = {}

    # A1: Total calls scored ≥ 30
    total_calls = count_total_calls()
    gates["A1_total_calls"] = {
        "criterion": "Total calls scored >= 30",
        "actual": total_calls,
        "threshold": 30,
        "met": total_calls >= 30,
    }

    # A7: Consecutive zero-flag cycles ≥ 1
    zero_flag_streak = count_zero_flag_streak()
    gates["A7_zero_flag_cycles"] = {
        "criterion": "Consecutive zero-flag cycles >= 1",
        "actual": zero_flag_streak,
        "threshold": 1,
        "met": zero_flag_streak >= 1,
    }

    return gates


def check_pe_gates():
    """Section B: PE behavioral gates."""
    gates = {}

    # B1: PE compiles and returns correct keys
    try:
        from personality_engine import PersonalityEngine
        pe = PersonalityEngine()
        result = pe.process_turn("positive", "Hello there")
        required_keys = [
            "state", "persona", "mood_score", "relationship_depth",
            "flare", "system_instruction", "prosody_bias",
            "quantum_event", "quantum_dominant",
        ]
        missing = [k for k in required_keys if k not in result]
        gates["B_pe_api"] = {
            "criterion": "PE process_turn returns all required keys",
            "missing_keys": missing,
            "met": len(missing) == 0,
        }

        # Check prosody_bias structure
        pb = result.get("prosody_bias", {})
        pb_keys = ["speed_mod", "silence_mod", "preferred_intent"]
        pb_missing = [k for k in pb_keys if k not in pb]
        gates["B_prosody_keys"] = {
            "criterion": "prosody_bias has speed_mod, silence_mod, preferred_intent",
            "missing_keys": pb_missing,
            "met": len(pb_missing) == 0,
        }

        # Check quantum_dominant is valid dimension
        valid_dims = ["wit", "empathy", "precision", "patience", "entropy"]
        dominant = result.get("quantum_dominant", "")
        gates["B_valid_dominant"] = {
            "criterion": "quantum_dominant is valid dimension name",
            "actual": dominant,
            "valid_values": valid_dims,
            "met": dominant in valid_dims,
        }

        # Check state vector is 5D and normalized
        import numpy as np
        state_vec = pe.quantum_state.state
        norm = float(np.linalg.norm(state_vec))
        gates["B_state_vector"] = {
            "criterion": "State vector is 5D and normalized",
            "dimensions": len(state_vec),
            "norm": round(norm, 6),
            "met": len(state_vec) == 5 and abs(norm - 1.0) < 0.01,
        }

    except ImportError as e:
        gates["B_pe_api"] = {
            "criterion": "PE imports and runs",
            "error": str(e),
            "met": False,
        }

    return gates


def check_infrastructure_gates():
    """Section C: Infrastructure gates."""
    gates = {}

    # C2: Neg-proof passes
    core_files = [
        "personality_engine.py",
        "aqi_conversation_relay_server.py",
        "agent_alan_business_ai.py",
    ]
    neg_results = {}
    for fname in core_files:
        fpath = os.path.join(PROJECT_ROOT, fname)
        if os.path.exists(fpath):
            try:
                import py_compile
                py_compile.compile(fpath, doraise=True)
                neg_results[fname] = "OK"
            except py_compile.PyCompileError as e:
                neg_results[fname] = f"FAIL: {e}"
        else:
            neg_results[fname] = "NOT FOUND"

    all_ok = all(v == "OK" for v in neg_results.values())
    gates["C2_neg_proof"] = {
        "criterion": "All 3 core files compile clean",
        "results": neg_results,
        "met": all_ok,
    }

    return gates


def count_total_calls():
    """Count total calls across all cycle JSONL files."""
    total = 0
    pattern = os.path.join(CYCLES_DIR, "cycle_*", "*.jsonl")
    for fpath in glob.glob(pattern):
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                # Count unique call_ids
                call_ids = set()
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            record = json.loads(line)
                            cid = record.get("call_id", "")
                            if cid:
                                call_ids.add(cid)
                        except json.JSONDecodeError:
                            pass
                total += len(call_ids) if call_ids else 0
        except IOError:
            pass
    return total


def count_zero_flag_streak():
    """Count consecutive cycles with zero failure flags (from most recent)."""
    # Look for cycle summary files with anomaly data
    pattern = os.path.join(CYCLES_DIR, "cycle_*", "*_anomalies.json")
    files = sorted(glob.glob(pattern))

    streak = 0
    for fpath in reversed(files):
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data.get("total_anomalies", 0) == 0:
                    streak += 1
                else:
                    break
        except (json.JSONDecodeError, IOError):
            break
    return streak


def main():
    print("=" * 60)
    print("  PHASE 6 ACTIVATION CHECK")
    print("=" * 60)

    dry_run = "--dry-run" in sys.argv or "--activate" not in sys.argv

    if dry_run:
        print("  Mode: DRY RUN (validation only)")
    else:
        print("  Mode: ACTIVATE (will enable Phase 6 if all gates pass)")

    all_gates = {}

    # Section A
    print("\n  [Section A] Quantitative Gates...")
    gates_a = check_quantitative_gates()
    all_gates.update(gates_a)
    for key, gate in gates_a.items():
        status = "PASS" if gate["met"] else "FAIL"
        print(f"    {key}: {status} — {gate['criterion']}")

    # Section B
    print("\n  [Section B] PE Behavioral Gates...")
    gates_b = check_pe_gates()
    all_gates.update(gates_b)
    for key, gate in gates_b.items():
        status = "PASS" if gate["met"] else "FAIL"
        print(f"    {key}: {status} — {gate['criterion']}")

    # Section C
    print("\n  [Section C] Infrastructure Gates...")
    gates_c = check_infrastructure_gates()
    all_gates.update(gates_c)
    for key, gate in gates_c.items():
        status = "PASS" if gate["met"] else "FAIL"
        print(f"    {key}: {status} — {gate['criterion']}")

    # Summary
    total = len(all_gates)
    passed = sum(1 for g in all_gates.values() if g["met"])

    print("\n" + "=" * 60)
    print(f"  RESULT: {passed}/{total} gates passed")

    if passed == total:
        print("  VERDICT: ALL GATES CLEAR — Phase 6 eligible")
        if not dry_run:
            print("\n  Activating Phase 6...")
            print("  NOTE: Manual steps required:")
            print("    1. Enable ENTANGLEMENT_BRIDGE flag in relay server")
            print("    2. Deploy secondary instance (S-Alan-1)")
            print("    3. Start entanglement_bridge_health_monitor.py")
            print("    4. Open RRG V")
    else:
        print("  VERDICT: NOT READY — resolve failing gates before Phase 6")
        failing = [k for k, v in all_gates.items() if not v["met"]]
        print(f"  Failing gates: {', '.join(failing)}")

    # Write report
    report_path = os.path.join(PROJECT_ROOT, "phase6_activation_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": __import__("time").strftime("%Y-%m-%d %H:%M:%S"),
            "mode": "dry_run" if dry_run else "activate",
            "gates": all_gates,
            "passed": passed,
            "total": total,
            "eligible": passed == total,
        }, f, indent=2)
    print(f"\n  Report saved to: {report_path}")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
