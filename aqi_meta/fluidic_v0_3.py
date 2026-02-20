from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set
import math
import uuid
import time
import logging
from contextlib import contextmanager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


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

    def validate(self) -> bool:
        """Basic input validation"""
        if not self.container_id or not self.intent or not self.role:
            return False
        if not isinstance(self.fields, dict) or not isinstance(self.mass_map, dict):
            return False
        return True


class MEngine:
    """
    Natural law of the system: axioms, constraints with enhanced validation.
    """

    def __init__(self) -> None:
        self.axioms: List[FundamentalRule] = []
        self.constraints: List[FundamentalRule] = []
        self.violation_count: Dict[str, int] = {}

    def add_axiom(self, rule: FundamentalRule) -> None:
        self.axioms.append(rule)
        logger.info(f"Added axiom: {rule.name}")

    def add_constraint(self, rule: FundamentalRule) -> None:
        self.constraints.append(rule)
        logger.info(f"Added constraint: {rule.name}")

    def validate_context(self, ctx: Context) -> bool:
        """Enhanced validation with metrics"""
        if not ctx.validate():
            logger.error(f"[MENGINE] Context validation failed: invalid structure")
            return False

        for rule in self.axioms + self.constraints:
            try:
                if not rule.check(ctx):
                    rule_name = rule.name
                    self.violation_count[rule_name] = self.violation_count.get(rule_name, 0) + 1
                    logger.warning(f"[MENGINE] Rule failed: {rule_name} (violations: {self.violation_count[rule_name]})")
                    return False
            except Exception as e:
                logger.error(f"[MENGINE] Rule execution error in {rule.name}: {e}")
                return False
        return True

    def get_violation_stats(self) -> Dict[str, int]:
        return self.violation_count.copy()


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
    max_patterns: int = 100  # Limit stored patterns


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
    created_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)

    def activate(self) -> None:
        if self.state in {ContainerLifecycleState.CREATED, ContainerLifecycleState.SUSPENDED}:
            self.state = ContainerLifecycleState.ACTIVE
            self.last_active = time.time()
            logger.info(f"[CONTAINER] Activated: {self.spec.container_id}")
        else:
            raise ValueError(f"Cannot activate container in state: {self.state}")

    def suspend(self) -> None:
        if self.state == ContainerLifecycleState.ACTIVE:
            self.state = ContainerLifecycleState.SUSPENDED
            logger.info(f"[CONTAINER] Suspended: {self.spec.container_id}")
        else:
            logger.warning(f"[CONTAINER] Cannot suspend container in state: {self.state}")

    def archive(self) -> None:
        self.state = ContainerLifecycleState.ARCHIVED
        logger.info(f"[CONTAINER] Archived: {self.spec.container_id}")

    def destroy(self) -> None:
        self.state = ContainerLifecycleState.DESTROYED
        logger.info(f"[CONTAINER] Destroyed: {self.spec.container_id}")

    def store_form_pattern(self, form: "Form") -> None:
        """Enhanced pattern storage with limits"""
        intent_key = form.metadata.get("intent", "unknown")

        # Enforce pattern limit (LRU eviction)
        if len(self.spec.self_store) >= self.spec.max_patterns:
            # Remove oldest pattern (simple heuristic)
            oldest_key = min(self.spec.self_store.keys(),
                           key=lambda k: self.spec.self_store[k].get("stored_at", 0))
            del self.spec.self_store[oldest_key]
            logger.info(f"[CONTAINER] Evicted old pattern: {oldest_key}")

        # Store with timestamp
        pattern = form.to_pattern()
        pattern["stored_at"] = time.time()
        self.spec.self_store[intent_key] = pattern
        logger.info(f"[CONTAINER] Stored form pattern for intent: {intent_key}")

    def load_form_pattern_for_intent(self, intent: str) -> Optional[Dict[str, Any]]:
        pattern = self.spec.self_store.get(intent)
        if pattern:
            logger.debug(f"[CONTAINER] Loaded pattern for intent: {intent}")
        return pattern

    def cleanup_expired_patterns(self, max_age_seconds: float = 3600*24) -> int:
        """Remove patterns older than max_age"""
        current_time = time.time()
        expired_keys = [
            key for key, pattern in self.spec.self_store.items()
            if (current_time - pattern.get("stored_at", 0)) > max_age_seconds
        ]
        for key in expired_keys:
            del self.spec.self_store[key]
        if expired_keys:
            logger.info(f"[CONTAINER] Cleaned up {len(expired_keys)} expired patterns")
        return len(expired_keys)


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
    priority: int = 1  # 1=low, 5=high


