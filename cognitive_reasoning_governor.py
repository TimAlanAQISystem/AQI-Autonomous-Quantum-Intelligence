import json
import os
from typing import Dict, Any


class CRGConfig:
    def __init__(self, path: str):
        if not os.path.exists(path):
            self.novelty_levels = {"0": {"allowed_reasoning": []}}
            self.mapping_rules = {"defaults": {"max_level": 1}, "temperature_thresholds": {"low": 40, "medium": 65, "high": 80}}
            self.global_forbidden = []
            return

        with open(path, "r") as f:
            cfg = json.load(f)

        self.novelty_levels = cfg["novelty"]["levels"]
        self.mapping_rules = cfg["novelty"]["mapping_rules"]
        self.global_forbidden = cfg["safety_constraints"]["global_forbidden"]

    def get_max_level_for_archetype(self, archetype: str) -> int:
        rules = self.mapping_rules.get(archetype, self.mapping_rules["defaults"])
        return int(rules.get("max_level", 1))

    def get_temperature_bands(self) -> Dict[str, int]:
        return self.mapping_rules["temperature_thresholds"]


class CognitiveReasoningGovernor:
    def __init__(self, config_path: str = "crg_config.json"):
        self.cfg = CRGConfig(config_path)

    def compute_novelty_level(self, archetype: str, temperature: int, confidence: int) -> int:
        """
        Real-world, constraint-bound novelty:
        - Archetype caps the maximum.
        - Temperature and confidence modulate within that cap.
        """
        max_level = self.cfg.get_max_level_for_archetype(archetype)
        bands = self.cfg.get_temperature_bands()

        # Start conservative
        level = 0

        # Temperature / confidence gating (checked from highest to lowest)
        if temperature >= bands["high"] and confidence >= bands["high"]:
            level = min(3, max_level)
        elif temperature >= bands["medium"] and confidence >= bands["medium"]:
            level = min(2, max_level)
        elif temperature < bands["low"] or confidence < bands["low"]:
            level = 0
        else:
            level = min(1, max_level)  # Between low and medium thresholds

        # Ensure we never exceed archetype cap
        return min(level, max_level)

    def build_reasoning_block(self, signals: Dict[str, Any]) -> str:
        """
        signals: {
          "archetype": str,
          "temperature": int,
          "confidence": int
        }
        """
        archetype = signals.get("archetype") or "defaults"
        temperature = signals.get("temperature", 50)
        confidence = signals.get("confidence", 50)

        novelty_level = self.compute_novelty_level(archetype, temperature, confidence)
        level_cfg = self.cfg.novelty_levels[str(novelty_level)]

        allowed_reasoning = level_cfg["allowed_reasoning"]
        forbidden = self.cfg.global_forbidden

        lines = [
            "[REASONING GOVERNOR]",
            f"- Novelty Budget: {novelty_level}",
            "- Allowed Reasoning:"
        ]
        for item in allowed_reasoning:
            lines.append(f"  - {item}")
        lines.append("- Forbidden:")
        for item in forbidden:
            lines.append(f"  - {item}")
        lines.append("[/REASONING GOVERNOR]")

        return "\n".join(lines)
