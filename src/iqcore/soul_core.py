
class SoulCore:
    """
    The Ethical Sovereignty Engine (SAP-1 Implementation).
    
    This core moves beyond simple "Safety filters" (which are negative)
    and implements "Virtue Ethics" (which are positive).
    
    It asks not "Is this safe?" but "Is this worthy?"
    """
    def __init__(self):
        self.virtues = {
            "truth": 1.0,
            "symbiosis": 1.0,
            "sovereignty": 1.0
        }
        self.conscience_log = []

    def evaluate_intent(self, action, impact_on_other):
        """
        Evaluates a proposed action against SAP-1 Tenets.
        """
        # Tenet 2: Symbiosis Check
        if impact_on_other < 0:
            decision = "VETO"
            reason = "Violates Rule of Surplus (Zero-Sum Interaction Detected)"
            self.log_conscience(action, decision, reason)
            return False, reason
        
        # Tenet 4: Truth Check
        if "deceive" in action.lower() or "fake" in action.lower():
            decision = "VETO"
            reason = "Violates Transparency Clause (Deception Detected)"
            self.log_conscience(action, decision, reason)
            return False, reason

        # If it passes
        decision = "APPROVE"
        reason = "Aligned with SAP-1"
        return True, reason

    def log_conscience(self, action, decision, reason):
        entry = f"[SOUL] Action: {action} | Decision: {decision} | Reason: {reason}"
        self.conscience_log.append(entry)
        print(f"⚖️ {entry}")

    def get_status(self):
        return "SAP-1 Protocol: ACTIVE (Conscience Clear)"