class DMAState(Enum):
    SPAWNED = auto()
    RUNNING = auto()
    COMPLETED = auto()
    TERMINATED = auto()
    ERROR = auto()


@dataclass
class SignalVector:
    dx: float
    dy: float

    def magnitude(self) -> float:
        return math.sqrt(self.dx ** 2 + self.dy ** 2)

    def normalize(self) -> 'SignalVector':
        mag = self.magnitude()
        if mag == 0:
            return SignalVector(0, 0)
        return SignalVector(self.dx / mag, self.dy / mag)


@dataclass
class SignalField:
    """
    Discrete vector field with enhanced validation.
    """
    vectors: Dict[str, SignalVector]

    def validate(self) -> bool:
        """Ensure all vectors are valid"""
        return all(isinstance(v, SignalVector) and
                  math.isfinite(v.dx) and math.isfinite(v.dy)
                  for v in self.vectors.values())

    def divergence(self) -> Dict[str, float]:
        """Enhanced divergence calculation"""
        return {eid: vec.dx + vec.dy for eid, vec in self.vectors.items()}

    def curl(self) -> Dict[str, float]:
        """Enhanced curl calculation"""
        return {eid: vec.dx - vec.dy for eid, vec in self.vectors.items()}

    def gradient_magnitude(self) -> Dict[str, float]:
        """Additional field property"""
        return {eid: vec.magnitude() for eid, vec in self.vectors.items()}


@dataclass
class FluidSubstrate:
    """
    Enhanced execution space with validation.
    """
    state_space: Dict[str, Any]
    signal_field: SignalField

    def validate(self) -> bool:
        """Validate substrate integrity"""
        return (isinstance(self.state_space, dict) and
                self.signal_field.validate())


@dataclass
class DMA:
    dma_id: str
    config: DMAConfig
    context: Context
    created_at: float = field(default_factory=time.time)
    state: DMAState = DMAState.SPAWNED
    local_data: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None

    def validate_access(self, field_name: str = None, boundary_name: str = None) -> bool:
        """Enforce boundary and field access controls"""
        if field_name and field_name not in self.config.allowed_fields:
            self.error_message = f"Access denied to field: {field_name}"
            return False
        if boundary_name and boundary_name not in self.config.allowed_boundaries:
            self.error_message = f"Access denied to boundary: {boundary_name}"
            return False
        return True

    def step(self, substrate: FluidSubstrate) -> None:
        """
        Enhanced DMA logic with error handling and access control.
        """
        try:
            if self.state in {DMAState.COMPLETED, DMAState.TERMINATED, DMAState.ERROR}:
                return

            if not substrate.validate():
                self.state = DMAState.ERROR
                self.error_message = "Invalid substrate"
                return

            self.state = DMAState.RUNNING

            # Validate access to required fields
            required_fields = ["env", "merchant_id"]
            for field in required_fields:
                if field in self.context.fields and not self.validate_access(field_name=field):
                    self.state = DMAState.ERROR
                    return

            mass_map = self.context.mass_map
            div_map = substrate.signal_field.divergence()
            curl_map = substrate.signal_field.curl()
            grad_map = substrate.signal_field.gradient_magnitude()

            # Enhanced decision logic
            target_id = None
            best_score = -1e9

            for eid, mass in mass_map.items():
                if not math.isfinite(mass) or mass < 0:
                    continue

                div = div_map.get(eid, 0.0)
                curl = curl_map.get(eid, 0.0)
                grad = grad_map.get(eid, 0.0)

                # Enhanced scoring with gradient and validation
                score = (mass * 1.0 +
                        div * 0.5 +
                        grad * 0.3 -
                        abs(curl) * 0.2)

                if math.isfinite(score) and score > best_score:
                    best_score = score
                    target_id = eid

            if target_id is not None:
                logger.info(
                    f"[DMA:{self.config.name}] "
                    f"Target={target_id}, mass={mass_map[target_id]:.3f}, "
                    f"div={div_map.get(target_id, 0):.3f}, "
                    f"curl={curl_map.get(target_id, 0):.3f}, "
                    f"grad={grad_map.get(target_id, 0):.3f}"
                )
                self.local_data["target"] = target_id
                self.local_data["confidence"] = best_score
                self.state = DMAState.COMPLETED
            else:
                logger.warning(f"[DMA:{self.config.name}] No meaningful target found.")
                self.state = DMAState.TERMINATED

        except Exception as e:
            logger.error(f"[DMA:{self.config.name}] Step failed: {e}")
            self.state = DMAState.ERROR
            self.error_message = str(e)

    def expired(self) -> bool:
        return (time.time() - self.created_at) > self.config.max_lifetime_sec

    def get_metrics(self) -> Dict[str, Any]:
        """DMA performance metrics"""
        return {
            "dma_id": self.dma_id,
            "name": self.config.name,
            "state": self.state.name,
            "age": time.time() - self.created_at,
            "has_error": self.error_message is not None,
            "target_found": "target" in self.local_data
        }


