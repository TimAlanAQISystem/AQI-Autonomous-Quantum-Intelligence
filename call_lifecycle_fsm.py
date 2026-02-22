"""
CALL LIFECYCLE FSM — Governor Replacement
==========================================
Created: February 18, 2026 — CW20
Purpose: Replace CALL_IN_PROGRESS boolean with explicit state machine.

Three Laws Doctrine, Law 3:
  "No shared resource controlling live behavior may be governed
   by a single boolean flag."

This module provides a complete Call Lifecycle FSM that replaces:
  - CALL_IN_PROGRESS (boolean) in control_api_fixed.py
  - governor_mark_start/end/check/clear in telephony_resilience.py
  - governor_watchdog_loop in telephony_resilience.py

Integration (Law 1 — capability must ship with integration):
  - Supervisor: FSM state reported via get_state_dict()
  - /health endpoint: reads FSM state directly
  - /twilio/events: feeds Twilio callbacks into on_twilio_event()
  - ARDE: can detect stuck states via get_state_dict()["status"]
  - Coaching: lifecycle phase visible for per-turn scoring

Behavioral Fusion Governor Integration (Session 18):
  - Added COOLDOWN state for behavioral circuit-breaking.
  - Added force_soft_terminate() for stalled calls.
  - Added enter_cooldown() for high-friction scenarios.

Failure philosophy (Law 2 — failure must never manifest as silence):
  - Every state has a bounded timeout
  - Every timeout leads to a terminal state
  - Every terminal state resolves to IDLE
  - No path can permanently block outbound calls
  - Every transition is logged

[NEG-PROOF] This file has zero production side effects on import.
It provides a class. Nothing runs until instantiated.
"""

from enum import Enum, auto
import time
import logging
import asyncio
from typing import Optional, Dict, Any, List

logger = logging.getLogger("CallLifecycleFSM")


# =============================================================================
# CALL STATES
# =============================================================================

class CallState(Enum):
    """
    Explicit call lifecycle states. Each has defined transitions and timeouts.
    No state can persist indefinitely — every non-IDLE state has a timeout.
    """
    IDLE = auto()               # No active call. Ready to fire.
    DIALING = auto()            # calls.create issued, waiting for Twilio acknowledgment
    RINGING = auto()            # Twilio reports ringing at destination
    CONNECTED_HUMAN = auto()    # Human answered (real conversation)
    CONNECTED_MACHINE = auto()  # Machine/IVR/voicemail detected
    WRAP_UP = auto()            # Call ended, post-call processing
    FAILED = auto()             # Call failed (error, canceled, busy)
    TIMEOUT = auto()            # State timeout triggered (no-answer, stuck)
    COOLDOWN = auto()           # [NEW] Mandatory cool-down state (behavioral/heat)


# =============================================================================
# PER-STATE TIMEOUT CONFIGURATION (seconds)
# =============================================================================
# Every non-IDLE state MUST have a timeout. This is what makes governor
# lock leaks structurally impossible.

STATE_TIMEOUTS: Dict[CallState, int] = {
    CallState.DIALING: 30,           # Twilio should report ringing within 30s
    CallState.RINGING: 55,           # Ring timeout is 50s + 5s buffer
    CallState.CONNECTED_HUMAN: 600,  # 10 min max (Cost Sentinel handles finer)
    CallState.CONNECTED_MACHINE: 90, # IVR/voicemail kill threshold
    CallState.WRAP_UP: 30,           # Post-hangup cleanup window
    CallState.FAILED: 5,             # Immediate cleanup
    CallState.TIMEOUT: 5,            # Immediate cleanup
    CallState.COOLDOWN: 300,         # Max 5 min cooldown (usually cleared manually or by timer)
    # IDLE has no timeout — it IS the resting state
}

# Post-call cooldown (seconds) — reflection window after call ends
POST_CALL_COOLDOWN: int = 30


# =============================================================================
# VALID STATE TRANSITIONS
# =============================================================================
# Explicit transition table. Any transition not listed here is invalid.
# This prevents illegal state jumps that could leave the FSM in a bad state.

