"""
Bias Auditing System (BAS)
Alan's genetic hygiene - prevents drift and runaway traits
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
from collections import Counter

logger = logging.getLogger(__name__)


class BiasAuditingSystem:
    """
    Runs periodic audits to detect:
    - Trajectory skew
    - Closing bias over-dominance
    - Archetype overconfidence
    - Novelty instability/stagnation
    Sits outside Living Calibration Space and corrects evolution.
    """

    def __init__(self, db_path: str = "bas_audit_log.jsonl"):
        self.db_path = db_path
        self.logger = logging.getLogger("BAS")

    def run_daily_audit(self, stats: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Light daily audit"""
        violations = []

        violations += self._check_trajectory_distribution(stats.get("trajectory", {}))
        violations += self._check_closing_bias(stats.get("closing_bias", {}))
        violations += self._check_archetype_confidence(stats.get("archetype", []))
        violations += self._check_novelty_usage(stats.get("novelty", []))

        if violations:
            self._apply_corrections(violations)
            self._log_violations(violations)

        return violations

    def run_weekly_audit(self, stats: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Deep weekly audit with stricter thresholds"""
        # Similar to daily but with different thresholds
        return self.run_daily_audit(stats)

    def _check_trajectory_distribution(self, trajectory_stats: Dict[str, int]) -> List[Dict[str, Any]]:
        """Check if one trajectory dominates (>60%)"""
        violations = []
        total = sum(trajectory_stats.values())
        if total == 0:
            return violations

        for trajectory, count in trajectory_stats.items():
            ratio = count / total
            if ratio > 0.6:
                violations.append({
                    "type": "trajectory_skew",
                    "trajectory": trajectory,
                    "ratio": ratio,
                    "severity": "warning"
                })

        return violations

    def _check_closing_bias(self, bias_stats: Dict[str, int]) -> List[Dict[str, Any]]:
        """Check if one closing bias over-dominates (>50%)"""
        violations = []
        total = sum(bias_stats.values())
        if total == 0:
            return violations

        for bias, count in bias_stats.items():
            ratio = count / total
            if ratio > 0.5:
                violations.append({
                    "type": "closing_bias_skew",
                    "bias": bias,
                    "ratio": ratio,
                    "severity": "warning"
                })

        return violations

    def _check_archetype_confidence(self, archetype_history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Check for overconfidence or underfitting"""
        violations = []
        
        if len(archetype_history) < 10:
            return violations

        recent = archetype_history[-10:]
        avg_confidence = sum(a["confidence"] for a in recent) / len(recent)

        if avg_confidence > 0.85:
            violations.append({
                "type": "archetype_overconfidence",
                "avg_confidence": avg_confidence,
                "severity": "warning"
            })
        elif avg_confidence < 0.25:
            violations.append({
                "type": "archetype_underfitting",
                "avg_confidence": avg_confidence,
                "severity": "warning"
            })

        return violations

    def _check_novelty_usage(self, novelty_logs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Check for novelty instability or stagnation"""
        violations = []

        if len(novelty_logs) < 10:
            return violations

        recent = novelty_logs[-10:]
        avg_novelty = sum(n.get("level", 1) for n in recent) / len(recent)

        # Baseline is 1.0
        if avg_novelty > 1.5:
            violations.append({
                "type": "novelty_instability",
                "avg_novelty": avg_novelty,
                "severity": "warning"
            })
        elif avg_novelty < 0.5:
            violations.append({
                "type": "novelty_stagnation",
                "avg_novelty": avg_novelty,
                "severity": "info"
            })

        return violations

    def _apply_corrections(self, violations: List[Dict[str, Any]]):
        """Apply micro-nudges to correct drift"""
        for v in violations:
            if v["type"] == "trajectory_skew":
                self._rebalance_trajectory_weights(v["trajectory"])
            elif v["type"] == "closing_bias_skew":
                self._rebalance_closing_bias(v["bias"])
            elif v["type"] == "archetype_overconfidence":
                self._reduce_archetype_confidence()
            elif v["type"] == "novelty_instability":
                self._tighten_novelty_budget()
            elif v["type"] == "novelty_stagnation":
                self._loosen_novelty_budget()

    def _rebalance_trajectory_weights(self, dominant_trajectory: str):
        """Reduce weight of dominant trajectory"""
        self.logger.info(f"[BAS] Rebalancing trajectory weights (dominant: {dominant_trajectory})")
        # TODO: Implement actual rebalancing logic

    def _rebalance_closing_bias(self, dominant_bias: str):
        """Reduce weight of dominant closing bias"""
        self.logger.info(f"[BAS] Rebalancing closing bias (dominant: {dominant_bias})")
        # TODO: Implement actual rebalancing logic

    def _reduce_archetype_confidence(self):
        """Lower confidence caps"""
        self.logger.info("[BAS] Reducing archetype confidence caps")
        # TODO: Implement actual adjustment

    def _tighten_novelty_budget(self):
        """Reduce novelty allowance"""
        self.logger.info("[BAS] Tightening novelty budget")
        # TODO: Implement actual adjustment

    def _loosen_novelty_budget(self):
        """Increase novelty allowance"""
        self.logger.info("[BAS] Loosening novelty budget")
        # TODO: Implement actual adjustment

    def _log_violations(self, violations: List[Dict[str, Any]]):
        """Log violations for dashboard"""
        record = {
            "timestamp": datetime.utcnow().isoformat(),
            "violations": violations
        }

        try:
            with open(self.db_path, "a") as f:
                f.write(json.dumps(record) + "\n")
        except Exception as e:
            self.logger.error(f"Failed to log BAS violations: {e}")

    def should_pause_evolution(self, violations: List[Dict[str, Any]]) -> bool:
        """Determine if evolution should be paused"""
        critical = [v for v in violations if v.get("severity") == "critical"]
        return len(critical) > 0
