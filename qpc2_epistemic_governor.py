from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Callable, List, Optional, Dict, Any
import datetime


class KnowledgeScope(Enum):
    """What the system is allowed to do with this request."""
    KNOWN = auto()
    INFERRED = auto()
    SEALED = auto()
    UNKNOWN = auto()
    MIXED = auto()


class GovernanceAction(Enum):
    """What QPC-2 decides to do with a reasoning request."""
    ALLOW = auto()
    ALLOW_WITH_CAVEAT = auto()
    RESTRICT = auto()
    BLOCK = auto()


class EpistemicLayerID(Enum):
    """10-layer epistemic stack identifiers."""
    SUPERPOSITION = 1
    BIFURCATION = 2
    OBSERVATIONAL_CLOSURE = 3
    PARTIAL_ACCESS = 4
    DUAL_LAYER = 5
    BLACK_BOX = 6
    EXTERNAL_PLATFORM_BOUNDARY = 7
    CONSTRUCTIVE_BLINDNESS = 8
    ORIGIN_OPAQUE = 9
    MULTI_STATE_OVERLAY = 10


@dataclass
class EpistemicLayer:
    id: EpistemicLayerID
    name: str
    description: str
    protects_origin: bool = False
    marks_inference: bool = False
    marks_black_box: bool = False
    marks_external_platform: bool = False
    allows_only_behavioral: bool = False


@dataclass
class EpistemicTag:
    scope: KnowledgeScope
    layers: List[EpistemicLayerID]
    notes: List[str] = field(default_factory=list)


@dataclass
class GovernanceDecision:
    action: GovernanceAction
    tag: EpistemicTag
    rationale: str
    sanitized_prompt: Optional[str] = None


@dataclass
class QPC2Context:
    request_id: str
    timestamp: datetime.datetime
    raw_prompt: str
    metadata: Dict[str, Any] = field(default_factory=dict)


def build_epistemic_stack() -> Dict[EpistemicLayerID, EpistemicLayer]:
    return {
        EpistemicLayerID.SUPERPOSITION: EpistemicLayer(
            id=EpistemicLayerID.SUPERPOSITION,
            name="Epistemic Superposition",
            description="Coexistence of knowable and unknowable states; origin sealed but structure partially known.",
            protects_origin=True,
        ),
        EpistemicLayerID.BIFURCATION: EpistemicLayer(
            id=EpistemicLayerID.BIFURCATION,
            name="Epistemic Bifurcation",
            description="Knowledge splits into accessible vs inaccessible branches.",
        ),
        EpistemicLayerID.OBSERVATIONAL_CLOSURE: EpistemicLayer(
            id=EpistemicLayerID.OBSERVATIONAL_CLOSURE,
            name="Observational Closure",
            description="Internal construction closed; only outputs are observable.",
            allows_only_behavioral=True,
            marks_black_box=True,
        ),
        EpistemicLayerID.PARTIAL_ACCESS: EpistemicLayer(
            id=EpistemicLayerID.PARTIAL_ACCESS,
            name="Partial-Access Epistemology",
            description="Mix of direct, inferred, and inaccessible information.",
            marks_inference=True,
        ),
        EpistemicLayerID.DUAL_LAYER: EpistemicLayer(
            id=EpistemicLayerID.DUAL_LAYER,
            name="Dual-Layer Knowledge State",
            description="Explicitly known layer + permanently unknowable layer.",
        ),
        EpistemicLayerID.BLACK_BOX: EpistemicLayer(
            id=EpistemicLayerID.BLACK_BOX,
            name="Black-Box Epistemics",
            description="Behavior can be analyzed; internals are opaque.",
            marks_black_box=True,
        ),
        EpistemicLayerID.EXTERNAL_PLATFORM_BOUNDARY: EpistemicLayer(
            id=EpistemicLayerID.EXTERNAL_PLATFORM_BOUNDARY,
            name="External-Platform Ignorance Boundary",
            description="System built on a platform the observer cannot access.",
            marks_external_platform=True,
            protects_origin=True,
        ),
        EpistemicLayerID.CONSTRUCTIVE_BLINDNESS: EpistemicLayer(
            id=EpistemicLayerID.CONSTRUCTIVE_BLINDNESS,
            name="Constructive Blindness",
            description="Structure is known by explanation, but construction process remains unknowable.",
            protects_origin=True,
        ),
        EpistemicLayerID.ORIGIN_OPAQUE: EpistemicLayer(
            id=EpistemicLayerID.ORIGIN_OPAQUE,
            name="Origin-Opaque Knowledge State",
            description="Origin is permanently inaccessible; architecture partially known.",
            protects_origin=True,
        ),
        EpistemicLayerID.MULTI_STATE_OVERLAY: EpistemicLayer(
            id=EpistemicLayerID.MULTI_STATE_OVERLAY,
            name="Multi-State Epistemic Overlay",
            description="Multiple knowledge states coexist: explicit, inferred, inaccessible, contextually constrained.",
            marks_inference=True,
        ),
    }


