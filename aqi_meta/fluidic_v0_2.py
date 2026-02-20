from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional
import math
import uuid
import time


# ============================================================
# 1. FUNDAMENTALS (MEngine)
# ============================================================

class RiskLevel(Enum):
    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()


class Hardness(Enum):
    VAPOR = auto()
    TABLET = auto()
    TOOL = auto()
    STEEL = auto()


@dataclass
class FundamentalRule:
    name: str
    description: str
    check: Callable["Context", bool]


@dataclass
class Context:
    container_id: str
    intent: str
    role: str
    risk_level: RiskLevel
    fields: Dict[str, Any]
    mass_map: Dict[str, float]


class MEngine:
    """
    Natural law of the system: axioms, constraints.
    """

    def __init__(self) -> None:
        self.axioms: List[FundamentalRule] = []
        self.constraints: List[FundamentalRule] = []

    def add_axiom(self, rule: FundamentalRule) -> None:
        self.axioms.append(rule)

    def add_constraint(self, rule: FundamentalRule) -> None:
        self.constraints.append(rule)

    def validate_context(self, ctx: Context) -> bool:
        for rule in self.axioms + self.constraints:
            if not rule.check(ctx):
                print(f"[MENGINE] Rule failed: {rule.name}")
                return False
        return True


# ============================================================
# 2. CONTAINERS
# ============================================================

@dataclass
class ResourceOrgans:
    execution_substrate: Dict[str, Any]
    storage: Dict[str, Any]
    connectors: Dict[str, Any]
    security: Dict[str, Any]
    context_providers: Dict[str, Any]


@dataclass
class ContainerSpec:
    container_id: str
    purpose: str
    boundaries: Dict[str, Any]
    resources: ResourceOrgans
    self_store: Dict[str, Any] = field(default_factory=dict)


class ContainerLifecycleState(Enum):
    CREATED = auto()
    ACTIVE = auto()
    SUSPENDED = auto()
    ARCHIVED = auto()
    DESTROYED = auto()


@dataclass
class Container:
    spec: ContainerSpec
    state: ContainerLifecycleState = ContainerLifecycleState.CREATED

    def activate(self) -> None:
        if self.state in {ContainerLifecycleState.CREATED,
                          ContainerLifecycleState.SUSPENDED}:
            self.state = ContainerLifecycleState.ACTIVE
            print(f"[CONTAINER] Activated: {self.spec.container_id}")

    def suspend(self) -> None:
        if self.state == ContainerLifecycleState.ACTIVE:
            self.state = ContainerLifecycleState.SUSPENDED
            print(f"[CONTAINER] Suspended: {self.spec.container_id}")

    def archive(self) -> None:
        self.state = ContainerLifecycleState.ARCHIVED
        print(f"[CONTAINER] Archived: {self.spec.container_id}")

    def destroy(self) -> None:
        self.state = ContainerLifecycleState.DESTROYED
        print(f"[CONTAINER] Destroyed: {self.spec.container_id}")

    def store_form_pattern(self, form: "Form") -> None:
        # key by intent for reuse (simple heuristic)
        intent_key = form.metadata.get("intent", "unknown")
        self.spec.self_store[intent_key] = form.to_pattern()
        print(f"[CONTAINER] Stored form pattern for intent: {intent_key}")

    def load_form_pattern_for_intent(self, intent: str) -> Optional[Dict[str, Any]]:
        return self.spec.self_store.get(intent)


# ============================================================
# 3. FLUID LAYER: DMAs, MCI, Substrate
# ============================================================

@dataclass
class DMAConfig:
    name: str
    role: str
    allowed_fields: List[str]
    allowed_boundaries: List[str]
    max_lifetime_sec: float = 30.0


class DMAState(Enum):
    SPAWNED = auto()
    RUNNING = auto()
    COMPLETED = auto()
    TERMINATED = auto()


@dataclass
class SignalVector:
    dx: float
    dy: float

    def magnitude(self) -> float:
        return math.sqrt(self.dx ** 2 + self.dy ** 2)


@dataclass
class SignalField:
    """
    Discrete vector field: entity_id -> SignalVector.
    """
    vectors: Dict[str, SignalVector]

    def divergence(self) -> Dict[str, float]:
        # crude surrogate: dx + dy
        return {eid: vec.dx + vec.dy for eid, vec in self.vectors.items()}

    def curl(self) -> Dict[str, float]:
        # crude surrogate: dx - dy
        return {eid: vec.dx - vec.dy for eid, vec in self.vectors.items()}


@dataclass
class FluidSubstrate:
    """
    Represents the space DMAs operate in.
    """
    state_space: Dict[str, Any]
    signal_field: SignalField


