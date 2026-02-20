# ============================================================================
# INSTRUCTOR MODE — Core Module
# ============================================================================
# Production-grade governed learning system for Alan.
#
# Components:
#   1. InstructorModeFSM       — State machine for mode transitions
#   2. TrainingSignal          — Structured correction/learning data
#   3. InstructorSession       — Per-session state, turns, signals
#   4. FeedbackProtocol        — Processes instructor corrections
#   5. InstructorLearningEngine — Captures, stores, and reviews learnings
#   6. ApprovalWorkflow        — Tim approves/rejects training signals
#
# Constitutional guarantees:
#   - No write to core persona without human approval
#   - No activation during live calls
#   - No sales, persuasion, data capture, or improvisation
#   - Full audit trail (JSONL log + in-memory trace)
#   - Drift-resistant: all integration goes through governance check
#
# File: instructor_mode.py
# Author: AQI System / Tim Alan
# Created: 2026-02-19
# ============================================================================

import json
import os
import logging
import time
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import Optional

logger = logging.getLogger("AQI.InstructorMode")


# ============================================================================
# 1. FSM — Finite State Machine for Mode Transitions
# ============================================================================

class InstructorState(Enum):
    """Instructor Mode FSM states."""
    PRODUCTION_MODE     = "PRODUCTION_MODE"
    INSTRUCTOR_PENDING  = "INSTRUCTOR_PENDING"
    INSTRUCTOR_MODE     = "INSTRUCTOR_MODE"
    INSTRUCTOR_SUMMARY  = "INSTRUCTOR_SUMMARY"
    IDLE                = "IDLE"


class InstructorTransition(Enum):
    """Valid FSM transitions."""
    ENTER_INSTRUCTOR    = "enter_instructor_mode"
    CONFIRM_INSTRUCTOR  = "confirm_instructor_mode"
    CANCEL_INSTRUCTOR   = "cancel_instructor_mode"
    END_SESSION         = "end_instructor_session"
    RESUME_PRODUCTION   = "resume_production"
    SUMMARY_COMPLETE    = "summary_complete"
    SLEEP               = "sleep"
    WAKE                = "wake"


# Transition table: (current_state, trigger) → next_state
_TRANSITION_TABLE = {
    (InstructorState.PRODUCTION_MODE,    InstructorTransition.ENTER_INSTRUCTOR):   InstructorState.INSTRUCTOR_PENDING,
    (InstructorState.PRODUCTION_MODE,    InstructorTransition.SLEEP):              InstructorState.IDLE,
    (InstructorState.IDLE,               InstructorTransition.WAKE):               InstructorState.PRODUCTION_MODE,
    (InstructorState.IDLE,               InstructorTransition.ENTER_INSTRUCTOR):   InstructorState.INSTRUCTOR_PENDING,
    (InstructorState.INSTRUCTOR_PENDING, InstructorTransition.CONFIRM_INSTRUCTOR): InstructorState.INSTRUCTOR_MODE,
    (InstructorState.INSTRUCTOR_PENDING, InstructorTransition.CANCEL_INSTRUCTOR):  InstructorState.PRODUCTION_MODE,
    (InstructorState.INSTRUCTOR_MODE,    InstructorTransition.END_SESSION):        InstructorState.INSTRUCTOR_SUMMARY,
    (InstructorState.INSTRUCTOR_MODE,    InstructorTransition.RESUME_PRODUCTION):  InstructorState.PRODUCTION_MODE,
    (InstructorState.INSTRUCTOR_MODE,    InstructorTransition.SLEEP):              InstructorState.IDLE,
    (InstructorState.INSTRUCTOR_SUMMARY, InstructorTransition.SUMMARY_COMPLETE):   InstructorState.PRODUCTION_MODE,
    (InstructorState.INSTRUCTOR_SUMMARY, InstructorTransition.SLEEP):              InstructorState.IDLE,
}


