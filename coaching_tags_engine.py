# coaching_tags_engine.py

def derive_coaching_tags(behavioral_vector: dict, perception_vector: dict) -> list[str]:
    tags = []

    mode = behavioral_vector.get("mode")
    health = behavioral_vector.get("health")
    state = behavioral_vector.get("fluidic_state")
    drift = behavioral_vector.get("trajectory_drift", 0.0)
    velocity = behavioral_vector.get("trajectory_velocity", 0.0)
    viscosity = behavioral_vector.get("emotional_viscosity", 1.0)
    objections = behavioral_vector.get("objection_count", 0)

    p_mode = perception_vector.get("mode")
    p_health = perception_vector.get("health")

    # Stalls
    if mode == "stalled" and state == "DISCOVERY":
        tags.append("STALL_DISCOVERY")
    if mode == "stalled" and state == "OPENING":
        tags.append("STALL_OPENING")

    # Collapses
    if mode == "collapsed" and state == "NEGOTIATION":
        tags.append("COLLAPSE_NEGOTIATION")
    if mode == "collapsed" and state == "CLOSING":
        tags.append("COLLAPSE_CLOSING")

    # High friction
    if mode == "high_friction" and objections >= 2:
        tags.append("HIGH_FRICTION_OBJECTIONS")
    if mode == "high_friction" and viscosity >= 1.4:
        tags.append("HIGH_VISCOSITY_USER_STATE")

    # Dead air / STT issues
    if mode == "stalled" and velocity <= 0.01 and p_mode == "silence":
        tags.append("DEAD_AIR_STT_FAILURE")

    # IVR / voicemail late detection
    if p_mode in ("ivr", "voicemail") and health == "failed":
        tags.append("IVR_LATE_DETECTION")

    # Audio / drift issues
    if p_health in ("degraded", "critical"):
        tags.append("AUDIO_DRIFT_OR_LATENCY")

    return tags
