import json
import os
import logging
from datetime import datetime

class EvolutionEngine:
    """
    The Evolution Engine performs bounded micro-learning on Alan's performance weights.
    It takes an Outcome and an Engagement Score to produce 'nudges' in trajectory 
    weights and closing biases, ensuring Alan adapts without identity drift.
    """
    def __init__(self, config_path="evolution_config.json"):
        self.config_path = config_path
        self.config = self._load_config()
        self.logger = logging.getLogger("EvolutionEngine")

    def _load_config(self):
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading evolution config: {e}")
            return {}

    def calculate_nudge(self, outcome, engagement_score, current_weights):
        """
        Calculates weight adjustments based on call outcome and engagement metrics.
        
        outcome: One of ['statement_obtained', 'kept_engaged', 'soft_decline', 'hard_decline', 'hangup']
        engagement_score: 0.0 to 10.0 (float)
        current_weights: dict containing trajectory weights, closing biases, etc.
        """
        nudges = {
            "trajectory_nudges": {},
            "bias_nudges": {},
            "archetype_nudges": {}
        }

        is_positive = outcome in self.config.get("signals", {}).get("outcomes", {}).get("positive", [])
        is_negative = outcome in self.config.get("signals", {}).get("outcomes", {}).get("negative", [])

        # 1. Trajectory Weight Nudges
        traj_adjustments = self.config.get("adjustments", {}).get("trajectory_weights", {})
        for weight_key, adj in traj_adjustments.items():
            if is_positive:
                nudges["trajectory_nudges"][weight_key] = adj.get("on_positive", 0)
            elif is_negative:
                nudges["trajectory_nudges"][weight_key] = adj.get("on_negative", 0)

        # 2. Closing Bias Tendency Nudges
        bias_adjustments = self.config.get("adjustments", {}).get("closing_bias_tendencies", {})
        for bias_key, adj in bias_adjustments.items():
            if is_positive:
                nudges["bias_nudges"][bias_key] = adj.get("on_positive", 0)
            elif is_negative:
                nudges["bias_nudges"][bias_key] = adj.get("on_negative", 0)

        # 3. Log the nudge event
        self._log_evolution_event(outcome, engagement_score, nudges)

        return nudges

    def apply_bounded_nudges(self, current_state, nudges):
        """
        Applies nudges to current state while enforcing configuration bounds.
        Ensures no drift beyond specified limits (-5 to +5).
        """
        updated_state = current_state.copy()
        bounds = self.config.get("bounds", {})

        # Trajectory Weight Bounds
        min_v = bounds.get("trajectory_weight_min", -5)
        max_v = bounds.get("trajectory_weight_max", 5)
        for k, v in nudges.get("trajectory_nudges", {}).items():
            if k in updated_state.get("trajectories", {}):
                current_val = updated_state["trajectories"][k]
                updated_state["trajectories"][k] = max(min_v, min(max_v, current_val + v))

        # Bias Bounds
        min_b = bounds.get("closing_bias_min", -5)
        max_b = bounds.get("closing_bias_max", 5)
        for k, v in nudges.get("bias_nudges", {}).items():
            if k in updated_state.get("biases", {}):
                current_val = updated_state["biases"][k]
                updated_state["biases"][k] = max(min_b, min(max_b, current_val + v))

        return updated_state

    def apply_call_result_with_confidence(self, call_summary):
        """
        Calculates and applies nudges scaled by outcome confidence.
        """
        confidence = call_summary.get("outcome_confidence", 0.0)
        band = call_summary.get("outcome_confidence_band", "low")

        if band == "high":
            scale = 1.0
        elif band == "medium":
            scale = 0.5
        else:
            scale = 0.0

        if scale == 0.0:
            self._log_evolution_event(
                call_summary.get("outcome", "unknown"),
                call_summary.get("engagement_score", 0.0),
                {"status": "skipped_low_confidence"}
            )
            return None

        # Calculate base nudges
        outcome = call_summary.get("outcome")
        engagement_score = call_summary.get("engagement_score", 0.0)
        
        # We assume current state is managed elsewhere or passed in
        # For this integration, we just calculate the scaled nudges
        nudges = self.calculate_nudge(outcome, engagement_score, {})
        
        # Scale each nudge
        scaled_nudges = {
            "trajectory_nudges": {k: v * scale for k, v in nudges.get("trajectory_nudges", {}).items()},
            "bias_nudges": {k: v * scale for k, v in nudges.get("bias_nudges", {}).items()},
            "archetype_nudges": {k: v * scale for k, v in nudges.get("archetype_nudges", {}).items()}
        }
        
        return scaled_nudges

    def apply_coaching_nudges(self, coaching_report):
        """
        CW20 Step 5 — Evolution Nudge Engine.
        
        Translates per-call coaching flags into behavioral nudges that modify
        Alan's trajectory weights and closing biases. This is the bridge between
        "how Alan performed" (coaching) and "how Alan should evolve" (evolution).
        
        The existing evolution system operates on OUTCOMES (what happened).
        This method operates on BEHAVIOR (how Alan performed during the call).
        Both feed into the same bounded weight system.
        
        Args:
            coaching_report: dict from CoachingEngine.generate_call_report()
                - coaching_score: float 0.0-1.0
                - coaching_weaknesses: str (comma-separated flags with optional counts)
                - coaching_strengths: str (comma-separated flags)
                - coaching_action_item: str
                
        Returns:
            dict with behavioral_nudges applied, or None if no actionable data
        """
        if not coaching_report or coaching_report.get('coaching_score') is None:
            return None
        
        score = coaching_report['coaching_score']
        weaknesses = coaching_report.get('coaching_weaknesses', '')
        strengths = coaching_report.get('coaching_strengths', '')
        
        # Parse weakness flags and their counts: "mild_over_response(3x), high_latency" 
        weakness_flags = {}
        if weaknesses and weaknesses != 'none_detected':
            for part in weaknesses.split(','):
                part = part.strip()
                if '(' in part:
                    flag = part[:part.index('(')]
                    count_str = part[part.index('(')+1:part.index(')')]
                    try:
                        weakness_flags[flag] = int(count_str.replace('x', ''))
                    except ValueError:
                        weakness_flags[flag] = 1
                else:
                    weakness_flags[part] = 1
        
        strength_flags = set()
        if strengths and strengths != 'none_detected':
            for part in strengths.split(','):
                part = part.strip()
                if '(' in part:
                    strength_flags.add(part[:part.index('(')])
                else:
                    strength_flags.add(part)
        
        # ---- BEHAVIORAL NUDGE RULES ----
        # These modify trajectory weights and closing biases based on HOW Alan
        # talked, not just what happened. Bounded by the same -5 to +5 limits.
        
        behavioral_nudges = {
            "trajectory_nudges": {},
            "bias_nudges": {},
            "behavioral_flags": [],
            "coaching_score": score,
        }
        
        bounds = self.config.get("bounds", {})
        
        # Rule 1: Over-response pattern → cool down aggressiveness
        # If Alan talks too much, bias toward consultative (ask questions) instead of direct (pitch)
        over_response_count = weakness_flags.get('over_response', 0) + weakness_flags.get('mild_over_response', 0)
        if over_response_count >= 2:
            behavioral_nudges["bias_nudges"]["direct"] = -1
            behavioral_nudges["bias_nudges"]["consultative"] = 1
            behavioral_nudges["behavioral_flags"].append("over_talk_correction")
        
        # Rule 2: Latency issues → nudge toward warming (keep engagement while system lags)
        # High latency means Alan is slow to respond — focus on relationship building
        # which is more forgiving of pauses than direct selling
        latency_count = weakness_flags.get('high_latency', 0) + weakness_flags.get('elevated_latency', 0)
        if latency_count >= 2:
            behavioral_nudges["trajectory_nudges"]["warming"] = 1
            behavioral_nudges["behavioral_flags"].append("latency_warming_shift")
        
        # Rule 3: AI language detected → nudge toward relational (more human)
        if 'ai_language' in weakness_flags:
            behavioral_nudges["bias_nudges"]["relational"] = 1
            behavioral_nudges["bias_nudges"]["soft"] = 1
            behavioral_nudges["behavioral_flags"].append("humanization_nudge")
        
        # Rule 4: Dead-end responses → nudge toward consultative (ask questions)
        if 'dead_end_response' in weakness_flags:
            behavioral_nudges["bias_nudges"]["consultative"] = 1
            behavioral_nudges["trajectory_nudges"]["stalling"] = -1
            behavioral_nudges["behavioral_flags"].append("dead_end_recovery")
        
        # Rule 5: No acknowledgment → nudge toward relational (listen more)
        if 'no_acknowledgment' in weakness_flags:
            behavioral_nudges["bias_nudges"]["relational"] = 1
            behavioral_nudges["behavioral_flags"].append("active_listening_nudge")
        
        # Rule 6: Under-response → nudge toward direct (give fuller answers)
        if 'under_response' in weakness_flags:
            behavioral_nudges["bias_nudges"]["direct"] = 1
            behavioral_nudges["behavioral_flags"].append("fuller_response_nudge")
        
        # ---- POSITIVE REINFORCEMENT ----
        
        # Rule 7: Good questions → reinforce consultative approach
        if 'good_question' in strength_flags:
            behavioral_nudges["bias_nudges"]["consultative"] = \
                behavioral_nudges["bias_nudges"].get("consultative", 0) + 1
            behavioral_nudges["behavioral_flags"].append("question_quality_reinforced")
        
        # Rule 8: High overall score → reinforce current trajectory
        if score >= 0.90:
            behavioral_nudges["trajectory_nudges"]["warming"] = \
                behavioral_nudges["trajectory_nudges"].get("warming", 0) + 1
            behavioral_nudges["behavioral_flags"].append("high_performance_reinforced")
        
        # Scale all nudges by coaching score (higher score = smaller corrections needed)
        # A 0.50 score means bigger corrections; a 0.95 score means minimal corrections
        # Invert: correction_weight = 1.0 - score (range 0.0 to 1.0)
        correction_weight = max(0.1, 1.0 - score)  # Floor at 0.1 to avoid zero-out
        
        for key in behavioral_nudges["trajectory_nudges"]:
            behavioral_nudges["trajectory_nudges"][key] = round(
                behavioral_nudges["trajectory_nudges"][key] * correction_weight, 2
            )
        for key in behavioral_nudges["bias_nudges"]:
            behavioral_nudges["bias_nudges"][key] = round(
                behavioral_nudges["bias_nudges"][key] * correction_weight, 2
            )
        
        # Log the behavioral evolution event
        self._log_evolution_event(
            "coaching_nudge",
            score,
            behavioral_nudges
        )
        
        self.logger.info(
            f"[EVOLUTION] Coaching nudge applied: score={score:.3f}, "
            f"flags={behavioral_nudges['behavioral_flags']}, "
            f"trajectory_nudges={behavioral_nudges['trajectory_nudges']}, "
            f"bias_nudges={behavioral_nudges['bias_nudges']}"
        )
        
        return behavioral_nudges

    def _log_evolution_event(self, outcome, engagement_score, nudges):
        log_file = self.config.get("logging", {}).get("file", "evolution_log.jsonl")
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "outcome": outcome,
            "engagement_score": engagement_score,
            "nudges": nudges
        }
        try:
            with open(log_file, "a") as f:
                f.write(json.dumps(log_entry) + "\n")
        except Exception as e:
            self.logger.error(f"Failed to log evolution event: {e}")

if __name__ == "__main__":
    # Test Evolution Engine logic
    ee = EvolutionEngine()
    current_state = {
        "trajectories": {"warming": 2, "cooling": 1, "stalling": 0, "escalating": -1},
        "biases": {"direct": 1, "consultative": 0, "relational": 2, "soft": -1}
    }
    
    # Simulate a Hard Decline (Negative Outcome)
    nudges = ee.calculate_nudge("hard_decline", 2.5, current_state)
    new_state = ee.apply_bounded_nudges(current_state, nudges)
    
    print("Evolution Nudges for Hard Decline:")
    print(json.dumps(nudges, indent=2))
    print("\nUpdated Bounded State:")
    print(json.dumps(new_state, indent=2))
