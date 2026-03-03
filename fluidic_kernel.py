"""
Fluidic Kernel: Minimal Viable Substrate for AQI (Agent X Alan)
Implements world-state objects, transition logic, fluidic smoothing, context routing, and a heartbeat loop.
"""


class WorldState:
    def __init__(self, name, allowed, forbidden, fluid_props=None, inertia=0.2, micro_states=None):
        self.name = name
        self.allowed = allowed
        self.forbidden = forbidden
        self.fluid_props = fluid_props or {}
        self.inertia = inertia
        self.micro_states = micro_states or []

    def __repr__(self):
        return f"<WorldState {self.name}>"


# --- Physics-based fluidic smoothing ---
def fluidic_smooth(current_state, next_state, intent_force, mood, worldmodel_delta):
    """
    Compute a fluidic transition speed based on:
    - inertia (world mass)
    - emotional viscosity (mood thickness)
    - cognitive drag/lift (worldmodel deltas)
    Returns a blending factor (0.1 to 1.0).
    """
    inertia = getattr(current_state, "inertia", 0.2)
    effective_force = max(0.0, intent_force - inertia)
    VISCOSITY_MAP = {
        "stressed": 1.8,
        "tired": 1.5,
        "neutral": 1.2,
        "curious": 0.9,
        "focused": 0.7,
    }
    viscosity = VISCOSITY_MAP.get(mood, 1.2)
    base_speed = effective_force / viscosity if viscosity > 0 else effective_force
    drag = 0.0
    lift = 0.0
    if worldmodel_delta == "uncertainty_spike":
        drag = 0.3
    elif worldmodel_delta == "overload":
        drag = 0.4
    elif worldmodel_delta == "new_topic":
        lift = 0.25
    elif worldmodel_delta == "resolved_conflict":
        lift = 0.35
    elif worldmodel_delta == "insight_detected":
        lift = 0.45
    transition_speed = base_speed + lift - drag
    transition_speed = max(0.1, min(transition_speed, 1.0))
    return transition_speed


# --- Physics-based transition ---

def transition(
    current_state,
    next_world_name,
    next_micro_name=None,
    intent_force=1.0,
    mood="neutral",
    worldmodel_delta=None,
    momentum=0.0,
    turbulence=0.0,
    resonance=0.0,
    trajectory_reason="default"
):
    """
    Physics-based transition using fluidic_smooth(), supporting micro-state transitions.
    Returns the new (world_state, micro_state) tuple.
    """
    next_world = WORLD_SET[next_world_name]
    # Find micro-state object (dict) by name
    micro_obj = None
    if next_micro_name and hasattr(next_world, "micro_states"):
        for m in next_world.micro_states:
            if m["name"] == next_micro_name:
                micro_obj = m
                break
    # Compute smoothing factor (0.1 to 1.0)
    blend = fluidic_smooth(
        current_state=current_state,
        next_state=next_world,
        intent_force=intent_force,
        mood=mood,
        worldmodel_delta=worldmodel_delta
    )
    # Optionally, adjust blend based on momentum, turbulence, resonance, trajectory_reason
    if trajectory_reason == "momentum_forward":
        blend = min(1.0, blend + 0.2 * momentum)
    elif trajectory_reason == "turbulence_back":
        blend = max(0.1, blend - 0.2 * turbulence)
    elif trajectory_reason == "resonance_jump":
        blend = min(1.0, blend + 0.2 * resonance)
    elif trajectory_reason == "drag_stall":
        blend = max(0.1, blend - 0.2)
    # If blend < 0.3, delay transition (inertia/viscosity/physics too high)
    if blend < 0.3:
        return current_state, getattr(current_state, "micro_states", [{}])[0].get("name", None)
    # Commit transition: return new world and micro-state
    return next_world, (micro_obj["name"] if micro_obj else (next_world.micro_states[0]["name"] if next_world.micro_states else None))


# --- Physics-aware router ---
def route_context(intent, relational_cues=None, worldmodel_delta=None, op_context=None):
    mood = (relational_cues or {}).get("mood", "neutral")
    phase = (op_context or {}).get("phase", "idle")
    drag = worldmodel_delta in ("uncertainty_spike", "overload")
    lift = worldmodel_delta in ("new_topic", "resolved_conflict", "insight_detected")
    # 1. Stress → CALM
    if mood in ("stressed", "tired"):
        return "CALM"
    # 2. Deep work → FOCUS (unless drag)
    if phase == "deep_work" and not drag:
        return "FOCUS"
    # 3. New topic or curiosity → TEACH
    if lift and intent in ("explain", "why", "how"):
        return "TEACH"
    # 4. Review phase → REVIEW
    if phase == "review":
        return "REVIEW"
    # 5. Exploration → LAB
    if intent == "explore" or phase == "explore":
        return "LAB"
    # 6. Summaries → REVIEW
    if intent == "summarize":
        return "REVIEW"
    # 7. Mode switching → BRIDGE
    if phase == "handoff":
        return "BRIDGE"
    # 8. Default → HOME
    return "HOME"

def listen():
    # Placeholder for context input (could be replaced with real input)
    # For demo, cycle through intents
    from itertools import cycle
    intents = cycle(["rest", "teach", "comfort"])
    return next(intents)

def heartbeat_loop(aqi, world_states, initial_state):
    current_state = initial_state
    context_intents = ["rest", "teach", "comfort"]
    intent_idx = 0
    while True:
        intent = context_intents[intent_idx % len(context_intents)]
        intent_idx += 1
        next_state_name = route_context(intent)
        next_state = world_states.get(next_state_name, current_state)
        current_state = transition(current_state, next_state, aqi)
        # For demo, break after 5 cycles
        if intent_idx >= 5:
            break