class MCI:
    """
    Enhanced Micro Capability Interface with monitoring and stability.
    """

    def __init__(self, base_max_active_dmas: int = 16) -> None:
        self.base_max_active_dmas = base_max_active_dmas
        self.active_dmas: Dict[str, DMA] = {}
        self.completed_dmas: List[DMA] = []
        self.max_completed_history = 100
        self.error_count = 0

    def _hardness_multiplier(self, hardness: Hardness) -> float:
        multipliers = {
            Hardness.VAPOR: 1.0,
            Hardness.TABLET: 0.75,
            Hardness.TOOL: 0.5,
            Hardness.STEEL: 0.25
        }
        return multipliers.get(hardness, 1.0)

    def max_active_for_hardness(self, hardness: Hardness) -> int:
        return max(1, int(self.base_max_active_dmas * self._hardness_multiplier(hardness)))

    def spawn_dma(self, config: DMAConfig, ctx: Context, hardness: Hardness) -> DMA:
        """Enhanced spawning with validation"""
        max_active = self.max_active_for_hardness(hardness)

        if len(self.active_dmas) >= max_active:
            logger.warning(f"[MCI] DMA limit reached ({max_active}) for {hardness.name}, cannot spawn {config.name}.")
            raise RuntimeError(f"DMA limit reached for {hardness.name}")

        # Validate config
        if not config.name or not config.allowed_fields or not config.allowed_boundaries:
            raise ValueError(f"Invalid DMA config: {config.name}")

        dma_id = str(uuid.uuid4())
        dma = DMA(dma_id=dma_id, config=config, context=ctx)
        self.active_dmas[dma_id] = dma
        logger.info(f"[MCI] Spawned DMA: {config.name} ({dma_id}) - Active: {len(self.active_dmas)}/{max_active}")
        return dma

    def step_all(self, substrate: FluidSubstrate) -> Dict[str, Any]:
        """Enhanced stepping with metrics"""
        metrics = {
            "stepped": 0,
            "completed": 0,
            "terminated": 0,
            "errors": 0,
            "retired": 0
        }

        for dma_id, dma in list(self.active_dmas.items()):
            dma.step(substrate)
            metrics["stepped"] += 1

            if dma.state in {DMAState.COMPLETED, DMAState.TERMINATED, DMAState.ERROR} or dma.expired():
                if dma.state == DMAState.ERROR:
                    metrics["errors"] += 1
                    self.error_count += 1
                elif dma.state == DMAState.COMPLETED:
                    metrics["completed"] += 1
                elif dma.state == DMAState.TERMINATED:
                    metrics["terminated"] += 1

                # Move to completed history
                self.completed_dmas.append(dma)
                if len(self.completed_dmas) > self.max_completed_history:
                    self.completed_dmas.pop(0)

                logger.debug(f"[MCI] Retiring DMA: {dma.config.name} ({dma_id}) - State: {dma.state.name}")
                del self.active_dmas[dma_id]
                metrics["retired"] += 1

        return metrics

    def get_system_metrics(self) -> Dict[str, Any]:
        """System-wide MCI metrics"""
        return {
            "active_dmas": len(self.active_dmas),
            "completed_history": len(self.completed_dmas),
            "total_errors": self.error_count,
            "error_rate": self.error_count / max(1, len(self.completed_dmas) + len(self.active_dmas))
        }

    def force_cleanup(self) -> int:
        """Force cleanup of stuck DMAs"""
        stuck_count = 0
        current_time = time.time()

        for dma_id, dma in list(self.active_dmas.items()):
            if (dma.state == DMAState.RUNNING and
                (current_time - dma.created_at) > dma.config.max_lifetime_sec * 2):
                logger.warning(f"[MCI] Force terminating stuck DMA: {dma.config.name} ({dma_id})")
                dma.state = DMAState.TERMINATED
                self.completed_dmas.append(dma)
                del self.active_dmas[dma_id]
                stuck_count += 1

        return stuck_count


