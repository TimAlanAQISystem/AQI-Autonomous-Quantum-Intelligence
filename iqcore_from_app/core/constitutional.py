def check_ethics(data: dict, rules: dict) -> bool:
    """
    Enforces constitutional boundaries before logic execution.
    """
    restricted = rules.get("restricted_categories", [])
    return data.get("business_type") not in restricted

def apply_override(case: dict, founder_flag: bool) -> dict:
    """
    Allows founder-led override of flagged decisions.
    """
    if founder_flag:
        case["status"] = "approved"
        case["reason"] = "founder override"
    return case