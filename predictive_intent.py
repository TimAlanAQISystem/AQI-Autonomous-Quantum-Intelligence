import json
import re
import logging

logger = logging.getLogger(__name__)

class Prediction:
    def __init__(self, intent_name, objection_type, confidence):
        self.intent_name = intent_name
        self.objection_type = objection_type
        self.confidence = confidence

class PredictiveIntentEngine:
    def __init__(self, config_path="predictive_intent_model.json"):
        try:
            with open(config_path, "r") as f:
                self.config = json.load(f)
            logger.info(f"[PREDICTIVE] Config loaded from {config_path}")
        except Exception as e:
            logger.error(f"[PREDICTIVE] Failed to load config: {e}")
            self.config = {"intents": {}, "thresholds": {"min_confidence": 0.55}}
        
        # CCNM calibration weights: objection_type → frequency weight (0.0 – 1.0)
        # When set, these boost the score of intents whose default_objection_type
        # matches the more commonly observed objection types from past calls.
        # This makes the engine more likely to predict objections that actually
        # appear in practice, rather than treating all types equally.
        self._ccnm_calibration = {}

    def set_calibration(self, calibration: dict):
        """
        Apply CCNM-learned objection frequency calibration.
        
        Args:
            calibration: dict of objection_type → frequency weight (0.0 – 1.0).
                         e.g., {"rate": 0.4, "time": 0.3, "loyalty": 0.2, "skepticism": 0.1}
                         Higher weight = this objection type appeared more often in past calls.
        
        The calibration is applied as a small additive boost (up to +0.15) to
        the raw intent score, making the engine more likely to predict objection
        types that have historically been more common.
        """
        self._ccnm_calibration = calibration if calibration else {}
        if calibration:
            logger.info(f"[PREDICTIVE←CCNM] Calibration applied: {calibration}")

    def predict(self, user_text, sentiment):
        user_text_lower = user_text.lower()
        best_intent = None
        best_score = 0.0
        
        for intent_name, data in self.config.get("intents", {}).items():
            score = 0.0
            
            # Keyword match
            for kw in data.get("keywords", []):
                if kw in user_text_lower:
                    score += 0.4
            
            # Regex pattern match
            for pattern in data.get("patterns", []):
                if re.search(pattern, user_text_lower, re.I):
                    score += 0.6
            
            # Sentiment bias boost
            if sentiment == data.get("sentiment_bias"):
                score += 0.2
            
            # CCNM calibration boost: objection types that appeared more often
            # in past calls get a small additive boost (up to +0.15)
            obj_type = data.get("default_objection_type", "")
            if obj_type and obj_type in self._ccnm_calibration:
                cal_weight = self._ccnm_calibration[obj_type]
                score += cal_weight * 0.15  # Max boost: 0.15 (when weight=1.0)
            
            # Normalize score (cap at 1.0 for simplicity)
            score = min(score, 1.0)
            
            if score > best_score:
                best_score = score
                best_intent = {
                    "name": intent_name,
                    "objection_type": data.get("default_objection_type")
                }
        
        if best_intent and best_score >= self.config.get("thresholds", {}).get("min_confidence", 0.55):
            return Prediction(best_intent["name"], best_intent["objection_type"], best_score)
        
        return None

    def build_anticipatory_prefix(self, prediction):
        if not prediction:
            return ""
            
        obj_type = prediction.objection_type
        if obj_type == "rate":
            return "A lot of owners feel like the fees have been creeping up, even if they haven't said it out loud yet."
        if obj_type == "time":
            return "Most people I talk to are slammed and don't want another time sink."
        if obj_type == "loyalty":
            return "If you’ve got someone you like, the last thing you want is drama."
        if obj_type == "skepticism":
            return "You’ve probably heard versions of this before and wondered what the catch is."
        return ""

    def build_probing_question(self, prediction):
        if not prediction:
            return ""
            
        obj_type = prediction.objection_type
        if obj_type == "rate":
            return "Let me ask you this—have your fees felt stable, or have they been creeping up over time?"
        if obj_type == "time":
            return "Is the main concern right now just time, or is it more about not wanting to change anything that’s working?"
        if obj_type == "loyalty":
            return "Are you mostly staying where you are because you like the person, or because the numbers are actually solid?"
        if obj_type == "skepticism":
            return "Does this sound like something you’ve heard before that didn’t pan out?"
        return ""
