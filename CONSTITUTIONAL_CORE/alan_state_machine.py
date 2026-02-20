"""
Alan's Hierarchical State Machine
==================================

Two-layer state machine implementing Alan's operational contract:
- System Layer: Infrastructure stability and service readiness
- Session Layer: User session management and governance

Constitutional compliance enforced at every transition.

UPDATED: February 5, 2026 - Phase 1A Step 2
- Integrated session_persistence.py for crash recovery
- Auto-save sessions on state transitions
- Recovery mechanism for system restarts
"""

import logging
import time
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, Callable, List
from dataclasses import dataclass, field
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AlanStateMachine")


# ============================================================================
# SYSTEM LAYER STATES
# ============================================================================

class SystemState(Enum):
    """System layer states - infrastructure and service health"""
    BOOTSTRAPPING = "bootstrapping"
    READY = "ready"
    DEGRADED = "degraded"
    SYSTEM_ERROR = "system_error"
    SHUTTING_DOWN = "shutting_down"
    OFF = "off"


class SystemEvent(Enum):
    """System layer events"""
    BOOT_OK = "boot_ok"
    BOOT_PARTIAL = "boot_partial"
    BOOT_FAIL = "boot_fail"
    HEALTH_FAIL = "health_fail"
    HEALTH_RECOVERED = "health_recovered"
    HEALTH_WORSE = "health_worse"
    SHUTDOWN_REQUEST = "shutdown_request"
    SHUTDOWN_COMPLETE = "shutdown_complete"
    RECOVER_OK = "recover_ok"


# ============================================================================
# SESSION LAYER STATES
# ============================================================================

class SessionState(Enum):
    """Session layer states - user interaction management"""
    SESSION_IDLE = "session_idle"
    IDENTITY_LOCK_PENDING = "identity_lock_pending"
    SESSION_DENIED = "session_denied"
    OPENING_INTENT = "opening_intent"
    CONVERSATIONAL_FLOW = "conversational_flow"
    TASK_MODE = "task_mode"
    ESCALATION_MODE = "escalation_mode"
    GOVERNANCE_BLOCK = "governance_block"
    ERROR_RECOVERY = "error_recovery"
    SESSION_TERMINATED = "session_terminated"


class SessionEvent(Enum):
    """Session layer events"""
    USER_CONNECT = "user_connect"
    USER_DISCONNECT = "user_disconnect"
    IDENTITY_OK = "identity_ok"
    IDENTITY_FAIL = "identity_fail"
    TIMEOUT = "timeout"
    RETRY_ALLOWED = "retry_allowed"
    USER_RETRY = "user_retry"
    INTENT_CONVERSATIONAL = "intent_conversational"
    INTENT_TASK = "intent_task"
    INTENT_ESCALATION = "intent_escalation"
    INTENT_INVALID = "intent_invalid"
    TASK_REQUEST = "task_request"
    TASK_COMPLETE = "task_complete"
    TASK_FAIL_RECOVERABLE = "task_fail_recoverable"
    TASK_FAIL_FATAL = "task_fail_fatal"
    ESCALATION_NEEDED = "escalation_needed"
    ESCALATION_ROUTED = "escalation_routed"
    ESCALATION_REFUSED = "escalation_refused"
    POLICY_VIOLATION = "policy_violation"
    REPEATED_VIOLATION = "repeated_violation"
    USER_ADJUSTS_REQUEST = "user_adjusts_request"
    RECOVER_OK = "recover_ok"
    RECOVER_FAIL = "recover_fail"
    IDLE_TIMEOUT = "idle_timeout"
    USER_ABORT = "user_abort"


# ============================================================================
# TASK MODE SUBSTATES
# ============================================================================

class TaskSubstate(Enum):
    """Substates within TaskMode"""
    PLANNING = "planning"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    REPORTING = "reporting"


# ============================================================================
# STATE TRANSITION
# ============================================================================

@dataclass
class StateTransition:
    """Record of a state transition with full context"""
    timestamp: str
    from_state: str
    to_state: str
    event: str
    guard_result: bool
    correlation_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_log_entry(self) -> str:
        """Format as structured log entry"""
        return json.dumps({
            "timestamp": self.timestamp,
            "from_state": self.from_state,
            "to_state": self.to_state,
            "event": self.event,
            "guard_result": self.guard_result,
            "correlation_id": self.correlation_id,
            "metadata": self.metadata
        })


