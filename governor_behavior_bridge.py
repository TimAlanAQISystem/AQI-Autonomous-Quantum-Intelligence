from enum import Enum
from typing import Optional, Dict, Any

class GovernorAction(Enum):
    NONE = "none"
    NUDGE = "nudge"          # Log for tuning, potential future real-time hint
    FLAG = "flag"            # Mark for human/QA review (e.g. recovering calls)
    SOFT_KILL = "soft_kill"  # Mark outcome as system-aborted (retrospective) or stop campaign
    HARD_KILL = "hard_kill"  # Immediate stop of campaign / cooldown required
    COOLDOWN = "cooldown"    # Enter cool-down mode due to friction/heat

def decide_governor_action(behavioral_snapshot) -> GovernorAction:
    """
    Maps a BehavioralSnapshot to a GovernorAction.
    Policies:
      - COLLAPSED/FAILED -> HARD_KILL (Stop campaign, something is wrong)
      - STALLED + Low Velocity -> SOFT_KILL (Waste of resources)
      - HIGH_FRICTION + High Drift -> COOLDOWN (Agent getting heated/confused)
      - RECOVERING -> FLAG (Interesting edge case for learning)
    """
    if not behavioral_snapshot:
        return GovernorAction.NONE

    mode = behavioral_snapshot.mode.value
    health = behavioral_snapshot.health.value
    drift = behavioral_snapshot.trajectory_drift
    velocity = behavioral_snapshot.trajectory_velocity

    # 1. Critical Failures -> Hard Stop
    if health == "failed" or mode == "collapsed":
        return GovernorAction.HARD_KILL

    # 2. Resource Waste (Stalled) -> Soft Stop / Review
    # If velocity is very low (< 0.02) and we are stalled, it's a dead end.
    if mode == "stalled" and velocity <= 0.02:
        return GovernorAction.SOFT_KILL

    # 3. High Friction / Confusion -> Cooldown
    # If high friction AND significant drift, the agent is fighting the current.
    if mode == "high_friction" and abs(drift) >= 0.7:
        return GovernorAction.COOLDOWN
    
    # 4. Recovering -> Flag for Review
    # These are valuable positive examples or near-misses.
    if mode == "recovering":
        return GovernorAction.FLAG

    return GovernorAction.NONE
