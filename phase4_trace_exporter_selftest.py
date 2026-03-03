"""
Phase 4 Trace Exporter — Self-Test
====================================
Verifies the exporter module in isolation:
  1. init_trace → creates skeleton
  2. append_turn → accumulates turns + trajectories
  3. finalize_trace → writes canonical JSONL
  4. Trajectory builders work independently
  5. JSONL output matches Phase4CallTrace schema
  6. Thread safety (basic)
  7. Edge cases (empty call, missing data, double-finalize)

Run: .venv\\Scripts\\python.exe phase4_trace_exporter_selftest.py
"""

import json
import os
import sys
import tempfile
import shutil
from datetime import datetime, timezone

# ─── Ensure we can import the exporter ───
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from phase4_trace_exporter import Phase4TraceExporter, _get_prompt_layers_dict

# ─── Test infrastructure ───
_pass = 0
_fail = 0

def check(label, condition):
    global _pass, _fail
    if condition:
        _pass += 1
        print(f"  [PASS] {label}")
    else:
        _fail += 1
        print(f"  [FAIL] {label}")


def main():
    global _pass, _fail

    # Create temp dir for output
    tmp_dir = tempfile.mkdtemp(prefix="p4_exporter_test_")
    tmp_file = os.path.join(tmp_dir, "traces.jsonl")

    try:
        # ─── 1. Prompt Layer Builder ─────────────────────────
        print("\n=== 1. Prompt Layer Builder ===")

        layers_fast = _get_prompt_layers_dict(1)
        check("FAST_PATH has Identity active", layers_fast["Identity"] == "active")
        check("FAST_PATH has Ethics inactive", layers_fast["Ethics"] == "inactive")
        check("FAST_PATH has Mission active", layers_fast["Mission"] == "active")

        layers_mid = _get_prompt_layers_dict(5)
        check("MIDWEIGHT has Identity active", layers_mid["Identity"] == "active")
        check("MIDWEIGHT has Ethics active", layers_mid["Ethics"] == "active")
        check("MIDWEIGHT has Knowledge inactive", layers_mid["Knowledge"] == "inactive")

        layers_full = _get_prompt_layers_dict(10)
        check("FULL has all 6 active", all(v == "active" for v in layers_full.values()))

        layers_explicit = _get_prompt_layers_dict(0, ["Identity", "Mission"])
        check("Explicit layers: Identity active", layers_explicit["Identity"] == "active")
        check("Explicit layers: Ethics inactive", layers_explicit["Ethics"] == "inactive")
        check("Explicit layers: Mission active", layers_explicit["Mission"] == "active")

        # ─── 2. Basic Lifecycle ──────────────────────────────
        print("\n=== 2. Basic Lifecycle ===")

        exporter = Phase4TraceExporter(output_dir=tmp_dir, output_file=tmp_file)
        check("Exporter created", exporter is not None)
        check("No active traces", exporter.active_traces == 0)
        check("Zero finalized", exporter.finalized_count == 0)

        # init_trace
        start = datetime(2025, 6, 15, 10, 0, 0, tzinfo=timezone.utc)
        exporter.init_trace("CALL_001", {
            "prospect_name": "John Doe",
            "business_name": "Acme Corp",
            "prospect_phone": "+15551234567",
            "call_type": "sales",
        }, start)

        check("One active trace", exporter.active_traces == 1)
        check("has_trace CALL_001", exporter.has_trace("CALL_001"))
        check("active call IDs", exporter.get_active_call_ids() == ["CALL_001"])

        # append_turn — turn 0 (OPENING)
        exporter.append_turn("CALL_001", {
            "fsm_state": "OPENING",
            "fsm_prev_state": "OPENING",
            "fsm_event": "merchant_speaks",
            "organism_level": 1,
            "telephony_state": "Excellent",
            "turn_count": 0,
            "user_text": "Hello?",
            "response_text": "Hi there! This is Alan.",
            "aqi_layers": ["Identity", "Personality", "Mission"],
        })

        # append_turn — turn 1 (DISCOVERY)
        exporter.append_turn("CALL_001", {
            "fsm_state": "DISCOVERY",
            "fsm_prev_state": "OPENING",
            "fsm_event": "merchant_speaks",
            "organism_level": 1,
            "telephony_state": "Excellent",
            "turn_count": 1,
            "user_text": "What's this about?",
            "response_text": "I'm calling about your credit card processing.",
        })

        # append_turn — turn 2 (VALUE)
        exporter.append_turn("CALL_001", {
            "fsm_state": "VALUE",
            "fsm_prev_state": "DISCOVERY",
            "fsm_event": "merchant_speaks",
            "organism_level": 1,
            "telephony_state": "Good",
            "turn_count": 2,
            "user_text": "Okay, tell me more.",
            "response_text": "We can save you up to 40% on processing fees.",
        })

        # append_turn — turn 3 (OBJECTION)
        exporter.append_turn("CALL_001", {
            "fsm_state": "OBJECTION",
            "fsm_prev_state": "VALUE",
            "fsm_event": "objection_detected",
            "organism_level": 2,
            "telephony_state": "Good",
            "turn_count": 3,
            "user_text": "I'm not sure, we have a contract.",
            "response_text": "I completely understand. Most of our merchants had contracts too.",
            "live_objection_type": "contract_objection",
            "master_closer_state": {"endgame_state": "not_ready", "trajectory": "warming"},
        })

        # append_turn — turn 4 (CLOSE)
        exporter.append_turn("CALL_001", {
            "fsm_state": "CLOSE",
            "fsm_prev_state": "OBJECTION",
            "fsm_event": "merchant_speaks",
            "organism_level": 1,
            "telephony_state": "Good",
            "turn_count": 4,
            "user_text": "Alright, what would I need to do?",
            "response_text": "Great! Let me schedule a quick 10-minute review.",
            "master_closer_state": {"endgame_state": "ready", "trajectory": "warming"},
        })

        check("Still one active trace", exporter.active_traces == 1)

        # finalize_trace
        result = exporter.finalize_trace("CALL_001", {
            "fsm_state": "CLOSE",
            "exit_reason": "appointment_set",
            "end_time": datetime(2025, 6, 15, 10, 5, 30, tzinfo=timezone.utc),
            "master_closer_state": {"endgame_state": "ready", "trajectory": "warming"},
        })

        check("finalize returns dict", isinstance(result, dict))
        check("No active traces after finalize", exporter.active_traces == 0)
        check("Finalized count is 1", exporter.finalized_count == 1)

        # ─── 3. Verify Canonical Shape ───────────────────────
        print("\n=== 3. Canonical Shape Verification ===")

        check("has call_id", result["call_id"] == "CALL_001")
        check("has metadata", "metadata" in result)
        check("has turns", "turns" in result)
        check("has final", "final" in result)

        meta = result["metadata"]
        check("metadata.timestamp_start", "2025-06-15" in meta["timestamp_start"])
        check("metadata.timestamp_end", "2025-06-15" in meta["timestamp_end"])
        check("metadata.merchant_profile", meta["merchant_profile"]["business_type"] == "Acme Corp")

        check("5 turns", len(result["turns"]) == 5)

        # Check turn 0
        t0 = result["turns"][0]
        check("turn_0.turn_index == 0", t0["turn_index"] == 0)
        check("turn_0.fsm_state == OPENING", t0["fsm_state"] == "OPENING")
        check("turn_0.fsm_prev_state", t0["fsm_prev_state"] == "OPENING")
        check("turn_0.fsm_event", t0["fsm_event"] == "merchant_speaks")
        check("turn_0.prompt_layers has 6 keys", len(t0["prompt_layers"]) == 6)
        check("turn_0.prompt_layers.Identity active", t0["prompt_layers"]["Identity"] == "active")
        check("turn_0.health_snapshot.organism_level", t0["health_snapshot"]["organism_level"] == 1)
        check("turn_0.health_snapshot.telephony_state", t0["health_snapshot"]["telephony_state"] == "Excellent")
        check("turn_0.context.close_attempt False", t0["context"]["close_attempt"] is False)

        # Check turn 3 (objection)
        t3 = result["turns"][3]
        check("turn_3.fsm_state == OBJECTION", t3["fsm_state"] == "OBJECTION")
        check("turn_3.context.objection_branch", t3["context"]["objection_branch"] == "contract_objection")
        check("turn_3.health_snapshot.organism_level == 2", t3["health_snapshot"]["organism_level"] == 2)

        # Check turn 4 (close)
        t4 = result["turns"][4]
        check("turn_4.fsm_state == CLOSE", t4["fsm_state"] == "CLOSE")
        check("turn_4.context.close_attempt True", t4["context"]["close_attempt"] is True)
        check("turn_4.context.mission_escalation True", t4["context"]["mission_escalation"] is True)

        # ─── 4. Final Block ──────────────────────────────────
        print("\n=== 4. Final Block ===")

        final = result["final"]
        check("final.fsm_state == CLOSE", final["fsm_state"] == "CLOSE")
        check("final.exit_reason == appointment_set", final["exit_reason"] == "appointment_set")

        # Health trajectory
        ht = final["health_trajectory"]
        check("health_trajectory has 5 entries", len(ht) == 5)
        check("ht[0] organism_level == 1", ht[0]["organism_level"] == 1)
        check("ht[0] telephony_state == Excellent", ht[0]["telephony_state"] == "Excellent")
        check("ht[2] telephony_state == Good", ht[2]["telephony_state"] == "Good")
        check("ht[3] organism_level == 2", ht[3]["organism_level"] == 2)

        # Telephony trajectory
        tt = final["telephony_trajectory"]
        check("telephony_trajectory has 5 entries", len(tt) == 5)
        check("tt[0] telephony_state == Excellent", tt[0]["telephony_state"] == "Excellent")
        check("tt[2] telephony_state == Good", tt[2]["telephony_state"] == "Good")

        # Outcome vector
        ov = final["outcome_vector"]
        check("ov.appointment_set True", ov["appointment_set"] is True)
        check("ov.soft_decline False", ov["soft_decline"] is False)
        check("ov.hard_decline False", ov["hard_decline"] is False)
        check("ov.telephony_unusable False", ov["telephony_unusable"] is False)
        check("ov.organism_unfit False", ov["organism_unfit"] is False)

        # ─── 5. JSONL Output ─────────────────────────────────
        print("\n=== 5. JSONL Output ===")

        check("JSONL file exists", os.path.exists(tmp_file))
        with open(tmp_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
        check("JSONL has 1 line", len(lines) == 1)
        parsed = json.loads(lines[0])
        check("JSONL call_id matches", parsed["call_id"] == "CALL_001")
        check("JSONL turns count matches", len(parsed["turns"]) == 5)
        check("JSONL final.exit_reason matches", parsed["final"]["exit_reason"] == "appointment_set")

        # ─── 6. Static Trajectory Builders ───────────────────
        print("\n=== 6. Static Trajectory Builders ===")

        h_traj = Phase4TraceExporter.build_health_trajectory(result["turns"])
        check("build_health_trajectory returns 5 entries", len(h_traj) == 5)
        check("h_traj[3].organism_level == 2", h_traj[3]["organism_level"] == 2)

        t_traj = Phase4TraceExporter.build_telephony_trajectory(result["turns"])
        check("build_telephony_trajectory returns 5 entries", len(t_traj) == 5)
        check("t_traj[1].telephony_state == Excellent", t_traj[1]["telephony_state"] == "Excellent")

        # ─── 7. Edge Cases ───────────────────────────────────
        print("\n=== 7. Edge Cases ===")

        # Empty call (init + immediate finalize, no turns)
        exporter.init_trace("EMPTY_CALL", {}, datetime.now(timezone.utc))
        empty_result = exporter.finalize_trace("EMPTY_CALL", {
            "exit_reason": "caller_hangup",
        })
        check("Empty call finalized", empty_result is not None)
        check("Empty call has 0 turns", len(empty_result["turns"]) == 0)
        check("Empty call health_trajectory empty", len(empty_result["final"]["health_trajectory"]) == 0)
        check("Empty call exit = caller_hangup", empty_result["final"]["exit_reason"] == "caller_hangup")
        check("Empty call soft_decline True", empty_result["final"]["outcome_vector"]["soft_decline"] is True)

        # Double finalize (should return None second time)
        double_result = exporter.finalize_trace("EMPTY_CALL", {})
        check("Double finalize returns None", double_result is None)

        # Append to non-existent call (should not crash)
        exporter.append_turn("GHOST_CALL", {"fsm_state": "OPENING"})
        check("Append to ghost call — no crash", True)

        # init_trace with empty call_id (should be skipped)
        exporter.init_trace("", {})
        check("Empty call_id — no active trace", not exporter.has_trace(""))

        # Finalized count check
        check("Total finalized == 2", exporter.finalized_count == 2)

        # Check JSONL has 2 lines now
        with open(tmp_file, "r", encoding="utf-8") as f:
            lines2 = f.readlines()
        check("JSONL has 2 lines", len(lines2) == 2)

        # ─── 8. Degraded Health Call ─────────────────────────
        print("\n=== 8. Degraded Health Call ===")

        exporter.init_trace("DEGRADED_001", {
            "business_name": "Bad Signal Inc",
        }, datetime.now(timezone.utc))

        for i in range(6):
            org_level = min(1 + i, 4)
            tel_states = ["Excellent", "Good", "Good", "Degraded", "Degraded", "Unusable"]
            exporter.append_turn("DEGRADED_001", {
                "fsm_state": "DISCOVERY" if i < 3 else "EXIT",
                "fsm_prev_state": "OPENING" if i == 0 else ("DISCOVERY" if i <= 3 else "EXIT"),
                "fsm_event": "degrade" if i >= 3 else "merchant_speaks",
                "organism_level": org_level,
                "telephony_state": tel_states[i],
                "turn_count": i,
                "user_text": "..." if i < 5 else "",
                "response_text": "..." if i < 5 else "",
            })

        deg_result = exporter.finalize_trace("DEGRADED_001", {
            "fsm_state": "EXIT",
            "exit_reason": "organism_unfit",
        })

        check("Degraded call finalized", deg_result is not None)
        check("Degraded has 6 turns", len(deg_result["turns"]) == 6)
        check("Health trajectory shows degradation", deg_result["final"]["health_trajectory"][-1]["organism_level"] == 4)
        check("Telephony trajectory shows Unusable", deg_result["final"]["telephony_trajectory"][-1]["telephony_state"] == "Unusable")
        check("Outcome: organism_unfit True", deg_result["final"]["outcome_vector"]["organism_unfit"] is True)
        check("Outcome: appointment_set False", deg_result["final"]["outcome_vector"]["appointment_set"] is False)

        # ─── 9. Phase 4 Schema Compliance ────────────────────
        print("\n=== 9. Schema Compliance ===")

        # Verify all required fields present
        for field in ["call_id", "metadata", "turns", "final"]:
            check(f"Top-level field: {field}", field in result)

        for field in ["timestamp_start", "timestamp_end", "merchant_profile"]:
            check(f"metadata.{field}", field in result["metadata"])

        for field in ["fsm_state", "exit_reason", "health_trajectory", "telephony_trajectory", "outcome_vector"]:
            check(f"final.{field}", field in result["final"])

        t0 = result["turns"][0]
        for field in ["turn_index", "fsm_prev_state", "fsm_event", "fsm_state", "prompt_layers", "context", "health_snapshot"]:
            check(f"turn.{field}", field in t0)

        for field in ["Identity", "Ethics", "Personality", "Knowledge", "Mission", "Output"]:
            check(f"prompt_layers.{field}", field in t0["prompt_layers"])

        for field in ["mission_escalation", "objection_branch", "close_attempt", "output_complexity", "supervisor_flags"]:
            check(f"context.{field}", field in t0["context"])

        for field in ["organism_level", "telephony_state"]:
            check(f"health_snapshot.{field}", field in t0["health_snapshot"])

        for field in ["appointment_set", "soft_decline", "hard_decline", "telephony_unusable", "organism_unfit"]:
            check(f"outcome_vector.{field}", field in result["final"]["outcome_vector"])

    finally:
        # Cleanup
        shutil.rmtree(tmp_dir, ignore_errors=True)

    # ─── Summary ─────────────────────────────────────────────
    total = _pass + _fail
    print(f"\n{'='*60}")
    print(f"Phase 4 Trace Exporter Self-Test: {_pass}/{total} PASS")
    if _fail:
        print(f"  {_fail} FAILURES")
    else:
        print("  ALL PASS — Exporter is canonical-compliant")
    print(f"{'='*60}")

    return 0 if _fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
