import json
import logging
import re
import random

logger = logging.getLogger(__name__)

class CallMemory:
    def __init__(self):
        self.key_points = []      # ["fees creeping up", "loyal to current rep"]
        self.objections = []      # [{"type": "rate", "strength": 4}]
        self.agreements = []      # ["open to looking at numbers"]
        self.goals = []           # ["keep costs predictable"]
    
    def to_dict(self):
        return {
            "key_points": self.key_points,
            "objections": self.objections,
            "agreements": self.agreements,
            "goals": self.goals
        }
    
    @classmethod
    def from_dict(cls, data):
        m = cls()
        if data:
            m.key_points = data.get("key_points", [])
            m.objections = data.get("objections", [])
            m.agreements = data.get("agreements", [])
            m.goals = data.get("goals", [])
        return m

class MasterCloserLayer:
    def __init__(self, config_path="master_closer_config.json"):
        try:
            with open(config_path, "r") as f:
                self.config = json.load(f)
            logger.info(f"[MASTER CLOSER] Config loaded from {config_path}")
        except Exception as e:
            logger.error(f"[MASTER CLOSER] Failed to load config: {e}")
            self.config = {}

        self.MICRO_PATTERNS = {
            "hesitation": ["uh", "um", "i mean", "well..."],
            "soft_resistance": ["i don't know", "not sure", "maybe", "kinda"],
            "half_objection": ["sounds good but", "yeah it's just", "the only thing is"]
        }

    def detect_micro_patterns(self, user_text):
        text = user_text.lower()
        hits = []
        for label, phrases in self.MICRO_PATTERNS.items():
            if any(p in text for p in phrases):
                hits.append(label)
        return hits

    def update_trajectory(self, current_state, signals):
        # Simplistic trajectory logic based on signals
        if not signals:
            return current_state or "neutral"
        
        warm_signals = self.config.get("trajectory", {}).get("rules", {}).get("warming", {}).get("signals", [])
        cool_signals = self.config.get("trajectory", {}).get("rules", {}).get("cooling", {}).get("signals", [])
        stall_signals = self.config.get("trajectory", {}).get("rules", {}).get("stalling", {}).get("signals", [])
        
        score = 0
        if any(s in signals for s in warm_signals): score += 1
        if any(s in signals for s in cool_signals): score -= 1
        if any(s in signals for s in stall_signals): score -= 2
        
        if score > 0: return "warming"
        if score < -1: return "stalling"
        if score < 0: return "cooling"
        return current_state or "neutral"

    def classify_merchant(self, user_text, current_type):
        if current_type and current_type != "unknown":
            return current_type
            
        text = user_text.lower()
        for m_type, data in self.config.get("merchant_types", {}).items():
            if any(s in text for s in data.get("signals", [])):
                return m_type
        return "neutral"

    def calculate_objection_weight(self, obj_type, trajectory, micro_patterns):
        base = self.config.get("objection_weighting", {}).get("types", {}).get(obj_type, {}).get("base_weight", 2)
        
        modifiers = self.config.get("objection_weighting", {}).get("modifiers", {})
        weight = base
        
        if trajectory in modifiers:
            weight += modifiers[trajectory]
            
        for pattern in micro_patterns:
            if pattern in modifiers:
                weight += modifiers[pattern]
                
        return max(1, weight)

    def update_scores(self, state, signals, sentiment):
        # Update Temperature (0-100)
        temp = state.get('temperature', 50)
        if sentiment == 'positive': temp += 10
        elif sentiment == 'negative': temp -= 10
        
        if "warming" in signals: temp += 5
        if "cooling" in signals: temp -= 5
        
        state['temperature'] = max(0, min(100, temp))
        
        # Update Confidence (0-100)
        conf = state.get('confidence_score', 50)
        if "warming" in signals: conf += 5
        if "stalling" in signals: conf -= 10
        if "good_question" in signals: conf += 3
        
        state['confidence_score'] = max(0, min(100, conf))

    def get_endgame_state(self, temperature, confidence):
        thresholds = self.config.get("endgame", {}).get("thresholds", {})
        
        if temperature >= thresholds["ready"]["temp_min"] and confidence >= thresholds["ready"]["conf_min"]:
            return "ready"
        if temperature >= thresholds["approaching"]["temp_min"] and confidence >= thresholds["approaching"]["conf_min"]:
            return "approaching"
        if temperature <= thresholds["too_cold"]["temp_max"] and confidence <= thresholds["too_cold"]["conf_max"]:
            return "too_cold"
        
        return "not_ready"

    def apply_mode_logic(self, response_text, merchant_type, trajectory):
        mode = "expansion"
        if merchant_type == "busy_owner" or trajectory in ["cooling", "stalling"]:
            mode = "compression"
            
        mode_cfg = self.config.get("modes", {}).get(mode, {})
        max_s = mode_cfg.get("max_sentences", 5)
        
        sentences = re.split(r'(?<=[.!?]) +', response_text)
        if len(sentences) > max_s:
            return " ".join(sentences[:max_s])
        return response_text