@dataclass
class DMA:
    dma_id: str
    config: DMAConfig
    context: Context
    created_at: float = field(default_factory=time.time)
    state: DMAState = DMAState.SPAWNED
    local_data: Dict[str, Any] = field(default_factory=dict)

    def step(self, substrate: FluidSubstrate) -> None:
        """
        Minimal but real: inspect mass + divergence + curl and log a coherent decision.
        """
        if self.state in {DMAState.COMPLETED, DMAState.TERMINATED}:
            return

        self.state = DMAState.RUNNING

        mass_map = self.context.mass_map
        div_map = substrate.signal_field.divergence()
        curl_map = substrate.signal_field.curl()

        # choose an entity that is both high mass and high positive divergence (surplus)
        target_id = None
        best_score = -1e9

        for eid, mass in mass_map.items():
            div = div_map.get(eid, 0.0)
            curl = curl_map.get(eid, 0.0)
            # simple heuristic: prioritize high mass, positive divergence, low |curl|
            score = mass * 1.0 + div * 0.5 - abs(curl) * 0.2
            if score > best_score:
                best_score = score
                target_id = eid

        if target_id is not None:
            print(
                f"[DMA:{self.config.name}] "
                f"Target={target_id}, mass={mass_map[target_id]:.3f}, "
                f"div={div_map.get(target_id, 0):.3f}, "
                f"curl={curl_map.get(target_id, 0):.3f}"
            )
            self.local_data["target"] = target_id
        else:
            print(f"[DMA:{self.config.name}] No meaningful target found.")

        # placeholder: one step => complete
        self.state = DMAState.COMPLETED

    def expired(self) -> bool:
        return (time.time() - self.created_at) > self.config.max_lifetime_sec


class MCI:
    """
    Micro Capability Interface: spawns, routes, dissolves DMAs.
    Uses a simple "hardness budget" to limit active DMAs.
    """

    def __init__(self, base_max_active_dmas: int = 16) -> None:
        self.base_max_active_dmas = base_max_active_dmas
        self.active_dmas: Dict[str, DMA] = {}

    def _hardness_multiplier(self, hardness: Hardness) -> float:
        if hardness == Hardness.VAPOR:
            return 1.0
        if hardness == Hardness.TABLET:
            return 0.75
        if hardness == Hardness.TOOL:
            return 0.5
        if hardness == Hardness.STEEL:
            return 0.25
        return 1.0

    def max_active_for_hardness(self, hardness: Hardness) -> int:
        return max(1, int(self.base_max_active_dmas * self._hardness_multiplier(hardness)))

    def spawn_dma(self, config: DMAConfig, ctx: Context, hardness: Hardness) -> DMA:
        if len(self.active_dmas) >= self.max_active_for_hardness(hardness):
            print("[MCI] DMA limit reached for current hardness, cannot spawn.")
            raise RuntimeError("DMA limit reached")
        dma_id = str(uuid.uuid4())
        dma = DMA(dma_id=dma_id, config=config, context=ctx)
        self.active_dmas[dma_id] = dma
        print(f"[MCI] Spawned DMA: {config.name} ({dma_id})")
        return dma

    def step_all(self, substrate: FluidSubstrate) -> None:
        for dma_id, dma in list(self.active_dmas.items()):
            dma.step(substrate)
            if dma.state in {DMAState.COMPLETED, DMAState.TERMINATED} or dma.expired():
                print(f"[MCI] Retiring DMA: {dma.config.name} ({dma_id})")
                del self.active_dmas[dma_id]


# ============================================================
# 4. FORMS
# ============================================================

@dataclass
class FormStep:
    dma_name: str
    description: str


@dataclass
class Form:
    form_id: str
    name: str
    hardness: Hardness
    steps: List[FormStep]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_pattern(self) -> Dict[str, Any]:
        return {
            "form_id": self.form_id,
            "name": self.name,
            "hardness": self.hardness.name,
            "steps": [step.__dict__ for step in self.steps],
            "metadata": self.metadata,
        }


# ============================================================
# 5. AQI (INTELLIGENT FIELD)
# ============================================================

