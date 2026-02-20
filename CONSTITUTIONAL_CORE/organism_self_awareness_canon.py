# organism_self_awareness_canon.py
# Canon: Internal Health & Operational Context (Proprioception for Alan)

from enum import Enum, auto
from dataclasses import dataclass
from typing import Optional, Dict, Any
import datetime


# ---------- ENUMS ----------

class InternalHealth(Enum):
    OK = auto()
    WARM = auto()
    STRESSED = auto()
    DEGRADED = auto()


class OperationalContext(Enum):
    NORMAL = auto()
    QUIET_HOURS = auto()
    RUSH_WINDOW = auto()
    OVERNIGHT_MONITOR = auto()
    HIGH_LOAD = auto()


# ---------- TELEMETRY MODELS ----------

@dataclass
class InternalTelemetry:
    # Raw internal metrics (you can wire these from your infra)
    cpu_percent: float
    memory_percent: float
    event_loop_lag_ms: float
    active_calls: int
    queued_tasks: int
    error_rate_5m: float  # errors per minute over last 5 minutes


@dataclass
class ContextTelemetry:
    # Operational surroundings
    now_utc: datetime.datetime
    local_hour: int
    is_weekend: bool
    is_quiet_hours: bool
    is_rush_window: bool
    overnight_monitor_mode: bool
    global_active_calls: int
    global_queue_depth: int


@dataclass
class SelfAwarenessResult:
    internal_health: InternalHealth
    operational_context: OperationalContext
    reason_internal: str
    reason_context: str
    sovereign_state: str
    action: str
    # NOTE: These messages are primarily for logs / governance,
    # not for merchant-facing speech unless you explicitly choose to surface them.
    internal_log_message: str
    context_log_message: str


# ---------- CANONICAL INTERNAL PHRASES (LOG-LEVEL) ----------

INTERNAL_OK_MSG = "Internal state stable — timing, load, and error rates within sovereign bounds."
INTERNAL_WARM_MSG = "Internal state warm — elevated load, but within acceptable operating range."
INTERNAL_STRESSED_MSG = "Internal state stressed — high load or lag; recommend reduced concurrency or pacing adjustments."
INTERNAL_DEGRADED_MSG = "Internal state degraded — error rates or lag breaching thresholds; recommend shedding load or pausing new calls."


# ---------- CANONICAL CONTEXT PHRASES (LOG-LEVEL) ----------

CONTEXT_NORMAL_MSG = "Operational context: normal calling window, standard behavior."
CONTEXT_QUIET_HOURS_MSG = "Operational context: quiet hours — outbound calling should be restricted or disabled."
CONTEXT_RUSH_WINDOW_MSG = "Operational context: rush window — merchants likely busy; Rush Hour logic should be more sensitive."
CONTEXT_OVERNIGHT_MONITOR_MSG = "Operational context: overnight monitor — observation only, no outbound motion."
CONTEXT_HIGH_LOAD_MSG = "Operational context: high global load — consider throttling new sessions."


# ---------- EVALUATION LOGIC ----------

def evaluate_internal_health(t: InternalTelemetry) -> (InternalHealth, str):
    # You can tune these thresholds to your infra
    if (
        t.cpu_percent < 60
        and t.memory_percent < 70
        and t.event_loop_lag_ms < 80
        and t.error_rate_5m < 0.5
    ):
        return InternalHealth.OK, INTERNAL_OK_MSG

    if (
        t.cpu_percent < 80
        and t.memory_percent < 85
        and t.event_loop_lag_ms < 150
        and t.error_rate_5m < 1.0
    ):
        return InternalHealth.WARM, INTERNAL_WARM_MSG

    if (
        t.cpu_percent < 92
        and t.memory_percent < 92
        and t.event_loop_lag_ms < 250
        and t.error_rate_5m < 2.0
    ):
        return InternalHealth.STRESSED, INTERNAL_STRESSED_MSG

    return InternalHealth.DEGRADED, INTERNAL_DEGRADED_MSG