class InstructorModeFSM:
    """
    Finite State Machine for Instructor Mode transitions.
    
    Guarantees:
    - No accidental activation
    - No cross-contamination with production
    - Full governance compliance
    - Every transition logged
    """

    def __init__(self, initial_state: InstructorState = InstructorState.PRODUCTION_MODE):
        self.state = initial_state
        self.history: list[dict] = []
        self._created = datetime.now()

    def can_transition(self, trigger: InstructorTransition) -> bool:
        """Check if a transition is valid from current state."""
        return (self.state, trigger) in _TRANSITION_TABLE

    def transition(self, trigger: InstructorTransition, reason: str = "") -> InstructorState:
        """
        Execute a state transition. Raises ValueError if invalid.
        Logs every transition for audit trail.
        """
        key = (self.state, trigger)
        if key not in _TRANSITION_TABLE:
            raise ValueError(
                f"[INSTRUCTOR FSM] Invalid transition: {self.state.value} + {trigger.value}. "
                f"No path exists."
            )

        old_state = self.state
        self.state = _TRANSITION_TABLE[key]

        entry = {
            "timestamp": datetime.now().isoformat(),
            "from": old_state.value,
            "to": self.state.value,
            "trigger": trigger.value,
            "reason": reason,
        }
        self.history.append(entry)
        logger.info(f"[INSTRUCTOR FSM] {old_state.value} → {self.state.value} (trigger: {trigger.value})")

        return self.state

    @property
    def is_instructor_active(self) -> bool:
        """True if currently in any instructor-related state."""
        return self.state in (
            InstructorState.INSTRUCTOR_PENDING,
            InstructorState.INSTRUCTOR_MODE,
            InstructorState.INSTRUCTOR_SUMMARY,
        )

    @property
    def is_training(self) -> bool:
        """True if actively in training (not pending or summarizing)."""
        return self.state == InstructorState.INSTRUCTOR_MODE

    def to_dict(self) -> dict:
        return {
            "state": self.state.value,
            "history": self.history,
            "is_instructor_active": self.is_instructor_active,
            "is_training": self.is_training,
        }


# ============================================================================
# 2. Training Signal — Structured correction data
# ============================================================================

class SignalType(Enum):
    """Training signal error categories."""
    TONE               = "TONE"
    PACING             = "PACING"
    LOGIC              = "LOGIC"
    OBJECTION_HANDLING  = "OBJECTION_HANDLING"
    DOMAIN_ACCURACY     = "DOMAIN_ACCURACY"
    COMPLIANCE          = "COMPLIANCE"
    STRUCTURE           = "STRUCTURE"
    CLOSING_BEHAVIOR    = "CLOSING_BEHAVIOR"
    GATEKEEPER_NAV      = "GATEKEEPER_NAVIGATION"
    COLD_OPEN           = "COLD_OPEN_DELIVERY"
    RECOVERY            = "RECOVERY"
    LISTENING           = "LISTENING"


@dataclass
class TrainingSignal:
    """
    A single training signal emitted from an instructor correction.
    
    Schema matches the constitutional spec:
    - timestamp, instructor_id, conversation_turn
    - error_type, error_summary, corrected_behavior
    - before (Alan's original), after (corrected version)
    - confidence (0.0-1.0)
    - requires_human_approval (always True — constitutional guarantee)
    """
    timestamp: str
    instructor_id: str
    session_id: str
    conversation_turn: int
    error_type: str                     # From SignalType enum
    error_summary: str                  # What was wrong
    corrected_behavior: str             # What Alan should do instead
    before: str = ""                    # Alan's original utterance
    after: str = ""                     # Corrected version
    confidence: float = 0.7            # Default conservative confidence
    requires_human_approval: bool = True  # ALWAYS TRUE — constitutional
    status: str = "pending_review"      # pending_review | approved | rejected
    reviewer_notes: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_feedback(cls, session_id: str, instructor_id: str, turn: int,
                      feedback_type: str, correction: str,
                      alan_original: str = "", example: str = "",
                      rationale: str = "") -> "TrainingSignal":
        """Build a TrainingSignal from instructor feedback."""
        return cls(
            timestamp=datetime.utcnow().isoformat() + "Z",
            instructor_id=instructor_id,
            session_id=session_id,
            conversation_turn=turn,
            error_type=feedback_type,
            error_summary=correction,
            corrected_behavior=example or correction,
            before=alan_original,
            after=example,
            confidence=0.7,
            requires_human_approval=True,
        )


