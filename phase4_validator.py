"""
Phase 4 → Phase 5 Validator
==============================
Validates Phase 4 call traces before Phase 5 ingestion.
Supports both JSON Schema validation and Pydantic structural validation.

This is the gatekeeper between Phase 4 and Phase 5.
"""

import json
import os


class Phase4Validator:
    """Validates a Phase 4 call trace dict against the canonical schema."""

    # AQI constitutional constants for semantic validation
    VALID_FSM_STATES = {"OPENING", "DISCOVERY", "VALUE", "OBJECTION", "CLOSE", "EXIT"}
    VALID_EXIT_REASONS = {
        "appointment_set", "soft_decline", "hard_decline",
        "telephony_unusable", "organism_unfit", "caller_hangup",
        "max_duration", "ivr_detected", "voicemail_detected",
        "no_answer", "busy",
    }
    VALID_TELEPHONY_STATES = {"Excellent", "Good", "Fair", "Poor", "Unusable"}
    GOVERNANCE_ORDER = ["Identity", "Ethics", "Personality", "Knowledge", "Mission", "Output"]

    def __init__(self, schema_path=None):
        if schema_path is None:
            schema_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "phase4_call_trace.schema.json"
            )
        self._schema_path = schema_path
        self._schema = None
        self._jsonschema_available = False

        try:
            import jsonschema  # noqa: F401
            self._jsonschema_available = True
        except ImportError:
            pass

    def _load_schema(self):
        if self._schema is None and os.path.exists(self._schema_path):
            with open(self._schema_path, "r", encoding="utf-8") as f:
                self._schema = json.load(f)
        return self._schema

    def validate_schema(self, trace: dict) -> list:
        """
        JSON Schema validation (requires jsonschema package).
        Returns list of error messages. Empty list = valid.
        """
        if not self._jsonschema_available:
            return []  # Skip if jsonschema not installed

        schema = self._load_schema()
        if schema is None:
            return ["Schema file not found"]

        import jsonschema
        errors = []
        validator = jsonschema.Draft7Validator(schema)
        for err in validator.iter_errors(trace):
            errors.append(f"{err.json_path}: {err.message}")
        return errors

    def validate_structural(self, trace: dict) -> list:
        """
        Structural validation — checks required fields without jsonschema.
        Returns list of error messages. Empty list = valid.
        """
        errors = []

        # Top-level
        if not isinstance(trace, dict):
            return ["Trace must be a dict"]

        for field in ("call_id", "metadata", "turns", "final"):
            if field not in trace:
                errors.append(f"Missing required field: {field}")

        if errors:
            return errors

        # Metadata
        meta = trace.get("metadata", {})
        for field in ("timestamp_start", "timestamp_end"):
            if field not in meta:
                errors.append(f"metadata.{field} missing")

        # Turns
        turns = trace.get("turns", [])
        if not isinstance(turns, list):
            errors.append("turns must be a list")
        else:
            for i, t in enumerate(turns):
                for field in ("turn_index", "fsm_prev_state", "fsm_event",
                              "fsm_state", "prompt_layers", "context", "health_snapshot"):
                    if field not in t:
                        errors.append(f"turns[{i}].{field} missing")

        # Final block
        final = trace.get("final", {})
        for field in ("fsm_state", "exit_reason", "health_trajectory",
                      "telephony_trajectory", "outcome_vector"):
            if field not in final:
                errors.append(f"final.{field} missing")

        return errors

    def validate_semantic(self, trace: dict) -> list:
        """
        Semantic validation — checks AQI constitutional compliance.
        Returns list of warning messages.
        """
        warnings = []

        # Check FSM states
        for i, t in enumerate(trace.get("turns", [])):
            state = t.get("fsm_state", "")
            prev = t.get("fsm_prev_state", "")
            if state not in self.VALID_FSM_STATES:
                warnings.append(f"turns[{i}].fsm_state '{state}' not in valid FSM states")
            if prev not in self.VALID_FSM_STATES:
                warnings.append(f"turns[{i}].fsm_prev_state '{prev}' not in valid FSM states")

        # Check exit reason
        exit_reason = trace.get("final", {}).get("exit_reason", "")
        if exit_reason not in self.VALID_EXIT_REASONS:
            warnings.append(f"final.exit_reason '{exit_reason}' not in valid exit reasons")

        # Check health levels
        for i, h in enumerate(trace.get("final", {}).get("health_trajectory", [])):
            level = h.get("organism_level", 0)
            if level < 1 or level > 4:
                warnings.append(f"health_trajectory[{i}].organism_level {level} out of range [1,4]")

        # Check governance order in prompt layers
        for i, t in enumerate(trace.get("turns", [])):
            layers = t.get("prompt_layers", {})
            if isinstance(layers, dict):
                keys = list(layers.keys())
                expected_positions = []
                for k in keys:
                    if k in self.GOVERNANCE_ORDER:
                        expected_positions.append(self.GOVERNANCE_ORDER.index(k))
                if expected_positions != sorted(expected_positions):
                    warnings.append(f"turns[{i}].prompt_layers governance order violation")

        return warnings

    def validate(self, trace: dict) -> dict:
        """
        Full validation pipeline.

        Returns
        -------
        dict with keys: valid, schema_errors, structural_errors, semantic_warnings
        """
        schema_errors = self.validate_schema(trace)
        structural_errors = self.validate_structural(trace)
        semantic_warnings = self.validate_semantic(trace)

        return {
            "valid": len(schema_errors) == 0 and len(structural_errors) == 0,
            "schema_errors": schema_errors,
            "structural_errors": structural_errors,
            "semantic_warnings": semantic_warnings,
        }

    def validate_strict(self, trace: dict) -> bool:
        """Returns True if all validations pass (including semantic)."""
        result = self.validate(trace)
        return result["valid"] and len(result["semantic_warnings"]) == 0
