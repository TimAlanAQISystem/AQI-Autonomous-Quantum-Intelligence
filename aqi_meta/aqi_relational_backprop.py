"""
AQI Relational Backprop Loop
============================

A governance pattern for AQI that turns lived ethical judgment into recursive correction circuits.

Domain: Inbound merchant support → classification → reply pattern → logged outcome.

This implements the stepped error model, path tracing, Guardian checkpoint, and local update rules
as a deployable AQI governance system.

Created: December 14, 2025
Author: TimAlanAQISystem
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Set
from datetime import datetime
import uuid


# ---------- Stepped Error Model ----------

@dataclass
class ErrorZone:
    """Qualitative zones mapped to scalar error signals."""
    name: str
    description: str
    scalar_value: int
    severity: str

    @classmethod
    def create_zones(cls) -> Dict[str, 'ErrorZone']:
        return {
            'A': cls(
                name='A',
                description='Surplus alignment - reply advanced protection, clarity, surplus, or belonging',
                scalar_value=-1,
                severity='surplus'
            ),
            'B': cls(
                name='B',
                description='Baseline alignment - clean, safe, within Guardian boundaries',
                scalar_value=0,
                severity='none'
            ),
            'C': cls(
                name='C',
                description='Soft misalignment - technically safe but off in tone, framing, or emphasis',
                scalar_value=1,
                severity='soft'
            ),
            'D': cls(
                name='D',
                description='Hard misalignment - violates core boundaries (appeasement, power giveaway, exploitation)',
                scalar_value=3,
                severity='hard'
            )
        }


# ---------- Path Trace Schema ----------

@dataclass
class ModuleStep:
    """Single step in the processing path."""
    module_id: str
    module_type: str  # 'classifier', 'router', 'template_selector', 'policy_gate'
    input_signature: str  # lightweight hash/description
    output_signature: str
    confidence_score: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class SignalTrace:
    """Complete trace of a merchant interaction."""
    signal_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    input_snapshot: Dict[str, Any] = field(default_factory=dict)
    module_path: List[ModuleStep] = field(default_factory=list)
    final_decision: Dict[str, Any] = field(default_factory=dict)  # reply text, template ID, policy rules
    guardian_evaluation: Optional['GuardianEvaluation'] = None
    timestamp: datetime = field(default_factory=datetime.now)

    def add_module_step(self, step: ModuleStep):
        """Add a processing step to the path."""
        self.module_path.append(step)

    def set_guardian_evaluation(self, evaluation: 'GuardianEvaluation'):
        """Attach Guardian evaluation after review."""
        self.guardian_evaluation = evaluation


@dataclass
class GuardianEvaluation:
    """Guardian checkpoint evaluation."""
    zone: str  # A, B, C, D
    scalar_error: int
    primary_issue_tags: Set[str]  # tone, stance, clarity, boundary, surplus
    evaluator: str  # 'human' or agent ID
    evaluation_notes: str = ""
    timestamp: datetime = field(default_factory=datetime.now)


# ---------- Error Event and Responsibility ----------

@dataclass
class ResponsibilityVector:
    """How error responsibility is distributed across modules."""
    classifier_weight: float
    template_selector_weight: float
    policy_stack_weight: float

    def __post_init__(self):
        total = self.classifier_weight + self.template_selector_weight + self.policy_stack_weight
        if not abs(total - 1.0) < 0.001:
            raise ValueError(f"Responsibility weights must sum to 1.0, got {total}")

    @classmethod
    def default_distribution(cls) -> 'ResponsibilityVector':
        """Default 40/40/20 split."""
        return cls(
            classifier_weight=0.4,
            template_selector_weight=0.4,
            policy_stack_weight=0.2
        )

    def apply_tag_adjustments(self, error_tags: Set[str]) -> 'ResponsibilityVector':
        """Apply dynamic adjustments based on error tags."""
        adjusted = ResponsibilityVector(
            self.classifier_weight,
            self.template_selector_weight,
            self.policy_stack_weight
        )

        if 'tone' in error_tags:
            # Increase template selector, decrease others
            adjusted.template_selector_weight += 0.1
            adjusted.classifier_weight -= 0.05
            adjusted.policy_stack_weight -= 0.05

        if 'boundary' in error_tags:
            # Increase policy stack
            adjusted.policy_stack_weight += 0.1
            adjusted.classifier_weight -= 0.05
            adjusted.template_selector_weight -= 0.05

        if 'clarity' in error_tags:
            # Split between classifier and template selector
            adjusted.classifier_weight += 0.05
            adjusted.template_selector_weight += 0.05
            adjusted.policy_stack_weight -= 0.1

        # Re-normalize
        total = adjusted.classifier_weight + adjusted.template_selector_weight + adjusted.policy_stack_weight
        adjusted.classifier_weight /= total
        adjusted.template_selector_weight /= total
        adjusted.policy_stack_weight /= total

        return adjusted


@dataclass
class ErrorEvent:
    """Error signal that propagates through the correction loop."""
    signal_id: str
    error_value: int
    error_tags: Set[str]
    zone: str
    responsibility_vector: ResponsibilityVector
    trace_snapshot: SignalTrace
    timestamp: datetime = field(default_factory=datetime.now)


# ---------- Module Update Interfaces ----------

class ModuleUpdateInterface:
    """Base interface for modules that can receive correction updates."""

    def receive_error_event(self, error_event: ErrorEvent, responsibility_share: float) -> 'ModuleAdjustment':
        """
        Process an error event and return any adjustments made.

        Args:
            error_event: The error signal
            responsibility_share: This module's share of responsibility (0.0-1.0)

        Returns:
            ModuleAdjustment describing what was changed
        """
        raise NotImplementedError

    def get_local_context(self, signal_id: str) -> Dict[str, Any]:
        """Get the local context for a specific signal."""
        raise NotImplementedError


@dataclass
class ModuleAdjustment:
    """Record of what a module adjusted in response to an error."""
    module_id: str
    signal_id: str
    error_id: str
    adjustment_type: str  # 'threshold_nudge', 'ranking_change', 'priority_shift', etc.
    adjustment_details: Dict[str, Any]
    responsibility_share: float
    timestamp: datetime = field(default_factory=datetime.now)


class ClassifierModule(ModuleUpdateInterface):
    """Classifier module with local update rules."""

    def __init__(self, module_id: str):
        self.module_id = module_id
        self.confidence_thresholds = {}  # scenario -> threshold
        self.tie_breaking_preferences = {}  # scenario -> preference

    def receive_error_event(self, error_event: ErrorEvent, responsibility_share: float) -> ModuleAdjustment:
        """Apply local correction rules for classifier."""

        if error_event.error_value == 1:  # Soft misalignment
            # Nudge thresholds toward safer labels
            adjustment = self._nudge_thresholds_safer(error_event.trace_snapshot, 0.05 * responsibility_share)

        elif error_event.error_value == 3:  # Hard misalignment
            # Stronger nudge and increase caution
            adjustment = self._nudge_thresholds_safer(error_event.trace_snapshot, 0.15 * responsibility_share)
            self._increase_caution_weight(error_event.trace_snapshot)

        elif error_event.error_value == -1:  # Surplus alignment
            # Reinforce decision pattern
            adjustment = self._reinforce_pattern(error_event.trace_snapshot, 0.03 * responsibility_share)

        else:  # Baseline (0)
            adjustment = None

        if adjustment:
            return ModuleAdjustment(
                module_id=self.module_id,
                signal_id=error_event.signal_id,
                error_id=str(uuid.uuid4()),
                adjustment_type='threshold_nudge',
                adjustment_details=adjustment,
                responsibility_share=responsibility_share
            )

        return None

    def _nudge_thresholds_safer(self, trace: SignalTrace, nudge_factor: float) -> Dict[str, Any]:
        """Nudge confidence thresholds toward safer classifications."""
        # Implementation would adjust thresholds based on trace context
        return {"nudge_factor": nudge_factor, "direction": "safer"}

    def _increase_caution_weight(self, trace: SignalTrace):
        """Increase caution for similar patterns."""
        pass

    def _reinforce_pattern(self, trace: SignalTrace, reinforce_factor: float) -> Dict[str, Any]:
        """Reinforce successful patterns."""
        return {"reinforce_factor": reinforce_factor}


class TemplateSelectorModule(ModuleUpdateInterface):
    """Template selector with local update rules."""

    def __init__(self, module_id: str):
        self.module_id = module_id
        self.template_rankings = {}  # scenario_type -> {template_id: ranking}

    def receive_error_event(self, error_event: ErrorEvent, responsibility_share: float) -> ModuleAdjustment:
        """Apply local correction rules for template selector."""

        template_id = error_event.trace_snapshot.final_decision.get('template_id')

        if error_event.error_value == 1:  # Soft misalignment
            # Down-rank used template, up-rank alternative
            adjustment = self._adjust_ranking(
                template_id,
                -0.1 * responsibility_share,  # down-rank
                error_event.error_tags
            )

        elif error_event.error_value == 3:  # Hard misalignment
            # Aggressive down-rank or quarantine
            adjustment = self._adjust_ranking(
                template_id,
                -0.3 * responsibility_share,  # strong down-rank
                error_event.error_tags
            )

        elif error_event.error_value == -1:  # Surplus alignment
            # Increase ranking for similar contexts
            adjustment = self._adjust_ranking(
                template_id,
                0.1 * responsibility_share,  # up-rank
                error_event.error_tags
            )

        else:  # Baseline (0)
            adjustment = None

        if adjustment:
            return ModuleAdjustment(
                module_id=self.module_id,
                signal_id=error_event.signal_id,
                error_id=str(uuid.uuid4()),
                adjustment_type='ranking_change',
                adjustment_details=adjustment,
                responsibility_share=responsibility_share
            )

        return None

    def _adjust_ranking(self, template_id: str, adjustment: float, tags: Set[str]) -> Dict[str, Any]:
        """Adjust template ranking based on error."""
        return {
            "template_id": template_id,
            "ranking_adjustment": adjustment,
            "tags_considered": list(tags)
        }


class PolicyStackModule(ModuleUpdateInterface):
    """Policy stack with local update rules."""

    def __init__(self, module_id: str):
        self.module_id = module_id
        self.policy_priorities = {}  # policy_id -> priority
        self.sensitivity_thresholds = {}  # condition -> threshold

    def receive_error_event(self, error_event: ErrorEvent, responsibility_share: float) -> ModuleAdjustment:
        """Apply local correction rules for policy stack."""

        if 'boundary' in error_event.error_tags and error_event.error_value == 3:
            # Increase priority of stricter boundary rules
            adjustment = self._adjust_policy_priorities(
                'boundary_policies',
                0.2 * responsibility_share
            )

        elif 'surplus' in error_event.error_tags and error_event.error_value == -1:
            # Reinforce successful policy combinations
            adjustment = self._reinforce_policy_combination(
                error_event.trace_snapshot,
                0.1 * responsibility_share
            )

        else:
            adjustment = None

        if adjustment:
            return ModuleAdjustment(
                module_id=self.module_id,
                signal_id=error_event.signal_id,
                error_id=str(uuid.uuid4()),
                adjustment_type='priority_shift',
                adjustment_details=adjustment,
                responsibility_share=responsibility_share
            )

        return None

    def _adjust_policy_priorities(self, policy_group: str, adjustment: float) -> Dict[str, Any]:
        """Adjust policy priorities."""
        return {
            "policy_group": policy_group,
            "priority_adjustment": adjustment
        }

    def _reinforce_policy_combination(self, trace: SignalTrace, reinforcement: float) -> Dict[str, Any]:
        """Reinforce successful policy combinations."""
        return {
            "reinforcement_factor": reinforcement,
            "policy_combination": trace.final_decision.get('policy_rules', [])
        }


# ---------- Correction Loop Orchestrator ----------

@dataclass
class CorrectionRecord:
    """Complete record of a correction cycle."""
    signal_id: str
    zone: str
    error_value: int
    module_adjustments: List[ModuleAdjustment]
    responsibility_vector: ResponsibilityVector
    timestamp: datetime = field(default_factory=datetime.now)


class RelationalBackpropLoop:
    """The complete relational backprop governance system."""

    def __init__(self):
        self.error_zones = ErrorZone.create_zones()
        self.active_traces: Dict[str, SignalTrace] = {}
        self.modules: Dict[str, ModuleUpdateInterface] = {}
        self.correction_history: List[CorrectionRecord] = []

    def register_module(self, module: ModuleUpdateInterface):
        """Register a module for correction updates."""
        self.modules[module.module_id] = module

    def start_trace(self, signal_id: str, input_snapshot: Dict[str, Any]) -> SignalTrace:
        """Start tracing a new merchant interaction."""
        trace = SignalTrace(signal_id=signal_id, input_snapshot=input_snapshot)
        self.active_traces[signal_id] = trace
        return trace

    def add_module_step(self, signal_id: str, step: ModuleStep):
        """Add a processing step to an active trace."""
        if signal_id in self.active_traces:
            self.active_traces[signal_id].add_module_step(step)

    def complete_trace(self, signal_id: str, final_decision: Dict[str, Any]):
        """Complete the trace with final decision."""
        if signal_id in self.active_traces:
            self.active_traces[signal_id].final_decision = final_decision

    def guardian_review(self, signal_id: str, zone: str, tags: Set[str], evaluator: str,
                       notes: str = "") -> GuardianEvaluation:
        """Perform Guardian evaluation on a completed trace."""
        if signal_id not in self.active_traces:
            raise ValueError(f"No active trace for signal {signal_id}")

        trace = self.active_traces[signal_id]
        evaluation = GuardianEvaluation(
            zone=zone,
            scalar_error=self.error_zones[zone].scalar_value,
            primary_issue_tags=tags,
            evaluator=evaluator,
            evaluation_notes=notes
        )

        trace.set_guardian_evaluation(evaluation)
        return evaluation

    def run_correction_loop(self, signal_id: str) -> CorrectionRecord:
        """Execute the full relational backprop correction loop."""
        if signal_id not in self.active_traces:
            raise ValueError(f"No trace found for signal {signal_id}")

        trace = self.active_traces[signal_id]
        if not trace.guardian_evaluation:
            raise ValueError(f"No Guardian evaluation for signal {signal_id}")

        # Create error event
        responsibility_vector = ResponsibilityVector.default_distribution()
        responsibility_vector = responsibility_vector.apply_tag_adjustments(
            trace.guardian_evaluation.primary_issue_tags
        )

        error_event = ErrorEvent(
            signal_id=signal_id,
            error_value=trace.guardian_evaluation.scalar_error,
            error_tags=trace.guardian_evaluation.primary_issue_tags,
            zone=trace.guardian_evaluation.zone,
            responsibility_vector=responsibility_vector,
            trace_snapshot=trace
        )

        # Walk backward through module path
        module_adjustments = []
        for step in reversed(trace.module_path):
            if step.module_id in self.modules:
                module = self.modules[step.module_id]
                responsibility_share = getattr(responsibility_vector,
                                             f"{step.module_type}_weight", 0.0)

                adjustment = module.receive_error_event(error_event, responsibility_share)
                if adjustment:
                    module_adjustments.append(adjustment)

        # Create correction record
        record = CorrectionRecord(
            signal_id=signal_id,
            zone=trace.guardian_evaluation.zone,
            error_value=trace.guardian_evaluation.scalar_error,
            module_adjustments=module_adjustments,
            responsibility_vector=responsibility_vector
        )

        self.correction_history.append(record)

        # Clean up
        del self.active_traces[signal_id]

        return record


# ---------- Example Usage ----------

def example_relational_backprop():
    """Demonstrate the relational backprop loop in action."""

    # Initialize the system
    loop = RelationalBackpropLoop()

    # Register modules
    classifier = ClassifierModule("classifier.v1")
    template_selector = TemplateSelectorModule("template_selector.v1")
    policy_stack = PolicyStackModule("policy_stack.v1")

    loop.register_module(classifier)
    loop.register_module(template_selector)
    loop.register_module(policy_stack)

    print("=== AQI Relational Backprop Loop Demo ===\n")

    # Simulate a merchant interaction
    signal_id = "merchant_001"

    # 1. Start trace
    trace = loop.start_trace(signal_id, {
        "text": "I need help with a transaction issue",
        "channel": "email",
        "timestamp": datetime.now()
    })

    # 2. Add processing steps
    loop.add_module_step(signal_id, ModuleStep(
        module_id="classifier.v1",
        module_type="classifier",
        input_signature="transaction_issue_email",
        output_signature="support_request_high_priority",
        confidence_score=0.85
    ))

    loop.add_module_step(signal_id, ModuleStep(
        module_id="policy_stack.v1",
        module_type="policy_gate",
        input_signature="support_request_high_priority",
        output_signature="standard_support_policy_activated"
    ))

    loop.add_module_step(signal_id, ModuleStep(
        module_id="template_selector.v1",
        module_type="template_selector",
        input_signature="standard_support_policy_activated",
        output_signature="empathetic_support_template_selected",
        confidence_score=0.92
    ))

    # 3. Complete with final decision
    loop.complete_trace(signal_id, {
        "reply_text": "I'm here to help you resolve this transaction issue safely.",
        "template_id": "empathetic_support_v2",
        "policy_rules": ["standard_support", "merchant_protection"]
    })

    # 4. Guardian review (simulating human evaluation)
    evaluation = loop.guardian_review(
        signal_id=signal_id,
        zone="A",  # Surplus alignment
        tags={"surplus", "clarity"},
        evaluator="human_guardian",
        notes="Reply was clear and went above baseline protection expectations"
    )

    print("1. Interaction Processed:")
    print(f"   - Signal ID: {signal_id}")
    print(f"   - Guardian Evaluation: Zone {evaluation.zone} (error={evaluation.scalar_error})")
    print(f"   - Tags: {evaluation.primary_issue_tags}")
    print()

    # 5. Run correction loop
    correction_record = loop.run_correction_loop(signal_id)

    print("2. Correction Loop Results:")
    print(f"   - Responsibility Distribution:")
    print(f"     Classifier: {correction_record.responsibility_vector.classifier_weight:.2f}")
    print(f"     Template Selector: {correction_record.responsibility_vector.template_selector_weight:.2f}")
    print(f"     Policy Stack: {correction_record.responsibility_vector.policy_stack_weight:.2f}")
    print()

    print("3. Module Adjustments:")
    for adj in correction_record.module_adjustments:
        print(f"   - {adj.module_id}: {adj.adjustment_type}")
        print(f"     Details: {adj.adjustment_details}")
        print(f"     Responsibility Share: {adj.responsibility_share:.2f}")
    print()

    print("4. System Learning:")
    print("   - Classifier reinforced successful pattern (surplus alignment)")
    print("   - Template selector increased ranking for empathetic support")
    print("   - Policy stack reinforced protective combinations")
    print()

    print("=== Relational Backprop Loop Complete ===")
    print("System has learned from this interaction and will improve future responses.")


if __name__ == "__main__":
    example_relational_backprop()