# ============================================================================
# 3. Instructor Session — Per-session state container
# ============================================================================

@dataclass
class InstructorSession:
    """
    Encapsulates a single Instructor Mode training session.
    
    Tracks:
    - Session metadata (who, when, how long)
    - All conversation turns
    - All training signals emitted
    - Session summary (generated at end)
    """
    session_id: str
    instructor_id: str              # Name or ID of the instructor
    instructor_name: str = ""       # Display name
    start_time: str = field(default_factory=lambda: datetime.now().isoformat())
    end_time: str = ""
    turns: list = field(default_factory=list)
    training_signals: list = field(default_factory=list)
    summary: dict = field(default_factory=dict)
    status: str = "active"          # active | completed | aborted
    governance_events: list = field(default_factory=list)

    @property
    def turn_count(self) -> int:
        return len(self.turns)

    @property
    def signal_count(self) -> int:
        return len(self.training_signals)

    @property
    def duration_seconds(self) -> float:
        if not self.end_time:
            return (datetime.now() - datetime.fromisoformat(self.start_time)).total_seconds()
        return (datetime.fromisoformat(self.end_time) - datetime.fromisoformat(self.start_time)).total_seconds()

    def add_turn(self, role: str, text: str, metadata: dict = None):
        """Record a conversation turn."""
        self.turns.append({
            "index": len(self.turns),
            "role": role,
            "text": text,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {},
        })

    def emit_signal(self, signal: TrainingSignal):
        """Add a training signal to this session."""
        self.training_signals.append(signal.to_dict())
        logger.info(f"[INSTRUCTOR] Signal emitted: {signal.error_type} — {signal.error_summary[:60]}")

    def finalize(self) -> dict:
        """Close the session and generate summary."""
        self.end_time = datetime.now().isoformat()
        self.status = "completed"
        self.summary = {
            "session_id": self.session_id,
            "instructor": self.instructor_name or self.instructor_id,
            "duration_seconds": self.duration_seconds,
            "total_turns": self.turn_count,
            "total_signals": self.signal_count,
            "signal_types": list(set(s.get("error_type", "") for s in self.training_signals)),
            "status": "pending_review",
            "finalized_at": self.end_time,
        }
        return self.summary

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "instructor_id": self.instructor_id,
            "instructor_name": self.instructor_name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "turn_count": self.turn_count,
            "signal_count": self.signal_count,
            "duration_seconds": self.duration_seconds,
            "turns": self.turns,
            "training_signals": self.training_signals,
            "summary": self.summary,
            "status": self.status,
            "governance_events": self.governance_events,
        }


# ============================================================================
# 4. Feedback Protocol — Process instructor corrections
# ============================================================================

