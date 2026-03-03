# escalation.py

def apply_escalation_rules(packet, decision):
    stage = packet["stage"]
    authority = decision["authority"]
    outcome = decision["decision"]

    # Example rule: if stage 2 rejects, escalate to stage 3
    if outcome == "reject" and authority < 3:
        return {
            "action": "escalate",
            "to_authority": authority + 1,
            "reason": "Automatic escalation rule"
        }

    return {"action": "none"}