"""Authority management and validation."""

from __future__ import annotations

from typing import Dict, Any, Optional
from talk.schema import Lineage, AuthorityChain


class AuthorityManager:
    """
    Manages authority levels and validates authority chains.

    This is the gatekeeper for who can do what in AQI.
    """

    def __init__(self):
        self.authority_levels: Dict[str, int] = {}
        self.trusted_sources: Dict[str, int] = {}

        self._setup_default_authorities()

    def _setup_default_authorities(self):
        """Set up default authority mappings."""
        self.authority_levels = {
            "engine": 1,
            "human": 2,
            "supervisor": 3,
            "administrator": 4,
            "system": 5,
        }

        self.trusted_sources = {
            "MODULE:inventory": 1,
            "MODULE:metadata": 1,
            "MODULE:crossrefs": 1,
            "MODULE:graph": 2,
            "MODULE:summaries": 1,
            "MODULE:normalization": 2,
            "HUMAN:Tim": 4,
            "SYSTEM:filesystem": 1,
            "ENGINE:ExternalX": 1,
        }

    def validate_authority_chain(self, lineage: Lineage) -> Dict[str, Any]:
        """
        Validate an authority chain.

        Returns validation results including authority level and any issues.
        """
        issues = []
        authority_level = 0

        # Check source authority
        source_key = f"{lineage.source.source_type}:{lineage.source.source_id}"
        if source_key in self.trusted_sources:
            authority_level = self.trusted_sources[source_key]
        else:
            # Unknown source - assign minimal authority
            authority_level = 1
            issues.append(f"unknown_source: {source_key}")

        # Check authority level mapping
        source_type_level = self.authority_levels.get(lineage.source.source_type, 1)
        if source_type_level > authority_level:
            authority_level = source_type_level

        # Check for authority chain issues
        if lineage.parent_lineage_id:
            issues.append("authority_chain_present")  # Would need to validate chain

        # Check timestamp (basic freshness check)
        # This would be more sophisticated in production

        return {
            "valid": len(issues) == 0 or issues == ["authority_chain_present"],
            "authority_level": authority_level,
            "issues": issues,
            "source_trusted": source_key in self.trusted_sources,
        }

    def get_required_authority(self, operation_type: str) -> int:
        """Get the minimum authority level required for an operation."""
        requirements = {
            "graph_mutation": 2,
            "constraint_override": 3,
            "authority_modification": 4,
            "system_configuration": 4,
        }
        return requirements.get(operation_type, 1)

    def can_perform_operation(self, lineage: Lineage, operation_type: str) -> bool:
        """Check if the given lineage has authority for an operation."""
        validation = self.validate_authority_chain(lineage)
        required = self.get_required_authority(operation_type)
        return validation["authority_level"] >= required

    def register_trusted_source(self, source_key: str, authority_level: int) -> None:
        """Register a new trusted source."""
        self.trusted_sources[source_key] = authority_level

    def update_authority_level(self, source_type: str, level: int) -> None:
        """Update authority level for a source type."""
        self.authority_levels[source_type] = level