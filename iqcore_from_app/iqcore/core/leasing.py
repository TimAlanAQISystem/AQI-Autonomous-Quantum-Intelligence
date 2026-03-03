from core.config_loader import load_thresholds

def escalate_case(case_data: dict) -> dict:
    """
    Escalates cases based on threshold parameters.
    """
    thresholds = load_thresholds("escalation_thresholds.yaml")
    escalation_level = 0
    for crit in thresholds.get("criteria", []):
        if case_data.get(crit["field"], 0) >= crit["threshold"]:
            escalation_level = max(escalation_level, crit["level"])
    status = "escalated" if escalation_level > 0 else "not_escalated"
    return {
        "status": status,
        "level": escalation_level,
        "escalation_path": thresholds.get("levels", {}).get(str(escalation_level), "None")
    }