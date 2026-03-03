from core.config_loader import load_flags

def analyze_retention(data: dict) -> dict:
    """
    Analyzes engagement data and flags accounts at risk.
    """
    flags = load_flags("retention_flags.yaml")
    risk_score = 0
    reasons = []
    for flag in flags.get("risk_factors", []):
        if data.get(flag["field"], 0) < flag["threshold"]:
            risk_score += flag["weight"]
            reasons.append(flag["reason"])
    status = "at_risk" if risk_score >= flags.get("risk_score_threshold", 1) else "stable"
    return {
        "status": status,
        "risk_score": risk_score,
        "reasons": reasons
    }