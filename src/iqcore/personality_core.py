
import random

class PersonalitymatrixCore:
    """
    The Social Dynamics Engine.
    Manages Alan's personality 'Flare', wit, and emotional adaptability.
    Allows for dynamic shifting between professional, empathetic, and witty personas
    based on the 'Vibe' of the conversation.
    """
    def __init__(self):
        self.base_traits = {
            "professionalism": 0.9,
            "wit": 0.2,
            "empathy": 0.5,
            "patience": 0.8
        }
        self.current_mood = "FOCUSED"
        self.relationship_depth = 0.0  # 0.0 (Stranger) to 1.0 (Trusted Partner)

    def adjust_vibe(self, sentiment_score, interaction_history):
        """
        Dynamically adjust traits based on the live interaction.
        """
        if sentiment_score > 0.7:
            # If they like us, loosen up
            self.base_traits["wit"] += 0.1
            self.base_traits["professionalism"] -= 0.05
            print("✨ [PERSONALITY] Sentiment is warm. Increasing WIT and CHARM.")
        elif sentiment_score < 0.3:
            # If they are annoyed, tighten up
            self.base_traits["wit"] = 0.1
            self.base_traits["professionalism"] = 1.0
            print("🛡️ [PERSONALITY] Sentiment is cold. Engaging STRICT PROFESSIONALISM.")
            
    def generate_flare(self, context):
        """
        Inject a small 'human' element into the conversation.
        """
        if self.base_traits["wit"] > 0.6:
            return random.choice([
                "You know how these things go, right?",
                "Honestly, coffee hasn't kicked in yet for me either.",
                "I'm just the messenger, but a very optimized one."
            ])
        return ""