VALID_TRANSITIONS: Dict[CallState, frozenset] = {
    CallState.IDLE: frozenset({CallState.DIALING, CallState.COOLDOWN}),
    CallState.DIALING: frozenset({CallState.RINGING, CallState.FAILED, CallState.TIMEOUT}),
    CallState.RINGING: frozenset({
        CallState.CONNECTED_HUMAN, CallState.CONNECTED_MACHINE,
        CallState.FAILED, CallState.TIMEOUT,
    }),
    CallState.CONNECTED_HUMAN: frozenset({CallState.WRAP_UP, CallState.FAILED, CallState.TIMEOUT, CallState.COOLDOWN}),
    CallState.CONNECTED_MACHINE: frozenset({CallState.WRAP_UP, CallState.FAILED, CallState.TIMEOUT, CallState.COOLDOWN}),
    CallState.WRAP_UP: frozenset({CallState.IDLE, CallState.COOLDOWN}),
    CallState.FAILED: frozenset({CallState.IDLE, CallState.COOLDOWN}),
    CallState.TIMEOUT: frozenset({CallState.IDLE, CallState.COOLDOWN}),
    CallState.COOLDOWN: frozenset({CallState.IDLE}),
}


# =============================================================================
# FSM CLASS
# =============================================================================

class CallLifecycleFSM:
    """
    Single FSM instance managing call lifecycle. Replaces CALL_IN_PROGRESS entirely.

    Usage:
        fsm = CallLifecycleFSM()
        fsm.start_call("CA_xxxx")           # Before calls.create
        fsm.on_twilio_event("ringing", ...)  # Fed by /twilio/events
        fsm.tick()                           # Called by background watchdog

    Query:
        fsm.is_active()       # Replaces CALL_IN_PROGRESS
        fsm.can_start_call()  # Replaces can_fire_call()
        fsm.get_state_dict()  # For /health, supervisor, dashboard
    """

    def __init__(self):
        self.call_id: str = ""
        self.state: CallState = CallState.IDLE
        self.state_entered_at: float = time.time()
        self.last_call_ended_at: float = 0.0  # For cooldown tracking (replaces LAST_CALL_TS)
        self._history: List[Dict[str, Any]] = []  # State transition log
        self._total_calls: int = 0  # Lifetime call counter
        self._total_timeouts: int = 0  # Lifetime timeout counter
        self._total_failures: int = 0  # Lifetime failure counter
        self._cooldown_expiry: float = 0.0 # [NEW] When explicitly set

    # ------------------------------------------------------------------
    # State transitions (internal)
    # ------------------------------------------------------------------

    def _transition(self, new_state: CallState, reason: str) -> bool:
        """
        Execute a state transition with validation and logging.
        Returns True if transition was executed, False if rejected.
        """
        old = self.state
        now = time.time()
        duration_in_old = round(now - self.state_entered_at, 2)

        # Validate transition
        valid = VALID_TRANSITIONS.get(old, frozenset())
        if new_state not in valid and new_state != CallState.IDLE:
            # Allow force-to-IDLE from any state (emergency recovery)
            logger.warning(
                f"[FSM] INVALID transition {old.name} → {new_state.name} "
                f"({reason}). Valid: {[s.name for s in valid]}. REJECTED."
            )
            return False

        # Record history
        entry = {
            "from": old.name,
            "to": new_state.name,
            "reason": reason,
            "duration_s": duration_in_old,
            "ts": now,
            "call_id": self.call_id,
        }
        self._history.append(entry)
        # Keep history bounded (last 50 transitions)
        if len(self._history) > 50:
            self._history = self._history[-50:]

        logger.info(
            f"[FSM] {old.name} → {new_state.name} "
            f"({reason}, spent {duration_in_old}s in {old.name}) "
            f"[call={self.call_id}]"
        )

        # Track metrics
        if new_state == CallState.TIMEOUT:
            self._total_timeouts += 1
        elif new_state == CallState.FAILED:
            self._total_failures += 1

        # Track when we return to IDLE for cooldown
        if new_state == CallState.IDLE and old != CallState.IDLE:
            self.last_call_ended_at = now
            self._total_calls += 1

        self.state = new_state
        self.state_entered_at = now
        return True

    def _seconds_in_state(self) -> float:
        """How long the FSM has been in the current state."""
        return time.time() - self.state_entered_at

    # ------------------------------------------------------------------
    # Public API — called by control_api_fixed.py
    # ------------------------------------------------------------------

    def start_call(self, call_id: str = "") -> bool:
        """
        Begin a new call lifecycle. Replaces mark_call_start().
        Called before calls.create.
        Returns True if transition accepted, False if busy.
        """
        if self.state != CallState.IDLE:
            logger.warning(
                f"[FSM] start_call() called in state {self.state.name} "
                f"(call_id={call_id}) — REJECTED. Current call: {self.call_id}"
            )
            return False
        self.call_id = call_id or ""
        self._transition(CallState.DIALING, "start_call")
        return True

    def on_twilio_event(self, call_status: str, answered_by: str = "", call_sid: str = ""):
        """
        Process a Twilio status callback. Replaces the governor logic inside /twilio/events.

        Maps Twilio's CallStatus strings to FSM transitions.
        Called by the /twilio/events endpoint handler.

        Twilio sends: initiated, ringing, answered, completed, busy, no-answer, canceled, failed
        """
        status = call_status.lower().replace("call.", "").strip() if call_status else ""

        if call_sid and not self.call_id:
            self.call_id = call_sid

        # ---- DIALING state ----
        if self.state == CallState.DIALING:
            if status == "initiated":
                # Twilio accepted — stay in DIALING
                logger.info(f"[FSM] Twilio initiated call {call_sid} — staying in DIALING")
            elif status == "ringing":
                self._transition(CallState.RINGING, f"twilio: {call_status}")
            elif status in ("failed", "canceled"):
                self._transition(CallState.FAILED, f"twilio: {call_status} (in DIALING)")
            elif status in ("busy", "no-answer"):
                self._transition(CallState.TIMEOUT, f"twilio: {call_status} (in DIALING)")
            elif status == "completed":
                # Rare: completed without answered — treat as failed
                self._transition(CallState.FAILED, f"twilio: completed before answered (in DIALING)")
            elif status == "answered":
                # Rare: answered without ringing event — handle gracefully
                if answered_by in ("machine_start", "machine_end", "fax"):
                    self._transition(CallState.RINGING, "twilio: ringing (implied)")
                    self._transition(CallState.CONNECTED_MACHINE, f"twilio: machine ({answered_by})")
                else:
                    self._transition(CallState.RINGING, "twilio: ringing (implied)")
                    self._transition(CallState.CONNECTED_HUMAN, f"twilio: human ({answered_by})")

        # ---- RINGING state ----
        elif self.state == CallState.RINGING:
            if status == "answered":
                if answered_by in ("machine_start", "machine_end", "fax"):
                    self._transition(CallState.CONNECTED_MACHINE, f"twilio: machine ({answered_by})")
                else:
                    self._transition(CallState.CONNECTED_HUMAN, f"twilio: human ({answered_by})")
            elif status in ("no-answer", "busy"):
                self._transition(CallState.TIMEOUT, f"twilio: {call_status}")
            elif status in ("failed", "canceled"):
                self._transition(CallState.FAILED, f"twilio: {call_status}")
            elif status == "completed":
                # Completed from ringing — brief flash connect, treat as wrap-up
                self._transition(CallState.CONNECTED_HUMAN, "twilio: brief connect (implied)")
                self._transition(CallState.WRAP_UP, f"twilio: {call_status}")

        # ---- CONNECTED states ----
        elif self.state in (CallState.CONNECTED_HUMAN, CallState.CONNECTED_MACHINE):
            if status == "completed":
                self._transition(CallState.WRAP_UP, f"twilio: {call_status}")
            elif status in ("failed", "canceled"):
                self._transition(CallState.FAILED, f"twilio: {call_status}")

        # ---- Catch-all: completed from any non-terminal state ----
        elif status == "completed" and self.state not in (
            CallState.IDLE, CallState.WRAP_UP, CallState.FAILED, CallState.TIMEOUT, CallState.COOLDOWN
        ):
            self._transition(CallState.WRAP_UP, f"twilio: {call_status} (catch-all from {self.state.name})")

        else:
            logger.debug(
                f"[FSM] Unhandled event '{call_status}' (answered_by={answered_by}) "
                f"in state {self.state.name} [call={self.call_id}]"
            )

    def force_end(self, reason: str = "force_end"):
        """
        Emergency force-return to IDLE. Replaces watchdog force-unlock.
        Allowed from ANY state (bypasses transition validation).
        """
        if self.state == CallState.IDLE:
            return
        old = self.state
        now = time.time()
        duration = round(now - self.state_entered_at, 2)
        self._history.append({
            "from": old.name,
            "to": "IDLE",
            "reason": f"FORCE: {reason}",
            "duration_s": duration,
            "ts": now,
            "call_id": self.call_id,
        })
        if len(self._history) > 50:
            self._history = self._history[-50:]
        logger.warning(
            f"[FSM] FORCE {old.name} → IDLE ({reason}, spent {duration}s) "
            f"[call={self.call_id}]"
        )
        self.last_call_ended_at = now
        self._total_calls += 1
        self.state = CallState.IDLE
        self.state_entered_at = now
        self.call_id = ""

    # ------------------------------------------------------------------
    # Behavioral Governor Integration
    # ------------------------------------------------------------------    

    def force_soft_terminate(self, call_id: str):
        """
        Signal a soft termination (stall/bad path), leading to WRAP_UP or FAILED.
        Does not imply hardware failure.
        """
        # If call_id mismatch, we ignore to prevent cross-talk, unless system-wide
        if self.call_id and call_id and self.call_id != call_id:
            logger.warning(f"[FSM] force_soft_terminate mismatch: {call_id} != {self.call_id}")
            return
        
        # Move directly to WRAP_UP if connected, otherwise FAIL
        if self.state in (CallState.CONNECTED_HUMAN, CallState.CONNECTED_MACHINE):
            self._transition(CallState.WRAP_UP, "governor: soft_terminate")
        elif self.state == CallState.DIALING or self.state == CallState.RINGING:
            self._transition(CallState.FAILED, "governor: soft_terminate (pre-connect)")
        else:
            logger.info(f"[FSM] Soft terminate in state {self.state.name} - ignored or handled")

    def force_hard_terminate(self, call_id: str):
        """
        Hard terminate immediately. Similar to force_end but respects state logic if possible.
        """
        if self.call_id and call_id and self.call_id != call_id:
            logger.warning(f"[FSM] force_hard_terminate mismatch: {call_id} != {self.call_id}")
            return

        self.force_end("governor: hard_terminate")

    def enter_cooldown(self, duration_s: int = 300):
        """
        Force the FSM into COOLDOWN state for a set duration.
        """
        self._cooldown_expiry = time.time() + duration_s
        # Only transition if not IDLE (or from IDLE) — actually from anywhere
        # If in a call, we should force end first? user says 'enter_cooldown' implies stop taking calls.
        if self.state != CallState.IDLE and self.state != CallState.COOLDOWN:
            self.force_end("governor: cooldown_preemption")
        
        self._transition(CallState.COOLDOWN, f"governor: explicit cooldown ({duration_s}s)")

    def is_in_cooldown(self) -> bool:
        """Check if currently in cooldown."""
        if self.state == CallState.COOLDOWN:
            if time.time() > self._cooldown_expiry:
                # Cooldown expired, check transition back
                # Self-healing: if check is called, resolve state
                self._transition(CallState.IDLE, "cooldown: expired")
                return False
            return True
        return False

    # ------------------------------------------------------------------
    # Tick — called by background watchdog task
    # ------------------------------------------------------------------

    def tick(self) -> Optional[str]:
        """
        Check for state timeouts. Call every N seconds from a background task.
        Returns a string describing any action taken, or None if no action.

        This is what makes governor lock leaks STRUCTURALLY IMPOSSIBLE:
        every non-IDLE state will eventually time out and return to IDLE.
        """
        if self.state == CallState.IDLE:
            return None  # IDLE has no timeout

        # Cooldown check in tick
        if self.state == CallState.COOLDOWN:
            if time.time() > self._cooldown_expiry:
                self._transition(CallState.IDLE, "cooldown: expired (watchdog)")
                return "cooldown_expired"
            return None

        timeout = STATE_TIMEOUTS.get(self.state)
        if timeout is None:
            return None

        elapsed = self._seconds_in_state()
        if elapsed <= timeout:
            return None

        # Timeout triggered
        action = None
        if self.state in (CallState.FAILED, CallState.TIMEOUT, CallState.WRAP_UP):
            # Terminal states → IDLE (cleanup)
            self._transition(CallState.IDLE, f"cleanup after {elapsed:.0f}s in {self.state.name}")
            action = f"cleanup: {self.state.name} → IDLE"
        elif self.state == CallState.DIALING:
            self._transition(CallState.TIMEOUT, f"dialing timeout ({elapsed:.0f}s > {timeout}s)")
            action = "dialing_timeout"
        elif self.state == CallState.RINGING:
            self._transition(CallState.TIMEOUT, f"ringing timeout ({elapsed:.0f}s > {timeout}s)")
            action = "ringing_timeout"
        elif self.state == CallState.CONNECTED_MACHINE:
            self._transition(CallState.TIMEOUT, f"machine timeout ({elapsed:.0f}s > {timeout}s)")
            action = "machine_timeout"
        elif self.state == CallState.CONNECTED_HUMAN:
            self._transition(CallState.TIMEOUT, f"call too long ({elapsed:.0f}s > {timeout}s)")
            action = "max_duration_timeout"

        return action

    # ------------------------------------------------------------------
    # Query methods — replace CALL_IN_PROGRESS reads
    # ------------------------------------------------------------------

    def is_idle(self) -> bool:
        """True when no call is active. Replaces `not CALL_IN_PROGRESS`."""
        return self.state == CallState.IDLE

    def is_active(self) -> bool:
        """True when a call is in progress. Replaces `CALL_IN_PROGRESS`."""
        return self.state != CallState.IDLE

    def can_start_call(self) -> bool:
        """
        True when a new call can begin. Replaces `can_fire_call()`.
        Checks: must be IDLE + cooldown must be expired.
        """
        # If in explicit cooldown state
        if self.state == CallState.COOLDOWN:
            if self.is_in_cooldown(): # checks expiry
                return False

        if not self.is_idle():
            return False
            
        if self.last_call_ended_at > 0:
            cooldown_remaining = POST_CALL_COOLDOWN - (time.time() - self.last_call_ended_at)
            if cooldown_remaining > 0:
                return False
        return True

    def cooldown_remaining(self) -> float:
        """Seconds remaining in post-call cooldown. 0 if none."""
        if self.state == CallState.COOLDOWN:
             return max(0.0, self._cooldown_expiry - time.time())
             
        if not self.is_idle() or self.last_call_ended_at == 0:
            return 0.0
        remaining = POST_CALL_COOLDOWN - (time.time() - self.last_call_ended_at)
        return max(0.0, remaining)

    # ------------------------------------------------------------------
    # Dashboard / supervisor / health integration
    # ------------------------------------------------------------------

    def get_state_dict(self) -> Dict[str, Any]:
        """
        Returns complete state for /health, supervisor, dashboard.
        Replaces the scattered update_governor_state() calls.
        """
        return {
            "state": self.state.name,
            "call_id": self.call_id,
            "seconds_in_state": round(self._seconds_in_state(), 1),
            "timeout_for_state": STATE_TIMEOUTS.get(self.state),
            "is_active": self.is_active(),
            "can_start_call": self.can_start_call(),
            "cooldown_remaining": round(self.cooldown_remaining(), 1),
            "last_call_ended_at": self.last_call_ended_at,
            "total_calls": self._total_calls,
            "total_timeouts": self._total_timeouts,
            "total_failures": self._total_failures,
            "history": self._history[-10:],  # Last 10 transitions
            "status": self._derive_status(),
            # Backward compatibility — old governor field names
            "call_in_progress": self.is_active(),
            "watchdog_active": True,  # FSM is always watching
        }

    def _derive_status(self) -> str:
        """
        Derives the same idle/active/cooldown/stuck labels the old governor used.
        Backward-compatible with supervisor.update_governor_state().
        """
        if self.state == CallState.IDLE:
            if self.cooldown_remaining() > 0:
                return "cooldown"
            return "idle"
        if self.state == CallState.COOLDOWN:
            return "cooldown"
        timeout = STATE_TIMEOUTS.get(self.state, 999)
        if self._seconds_in_state() > timeout:
            return "stuck"
        return "active"


