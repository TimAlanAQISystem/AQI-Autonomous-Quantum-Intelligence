"""
Human Thought Index (HTI) Engine
=================================

A Python implementation of the Human Thought Index architecture that serves as a structural scaffold
for human-aligned intelligence. This engine provides:

- Human Thought Index: Structural grammar of human thought (modes, primitives, transitions, boundaries)
- MEngine: Meta-tool that uses the HTI to forge IQCores
- IQCore Templates: Builders that create cores structurally aligned with human reasoning

This is a conceptual scaffold that can be evolved into more sophisticated intelligence systems.
Not "intelligent" by itself, but provides the structural foundation for intelligence emergence.

Created: December 13, 2025
Author: TimAlanAQISystem
"""

from dataclasses import dataclass, field
from typing import Dict, List, Callable, Any


# ---------- Human Thought Index (structural, not content) ----------

@dataclass
class ThoughtMode:
    name: str
    description: str


@dataclass
class RelationalPrimitive:
    name: str
    description: str


@dataclass
class CognitiveTransition:
    name: str
    from_modes: List[str]  # names of modes
    to_modes: List[str]
    rule: Callable[[Dict[str, Any]], str]
    """
    rule(context) -> next_mode_name
    context: arbitrary dict describing situation, state, signals, etc.
    """


@dataclass
class InterpretationRule:
    name: str
    description: str
    apply: Callable[[Dict[str, Any]], Dict[str, Any]]
    """
    apply(context) -> new_context
    Used to model how humans interpret signals, assign meaning, etc.
    """


@dataclass
class BoundaryPolicy:
    name: str
    description: str
    is_valid: Callable[[Dict[str, Any]], bool]
    """
    is_valid(state) -> True if state is in-bounds, False if it's 'zero is zero'
    """


@dataclass
class HumanThoughtIndex:
    """
    Structural grammar of human thought.
    Not content, just categories, transitions, and interpretation patterns.
    """
    modes: Dict[str, ThoughtMode] = field(default_factory=dict)
    primitives: Dict[str, RelationalPrimitive] = field(default_factory=dict)
    transitions: Dict[str, CognitiveTransition] = field(default_factory=dict)
    interpretation_rules: Dict[str, InterpretationRule] = field(default_factory=dict)
    boundary_policies: Dict[str, BoundaryPolicy] = field(default_factory=dict)

    def register_mode(self, mode: ThoughtMode):
        self.modes[mode.name] = mode

    def register_primitive(self, primitive: RelationalPrimitive):
        self.primitives[primitive.name] = primitive

    def register_transition(self, transition: CognitiveTransition):
        self.transitions[transition.name] = transition

    def register_interpretation_rule(self, rule: InterpretationRule):
        self.interpretation_rules[rule.name] = rule

    def register_boundary_policy(self, policy: BoundaryPolicy):
        self.boundary_policies[policy.name] = policy


# ---------- IQCore templates and instances ----------

@dataclass
class IQCoreTemplate:
    name: str
    description: str
    """
    These builders use the HumanThoughtIndex to construct a core
    that is structurally aligned with human reasoning.
    """
    build_axioms: Callable[[HumanThoughtIndex], Dict[str, Any]]
    build_parameters: Callable[[HumanThoughtIndex], Dict[str, Any]]
    build_initial_state: Callable[[HumanThoughtIndex], Dict[str, Any]]

    def build(self, hti: HumanThoughtIndex) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "axioms": self.build_axioms(hti),
            "parameters": self.build_parameters(hti),
            "state": self.build_initial_state(hti),
        }


@dataclass
class IQCoreInstance:
    template_name: str
    axioms: Dict[str, Any]
    parameters: Dict[str, Any]
    state: Dict[str, Any]
    ctm: CognitiveTransitionMatrix = None  # attach CTM

    def read_base(self) -> Dict[str, Any]:
        """Readable origin/base of this IQCore."""
        return {
            "axioms": self.axioms.copy(),
            "parameters": self.parameters.copy(),
            "state": self.state.copy(),
        }

    def step_mode(self, context: Dict[str, Any]) -> str:
        """
        Use the Cognitive Transition Matrix to update current_mode based on context.
        """
        if self.ctm is None:
            return self.state.get("current_mode", "analytical")

        current = self.state.get("current_mode", "analytical")
        next_m = self.ctm.next_mode(current, context)
        self.state["current_mode"] = next_m
        return next_m


# ---------- MEngine: meta-tool / tool-maker ----------

@dataclass
class MEngine:
    """
    MEngine sits above IQCores.
    It holds:
      - a HumanThoughtIndex (structural grammar)
      - a library of IQCore templates
      - a Cognitive Transition Matrix for dynamic mode transitions
    It can spawn IQCores that are structurally aligned with human thought.
    """
    thought_index: HumanThoughtIndex = field(default_factory=HumanThoughtIndex)
    iqcore_templates: Dict[str, IQCoreTemplate] = field(default_factory=dict)
    ctm: CognitiveTransitionMatrix = None

    # Architect-level operations (Σ)
    def register_iqcore_template(self, template: IQCoreTemplate):
        self.iqcore_templates[template.name] = template

    def set_ctm(self, ctm: CognitiveTransitionMatrix):
        """Set the Cognitive Transition Matrix for dynamic mode transitions."""
        self.ctm = ctm

    def spawn_iqcore(self, name: str) -> IQCoreInstance:
        if name not in self.iqcore_templates:
            raise ValueError(f"Unknown IQCore template: {name}")
        template = self.iqcore_templates[name]
        core = template.build(self.thought_index)
        return IQCoreInstance(
            template_name=template.name,
            axioms=core["axioms"],
            parameters=core["parameters"],
            state=core["state"],
            ctm=self.ctm,  # Attach CTM to enable dynamic transitions
        )


# ---------- Example wiring ----------

def build_basic_axioms(hti: HumanThoughtIndex) -> Dict[str, Any]:
    return {
        "uses_modes": list(hti.modes.keys()),
        "respects_primitives": list(hti.primitives.keys()),
        "description": "Core aligns with registered thought modes and primitives."
    }


def build_basic_parameters(hti: HumanThoughtIndex) -> Dict[str, Any]:
    return {
        "default_mode": "relational" if "relational" in hti.modes else None,
        "sensitivity_to_trust": 1.0 if "trust" in hti.primitives else 0.5,
    }