# ============================================================================
# SYSTEM STATE MACHINE
# ============================================================================

class SystemStateMachine:
    """
    System layer state machine - manages infrastructure health and service availability.
    
    States: Bootstrapping → Ready/Degraded → SystemError/ShuttingDown → Off
    """
    
    def __init__(self, correlation_id: str):
        self.state = SystemState.OFF
        self.correlation_id = correlation_id
        self.transitions_log: List[StateTransition] = []
        self.metadata: Dict[str, Any] = {}
        
        # Health check components
        self.health_checks = {
            "control_api": False,
            "llm_backend": False,
            "vector_store": False,
            "logging": False,
            "voice_module": False
        }
        
    def _log_transition(self, from_state: SystemState, to_state: SystemState, 
                       event: SystemEvent, guard_result: bool = True, 
                       metadata: Dict[str, Any] = None):
        """Log state transition"""
        transition = StateTransition(
            timestamp=datetime.now().isoformat(),
            from_state=from_state.value,
            to_state=to_state.value,
            event=event.value,
            guard_result=guard_result,
            correlation_id=self.correlation_id,
            metadata=metadata or {}
        )
        self.transitions_log.append(transition)
        logger.info(f"SYSTEM TRANSITION: {transition.to_log_entry()}")
        
    def _entry_action_bootstrapping(self):
        """Entry actions for Bootstrapping state"""
        logger.info("SYSTEM BOOTSTRAPPING: Checking substrate and services...")
        
        # Check substrate (OS, network, storage)
        substrate_ok = True  # Placeholder for actual checks
        
        # Check services
        services_status = {k: False for k in self.health_checks.keys()}
        # Placeholder: would check each service
        
        self.metadata["substrate_ok"] = substrate_ok
        self.metadata["services_status"] = services_status
        
    def _entry_action_ready(self):
        """Entry actions for Ready state"""
        logger.info("SYSTEM READY: Registering presence, resetting counters...")
        self.metadata["available"] = True
        self.metadata["error_count"] = 0
        self.metadata["session_count"] = 0
        
    def _entry_action_degraded(self):
        """Entry actions for Degraded state"""
        logger.warning("SYSTEM DEGRADED: Enabling reduced capacity mode...")
        self.metadata["degraded_mode"] = True
        self.metadata["max_concurrent_sessions"] = 1  # Reduce from normal capacity
        
    def _entry_action_system_error(self):
        """Entry actions for SystemError state"""
        logger.error("SYSTEM ERROR: Freezing intake, capturing diagnostic snapshot...")
        self.metadata["intake_frozen"] = True
        self.metadata["error_snapshot"] = {
            "timestamp": datetime.now().isoformat(),
            "health_checks": self.health_checks,
            "last_transitions": [t.to_log_entry() for t in self.transitions_log[-5:]]
        }
        
    def _entry_action_shutting_down(self):
        """Entry actions for ShuttingDown state"""
        logger.info("SYSTEM SHUTTING DOWN: Draining sessions, persisting state...")
        self.metadata["accepting_new"] = False
        self.metadata["shutdown_initiated"] = datetime.now().isoformat()
        
    def handle_event(self, event: SystemEvent, metadata: Dict[str, Any] = None) -> bool:
        """
        Handle system event and perform state transition if valid.
        Returns True if transition occurred, False otherwise.
        """
        old_state = self.state
        new_state = None
        guard_result = True
        
        # Define transitions
        if self.state == SystemState.OFF:
            if event == SystemEvent.BOOT_OK:
                # Start bootstrap process
                new_state = SystemState.BOOTSTRAPPING
                
        elif self.state == SystemState.BOOTSTRAPPING:
            if event == SystemEvent.BOOT_OK:
                new_state = SystemState.READY
            elif event == SystemEvent.BOOT_PARTIAL:
                new_state = SystemState.DEGRADED
            elif event == SystemEvent.BOOT_FAIL:
                new_state = SystemState.SYSTEM_ERROR
                
        elif self.state == SystemState.READY:
            if event == SystemEvent.HEALTH_FAIL:
                new_state = SystemState.SYSTEM_ERROR
            elif event == SystemEvent.SHUTDOWN_REQUEST:
                new_state = SystemState.SHUTTING_DOWN
                
        elif self.state == SystemState.DEGRADED:
            if event == SystemEvent.HEALTH_RECOVERED:
                new_state = SystemState.READY
            elif event == SystemEvent.HEALTH_WORSE:
                new_state = SystemState.SYSTEM_ERROR
            elif event == SystemEvent.SHUTDOWN_REQUEST:
                new_state = SystemState.SHUTTING_DOWN
                
        elif self.state == SystemState.SYSTEM_ERROR:
            if event == SystemEvent.RECOVER_OK:
                new_state = SystemState.BOOTSTRAPPING  # Full re-verify
            elif event == SystemEvent.SHUTDOWN_REQUEST:
                new_state = SystemState.SHUTTING_DOWN
                
        elif self.state == SystemState.SHUTTING_DOWN:
            if event == SystemEvent.SHUTDOWN_COMPLETE:
                new_state = SystemState.OFF
        
        # Execute transition if valid
        if new_state and new_state != old_state:
            self._log_transition(old_state, new_state, event, guard_result, metadata)
            self.state = new_state
            
            # Execute entry actions
            if new_state == SystemState.BOOTSTRAPPING:
                self._entry_action_bootstrapping()
            elif new_state == SystemState.READY:
                self._entry_action_ready()
            elif new_state == SystemState.DEGRADED:
                self._entry_action_degraded()
            elif new_state == SystemState.SYSTEM_ERROR:
                self._entry_action_system_error()
            elif new_state == SystemState.SHUTTING_DOWN:
                self._entry_action_shutting_down()
                
            return True
        
        return False
    
    def is_accepting_sessions(self) -> bool:
        """Check if system can accept new sessions"""
        return self.state in [SystemState.READY, SystemState.DEGRADED]


