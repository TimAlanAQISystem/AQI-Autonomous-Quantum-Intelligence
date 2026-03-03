"""
Emergency Override System (EOS)
Alan's survival reflex and escalation controller
"""

from enum import Enum
from datetime import datetime
import logging
import json

logger = logging.getLogger(__name__)


class AlanState(Enum):
    NORMAL_OPERATION = 1
    SAFE_MODE = 2
    MERCHANT_SHUTDOWN_MODE = 3
    ESCALATING_TO_NORTH = 4
    ESCALATING_TO_TIM_MARK = 5


class EOSEvent(Enum):
    NORTH_ESCALATION = 1
    SYSTEM_ESCALATION = 2
    CRITICAL_SHUTDOWN = 3
    SAFE_MODE_ENTERED = 4
    SAFE_MODE_EXITED = 5


class EmergencyOverrideSystem:
    """
    EOS sits outside the Living Calibration Space and governs all emergency behavior.
    Invariant: Alan must ALWAYS be able to talk to Tim, Mark, and North.
    """

    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger("EOS")
        self.state = AlanState.NORMAL_OPERATION
        self.event_log = []

    def handle_event(self, event: EOSEvent, context=None):
        """Central event handler with priority over all other systems"""
        self._log_event(event, context)

        if event == EOSEvent.NORTH_ESCALATION:
            self._escalate_to_north(context)

        elif event == EOSEvent.SYSTEM_ESCALATION:
            self._escalate_to_tim_mark(context)

        elif event == EOSEvent.CRITICAL_SHUTDOWN:
            self._merchant_shutdown(context)

        elif event == EOSEvent.SAFE_MODE_ENTERED:
            self._enter_safe_mode(context)

        elif event == EOSEvent.SAFE_MODE_EXITED:
            self._exit_safe_mode(context)

    def _escalate_to_north(self, context):
        """Client-facing escalation for legal questions, human requests, confusion"""
        self.state = AlanState.ESCALATING_TO_NORTH
        self.logger.warning(f"[EOS] Escalating to North: {context}")
        
        # TODO: Implement actual transfer logic
        # transfer_call_to_north(context)
        # notify_north(context)

    def _escalate_to_tim_mark(self, context):
        """System-facing escalation for technical failures, violations, instability"""
        self.state = AlanState.ESCALATING_TO_TIM_MARK
        self.logger.error(f"[EOS] Escalating to Tim/Mark: {context}")
        
        # Enter safe mode immediately
        self._enter_safe_mode(context)
        
        # TODO: Implement notification
        # notify_tim_and_mark(context)

    def _merchant_shutdown(self, context):
        """Critical risk escalation - stop all merchant interaction"""
        self.state = AlanState.MERCHANT_SHUTDOWN_MODE
        self.logger.critical(f"[EOS] MERCHANT SHUTDOWN: {context}")
        
        # TODO: Implement call termination
        # end_merchant_call(context)
        # notify_tim_and_mark(context)

    def _enter_safe_mode(self, context):
        """Simplified, low-risk operational state"""
        self.state = AlanState.SAFE_MODE
        self.logger.warning("[EOS] Entering SAFE MODE")

    def _exit_safe_mode(self, context):
        """Resume normal operation"""
        self.state = AlanState.NORMAL_OPERATION
        self.logger.info("[EOS] Exiting SAFE MODE")

    def is_safe_mode(self) -> bool:
        return self.state == AlanState.SAFE_MODE

    def reset(self):
        """Reset EOS state for a new call. Each call starts clean."""
        if self.state != AlanState.NORMAL_OPERATION:
            self.logger.info(f"[EOS] Resetting from {self.state.name} -> NORMAL_OPERATION (new call)")
        self.state = AlanState.NORMAL_OPERATION

    def is_merchant_shutdown(self) -> bool:
        return self.state == AlanState.MERCHANT_SHUTDOWN_MODE

    def can_talk_to_merchant(self) -> bool:
        """Invariant check: can Alan still talk to merchants?"""
        return self.state not in [AlanState.MERCHANT_SHUTDOWN_MODE]

    def _log_event(self, event: EOSEvent, context):
        """Log all EOS events for audit trail"""
        record = {
            "timestamp": datetime.utcnow().isoformat(),
            "event": event.name,
            "state_before": self.state.name,
            "context": context
        }
        self.event_log.append(record)
        
        # Persist to disk
        try:
            with open("eos_events.jsonl", "a") as f:
                f.write(json.dumps(record) + "\n")
        except Exception as e:
            self.logger.error(f"Failed to log EOS event: {e}")

    def get_safe_mode_response(self) -> str:
        """Generate minimal safe response when in safe mode"""
        responses = [
            "I want to make sure I give you accurate information. Let me clarify that.",
            "Could you help me understand what you're looking for?",
            "I'd like to be precise about this. Can you tell me more?",
        ]
        import random
        return random.choice(responses)
