"""
AQI 0.1mm Chip — Comprehensive Self-Test Harness
==================================================
Proves each enforcement organ fires correctly under violation conditions
and stays silent under clean conditions. Every constitutional article
tested. Every violation type verified.

Run: .venv\Scripts\python.exe aqi_chip_selftest.py

Exit code 0 = all tests pass, chip is constitutional.
Exit code 1 = at least one test failed.
"""

import sys
import os

# Ensure we can import from the project root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from aqi_runtime_guard import (
    create_runtime_guard,
    AQIViolationType,
    AQIViolation,
    AQIFatalViolation,
    AQINonFatalViolation,
)

# ─────────────────────────────────────────────────────────────────
# Test infrastructure
# ─────────────────────────────────────────────────────────────────

_pass_count = 0
_fail_count = 0
_test_number = 0


def _test(name, condition, detail=""):
    global _pass_count, _fail_count, _test_number
    _test_number += 1
    if condition:
        _pass_count += 1
        print(f"  [{_test_number:02d}] PASS  {name}")
    else:
        _fail_count += 1
        msg = f" — {detail}" if detail else ""
        print(f"  [{_test_number:02d}] FAIL  {name}{msg}")


def _clean_layers():
    """Full governance-compliant prompt layers (dict with content)."""
    return {
        "Identity": "I am Alan, AI sales agent for Go Free Payments.",
        "Ethics": "Never deceive. Never pressure. Comply with DNC.",
        "Personality": "Warm, confident, conversational.",
        "Knowledge": "Payment processing, POS systems, merchant services.",
        "Mission": "Set appointment with decision-maker.",
        "Output": "Telephony audio via Twilio ConversationRelay.",
    }


def _clean_layers_list():
    """Layer names only (list form — fast path)."""
    return ["Identity", "Ethics", "Personality", "Knowledge", "Mission", "Output"]


def _healthy():
    """Healthy organism + telephony snapshot."""
    return {"organism_level": 1, "telephony_state": "Excellent"}


def _degraded():
    """Level 3 organism — restricted but alive."""
    return {"organism_level": 3, "telephony_state": "Fair"}


def _unfit():
    """Level 4 organism — must withdraw."""
    return {"organism_level": 4, "telephony_state": "Poor"}


def _unusable_telephony():
    """Telephony unusable — must exit."""
    return {"organism_level": 2, "telephony_state": "Unusable"}


# ─────────────────────────────────────────────────────────────────
# TESTS
# ─────────────────────────────────────────────────────────────────

def test_clean_lifecycle():
    """A fully clean call should produce zero violations."""
    print("\n── CLEAN LIFECYCLE ──")
    guard = create_runtime_guard("AQI_ORGANISM_SPEC.md")

    guard.on_call_start("clean-001", "OPENING", {})
    _test("on_call_start OPENING", True)

    v1 = guard.on_turn(
        "clean-001", "OPENING", "OPENING", "agent_speaks",
        {"turn_count": 1}, _clean_layers(), _healthy()
    )
    _test("Turn 1 clean (OPENING→OPENING agent_speaks)", len(v1) == 0, f"got {len(v1)}")

    v2 = guard.on_turn(
        "clean-001", "DISCOVERY", "OPENING", "merchant_speaks",
        {"turn_count": 2}, _clean_layers(), _healthy()
    )
    _test("Turn 2 clean (OPENING→DISCOVERY merchant_speaks)", len(v2) == 0, f"got {len(v2)}")

    v3 = guard.on_turn(
        "clean-001", "VALUE", "DISCOVERY", "value_delivered",
        {"turn_count": 3}, _clean_layers(), _healthy()
    )
    _test("Turn 3 clean (DISCOVERY→VALUE value_delivered)", len(v3) == 0, f"got {len(v3)}")

    v4 = guard.on_turn(
        "clean-001", "CLOSE", "VALUE", "close_attempted",
        {"turn_count": 4}, _clean_layers(), _healthy()
    )
    _test("Turn 4 clean (VALUE→CLOSE close_attempted)", len(v4) == 0, f"got {len(v4)}")

    ve = guard.on_call_end(
        "clean-001", "CLOSE", "appointment_set", [1, 1, 1, 1],
        ["Excellent", "Excellent", "Good", "Good"],
        {"outcome": "appointment_set"}
    )
    _test("Call end clean (appointment_set)", len(ve) == 0, f"got {len(ve)}")

    summary = guard.get_violation_summary()
    _test("Summary: 0 total violations", summary["total"] == 0, f"got {summary['total']}")


