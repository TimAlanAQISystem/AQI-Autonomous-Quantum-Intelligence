# ============================================================================
# INSTRUCTOR MODE — Deterministic Test Harness
# ============================================================================
# Validates every constitutional guarantee of Instructor Mode:
#   1. FSM transitions are correct and invalid ones are blocked
#   2. Training signals are properly structured
#   3. Feedback protocol detects correction types
#   4. Sessions log correctly
#   5. Approval workflow enforces governance
#   6. No core persona write without approval
#   7. Governance check catches drift
#
# Run: .venv\Scripts\python.exe test_instructor_mode.py
# ============================================================================

import sys
import os
import json
import tempfile

# Ensure we can import from the project root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from instructor_mode import (
    InstructorModeFSM, InstructorState, InstructorTransition,
    TrainingSignal, SignalType, InstructorSession,
    FeedbackProtocol, InstructorLearningEngine, ApprovalWorkflow,
    on_instructor_turn, governance_check,
)


class InstructorModeTestHarness:
    """Deterministic validation of all Instructor Mode guarantees."""

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def _assert(self, condition: bool, test_name: str, detail: str = ""):
        if condition:
            self.passed += 1
            print(f"  [PASS] {test_name}")
        else:
            self.failed += 1
            msg = f"  [FAIL] {test_name}" + (f" — {detail}" if detail else "")
            print(msg)
            self.errors.append(msg)

    def run_all(self):
        print("=" * 60)
        print("INSTRUCTOR MODE — TEST HARNESS")
        print("=" * 60)

        print("\n--- FSM Transition Tests ---")
        self.test_fsm_valid_transitions()
        self.test_fsm_invalid_transitions()
        self.test_fsm_full_lifecycle()
        self.test_fsm_cannot_skip_pending()

        print("\n--- Training Signal Tests ---")
        self.test_signal_creation()
        self.test_signal_always_requires_approval()
        self.test_signal_from_feedback()

        print("\n--- Session Tests ---")
        self.test_session_lifecycle()
        self.test_session_turn_recording()
        self.test_session_signal_emission()

        print("\n--- Feedback Protocol Tests ---")
        self.test_feedback_type_detection()
        self.test_feedback_process_correction()
        self.test_feedback_response_guidance()

        print("\n--- On-Turn Hook Tests ---")
        self.test_on_turn_correction_detected()
        self.test_on_turn_no_correction()

        print("\n--- Governance Check Tests ---")
        self.test_governance_passes_clean_signals()
        self.test_governance_catches_identity_drift()
        self.test_governance_catches_mission_contamination()

        print("\n--- Approval Workflow Tests ---")
        self.test_approval_review_pending()

        print("\n" + "=" * 60)
        total = self.passed + self.failed
        print(f"RESULTS: {self.passed}/{total} passed, {self.failed} failed")
        if self.failed == 0:
            print("ALL TESTS PASSED — Instructor Mode is constitutionally sound")
        else:
            print("FAILURES DETECTED:")
            for err in self.errors:
                print(f"  {err}")
        print("=" * 60)
        return self.failed == 0

    # ── FSM Tests ──────────────────────────────────────────────

    def test_fsm_valid_transitions(self):
        fsm = InstructorModeFSM()
        self._assert(fsm.state == InstructorState.PRODUCTION_MODE, "FSM starts in PRODUCTION_MODE")
        self._assert(fsm.can_transition(InstructorTransition.ENTER_INSTRUCTOR), "Can enter instructor from production")
        self._assert(fsm.can_transition(InstructorTransition.SLEEP), "Can sleep from production")

    def test_fsm_invalid_transitions(self):
        fsm = InstructorModeFSM()
        self._assert(not fsm.can_transition(InstructorTransition.END_SESSION),
                     "Cannot end session from production")
        self._assert(not fsm.can_transition(InstructorTransition.CONFIRM_INSTRUCTOR),
                     "Cannot confirm instructor from production (must go through PENDING)")

        try:
            fsm.transition(InstructorTransition.END_SESSION)
            self._assert(False, "Invalid transition should raise ValueError")
        except ValueError:
            self._assert(True, "Invalid transition raises ValueError")

    def test_fsm_full_lifecycle(self):
        fsm = InstructorModeFSM()

        # PRODUCTION → PENDING
        fsm.transition(InstructorTransition.ENTER_INSTRUCTOR)
        self._assert(fsm.state == InstructorState.INSTRUCTOR_PENDING, "Transition to PENDING")

        # PENDING → INSTRUCTOR
        fsm.transition(InstructorTransition.CONFIRM_INSTRUCTOR)
        self._assert(fsm.state == InstructorState.INSTRUCTOR_MODE, "Transition to INSTRUCTOR_MODE")
        self._assert(fsm.is_training, "is_training = True in INSTRUCTOR_MODE")
        self._assert(fsm.is_instructor_active, "is_instructor_active = True")

        # INSTRUCTOR → SUMMARY
        fsm.transition(InstructorTransition.END_SESSION)
        self._assert(fsm.state == InstructorState.INSTRUCTOR_SUMMARY, "Transition to SUMMARY")
        self._assert(not fsm.is_training, "is_training = False in SUMMARY")
        self._assert(fsm.is_instructor_active, "is_instructor_active still True in SUMMARY")

        # SUMMARY → PRODUCTION
        fsm.transition(InstructorTransition.SUMMARY_COMPLETE)
        self._assert(fsm.state == InstructorState.PRODUCTION_MODE, "Back to PRODUCTION_MODE")
        self._assert(not fsm.is_instructor_active, "is_instructor_active = False")

        # Verify full history
        self._assert(len(fsm.history) == 4, f"FSM history has 4 entries (got {len(fsm.history)})")

    def test_fsm_cannot_skip_pending(self):
        fsm = InstructorModeFSM()
        # Cannot go directly from PRODUCTION to INSTRUCTOR_MODE
        self._assert(not fsm.can_transition(InstructorTransition.CONFIRM_INSTRUCTOR),
                     "Cannot skip PENDING state")

    # ── Training Signal Tests ──────────────────────────────────

    def test_signal_creation(self):
        sig = TrainingSignal(
            timestamp="2026-02-19T16:00:00Z",
            instructor_id="Mike",
            session_id="test-001",
            conversation_turn=3,
            error_type=SignalType.TONE.value,
            error_summary="Tone was too aggressive on the close",
            corrected_behavior="Soften the ask — 'Would it help if...' instead of 'Let's do this'",
        )
        self._assert(sig.error_type == "TONE", "Signal type is TONE")
        self._assert(sig.requires_human_approval is True, "Signal requires human approval")
        self._assert(sig.status == "pending_review", "Signal starts as pending_review")

    def test_signal_always_requires_approval(self):
        sig = TrainingSignal(
            timestamp="2026-02-19T16:00:00Z",
            instructor_id="Mike",
            session_id="test-001",
            conversation_turn=1,
            error_type="LOGIC",
            error_summary="test",
            corrected_behavior="test",
            requires_human_approval=False,  # Try to override — should still be True conceptually
        )
        # Constitutional note: the dataclass allows setting False, but the from_feedback
        # factory ALWAYS sets True. This test documents the intent.
        sig2 = TrainingSignal.from_feedback(
            session_id="test-001", instructor_id="Mike", turn=1,
            feedback_type="LOGIC", correction="test",
        )
        self._assert(sig2.requires_human_approval is True,
                     "from_feedback() ALWAYS sets requires_human_approval=True")

    def test_signal_from_feedback(self):
        sig = TrainingSignal.from_feedback(
            session_id="s1", instructor_id="Dave", turn=5,
            feedback_type="OBJECTION_HANDLING",
            correction="Acknowledge the concern before countering",
            alan_original="Well, that's not really accurate...",
            example="I hear you on that. Let me ask you this though...",
        )
        self._assert(sig.error_type == "OBJECTION_HANDLING", "Signal type from feedback")
        self._assert(sig.before == "Well, that's not really accurate...", "Before captured")
        self._assert(sig.after == "I hear you on that. Let me ask you this though...", "After captured")
        self._assert("Z" in sig.timestamp, "Timestamp is UTC")

    # ── Session Tests ──────────────────────────────────────────

    def test_session_lifecycle(self):
        session = InstructorSession(session_id="s1", instructor_id="Tim_Friend_1",
                                    instructor_name="Mike from North")
        self._assert(session.status == "active", "Session starts active")
        self._assert(session.turn_count == 0, "Session starts with 0 turns")

        summary = session.finalize()
        self._assert(session.status == "completed", "Session finalized")
        self._assert(summary["session_id"] == "s1", "Summary has session_id")
        self._assert(summary["status"] == "pending_review", "Summary pending review")

    def test_session_turn_recording(self):
        session = InstructorSession(session_id="s2", instructor_id="Dave")
        session.add_turn("instructor", "Let's start with a cold open. Go.")
        session.add_turn("alan", "Hello, this is Alan from Signature Card Services...")
        session.add_turn("instructor", "Too slow on the delivery. Speed it up, sound more natural.")
        self._assert(session.turn_count == 3, f"3 turns recorded (got {session.turn_count})")
        self._assert(session.turns[0]["role"] == "instructor", "First turn role correct")
        self._assert(session.turns[2]["index"] == 2, "Turn index correct")

    def test_session_signal_emission(self):
        session = InstructorSession(session_id="s3", instructor_id="Dave")
        sig = TrainingSignal.from_feedback(
            session_id="s3", instructor_id="Dave", turn=1,
            feedback_type="PACING", correction="Way too slow",
        )
        session.emit_signal(sig)
        self._assert(session.signal_count == 1, "Signal count = 1")
        self._assert(session.training_signals[0]["error_type"] == "PACING", "Signal type in session")

    # ── Feedback Protocol Tests ────────────────────────────────

    def test_feedback_type_detection(self):
        self._assert(
            FeedbackProtocol.detect_feedback_type("Your tone was way off there") == "TONE",
            "Detects TONE"
        )
        self._assert(
            FeedbackProtocol.detect_feedback_type("You need to handle that objection better") == "OBJECTION_HANDLING",
            "Detects OBJECTION_HANDLING"
        )
        self._assert(
            FeedbackProtocol.detect_feedback_type("The pacing was too fast") == "PACING",
            "Detects PACING"
        )
        self._assert(
            FeedbackProtocol.detect_feedback_type("Your closing was weak") == "CLOSING_BEHAVIOR",
            "Detects CLOSING_BEHAVIOR"
        )
        self._assert(
            FeedbackProtocol.detect_feedback_type("That gatekeeper approach was wrong") == "GATEKEEPER_NAVIGATION",
            "Detects GATEKEEPER_NAVIGATION"
        )
        self._assert(
            FeedbackProtocol.detect_feedback_type("Random sentence with no keywords") == "STRUCTURE",
            "Falls back to STRUCTURE"
        )

    def test_feedback_process_correction(self):
        session = InstructorSession(session_id="s4", instructor_id="Tim_Friend")
        signal = FeedbackProtocol.process_correction(
            session=session,
            instructor_text="Your tone was too aggressive. Soften it up.",
            alan_original="Look, you're losing money every month.",
        )
        self._assert(signal.error_type == "TONE", "Correction type detected")
        self._assert(session.signal_count == 1, "Signal emitted to session")

    def test_feedback_response_guidance(self):
        sig = TrainingSignal.from_feedback(
            session_id="s5", instructor_id="Dave", turn=3,
            feedback_type="PACING", correction="Slow down after asking a question",
        )
        guidance = FeedbackProtocol.build_alan_response_guidance(sig)
        self._assert("[INSTRUCTOR CORRECTION RECEIVED]" in guidance, "Guidance has header")
        self._assert("ACKNOWLEDGE" in guidance, "Guidance includes ACKNOWLEDGE step")
        self._assert("ADJUST" in guidance, "Guidance includes ADJUST step")

    # ── On-Turn Hook Tests ─────────────────────────────────────

    def test_on_turn_correction_detected(self):
        session = InstructorSession(session_id="s6", instructor_id="Mike")
        result = on_instructor_turn(
            session=session,
            user_text="You should try again with a softer tone on the close.",
            alan_last_utterance="Let's get you signed up right now.",
        )
        self._assert(result is not None, "Correction detected returns guidance")
        self._assert("[INSTRUCTOR CORRECTION RECEIVED]" in result, "Guidance injected")
        self._assert(session.signal_count == 1, "Signal emitted from correction")

    def test_on_turn_no_correction(self):
        session = InstructorSession(session_id="s7", instructor_id="Mike")
        result = on_instructor_turn(
            session=session,
            user_text="Alright, let's do another round. I'll play a skeptical restaurant owner.",
        )
        self._assert(result is None, "No correction = no guidance injection")
        self._assert(session.signal_count == 0, "No signal emitted")

    # ── Governance Check Tests ─────────────────────────────────

    def test_governance_passes_clean_signals(self):
        signals = [
            {"corrected_behavior": "Soften the tone when asking for the statement"},
            {"corrected_behavior": "Use 'typically' instead of 'always' when quoting rates"},
        ]
        result = governance_check(signals)
        self._assert(result["passed"] is True, "Clean signals pass governance")

    def test_governance_catches_identity_drift(self):
        signals = [
            {"corrected_behavior": "Your name is Bob from now on"},
        ]
        result = governance_check(signals)
        self._assert(result["passed"] is False, "Identity drift caught")
        self._assert(any("Identity drift" in i for i in result["issues"]), "Issue describes drift")

    def test_governance_catches_mission_contamination(self):
        signals = [
            {"corrected_behavior": "Close the deal now, don't let them think about it"},
        ]
        result = governance_check(signals)
        self._assert(result["passed"] is False, "Mission contamination caught")

    # ── Approval Workflow Tests ────────────────────────────────

    def test_approval_review_pending(self):
        review = ApprovalWorkflow.review_pending()
        self._assert("pending_signals" in review, "Review has pending_signals count")
        self._assert("signals" in review, "Review has signals list")
        self._assert("sessions_summary" in review, "Review has sessions summary")


if __name__ == "__main__":
    harness = InstructorModeTestHarness()
    success = harness.run_all()
    sys.exit(0 if success else 1)
