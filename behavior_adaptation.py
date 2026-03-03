import json
import os
from typing import Dict, Any, List

class BehaviorProfile:
    def __init__(self, data: Dict[str, Any]):
        self.tone = data.get("tone", "professional")
        self.pacing = data.get("pacing", "normal")
        self.formality = data.get("formality", "neutral")
        self.assertiveness = data.get("assertiveness", "medium")
        self.rapport_level = data.get("rapport_level", "medium")
        self.pivot_style = data.get("pivot_style", "soft")
        self.closing_bias = data.get("closing_bias", "direct")
        self.compression_mode = data.get("compression_mode", False)
        self.expansion_mode = data.get("expansion_mode", False)

    def to_prompt_block(self) -> str:
        return (
            "[BEHAVIOR PROFILE]\n"
            f"- Tone: {self.tone}\n"
            f"- Pacing: {self.pacing}\n"
            f"- Formality: {self.formality}\n"
            f"- Assertiveness: {self.assertiveness}\n"
            f"- Rapport Level: {self.rapport_level}\n"
            f"- Pivot Style: {self.pivot_style}\n"
            f"- Closing Bias: {self.closing_bias}\n"
            f"- Compression Mode: {self.compression_mode}\n"
            f"- Expansion Mode: {self.expansion_mode}\n"
            "[/BEHAVIOR PROFILE]"
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tone": self.tone,
            "pacing": self.pacing,
            "formality": self.formality,
            "assertiveness": self.assertiveness,
            "rapport_level": self.rapport_level,
            "pivot_style": self.pivot_style,
            "closing_bias": self.closing_bias,
            "compression_mode": self.compression_mode,
            "expansion_mode": self.expansion_mode
        }

class BehaviorAdaptationEngine:
    def __init__(self, config_path: str = "behavior_adaptation_config.json"):
        if not os.path.exists(config_path):
            self.config = {"archetypes": {}, "defaults": {"behavior": {}}}
        else:
            with open(config_path, "r") as f:
                self.config = json.load(f)
        
        self.archetypes = self.config.get("archetypes", {})
        self.default_behavior = BehaviorProfile(self.config.get("defaults", {}).get("behavior", {}))

    def classify_archetype(self, signals: Dict[str, Any]) -> str:
        """
        signals: {
          "user_text": str,
          "trajectory": str,
          "merchant_type": str,
          "micro_patterns": List[str],
          "temperature": int,
          "confidence": int,
          "objection_weights": Dict[str, int]
        }
        """
        text = signals.get("user_text", "").lower()
        trajectory = signals.get("trajectory")
        merchant_type = signals.get("merchant_type")
        micro_patterns = signals.get("micro_patterns", [])
        temperature = signals.get("temperature", 50)
        confidence = signals.get("confidence", 50)
        objection_weights = signals.get("objection_weights", {})

        best_match = None
        best_score = 0

        for name, spec in self.archetypes.items():
            score = 0
            sig = spec.get("signals", {})

            # phrase hits — handle both single string and list formats
            phrase_val = sig.get("phrase", [])
            if isinstance(phrase_val, str):
                phrase_val = [phrase_val]
            for phrase in phrase_val:
                if phrase in text:
                    score += 2
            
            # handle phrases list correctly as per config
            for phrase in sig.get("phrases", []):
                if phrase in text:
                    score += 2

            # trajectory bias
            if trajectory in sig.get("trajectory_bias", []):
                score += 2

            # merchant type
            if merchant_type in sig.get("merchant_types", []):
                score += 3

            # micro patterns
            for mp in sig.get("micro_patterns", []):
                if mp in micro_patterns:
                    score += 2

            # temperature thresholds
            t_min = sig.get("temperature_min")
            t_max = sig.get("temperature_max")
            if t_min is not None and temperature >= t_min:
                score += 1
            if t_max is not None and temperature <= t_max:
                score += 1

            # confidence thresholds
            c_min = sig.get("confidence_min")
            if c_min is not None and confidence >= c_min:
                score += 1

            # objection weights
            tw_min = sig.get("time_objection_weight_min")
            if tw_min is not None and objection_weights.get("time", 0) >= tw_min:
                score += 2

            sw_min = sig.get("skepticism_objection_weight_min")
            if sw_min is not None and objection_weights.get("skepticism", 0) >= sw_min:
                score += 2

            if score > best_score:
                best_score = score
                best_match = name

        return best_match

    def get_behavior_profile(self, signals: Dict[str, Any]) -> BehaviorProfile:
        archetype = self.classify_archetype(signals)
        if archetype and archetype in self.archetypes:
            behavior_data = self.archetypes[archetype]["behavior"]
            return BehaviorProfile(behavior_data)
        return self.default_behavior