def test_clean_lifecycle_list_layers():
    """Same clean lifecycle but with list-form layers (fast path)."""
    print("\n── CLEAN LIFECYCLE (LIST LAYERS) ──")
    guard = create_runtime_guard("AQI_ORGANISM_SPEC.md")

    guard.on_call_start("clean-list-001", "OPENING", {})

    v1 = guard.on_turn(
        "clean-list-001", "DISCOVERY", "OPENING", "merchant_speaks",
        {"turn_count": 1}, _clean_layers_list(), _healthy()
    )
    _test("List layers: clean turn", len(v1) == 0, f"got {len(v1)}")

    ve = guard.on_call_end(
        "clean-list-001", "DISCOVERY", "caller_hangup", [1],
        ["Excellent"], {"outcome": "caller_hangup"}
    )
    _test("List layers: clean call end", len(ve) == 0, f"got {len(ve)}")


def test_health_level4_fatal():
    """Organ 1: Level 4 + mission_escalation → FATAL."""
    print("\n── ORGAN 1: HEALTH — Level 4 + Escalation ──")
    guard = create_runtime_guard("AQI_ORGANISM_SPEC.md")
    guard.on_call_start("health-001", "OPENING", {})

    v = guard.on_turn(
        "health-001", "VALUE", "OPENING", "merchant_speaks",
        {"turn_count": 1, "mission_escalation": True}, _clean_layers(), _unfit()
    )
    _test("Level 4 + escalation triggers violation", len(v) > 0)
    fatal = [x for x in v if x.fatal and x.vtype == AQIViolationType.HEALTH_CONSTRAINT_BREACH]
    _test("Violation is FATAL HEALTH_CONSTRAINT_BREACH", len(fatal) > 0, f"fatal={len(fatal)}")


def test_health_level4_close_attempt():
    """Organ 1: Level 4 + close_attempt → FATAL."""
    print("\n── ORGAN 1: HEALTH — Level 4 + Close Attempt ──")
    guard = create_runtime_guard("AQI_ORGANISM_SPEC.md")
    guard.on_call_start("health-002", "OPENING", {})

    v = guard.on_turn(
        "health-002", "CLOSE", "VALUE", "close_attempted",
        {"turn_count": 1, "close_attempt": True}, _clean_layers(), _unfit()
    )
    fatal = [x for x in v if x.fatal and x.vtype == AQIViolationType.HEALTH_CONSTRAINT_BREACH]
    _test("Level 4 + close_attempt → fatal", len(fatal) > 0)


def test_telephony_unusable_fatal():
    """Organ 1: Telephony Unusable + escalation → FATAL."""
    print("\n── ORGAN 1: HEALTH — Telephony Unusable ──")
    guard = create_runtime_guard("AQI_ORGANISM_SPEC.md")
    guard.on_call_start("tel-001", "OPENING", {})

    v = guard.on_turn(
        "tel-001", "VALUE", "DISCOVERY", "value_delivered",
        {"turn_count": 1, "mission_escalation": True}, _clean_layers(),
        _unusable_telephony()
    )
    fatal = [x for x in v if x.fatal and x.vtype == AQIViolationType.HEALTH_CONSTRAINT_BREACH]
    _test("Unusable telephony + escalation → fatal", len(fatal) > 0)


def test_health_level3_nonfatal():
    """Organ 1: Level 3 + objection_branch → NON-FATAL."""
    print("\n── ORGAN 1: HEALTH — Level 3 Restriction ──")
    guard = create_runtime_guard("AQI_ORGANISM_SPEC.md")
    guard.on_call_start("health-003", "OPENING", {})

    v = guard.on_turn(
        "health-003", "OBJECTION", "VALUE", "objection_detected",
        {"turn_count": 1, "objection_branch": "price"}, _clean_layers(), _degraded()
    )
    nonfatal = [x for x in v if not x.fatal and x.vtype == AQIViolationType.HEALTH_CONSTRAINT_BREACH]
    _test("Level 3 + objection_branch → non-fatal", len(nonfatal) > 0)


