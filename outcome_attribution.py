import json
from typing import Dict, Any
from datetime import datetime, timedelta


class OutcomeAttributionConfig:
    def __init__(self, path: str):
        with open(path, "r") as f:
            cfg = json.load(f)

        self.dimensions = cfg["dimensions"]
        self.review_policy = cfg["review_policy"]
        self.logging_enabled = cfg["logging"]["enabled"]
        self.log_file = cfg["logging"]["file"]


class OutcomeAttributionEngine:
    """
    Alan uses this to understand WHY an outcome occurred.
    Scores are deterministic, rule-based, and grounded in real call signals.
    """

    def __init__(self, config_path: str):
        self.cfg = OutcomeAttributionConfig(config_path)
        self.call_counter = 0
        self.last_review_time = datetime.utcnow()

    def _score_dimension(self, dim_name: str, context: Dict[str, Any]) -> float:
        rules = self.cfg.dimensions[dim_name]["weights"]
        score = 0.0

        for key, weight in rules.items():
            if context.get(key, False):
                score += weight

        # Normalize to 0–1
        return max(0.0, min(1.0, (score + 1) / 2))

    def attribute(self, call_context: Dict[str, Any]) -> Dict[str, float]:
        """
        call_context example:
        {
          "stable_archetype": bool,
          "archetype_flip": bool,
          "engagement_high": bool,
          "engagement_low": bool,
          "warming": bool,
          "stable": bool,
          "cooling": bool,
          "escalating": bool,
          "soft_to_positive": bool,
          "soft_to_neutral": bool,
          "hard_to_negative": bool,
          "ignored_objection": bool,
          "bias_match": bool,
          "bias_mismatch": bool,
          "high_novelty_positive": bool,
          "high_novelty_negative": bool,
          "low_novelty_positive": bool,
          "low_novelty_negative": bool
        }
        """

        attribution = {}

        for dim in self.cfg.dimensions.keys():
            attribution[dim] = self._score_dimension(dim, call_context)

        self._log(call_context, attribution)
        self.call_counter += 1

        return attribution

    def _log(self, call_context: Dict[str, Any], attribution: Dict[str, float]) -> None:
        if not self.cfg.logging_enabled:
            return

        record = {
            "ts": datetime.utcnow().isoformat(),
            "call_context": call_context,
            "attribution": attribution
        }

        with open(self.cfg.log_file, "a") as f:
            f.write(json.dumps(record) + "\n")

    def should_review(self) -> bool:
        """
        Alan reviews attribution logs periodically, not daily.
        This prevents over-adaptation and keeps evolution stable.
        """
        now = datetime.utcnow()

        if self.call_counter >= self.cfg.review_policy["review_interval_calls"]:
            self.call_counter = 0
            self.last_review_time = now
            return True

        if now - self.last_review_time >= timedelta(hours=self.cfg.review_policy["review_interval_hours"]):
            self.last_review_time = now
            return True

        return False