# ============================================================================
# SESSION STATE MACHINE
# ============================================================================

class SessionStateMachine:
    """
    Session layer state machine - manages individual user sessions with governance.
    
    Only operates when System layer is Ready or Degraded.
    """
    
    def __init__(self, session_id: str, user_id: Optional[str] = None):
        self.state = SessionState.SESSION_IDLE
        self.session_id = session_id
        self.user_id = user_id
        self.transitions_log: List[StateTransition] = []
        self.metadata: Dict[str, Any] = {
            "violation_count": 0,
            "task_substate": None,
            "conversation_turns": 0
        }
        self.previous_state: Optional[SessionState] = None
        
    def _log_transition(self, from_state: SessionState, to_state: SessionState, 
                       event: SessionEvent, guard_result: bool = True, 
                       metadata: Dict[str, Any] = None):
        """Log state transition"""
        transition = StateTransition(
            timestamp=datetime.now().isoformat(),
            from_state=from_state.value,
            to_state=to_state.value,
            event=event.value,
            guard_result=guard_result,
            correlation_id=self.session_id,
            metadata=metadata or {}
        )
        self.transitions_log.append(transition)
        logger.info(f"SESSION TRANSITION [{self.session_id}]: {transition.to_log_entry()}")
        
    def _guard_identity_verified(self) -> bool:
        """Guard: Check if identity is verified and policy loaded"""
        identity_verified = self.metadata.get("identity_verified", False)
        policy_loaded = self.metadata.get("policy_loaded", False)
        return identity_verified and policy_loaded
    
    def _guard_retry_allowed(self) -> bool:
        """Guard: Check if retry is allowed"""
        retry_count = self.metadata.get("retry_count", 0)
        return retry_count < 3
    
    def _entry_action_identity_lock_pending(self):
        """Entry actions for IdentityLockPending"""
        logger.info(f"SESSION {self.session_id}: Running identity pipeline...")
        # Placeholder: Run auth, account lookup, risk checks, policy loading
        self.metadata["identity_check_started"] = datetime.now().isoformat()
        
    def _entry_action_session_denied(self):
        """Entry actions for SessionDenied"""
        logger.warning(f"SESSION {self.session_id}: Session explicitly denied")
        reason = self.metadata.get("denial_reason", "Identity verification failed")
        self.metadata["denial_logged"] = datetime.now().isoformat()
        self.metadata["denial_reason"] = reason
        
    def _entry_action_opening_intent(self):
        """Entry actions for OpeningIntent"""
        logger.info(f"SESSION {self.session_id}: Classifying opening intent...")
        # Placeholder: Classify intent (support, build, legal, debug, etc.)
        self.metadata["intent_classification_started"] = datetime.now().isoformat()
        
    def _entry_action_conversational_flow(self):
        """Entry actions for ConversationalFlow"""
        logger.info(f"SESSION {self.session_id}: Initializing conversation state...")
        self.metadata["conversation_started"] = datetime.now().isoformat()
        self.metadata["conversation_turns"] = 0
        self.metadata["memory_window_active"] = True
        
    def _entry_action_task_mode(self):
        """Entry actions for TaskMode"""
        logger.info(f"SESSION {self.session_id}: Entering TaskMode - defining contract...")
        self.metadata["task_started"] = datetime.now().isoformat()
        self.metadata["task_substate"] = TaskSubstate.PLANNING.value
        self.metadata["task_contract"] = {
            "inputs": None,
            "outputs": None,
            "constraints": None,
            "success_criteria": None
        }
        
    def _entry_action_escalation_mode(self):
        """Entry actions for EscalationMode"""
        logger.warning(f"SESSION {self.session_id}: Escalating - preparing handoff...")
        self.metadata["escalation_started"] = datetime.now().isoformat()
        self.metadata["escalation_summary"] = {
            "context": "Preserved",
            "logs": [t.to_log_entry() for t in self.transitions_log[-5:]],
            "risk_flags": []
        }
        
    def _entry_action_governance_block(self):
        """Entry actions for GovernanceBlock"""
        logger.error(f"SESSION {self.session_id}: GOVERNANCE BLOCK - constitutional constraint enforced")
        self.metadata["violation_count"] += 1
        self.metadata["block_logged"] = datetime.now().isoformat()
        self.metadata["policy_reference"] = "Constitutional Article [TBD]"
        
    def _entry_action_error_recovery(self):
        """Entry actions for ErrorRecovery"""
        logger.warning(f"SESSION {self.session_id}: Attempting error recovery...")
        self.metadata["recovery_started"] = datetime.now().isoformat()
        self.metadata["error_context"] = {
            "timestamp": datetime.now().isoformat(),
            "previous_state": self.previous_state.value if self.previous_state else None
        }
        
    def _entry_action_session_terminated(self):
        """Entry actions for SessionTerminated"""
        logger.info(f"SESSION {self.session_id}: Session terminated - persisting logs...")
        self.metadata["terminated"] = datetime.now().isoformat()
        self.metadata["termination_reason"] = self.metadata.get("termination_reason", "User disconnect")
        
    def handle_event(self, event: SessionEvent, metadata: Dict[str, Any] = None) -> bool:
        """
        Handle session event and perform state transition if valid.
        Returns True if transition occurred, False otherwise.
        
        INVARIANTS:
        1. No TaskMode or ConversationalFlow without passing IdentityLockPending
        2. Any policy_violation must route through GovernanceBlock
        3. System layer SystemError/ShuttingDown forces SessionTerminated/SessionIdle
        """
        old_state = self.state
        new_state = None
        guard_result = True
        
        # Merge provided metadata
        if metadata:
            self.metadata.update(metadata)
        
        # Define transitions
        if self.state == SessionState.SESSION_IDLE:
            if event == SessionEvent.USER_CONNECT:
                new_state = SessionState.IDENTITY_LOCK_PENDING
                
        elif self.state == SessionState.IDENTITY_LOCK_PENDING:
            if event == SessionEvent.IDENTITY_OK:
                guard_result = self._guard_identity_verified()
                if guard_result:
                    new_state = SessionState.OPENING_INTENT
            elif event == SessionEvent.IDENTITY_FAIL:
                new_state = SessionState.SESSION_DENIED
            elif event == SessionEvent.TIMEOUT:
                new_state = SessionState.SESSION_IDLE
                
        elif self.state == SessionState.SESSION_DENIED:
            if event == SessionEvent.USER_DISCONNECT:
                new_state = SessionState.SESSION_IDLE
            elif event == SessionEvent.USER_RETRY:
                guard_result = self._guard_retry_allowed()
                if guard_result:
                    new_state = SessionState.IDENTITY_LOCK_PENDING
                    self.metadata["retry_count"] = self.metadata.get("retry_count", 0) + 1
                    
        elif self.state == SessionState.OPENING_INTENT:
            if event == SessionEvent.INTENT_CONVERSATIONAL:
                new_state = SessionState.CONVERSATIONAL_FLOW
            elif event == SessionEvent.INTENT_TASK:
                new_state = SessionState.TASK_MODE
            elif event == SessionEvent.INTENT_ESCALATION:
                new_state = SessionState.ESCALATION_MODE
            elif event == SessionEvent.INTENT_INVALID:
                new_state = SessionState.GOVERNANCE_BLOCK
                
        elif self.state == SessionState.CONVERSATIONAL_FLOW:
            if event == SessionEvent.TASK_REQUEST:
                new_state = SessionState.TASK_MODE
            elif event == SessionEvent.ESCALATION_NEEDED:
                new_state = SessionState.ESCALATION_MODE
            elif event == SessionEvent.POLICY_VIOLATION:
                new_state = SessionState.GOVERNANCE_BLOCK
            elif event in [SessionEvent.USER_DISCONNECT, SessionEvent.IDLE_TIMEOUT]:
                new_state = SessionState.SESSION_IDLE
                
        elif self.state == SessionState.TASK_MODE:
            if event == SessionEvent.TASK_COMPLETE:
                new_state = SessionState.CONVERSATIONAL_FLOW
            elif event == SessionEvent.TASK_FAIL_RECOVERABLE:
                new_state = SessionState.ERROR_RECOVERY
            elif event == SessionEvent.TASK_FAIL_FATAL:
                new_state = SessionState.ESCALATION_MODE
            elif event == SessionEvent.POLICY_VIOLATION:
                new_state = SessionState.GOVERNANCE_BLOCK
            elif event == SessionEvent.USER_ABORT:
                new_state = SessionState.CONVERSATIONAL_FLOW
                
        elif self.state == SessionState.ESCALATION_MODE:
            if event == SessionEvent.ESCALATION_ROUTED:
                new_state = SessionState.SESSION_IDLE
            elif event == SessionEvent.ESCALATION_REFUSED:
                new_state = SessionState.GOVERNANCE_BLOCK
            elif event == SessionEvent.USER_DISCONNECT:
                new_state = SessionState.SESSION_IDLE
                
        elif self.state == SessionState.GOVERNANCE_BLOCK:
            if event == SessionEvent.USER_ADJUSTS_REQUEST:
                # Return to appropriate state based on previous context
                if self.metadata.get("came_from") == "task":
                    new_state = SessionState.TASK_MODE
                else:
                    new_state = SessionState.CONVERSATIONAL_FLOW
            elif event == SessionEvent.REPEATED_VIOLATION:
                new_state = SessionState.SESSION_TERMINATED
                
        elif self.state == SessionState.ERROR_RECOVERY:
            if event == SessionEvent.RECOVER_OK:
                # Return to previous state
                new_state = self.previous_state if self.previous_state else SessionState.CONVERSATIONAL_FLOW
            elif event == SessionEvent.RECOVER_FAIL:
                new_state = SessionState.ESCALATION_MODE
                
        elif self.state == SessionState.SESSION_TERMINATED:
            if event in [SessionEvent.USER_DISCONNECT, SessionEvent.TIMEOUT]:
                new_state = SessionState.SESSION_IDLE
        
        # Execute transition if valid
        if new_state and new_state != old_state:
            self._log_transition(old_state, new_state, event, guard_result, metadata)
            self.previous_state = old_state
            self.state = new_state
            
            # Execute entry actions
            if new_state == SessionState.IDENTITY_LOCK_PENDING:
                self._entry_action_identity_lock_pending()
            elif new_state == SessionState.SESSION_DENIED:
                self._entry_action_session_denied()
            elif new_state == SessionState.OPENING_INTENT:
                self._entry_action_opening_intent()
            elif new_state == SessionState.CONVERSATIONAL_FLOW:
                self._entry_action_conversational_flow()
            elif new_state == SessionState.TASK_MODE:
                self._entry_action_task_mode()
            elif new_state == SessionState.ESCALATION_MODE:
                self._entry_action_escalation_mode()
            elif new_state == SessionState.GOVERNANCE_BLOCK:
                self._entry_action_governance_block()
            elif new_state == SessionState.ERROR_RECOVERY:
                self._entry_action_error_recovery()
            elif new_state == SessionState.SESSION_TERMINATED:
                self._entry_action_session_terminated()
                
            return True
        
        return False
    
    def can_accept_work(self) -> bool:
        """Check if session can accept work (conversation or tasks)"""
        return self.state in [
            SessionState.CONVERSATIONAL_FLOW,
            SessionState.TASK_MODE,
            SessionState.OPENING_INTENT
        ]