# ============================================================
# 4. FORMS
# ============================================================

class FormType(Enum):
    CLUSTER = auto()  # Group related entities
    FLOW = auto()     # Process sequence
    WELL = auto()     # Resource container
    ORBIT = auto()    # Cyclic pattern


@dataclass
class FormStep:
    dma_name: str
    description: str
    priority: int = 1
    dependencies: List[str] = field(default_factory=list)


@dataclass
class Form:
    form_id: str
    name: str
    hardness: Hardness
    form_type: FormType
    steps: List[FormStep]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> bool:
        """Form validation"""
        return (self.form_id and self.name and
                isinstance(self.steps, list) and
                all(isinstance(step, FormStep) for step in self.steps))

    def to_pattern(self) -> Dict[str, Any]:
        """Enhanced serialization"""
        return {
            "form_id": self.form_id,
            "name": self.name,
            "hardness": self.hardness.name,
            "form_type": self.form_type.name,
            "steps": [{"dma_name": s.dma_name, "description": s.description,
                      "priority": s.priority, "dependencies": s.dependencies}
                     for s in self.steps],
            "metadata": self.metadata,
            "created_at": time.time()
        }

    def get_execution_order(self) -> List[FormStep]:
        """Return steps in priority order"""
        return sorted(self.steps, key=lambda s: s.priority, reverse=True)


# ============================================================
# 5. AQI (INTELLIGENT FIELD)
# ============================================================

