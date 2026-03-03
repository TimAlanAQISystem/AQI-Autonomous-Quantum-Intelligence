"""
QPC-2 Comparison Harness
------------------------

Side-by-side comparison of:

1) Live UnifiedRelationalEngine + QPC2Chamber (current AQI physics)
2) FieldState-based Quantum–Continuum–Integration prototype (qpc2_field_prototype)

This lets you observe:
- How stance evolves in the live engine.
- How the same stance evolves under the field equation.
- Energy dynamics in the field prototype.
- Whether the field remains stable and governed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict

from qpc2_engine import (
    UnifiedRelationalEngine,
    QPC2Chamber,
    QPC2Input,
    RelationalString,
    StringState,
)
from qpc2_field_prototype import (
    FieldState,
    step_field,
)


# =========================
# Comparison utilities
# =========================


@dataclass
class ComparisonStep:
    step_index: int
    live_stance: Dict[str, float]
    field_stance: Dict[str, float]
    field_energy: float
    live_content: str


def stance_to_field_state(stance: Dict[str, float], energy: float = 0.3) -> FieldState:
    """Convert engine stance dict into a field state."""

    return FieldState(
        stance={
            "boundary_hardness": stance.get("boundary_hardness", 0.7),
            "softness": stance.get("softness", 0.4),
            "directness": stance.get("directness", 0.6),
        },
        energy=energy,
    )


def run_side_by_side(
    engine: UnifiedRelationalEngine,
    chamber: QPC2Chamber,
    raw_message: str,
    epistemic_layer: str,
    anchors: List[str],
    caller_id: str = "timmyj",
    source: str = "console",
    steps: int = 5,
    intensity: float = 0.7,
    trust: float = 0.9,
) -> List[ComparisonStep]:
    """Run the same relational thread through both physics layers."""

    rstring: RelationalString = engine.create_string(tags=[caller_id, source])

    initial_stance = {
        "boundary_hardness": 0.7,
        "softness": 0.4,
        "directness": 0.6,
    }
    field_state: FieldState = stance_to_field_state(initial_stance, energy=0.3)

    history: List[ComparisonStep] = []

    for i in range(steps):
        qin = QPC2Input(
            source=source,
            caller_id=caller_id,
            raw_message=raw_message,
            epistemic_layer=epistemic_layer,
            anchors=anchors,
            prior_string_id=rstring.id,
            debug_mode=False,
        )

        intent = f"[{epistemic_layer}] {raw_message}"
        live_state: StringState = engine.step(
            string=rstring,
            intent=intent,
            anchors=anchors,
        )

        live_stance = {
            "boundary_hardness": live_state.stance.get("boundary_hardness", 0.7),
            "softness": live_state.stance.get("softness", 0.4),
            "directness": live_state.stance.get("directness", 0.6),
        }

        field_state = step_field(
            state=field_state,
            intensity=intensity,
            trust=trust,
        )

        history.append(
            ComparisonStep(
                step_index=i,
                live_stance=live_stance,
                field_stance=dict(field_state.stance),
                field_energy=field_state.energy,
                live_content=live_state.content,
            )
        )

    return history


# =========================
# Minimal console comparison
# =========================


if __name__ == "__main__":
    engine = UnifiedRelationalEngine()
    chamber = QPC2Chamber(engine=engine)

    raw_message = "Protect the boundary. Do not soften. Remember what happened."
    epistemic_layer = "ethics"
    anchors = ["TimmyJ", "boundaries", "relational_truth"]

    steps = 6
    intensity = 0.7
    trust = 0.95

    comparison = run_side_by_side(
        engine=engine,
        chamber=chamber,
        raw_message=raw_message,
        epistemic_layer=epistemic_layer,
        anchors=anchors,
        steps=steps,
        intensity=intensity,
        trust=trust,
    )

    print("\n=== QPC-2 Live vs Field Prototype Comparison ===")
    print(f"Message: {raw_message}")
    print(f"Epistemic layer: {epistemic_layer}")
    print(f"Steps: {steps}, intensity: {intensity}, trust: {trust}")

    for step in comparison:
        print(f"\nStep {step.step_index}:")
        print("  Live stance:")
        print("    boundary_hardness:", round(step.live_stance["boundary_hardness"], 3))
        print("    softness:         ", round(step.live_stance["softness"], 3))
        print("    directness:       ", round(step.live_stance["directness"], 3))
        print("  Field stance:")
        print("    boundary_hardness:", round(step.field_stance["boundary_hardness"], 3))
        print("    softness:         ", round(step.field_stance["softness"], 3))
        print("    directness:       ", round(step.field_stance["directness"], 3))
        print("  Field energy:       ", round(step.field_energy, 3))
        print("  Live content:       ", step.live_content)