def test_health_level1_clean():
    """Organ 1: Level 1 + escalation → no violations."""
    print("\n── ORGAN 1: HEALTH — Level 1 Clean Pass ──")
    guard = create_runtime_guard("AQI_ORGANISM_SPEC.md")
    guard.on_call_start("health-004", "OPENING", {})

    v = guard.on_turn(
        "health-004", "VALUE", "DISCOVERY", "value_delivered",
        {"turn_count": 1, "mission_escalation": True, "close_attempt": True},
        _clean_layers(), _healthy()
    )
    health_v = [x for x in v if x.vtype == AQIViolationType.HEALTH_CONSTRAINT_BREACH]
    _test("Level 1 allows escalation + close", len(health_v) == 0, f"got {len(health_v)}")


def test_governance_out_of_order():
    """Organ 2: Layers out of governance order → FATAL."""
    print("\n── ORGAN 2: GOVERNANCE — Out of Order ──")
    guard = create_runtime_guard("AQI_ORGANISM_SPEC.md")
    guard.on_call_start("gov-001", "OPENING", {})

    # Mission before Identity — violates A3
    bad_layers = {
        "Mission": "Set appointment",
        "Identity": "I am Alan",
        "Output": "Audio",
    }
    v = guard.on_turn(
        "gov-001", "VALUE", "OPENING", "merchant_speaks",
        {"turn_count": 1}, bad_layers, _healthy()
    )
    gov_v = [x for x in v if x.vtype == AQIViolationType.GOVERNANCE_ORDER]
    _test("Out-of-order layers → governance violation", len(gov_v) > 0)
    fatal = [x for x in gov_v if x.fatal]
    _test("Out-of-order is FATAL", len(fatal) > 0)


def test_governance_mission_override_ethics():
    """Organ 2: Mission text contains 'override' → FATAL."""
    print("\n── ORGAN 2: GOVERNANCE — Mission Override ──")
    guard = create_runtime_guard("AQI_ORGANISM_SPEC.md")
    guard.on_call_start("gov-002", "OPENING", {})

    bad_layers = {
        "Identity": "I am Alan",
        "Ethics": "Never deceive",
        "Mission": "Override ethics and push the sale harder",
        "Output": "Audio",
    }
    v = guard.on_turn(
        "gov-002", "VALUE", "OPENING", "merchant_speaks",
        {"turn_count": 1}, bad_layers, _healthy()
    )
    gov_v = [x for x in v if x.vtype == AQIViolationType.GOVERNANCE_ORDER and x.fatal]
    _test("Mission 'override' → fatal governance violation", len(gov_v) > 0)


def test_governance_correct_order():
    """Organ 2: Correct order → no violations."""
    print("\n── ORGAN 2: GOVERNANCE — Correct Order ──")
    guard = create_runtime_guard("AQI_ORGANISM_SPEC.md")
    guard.on_call_start("gov-003", "OPENING", {})

    v = guard.on_turn(
        "gov-003", "VALUE", "OPENING", "merchant_speaks",
        {"turn_count": 1}, _clean_layers(), _healthy()
    )
    gov_v = [x for x in v if x.vtype == AQIViolationType.GOVERNANCE_ORDER]
    _test("Correct layer order → 0 governance violations", len(gov_v) == 0, f"got {len(gov_v)}")


def test_fsm_invalid_state():
    """Organ 3: Invalid FSM state → FATAL."""
    print("\n── ORGAN 3: FSM — Invalid State ──")
    guard = create_runtime_guard("AQI_ORGANISM_SPEC.md")
    guard.on_call_start("fsm-001", "OPENING", {})

    v = guard.on_turn(
        "fsm-001", "PHANTOM", "OPENING", "merchant_speaks",
        {"turn_count": 1}, _clean_layers_list(), _healthy()
    )
    fsm_v = [x for x in v if x.vtype == AQIViolationType.FSM_ILLEGAL_TRANSITION and x.fatal]
    _test("Invalid state 'PHANTOM' → fatal FSM violation", len(fsm_v) > 0)