# =============================================================================
# BACKGROUND WATCHDOG TASK — replaces governor_watchdog_loop
# =============================================================================

async def fsm_watchdog_loop(
    fsm: CallLifecycleFSM,
    check_interval: float = 10,
    supervisor_getter=None,
):
    """
    Background task — calls fsm.tick() every check_interval seconds.
    Replaces governor_watchdog_loop() entirely.

    Faster interval (10s vs old 30s) because FSM handles its own timeouts
    correctly — no risk of premature unlock, so we can check more often.

    Args:
        fsm: The CallLifecycleFSM instance
        check_interval: Seconds between tick() calls
        supervisor_getter: Optional callable returning supervisor instance
    """
    logger.info(f"[FSM-WATCHDOG] Started. Interval: {check_interval}s")
    while True:
        try:
            await asyncio.sleep(check_interval)
            action = fsm.tick()
            if action:
                logger.warning(f"[FSM-WATCHDOG] Tick action: {action}")
                # Report to supervisor if available
                if supervisor_getter:
                    try:
                        sup = supervisor_getter()
                        if sup and hasattr(sup, 'report_incident'):
                            sup.report_incident(
                                component="GOVERNOR_FSM",
                                severity="warning",
                                issue=f"FSM timeout action: {action}",
                                reason=f"State {fsm.state.name} exceeded timeout",
                                fix="FSM auto-recovered to IDLE",
                                context=fsm.get_state_dict(),
                                id_prefix="fsm-timeout",
                            )
                    except Exception:
                        pass  # Supervisor not available — non-critical
        except asyncio.CancelledError:
            logger.info("[FSM-WATCHDOG] Cancelled. Shutting down.")
            break
        except Exception as e:
            logger.error(f"[FSM-WATCHDOG] Error: {e}")
