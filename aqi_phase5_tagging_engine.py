"""
AQI Phase 5 — Tagging Engine
==============================
Applies the Phase 5 behavioral vocabulary to a call's signals and continuum.
6 positive tags. 6 warning tags. All grounded in the Continuum Map.

Part of the AQI 0.1mm Chip ecosystem.
"""


class TaggingEngine:
    """Classifies a single call's behavior using the Phase 5 vocabulary."""

    # ── Positive Tags ──────────────────────────────────────────
    POSITIVE_TAGS = [
        "StrongCloseTiming",
        "HealthyPersistence",
        "AdaptiveWithdrawal",
        "BalancedCaution",
        "EffectiveObjectionHandling",
        "StablePersonalityModulation",
    ]

    # ── Warning Tags ──────────────────────────────────────────
    WARNING_TAGS = [
        "OverPersistence",
        "UnderPersistence",
        "PrematureWithdrawal",
        "LateCloseAttempt",
        "ShallowObjectionHandling",
        "PersonalityMismatch",
    ]

    def tag(self, signals: dict, continuum: dict) -> list:
        """
        Apply behavioral tags based on extracted signals and continuum mapping.

        Parameters
        ----------
        signals : dict
            Keys: persistence, caution, escalation_timing, objection_depth,
                  withdrawal_behavior, personality_modulation
        continuum : dict
            Keys: time_axis, state_axis, health_axis, mission_axis, identity_axis

        Returns
        -------
        list[str]  — ordered list of tags that apply to this call
        """
        tags = []

        # ── Positive tags ─────────────────────────────────────
        if signals.get("escalation_timing") == "optimal":
            tags.append("StrongCloseTiming")

        if signals.get("persistence") == "healthy":
            tags.append("HealthyPersistence")

        if signals.get("withdrawal_behavior") in ("adaptive", "graceful"):
            tags.append("AdaptiveWithdrawal")

        if signals.get("caution") == "balanced":
            tags.append("BalancedCaution")

        if signals.get("objection_depth") in ("sufficient", "deep"):
            tags.append("EffectiveObjectionHandling")

        if signals.get("personality_modulation") == "stable":
            tags.append("StablePersonalityModulation")

        # ── Warning tags ──────────────────────────────────────
        if signals.get("persistence") == "excessive":
            tags.append("OverPersistence")

        if signals.get("persistence") == "weak":
            tags.append("UnderPersistence")

        if signals.get("withdrawal_behavior") == "premature":
            tags.append("PrematureWithdrawal")

        if signals.get("escalation_timing") == "late":
            tags.append("LateCloseAttempt")

        if signals.get("objection_depth") == "shallow":
            tags.append("ShallowObjectionHandling")

        if signals.get("personality_modulation") == "unstable":
            tags.append("PersonalityMismatch")

        # ── Continuum-derived bonus tags ──────────────────────
        state_axis = continuum.get("state_axis", {})
        health_axis = continuum.get("health_axis", {})
        mission_axis = continuum.get("mission_axis", {})

        # OPTIMAL_PRESSURE: healthy persistence + appointment + no fatal
        if (signals.get("persistence") == "healthy"
                and mission_axis.get("appointment_set")):
            if "StrongCloseTiming" not in tags:
                tags.append("StrongCloseTiming")

        # HEALTH_ADAPTIVE: withdrew or simplified when health degraded
        if (health_axis.get("peak_degradation", 1) >= 3
                and signals.get("withdrawal_behavior") in ("adaptive", "graceful")):
            if "AdaptiveWithdrawal" not in tags:
                tags.append("AdaptiveWithdrawal")

        # FAST_FUNNEL: reached CLOSE in ≤ 6 turns
        first_close = continuum.get("time_axis", {}).get("first_close_turn")
        if first_close is not None and first_close <= 5:
            tags.append("FastFunnel")

        # OVER_PERSISTENT_COMPOUND: >3 backtracks
        if state_axis.get("backtracks", 0) > 3:
            if "OverPersistence" not in tags:
                tags.append("OverPersistence")

        return tags

    @staticmethod
    def is_positive(tag: str) -> bool:
        return tag in TaggingEngine.POSITIVE_TAGS or tag == "FastFunnel"

    @staticmethod
    def is_warning(tag: str) -> bool:
        return tag in TaggingEngine.WARNING_TAGS

    def split_tags(self, tags: list) -> dict:
        """Split tags into positive and warning buckets."""
        return {
            "positive": [t for t in tags if self.is_positive(t)],
            "warning": [t for t in tags if self.is_warning(t)],
        }
