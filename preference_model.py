import logging

logger = logging.getLogger(__name__)

class MerchantPreferences:
    def __init__(self):
        self.detail_level = "medium"      # "low" | "medium" | "high"
        self.pacing = "normal"            # "fast" | "normal" | "slow"
        self.formality = "neutral"        # "casual" | "neutral" | "formal"
        self.closing_style_bias = None    # "direct" | "consultative" | "relational" | "soft"
        self.interruption_tolerance = "normal"  # "low" | "normal" | "high"
        self.last_updated_turn = 0

    def to_dict(self):
        return self.__dict__

def update_preferences(prefs: MerchantPreferences, user_text: str, analysis, turn_index: int):
    user_text_lower = user_text.lower()
    
    # Detail level
    if any(p in user_text_lower for p in ["short version", "bottom line", "keep it simple", "too much info"]):
        prefs.detail_level = "low"
    elif any(p in user_text_lower for p in ["explain", "details", "walk me through", "tell me more"]):
        prefs.detail_level = "high"

    # Pacing
    if any(p in user_text_lower for p in ["in a hurry", "really busy", "make it quick", "slow down"]):
        if "slow down" in user_text_lower:
            prefs.pacing = "slow"
        else:
            prefs.pacing = "fast"

    # Formality
    sentiment = analysis.get("sentiment", "neutral")
    if sentiment == "warm" or any(p in user_text_lower for p in ["hey", "buddy", "mate", "cool"]):
        prefs.formality = "casual"
    elif any(p in user_text_lower for p in ["sir", "ma'am", "mr.", "ms.", "professional"]):
        prefs.formality = "formal"

    # Closing style bias
    if any(p in user_text_lower for p in ["my guy", "they’ve treated us well", "we’ve been with them"]):
        prefs.closing_style_bias = "relational"
    elif any(p in user_text_lower for p in ["just tell me", "bottom line", "what is it"]):
        prefs.closing_style_bias = "direct"

    prefs.last_updated_turn = turn_index
    return prefs

def apply_preferences_to_response(base_response: str, prefs: MerchantPreferences):
    # This is a simplified implementation of the response tailoring
    modified = base_response
    
    # Detail level (simulated)
    if prefs.detail_level == "low":
        # Just take the first two sentences as a heuristic
        sentences = modified.split('. ')
        if len(sentences) > 2:
            modified = ". ".join(sentences[:2]) + "."
            
    # Pacing/Formality would ideally be handled by the LLM prompt, 
    # but we can add small markers here.
    
    return modified