# ============================================================================
# INTEGRATED STATE MANAGER
# ============================================================================

class AlanStateManager:
    """
    Integrated state manager coordinating System and Session layers.
    
    Enforces invariants:
    - Session layer only operates when System is Ready/Degraded
    - System failures cascade to all active sessions
    - All transitions logged for governance audit
    - Sessions persisted for crash recovery (Phase 1A Step 2)
    """
    
    def __init__(self, enable_persistence: bool = True):
        self.system = SystemStateMachine(correlation_id="alan-system-001")
        self.sessions: Dict[str, SessionStateMachine] = {}
        self.session_counter = 0
        
        # Phase 1A Step 2: Session Persistence
        self.enable_persistence = enable_persistence
        self.persistence = None
        
        if enable_persistence:
            try:
                from session_persistence import get_persistence_manager
                self.persistence = get_persistence_manager()
                logger.info("Session persistence enabled")
            except Exception as e:
                logger.warning(f"Session persistence unavailable: {e}")
                self.enable_persistence = False
        
    def bootstrap(self) -> bool:
        """Bootstrap Alan from cold start"""
        logger.info("=== ALAN BOOTSTRAP INITIATED ===")
        
        # Start bootstrap
        self.system.handle_event(SystemEvent.BOOT_OK)
        
        # Simulate checks (in production, these would be real health checks)
        time.sleep(0.1)
        
        # Complete bootstrap
        success = self.system.handle_event(SystemEvent.BOOT_OK)
        
        if success:
            logger.info("=== ALAN BOOTSTRAP COMPLETE - SYSTEM READY ===")
        else:
            logger.error("=== ALAN BOOTSTRAP FAILED ===")
            
        return success
    
    def create_session(self, user_id: Optional[str] = None) -> Optional[str]:
        """
        Create new session if system is accepting.
        Returns session_id or None if system not ready.
        """
        if not self.system.is_accepting_sessions():
            logger.warning("Cannot create session - system not ready")
            return None
        
        self.session_counter += 1
        session_id = f"session-{self.session_counter:04d}"
        self.sessions[session_id] = SessionStateMachine(session_id, user_id)
        
        logger.info(f"Session created: {session_id}")
        return session_id
    
    def handle_session_event(self, session_id: str, event: SessionEvent, 
                           metadata: Dict[str, Any] = None) -> bool:
        """Handle event for specific session with auto-save"""
        if session_id not in self.sessions:
            logger.error(f"Session not found: {session_id}")
            return False
        
        # Get state before transition
        session = self.sessions[session_id]
        old_state = session.state
        
        # Handle event
        success = session.handle_event(event, metadata)
        
        # Auto-save session after state transition (Phase 1A Step 2)
        if success and self.persistence:
            try:
                self.persistence.save_session(session)
                
                # Log state transition
                if old_state != session.state:
                    self.persistence.log_session_event(
                        session_id,
                        "state_transition",
                        from_state=old_state.value,
                        to_state=session.state.value,
                        details={"event": event.value}
                    )
            except Exception as e:
                logger.error(f"Failed to persist session {session_id}: {e}")
        
        return success
    
    def recover_sessions(self) -> int:
        """
        Recover active sessions after system restart.
        
        Called after bootstrap to restore sessions that were active
        when the system crashed or was shut down.
        
        Returns:
            Number of sessions recovered
        """
        if not self.persistence:
            logger.warning("Session recovery unavailable - persistence disabled")
            return 0
        
        try:
            active_sessions = self.persistence.recover_active_sessions()
            
            recovered = 0
            for session_data in active_sessions:
                try:
                    # Recreate session state machine
                    session_id = session_data['session_id']
                    user_id = session_data['user_id']
                    
                    # Parse state
                    try:
                        state = SessionState(session_data['state'])
                    except ValueError:
                        logger.warning(f"Invalid state for session {session_id}: {session_data['state']}")
                        continue
                    
                    # Create session machine
                    session = SessionStateMachine(session_id, user_id)
                    
                    # Restore state and metadata
                    session.state = state
                    session.metadata = session_data['metadata']
                    
                    # Add to active sessions
                    self.sessions[session_id] = session
                    
                    recovered += 1
                    logger.info(f"Recovered session {session_id} in state {state.value}")
                    
                except Exception as e:
                    logger.error(f"Failed to recover session {session_data.get('session_id')}: {e}")
            
            logger.info(f"Session recovery complete: {recovered}/{len(active_sessions)} sessions restored")
            return recovered
            
        except Exception as e:
            logger.error(f"Session recovery failed: {e}")
            return 0
    
    def handle_system_event(self, event: SystemEvent, metadata: Dict[str, Any] = None) -> bool:
        """
        Handle system event with cascade to sessions.
        
        If system goes to SystemError or ShuttingDown, all sessions are terminated.
        """
        success = self.system.handle_event(event, metadata)
        
        # Cascade to sessions if system failure
        if self.system.state in [SystemState.SYSTEM_ERROR, SystemState.SHUTTING_DOWN]:
            logger.warning("System failure - terminating all sessions")
            for session_id in list(self.sessions.keys()):
                self.sessions[session_id].handle_event(
                    SessionEvent.USER_DISCONNECT,
                    {"reason": f"System {self.system.state.value}"}
                )
        
        return success
    
    def get_session_state(self, session_id: str) -> Optional[SessionState]:
        """Get current state of session"""
        session = self.sessions.get(session_id)
        return session.state if session else None
    
    def get_system_state(self) -> SystemState:
        """Get current system state"""
        return self.system.state
    
    def get_audit_log(self, session_id: Optional[str] = None) -> List[str]:
        """
        Get audit log of transitions.
        If session_id provided, returns session log.
        Otherwise returns system log.
        """
        if session_id:
            session = self.sessions.get(session_id)
            if session:
                return [t.to_log_entry() for t in session.transitions_log]
            return []
        else:
            return [t.to_log_entry() for t in self.system.transitions_log]


