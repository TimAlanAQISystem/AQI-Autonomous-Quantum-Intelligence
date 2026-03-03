"""
Minimal CLI runner for the QPC prototype.
Builds a sample QPC, evaluates a context, prints the decision.
"""
from __future__ import annotations

from qpc_prototype import (
    MultiWaveReasoner,
    QPC,
    Wave,
    WaveType,
    log_eval,
)


# Example evaluation functions (replace with real logic later)
@log_eval
def protect_merchant(context):
    return context.get("risk_level", 0.0)


@log_eval
def optimize_surplus(context):
    return context.get("surplus_potential", 0.0)


@log_eval
def deescalate(context):
    return context.get("conflict_intensity", 0.0)


@log_eval
def observe_only(context):
    return 0.1


@log_eval
def cadence_sync(context):
    return context.get("tempo_alignment", 0.0)


@log_eval
def ethical_guard(context):
    return 1.0 if context.get("ethical_violation", False) else 0.2


def build_sample_qpc() -> QPC:
    qpc = QPC()

    qpc.add_wave(
        Wave(
            name="ProtectMerchant",
            wave_type=WaveType.STANDING,
            amplitude=0.9,
            eval_fn=protect_merchant,
        )
    )

    qpc.add_wave(
        Wave(
            name="OptimizeSurplus",
            wave_type=WaveType.SURPLUS,
            amplitude=0.7,
            eval_fn=optimize_surplus,
        )
    )

    qpc.add_wave(
        Wave(
            name="Deescalate",
            wave_type=WaveType.SUPERPOSITION,
            amplitude=0.8,
            eval_fn=deescalate,
        )
    )

    # Cadence control (transitional)
    qpc.add_wave(
        Wave(
            name="CadenceSync",
            wave_type=WaveType.CADENCE,
            amplitude=0.5,
            eval_fn=cadence_sync,
        )
    )

    # Ethical guard (latent until triggered)
    qpc.add_wave(
        Wave(
            name="ObserveOnly",
            wave_type=WaveType.ETHICAL,
            amplitude=0.6,
            eval_fn=ethical_guard,
        ),
        latent=True,
        activation_fn=lambda ctx: ctx.get("ethical_violation", False),
    )

    # Calibration (latent, activates when uncertainty high)
    qpc.add_wave(
        Wave(
            name="Calibration",
            wave_type=WaveType.CALIBRATION,
            amplitude=0.4,
            eval_fn=observe_only,
        ),
        latent=True,
        activation_fn=lambda ctx: ctx.get("uncertainty", 0.0) >= 0.7,
    )

    return qpc


def main():
    context = {
        "risk_level": 0.8,
        "surplus_potential": 0.6,
        "conflict_intensity": 0.3,
        "tempo_alignment": 0.4,
        "ethical_violation": True,
        "uncertainty": 0.75,
    }

    reasoner = MultiWaveReasoner(qpc=build_sample_qpc())
    result = reasoner.evaluate_context(context)

    print("Decision result:")
    for k, v in result.items():
        print(f"{k}: {v}")

    print("\nVariant space:")
    print(reasoner.qpc.visualize())


if __name__ == "__main__":
    main()