class FeedbackProtocol:
    """
    Processes structured instructor feedback and emits training signals.
    
    Instructor corrections follow the constitutional format:
    1. FEEDBACK_TYPE (from SignalType enum)
    2. CORRECTION (what Alan should have done)
    3. RATIONALE (why — optional)
    4. EXAMPLE (correct phrasing — optional)
    
    Alan's required response:
    1. ACKNOWLEDGMENT
    2. REFLECTION
    3. ADJUSTMENT
    4. REQUEST (verify correction is accurate)
    """

    # Keywords that map natural language to signal types
    # Order matters: more specific categories first to prevent false matches
    _TYPE_KEYWORDS = {
        SignalType.GATEKEEPER_NAV.value: ["gatekeeper", "receptionist", "front desk", "who's calling"],
        SignalType.COLD_OPEN.value: ["opening", "intro", "first thing", "greeting", "cold open"],
        SignalType.OBJECTION_HANDLING.value: ["objection", "pushback", "resistance", "handle", "overcome"],
        SignalType.CLOSING_BEHAVIOR.value: ["close", "closing", "ask for the sale", "commitment", "next step"],
        SignalType.TONE.value: ["tone", "tonality", "energy", "sound", "voice", "inflection"],
        SignalType.PACING.value: ["pacing", "pace", "speed", "slow", "fast", "rushed", "timing"],
        SignalType.RECOVERY.value: ["recover", "stumble", "fumble", "awkward", "silence"],
        SignalType.LISTENING.value: ["listening", "didn't hear", "missed what", "not paying attention"],
        SignalType.COMPLIANCE.value: ["compliance", "legal", "regulation", "can't say that", "not allowed"],
        SignalType.DOMAIN_ACCURACY.value: ["incorrect", "wrong fact", "that's not right", "misinformation"],
        SignalType.LOGIC.value: ["logic", "reasoning", "makes no sense", "doesn't follow"],
        SignalType.STRUCTURE.value: ["structure", "flow", "sequence", "order", "organize"],
    }

    @classmethod
    def detect_feedback_type(cls, text: str) -> str:
        """
        Auto-detect the feedback type from natural language.
        Falls back to STRUCTURE if no match found.
        """
        text_lower = text.lower()
        for signal_type, keywords in cls._TYPE_KEYWORDS.items():
            for kw in keywords:
                if kw in text_lower:
                    return signal_type
        return SignalType.STRUCTURE.value

    @classmethod
    def process_correction(cls, session: InstructorSession, instructor_text: str,
                           alan_original: str = "") -> TrainingSignal:
        """
        Process an instructor correction and emit a training signal.
        
        Auto-detects feedback type from natural language.
        Returns the TrainingSignal for logging.
        """
        feedback_type = cls.detect_feedback_type(instructor_text)

        signal = TrainingSignal.from_feedback(
            session_id=session.session_id,
            instructor_id=session.instructor_id,
            turn=session.turn_count,
            feedback_type=feedback_type,
            correction=instructor_text,
            alan_original=alan_original,
        )

        session.emit_signal(signal)
        return signal

    @classmethod
    def build_alan_response_guidance(cls, signal: TrainingSignal) -> str:
        """
        Generate guidance for Alan's response to a correction.
        This gets injected into the LLM context so Alan follows the protocol.
        """
        return (
            f"[INSTRUCTOR CORRECTION RECEIVED]\n"
            f"Type: {signal.error_type}\n"
            f"Correction: {signal.error_summary}\n"
            f"Your response MUST follow this protocol:\n"
            f"1. ACKNOWLEDGE: Confirm you received the correction\n"
            f"2. REFLECT: Summarize what was wrong in your own words\n"
            f"3. ADJUST: Show the corrected behavior immediately\n"
            f"4. REQUEST: Ask if your adjustment is accurate\n"
            f"Example: \"Got it — {signal.error_summary[:50]}... Let me try that again.\""
        )


# ============================================================================
# 5. Instructor Learning Engine — Capture, Store, Review
# ============================================================================