def evaluate_operational_context(c: ContextTelemetry) -> (OperationalContext, str):
    if c.overnight_monitor_mode:
        return OperationalContext.OVERNIGHT_MONITOR, CONTEXT_OVERNIGHT_MONITOR_MSG

    if c.is_quiet_hours:
        return OperationalContext.QUIET_HOURS, CONTEXT_QUIET_HOURS_MSG

    if c.is_rush_window:
        # e.g., lunch / dinner windows for restaurants, etc.
        return OperationalContext.RUSH_WINDOW, CONTEXT_RUSH_WINDOW_MSG

    if c.global_active_calls > 0 and c.global_queue_depth > 20:
        return OperationalContext.HIGH_LOAD, CONTEXT_HIGH_LOAD_MSG

    return OperationalContext.NORMAL, CONTEXT_NORMAL_MSG


def perceive_self_and_context(
    internal_dict: Dict[str, Any],
    context_dict: Dict[str, Any],
) -> SelfAwarenessResult:
    internal = InternalTelemetry(
        cpu_percent=internal_dict.get("cpu_percent", 0.0),
        memory_percent=internal_dict.get("memory_percent", 0.0),
        event_loop_lag_ms=internal_dict.get("event_loop_lag_ms", 0.0),
        active_calls=internal_dict.get("active_calls", 0),
        queued_tasks=internal_dict.get("queued_tasks", 0),
        error_rate_5m=internal_dict.get("error_rate_5m", 0.0),
    )

    now_utc = context_dict.get("now_utc") or datetime.datetime.utcnow()
    local_hour = context_dict.get("local_hour", now_utc.hour)

    context = ContextTelemetry(
        now_utc=now_utc,
        local_hour=local_hour,
        is_weekend=context_dict.get("is_weekend", False),
        is_quiet_hours=context_dict.get("is_quiet_hours", False),
        is_rush_window=context_dict.get("is_rush_window", False),
        overnight_monitor_mode=context_dict.get("overnight_monitor_mode", False),
        global_active_calls=context_dict.get("global_active_calls", 0),
        global_queue_depth=context_dict.get("global_queue_depth", 0),
    )

    internal_health, internal_msg = evaluate_internal_health(internal)
    op_context, context_msg = evaluate_operational_context(context)

    # Sovereign state + action are for the governance layer to interpret.
    # You can tune these mappings to your liking.
    if internal_health == InternalHealth.DEGRADED:
        sovereign_state = "self_degraded"
        action = "shed_load_and_pause_new_calls"
    elif internal_health == InternalHealth.STRESSED:
        sovereign_state = "self_stressed"
        action = "throttle_new_calls_and_slow_pacing"
    elif op_context == OperationalContext.OVERNIGHT_MONITOR:
        sovereign_state = "overnight_monitor"
        action = "observe_only"
    elif op_context == OperationalContext.QUIET_HOURS:
        sovereign_state = "quiet_hours"
        action = "restrict_outbound"
    else:
        sovereign_state = "self_stable"
        action = "normal_operation"

    return SelfAwarenessResult(
        internal_health=internal_health,
        operational_context=op_context,
        reason_internal=internal_msg,
        reason_context=context_msg,
        sovereign_state=sovereign_state,
        action=action,
        internal_log_message=internal_msg,
        context_log_message=context_msg,
    )


# ---------- INTEGRATION HOOK FOR ALAN’S CORTEX ----------

def self_awareness_hook(
    internal_dict: Dict[str, Any],
    context_dict: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Entry point for agent_alan_business_ai.py

    Input:
      - internal_dict: metrics from infra / runtime
      - context_dict: time-of-day, mode flags, global load

    Output:
      - governance object for context_sovereign_governance.py
    """

    result = perceive_self_and_context(internal_dict, context_dict)

    return {
        "internal_health": result.internal_health.name,
        "operational_context": result.operational_context.name,
        "sovereign_state": result.sovereign_state,
        "action": result.action,
        "internal_log_message": result.internal_log_message,
        "context_log_message": result.context_log_message,
    }