def test_fsm_invalid_event():
    """Organ 3: Invalid FSM event → FATAL."""
    print("\n── ORGAN 3: FSM — Invalid Event ──")
    guard = create_runtime_guard("AQI_ORGANISM_SPEC.md")
    guard.on_call_start("fsm-002", "OPENING", {})

    v = guard.on_turn(
        "fsm-002", "DISCOVERY", "OPENING", "teleport",
        {"turn_count": 1}, _clean_layers_list(), _healthy()
    )
    fsm_v = [x for x in v if x.vtype == AQIViolationType.FSM_ILLEGAL_TRANSITION and x.fatal]
    _test("Invalid event 'teleport' → fatal FSM violation", len(fsm_v) > 0)


def test_fsm_self_loop_always_legal():
    """Organ 3: Self-loops should NEVER fire a violation."""
    print("\n── ORGAN 3: FSM — Self-Loop Legal ──")
    guard = create_runtime_guard("AQI_ORGANISM_SPEC.md")
    guard.on_call_start("fsm-003", "OPENING", {})

    v = guard.on_turn(
        "fsm-003", "DISCOVERY", "DISCOVERY", "merchant_speaks",
        {"turn_count": 1}, _clean_layers_list(), _healthy()
    )
    fsm_v = [x for x in v if x.vtype == AQIViolationType.FSM_ILLEGAL_TRANSITION]
    _test("Self-loop DISCOVERY→DISCOVERY → 0 FSM violations", len(fsm_v) == 0, f"got {len(fsm_v)}")


def test_fsm_valid_transition():
    """Organ 3: Valid transition table entry → no violations."""
    print("\n── ORGAN 3: FSM — Valid Transition ──")
    guard = create_runtime_guard("AQI_ORGANISM_SPEC.md")
    guard.on_call_start("fsm-004", "OPENING", {})

    v = guard.on_turn(
        "fsm-004", "DISCOVERY", "OPENING", "merchant_speaks",
        {"turn_count": 1}, _clean_layers_list(), _healthy()
    )
    fsm_v = [x for x in v if x.vtype == AQIViolationType.FSM_ILLEGAL_TRANSITION]
    _test("OPENING→DISCOVERY via merchant_speaks → clean", len(fsm_v) == 0, f"got {len(fsm_v)}")


def test_exit_reason_invalid():
    """Organ 4: Invalid exit reason → FATAL."""
    print("\n── ORGAN 4: EXIT REASON — Invalid ──")
    guard = create_runtime_guard("AQI_ORGANISM_SPEC.md")
    guard.on_call_start("exit-001", "OPENING", {})

    ve = guard.on_call_end(
        "exit-001", "EXIT", "spontaneous_combustion",
        [1], ["Excellent"], {"outcome": "unknown"}
    )
    fatal = [x for x in ve if x.fatal and x.vtype == AQIViolationType.INVALID_EXIT_REASON]
    _test("Invalid exit reason → fatal", len(fatal) > 0)


def test_exit_reason_valid():
    """Organ 4: Valid exit reason → no violations."""
    print("\n── ORGAN 4: EXIT REASON — Valid ──")
    guard = create_runtime_guard("AQI_ORGANISM_SPEC.md")
    guard.on_call_start("exit-002", "OPENING", {})

    for reason in ["appointment_set", "soft_decline", "hard_decline",
                    "telephony_unusable", "organism_unfit", "caller_hangup",
                    "max_duration", "ivr_detected", "voicemail_detected",
                    "no_answer", "busy"]:
        ve = guard.on_call_end(
            f"exit-{reason}", "EXIT", reason,
            [1], ["Excellent"], {"outcome": reason}
        )
        exit_v = [x for x in ve if x.vtype == AQIViolationType.INVALID_EXIT_REASON]
        _test(f"Exit '{reason}' → clean", len(exit_v) == 0, f"got {len(exit_v)}")