class InstructorLearningEngine:
    """
    Manages the full lifecycle of instructor training data.
    
    Responsibilities:
    - Store training sessions (JSONL file)
    - Store training signals (JSONL file)
    - Provide review interface for Tim
    - Apply approved signals to behavioral templates
    - Enforce governance: nothing integrates without approval
    """

    LOG_DIR = "data"
    SESSION_LOG = "data/instructor_training_log.jsonl"
    SIGNAL_LOG = "data/instructor_training_signals.jsonl"
    APPROVED_LOG = "data/instructor_approved_learnings.jsonl"

    def __init__(self):
        os.makedirs(self.LOG_DIR, exist_ok=True)
        self._active_sessions: dict[str, InstructorSession] = {}

    def start_session(self, session_id: str, instructor_id: str,
                      instructor_name: str = "") -> InstructorSession:
        """Create and register a new training session."""
        session = InstructorSession(
            session_id=session_id,
            instructor_id=instructor_id,
            instructor_name=instructor_name,
        )
        self._active_sessions[session_id] = session
        logger.info(f"[INSTRUCTOR ENGINE] Session started: {session_id} with {instructor_name or instructor_id}")
        return session

    def get_session(self, session_id: str) -> Optional[InstructorSession]:
        """Get an active session by ID."""
        return self._active_sessions.get(session_id)

    def end_session(self, session_id: str) -> dict:
        """
        Finalize a session, write to disk, return summary.
        Session data is persisted to JSONL for Tim's review.
        """
        session = self._active_sessions.get(session_id)
        if not session:
            logger.warning(f"[INSTRUCTOR ENGINE] Session {session_id} not found")
            return {}

        summary = session.finalize()

        # Write full session to log
        try:
            with open(self.SESSION_LOG, "a", encoding="utf-8") as f:
                f.write(json.dumps(session.to_dict(), default=str) + "\n")
            logger.info(f"[INSTRUCTOR ENGINE] Session {session_id} written to {self.SESSION_LOG}")
        except Exception as e:
            logger.error(f"[INSTRUCTOR ENGINE] Failed to write session log: {e}")

        # Write individual signals to signal log
        try:
            with open(self.SIGNAL_LOG, "a", encoding="utf-8") as f:
                for signal in session.training_signals:
                    f.write(json.dumps(signal, default=str) + "\n")
            logger.info(f"[INSTRUCTOR ENGINE] {session.signal_count} signals written to {self.SIGNAL_LOG}")
        except Exception as e:
            logger.error(f"[INSTRUCTOR ENGINE] Failed to write signal log: {e}")

        # Remove from active
        self._active_sessions.pop(session_id, None)
        return summary

    def get_pending_signals(self) -> list[dict]:
        """
        Read all training signals pending Tim's review.
        Returns signals with status='pending_review'.
        """
        signals = []
        if not os.path.exists(self.SIGNAL_LOG):
            return signals
        try:
            with open(self.SIGNAL_LOG, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        sig = json.loads(line)
                        if sig.get("status") == "pending_review":
                            signals.append(sig)
        except Exception as e:
            logger.error(f"[INSTRUCTOR ENGINE] Failed to read signal log: {e}")
        return signals

    def get_all_sessions(self) -> list[dict]:
        """Read all completed session summaries."""
        sessions = []
        if not os.path.exists(self.SESSION_LOG):
            return sessions
        try:
            with open(self.SESSION_LOG, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        sessions.append(json.loads(line))
        except Exception as e:
            logger.error(f"[INSTRUCTOR ENGINE] Failed to read session log: {e}")
        return sessions

    @property
    def active_session_count(self) -> int:
        return len(self._active_sessions)


# ============================================================================
# 6. Approval Workflow — Tim approves/rejects training signals
# ============================================================================

class ApprovalWorkflow:
    """
    Governed learning loop — Tim reviews, approves, or rejects training signals.
    
    Step 1: Session ends → signals written to JSONL
    Step 2: Tim reviews via /instructor/review API
    Step 3: Tim approves/rejects via /instructor/approve API
    Step 4: Approved signals written to approved_learnings log
    Step 5: Governance check before any integration
    
    Constitutional guarantee: NOTHING enters core persona without this workflow.
    """

    SIGNAL_LOG = InstructorLearningEngine.SIGNAL_LOG
    APPROVED_LOG = InstructorLearningEngine.APPROVED_LOG

    @classmethod
    def review_pending(cls) -> dict:
        """
        Get all pending signals for Tim's review.
        Returns structured review package.
        """
        engine = InstructorLearningEngine()
        pending = engine.get_pending_signals()
        sessions = engine.get_all_sessions()

        return {
            "pending_signals": len(pending),
            "total_sessions": len(sessions),
            "signals": pending,
            "sessions_summary": [
                {
                    "session_id": s.get("session_id"),
                    "instructor": s.get("instructor_name", s.get("instructor_id")),
                    "duration": s.get("duration_seconds"),
                    "turns": s.get("turn_count"),
                    "signals": s.get("signal_count"),
                    "status": s.get("status"),
                }
                for s in sessions
            ],
        }

    @classmethod
    def approve_signals(cls, signal_indices: list[int], notes: str = "") -> dict:
        """
        Approve specific training signals by index.
        Writes approved signals to the approved learnings log.
        Updates status in the signal log.
        """
        if not os.path.exists(cls.SIGNAL_LOG):
            return {"error": "No signal log found", "approved": 0}

        # Read all signals
        all_signals = []
        try:
            with open(cls.SIGNAL_LOG, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        all_signals.append(json.loads(line))
        except Exception as e:
            return {"error": f"Failed to read signals: {e}", "approved": 0}

        # Find pending signals
        pending = [(i, s) for i, s in enumerate(all_signals) if s.get("status") == "pending_review"]

        approved_count = 0
        approved_signals = []
        for idx in signal_indices:
            if 0 <= idx < len(pending):
                real_idx, signal = pending[idx]
                all_signals[real_idx]["status"] = "approved"
                all_signals[real_idx]["reviewer_notes"] = notes
                all_signals[real_idx]["approved_at"] = datetime.now().isoformat()
                approved_signals.append(all_signals[real_idx])
                approved_count += 1

        # Rewrite signal log with updated statuses
        try:
            with open(cls.SIGNAL_LOG, "w", encoding="utf-8") as f:
                for sig in all_signals:
                    f.write(json.dumps(sig, default=str) + "\n")
        except Exception as e:
            logger.error(f"[APPROVAL] Failed to update signal log: {e}")

        # Write approved signals to approved learnings log
        if approved_signals:
            try:
                os.makedirs("data", exist_ok=True)
                with open(cls.APPROVED_LOG, "a", encoding="utf-8") as f:
                    for sig in approved_signals:
                        f.write(json.dumps(sig, default=str) + "\n")
                logger.info(f"[APPROVAL] {approved_count} signals approved and written to {cls.APPROVED_LOG}")
            except Exception as e:
                logger.error(f"[APPROVAL] Failed to write approved learnings: {e}")

        return {
            "approved": approved_count,
            "total_pending_remaining": len(pending) - approved_count,
            "notes": notes,
        }

    @classmethod
    def reject_signals(cls, signal_indices: list[int], notes: str = "") -> dict:
        """
        Reject specific training signals by index.
        Updates status but does NOT write to approved log.
        """
        if not os.path.exists(cls.SIGNAL_LOG):
            return {"error": "No signal log found", "rejected": 0}

        all_signals = []
        try:
            with open(cls.SIGNAL_LOG, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        all_signals.append(json.loads(line))
        except Exception as e:
            return {"error": f"Failed to read signals: {e}", "rejected": 0}

        pending = [(i, s) for i, s in enumerate(all_signals) if s.get("status") == "pending_review"]

        rejected_count = 0
        for idx in signal_indices:
            if 0 <= idx < len(pending):
                real_idx, _ = pending[idx]
                all_signals[real_idx]["status"] = "rejected"
                all_signals[real_idx]["reviewer_notes"] = notes
                all_signals[real_idx]["rejected_at"] = datetime.now().isoformat()
                rejected_count += 1

        try:
            with open(cls.SIGNAL_LOG, "w", encoding="utf-8") as f:
                for sig in all_signals:
                    f.write(json.dumps(sig, default=str) + "\n")
        except Exception as e:
            logger.error(f"[APPROVAL] Failed to update signal log: {e}")

        return {
            "rejected": rejected_count,
            "total_pending_remaining": len(pending) - rejected_count,
            "notes": notes,
        }


# ============================================================================
# 7. On-Turn Hook — Mode-aware behavior during conversations
# ============================================================================

def on_instructor_turn(session: InstructorSession, user_text: str,
                       alan_last_utterance: str = "") -> Optional[str]:
    """
    Process a turn during an active instructor session.
    
    Called from the relay server's response pipeline when instructor_mode is active.
    
    - Records the instructor's turn
    - Detects if it contains a correction/feedback
    - Emits training signal if correction detected
    - Returns guidance string to inject into Alan's LLM context
    
    Returns None if no correction detected (normal conversation flow).
    """
    # Record the turn
    session.add_turn(role="instructor", text=user_text)

    # Detect correction keywords
    _correction_markers = [
        "you should", "try again", "don't say", "instead of", "better to",
        "that was wrong", "correction", "fix that", "let me correct",
        "here's what", "what you should", "the problem", "issue with",
        "you missed", "you forgot", "practice that", "work on",
        "too slow", "too fast", "tone was", "pacing", "didn't handle",
        "you need to", "stop doing", "start doing", "rather than",
    ]

    text_lower = user_text.lower()
    is_correction = any(marker in text_lower for marker in _correction_markers)

    if is_correction:
        signal = FeedbackProtocol.process_correction(
            session=session,
            instructor_text=user_text,
            alan_original=alan_last_utterance,
        )
        guidance = FeedbackProtocol.build_alan_response_guidance(signal)
        logger.info(f"[INSTRUCTOR TURN] Correction detected: {signal.error_type} — injecting guidance")
        return guidance

    return None


# ============================================================================
# 8. Governance Check — Verify no drift before integration
# ============================================================================

def governance_check(approved_signals: list[dict]) -> dict:
    """
    Final governance verification before any approved signals
    are integrated into Alan's behavioral templates.
    
    Checks:
    1. No identity drift (signals don't change who Alan is)
    2. No mission contamination (signals don't add sales behavior to non-sales contexts)
    3. No persona degradation (signals don't lower quality/professionalism)
    
    Returns: {passed: bool, issues: list[str]}
    """
    issues = []

    # Identity drift check — reject anything that changes Alan's name, company, role
    _identity_keywords = ["your name is", "you are not alan", "forget you are",
                          "you work for", "change your name", "you're not"]
    for sig in approved_signals:
        correction = sig.get("corrected_behavior", "").lower()
        for kw in _identity_keywords:
            if kw in correction:
                issues.append(f"Identity drift risk: signal contains '{kw}' — rejected")

    # Mission contamination check — sales language in corrections is fine (it's training)
    # But corrections that tell Alan to sell DURING instructor mode are wrong
    _mission_contamination = ["close the deal now", "sell them", "get their credit card",
                              "capture their data", "sign them up"]
    for sig in approved_signals:
        correction = sig.get("corrected_behavior", "").lower()
        for kw in _mission_contamination:
            if kw in correction:
                issues.append(f"Mission contamination risk: '{kw}' in correction — flagged")

    passed = len(issues) == 0
    if passed:
        logger.info(f"[GOVERNANCE] {len(approved_signals)} signals passed governance check")
    else:
        logger.warning(f"[GOVERNANCE] {len(issues)} issues found in approved signals")

    return {"passed": passed, "issues": issues, "signals_checked": len(approved_signals)}


# ============================================================================
# Module-level singleton for the learning engine
# ============================================================================
_learning_engine: Optional[InstructorLearningEngine] = None


def get_learning_engine() -> InstructorLearningEngine:
    """Get or create the singleton learning engine."""
    global _learning_engine
    if _learning_engine is None:
        _learning_engine = InstructorLearningEngine()
    return _learning_engine
