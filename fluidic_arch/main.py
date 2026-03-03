# main.py

from __future__ import annotations
from typing import Any, Dict

from mengine import MEngine, FundamentalRule, RiskLevel
from containers import ContainerSpec, Container, ResourceOrgans
from fluid import SignalField, SignalVector, FluidSubstrate, MCI
from aqi import AQI
from config import DEFAULT_ENVIRONMENT

from metrics import Metrics


def setup_mengine() -> MEngine:
    mengine = MEngine()
    mengine.add_axiom(
        FundamentalRule(
            name="no_high_risk_anonymous",
            description="Risk HIGH cannot be handled by anonymous role.",
            check=lambda ctx: not (ctx.risk_level == RiskLevel.HIGH and ctx.role == "anonymous"),
        )
    )
    return mengine


def setup_container() -> Container:
    # Real connector: logs path
    logs_path = "diagnostics.log"  # You can create this file next to the script

    resources = ResourceOrgans(
        execution_substrate={},
        storage={},
        connectors={"logs": logs_path},
        security={"auth_mode": "scoped"},
        context_providers={"env": DEFAULT_ENVIRONMENT.name.lower()},
    )

    spec = ContainerSpec(
        container_id="diagnostics_v1",
        purpose="Diagnostics for communication failures",
        boundaries={"logs": "read_only"},
        resources=resources,
    )
    container = Container(spec=spec)
    container.activate()
    return container


def setup_substrate(container: Container) -> FluidSubstrate:
    signal_field = SignalField(
        vectors={
            "twilio_sms_failure_client_X": SignalVector(dx=0.8, dy=0.3),
            "other_noise": SignalVector(dx=0.1, dy=-0.2),
        }
    )
    substrate = FluidSubstrate(
        container=container,
        signal_field=signal_field,
    )
    return substrate


def example_run() -> None:
    mengine = setup_mengine()
    container = setup_container()
    substrate = setup_substrate(container)
    mci = MCI()
    aqi = AQI(mengine=mengine)

    # Mass + fields
    mass_map: Dict[str, float] = {
        "twilio_sms_failure_client_X": 0.9,
        "other_noise": 0.1,
    }
    fields: Dict[str, Any] = {
        "env": container.spec.resources.context_providers["env"],
        "client_id": "client_X",
    }

    intent = "Diagnose Twilio SMS failures for Client X"

    print("\n=== FIRST RUN (create pattern) ===")
    Metrics.start_run()
    form1 = aqi.handle_intent(
        container=container,
        intent=intent,
        role="operator",
        risk_level=RiskLevel.MEDIUM,
        initial_mass_map=mass_map,
        fields=fields,
        mci=mci,
        substrate=substrate,
    )
    Metrics.end_run()
    if form1:
        print("Form1:", form1.to_pattern())
    print("First run metrics:", Metrics.snapshot())

    print("\n=== SECOND RUN (reuse pattern) ===")
    Metrics.start_run()
    form2 = aqi.handle_intent(
        container=container,
        intent=intent,
        role="operator",
        risk_level=RiskLevel.MEDIUM,
        initial_mass_map=mass_map,
        fields=fields,
        mci=mci,
        substrate=substrate,
    )
    Metrics.end_run()
    if form2:
        print("Form2:", form2.to_pattern())
    print("Second run metrics:", Metrics.snapshot())


if __name__ == "__main__":
    example_run()