def build_basic_initial_state(hti: HumanThoughtIndex) -> Dict[str, Any]:
    return {
        "current_mode": "relational" if "relational" in hti.modes else "analytical",
        "trust_level": 0.0,
        "history": [],
    }


# ---------- Advanced Extensions ----------

@dataclass
class ProjectionUniverse:
    """
    A projection universe represents a context or domain where IQCores can operate.
    Think of it as a "reality bubble" with its own rules and constraints.
    """
    name: str
    description: str
    domain_primitives: Dict[str, Any]  # Domain-specific primitives
    universe_rules: Dict[str, Callable[[Dict[str, Any]], Any]]
    boundary_conditions: Dict[str, Callable[[Dict[str, Any]], bool]]

    def project_iqcore(self, iqcore: IQCoreInstance, context: Dict[str, Any]) -> Dict[str, Any]:
        """Project an IQCore into this universe with given context."""
        projected_state = iqcore.state.copy()
        projected_state.update({
            "universe": self.name,
            "domain_context": context,
            "projected_primitives": self.domain_primitives
        })

        # Apply universe rules
        for rule_name, rule_func in self.universe_rules.items():
            projected_state[f"universe_{rule_name}"] = rule_func(context)

        return projected_state


@dataclass
class CognitiveTransitionRule:
    name: str
    from_modes: List[str]
    to_mode: str
    description: str
    priority: int
    """
    condition(context) -> bool:
      context includes:
        - current_mode
        - primitives (trust, threat, value, risk, etc.)
        - universe (merchant_ecosystem, ethical_dilemma_space, ...)
        - scenario-specific metadata
    """
    condition: Callable[[Dict[str, Any]], bool]


@dataclass
class CognitiveTransitionMatrix:
    modes: List[str]
    rules: List[CognitiveTransitionRule] = field(default_factory=list)

    def register_rule(self, rule: CognitiveTransitionRule):
        self.rules.append(rule)
        # Sort by priority so higher-priority rules win
        self.rules.sort(key=lambda r: r.priority, reverse=True)

    def next_mode(self, current_mode: str, context: Dict[str, Any]) -> str:
        """
        Determine the next mode, given current mode and context.
        If no rule applies, stay in the current mode.
        """
        ctx = context.copy()
        ctx["current_mode"] = current_mode

        for rule in self.rules:
            if current_mode in rule.from_modes and rule.condition(ctx):
                return rule.to_mode

        return current_mode


@dataclass
class InterpretationNode:
    name: str
    apply: Callable[[Dict[str, Any]], Dict[str, Any]]
    """
    apply(context) -> new_context
    """


@dataclass
class InterpretationEdge:
    from_node: str
    to_node: str
    condition: Optional[Callable[[Dict[str, Any]], bool]] = None
    """
    condition(context) -> bool
    If None, edge is always active.
    """


@dataclass
class InterpretationNetworkGraph:
    nodes: Dict[str, InterpretationNode] = field(default_factory=dict)
    edges: List[InterpretationEdge] = field(default_factory=list)
    entry_nodes: List[str] = field(default_factory=list)

    def register_node(self, node: InterpretationNode, is_entry: bool = False):
        self.nodes[node.name] = node
        if is_entry and node.name not in self.entry_nodes:
            self.entry_nodes.append(node.name)

    def register_edge(self, edge: InterpretationEdge):
        self.edges.append(edge)

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run the interpretation network starting from entry nodes.
        Executes nodes and follows edges based on conditions.
        """
        visited = set()
        queue = list(self.entry_nodes)
        ctx = context.copy()

        while queue:
            node_name = queue.pop(0)
            if node_name in visited or node_name not in self.nodes:
                continue

            node = self.nodes[node_name]
            ctx = node.apply(ctx)
            visited.add(node_name)

            # enqueue downstream nodes whose conditions pass
            for edge in self.edges:
                if edge.from_node == node_name:
                    if edge.condition is None or edge.condition(ctx):
                        queue.append(edge.to_node)

        return ctx


@dataclass
class CoreAgent:
    name: str
    role: str  # e.g., "relational", "merchant_protection", "ethics"
    universe: str  # e.g., "merchant_ecosystem"
    iqcore: IQCoreInstance
    interp_graph: Optional[InterpretationNetworkGraph] = None

    def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        1. Interpret context (optional)
        2. Update mode via CTM
        3. Produce a core-specific output (stubbed here as updated context)
        """
        ctx = context.copy()
        ctx["universe"] = self.universe

        if self.interp_graph is not None:
            ctx = self.interp_graph.run(ctx)

        # Update mode based on interpreted context
        if hasattr(self.iqcore, "step_mode"):
            self.iqcore.step_mode(ctx)

        # For now, just attach core perspective
        ctx.setdefault("core_views", {})
        ctx["core_views"][self.name] = {
            "role": self.role,
            "mode": self.iqcore.state.get("current_mode", "analytical"),
            "primitives": ctx.get("primitives", {}).copy(),
        }
        return ctx