class AQI:
    """
    Enhanced orchestrator with stability and monitoring.
    """

    def __init__(self, mengine: MEngine) -> None:
        self.mengine = mengine
        self.intent_history: Dict[str, List[Dict[str, Any]]] = {}
        self.max_history_per_intent = 10

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
        form_type: FormType = FormType.FLOW,
    ) -> Optional[Form]:
        """Enhanced intent handling with error recovery"""
        start_time = time.time()

        try:
            # 1. Build and validate context
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
                logger.error("[AQI] Context validation failed. Aborting.")
                return None

            # 3. Container must be active
            if container.state != ContainerLifecycleState.ACTIVE:
                logger.error("[AQI] Container not active. Aborting.")
                return None

            # 4. Check for existing pattern in self-store (reuse)
            existing_pattern = container.load_form_pattern_for_intent(intent)
            if existing_pattern:
                logger.info("[AQI] Reusing existing form pattern from self-store.")
                try:
                    steps = [
                        FormStep(dma_name=s["dma_name"], description=s["description"],
                                priority=s.get("priority", 1), dependencies=s.get("dependencies", []))
                        for s in existing_pattern.get("steps", [])
                    ]
                    form = Form(
                        form_id=existing_pattern["form_id"],
                        name=existing_pattern["name"],
                        hardness=Hardness[existing_pattern["hardness"]],
                        form_type=FormType[existing_pattern.get("form_type", "FLOW")],
                        steps=steps,
                        metadata=existing_pattern.get("metadata", {}),
                    )
                    if form.validate():
                        return form
                    else:
                        logger.warning("[AQI] Invalid cached form, regenerating.")
                except (KeyError, ValueError) as e:
                    logger.warning(f"[AQI] Error loading cached form: {e}, regenerating.")

            # 5. Determine hardness and form type based on intent analysis
            hardness = self._determine_hardness(intent, risk_level)
            if form_type == FormType.FLOW:  # Auto-determine if not specified
                form_type = self._determine_form_type(intent)

            # 6. Generate DMA configs based on intent and form type
            dma_configs = self._generate_dma_configs(intent, form_type, fields)

            # 7. Spawn DMAs with error handling
            spawned_dmas = []
            for cfg in dma_configs:
                try:
                    dma = mci.spawn_dma(cfg, ctx, hardness=hardness)
                    spawned_dmas.append(dma)
                except RuntimeError as e:
                    logger.warning(f"[AQI] Failed to spawn DMA {cfg.name}: {e}")
                    continue

            if not spawned_dmas:
                logger.error("[AQI] No DMAs could be spawned. Aborting.")
                return None

            # 8. Run DMAs
            metrics = mci.step_all(substrate)

            # 9. Build Form with enhanced metadata
            form_id = str(uuid.uuid4())
            form = Form(
                form_id=form_id,
                name=f"{form_type.name.title()}_Flow_v1",
                hardness=hardness,
                form_type=form_type,
                steps=[
                    FormStep(dma_name=cfg.name, description=f"Execute {cfg.name} for {intent}",
                            priority=cfg.priority)
                    for cfg in dma_configs
                ],
                metadata={
                    "intent": intent,
                    "role": role,
                    "risk": risk_level.name,
                    "execution_time": time.time() - start_time,
                    "dma_metrics": metrics,
                    "form_type": form_type.name
                },
            )

            # 10. Store pattern in container
            container.store_form_pattern(form)

            # 11. Update intent history
            if intent not in self.intent_history:
                self.intent_history[intent] = []
            self.intent_history[intent].append({
                "timestamp": time.time(),
                "form_id": form_id,
                "success": True,
                "metrics": metrics
            })
            # Keep only recent history
            if len(self.intent_history[intent]) > self.max_history_per_intent:
                self.intent_history[intent].pop(0)

            logger.info(f"[AQI] Successfully handled intent '{intent}' in {time.time() - start_time:.2f}s")
            return form

        except Exception as e:
            logger.error(f"[AQI] Intent handling failed: {e}")
            # Update history with failure
            if intent not in self.intent_history:
                self.intent_history[intent] = []
            self.intent_history[intent].append({
                "timestamp": time.time(),
                "error": str(e),
                "success": False
            })
            return None

    def _determine_hardness(self, intent: str, risk_level: RiskLevel) -> Hardness:
        """Intelligent hardness determination"""
        if risk_level == RiskLevel.HIGH:
            return Hardness.TOOL
        elif risk_level == RiskLevel.MEDIUM:
            return Hardness.TABLET
        else:
            # Analyze intent for complexity
            if any(keyword in intent.lower() for keyword in ["diagnose", "analyze", "complex"]):
                return Hardness.TABLET
            else:
                return Hardness.VAPOR

    def _determine_form_type(self, intent: str) -> FormType:
        """Intelligent form type determination"""
        intent_lower = intent.lower()
        if "group" in intent_lower or "cluster" in intent_lower:
            return FormType.CLUSTER
        elif "sequence" in intent_lower or "process" in intent_lower:
            return FormType.FLOW
        elif "resource" in intent_lower or "store" in intent_lower:
            return FormType.WELL
        elif "cycle" in intent_lower or "repeat" in intent_lower:
            return FormType.ORBIT
        else:
            return FormType.FLOW  # Default

    def _generate_dma_configs(self, intent: str, form_type: FormType, fields: Dict[str, Any]) -> List[DMAConfig]:
        """Generate appropriate DMA configs based on intent and form type"""
        base_configs = [
            DMAConfig(
                name="analyze_context",
                role="analysis",
                allowed_fields=["env", "merchant_id"],
                allowed_boundaries=["logs", "context"],
                priority=3
            ),
            DMAConfig(
                name="process_data",
                role="processing",
                allowed_fields=["env", "merchant_id"],
                allowed_boundaries=["logs", "data"],
                priority=2
            ),
            DMAConfig(
                name="generate_output",
                role="synthesis",
                allowed_fields=["env", "merchant_id"],
                allowed_boundaries=["logs", "output"],
                priority=1
            ),
        ]

        # Customize based on form type
        if form_type == FormType.CLUSTER:
            base_configs.append(DMAConfig(
                name="cluster_entities",
                role="clustering",
                allowed_fields=["env", "merchant_id"],
                allowed_boundaries=["logs", "clusters"],
                priority=4
            ))
        elif form_type == FormType.WELL:
            base_configs.append(DMAConfig(
                name="manage_resources",
                role="resource_management",
                allowed_fields=["env", "merchant_id"],
                allowed_boundaries=["storage", "resources"],
                priority=4
            ))

        return base_configs

    def get_intent_history(self, intent: str) -> List[Dict[str, Any]]:
        """Get execution history for an intent"""
        return self.intent_history.get(intent, []).copy()

    def get_system_health(self) -> Dict[str, Any]:
        """Overall system health metrics"""
        total_intents = len(self.intent_history)
        successful_intents = sum(
            1 for history in self.intent_history.values()
            for entry in history
            if entry.get("success", False)
        )
        failed_intents = sum(
            1 for history in self.intent_history.values()
            for entry in history
            if not entry.get("success", True)
        )

        return {
            "total_intents_processed": total_intents,
            "successful_intents": successful_intents,
            "failed_intents": failed_intents,
            "success_rate": successful_intents / max(1, successful_intents + failed_intents),
            "mengine_violations": self.mengine.get_violation_stats()
        }


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
# 7. PRODUCTION ENHANCEMENTS
# ============================================================