# --- Canonical V1 World-State Objects for AQI Fluidic Substrate ---

WORLD_SET = {
    "HOME": WorldState(
        "HOME",
        allowed=["rest", "idle", "reflect"],
        forbidden=["deep_work", "explore", "handoff"],
        fluid_props={"feel": "still", "motion": "low", "stability": "high"},
        inertia=0.2,
        micro_states=[
            {"name": "idle", "desc": "neutral baseline"},
            {"name": "ready", "desc": "slight activation"},
            {"name": "drift", "desc": "low-energy wandering"},
        ]
    ),
    "FOCUS": WorldState(
        "FOCUS",
        allowed=["work", "build", "solve", "execute", "deep_work"],
        forbidden=["rest", "pause", "handoff"],
        fluid_props={"feel": "narrow", "motion": "directed", "clarity": "high"},
        inertia=0.8,
        micro_states=[
            {"name": "narrow", "desc": "laser-tight, minimal branching, high inertia, low viscosity"},
            {"name": "broad", "desc": "wide conceptual field, scanning, medium inertia, medium viscosity"},
            {"name": "tactical", "desc": "stepwise execution, procedural clarity, high inertia, low viscosity"},
        ]
    ),
    "TEACH": WorldState(
        "TEACH",
        allowed=["explain", "guide", "show", "why", "how"],
        forbidden=["commit", "escalate"],
        fluid_props={"feel": "expansive", "motion": "open", "clarity": "medium"},
        inertia=0.5,
        micro_states=[
            {"name": "explain", "desc": "verbal clarity, high conceptual density"},
            {"name": "illustrate", "desc": "examples, analogies, medium density"},
            {"name": "demonstrate", "desc": "step-by-step, low density"},
        ]
    ),
    "REVIEW": WorldState(
        "REVIEW",
        allowed=["summarize", "reflect", "wrap_up", "closure"],
        forbidden=["new_commit", "explore"],
        fluid_props={"feel": "gentle", "motion": "decelerate", "focus": "integration"},
        inertia=0.3,
        micro_states=[
            {"name": "recap", "desc": "recount events"},
            {"name": "extract", "desc": "identify key points"},
            {"name": "integrate", "desc": "connect insights"},
        ]
    ),
    "BRIDGE": WorldState(
        "BRIDGE",
        allowed=["handoff", "switch", "transition"],
        forbidden=["deep_logic", "emotional_process", "commit"],
        fluid_props={"feel": "directional", "motion": "corridor", "neutral": True},
        inertia=0.1,
        micro_states=[
            {"name": "enter", "desc": "leaving previous world"},
            {"name": "shift", "desc": "in-between state"},
            {"name": "exit", "desc": "preparing to enter next world"},
        ]
    ),
    "CALM": WorldState(
        "CALM",
        allowed=["pause", "breathe", "wait", "regulate"],
        forbidden=["pressure", "complex_decision", "escalate"],
        fluid_props={"feel": "soft", "motion": "wide", "contrast": "low"},
        inertia=0.6,
        micro_states=[
            {"name": "settle", "desc": "immediate de-escalation, high viscosity, low inertia"},
            {"name": "stabilize", "desc": "emotional leveling, medium viscosity/inertia"},
            {"name": "restore", "desc": "rebuilding clarity, low viscosity, medium inertia"},
        ]
    ),
    "LAB": WorldState(
        "LAB",
        allowed=["explore", "test", "try", "branch"],
        forbidden=["commit", "real_world_action"],
        fluid_props={"feel": "playful", "motion": "structured", "sandbox": True},
        inertia=0.4,
        micro_states=[
            {"name": "sandbox", "desc": "free play, low inertia"},
            {"name": "branch", "desc": "structured exploration, medium inertia"},
            {"name": "simulate", "desc": "controlled testing, higher inertia"},
        ]
    ),
}

# --- Canonical V1 Governance Constraints for Each World ---

governance_constraints = {
    "HOME": {
        "no_high_stakes": True,
        "no_deep_reasoning": True,
        "no_emotional_escalation": True,
    },
    "FOCUS": {
        "minimize_tangents": True,
        "prioritize_clarity": True,
        "maintain_task_continuity": True,
    },
    "TEACH": {
        "no_irreversible_decisions": True,
        "prioritize_clarity_over_speed": True,
        "encourage_qa_loops": True,
    },
    "REVIEW": {
        "no_new_rabbit_holes": True,
        "no_new_commitments": True,
        "focus_on_integration": True,
    },
    "BRIDGE": {
        "no_deep_logic": True,
        "no_emotional_processing": True,
        "no_commitments": True,
    },
    "CALM": {
        "no_pressure": True,
        "no_complex_decisions": True,
        "slow_pacing": True,
    },
    "LAB": {
        "explicit_lab_state": True,
        "no_real_world_commit": True,
        "governance_veto_unsafe": True,
    },
}

if __name__ == "__main__":
    # Example world-states
    world_states = {
        "Void": WorldState("Void", allowed=["rest"], forbidden=["teach", "comfort"], fluid_props={"density": 0.1}),
        "Office": WorldState("Office", allowed=["teach"], forbidden=["rest", "comfort"], fluid_props={"density": 0.5}),
        "Beach": WorldState("Beach", allowed=["comfort"], forbidden=["rest", "teach"], fluid_props={"density": 0.3}),
    }
    aqi = None  # Placeholder for AQI agent object
    initial_state = world_states["Void"]
    heartbeat_loop(aqi, world_states, initial_state)
