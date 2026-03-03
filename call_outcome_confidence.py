import json
from typing import Dict, Any


class CallOutcomeConfidenceConfig:
    def __init__(self, path: str):
        with open(path, "r") as f:
            cfg = json.load(f)

        self.weights = cfg["weights"]
        self.thresholds = cfg["thresholds"]
        self.oc_mapping = cfg["objection_clarity_mapping"]


class CallOutcomeConfidenceScorer:
    """
    Confidence scoring is fully real-world and stack-aware:
    - Uses ODL rule match strength
    - Uses Alan's engagement score (0–10)
    - Uses trajectory stability from BAL / Master Closer
    - Uses objection clarity from objection weighting
    - Uses hangup as an absolute signal
    """

    def __init__(self, config_path: str):
        self.cfg = CallOutcomeConfidenceConfig(config_path)

    def _normalize_engagement(self, engagement_score: float) -> float:
        # Engagement is 0–10; normalize to 0–1
        return max(0.0, min(1.0, engagement_score / 10.0))

    def _trajectory_certainty(self, trajectory_switches: int, turns: int) -> float:
        if turns <= 0:
            return 0.0
        # Fewer switches across more turns = higher certainty
        value = 1.0 - (trajectory_switches / max(1, turns))
        return max(0.0, min(1.0, value))

    def _objection_clarity_score(self, objection_type: str) -> float:
        # objection_type: "hard", "soft", "mixed", "none"
        return float(self.cfg.oc_mapping.get(objection_type, 0.0))

    def _hangup_certainty(self, hangup: bool) -> float:
        return 1.0 if hangup else 0.0

    def score(self, context: Dict[str, Any]) -> float:
        """
        context example:
        {
          "rule_matched_conditions": int,
          "rule_total_conditions": int,
          "engagement_score": float,          # 0–10 from Alan's engagement engine
          "trajectory_switches": int,         # from BAL / trajectory engine
          "turn_count": int,
          "objection_type": str,              # "hard", "soft", "mixed", "none"
          "hangup": bool
        }
        """

        w = self.cfg.weights

        # Rule Match Strength (RMS)
        matched = context.get("rule_matched_conditions", 0)
        total = max(1, context.get("rule_total_conditions", 1))
        rms = max(0.0, min(1.0, matched / total))

        # Engagement Score (normalized)
        es_norm = self._normalize_engagement(context.get("engagement_score", 0.0))

        # Trajectory Certainty (TC)
        tc = self._trajectory_certainty(
            context.get("trajectory_switches", 0),
            context.get("turn_count", 0)
        )

        # Objection Clarity Score (OCS)
        ocs = self._objection_clarity_score(context.get("objection_type", "none"))

        # Hangup Certainty (HCS)
        hcs = self._hangup_certainty(context.get("hangup", False))

        confidence = (
            w["rule_match_strength"] * rms +
            w["engagement_score"] * es_norm +
            w["trajectory_certainty"] * tc +
            w["objection_clarity"] * ocs +
            w["hangup_certainty"] * hcs
        )

        return max(0.0, min(1.0, confidence))

    def classify_band(self, confidence: float) -> str:
        if confidence >= self.cfg.thresholds["high_confidence"]:
            return "high"
        if confidence >= self.cfg.thresholds["medium_confidence"]:
            return "medium"
        return "low"
