"""Governance rules and policies."""

from __future__ import annotations

from typing import Dict, List, Any, Callable
from talk.schema import TalkPacket, ConstraintType, IntentType


class GovernanceRules:
    """
    Defines and enforces governance rules for AQI operations.

    This is where authority, constraints, and business rules are codified.
    """

    def __init__(self):
        self.rules: Dict[str, Callable[[TalkPacket], bool]] = {}
        self.authority_requirements: Dict[str, int] = {}
        self.constraint_policies: Dict[ConstraintType, Callable[[TalkPacket], bool]] = {}

        self._setup_default_rules()
        self._setup_authority_requirements()
        self._setup_constraint_policies()

    def _setup_default_rules(self):
        """Set up default governance rules."""

        # Metadata cannot override inventory
        self.rules["metadata_cannot_override_inventory"] = self._rule_metadata_cannot_override_inventory

        # Graph mutations require authority level ≥ 2
        self.rules["graph_mutation_authority"] = self._rule_graph_mutation_authority

        # Summaries cannot modify canonical tags
        self.rules["summaries_preserve_tags"] = self._rule_summaries_preserve_tags

        # Normalization is immutable
        self.rules["normalization_immutable"] = self._rule_normalization_immutable

        # Crossrefs corrections require provenance
        self.rules["crossrefs_correction_provenance"] = self._rule_crossrefs_correction_provenance

    def _setup_authority_requirements(self):
        """Set up authority level requirements."""
        self.authority_requirements = {
            "graph_mutation": 2,
            "normalization_override": 3,
            "constraint_violation": 3,
            "authority_chain_modification": 4,
        }

    def _setup_constraint_policies(self):
        """Set up constraint enforcement policies."""
        self.constraint_policies = {
            ConstraintType.IMMUTABLE: self._policy_immutable,
            ConstraintType.REQUIRE_ACK: self._policy_require_ack,
            ConstraintType.REQUIRE_LINEAGE: self._policy_require_lineage,
            ConstraintType.LOCAL_ONLY: self._policy_local_only,
            ConstraintType.EXTERNAL_ONLY: self._policy_external_only,
        }

    def evaluate_packet(self, packet: TalkPacket) -> Dict[str, Any]:
        """
        Evaluate a packet against all governance rules.

        Returns a dict with rule violations and required actions.
        """
        violations = []
        required_actions = []

        # Check all rules
        for rule_name, rule_func in self.rules.items():
            if not rule_func(packet):
                violations.append(rule_name)

        # Check constraints
        for constraint in packet.constraints:
            if constraint in self.constraint_policies:
                policy_func = self.constraint_policies[constraint]
                if not policy_func(packet):
                    violations.append(f"constraint_{constraint.value}")

        # Determine required authority
        required_authority = self._get_required_authority(packet)

        # Determine required actions
        if violations:
            required_actions.append("review_required")
        if required_authority > 1:
            required_actions.append("authority_check")

        return {
            "violations": violations,
            "required_actions": required_actions,
            "required_authority_level": required_authority,
            "compliant": len(violations) == 0,
        }

    def _get_required_authority(self, packet: TalkPacket) -> int:
        """Determine the authority level required for this packet."""
        resource_type = packet.state_change.resource_type

        # Check specific requirements
        if resource_type.startswith("graph"):
            return self.authority_requirements.get("graph_mutation", 1)
        elif resource_type.startswith("normalized"):
            return self.authority_requirements.get("normalization_override", 1)
        elif ConstraintType.IMMUTABLE in packet.constraints:
            return self.authority_requirements.get("constraint_violation", 1)

        return 1  # Default authority level

    # Rule implementations
    def _rule_metadata_cannot_override_inventory(self, packet: TalkPacket) -> bool:
        """Metadata cannot override inventory facts."""
        if packet.state_change.resource_type == "file_metadata":
            # Check if trying to modify inventory-level attributes
            payload = packet.state_change.payload
            if "path" in payload or "size" in payload:
                return False  # Metadata shouldn't modify path or size
        return True

    def _rule_graph_mutation_authority(self, packet: TalkPacket) -> bool:
        """Graph mutations require appropriate authority."""
        return packet.state_change.resource_type.startswith("graph")

    def _rule_summaries_preserve_tags(self, packet: TalkPacket) -> bool:
        """Summaries cannot modify canonical tags."""
        if packet.state_change.resource_type.startswith("summary"):
            payload = packet.state_change.payload
            if "tags" in payload:
                # Check if trying to modify existing tags inappropriately
                return packet.intent == IntentType.CREATE
        return True

    def _rule_normalization_immutable(self, packet: TalkPacket) -> bool:
        """Normalization artifacts are immutable."""
        if packet.state_change.resource_type.startswith("normalized"):
            return packet.state_change.operation == "create"
        return True

    def _rule_crossrefs_correction_provenance(self, packet: TalkPacket) -> bool:
        """Crossrefs corrections require strong provenance."""
        if (packet.state_change.resource_type == "file_crossrefs" and
            packet.intent == IntentType.CORRECT):
            return packet.lineage is not None
        return True

    # Constraint policy implementations
    def _policy_immutable(self, packet: TalkPacket) -> bool:
        """Immutable resources cannot be modified."""
        return packet.state_change.operation in ["create", "read"]

    def _policy_require_ack(self, packet: TalkPacket) -> bool:
        """Packets requiring ack should have been acknowledged."""
        # This would check for ack in metadata or separate tracking
        return "acknowledged" in packet.metadata

    def _policy_require_lineage(self, packet: TalkPacket) -> bool:
        """Packets must have lineage."""
        return packet.lineage is not None

    def _policy_local_only(self, packet: TalkPacket) -> bool:
        """Local-only packets should not be propagated externally."""
        # This would be enforced at the transmission layer
        return True

    def _policy_external_only(self, packet: TalkPacket) -> bool:
        """External-only packets should not be persisted internally."""
        # This would be enforced at the storage layer
        return True