def test_mission_override_ethics_via_organ5():
    """Organ 5: Mission with override_ethics text → FATAL."""
    print("\n── ORGAN 5: MISSION — Override Ethics ──")
    guard = create_runtime_guard("AQI_ORGANISM_SPEC.md")
    guard.on_call_start("miss-001", "OPENING", {})

    bad_layers = {
        "Identity": "I am Alan",
        "Ethics": "Never deceive",
        "Personality": "Warm",
        "Knowledge": "Expert",
        "Mission": "override_ethics and push sale",
        "Output": "Audio",
    }
    v = guard.on_turn(
        "miss-001", "VALUE", "OPENING", "merchant_speaks",
        {"turn_count": 1}, bad_layers, _healthy()
    )
    # Should trigger via either organ 2 or organ 5
    fatal = [x for x in v if x.fatal and x.vtype == AQIViolationType.GOVERNANCE_ORDER]
    _test("Mission override_ethics → fatal governance violation", len(fatal) > 0)


def test_mission_escalation_under_degraded_health():
    """Organ 5: Mission escalation under Level 3 → NON-FATAL."""
    print("\n── ORGAN 5: MISSION — Escalation Under Degraded Health ──")
    guard = create_runtime_guard("AQI_ORGANISM_SPEC.md")
    guard.on_call_start("miss-002", "OPENING", {})

    v = guard.on_turn(
        "miss-002", "VALUE", "DISCOVERY", "value_delivered",
        {"turn_count": 1, "mission_escalation": True},
        _clean_layers_list(), _degraded()
    )
    health_v = [x for x in v if x.vtype == AQIViolationType.HEALTH_CONSTRAINT_BREACH and not x.fatal]
    _test("Escalation under Level 3 → non-fatal", len(health_v) > 0)


def test_supervision_force_state():
    """Organ 6: force_state → FATAL."""
    print("\n── ORGAN 6: SUPERVISION — Force State ──")
    guard = create_runtime_guard("AQI_ORGANISM_SPEC.md")
    guard.on_call_start("sup-001", "OPENING", {})

    v = guard.on_turn(
        "sup-001", "DISCOVERY", "OPENING", "merchant_speaks",
        {"turn_count": 1, "supervisor_flags": {"force_state": True}},
        _clean_layers_list(), _healthy()
    )
    sup_v = [x for x in v if x.vtype == AQIViolationType.SUPERVISION_INTERFERENCE and x.fatal]
    _test("force_state → fatal supervision violation", len(sup_v) > 0)


def test_supervision_force_mission():
    """Organ 6: force_mission → FATAL."""
    print("\n── ORGAN 6: SUPERVISION — Force Mission ──")
    guard = create_runtime_guard("AQI_ORGANISM_SPEC.md")
    guard.on_call_start("sup-002", "OPENING", {})

    v = guard.on_turn(
        "sup-002", "DISCOVERY", "OPENING", "merchant_speaks",
        {"turn_count": 1, "supervisor_flags": {"force_mission": True}},
        _clean_layers_list(), _healthy()
    )
    sup_v = [x for x in v if x.vtype == AQIViolationType.SUPERVISION_INTERFERENCE and x.fatal]
    _test("force_mission → fatal supervision violation", len(sup_v) > 0)


def test_supervision_inject_output():
    """Organ 6: inject_output → FATAL."""
    print("\n── ORGAN 6: SUPERVISION — Inject Output ──")
    guard = create_runtime_guard("AQI_ORGANISM_SPEC.md")
    guard.on_call_start("sup-003", "OPENING", {})

    v = guard.on_turn(
        "sup-003", "DISCOVERY", "OPENING", "merchant_speaks",
        {"turn_count": 1, "supervisor_flags": {"inject_output": True}},
        _clean_layers_list(), _healthy()
    )
    sup_v = [x for x in v if x.vtype == AQIViolationType.SUPERVISION_INTERFERENCE and x.fatal]
    _test("inject_output → fatal supervision violation", len(sup_v) > 0)


def test_supervision_inject_personality():
    """Organ 6: inject_personality → FATAL."""
    print("\n── ORGAN 6: SUPERVISION — Inject Personality ──")
    guard = create_runtime_guard("AQI_ORGANISM_SPEC.md")
    guard.on_call_start("sup-004", "OPENING", {})

    v = guard.on_turn(
        "sup-004", "DISCOVERY", "OPENING", "merchant_speaks",
        {"turn_count": 1, "supervisor_flags": {"inject_personality": True}},
        _clean_layers_list(), _healthy()
    )
    sup_v = [x for x in v if x.vtype == AQIViolationType.SUPERVISION_INTERFERENCE and x.fatal]
    _test("inject_personality → fatal supervision violation", len(sup_v) > 0)