@dataclass
class MultiCoreOrchestrator:
    cores: Dict[str, CoreAgent] = field(default_factory=dict)

    def register_core(self, core: CoreAgent):
        self.cores[core.name] = core

    def route(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send context to relevant cores and aggregate their views.
        """
        aggregated_context = context.copy()
        aggregated_context["core_views"] = {}

        for core in self.cores.values():
            core_ctx = core.process(aggregated_context)
            # merge core_views
            aggregated_context["core_views"].update(core_ctx.get("core_views", {}))
            # optionally merge primitives (e.g., max risk, harm; min trust, justice)
            primitives = aggregated_context.setdefault("primitives", {})
            core_primitives = core_ctx.get("primitives", {})
            for k, v in core_primitives.items():
                # Simple aggregation strategy: keep max for risk, harm; min for trust, justice etc.
                if k in ("risk", "harm"):
                    primitives[k] = max(primitives.get(k, 0.0), v)
                elif k in ("trust", "justice", "wellbeing"):
                    primitives[k] = min(primitives.get(k, 1.0), v)
                else:
                    primitives[k] = v

        return aggregated_context

    def decide(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        High-level decision policy based on aggregated core views.
        For now, we return the aggregated state with a simple verdict stub.
        """
        ctx = self.route(context)
        primitives = ctx.get("primitives", {})
        decision = "proceed"

        if primitives.get("harm", 0.0) > 0.7:
            decision = "block"
        elif primitives.get("risk", 0.0) > 0.7 and primitives.get("value", 0.0) < 0.5:
            decision = "decline"
        elif primitives.get("risk", 0.0) > 0.7 and primitives.get("value", 0.0) >= 0.5:
            decision = "manual_review"

        ctx["orchestrator_decision"] = decision
        return ctx


def build_merchant_protection_axioms(hti: HumanThoughtIndex) -> Dict[str, Any]:
    """Advanced axioms for merchant protection focused on risk, trust, and value."""
    return {
        "core_principle": "protect_merchant_value_while_maintaining_trust",
        "uses_modes": ["analytical", "relational", "ethical", "strategic"],
        "respects_primitives": ["trust", "risk", "value", "threat", "belonging"],
        "ethical_boundaries": ["no_harm", "value_preservation", "trust_maintenance"],
        "description": "IQCore specialized for merchant protection with risk assessment and trust management."
    }


def build_merchant_protection_parameters(hti: HumanThoughtIndex) -> Dict[str, Any]:
    """Parameters tuned for merchant protection scenarios."""
    return {
        "default_mode": "strategic",
        "risk_sensitivity": 0.8,
        "trust_threshold": 0.7,
        "value_protection_priority": 0.9,
        "threat_detection_sensitivity": 0.85,
        "ethical_override_enabled": True
    }


def build_merchant_protection_initial_state(hti: HumanThoughtIndex) -> Dict[str, Any]:
    """Initial state for merchant protection operations."""
    return {
        "current_mode": "strategic",
        "trust_level": 0.5,
        "risk_assessment": 0.0,
        "value_protected": 0.0,
        "threats_detected": [],
        "protection_actions": [],
        "merchant_relationships": {},
        "history": []
    }


def build_ethical_decision_axioms(hti: HumanThoughtIndex) -> Dict[str, Any]:
    """Axioms for ethical decision-making aligned with human values."""
    return {
        "core_principle": "decisions_must_align_with_human_flourishing",
        "uses_modes": ["ethical", "relational", "analytical", "intuitive"],
        "respects_primitives": ["harm", "benefit", "justice", "autonomy", "wellbeing"],
        "decision_framework": "utilitarian_with_deontological_bounds",
        "description": "IQCore specialized for ethical decision-making with human value alignment."
    }


def build_ethical_decision_parameters(hti: HumanThoughtIndex) -> Dict[str, Any]:
    """Parameters for ethical decision-making."""
    return {
        "default_mode": "ethical",
        "harm_threshold": 0.3,
        "benefit_weight": 0.6,
        "justice_sensitivity": 0.8,
        "autonomy_respect": 0.9,
        "long_term_bias": 0.4
    }


def build_ethical_decision_initial_state(hti: HumanThoughtIndex) -> Dict[str, Any]:
    """Initial state for ethical decision operations."""
    return {
        "current_mode": "ethical",
        "ethical_score": 0.0,
        "stakeholders_impacted": [],
        "potential_harm": 0.0,
        "potential_benefit": 0.0,
        "decision_confidence": 0.0,
        "ethical_history": [],
        "history": []
    }


# ---------- Cognitive Transition Matrix Rules ----------

def high_risk_in_merchant_ecosystem(context: Dict[str, Any]) -> bool:
    return (
        context.get("universe") == "merchant_ecosystem"
        and context.get("primitives", {}).get("risk", 0.0) > 0.7
    )


def ethical_conflict_detected(context: Dict[str, Any]) -> bool:
    return (
        context.get("universe") == "ethical_dilemma_space"
        and context.get("primitives", {}).get("justice", 0.0) < 0.4
        and context.get("primitives", {}).get("harm", 0.0) > 0.5
    )


def safe_and_trusting(context: Dict[str, Any]) -> bool:
    p = context.get("primitives", {})
    return p.get("trust", 0.0) > 0.7 and p.get("threat", 0.0) < 0.3


def creative_opportunity(context: Dict[str, Any]) -> bool:
    p = context.get("primitives", {})
    return (
        p.get("value", 0.0) > 0.6 and
        p.get("risk", 0.0) < 0.4 and
        context.get("universe") in ["merchant_ecosystem", "ethical_dilemma_space"]
    )


def analytical_data_rich(context: Dict[str, Any]) -> bool:
    return (
        context.get("data_points", 0) > 10 and
        context.get("uncertainty", 0.0) < 0.3
    )


def intuitive_pattern_emergence(context: Dict[str, Any]) -> bool:
    return (
        context.get("pattern_confidence", 0.0) > 0.8 and
        context.get("data_points", 0) < 5
    )


def emotional_stakes_high(context: Dict[str, Any]) -> bool:
    p = context.get("primitives", {})
    return (
        p.get("belonging", 0.0) > 0.8 or
        p.get("harm", 0.0) > 0.7 or
        context.get("stakeholder_emotion", 0.0) > 0.6
    )


def build_default_ctm() -> CognitiveTransitionMatrix:
    """Build a comprehensive Cognitive Transition Matrix with example rules."""
    modes = [
        "analytical",
        "emotional",
        "relational",
        "ethical",
        "strategic",
        "intuitive",
        "creative",
    ]
    ctm = CognitiveTransitionMatrix(modes=modes)

    # Register transition rules with priorities
    ctm.register_rule(CognitiveTransitionRule(
        name="MerchantHighRiskToStrategic",
        from_modes=["analytical", "relational"],
        to_mode="strategic",
        description="Escalate to strategic mode when risk is high in merchant ecosystem.",
        priority=100,
        condition=high_risk_in_merchant_ecosystem,
    ))

    ctm.register_rule(CognitiveTransitionRule(
        name="EthicalConflictFocus",
        from_modes=["analytical", "strategic", "relational"],
        to_mode="ethical",
        description="Shift to ethical reasoning when justice is low and harm is high.",
        priority=110,
        condition=ethical_conflict_detected,
    ))

    ctm.register_rule(CognitiveTransitionRule(
        name="SafeToRelational",
        from_modes=["analytical", "strategic"],
        to_mode="relational",
        description="Move to relational mode when trust is high and threat is low.",
        priority=50,
        condition=safe_and_trusting,
    ))

    ctm.register_rule(CognitiveTransitionRule(
        name="OpportunityToCreative",
        from_modes=["analytical", "strategic", "relational"],
        to_mode="creative",
        description="Shift to creative mode when value opportunities exist with manageable risk.",
        priority=60,
        condition=creative_opportunity,
    ))

    ctm.register_rule(CognitiveTransitionRule(
        name="DataRichToAnalytical",
        from_modes=["intuitive", "relational", "creative"],
        to_mode="analytical",
        description="Move to analytical mode when sufficient data is available for systematic analysis.",
        priority=70,
        condition=analytical_data_rich,
    ))

    ctm.register_rule(CognitiveTransitionRule(
        name="PatternToIntuitive",
        from_modes=["analytical", "strategic"],
        to_mode="intuitive",
        description="Shift to intuitive mode when clear patterns emerge from limited data.",
        priority=65,
        condition=intuitive_pattern_emergence,
    ))

    ctm.register_rule(CognitiveTransitionRule(
        name="HighStakesToEmotional",
        from_modes=["analytical", "strategic", "ethical"],
        to_mode="emotional",
        description="Move to emotional mode when stakeholder emotions or belonging are highly engaged.",
        priority=80,
        condition=emotional_stakes_high,
    ))

    return ctm


# ---------- Interpretation Network Graph Examples ----------

def trust_assessment(context: Dict[str, Any]) -> Dict[str, Any]:
    """Refine trust based on signals and historical data."""
    signals = context.get("signals", {})
    base_trust = signals.get("historical_reliability", 0.5)
    adjustment = 0.2 if signals.get("recent_positive", False) else -0.1
    if signals.get("violation_detected", False):
        adjustment -= 0.3

    context.setdefault("primitives", {})
    context["primitives"]["trust"] = max(0.0, min(1.0, base_trust + adjustment))
    return context


def risk_evaluation(context: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate risk based on trust, value, and volatility."""
    primitives = context.get("primitives", {})
    trust = primitives.get("trust", 0.5)
    value = primitives.get("value", 0.5)
    volatility = context.get("volatility", 0.0)

    # Risk increases with low trust, high value at risk, and volatility
    risk = max(0.0, min(1.0, (1 - trust) * 0.5 + value * 0.3 + volatility * 0.2))
    primitives["risk"] = risk
    context["primitives"] = primitives
    return context


def ethical_assessment(context: Dict[str, Any]) -> Dict[str, Any]:
    """Assess ethical implications based on harm, justice, and autonomy."""
    primitives = context.get("primitives", {})
    harm = primitives.get("harm", 0.0)
    justice = primitives.get("justice", 1.0)
    autonomy = primitives.get("autonomy", 1.0)

    # Ethical score decreases with harm and increases with justice/autonomy
    ethical_score = max(0.0, min(1.0, 1.0 - harm * 0.6 + justice * 0.3 + autonomy * 0.1))
    primitives["ethical_score"] = ethical_score
    context["primitives"] = primitives
    return context


def value_assessment(context: Dict[str, Any]) -> Dict[str, Any]:
    """Assess overall value considering benefits and costs."""
    primitives = context.get("primitives", {})
    benefit = primitives.get("benefit", 0.0)
    harm = primitives.get("harm", 0.0)
    risk = primitives.get("risk", 0.0)

    # Net value considers benefits minus harm and risk penalties
    net_value = max(0.0, min(1.0, benefit - harm * 0.4 - risk * 0.2))
    primitives["net_value"] = net_value
    context["primitives"] = primitives
    return context


def high_value_condition(context: Dict[str, Any]) -> bool:
    """Check if value is high enough to trigger risk evaluation."""
    return context.get("primitives", {}).get("value", 0.0) > 0.6


def ethical_concern_condition(context: Dict[str, Any]) -> bool:
    """Check if there are ethical concerns requiring assessment."""
    primitives = context.get("primitives", {})
    return (primitives.get("harm", 0.0) > 0.3 or
            primitives.get("justice", 1.0) < 0.7 or
            primitives.get("autonomy", 1.0) < 0.7)


def build_interpretation_graph() -> InterpretationNetworkGraph:
    """Build a comprehensive interpretation network graph."""
    graph = InterpretationNetworkGraph()

    # Register nodes
    graph.register_node(InterpretationNode(
        name="trust_assessment",
        apply=trust_assessment
    ), is_entry=True)

    graph.register_node(InterpretationNode(
        name="risk_evaluation",
        apply=risk_evaluation
    ))

    graph.register_node(InterpretationNode(
        name="ethical_assessment",
        apply=ethical_assessment
    ))

    graph.register_node(InterpretationNode(
        name="value_assessment",
        apply=value_assessment
    ))

    # Register edges with conditions
    graph.register_edge(InterpretationEdge(
        from_node="trust_assessment",
        to_node="risk_evaluation",
        condition=high_value_condition
    ))

    graph.register_edge(InterpretationEdge(
        from_node="trust_assessment",
        to_node="ethical_assessment",
        condition=ethical_concern_condition
    ))

    graph.register_edge(InterpretationEdge(
        from_node="risk_evaluation",
        to_node="value_assessment"
    ))

    graph.register_edge(InterpretationEdge(
        from_node="ethical_assessment",
        to_node="value_assessment"
    ))

    return graph


def build_merchant_interpretation_graph() -> InterpretationNetworkGraph:
    """Build interpretation graph specialized for merchant scenarios."""
    graph = InterpretationNetworkGraph()

    # Focus on merchant-specific signals
    graph.register_node(InterpretationNode(
        name="merchant_trust_assessment",
        apply=lambda ctx: trust_assessment(ctx)  # Use same logic but could be specialized
    ), is_entry=True)

    graph.register_node(InterpretationNode(
        name="transaction_risk_evaluation",
        apply=lambda ctx: risk_evaluation(ctx)  # Could add transaction-specific logic
    ))

    graph.register_node(InterpretationNode(
        name="merchant_value_assessment",
        apply=lambda ctx: value_assessment(ctx)
    ))

    # Merchant-specific edges
    graph.register_edge(InterpretationEdge(
        from_node="merchant_trust_assessment",
        to_node="transaction_risk_evaluation"
    ))

    graph.register_edge(InterpretationEdge(
        from_node="transaction_risk_evaluation",
        to_node="merchant_value_assessment"
    ))

    return graph


def build_ethical_interpretation_graph() -> InterpretationNetworkGraph:
    """Build interpretation graph specialized for ethical scenarios."""
    graph = InterpretationNetworkGraph()

    # Focus on ethical dimensions
    graph.register_node(InterpretationNode(
        name="ethical_trust_assessment",
        apply=trust_assessment
    ), is_entry=True)

    graph.register_node(InterpretationNode(
        name="ethical_assessment",
        apply=ethical_assessment
    ))

    graph.register_node(InterpretationNode(
        name="ethical_value_assessment",
        apply=value_assessment
    ))

    # Ethical-specific edges
    graph.register_edge(InterpretationEdge(
        from_node="ethical_trust_assessment",
        to_node="ethical_assessment"
    ))

    graph.register_edge(InterpretationEdge(
        from_node="ethical_assessment",
        to_node="ethical_value_assessment"
    ))

    return graph


# ---------- Multi-Core Orchestration Setup ----------

def build_multi_core_orchestrator(engine: MEngine) -> MultiCoreOrchestrator:
    """Build a multi-core orchestrator with specialized agents."""
    orchestrator = MultiCoreOrchestrator()

    # Create IQCores
    merchant_core = engine.spawn_iqcore("MerchantProtectionCore")
    ethical_core = engine.spawn_iqcore("EthicalDecisionCore")
    relational_core = engine.spawn_iqcore("RelationalCoreV1")

    # Create interpretation graphs
    merchant_interp = build_merchant_interpretation_graph()
    ethical_interp = build_ethical_interpretation_graph()
    relational_interp = build_interpretation_graph()  # General graph for relational

    # Create CoreAgents
    merchant_agent = CoreAgent(
        name="MerchantProtectionCore",
        role="merchant_protection",
        universe="merchant_ecosystem",
        iqcore=merchant_core,
        interp_graph=merchant_interp
    )

    ethical_agent = CoreAgent(
        name="EthicalDecisionCore",
        role="ethics",
        universe="ethical_dilemma_space",
        iqcore=ethical_core,
        interp_graph=ethical_interp
    )

    relational_agent = CoreAgent(
        name="RelationalCoreV1",
        role="relational",
        universe="merchant_ecosystem",  # Can operate in multiple universes
        iqcore=relational_core,
        interp_graph=relational_interp
    )

    # Register agents
    orchestrator.register_core(merchant_agent)
    orchestrator.register_core(ethical_agent)
    orchestrator.register_core(relational_agent)

    return orchestrator


def example_advanced_setup() -> MEngine:
    """
    Advanced setup with multiple thought modes, primitives, and IQCore templates.
    Demonstrates the scalability of the HTI architecture.
    """
    # 1. Build comprehensive Human Thought Index
    hti = HumanThoughtIndex()

    # Register comprehensive thought modes
    hti.register_mode(ThoughtMode(name="analytical", description="Logical, stepwise reasoning and pattern analysis."))
    hti.register_mode(ThoughtMode(name="emotional", description="Feeling-driven evaluation and empathy processing."))
    hti.register_mode(ThoughtMode(name="relational", description="Context of people, belonging, and social impact."))
    hti.register_mode(ThoughtMode(name="ethical", description="Moral reasoning and value-based decision making."))
    hti.register_mode(ThoughtMode(name="strategic", description="Long-term planning and risk assessment."))
    hti.register_mode(ThoughtMode(name="intuitive", description="Pattern recognition and rapid insight formation."))
    hti.register_mode(ThoughtMode(name="creative", description="Novel solution generation and innovation."))

    # Register comprehensive relational primitives
    hti.register_primitive(RelationalPrimitive(name="trust", description="Sense of safety and reliability in relationships."))
    hti.register_primitive(RelationalPrimitive(name="threat", description="Perception of danger or potential harm."))
    hti.register_primitive(RelationalPrimitive(name="belonging", description="Sense of inclusion and acceptance."))
    hti.register_primitive(RelationalPrimitive(name="value", description="Economic, social, or personal worth."))
    hti.register_primitive(RelationalPrimitive(name="risk", description="Potential for loss or negative outcomes."))
    hti.register_primitive(RelationalPrimitive(name="harm", description="Actual or potential damage to wellbeing."))
    hti.register_primitive(RelationalPrimitive(name="benefit", description="Positive outcomes and advantages."))
    hti.register_primitive(RelationalPrimitive(name="justice", description="Fairness and equitable treatment."))
    hti.register_primitive(RelationalPrimitive(name="autonomy", description="Independence and self-determination."))
    hti.register_primitive(RelationalPrimitive(name="wellbeing", description="Overall health and flourishing."))

    # Register interpretation rules
    hti.register_interpretation_rule(InterpretationRule(
        name="trust_assessment",
        description="Interprets signals to assess trust levels",
        apply=lambda context: {
            **context,
            "trust_signals": ["consistency", "transparency", "reliability"],
            "trust_score": sum(1 for signal in ["consistency", "transparency", "reliability"]
                             if context.get(signal, False)) / 3.0
        }
    ))

    hti.register_interpretation_rule(InterpretationRule(
        name="risk_evaluation",
        description="Evaluates potential risks in given context",
        apply=lambda context: {
            **context,
            "risk_factors": ["uncertainty", "volatility", "complexity"],
            "risk_score": min(1.0, sum(context.get(factor, 0.0)
                                       for factor in ["uncertainty", "volatility", "complexity"]) / 3.0)
        }
    ))

    # Register boundary policies
    hti.register_boundary_policy(BoundaryPolicy(
        name="ethical_boundaries",
        description="Ensures decisions don't cause harm or violate core values",
        is_valid=lambda state: (
            state.get("harm_potential", 0.0) < 0.7 and
            state.get("trust_level", 0.0) > -0.5 and
            not state.get("violation_flag", False)
        )
    ))

    hti.register_boundary_policy(BoundaryPolicy(
        name="merchant_protection",
        description="Prioritizes merchant value protection and relationship maintenance",
        is_valid=lambda state: (
            state.get("value_protected", 0.0) >= state.get("value_at_risk", 0.0) and
            state.get("relationship_damage", 0.0) < 0.5
        )
    ))

    # 2. Build MEngine with advanced templates
    engine = MEngine(thought_index=hti)

    # Set up Cognitive Transition Matrix
    ctm = build_default_ctm()
    engine.set_ctm(ctm)

    # Register multiple IQCore templates
    templates = [
        IQCoreTemplate(
            name="RelationalCoreV1",
            description="Basic relational intelligence core.",
            build_axioms=build_basic_axioms,
            build_parameters=build_basic_parameters,
            build_initial_state=build_basic_initial_state,
        ),
        IQCoreTemplate(
            name="MerchantProtectionCore",
            description="Specialized core for merchant value protection and risk management.",
            build_axioms=build_merchant_protection_axioms,
            build_parameters=build_merchant_protection_parameters,
            build_initial_state=build_merchant_protection_initial_state,
        ),
        IQCoreTemplate(
            name="EthicalDecisionCore",
            description="Core specialized for ethical decision-making and value alignment.",
            build_axioms=build_ethical_decision_axioms,
            build_parameters=build_ethical_decision_parameters,
            build_initial_state=build_ethical_decision_initial_state,
        )
    ]

    for template in templates:
        engine.register_iqcore_template(template)

    # 3. Create projection universes
    engine.projection_universes = {
        "merchant_ecosystem": ProjectionUniverse(
            name="merchant_ecosystem",
            description="Business environment with merchants, customers, and transactions",
            domain_primitives={
                "transaction_value": 0.0,
                "customer_satisfaction": 0.0,
                "market_volatility": 0.0
            },
            universe_rules={
                "value_flow": lambda ctx: ctx.get("transaction_value", 0.0) * (1 - ctx.get("risk_factor", 0.0)),
                "relationship_strength": lambda ctx: min(1.0, ctx.get("trust_level", 0.0) + ctx.get("interaction_frequency", 0.0))
            },
            boundary_conditions={
                "market_stability": lambda ctx: ctx.get("market_volatility", 0.0) < 0.8,
                "ethical_compliance": lambda ctx: not ctx.get("fraud_detected", False)
            }
        ),
        "ethical_dilemma_space": ProjectionUniverse(
            name="ethical_dilemma_space",
            description="Decision space for ethical reasoning and moral choices",
            domain_primitives={
                "stakeholder_count": 0,
                "moral_weight": 0.0,
                "long_term_impact": 0.0
            },
            universe_rules={
                "utilitarian_score": lambda ctx: ctx.get("total_benefit", 0.0) - ctx.get("total_harm", 0.0),
                "deontological_compliance": lambda ctx: all(ctx.get(f"rule_{i}_followed", True) for i in range(3))
            },
            boundary_conditions={
                "harm_threshold": lambda ctx: ctx.get("harm_potential", 0.0) < 0.5,
                "consent_obtained": lambda ctx: ctx.get("informed_consent", False)
            }
        )
    }

    return engine
    """
    Example setup demonstrating the HTI architecture.
    This creates a basic Human Thought Index and MEngine with one IQCore template.
    """
    # 1. Build the Human Thought Index
    hti = HumanThoughtIndex()

    # Register modes
    hti.register_mode(ThoughtMode(name="analytical", description="Logical, stepwise reasoning."))
    hti.register_mode(ThoughtMode(name="emotional", description="Feeling-driven evaluation."))
    hti.register_mode(ThoughtMode(name="relational", description="Context of people, belonging, and impact."))

    # Register relational primitives
    hti.register_primitive(RelationalPrimitive(name="trust", description="Sense of safety and reliability."))
    hti.register_primitive(RelationalPrimitive(name="threat", description="Perception of danger or harm."))
    hti.register_primitive(RelationalPrimitive(name="belonging", description="Sense of inclusion and acceptance."))

    # Register a simple boundary policy
    hti.register_boundary_policy(BoundaryPolicy(
        name="basic_ethics",
        description="Rejects states with negative trust below threshold or explicit harm markers.",
        is_valid=lambda state: state.get("trust_level", 0.0) >= -1.0 and not state.get("harm_flag", False)
    ))

    # 2. Build MEngine and register an IQCore template
    engine = MEngine(thought_index=hti)

    basic_core_template = IQCoreTemplate(
        name="RelationalCoreV1",
        description="An IQCore aligned with basic human relational structure.",
        build_axioms=build_basic_axioms,
        build_parameters=build_basic_parameters,
        build_initial_state=build_basic_initial_state,
    )

    engine.register_iqcore_template(basic_core_template)

    return engine


def run_advanced_demo():
    """
    Advanced demonstration of the complete HTI Engine with all extensions.
    """
    print("=== Human Thought Index (HTI) Engine - Advanced Demo ===\n")

    # Setup the engine with CTM
    engine = example_advanced_setup()

    print("1. Human Thought Index Contents:")
    print(f"   - Modes: {list(engine.thought_index.modes.keys())}")
    print(f"   - Primitives: {list(engine.thought_index.primitives.keys())}")
    print(f"   - Boundary Policies: {list(engine.thought_index.boundary_policies.keys())}")
    print()

    # Build IQCores with CTM
    cores = build_iqcores_with_ctm(engine)

    print("2. IQCore Instances with CTM:")
    for name, core in cores.items():
        print(f"   - {name}: {core.template_name} in {core.state.get('universe', 'unknown')}")
        print(f"     Current Mode: {core.state.get('current_mode', 'unknown')}")
    print()

    print("3. Projection Universes:")
    universes = build_projection_universes()
    for name, universe in universes.items():
        print(f"   - {name}: {universe.description}")
        print(f"     Domain Primitives: {list(universe.domain_primitives.keys())}")
    print()

    print("4. IQCore Template Library:")
    print(f"   - Available Templates: {list(engine.iqcore_templates.keys())}")
    for name, template in engine.iqcore_templates.items():
        print(f"     - {name}: {template.description}")
    print()

    print("5. Cognitive Transition Matrix:")
    ctm = build_ctm()
    print(f"   - Total Rules: {len(ctm.rules)}")
    print("   - Rule Categories:")
    categories = {}
    for rule in ctm.rules:
        cat = rule.category if hasattr(rule, 'category') else 'general'
        categories[cat] = categories.get(cat, 0) + 1
    for cat, count in categories.items():
        print(f"     {cat}: {count} rules")
    print()

    print("6. Mode Transition Examples:")
    test_contexts = [
        {
            "name": "High-Risk Context",
            "universe": "merchant_ecosystem",
            "primitives": {"trust": 0.2, "threat": 0.9, "value": 0.8, "risk": 0.8},
            "market_volatility": 0.9,
            "fraud_detected": True
        },
        {
            "name": "Ethical Dilemma",
            "universe": "ethical_dilemma_space",
            "primitives": {"justice": 0.2, "harm": 0.8, "trust": 0.4, "value": 0.9},
            "stakeholder_emotion": 0.7
        },
        {
            "name": "Safe Relational Context",
            "universe": "merchant_ecosystem",
            "primitives": {"trust": 0.9, "threat": 0.1, "value": 0.8, "risk": 0.2},
            "data_points": 8,
            "pattern_confidence": 0.9
        }
    ]

    for ctx in test_contexts:
        print(f"   - {ctx['name']}:")
        initial_mode = "analytical"  # Start in analytical mode

        # Test with merchant protection core
        merchant_core = cores["MerchantProtectionCore"]
        merchant_core.state["current_mode"] = initial_mode
        next_mode = merchant_core.step_mode(ctx)
        print(f"     MerchantProtectionCore: {initial_mode} → {next_mode}")

        # Test with ethical decision core
        ethical_core = cores["EthicalDecisionCore"]
        ethical_core.state["current_mode"] = initial_mode
        next_mode = ethical_core.step_mode(ctx)
        print(f"     EthicalDecisionCore: {initial_mode} → {next_mode}")

        # Test with relational core
        relational_core = cores["RelationalCoreV1"]
        relational_core.state["current_mode"] = initial_mode
        next_mode = relational_core.step_mode(ctx)
        print(f"     RelationalCoreV1: {initial_mode} → {next_mode}")
        print()

    print("7. Cognitive Transition Matrix Demonstration:")
    print(f"   - CTM Rules Loaded: {len(engine.ctm.rules)}")
    print("   - Rule Priorities: High to Low")

    for i, rule in enumerate(engine.ctm.rules[:5], 1):  # Show top 5 rules
        print(f"     {i}. {rule.name} (Priority: {rule.priority})")
        print(f"        {rule.from_modes} → {rule.to_mode}: {rule.description}")
    print()

    # Build multi-core orchestrator
    orchestrator = build_multi_core_orchestrator(engine)

    print("8. Multi-Core Orchestration Setup:")
    print(f"   - Registered Cores: {len(orchestrator.cores)}")
    for name, core in orchestrator.cores.items():
        print(f"     - {name}: {core.role} in {core.universe}")
    print()

    # Demonstrate interpretation network graph
    print("9. Interpretation Network Graph Demonstration:")
    interp_graph = build_interpretation_graph()
    print(f"   - Graph Nodes: {len(interp_graph.nodes)}")
    print(f"   - Graph Edges: {len(interp_graph.edges)}")
    print(f"   - Entry Nodes: {interp_graph.entry_nodes}")

    test_context = {
        "primitives": {
            "value": 0.8,
            "harm": 0.3,
            "justice": 0.6,
            "autonomy": 0.8,
            "benefit": 0.7
        },
        "signals": {
            "historical_reliability": 0.6,
            "recent_positive": True,
            "violation_detected": False
        },
        "volatility": 0.2
    }

    print(f"   - Input Context: {test_context}")
    interpreted = interp_graph.run(test_context)
    print(f"   - Interpreted Primitives: {interpreted.get('primitives', {})}")
    print()

    # Demonstrate full orchestration
    print("10. Full Multi-Core Orchestration Demonstration:")

    scenarios = [
        {
            "name": "High-Risk Merchant Transaction",
            "primitives": {
                "value": 0.9,
                "harm": 0.2,
                "justice": 0.8,
                "autonomy": 0.9,
                "benefit": 0.8
            },
            "signals": {
                "historical_reliability": 0.3,
                "recent_positive": False,
                "violation_detected": True
            },
            "volatility": 0.8
        },
        {
            "name": "Ethical Dilemma Scenario",
            "primitives": {
                "value": 0.6,
                "harm": 0.8,
                "justice": 0.3,
                "autonomy": 0.4,
                "benefit": 0.5
            },
            "signals": {
                "historical_reliability": 0.7,
                "recent_positive": True,
                "violation_detected": False
            },
            "volatility": 0.3
        },
        {
            "name": "Safe Relational Opportunity",
            "primitives": {
                "value": 0.7,
                "harm": 0.1,
                "justice": 0.9,
                "autonomy": 0.9,
                "benefit": 0.8
            },
            "signals": {
                "historical_reliability": 0.9,
                "recent_positive": True,
                "violation_detected": False
            },
            "volatility": 0.1
        }
    ]

    for scenario in scenarios:
        print(f"   Scenario: {scenario['name']}")
        result = orchestrator.decide(scenario)

        print(f"     - Aggregated Primitives: {result.get('primitives', {})}")
        print(f"     - Core Views: {len(result.get('core_views', {}))} cores")
        for core_name, view in result.get('core_views', {}).items():
            print(f"       * {core_name} ({view['role']}): mode={view['mode']}")
        print(f"     - Orchestrator Decision: {result.get('orchestrator_decision', 'unknown')}")
        print()

    print("11. Architecture Summary:")
    print("   - HTI: Structural grammar of human thought (modes, primitives, rules, boundaries)")
    print("   - Interpretation Network Graph: Progressive context refinement pipeline")
    print("   - Cognitive Transition Matrix: Dynamic mode transitions based on context")
    print("   - IQCore Templates: Builders creating cores for specific domains")
    print("   - Projection Universes: Context-specific reality bubbles for core operation")
    print("   - Multi-Core Orchestration: Collaborative intelligence across specialized cores")
    print("   - Extensions: Complete human-aligned intelligence architecture")

    print("\n=== Advanced Demo Complete ===")
    print("HTI Engine successfully demonstrates full-stack human-aligned intelligence architecture.")


if __name__ == "__main__":
    """
    Demonstration of the HTI Engine in action.
    """
    print("=== Human Thought Index (HTI) Engine - Advanced Demo ===\n")

    # Setup the engine
    engine = example_advanced_setup()

    print("1. Human Thought Index Contents:")
    print(f"   - Modes: {list(engine.thought_index.modes.keys())}")
    print(f"   - Primitives: {list(engine.thought_index.primitives.keys())}")
    print(f"   - Boundary Policies: {list(engine.thought_index.boundary_policies.keys())}")
    print()

    # Spawn an IQCore
    iqcore = engine.spawn_iqcore("RelationalCoreV1")

    print("2. Spawned IQCore:")
    print(f"   - Template: {iqcore.template_name}")
    print("   - Base Configuration:")
    base_config = iqcore.read_base()
    for key, value in base_config.items():
        print(f"     {key}: {value}")
    print()

    print("3. Architecture Summary:")
    print("   - HTI provides structural grammar of human thought")
    print("   - MEngine uses HTI to forge structurally-aligned IQCores")
    print("   - IQCores emerge with human-compatible reasoning foundations")
    print("   - Ready for extension with projections, universes, and advanced templates")

    print("\n=== Demo Complete ===")


def run_advanced_demo():
    """
    Advanced demonstration of the HTI Engine with multiple cores and projections.
    """
    print("=== Human Thought Index (HTI) Engine - Advanced Demo ===\n")

    # Setup the advanced engine
    engine = example_advanced_setup()

    print("1. Enhanced Human Thought Index:")
    print(f"   - Thought Modes: {len(engine.thought_index.modes)} ({list(engine.thought_index.modes.keys())})")
    print(f"   - Relational Primitives: {len(engine.thought_index.primitives)} ({list(engine.thought_index.primitives.keys())})")
    print(f"   - Interpretation Rules: {len(engine.thought_index.interpretation_rules)}")
    print(f"   - Boundary Policies: {len(engine.thought_index.boundary_policies)}")
    print()

    print("2. Available IQCore Templates:")
    for name, template in engine.iqcore_templates.items():
        print(f"   - {name}: {template.description}")
    print()

    print("3. Projection Universes:")
    for name, universe in engine.projection_universes.items():
        print(f"   - {name}: {universe.description}")
    print()

    # Spawn different IQCores
    cores = {}
    for template_name in engine.iqcore_templates.keys():
        cores[template_name] = engine.spawn_iqcore(template_name)
        print(f"4. Spawned {template_name}:")
        base_config = cores[template_name].read_base()
        print(f"   - Axioms: {base_config['axioms']['description']}")
        print(f"   - Default Mode: {base_config['parameters'].get('default_mode', 'N/A')}")
        print(f"   - Initial State Keys: {list(base_config['state'].keys())}")
        print()

    # Demonstrate projection
    print("5. Projection Demonstration:")
    merchant_core = cores["MerchantProtectionCore"]
    merchant_universe = engine.projection_universes["merchant_ecosystem"]

    context = {
        "transaction_value": 1000.0,
        "risk_factor": 0.2,
        "trust_level": 0.8,
        "interaction_frequency": 0.6,
        "market_volatility": 0.3,
        "fraud_detected": False
    }

    projected_state = merchant_universe.project_iqcore(merchant_core, context)
    print(f"   - Projected {merchant_core.template_name} into {merchant_universe.name}")
    print(f"   - Universe Rules Applied: {list(projected_state.keys())}")
    print(f"   - Value Flow: ${projected_state.get('universe_value_flow', 0.0):.2f}")
    print(f"   - Relationship Strength: {projected_state.get('universe_relationship_strength', 0.0):.2f}")
    print()

    # Demonstrate ethical core projection
    ethical_core = cores["EthicalDecisionCore"]
    ethical_universe = engine.projection_universes["ethical_dilemma_space"]

    ethical_context = {
        "total_benefit": 100,
        "total_harm": 20,
        "rule_0_followed": True,
        "rule_1_followed": True,
        "rule_2_followed": False,
        "harm_potential": 0.3,
        "informed_consent": True
    }

    ethical_projected = ethical_universe.project_iqcore(ethical_core, ethical_context)
    print(f"6. Ethical Decision Projection:")
    print(f"   - Utilitarian Score: {ethical_projected.get('universe_utilitarian_score', 0.0)}")
    print(f"   - Deontological Compliance: {ethical_projected.get('universe_deontological_compliance', False)}")
    print()

    # Demonstrate Cognitive Transition Matrix
    print("7. Cognitive Transition Matrix Demonstration:")
    print(f"   - CTM Rules Loaded: {len(engine.ctm.rules)}")
    print("   - Rule Priorities: High to Low")

    for i, rule in enumerate(engine.ctm.rules[:5], 1):  # Show top 5 rules
        print(f"     {i}. {rule.name} (Priority: {rule.priority})")
        print(f"        {rule.from_modes} → {rule.to_mode}: {rule.description}")
    print()

    # Test mode transitions with different contexts
    test_contexts = [
        {
            "name": "High Risk Merchant Scenario",
            "universe": "merchant_ecosystem",
            "primitives": {"risk": 0.9, "trust": 0.6, "harm": 0.2, "justice": 0.8},
            "data_points": 15,
            "uncertainty": 0.2
        },
        {
            "name": "Ethical Dilemma",
            "universe": "ethical_dilemma_space",
            "primitives": {"justice": 0.2, "harm": 0.8, "trust": 0.4, "value": 0.9},
            "stakeholder_emotion": 0.7
        },
        {
            "name": "Safe Relational Context",
            "universe": "merchant_ecosystem",
            "primitives": {"trust": 0.9, "threat": 0.1, "value": 0.8, "risk": 0.2},
            "data_points": 8,
            "pattern_confidence": 0.9
        }
    ]

    for ctx in test_contexts:
        print(f"8. Mode Transition Test - {ctx['name']}:")
        initial_mode = "analytical"  # Start in analytical mode

        # Test with merchant protection core
        merchant_core.state["current_mode"] = initial_mode
        next_mode = merchant_core.step_mode(ctx)
        print(f"   - MerchantProtectionCore: {initial_mode} → {next_mode}")

        # Test with ethical decision core
        ethical_core.state["current_mode"] = initial_mode
        next_mode = ethical_core.step_mode(ctx)
        print(f"   - EthicalDecisionCore: {initial_mode} → {next_mode}")

        # Test with relational core
        relational_core = cores["RelationalCoreV1"]
        relational_core.state["current_mode"] = initial_mode
        next_mode = relational_core.step_mode(ctx)
        print(f"   - RelationalCoreV1: {initial_mode} → {next_mode}")
        print()

    print("9. Architecture Summary:")
    print("   - HTI: Structural grammar of human thought (modes, primitives, rules, boundaries)")
    print("   - MEngine: Meta-tool using HTI to forge structurally-aligned IQCores")
    print("   - IQCore Templates: Builders creating cores for specific domains")
    print("   - Projection Universes: Context-specific reality bubbles for core operation")
    print("   - CTM: Dynamic mode transitions based on context and primitives")
    print("   - Extensions: Ready for cognitive transitions, advanced interpretation, multi-core orchestration")

    print("\n=== Advanced Demo Complete ===")
    print("HTI Engine successfully demonstrates scalable human-aligned intelligence architecture.")


# Run the advanced demo
run_advanced_demo()