# ============================================================================
# USAGE EXAMPLE
# ============================================================================

if __name__ == "__main__":
    # Initialize Alan State Manager
    manager = AlanStateManager()
    
    # Bootstrap system
    manager.bootstrap()
    
    # Create session
    session_id = manager.create_session(user_id="tim-founder")
    
    # Simulate session flow
    if session_id:
        # User connects
        manager.handle_session_event(session_id, SessionEvent.USER_CONNECT)
        
        # Identity verified
        manager.handle_session_event(
            session_id, 
            SessionEvent.IDENTITY_OK,
            {"identity_verified": True, "policy_loaded": True}
        )
        
        # Opening intent classified
        manager.handle_session_event(session_id, SessionEvent.INTENT_CONVERSATIONAL)
        
        # User makes task request
        manager.handle_session_event(session_id, SessionEvent.TASK_REQUEST)
        
        # Task completes
        manager.handle_session_event(session_id, SessionEvent.TASK_COMPLETE)
        
        # User disconnects
        manager.handle_session_event(session_id, SessionEvent.USER_DISCONNECT)
        
    # Print audit log
    print("\n=== SYSTEM AUDIT LOG ===")
    for log_entry in manager.get_audit_log():
        print(log_entry)
    
    print(f"\n=== SESSION {session_id} AUDIT LOG ===")
    for log_entry in manager.get_audit_log(session_id):
        print(log_entry)
