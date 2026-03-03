"""
AQI Phase 5 — Aggregation Dashboard
=====================================
Aggregates behavioral intelligence across many calls.
Produces tag frequencies, behavioral tendencies, and continuum heatmaps.

This is the cross-call intelligence engine of the AQI 0.1mm Chip ecosystem.
"""

from collections import Counter


class Phase5Dashboard:
    """Cross-call behavioral intelligence aggregation."""

    def __init__(self):
        self.call_profiles = []

    def add_call_profile(self, profile: dict):
        """Add a single call's Phase 5 profile (output of Phase5CallAnalyzer)."""
        self.call_profiles.append(profile)

    @property
    def total_calls(self) -> int:
        return len(self.call_profiles)

    def aggregate(self) -> dict:
        """
        Produce cross-call intelligence snapshot.

        Returns
        -------
        dict with keys:
            total_calls, tag_counts, tendencies, heatmaps,
            signal_distributions, outcome_distribution
        """
        if not self.call_profiles:
            return {
                "total_calls": 0,
                "tag_counts": {},
                "tendencies": {},
                "heatmaps": {},
                "signal_distributions": {},
                "outcome_distribution": {},
            }

        tag_counts = self._count_tags()
        tendencies = self._derive_tendencies(tag_counts)
        heatmaps = self._build_heatmaps()
        signal_dist = self._signal_distributions()
        outcome_dist = self._outcome_distribution()

        return {
            "total_calls": self.total_calls,
            "tag_counts": dict(tag_counts),
            "tendencies": tendencies,
            "heatmaps": heatmaps,
            "signal_distributions": signal_dist,
            "outcome_distribution": outcome_dist,
        }

    # ─────────────────────────────────────────────────────────
    # TAG COUNTING
    # ─────────────────────────────────────────────────────────

    def _count_tags(self) -> Counter:
        all_tags = []
        for p in self.call_profiles:
            all_tags.extend(p.get("tags", []))
        return Counter(all_tags)

    # ─────────────────────────────────────────────────────────
    # TENDENCY DERIVATION
    # ─────────────────────────────────────────────────────────

    def _derive_tendencies(self, tag_counts: Counter) -> dict:
        return {
            "persistence_bias": self._persistence_bias(tag_counts),
            "caution_bias": self._caution_bias(tag_counts),
            "close_timing_bias": self._close_timing_bias(tag_counts),
            "objection_handling_bias": self._objection_bias(tag_counts),
            "personality_stability": self._personality_stability(tag_counts),
        }

    def _persistence_bias(self, tc: Counter) -> str:
        over = tc.get("OverPersistence", 0)
        under = tc.get("UnderPersistence", 0)
        healthy = tc.get("HealthyPersistence", 0)

        if over > healthy and over > under:
            return "over-persistent"
        elif under > healthy and under > over:
            return "under-persistent"
        else:
            return "balanced"

    def _caution_bias(self, tc: Counter) -> str:
        balanced = tc.get("BalancedCaution", 0)
        premature = tc.get("PrematureWithdrawal", 0)

        if premature > balanced:
            return "over-cautious"
        else:
            return "balanced"

    def _close_timing_bias(self, tc: Counter) -> str:
        strong = tc.get("StrongCloseTiming", 0)
        late = tc.get("LateCloseAttempt", 0)

        if late > strong:
            return "late"
        elif strong > late:
            return "optimal"
        else:
            return "neutral"

    def _objection_bias(self, tc: Counter) -> str:
        effective = tc.get("EffectiveObjectionHandling", 0)
        shallow = tc.get("ShallowObjectionHandling", 0)

        if shallow > effective:
            return "shallow"
        elif effective > shallow:
            return "effective"
        else:
            return "neutral"

    def _personality_stability(self, tc: Counter) -> str:
        stable = tc.get("StablePersonalityModulation", 0)
        mismatch = tc.get("PersonalityMismatch", 0)

        if mismatch > stable:
            return "unstable"
        elif stable > mismatch:
            return "stable"
        else:
            return "neutral"

    # ─────────────────────────────────────────────────────────
    # HEATMAPS (frequency distributions across Continuum axes)
    # ─────────────────────────────────────────────────────────

    def _build_heatmaps(self) -> dict:
        return {
            "state_axis": self._state_heatmap(),
            "health_axis": self._health_heatmap(),
            "mission_axis": self._mission_heatmap(),
        }

    def _state_heatmap(self) -> dict:
        """Total turn-dwell per FSM state across all calls."""
        state_counts = {}
        for p in self.call_profiles:
            dwell = (p.get("continuum", {})
                      .get("state_axis", {})
                      .get("state_dwell", {}))
            for state, count in dwell.items():
                state_counts[state] = state_counts.get(state, 0) + count
        return state_counts

    def _health_heatmap(self) -> dict:
        """Turn-count per organism health level across all calls."""
        level_counts = {1: 0, 2: 0, 3: 0, 4: 0}
        for p in self.call_profiles:
            trajectory = (p.get("continuum", {})
                           .get("health_axis", {})
                           .get("health_trajectory", []))
            for level in trajectory:
                if level in level_counts:
                    level_counts[level] += 1
        return level_counts

    def _mission_heatmap(self) -> dict:
        """Exit reason distribution across all calls."""
        outcome_counts = {}
        for p in self.call_profiles:
            reason = (p.get("continuum", {})
                       .get("mission_axis", {})
                       .get("exit_reason", "unknown"))
            outcome_counts[reason] = outcome_counts.get(reason, 0) + 1
        return outcome_counts

    # ─────────────────────────────────────────────────────────
    # SIGNAL DISTRIBUTIONS
    # ─────────────────────────────────────────────────────────

    def _signal_distributions(self) -> dict:
        """Distribution of each behavioral signal value across calls."""
        signal_keys = [
            "persistence", "caution", "escalation_timing",
            "objection_depth", "withdrawal_behavior", "personality_modulation",
        ]
        distributions = {}
        for key in signal_keys:
            counter = Counter()
            for p in self.call_profiles:
                val = p.get("signals", {}).get(key, "unknown")
                counter[val] += 1
            distributions[key] = dict(counter)
        return distributions

    def _outcome_distribution(self) -> dict:
        """Simple appointment_set vs others."""
        appt = sum(
            1 for p in self.call_profiles
            if (p.get("continuum", {})
                 .get("mission_axis", {})
                 .get("appointment_set", False))
        )
        return {
            "appointment_set": appt,
            "other": self.total_calls - appt,
            "conversion_rate": round(appt / max(self.total_calls, 1), 4),
        }

    # ─────────────────────────────────────────────────────────
    # ROLLING WINDOW
    # ─────────────────────────────────────────────────────────

    def get_rolling_aggregate(self, window: int = 50) -> dict:
        """Aggregate only the last N call profiles."""
        saved = self.call_profiles
        self.call_profiles = saved[-window:]
        result = self.aggregate()
        self.call_profiles = saved
        return result
