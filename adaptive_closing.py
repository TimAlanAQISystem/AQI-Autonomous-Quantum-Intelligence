import json
import random
import logging

logger = logging.getLogger(__name__)

class ClosingStrategyEngine:
    def __init__(self, config_path="adaptive_closing_strategy.json"):
        try:
            with open(config_path, "r") as f:
                self.config = json.load(f)
            logger.info(f"[CLOSING] Config loaded from {config_path}")
        except Exception as e:
            logger.error(f"[CLOSING] Failed to load config: {e}")
            self.config = {"styles": {}}

    def choose_style(self, analysis):
        """
        analysis expected to have: sentiment, personality_guess, key_phrases
        """
        sentiment = analysis.get("sentiment", "neutral")
        personality = analysis.get("personality_guess", "unknown")
        phrases = analysis.get("key_phrases", [])
        
        best_style = self.config.get("defaults", {}).get("style", "direct")
        max_matches = 0
        
        for style_name, data in self.config.get("styles", {}).items():
            matches = 0
            triggers = data.get("triggers", {})
            
            if sentiment in triggers.get("sentiment", []):
                matches += 1
            if personality in triggers.get("personality", []):
                matches += 1
            
            for phrase in phrases:
                if phrase in triggers.get("phrases", []):
                    matches += 1
            
            if matches > max_matches:
                max_matches = matches
                best_style = style_name
                
        return best_style

    def pick_line(self, style):
        lines = self.config.get("styles", {}).get(style, {}).get("closing_lines", [])
        if not lines:
            # Fallback to direct if style not found
            lines = self.config.get("styles", {}).get("direct", {}).get("closing_lines", ["Let's take a look at a statement."])
        return random.choice(lines)
