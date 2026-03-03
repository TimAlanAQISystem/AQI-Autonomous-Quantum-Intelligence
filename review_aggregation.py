import json
from typing import Dict, Any, List
from datetime import datetime, timedelta
from statistics import mean, pstdev


class ReviewAggregationConfig:
    def __init__(self, path: str):
        with open(path, "r") as f:
            cfg = json.load(f)

        self.layers = cfg["layers"]
        self.influence = cfg["influence"]
        self.trend_threshold = cfg["trend_threshold"]
        self.lt_promotion = cfg["long_term_promotion"]
        self.agg_policy = cfg["aggregation_policy"]
        self.dimensions = cfg["dimensions"]
        self.logging_enabled = cfg["logging"]["enabled"]
        self.log_file = cfg["logging"]["file"]


class ReviewAggregationEngine:
    """
    Aggregates multiple periodic review summaries into
    short-, mid-, and long-term trends for Alan.
    """

    def __init__(self, config_path: str):
        with open(config_path, "r") as f:
            cfg = json.load(f)

        self.layers = cfg["layers"]
        self.influence = cfg["influence"]
        self.trend_threshold = cfg["trend_threshold"]
        self.lt_promotion = cfg["long_term_promotion"]
        self.agg_policy = cfg["aggregation_policy"]
        self.dimensions = cfg["dimensions"]
        self.logging_enabled = cfg["logging"]["enabled"]
        self.log_file = cfg["logging"]["file"]

        self.review_history: List[Dict[str, Any]] = []
        self.long_term_patterns: Dict[str, Dict[str, Any]] = {}
        self.last_aggregation_time = datetime.utcnow()

    def add_review_summary(self, summary: Dict[str, Any]) -> None:
        """
        summary example:
        {
          "ts": str,
          "dimension_averages": {
            "archetype_fit": float,
            "trajectory_management": float,
            "objection_handling_quality": float,
            "closing_bias_appropriateness": float,
            "novelty_appropriateness": float
          },
          "avg_confidence": float
        }
        """
        self.review_history.append(summary)

    def _get_window(self, window_size: int) -> List[Dict[str, Any]]:
        return self.review_history[-window_size:] if len(self.review_history) >= window_size else self.review_history[:]

    def _compute_dim_stats(self, reviews: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
        stats = {}
        if not reviews:
            for d in self.dimensions:
                stats[d] = {"avg": 0.0, "var": 0.0}
            return stats

        for d in self.dimensions:
            vals = [r["dimension_averages"].get(d, 0.0) for r in reviews]
            if len(vals) == 1:
                stats[d] = {"avg": vals[0], "var": 0.0}
            else:
                stats[d] = {"avg": mean(vals), "var": pstdev(vals) ** 2}
        return stats

    def _detect_trend(self, prev_avg: float, curr_avg: float) -> str:
        delta = curr_avg - prev_avg
        if delta > self.trend_threshold:
            return "improving"
        if delta < -self.trend_threshold:
            return "declining"
        return "stable"

    def _update_long_term_patterns(self) -> None:
        if len(self.review_history) < self.layers["long_term_window"]:
            return

        window = self._get_window(self.layers["long_term_window"])
        stats = self._compute_dim_stats(window)

        for d in self.dimensions:
            vals = [r["dimension_averages"].get(d, 0.0) for r in window]
            occurrences = sum(1 for v in vals if v >= self.lt_promotion["min_confidence"])
            var = stats[d]["var"]

            if occurrences >= self.lt_promotion["min_occurrences"] and var <= self.lt_promotion["max_variance"]:
                self.long_term_patterns[d] = {
                    "avg": stats[d]["avg"],
                    "var": var,
                    "occurrences": occurrences,
                    "last_updated": datetime.utcnow().isoformat()
                }

    def should_aggregate(self) -> bool:
        now = datetime.utcnow()
        if len(self.review_history) >= self.agg_policy["min_reviews_for_aggregation"]:
            return True
        if now - self.last_aggregation_time >= timedelta(hours=self.agg_policy["max_hours_between_aggregations"]):
            return True
        return False

    def aggregate(self) -> Dict[str, Any]:
        """
        Returns aggregated trends and final dimension guidance.
        """
        if not self.review_history:
            return {
                "final_dimension_guidance": {d: 0.0 for d in self.dimensions},
                "short_term": {},
                "mid_term": {},
                "long_term": {},
                "trends": {}
            }

        # Short-term: last 1 review
        st_window = self._get_window(self.layers["short_term_window"])
        st_stats = self._compute_dim_stats(st_window)

        # Mid-term: last 5 reviews
        mt_window = self._get_window(self.layers["mid_term_window"])
        mt_stats = self._compute_dim_stats(mt_window)

        # Long-term: from promoted patterns
        self._update_long_term_patterns()
        lt_stats = {}
        for d in self.dimensions:
            if d in self.long_term_patterns:
                lt_stats[d] = {"avg": self.long_term_patterns[d]["avg"], "var": self.long_term_patterns[d]["var"]}
            else:
                lt_stats[d] = {"avg": mt_stats[d]["avg"], "var": mt_stats[d]["var"]}

        # Trends: compare mid-term vs short-term
        trends = {}
        for d in self.dimensions:
            trends[d] = self._detect_trend(mt_stats[d]["avg"], st_stats[d]["avg"])

        # Final guidance: weighted combination
        final_guidance = {}
        for d in self.dimensions:
            st = st_stats[d]["avg"]
            mt = mt_stats[d]["avg"]
            lt = lt_stats[d]["avg"]
            final_guidance[d] = (
                self.influence["short_term"] * st +
                self.influence["mid_term"] * mt +
                self.influence["long_term"] * lt
            )

        result = {
            "ts": datetime.utcnow().isoformat(),
            "short_term": st_stats,
            "mid_term": mt_stats,
            "long_term": lt_stats,
            "trends": trends,
            "final_dimension_guidance": final_guidance
        }

        self._log(result)
        self.last_aggregation_time = datetime.utcnow()
        return result

    def _log(self, aggregation_result: Dict[str, Any]) -> None:
        if not self.logging_enabled:
            return
        with open(self.log_file, "a") as f:
            f.write(json.dumps(aggregation_result) + "\n")