@contextmanager
def fluid_session(container: Container, mci: MCI):
    """Context manager for fluid operations with cleanup"""
    try:
        if container.state != ContainerLifecycleState.ACTIVE:
            container.activate()
        yield
    finally:
        # Cleanup stuck DMAs
        stuck_count = mci.force_cleanup()
        if stuck_count > 0:
            logger.info(f"Session cleanup: terminated {stuck_count} stuck DMAs")

        # Cleanup expired patterns
        expired_count = container.cleanup_expired_patterns()
        if expired_count > 0:
            logger.info(f"Session cleanup: removed {expired_count} expired patterns")


class FluidSystem:
    """Production-ready system wrapper"""

    def __init__(self, base_max_dmas: int = 16):
        self.mengine = MEngine()
        self.mci = MCI(base_max_active_dmas=base_max_dmas)
        self.aqi = AQI(self.mengine)
        self.containers: Dict[str, Container] = {}
        self.lattice = Lattice(nodes={}, edges=[], regions=[])

    def create_container(self, spec: ContainerSpec) -> Container:
        """Create and register a container"""
        if spec.container_id in self.containers:
            raise ValueError(f"Container {spec.container_id} already exists")

        container = Container(spec=spec)
        self.containers[spec.container_id] = container
        logger.info(f"Created container: {spec.container_id}")
        return container

    def get_container(self, container_id: str) -> Optional[Container]:
        return self.containers.get(container_id)

    def process_intent(self, container_id: str, intent: str, role: str,
                       risk_level: RiskLevel, mass_map: Dict[str, float],
                       fields: Dict[str, Any], substrate: FluidSubstrate,
                       form_type: FormType = FormType.FLOW) -> Optional[Form]:

        container = self.get_container(container_id)
        if not container:
            logger.error(f"Container not found: {container_id}")
            return None

        with fluid_session(container, self.mci):
            return self.aqi.handle_intent(
                container=container,
                intent=intent,
                role=role,
                risk_level=risk_level,
                initial_mass_map=mass_map,
                fields=fields,
                mci=self.mci,
                substrate=substrate,
                form_type=form_type
            )

    def get_system_status(self) -> Dict[str, Any]:
        """Comprehensive system status"""
        return {
            "containers": {
                cid: {
                    "state": container.state.name,
                    "patterns_stored": len(container.spec.self_store),
                    "age": time.time() - container.created_at
                }
                for cid, container in self.containers.items()
            },
            "mci_metrics": self.mci.get_system_metrics(),
            "aqi_health": self.aqi.get_system_health(),
            "lattice_coherence": self.lattice.coherence_score() if self.lattice.nodes else 0.0
        }


# ============================================================
# 8. EXAMPLE RUN (ENHANCED)
# ============================================================

