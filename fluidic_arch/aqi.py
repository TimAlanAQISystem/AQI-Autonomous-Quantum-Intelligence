# aqi.py

from __future__ import annotations
from typing import Dict, Optional
import uuid

from mengine import MEngine, Context, RiskLevel, Hardness
from containers import Container, ContainerLifecycleState
from fluid import MCI, FluidSubstrate, DMAConfig
from forms import Form, FormStep, FormType

from metrics import Metrics


class AQI:
    """
    Orchestrator: interprets intent, uses MEngine, spawns DMAs via MCI, shapes forms.
    """

    def __init__(self, mengine: MEngine) -> None:
        self.mengine = mengine

    def _infer_form_type(self, intent: str) -> FormType:
        intent_lower = intent.lower()
        if "diagnose" in intent_lower or "analyze" in intent_lower:
            return FormType.FLOW
        if "cluster" in intent_lower or "group" in intent_lower:
            return FormType.CLUSTER
        if "outage" in intent_lower or "critical" in intent_lower:
            return FormType.WELL
        return FormType.ORBIT

    def handle_intent(
        self,
        container: Container,
        intent: str,
        role: str,
        risk_level: RiskLevel,
        initial_mass_map: Dict[str, float],
        fields: Dict[str, Any],
        mci: MCI,
        substrate: FluidSubstrate,
    ) -> Optional[Form]:
        # 1. Build context
        ctx = Context(
            container_id=container.spec.container_id,
            intent=intent,
            role=role,
            risk_level=risk_level,
            fields=fields,
            mass_map=initial_mass_map,
        )

        # 2. Governance: MEngine validation
        if not self.mengine.validate_context(ctx):
            print("[AQI] Context validation failed. Aborting.")
            return None

        # 3. Container must be active
        if container.state != ContainerLifecycleState.ACTIVE:
            print("[AQI] Container not active. Aborting.")
            return None

        # 4. Check for existing pattern
        existing_pattern = container.load_form_pattern_for_intent(intent)
        if existing_pattern:
            print("[AQI] Reusing existing form pattern from self-store.")
            Metrics.record_form_reused()
            return Form.from_pattern(existing_pattern)

        # 5. Decide hardness
        hardness = Hardness.TABLET if risk_level != RiskLevel.HIGH else Hardness.TOOL

        # 6. Determine form type
        form_type = self._infer_form_type(intent)

        # 7. Spawn DMAs based on intent (simplified)
        dma_configs = [
            DMAConfig(
                name="fetch_logs",
                role="diagnostics",
                allowed_fields=["env", "client_id"],
                allowed_boundaries=["logs"],
            ),
            DMAConfig(
                name="group_errors",
                role="analytics",
                allowed_fields=["env", "client_id"],
                allowed_boundaries=["logs"],
            ),
            DMAConfig(
                name="summarize",
                role="summary",
                allowed_fields=["env", "client_id"],
                allowed_boundaries=["logs"],
            ),
        ]

        for cfg in dma_configs:
            mci.spawn_dma(cfg, ctx, hardness=hardness)

        # 8. Run DMAs (single tick, as a placeholder for a real event loop)
        mci.step_all(substrate)

        # 9. Build form
        form_id = str(uuid.uuid4())
        form = Form(
            form_id=form_id,
            name="Diagnostics_Flow_v1",
            form_type=form_type,
            hardness=hardness,
            steps=[
                FormStep(dma_name=cfg.name, description=f"Step using {cfg.name}")
                for cfg in dma_configs
            ],
            metadata={"intent": intent, "role": role, "risk": risk_level.name},
        )

        # 10. Store pattern
        container.store_form_pattern(intent, form.to_pattern())
        Metrics.record_form_created()
        return form