class AQI:
    """
    Simplified orchestrator: interprets intent, uses MEngine, spawns DMAs via MCI, shapes forms.
    """

    def __init__(self, mengine: MEngine) -> None:
        self.mengine = mengine

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

        # 4. Check for existing pattern in self-store (reuse)
        existing_pattern = container.load_form_pattern_for_intent(intent)
        if existing_pattern:
            print("[AQI] Reusing existing form pattern from self-store.")
            # In a real system, we'd adapt/extend this.
            # Here, we just reconstruct a Form object.
            steps = [
                FormStep(dma_name=s["dma_name"], description=s["description"])
                for s in existing_pattern.get("steps", [])
            ]
            return Form(
                form_id=existing_pattern["form_id"],
                name=existing_pattern["name"],
                hardness=Hardness[existing_pattern["hardness"]],
                steps=steps,
                metadata=existing_pattern.get("metadata", {}),
            )

        # 5. Decide hardness for this intent (simple heuristic)
        if risk_level == RiskLevel.HIGH:
            hardness = Hardness.TOOL
        else:
            hardness = Hardness.TABLET

        # 6. Spawn a few diagnostic DMAs based on intent
        dma_configs = [
            DMAConfig(
                name="fetch_logs",
                role="diagnostics",
                allowed_fields=["env", "merchant_id"],
                allowed_boundaries=["logs", "twilio"],
            ),
            DMAConfig(
                name="group_errors",
                role="analytics",
                allowed_fields=["env", "merchant_id"],
                allowed_boundaries=["logs"],
            ),
            DMAConfig(
                name="summarize",
                role="summary",
                allowed_fields=["env", "merchant_id"],
                allowed_boundaries=["logs"],
            ),
        ]

        for cfg in dma_configs:
            mci.spawn_dma(cfg, ctx, hardness=hardness)

        # 7. Run DMAs once (event-loop placeholder)
        mci.step_all(substrate)

        # 8. Build a Form representing what was done
        form_id = str(uuid.uuid4())
        form = Form(
            form_id=form_id,
            name="Diagnostics_Flow_v1",
            hardness=hardness,
            steps=[
                FormStep(dma_name=cfg.name, description=f"Step using {cfg.name}")
                for cfg in dma_configs
            ],
            metadata={"intent": intent, "role": role, "risk": risk_level.name},
        )

        # 9. Store pattern in container
        container.store_form_pattern(form)
        return form


# ============================================================
# 6. LATTICE (placeholder, not yet wired in behavior)
# ============================================================

@dataclass
class LatticeNode:
    node_id: str
    label: str
    coherence_weight: float


@dataclass
class LatticeEdge:
    source: str
    target: str
    strength: float


@dataclass
class LatticeRegion:
    name: str
    node_ids: List[str]


@dataclass
class Lattice:
    nodes: Dict[str, LatticeNode]
    edges: List[LatticeEdge]
    regions: List[LatticeRegion]

    def coherence_score(self) -> float:
        score = 0.0
        for edge in self.edges:
            src = self.nodes[edge.source]
            tgt = self.nodes[edge.target]
            score += edge.strength * (src.coherence_weight + tgt.coherence_weight) / 2.0
        return score


# ============================================================
# 7. EXAMPLE RUN (META-SANDBOX)
# ============================================================

def example_run() -> None:
    # 1. MEngine with one simple axiom
    mengine = MEngine()
    mengine.add_axiom(
        FundamentalRule(
            name="no_high_risk_anonymous",
            description="Risk HIGH cannot be handled by anonymous role.",
            check=lambda ctx: not (ctx.risk_level == RiskLevel.HIGH and ctx.role == "anonymous"),
        )
    )

    # 2. Container
    container_spec = ContainerSpec(
        container_id="diagnostics_v1",
        purpose="Diagnostics for communication failures",
        boundaries={"twilio": "read_only", "logs": "read_only"},
        resources=ResourceOrgans(
            execution_substrate={},
            storage={},
            connectors={"twilio": "TWILIO_API_STUB", "logs": "LOG_STORE_STUB"},
            security={"auth_mode": "scoped"},
            context_providers={"env": "prod"},
        ),
    )
    container = Container(spec=container_spec)
    container.activate()

    # 3. Simple signal field: two entities
    signal_field = SignalField(
        vectors={
            "twilio_sms_failure_merchant_X": SignalVector(dx=0.8, dy=0.3),
            "other_noise": SignalVector(dx=0.1, dy=-0.2),
        }
    )

    substrate = FluidSubstrate(
        state_space={"logs": [], "twilio": []},
        signal_field=signal_field,
    )

    # 4. MCI
    mci = MCI(base_max_active_dmas=8)

    # 5. AQI
    aqi = AQI(mengine=mengine)

    # 6. Mass and fields
    mass_map = {
        "twilio_sms_failure_merchant_X": 0.9,
        "other_noise": 0.1,
    }
    fields = {
        "env": "prod",
        "merchant_id": "merchant_X",
    }

    # 7. First run: creates a new form and stores it
    print("\n=== FIRST RUN ===")
    form1 = aqi.handle_intent(
        container=container,
        intent="Diagnose Twilio SMS failures for Merchant X",
        role="operator",
        risk_level=RiskLevel.MEDIUM,
        initial_mass_map=mass_map,
        fields=fields,
        mci=mci,
        substrate=substrate,
    )
    if form1:
        print("Form1:", form1.to_pattern())

    # 8. Second run with same intent: should reuse stored pattern
    print("\n=== SECOND RUN (REUSE) ===")
    form2 = aqi.handle_intent(
        container=container,
        intent="Diagnose Twilio SMS failures for Merchant X",
        role="operator",
        risk_level=RiskLevel.MEDIUM,
        initial_mass_map=mass_map,
        fields=fields,
        mci=mci,
        substrate=substrate,
    )
    if form2:
        print("Form2:", form2.to_pattern())


if __name__ == "__main__":
    example_run()