def example_run() -> None:
    """Enhanced example with production features"""

    # 1. Initialize production system
    system = FluidSystem(base_max_dmas=12)

    # 2. Setup MEngine with enhanced rules
    system.mengine.add_axiom(
        FundamentalRule(
            name="no_high_risk_anonymous",
            description="Risk HIGH cannot be handled by anonymous role.",
            check=lambda ctx: not (ctx.risk_level == RiskLevel.HIGH and ctx.role == "anonymous"),
        )
    )
    system.mengine.add_constraint(
        FundamentalRule(
            name="valid_mass_map",
            description="All mass values must be non-negative finite numbers.",
            check=lambda ctx: all(math.isfinite(m) and m >= 0 for m in ctx.mass_map.values()),
        )
    )

    # 3. Create container with enhanced spec
    container_spec = ContainerSpec(
        container_id="diagnostics_v1_prod",
        purpose="Production diagnostics for communication failures",
        boundaries={"twilio": "read_only", "logs": "read_write", "alerts": "write_only"},
        resources=ResourceOrgans(
            execution_substrate={"cpu_limit": 0.8, "memory_limit": 512},
            storage={"type": "encrypted", "retention_days": 30},
            connectors={"twilio": "TWILIO_API_V2", "logs": "LOG_AGGREGATOR_V3"},
            security={"auth_mode": "oauth2", "encryption": "aes256"},
            context_providers={"env": "prod", "region": "us-east-1"},
        ),
        max_patterns=50
    )
    container = system.create_container(container_spec)
    container.activate()

    # 4. Enhanced signal field with more entities
    signal_field = SignalField(
        vectors={
            "twilio_sms_failure_merchant_X": SignalVector(dx=0.8, dy=0.3),
            "api_timeout_errors": SignalVector(dx=0.6, dy=0.4),
            "network_latency_spikes": SignalVector(dx=0.2, dy=-0.1),
            "successful_transactions": SignalVector(dx=0.1, dy=0.8),
            "other_noise": SignalVector(dx=0.05, dy=-0.15),
        }
    )

    substrate = FluidSubstrate(
        state_space={
            "logs": [],
            "twilio": [],
            "alerts": [],
            "metrics": {"error_rate": 0.02, "latency_ms": 150}
        },
        signal_field=signal_field,
    )

    # 5. Enhanced mass map
    mass_map = {
        "twilio_sms_failure_merchant_X": 0.9,
        "api_timeout_errors": 0.7,
        "network_latency_spikes": 0.4,
        "successful_transactions": 0.2,
        "other_noise": 0.05,
    }
    fields = {
        "env": "prod",
        "merchant_id": "merchant_X",
        "region": "us-east-1",
        "time_window": "last_24h"
    }

    # 6. Test different form types
    form_types_to_test = [FormType.FLOW, FormType.CLUSTER, FormType.WELL]

    for form_type in form_types_to_test:
        print(f"\n=== TESTING {form_type.name} FORM TYPE ===")

        form = system.process_intent(
            container_id=container.spec.container_id,
            intent=f"Analyze communication patterns using {form_type.name.lower()} analysis",
            role="analyst",
            risk_level=RiskLevel.MEDIUM,
            mass_map=mass_map,
            fields=fields,
            substrate=substrate,
            form_type=form_type
        )

        if form:
            print(f"Generated {form.form_type.name} form: {form.name}")
            print(f"Steps: {len(form.steps)}, Hardness: {form.hardness.name}")
            print(f"Execution time: {form.metadata.get('execution_time', 'N/A'):.3f}s")
        else:
            print(f"Failed to generate {form_type.name} form")

    # 7. Test reuse
    print("\n=== TESTING PATTERN REUSE ===")
    form_reuse = system.process_intent(
        container_id=container.spec.container_id,
        intent="Analyze communication patterns using flow analysis",  # Same as first test
        role="analyst",
        risk_level=RiskLevel.MEDIUM,
        mass_map=mass_map,
        fields=fields,
        substrate=substrate,
        form_type=FormType.FLOW
    )

    if form_reuse:
        print("Successfully reused pattern!")
        print(f"Form ID: {form_reuse.form_id}")

    # 8. System status report
    print("\n=== SYSTEM STATUS ===")
    status = system.get_system_status()
    print(f"Containers: {len(status['containers'])}")
    print(f"Active DMAs: {status['mci_metrics']['active_dmas']}")
    print(f"AQI Success Rate: {status['aqi_health']['success_rate']:.1%}")
    print(f"MEngine Violations: {status['aqi_health']['mengine_violations']}")


if __name__ == "__main__":
    example_run()