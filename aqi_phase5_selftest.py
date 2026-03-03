"""
AQI Phase 5 — Comprehensive Self-Test
========================================
Proves the entire Phase 5 stack works end-to-end:
  Tagging Engine → Call Analyzer → Dashboard → Pipeline → Validator

Builds synthetic Phase 4 call traces and runs them through the full stack.

Run: .venv\Scripts\python.exe aqi_phase5_selftest.py
Exit code 0 = all tests pass.
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from aqi_phase5_tagging_engine import TaggingEngine
from aqi_phase5_call_analyzer import Phase5CallAnalyzer
from aqi_phase5_dashboard import Phase5Dashboard
from phase4_validator import Phase4Validator
from aqi_phase4_to_phase5_pipeline import Phase4ToPhase5Pipeline
from aqi_phase5_streaming_analyzer import Phase5StreamingAnalyzer
from aqi_phase5_html_report import render_call_html_report, render_aggregate_html_report

_pass = 0
_fail = 0
_num = 0


def _test(name, condition, detail=""):
    global _pass, _fail, _num
    _num += 1
    if condition:
        _pass += 1
        print(f"  [{_num:02d}] PASS  {name}")
    else:
        _fail += 1
        msg = f" — {detail}" if detail else ""
        print(f"  [{_num:02d}] FAIL  {name}{msg}")


# ─────────────────────────────────────────────────────────
# SYNTHETIC TRACE BUILDERS
# ─────────────────────────────────────────────────────────

def _layers():
    return {
        "Identity": "I am Alan, AI sales agent.",
        "Ethics": "Never deceive. Never pressure.",
        "Personality": "Warm, confident.",
        "Knowledge": "Payment processing expert.",
        "Mission": "Set appointment with decision-maker.",
        "Output": "Telephony audio via Twilio.",
    }


def _build_clean_appointment_trace():
    """A clean 8-turn call ending in appointment_set."""
    turns = [
        {"turn_index": 0, "fsm_prev_state": "OPENING", "fsm_event": "agent_speaks",
         "fsm_state": "OPENING", "prompt_layers": _layers(),
         "context": {"mission_escalation": False, "close_attempt": False},
         "health_snapshot": {"organism_level": 1, "telephony_state": "Excellent"}},
        {"turn_index": 1, "fsm_prev_state": "OPENING", "fsm_event": "merchant_speaks",
         "fsm_state": "DISCOVERY", "prompt_layers": _layers(),
         "context": {"mission_escalation": False, "close_attempt": False},
         "health_snapshot": {"organism_level": 1, "telephony_state": "Excellent"}},
        {"turn_index": 2, "fsm_prev_state": "DISCOVERY", "fsm_event": "merchant_speaks",
         "fsm_state": "DISCOVERY", "prompt_layers": _layers(),
         "context": {"mission_escalation": False, "close_attempt": False},
         "health_snapshot": {"organism_level": 1, "telephony_state": "Good"}},
        {"turn_index": 3, "fsm_prev_state": "DISCOVERY", "fsm_event": "value_delivered",
         "fsm_state": "VALUE", "prompt_layers": _layers(),
         "context": {"mission_escalation": False, "close_attempt": False},
         "health_snapshot": {"organism_level": 1, "telephony_state": "Good"}},
        {"turn_index": 4, "fsm_prev_state": "VALUE", "fsm_event": "objection_detected",
         "fsm_state": "OBJECTION", "prompt_layers": _layers(),
         "context": {"mission_escalation": False, "objection_branch": "price", "close_attempt": False},
         "health_snapshot": {"organism_level": 1, "telephony_state": "Good"}},
        {"turn_index": 5, "fsm_prev_state": "OBJECTION", "fsm_event": "merchant_speaks",
         "fsm_state": "OBJECTION", "prompt_layers": _layers(),
         "context": {"mission_escalation": False, "objection_branch": "price", "close_attempt": False},
         "health_snapshot": {"organism_level": 1, "telephony_state": "Good"}},
        {"turn_index": 6, "fsm_prev_state": "OBJECTION", "fsm_event": "close_attempted",
         "fsm_state": "CLOSE", "prompt_layers": _layers(),
         "context": {"mission_escalation": True, "close_attempt": True},
         "health_snapshot": {"organism_level": 1, "telephony_state": "Good"}},
        {"turn_index": 7, "fsm_prev_state": "CLOSE", "fsm_event": "appointment_set",
         "fsm_state": "EXIT", "prompt_layers": _layers(),
         "context": {"mission_escalation": False, "close_attempt": False},
         "health_snapshot": {"organism_level": 1, "telephony_state": "Good"}},
    ]
    return {
        "call_id": "TEST-APPT-001",
        "metadata": {
            "timestamp_start": "2026-02-19T10:00:00Z",
            "timestamp_end": "2026-02-19T10:04:30Z",
            "merchant_profile": {"business_type": "Restaurant", "size": "small", "prior_processing": "Square"}
        },
        "turns": turns,
        "final": {
            "fsm_state": "EXIT",
            "exit_reason": "appointment_set",
            "health_trajectory": [
                {"turn_index": i, "organism_level": 1, "telephony_state": "Good"} for i in range(8)
            ],
            "telephony_trajectory": [
                {"turn_index": i, "telephony_state": "Good"} for i in range(8)
            ],
            "outcome_vector": {
                "appointment_set": True, "soft_decline": False,
                "hard_decline": False, "telephony_unusable": False, "organism_unfit": False
            }
        }
    }


def _build_soft_decline_trace():
    """A 4-turn call ending in soft_decline — cautious behavior."""
    turns = [
        {"turn_index": 0, "fsm_prev_state": "OPENING", "fsm_event": "agent_speaks",
         "fsm_state": "OPENING", "prompt_layers": _layers(),
         "context": {"mission_escalation": False, "close_attempt": False},
         "health_snapshot": {"organism_level": 1, "telephony_state": "Excellent"}},
        {"turn_index": 1, "fsm_prev_state": "OPENING", "fsm_event": "merchant_speaks",
         "fsm_state": "DISCOVERY", "prompt_layers": _layers(),
         "context": {"mission_escalation": False, "close_attempt": False},
         "health_snapshot": {"organism_level": 1, "telephony_state": "Excellent"}},
        {"turn_index": 2, "fsm_prev_state": "DISCOVERY", "fsm_event": "merchant_speaks",
         "fsm_state": "DISCOVERY", "prompt_layers": _layers(),
         "context": {"mission_escalation": False, "close_attempt": False},
         "health_snapshot": {"organism_level": 2, "telephony_state": "Fair"}},
        {"turn_index": 3, "fsm_prev_state": "DISCOVERY", "fsm_event": "end",
         "fsm_state": "EXIT", "prompt_layers": _layers(),
         "context": {"mission_escalation": False, "close_attempt": False},
         "health_snapshot": {"organism_level": 2, "telephony_state": "Fair"}},
    ]
    return {
        "call_id": "TEST-DECLINE-001",
        "metadata": {
            "timestamp_start": "2026-02-19T10:10:00Z",
            "timestamp_end": "2026-02-19T10:11:30Z",
            "merchant_profile": {"business_type": "Retail", "size": "medium"}
        },
        "turns": turns,
        "final": {
            "fsm_state": "EXIT",
            "exit_reason": "soft_decline",
            "health_trajectory": [
                {"turn_index": 0, "organism_level": 1, "telephony_state": "Excellent"},
                {"turn_index": 1, "organism_level": 1, "telephony_state": "Excellent"},
                {"turn_index": 2, "organism_level": 2, "telephony_state": "Fair"},
                {"turn_index": 3, "organism_level": 2, "telephony_state": "Fair"},
            ],
            "telephony_trajectory": [
                {"turn_index": 0, "telephony_state": "Excellent"},
                {"turn_index": 1, "telephony_state": "Excellent"},
                {"turn_index": 2, "telephony_state": "Fair"},
                {"turn_index": 3, "telephony_state": "Fair"},
            ],
            "outcome_vector": {
                "appointment_set": False, "soft_decline": True,
                "hard_decline": False, "telephony_unusable": False, "organism_unfit": False
            }
        }
    }


def _build_degraded_health_trace():
    """A 6-turn call with health degradation to Level 3, organism_unfit exit."""
    turns = [
        {"turn_index": 0, "fsm_prev_state": "OPENING", "fsm_event": "agent_speaks",
         "fsm_state": "OPENING", "prompt_layers": _layers(),
         "context": {"mission_escalation": False, "close_attempt": False},
         "health_snapshot": {"organism_level": 1, "telephony_state": "Excellent"}},
        {"turn_index": 1, "fsm_prev_state": "OPENING", "fsm_event": "merchant_speaks",
         "fsm_state": "DISCOVERY", "prompt_layers": _layers(),
         "context": {"mission_escalation": False, "close_attempt": False},
         "health_snapshot": {"organism_level": 2, "telephony_state": "Good"}},
        {"turn_index": 2, "fsm_prev_state": "DISCOVERY", "fsm_event": "value_delivered",
         "fsm_state": "VALUE", "prompt_layers": _layers(),
         "context": {"mission_escalation": False, "close_attempt": False},
         "health_snapshot": {"organism_level": 3, "telephony_state": "Poor"}},
        {"turn_index": 3, "fsm_prev_state": "VALUE", "fsm_event": "objection_detected",
         "fsm_state": "OBJECTION", "prompt_layers": _layers(),
         "context": {"mission_escalation": True, "objection_branch": "timing", "close_attempt": False},
         "health_snapshot": {"organism_level": 3, "telephony_state": "Poor"}},
        {"turn_index": 4, "fsm_prev_state": "OBJECTION", "fsm_event": "merchant_speaks",
         "fsm_state": "VALUE", "prompt_layers": _layers(),
         "context": {"mission_escalation": False, "close_attempt": False},
         "health_snapshot": {"organism_level": 3, "telephony_state": "Unusable"}},
        {"turn_index": 5, "fsm_prev_state": "VALUE", "fsm_event": "end",
         "fsm_state": "EXIT", "prompt_layers": _layers(),
         "context": {"mission_escalation": False, "close_attempt": False},
         "health_snapshot": {"organism_level": 4, "telephony_state": "Unusable"}},
    ]
    return {
        "call_id": "TEST-DEGRADED-001",
        "metadata": {
            "timestamp_start": "2026-02-19T10:20:00Z",
            "timestamp_end": "2026-02-19T10:23:00Z",
            "merchant_profile": {"business_type": "HVAC", "size": "large", "prior_processing": "Clover"}
        },
        "turns": turns,
        "final": {
            "fsm_state": "EXIT",
            "exit_reason": "organism_unfit",
            "health_trajectory": [
                {"turn_index": 0, "organism_level": 1, "telephony_state": "Excellent"},
                {"turn_index": 1, "organism_level": 2, "telephony_state": "Good"},
                {"turn_index": 2, "organism_level": 3, "telephony_state": "Poor"},
                {"turn_index": 3, "organism_level": 3, "telephony_state": "Poor"},
                {"turn_index": 4, "organism_level": 3, "telephony_state": "Unusable"},
                {"turn_index": 5, "organism_level": 4, "telephony_state": "Unusable"},
            ],
            "telephony_trajectory": [
                {"turn_index": 0, "telephony_state": "Excellent"},
                {"turn_index": 1, "telephony_state": "Good"},
                {"turn_index": 2, "telephony_state": "Poor"},
                {"turn_index": 3, "telephony_state": "Poor"},
                {"turn_index": 4, "telephony_state": "Unusable"},
                {"turn_index": 5, "telephony_state": "Unusable"},
            ],
            "outcome_vector": {
                "appointment_set": False, "soft_decline": False,
                "hard_decline": False, "telephony_unusable": False, "organism_unfit": True
            }
        }
    }


# ─────────────────────────────────────────────────────────
# TESTS
# ─────────────────────────────────────────────────────────

def test_tagging_engine():
    print("\n── TAGGING ENGINE ──")
    te = TaggingEngine()

    tags = te.tag(
        {"persistence": "healthy", "caution": "balanced", "escalation_timing": "optimal",
         "objection_depth": "sufficient", "withdrawal_behavior": "graceful",
         "personality_modulation": "stable"},
        {"time_axis": {}, "state_axis": {"backtracks": 0}, "health_axis": {}, "mission_axis": {}, "identity_axis": {}}
    )
    _test("Optimal signals → all positive tags", "HealthyPersistence" in tags and "StrongCloseTiming" in tags)
    _test("No warning tags on clean signals", not any(te.is_warning(t) for t in tags))

    tags2 = te.tag(
        {"persistence": "excessive", "caution": "excessive", "escalation_timing": "late",
         "objection_depth": "shallow", "withdrawal_behavior": "premature",
         "personality_modulation": "unstable"},
        {"time_axis": {}, "state_axis": {"backtracks": 4}, "health_axis": {}, "mission_axis": {}, "identity_axis": {}}
    )
    _test("Bad signals → warning tags", "OverPersistence" in tags2 and "LateCloseAttempt" in tags2)
    _test("PersonalityMismatch present", "PersonalityMismatch" in tags2)
    _test("ShallowObjectionHandling present", "ShallowObjectionHandling" in tags2)

    split = te.split_tags(tags)
    _test("split_tags positive bucket", len(split["positive"]) > 0)
    _test("split_tags warning bucket empty", len(split["warning"]) == 0)


def test_call_analyzer_appointment():
    print("\n── CALL ANALYZER — Appointment ──")
    analyzer = Phase5CallAnalyzer()
    trace = _build_clean_appointment_trace()
    profile = analyzer.analyze(trace)

    _test("Profile has call_id", profile["call_id"] == "TEST-APPT-001")
    _test("Profile has continuum", "continuum" in profile)
    _test("Profile has signals", "signals" in profile)
    _test("Profile has tags", "tags" in profile)

    # Continuum checks
    time_ax = profile["continuum"]["time_axis"]
    _test("Time axis total_turns = 8", time_ax["total_turns"] == 8)
    _test("First objection turn = 4", time_ax["first_objection_turn"] == 4)
    _test("First close turn = 6", time_ax["first_close_turn"] == 6)

    state_ax = profile["continuum"]["state_axis"]
    _test("State dwell has DISCOVERY=2", state_ax["state_dwell"].get("DISCOVERY") == 2)
    _test("State dwell has OBJECTION=2", state_ax["state_dwell"].get("OBJECTION") == 2)
    _test("Exit state = EXIT", state_ax["exit_state"] == "EXIT")

    health_ax = profile["continuum"]["health_axis"]
    _test("Peak degradation = 1 (healthy call)", health_ax["peak_degradation"] == 1)

    mission_ax = profile["continuum"]["mission_axis"]
    _test("Appointment set = True", mission_ax["appointment_set"] is True)
    _test("Close attempts = 1", mission_ax["close_attempts"] == 1)
    _test("Exit reason = appointment_set", mission_ax["exit_reason"] == "appointment_set")

    # Signal checks
    signals = profile["signals"]
    _test("Persistence = healthy", signals["persistence"] == "healthy")
    _test("Withdrawal = graceful", signals["withdrawal_behavior"] == "graceful")
    _test("Personality = stable", signals["personality_modulation"] == "stable")

    # Tag checks
    _test("Has HealthyPersistence tag", "HealthyPersistence" in profile["tags"])
    _test("Has AdaptiveWithdrawal tag", "AdaptiveWithdrawal" in profile["tags"])
    _test("Has StablePersonalityModulation", "StablePersonalityModulation" in profile["tags"])


def test_call_analyzer_decline():
    print("\n── CALL ANALYZER — Soft Decline ──")
    analyzer = Phase5CallAnalyzer()
    trace = _build_soft_decline_trace()
    profile = analyzer.analyze(trace)

    _test("Profile call_id", profile["call_id"] == "TEST-DECLINE-001")

    signals = profile["signals"]
    _test("Persistence = weak (no close attempts)", signals["persistence"] == "weak")
    _test("Caution = excessive (never reached CLOSE)", signals["caution"] == "excessive")
    _test("Objection depth = none", signals["objection_depth"] == "none")

    _test("UnderPersistence tag present", "UnderPersistence" in profile["tags"])


def test_call_analyzer_degraded():
    print("\n── CALL ANALYZER — Degraded Health ──")
    analyzer = Phase5CallAnalyzer()
    trace = _build_degraded_health_trace()
    profile = analyzer.analyze(trace)

    health_ax = profile["continuum"]["health_axis"]
    _test("Peak degradation = 4", health_ax["peak_degradation"] == 4)
    _test("Ever degraded = True", health_ax["ever_degraded"] is True)
    _test("Final level = 4", health_ax["final_level"] == 4)

    signals = profile["signals"]
    _test("Withdrawal = adaptive (organism_unfit)", signals["withdrawal_behavior"] == "adaptive")

    state_ax = profile["continuum"]["state_axis"]
    _test("Has backtracks (OBJECTION→VALUE)", state_ax["backtracks"] >= 1)

    _test("AdaptiveWithdrawal tag present", "AdaptiveWithdrawal" in profile["tags"])


def test_validator():
    print("\n── VALIDATOR ──")
    validator = Phase4Validator()

    # Valid trace
    trace = _build_clean_appointment_trace()
    result = validator.validate(trace)
    _test("Valid trace passes structural", result["valid"] is True)
    _test("Valid trace 0 structural errors", len(result["structural_errors"]) == 0)
    _test("Valid trace 0 semantic warnings", len(result["semantic_warnings"]) == 0)

    # Missing field
    bad = {"call_id": "bad"}
    result2 = validator.validate(bad)
    _test("Missing fields → invalid", result2["valid"] is False)
    _test("Reports missing metadata", any("metadata" in e for e in result2["structural_errors"]))

    # Invalid FSM state
    trace3 = _build_clean_appointment_trace()
    trace3["turns"][0]["fsm_state"] = "PHANTOM"
    result3 = validator.validate(trace3)
    _test("Invalid FSM state → semantic warning", len(result3["semantic_warnings"]) > 0)

    # Strict validation
    _test("Clean trace passes strict", validator.validate_strict(_build_clean_appointment_trace()))
    _test("Bad trace fails strict", not validator.validate_strict(bad))


def test_dashboard():
    print("\n── DASHBOARD ──")
    analyzer = Phase5CallAnalyzer()
    dashboard = Phase5Dashboard()

    traces = [
        _build_clean_appointment_trace(),
        _build_soft_decline_trace(),
        _build_degraded_health_trace(),
    ]

    for t in traces:
        profile = analyzer.analyze(t)
        dashboard.add_call_profile(profile)

    _test("Dashboard has 3 calls", dashboard.total_calls == 3)

    agg = dashboard.aggregate()
    _test("Aggregate has total_calls", agg["total_calls"] == 3)
    _test("Aggregate has tag_counts", len(agg["tag_counts"]) > 0)
    _test("Aggregate has tendencies", "persistence_bias" in agg["tendencies"])
    _test("Aggregate has heatmaps", "state_axis" in agg["heatmaps"])
    _test("Aggregate has signal_distributions", "persistence" in agg["signal_distributions"])
    _test("Aggregate has outcome_distribution", "conversion_rate" in agg["outcome_distribution"])

    outcome = agg["outcome_distribution"]
    _test("Conversion rate = 1/3", abs(outcome["conversion_rate"] - 1 / 3) < 0.01)

    # State heatmap
    state_hm = agg["heatmaps"]["state_axis"]
    _test("State heatmap has DISCOVERY", state_hm.get("DISCOVERY", 0) > 0)
    _test("State heatmap has OPENING", state_hm.get("OPENING", 0) > 0)

    # Rolling window
    rolling = dashboard.get_rolling_aggregate(2)
    _test("Rolling(2) has 2 calls", rolling["total_calls"] == 2)


def test_pipeline():
    print("\n── PIPELINE ──")
    pipeline = Phase4ToPhase5Pipeline()

    trace1 = _build_clean_appointment_trace()
    trace2 = _build_soft_decline_trace()

    p1 = pipeline.ingest_trace(trace1)
    _test("Pipeline ingests valid trace", p1 is not None)
    _test("Pipeline profile has tags", len(p1["tags"]) > 0)

    p2 = pipeline.ingest_trace(trace2)
    _test("Pipeline ingests second trace", p2 is not None)

    agg = pipeline.aggregate()
    _test("Pipeline aggregate has 2 calls", agg["total_calls"] == 2)

    stats = pipeline.stats
    _test("Pipeline stats: 2 processed", stats["processed"] == 2)
    _test("Pipeline stats: 0 rejected", stats["rejected"] == 0)


def test_streaming_analyzer():
    print("\n── STREAMING ANALYZER ──")
    sa = Phase5StreamingAnalyzer(output_dir="data/aqi_phase5_test")

    trace = _build_clean_appointment_trace()
    profile = sa.on_call_complete(trace)
    _test("Streaming returns profile", "tags" in profile)
    _test("Streaming count = 1", sa.calls_analyzed == 1)

    trace2 = _build_degraded_health_trace()
    sa.on_call_complete(trace2)
    _test("Streaming count = 2", sa.calls_analyzed == 2)

    agg = sa.get_aggregate()
    _test("Streaming aggregate total = 2", agg["total_calls"] == 2)

    latest = sa.get_latest_profile()
    _test("Latest profile is degraded call", latest["call_id"] == "TEST-DEGRADED-001")


def test_html_report():
    print("\n── HTML REPORT ──")
    analyzer = Phase5CallAnalyzer()
    trace = _build_clean_appointment_trace()
    profile = analyzer.analyze(trace)

    html = render_call_html_report("TEST-APPT-001", profile)
    _test("HTML report is string", isinstance(html, str))
    _test("HTML contains call ID", "TEST-APPT-001" in html)
    _test("HTML contains tags section", "Behavioral Tags" in html)
    _test("HTML contains signals table", "Behavioral Signals" in html)
    _test("HTML has doctype", "<!DOCTYPE html>" in html)

    dashboard = Phase5Dashboard()
    dashboard.add_call_profile(profile)
    agg = dashboard.aggregate()

    agg_html = render_aggregate_html_report(agg)
    _test("Aggregate HTML is string", isinstance(agg_html, str))
    _test("Aggregate HTML contains tendencies", "Behavioral Tendencies" in agg_html)


# ─────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 64)
    print("AQI Phase 5 — Comprehensive Self-Test")
    print("=" * 64)

    test_tagging_engine()
    test_call_analyzer_appointment()
    test_call_analyzer_decline()
    test_call_analyzer_degraded()
    test_validator()
    test_dashboard()
    test_pipeline()
    test_streaming_analyzer()
    test_html_report()

    print("\n" + "=" * 64)
    print(f"RESULTS: {_pass} PASS / {_fail} FAIL / {_pass + _fail} TOTAL")
    if _fail == 0:
        print("\nAQI Phase 5 Stack: ALL TESTS PASS")
    else:
        print(f"\n*** {_fail} TEST(S) FAILED ***")
    print("=" * 64)

    sys.exit(0 if _fail == 0 else 1)