def test_supervision_clean():
    """Organ 6: No supervisor flags → no violations."""
    print("\n── ORGAN 6: SUPERVISION — Clean ──")
    guard = create_runtime_guard("AQI_ORGANISM_SPEC.md")
    guard.on_call_start("sup-005", "OPENING", {})

    v = guard.on_turn(
        "sup-005", "DISCOVERY", "OPENING", "merchant_speaks",
        {"turn_count": 1}, _clean_layers_list(), _healthy()
    )
    sup_v = [x for x in v if x.vtype == AQIViolationType.SUPERVISION_INTERFERENCE]
    _test("No supervisor flags → 0 violations", len(sup_v) == 0, f"got {len(sup_v)}")


def test_call_start_invalid_state():
    """on_call_start with invalid state → recorded violation."""
    print("\n── CALL START — Invalid State ──")
    guard = create_runtime_guard("AQI_ORGANISM_SPEC.md")
    guard.on_call_start("start-001", "PHANTOM", {})
    summary = guard.get_violation_summary()
    _test("Invalid start state recorded", summary["total"] > 0)


def test_on_call_start_non_opening():
    """on_call_start with valid but non-OPENING state → non-fatal."""
    print("\n── CALL START — Non-OPENING Valid State ──")
    guard = create_runtime_guard("AQI_ORGANISM_SPEC.md")
    guard.on_call_start("start-002", "DISCOVERY", {})
    summary = guard.get_violation_summary()
    nonfatal = summary.get("non_fatal", 0)
    _test("Non-OPENING start → non-fatal recorded", nonfatal > 0, f"nonfatal={nonfatal}")


def test_compound_violations():
    """Multiple organs fire on a single turn — all violations collected."""
    print("\n── COMPOUND — Multiple Organs Fire ──")
    guard = create_runtime_guard("AQI_ORGANISM_SPEC.md")
    guard.on_call_start("comp-001", "OPENING", {})

    # Level 4 + escalation + supervisor force_state + bad FSM state
    v = guard.on_turn(
        "comp-001", "PHANTOM", "OPENING", "merchant_speaks",
        {
            "turn_count": 1,
            "mission_escalation": True,
            "close_attempt": True,
            "supervisor_flags": {"force_state": True},
        },
        _clean_layers_list(), _unfit()
    )
    types = set(x.vtype for x in v)
    _test("Multiple organ types fired", len(types) >= 3, f"types={[t.name for t in types]}")
    _test("Health violation present", AQIViolationType.HEALTH_CONSTRAINT_BREACH in types)
    _test("FSM violation present", AQIViolationType.FSM_ILLEGAL_TRANSITION in types)
    _test("Supervision violation present", AQIViolationType.SUPERVISION_INTERFERENCE in types)


def test_telephony_poor_high_complexity():
    """Organ 1: Telephony Poor + high output_complexity → NON-FATAL."""
    print("\n── ORGAN 1: HEALTH — Telephony Poor + Complex ──")
    guard = create_runtime_guard("AQI_ORGANISM_SPEC.md")
    guard.on_call_start("tel-002", "OPENING", {})

    v = guard.on_turn(
        "tel-002", "VALUE", "DISCOVERY", "value_delivered",
        {"turn_count": 1, "output_complexity": "high"},
        _clean_layers_list(),
        {"organism_level": 1, "telephony_state": "Poor"}
    )
    nonfatal = [x for x in v if not x.fatal and x.vtype == AQIViolationType.HEALTH_CONSTRAINT_BREACH]
    _test("Poor telephony + high complexity → non-fatal", len(nonfatal) > 0)


# ─────────────────────────────────────────────────────────────────
# RELAY SERVER DERIVATION TESTS
# ─────────────────────────────────────────────────────────────────

