# campaign_optimization_engine.py

import math


class CampaignOptimizationEngine:
    """
    Consumes the behavioral audit summary and produces:
    - pattern analysis
    - threshold recommendations
    - Fluidic Kernel tuning hints
    - classifier / STT / TTS flags
    - next campaign readiness score
    """

    def __init__(self, cfg: dict | None = None):
        self.cfg = cfg or {
            "stall_rate_warn": 0.10,
            "collapse_rate_warn": 0.05,
            "high_friction_rate_warn": 0.15,
            "hard_kill_rate_warn": 0.03,
            "soft_kill_rate_warn": 0.08,
        }

    def analyze(self, summary: dict) -> dict:
        total = max(summary.get("total", 0), 1)
        # Handle case where summary keys might be slightly different or missing
        stalled = summary.get("stalled", 0)
        collapsed = summary.get("collapsed", 0)
        high_friction = summary.get("high_friction", 0)
        recovering = summary.get("recovering", 0)
        actions = summary.get("governor_actions", {})

        stall_rate = stalled / total
        collapse_rate = collapsed / total
        friction_rate = high_friction / total
        hard_kill_rate = actions.get("hard_kill", 0) / total
        soft_kill_rate = actions.get("soft_kill", 0) / total

        recs = {
            "thresholds": [],
            "fluidic_kernel": [],
            "classifier": [],
            "stt_tts": [],
        }

        # 1) Threshold adjustments (behavioral)
        if stall_rate > self.cfg["stall_rate_warn"]:
            recs["thresholds"].append(
                f"High stall rate ({stall_rate:.1%}): consider lowering stall_turn_threshold or increasing recovery nudges in DISCOVERY."
            )
        if collapse_rate > self.cfg["collapse_rate_warn"]:
            recs["thresholds"].append(
                f"High collapse rate ({collapse_rate:.1%}): consider tightening collapse_drift_threshold or adding earlier soft exits in CLOSING/NEGOTIATION."
            )
        if friction_rate > self.cfg["high_friction_rate_warn"]:
            recs["thresholds"].append(
                f"High friction rate ({friction_rate:.1%}): consider lowering high_viscosity_threshold or softening objection handling prompts."
            )

        # 2) Fluidic Kernel tuning
        if stalled > 0:
            recs["fluidic_kernel"].append(
                "Stalls detected: reduce DISCOVERY viscosity slightly or increase OPENING→DISCOVERY velocity to avoid interrogation loops."
            )
        if collapsed > 0:
            recs["fluidic_kernel"].append(
                "Collapses detected: increase NEGOTIATION inertia or add a 'soft landing' branch when drift turns strongly negative."
            )
        if recovering > 0:
            recs["fluidic_kernel"].append(
                "Recoveries present: consider reinforcing successful recovery patterns as templates for future prompts."
            )

        # 3) Classifier / IVR / voicemail hints
        if actions.get("hard_kill", 0) > 0 and collapsed > 0:
            recs["classifier"].append(
                "Some HARD_KILLs follow behavioral collapse: review those calls for misclassified IVR/voicemail or late detection."
            )

        # 4) STT/TTS vendor flags (using perception patterns from worst calls)
        worst_calls = summary.get("worst_calls", [])
        dead_air_like = [c for c in worst_calls if c.get("mode") == "stalled" and float(c.get("velocity", 0)) <= 0.01]
        if dead_air_like:
            recs["stt_tts"].append(
                "Stall patterns with near-zero velocity: check STT stability (dead air, missed 'hello') and consider model fallback."
            )

        # 5) Readiness score (0–100)
        readiness = self._compute_readiness(
            stall_rate=stall_rate,
            collapse_rate=collapse_rate,
            friction_rate=friction_rate,
            hard_kill_rate=hard_kill_rate,
            soft_kill_rate=soft_kill_rate,
        )

        return {
            "stall_rate": stall_rate,
            "collapse_rate": collapse_rate,
            "friction_rate": friction_rate,
            "hard_kill_rate": hard_kill_rate,
            "soft_kill_rate": soft_kill_rate,
            "recommendations": recs,
            "readiness_score": readiness,
        }

    def _compute_readiness(
        self,
        *,
        stall_rate: float,
        collapse_rate: float,
        friction_rate: float,
        hard_kill_rate: float,
        soft_kill_rate: float,
    ) -> int:
        # Start from 100 and subtract penalties
        score = 100.0

        score -= stall_rate * 40.0
        score -= collapse_rate * 50.0
        score -= friction_rate * 25.0
        score -= hard_kill_rate * 60.0
        score -= soft_kill_rate * 30.0

        score = max(0.0, min(100.0, score))
        return int(round(score))
