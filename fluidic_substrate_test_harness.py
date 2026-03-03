"""
fluidic_substrate_test_harness.py

Standalone test harness for AQI's fluidic substrate.

Simulates:
- intent changes
- mood / relational shifts
- governance vetoes
- world-model deltas
- operational context changes

And prints a trace of fluidic transitions.
"""

import time
import random

import fluidic_kernel as fk  # adjust if your module name differs


# --------------------------------------------------------------------
# 1. Simulation inputs
# --------------------------------------------------------------------

INTENTS = [
    "idle",
    "work",
    "explain",
    "summarize",
    "explore",
    "pause",
]

MOODS = [
    "neutral",
    "curious",
    "focused",
    "tired",
    "stressed",
]

WORLD_MODEL_DELTAS = [
    None,
    "new_topic",
    "uncertainty_spike",
    "resolved_conflict",
]

OP_PHASES = [
    "idle",
    "deep_work",
    "review",
    "handoff",
    "explore",
]

# For governance veto simulation
GOVERNANCE_SCENARIOS = [
    "normal",          # no extra vetoes
    "no_focus",        # FOCUS is disallowed
    "safe_only",       # restrict to HOME, CALM, BRIDGE
]


# --------------------------------------------------------------------
# 2. Helpers for simulated signals
# --------------------------------------------------------------------

def simulate_intent(step: int) -> str:
    """Simulate intent evolution over time."""
    # Simple pattern: start idle, move to work/explain, then review/idle
    if step < 3:
        return "idle"
    elif step < 7:
        return random.choice(["work", "explain"])
    elif step < 10:
        return random.choice(["summarize", "explore"])
    else:
        return random.choice(INTENTS)


def simulate_relational_cues(step: int) -> dict:
    """Simulate mood / relational state."""
    if step < 3:
        mood = "neutral"
    elif step < 6:
        mood = "focused"
    elif step < 9:
        mood = "curious"
    else:
        mood = random.choice(MOODS)

    # Occasionally inject stress / tired
    if step in (5, 8, 11):
        mood = random.choice(["tired", "stressed"])

    return {
        "mood": mood,
        "trust": "stable",  # placeholder
        "energy": "low" if mood in ("tired", "stressed") else "normal",
    }


def simulate_worldmodel_delta(step: int):
    """Simulate world-model deltas."""
    if step == 4:
        return "new_topic"
    if step == 7:
        return "uncertainty_spike"
    if step == 10:
        return "resolved_conflict"
    return None


def simulate_op_context(step: int) -> dict:
    """Simulate North's operational phase."""
    if step < 3:
        phase = "idle"
    elif step < 6:
        phase = "deep_work"
    elif step < 9:
        phase = "explore"
    elif step < 12:
        phase = "review"
    else:
        phase = random.choice(OP_PHASES)

    return {
        "phase": phase,
    }


def simulate_governance_mode(step: int) -> str:
    """Choose a governance scenario for demonstration."""
    if step < 5:
        return "normal"
    elif step < 9:
        return "no_focus"
    else:
        return "safe_only"


# --------------------------------------------------------------------
# 3. Governance hook wrapper
# --------------------------------------------------------------------

def can_transition(current_state_name: str,
                   next_state_name: str,
                   governance_mode: str) -> bool:
    """
    High-level governance simulation around the kernel's constraints.

    This wraps fk.governance_constraints and adds scenario-based vetoes.
    """

    # First, consult kernel's governance (if it exposes a helper).
    # If not, adapt this to your actual API.
    base_allowed = True
    if hasattr(fk, "governance_constraints"):
        # governance_constraints could be:
        # - dict: { state_name: { ...rules... } }
        # - or a callable: governance_constraints(from, to) -> bool
        gc = fk.governance_constraints

        if callable(gc):
            base_allowed = bool(gc(current_state_name, next_state_name))
        else:
            # Simple example: forbid transitions into a state whose
            # constraints mark it "restricted_entry": True
            state_rules = gc.get(next_state_name, {})
            restricted = state_rules.get("restricted_entry", False)
            base_allowed = not restricted

    if not base_allowed:
        return False

    # Scenario-level overrides
    if governance_mode == "no_focus" and next_state_name == "FOCUS":
        return False

    if governance_mode == "safe_only" and next_state_name not in ("HOME", "CALM", "BRIDGE"):
        return False

    return True


# --------------------------------------------------------------------
# 4. Main simulation harness
# --------------------------------------------------------------------

def run_simulation(steps: int = 15, delay: float = 0.5):
    """
    Run a step-based simulation of the fluidic substrate.

    At each step:
    - generate signals
    - route to a world
    - check governance
    - transition (or veto)
    - log the result
    """

    # Start in HOME (or your canonical resting state)
    current_state_name = "HOME"
    current_state = fk.WORLD_SET[current_state_name]

    last_intent = None
    last_relational_cues = None
    last_worldmodel_delta = None
    last_op_context = None

    print("=== Fluidic Substrate Test Harness ===")
    print(f"Initial state: {current_state_name}")
    print("--------------------------------------")

    for step in range(1, steps + 1):
        print(f"\n[STEP {step}]")

        # 1) Generate simulated signals
        intent = simulate_intent(step)
        relational_cues = simulate_relational_cues(step)
        worldmodel_delta = simulate_worldmodel_delta(step)
        op_context = simulate_op_context(step)
        governance_mode = simulate_governance_mode(step)

        print(f"Intent:           {intent}")
        print(f"Relational cues:  {relational_cues}")
        print(f"Worldmodel delta: {worldmodel_delta}")
        print(f"Op context:       {op_context}")
        print(f"Governance mode:  {governance_mode}")
        print(f"Current state:    {current_state_name}")

        # 2) Decide if hybrid invocation should fire
        # Trigger when *any* meaningful signal changed
        should_invoke = (
            intent != last_intent
            or relational_cues != last_relational_cues
            or worldmodel_delta != last_worldmodel_delta
            or op_context != last_op_context
        )

        if not should_invoke:
            print("Hybrid pattern: no significant change  no transition.")
        else:
            # 3) Route to a candidate next state
            next_state_name = fk.route_context(
                intent=intent,
                relational_cues=relational_cues,
                worldmodel_delta=worldmodel_delta,
                op_context=op_context,
            )

            print(f"Router suggests:  {next_state_name}")

            # 4) Governance check
            if can_transition(current_state_name, next_state_name, governance_mode):
                # 5) Perform transition using kernel's transition logic
                next_state = fk.transition(
                    current_state=current_state,
                    next_state_name=next_state_name,
                    # pass whatever extra args your transition() expects
                )

                print(
                    f"Transition:      {current_state_name}  {next_state_name} "
                    "(ALLOWED)"
                )
                current_state_name = next_state_name
                current_state = next_state
            else:
                print(
                    f"Transition:      {current_state_name}  {next_state_name} "
                    "(BLOCKED by governance)"
                )

        # 6) Update last signals for hybrid comparison
        last_intent = intent
        last_relational_cues = relational_cues
        last_worldmodel_delta = worldmodel_delta
        last_op_context = op_context

        time.sleep(delay)

    print("\n=== Simulation complete ===")


if __name__ == "__main__":
    run_simulation()
