"""Core governance engine."""

from __future__ import annotations

from typing import Any, Dict, Optional
from talk import TalkInterpreter
from talk.schema import TalkPacket
from .decision_packet import DecisionPacket, DecisionType
from .governance_rules import GovernanceRules
from .authority_manager import AuthorityManager
from talk.utils import generate_id, get_timestamp


class GovernanceEngine:
    """
    Core governance engine that enforces authority and constraints.

    This is where AQI becomes accountable and governed.
    """

    def __init__(self, interpreter: Optional[TalkInterpreter] = None):
        self.interpreter = interpreter or TalkInterpreter()
        self.rules = GovernanceRules()
        self.authority_manager = AuthorityManager()

    def evaluate_packet(self, packet: TalkPacket) -> DecisionPacket:
        """
        Evaluate a TalkPacket and make a governance decision.

        This is the main entry point for governance enforcement.
        """
        # Validate authority chain
        authority_validation = self.authority_manager.validate_authority_chain(packet.lineage)

        # Evaluate against rules
        rule_evaluation = self.rules.evaluate_packet(packet)

        # Make decision
        decision = self._make_decision(packet, authority_validation, rule_evaluation)

        # Create decision packet
        decision_packet = DecisionPacket(
            id=generate_id(),
            decision=decision["type"],
            original_packet=packet,
            reason=decision["reason"],
            violated_constraints=decision.get("violated_constraints", []),
            required_authority_level=rule_evaluation["required_authority_level"],
            suggested_modifications=decision.get("modifications", {}),
            lineage=packet.lineage,  # Use the packet's lineage
            timestamp=get_timestamp(),
            metadata={
                "authority_validation": authority_validation,
                "rule_evaluation": rule_evaluation,
            }
        )

        return decision_packet

    def _make_decision(
        self,
        packet: TalkPacket,
        authority: Dict[str, Any],
        rules: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Make a governance decision based on evaluation results."""

        # Authority check
        if not authority["valid"]:
            return {
                "type": DecisionType.REJECT,
                "reason": f"Invalid authority chain: {authority['issues']}",
            }

        # Authority level check
        required_level = rules["required_authority_level"]
        actual_level = authority["authority_level"]
        if actual_level < required_level:
            return {
                "type": DecisionType.ESCALATE,
                "reason": f"Insufficient authority (has {actual_level}, needs {required_level})",
            }

        # Rule violations
        if not rules["compliant"]:
            violations = rules["violations"]
            return {
                "type": DecisionType.REJECT,
                "reason": f"Governance rule violations: {violations}",
                "violated_constraints": violations,
            }

        # All checks passed
        return {
            "type": DecisionType.APPROVE,
            "reason": "All governance checks passed",
        }

    def process_decision(self, decision: DecisionPacket) -> None:
        """
        Process a governance decision.

        This would trigger appropriate actions based on the decision.
        """
        if decision.decision == DecisionType.APPROVE:
            self._process_approval(decision)
        elif decision.decision == DecisionType.REJECT:
            self._process_rejection(decision)
        elif decision.decision == DecisionType.ESCALATE:
            self._process_escalation(decision)
        elif decision.decision == DecisionType.MODIFY:
            self._process_modification(decision)

    def _process_approval(self, decision: DecisionPacket) -> None:
        """Process an approved decision."""
        # Emit the original packet through the interpreter
        self.interpreter.process_packet(decision.original_packet)

        # Log the approval
        self._log_decision(decision, "approved")

    def _process_rejection(self, decision: DecisionPacket) -> None:
        """Process a rejected decision."""
        # Do not emit the packet
        # Log the rejection
        self._log_decision(decision, "rejected")

        # Could emit a rejection packet
        self._emit_rejection_packet(decision)

    def _process_escalation(self, decision: DecisionPacket) -> None:
        """Process an escalated decision."""
        # Queue for higher authority review
        self._log_decision(decision, "escalated")

        # Could emit an escalation packet
        self._emit_escalation_packet(decision)

    def _process_modification(self, decision: DecisionPacket) -> None:
        """Process a modification decision."""
        # Apply suggested modifications
        modified_packet = self._apply_modifications(
            decision.original_packet,
            decision.suggested_modifications
        )

        # Process the modified packet
        self.interpreter.process_packet(modified_packet)

        # Log the modification
        self._log_decision(decision, "modified")

    def _apply_modifications(self, packet: TalkPacket, modifications: Dict[str, Any]) -> TalkPacket:
        """Apply suggested modifications to a packet."""
        # This would create a modified version of the packet
        # Implementation depends on what modifications are allowed
        return packet

    def _log_decision(self, decision: DecisionPacket, action: str) -> None:
        """Log a governance decision."""
        # This would write to governance logs
        print(f"GOVERNANCE: {action.upper()} - {decision.reason}")

    def _emit_rejection_packet(self, decision: DecisionPacket) -> None:
        """Emit a packet indicating rejection."""
        # Implementation for emitting rejection notifications
        pass

    def _emit_escalation_packet(self, decision: DecisionPacket) -> None:
        """Emit a packet indicating escalation."""
        # Implementation for emitting escalation notifications
        pass