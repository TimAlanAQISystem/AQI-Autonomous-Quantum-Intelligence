def calculate_score(data: dict, rules: dict) -> float:
    """
    Simple scoring logic for merchant onboarding.
    """
    score = 0.0
    # Example: +0.5 for location in approved states, +0.5 for business type in preferred list
    if data.get("location") in rules.get("preferred_states", []):
        score += 0.5
    if data.get("business_type") in rules.get("preferred_types", []):
        score += 0.5
    return score

def determine_next_steps(status: str) -> str:
    if status == "approved":
        return "Proceed to agreement signing."
    elif status == "rejected":
        return "Notify merchant of ineligibility."
    return "Review flagged for compliance."