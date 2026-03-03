"""
Human Override API
Admin commands for Tim/Mark/North to control Alan's state
"""

from enum import Enum
from typing import Dict, Any
import logging

from emergency_override_system import EmergencyOverrideSystem, EOSEvent, AlanState
from merchant_identity_persistence import MerchantIdentityPersistence
from multi_turn_strategic_planning import MultiTurnStrategicPlanner

logger = logging.getLogger(__name__)


class HumanCommand(Enum):
    FORCE_SAFE_MODE = "force_safe_mode"
    RESUME_NORMAL = "resume_normal"
    PAUSE_EVOLUTION = "pause_evolution"
    RESUME_EVOLUTION = "resume_evolution"
    CLEAR_MERCHANT_RISK_FLAG = "clear_merchant_risk_flag"
    MANUAL_CALLBACK_SCHEDULE = "manual_callback_schedule"
    OVERRIDE_ARCHETYPE = "override_archetype"


class HumanOverrideAPI:
    """
    Minimal admin interface for human control.
    Expose via REST API or CLI.
    """

    def __init__(
        self,
        eos: EmergencyOverrideSystem,
        mip: MerchantIdentityPersistence,
        mtsp: MultiTurnStrategicPlanner,
        db
    ):
        self.eos = eos
        self.mip = mip
        self.mtsp = mtsp
        self.db = db
        self.logger = logging.getLogger("HumanOverrideAPI")

    def execute_command(self, cmd: HumanCommand, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute human command and return result"""
        self.logger.info(f"[HUMAN OVERRIDE] Executing: {cmd.value} with payload: {payload}")

        try:
            if cmd == HumanCommand.FORCE_SAFE_MODE:
                return self._force_safe_mode(payload)

            elif cmd == HumanCommand.RESUME_NORMAL:
                return self._resume_normal(payload)

            elif cmd == HumanCommand.PAUSE_EVOLUTION:
                return self._pause_evolution(payload)

            elif cmd == HumanCommand.RESUME_EVOLUTION:
                return self._resume_evolution(payload)

            elif cmd == HumanCommand.CLEAR_MERCHANT_RISK_FLAG:
                return self._clear_merchant_risk_flag(payload)

            elif cmd == HumanCommand.MANUAL_CALLBACK_SCHEDULE:
                return self._manual_callback_schedule(payload)

            elif cmd == HumanCommand.OVERRIDE_ARCHETYPE:
                return self._override_archetype(payload)

            else:
                return {"success": False, "error": "Unknown command"}

        except Exception as e:
            self.logger.error(f"[HUMAN OVERRIDE] Command failed: {e}")
            return {"success": False, "error": str(e)}

    def _force_safe_mode(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Force Alan into safe mode"""
        self.eos.handle_event(EOSEvent.SYSTEM_ESCALATION, {
            "reason": "human_override",
            "payload": payload
        })
        return {"success": True, "state": self.eos.state.name}

    def _resume_normal(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Resume normal operation"""
        self.eos.state = AlanState.NORMAL_OPERATION
        return {"success": True, "state": self.eos.state.name}

    def _pause_evolution(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Pause evolution engine"""
        self.db.set_flag("evolution_paused", True)
        return {"success": True, "evolution_paused": True}

    def _resume_evolution(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Resume evolution engine"""
        self.db.set_flag("evolution_paused", False)
        return {"success": True, "evolution_paused": False}

    def _clear_merchant_risk_flag(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Clear risk flag from merchant profile"""
        merchant_id = payload.get("merchant_id")
        flag = payload.get("flag")

        if not merchant_id or not flag:
            return {"success": False, "error": "Missing merchant_id or flag"}

        profile = self.mip.load_profile(merchant_id)
        if flag in profile.risk_flags:
            profile.risk_flags.remove(flag)
            self.mip._save_profiles()

        return {"success": True, "merchant_id": merchant_id, "cleared_flag": flag}

    def _manual_callback_schedule(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Manually schedule a callback"""
        from multi_turn_strategic_planning import FollowUpTask
        from datetime import datetime

        merchant_id = payload.get("merchant_id")
        topic = payload.get("topic")
        due_str = payload.get("due")
        priority = payload.get("priority", 5)

        if not merchant_id or not topic or not due_str:
            return {"success": False, "error": "Missing required fields"}

        due = datetime.fromisoformat(due_str)

        task = FollowUpTask(
            merchant_id=merchant_id,
            due=due,
            topic=topic,
            priority=priority
        )

        self.mtsp.add_callback_task(task)

        return {"success": True, "task": task.dict()}

    def _override_archetype(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Override archetype classification for a merchant"""
        merchant_id = payload.get("merchant_id")
        archetype = payload.get("archetype")

        if not merchant_id or not archetype:
            return {"success": False, "error": "Missing merchant_id or archetype"}

        profile = self.mip.load_profile(merchant_id)
        profile.archetype_history.append({
            "type": archetype,
            "confidence": 1.0,
            "timestamp": datetime.utcnow().isoformat(),
            "source": "human_override"
        })
        self.mip._save_profiles()

        return {"success": True, "merchant_id": merchant_id, "archetype": archetype}


# Simple DB stub for flags
class SimpleFlagDB:
    def __init__(self):
        self.flags = {}

    def set_flag(self, key: str, value: bool):
        self.flags[key] = value

    def get_flag(self, key: str) -> bool:
        return self.flags.get(key, False)
