from core.constitutional import check_ethics
from core.config_loader import load_rules
from core.utils import calculate_score, determine_next_steps

def onboard_merchant(data: dict) -> dict:
    """
    Scores and activates a merchant based on eligibility and constitutional compliance.
    """
    rules = load_rules("onboarding_rules.yaml")
    if not check_ethics(data, rules):
        return {"status": "flagged", "reason": "constitutional violation"}
    score = calculate_score(data, rules)
    status = "approved" if score >= rules["score_threshold"] else "rejected"
    return {
        "status": status,
        "score": score,
        "next_steps": determine_next_steps(status)
    }
    }