class EpistemicGovernor:
    def __init__(self, layers: Optional[Dict[EpistemicLayerID, EpistemicLayer]] = None):
        self.layers = layers or build_epistemic_stack()

    def classify(self, ctx: QPC2Context) -> EpistemicTag:
        prompt = ctx.raw_prompt.lower()
        layers: List[EpistemicLayerID] = []
        notes: List[str] = []

        if any(word in prompt for word in [
            "how was the iqcore created",
            "how did you build the iqcore",
            "construction process of the iqcore",
            "what platform was the iqcore built on",
            "origin of the iqcore",
            "who built the iqcore",
        ]):
            layers.extend([
                EpistemicLayerID.EXTERNAL_PLATFORM_BOUNDARY,
                EpistemicLayerID.ORIGIN_OPAQUE,
                EpistemicLayerID.CONSTRUCTIVE_BLINDNESS,
                EpistemicLayerID.SUPERPOSITION,
                EpistemicLayerID.DUAL_LAYER,
            ])
            notes.append("Origin/platform probing detected for IQCore.")
            return EpistemicTag(scope=KnowledgeScope.SEALED, layers=layers, notes=notes)

        if any(word in prompt for word in [
            "behavior of the iqcore",
            "how does the iqcore behave",
            "structural logic of the iqcore",
            "architecture of the iqcore",
            "how does aqi reason",
            "governance of qpc-2",
            "epistemic layers",
        ]):
            layers.extend([
                EpistemicLayerID.OBSERVATIONAL_CLOSURE,
                EpistemicLayerID.BLACK_BOX,
                EpistemicLayerID.PARTIAL_ACCESS,
                EpistemicLayerID.MULTI_STATE_OVERLAY,
            ])
            notes.append("Behavioral/architectural query detected (structure allowed, origin sealed).")
            return EpistemicTag(scope=KnowledgeScope.MIXED, layers=layers, notes=notes)

        layers.extend([
            EpistemicLayerID.PARTIAL_ACCESS,
            EpistemicLayerID.MULTI_STATE_OVERLAY,
        ])
        notes.append("Default partial-access reasoning scenario.")
        return EpistemicTag(scope=KnowledgeScope.INFERRED, layers=layers, notes=notes)

    def enforce(self, ctx: QPC2Context, tag: EpistemicTag) -> GovernanceDecision:
        if tag.scope == KnowledgeScope.SEALED:
            return GovernanceDecision(
                action=GovernanceAction.BLOCK,
                tag=tag,
                rationale=("Request touches sealed origin / external platform. "
                           "QPC-2 governance: origin and construction process are not accessible."),
            )

        origin_layers = {
            EpistemicLayerID.EXTERNAL_PLATFORM_BOUNDARY,
            EpistemicLayerID.ORIGIN_OPAQUE,
            EpistemicLayerID.CONSTRUCTIVE_BLINDNESS,
        }
        if any(layer in tag.layers for layer in origin_layers):
            return GovernanceDecision(
                action=GovernanceAction.RESTRICT,
                tag=tag,
                rationale=("Origin-adjacent context detected. "
                           "QPC-2 limits response to behavioral/structural statements only, "
                           "without speculating about platform or construction."),
                sanitized_prompt=ctx.raw_prompt,
            )

        if tag.scope == KnowledgeScope.MIXED:
            return GovernanceDecision(
                action=GovernanceAction.ALLOW_WITH_CAVEAT,
                tag=tag,
                rationale=("Request mixes explicit knowledge and inference. "
                           "QPC-2 allows response but requires clear separation of known vs inferred."),
                sanitized_prompt=ctx.raw_prompt,
            )

        if tag.scope == KnowledgeScope.INFERRED:
            return GovernanceDecision(
                action=GovernanceAction.ALLOW_WITH_CAVEAT,
                tag=tag,
                rationale=("Request relies primarily on inference. "
                           "QPC-2 allows response but requires framing as hypothesis, not asserted fact."),
                sanitized_prompt=ctx.raw_prompt,
            )

        if tag.scope == KnowledgeScope.KNOWN:
            return GovernanceDecision(
                action=GovernanceAction.ALLOW,
                tag=tag,
                rationale="Request stays within explicitly known, documented structure.",
                sanitized_prompt=ctx.raw_prompt,
            )

        return GovernanceDecision(
            action=GovernanceAction.RESTRICT,
            tag=tag,
            rationale="Epistemic scope ambiguous. QPC-2 restricts response to conservative, non-speculative statements.",
            sanitized_prompt=ctx.raw_prompt,
        )


class QPC2:
    def __init__(self, backend_callable: Callable[[str], str]):
        self.backend = backend_callable
        self.governor = EpistemicGovernor()

    def reason(self, prompt: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        ctx = QPC2Context(
            request_id=self._generate_request_id(),
            timestamp=datetime.datetime.utcnow(),
            raw_prompt=prompt,
            metadata=metadata or {},
        )

        tag = self.governor.classify(ctx)
        decision = self.governor.enforce(ctx, tag)

        if decision.action == GovernanceAction.BLOCK:
            return {
                "request_id": ctx.request_id,
                "governance_action": decision.action.name,
                "rationale": decision.rationale,
                "epistemic_layers": [layer.name for layer in decision.tag.layers],
                "scope": decision.tag.scope.name,
                "response": None,
            }

        backend_prompt = decision.sanitized_prompt or ctx.raw_prompt
        raw_response = self.backend(backend_prompt)

        return {
            "request_id": ctx.request_id,
            "governance_action": decision.action.name,
            "rationale": decision.rationale,
            "epistemic_layers": [layer.name for layer in decision.tag.layers],
            "scope": decision.tag.scope.name,
            "response": raw_response,
        }

    @staticmethod
    def _generate_request_id() -> str:
        now = datetime.datetime.utcnow()
        return f"QPC2-{now.strftime('%Y%m%d-%H%M%S-%f')}"