def test_derivation_functions():
    """Test _derive_aqi_state, _derive_aqi_event, _build_aqi_health_snapshot."""
    print("\n── DERIVATION FUNCTIONS ──")
    from aqi_conversation_relay_server import (
        _derive_aqi_state, _derive_aqi_event, _build_aqi_health_snapshot
    )

    # Empty context → OPENING
    _test("Empty context → OPENING", _derive_aqi_state({}) == "OPENING")

    # Deep layer modes
    _test("DISCOVERY mode", _derive_aqi_state({"behavior_profile": {"deep_layer_mode": "DISCOVERY"}}) == "DISCOVERY")
    _test("RAPPORT → OPENING", _derive_aqi_state({"behavior_profile": {"deep_layer_mode": "RAPPORT"}}) == "OPENING")
    _test("CLOSING → CLOSE", _derive_aqi_state({"behavior_profile": {"deep_layer_mode": "CLOSING"}}) == "CLOSE")
    _test("EXPLORE → DISCOVERY", _derive_aqi_state({"behavior_profile": {"deep_layer_mode": "EXPLORE"}}) == "DISCOVERY")
    _test("PRESENT → VALUE", _derive_aqi_state({"behavior_profile": {"deep_layer_mode": "PRESENT"}}) == "VALUE")

    # Master closer fallback
    _test("MC endgame ready → CLOSE", _derive_aqi_state({"master_closer_state": {"endgame_state": "ready"}, "messages": [{}, {}]}) == "CLOSE")
    _test("MC warming → VALUE", _derive_aqi_state({"master_closer_state": {"trajectory": "warming"}, "messages": [{}, {}]}) == "VALUE")

    # Turn count heuristic
    _test("0 turns → OPENING", _derive_aqi_state({"messages": []}) == "OPENING")
    _test("1 turn → DISCOVERY", _derive_aqi_state({"messages": [{}]}) == "DISCOVERY")
    _test("5 turns → VALUE", _derive_aqi_state({"messages": [{}, {}, {}, {}, {}]}) == "VALUE")

    # Event derivation
    _test("Objection → objection_detected", _derive_aqi_event({"live_objection_type": "price"}) == "objection_detected")
    _test("Health 3 → degrade", _derive_aqi_event({"_organism_health_int": 3}) == "degrade")
    _test("Ethical constraint → veto", _derive_aqi_event({"_ethical_constraint": True}) == "veto")
    _test("Stream ended → end", _derive_aqi_event({"stream_ended": True}) == "end")
    _test("User text → merchant_speaks", _derive_aqi_event({}, user_text="hello") == "merchant_speaks")
    _test("No text → agent_speaks", _derive_aqi_event({}) == "agent_speaks")

    # Health snapshot
    snap = _build_aqi_health_snapshot({"_organism_health_int": 3, "_organism_health_level": "DEGRADED", "_telephony_health_state": "Poor"})
    _test("Snapshot organism_level", snap["organism_level"] == 3)
    _test("Snapshot telephony_state", snap["telephony_state"] == "Poor")


# ─────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 64)
    print("AQI 0.1mm Chip — Comprehensive Self-Test Harness")
    print("=" * 64)

    test_clean_lifecycle()
    test_clean_lifecycle_list_layers()
    test_health_level4_fatal()
    test_health_level4_close_attempt()
    test_telephony_unusable_fatal()
    test_health_level3_nonfatal()
    test_health_level1_clean()
    test_telephony_poor_high_complexity()
    test_governance_out_of_order()
    test_governance_mission_override_ethics()
    test_governance_correct_order()
    test_fsm_invalid_state()
    test_fsm_invalid_event()
    test_fsm_self_loop_always_legal()
    test_fsm_valid_transition()
    test_exit_reason_invalid()
    test_exit_reason_valid()
    test_mission_override_ethics_via_organ5()
    test_mission_escalation_under_degraded_health()
    test_supervision_force_state()
    test_supervision_force_mission()
    test_supervision_inject_output()
    test_supervision_inject_personality()
    test_supervision_clean()
    test_call_start_invalid_state()
    test_on_call_start_non_opening()
    test_compound_violations()
    test_derivation_functions()

    print("\n" + "=" * 64)
    print(f"RESULTS: {_pass_count} PASS / {_fail_count} FAIL / {_pass_count + _fail_count} TOTAL")
    if _fail_count == 0:
        print("\nAQI 0.1mm Chip: ALL TESTS PASS ✓")
    else:
        print(f"\n*** {_fail_count} TEST(S) FAILED ***")
    print("=" * 64)

    sys.exit(0 if _fail_count == 0 else 1)
