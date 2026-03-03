import json
import os
import re

class OutcomeDetectionLayer:
    """
    Analyzes call metadata, transcript patterns, and signals (TPS, RLS, ULS, TDS, OSS)
    to determine the deterministic outcome of a call and its Engagement Score.
    """
    def __init__(self, config_path="outcome_detection_config.json"):
        self.config_path = config_path
        self.config = self._load_config()

    def _load_config(self):
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading outcome detection config: {e}")
            return {}

    def calculate_engagement_score(self, signals):
        """
        signals: dict with {TPS, RLS, ULS, TDS, OSS} as binary (0 or 1).
        Formula: (TPS*0.2) + (RLS*0.3) + (ULS*0.2) + (TDS*0.2) + (OSS*0.1) * 10
        """
        weights = self.config.get("engagement_score_weights", {})
        score = 0.0
        for signal, weight in weights.items():
            score += signals.get(signal, 0) * weight
        
        return round(score * 10, 2)

    def detect_outcome(self, transcript, metadata, signals):
        """
        Legacy wrapper for detect_with_match_stats.
        """
        outcome, _, _ = self.detect_with_match_stats(transcript, metadata, signals)
        return outcome

    def detect_with_match_stats(self, transcript, metadata, signals):
        """
        Determines outcome based on keywords in transcript and signal patterns.
        Returns (outcome, matched_conditions, total_conditions).
        """
        norm_transcript = transcript.lower()
        outcomes = self.config.get("outcome_indicators", {})
        
        matched_conditions = 0
        total_conditions = 0

        # 1. Check for 'statement_obtained'
        stmt_info = outcomes.get("statement_obtained", {})
        total_conditions += 1
        found_stmt = False
        if any(kw in norm_transcript for kw in stmt_info.get("keywords", [])):
            if signals.get("ULS") == 1: # User Level Submission signal
                matched_conditions += 1
                return "statement_obtained", matched_conditions, total_conditions

        # 2. Check for 'hard_decline'
        hard_info = outcomes.get("hard_decline", {})
        total_conditions += 1
        if any(kw in norm_transcript for kw in hard_info.get("keywords", [])):
            matched_conditions += 1
            return "hard_decline", matched_conditions, total_conditions

        # 3. Check for 'soft_decline'
        soft_info = outcomes.get("soft_decline", {})
        total_conditions += 1
        if any(kw in norm_transcript for kw in soft_info.get("keywords", [])):
            matched_conditions += 1
            return "soft_decline", matched_conditions, total_conditions

        # 4. Check for 'kept_engaged' (Duration based or interest)
        engaged_info = outcomes.get("kept_engaged", {})
        total_conditions += 1
        if metadata.get("duration", 0) > engaged_info.get("threshold_duration", 120):
            matched_conditions += 1
            return "kept_engaged", matched_conditions, total_conditions
        
        total_conditions += 1
        if any(kw in norm_transcript for kw in engaged_info.get("keywords", [])):
            matched_conditions += 1
            return "kept_engaged", matched_conditions, total_conditions

        # 5. Fallback/Default
        total_conditions += 1
        if metadata.get("disconnected_by") == "user" and metadata.get("duration", 0) < 30:
            matched_conditions += 1
            return "hangup", matched_conditions, total_conditions
            
        return "soft_decline", matched_conditions, total_conditions # Default moderate outcome

if __name__ == "__main__":
    # Test ODL logic
    odl = OutcomeDetectionLayer()
    
    test_transcript = "I'm not really interested, stop calling me."
    test_signals = {"TPS": 1, "RLS": 0, "ULS": 0, "TDS": 0, "OSS": 0}
    test_metadata = {"duration": 15, "disconnected_by": "user"}
    
    outcome, matched, total = odl.detect_with_match_stats(test_transcript, test_metadata, test_signals)
    score = odl.calculate_engagement_score(test_signals)
    
    print(f"Detected Outcome: {outcome} ({matched}/{total} conditions)")
    print(f"Engagement Score: {score}/10.0")
