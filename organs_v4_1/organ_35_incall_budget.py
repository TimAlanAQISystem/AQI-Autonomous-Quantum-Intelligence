"""
╔══════════════════════════════════════════════════════════════════════════════╗
║           ORGAN 35 — IN-CALL IQCORE BUDGETING                                ║
║                                                                              ║
║  Extends IQcore governance INTO live calls. Tracks IQ spend per turn,        ║
║  throttles expensive organs when burn is high, and triggers fallback         ║
║  strategies under scarcity. Prevents runaway reasoning and ensures           ║
║  predictable behavior under cognitive load.                                  ║
║                                                                              ║
║  Constitutional Guarantees:                                                  ║
║    - Per-call budget is configurable                                         ║
║    - Spend tracking increments on each IQcore call                           ║
║    - Throttle threshold disables expensive organs                            ║
║    - Hard stop prevents all IQcore-costed operations                         ║
║    - Budget report generated at call end                                     ║
║    - Budget tiers are respected (Standard/Priority/VIP)                      ║
║    - All mid-call scarcity events logged                                     ║
║                                                                              ║
║  RRG: Section 45                                                             ║
║  Author: Agent X / v4.1                                                      ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from enum import Enum

# ─── IQcore Wiring ───────────────────────────────────────────────────────────
_parent = str(Path(__file__).resolve().parent.parent)
if _parent not in sys.path:
    sys.path.insert(0, _parent)

try:
    from iqcore_enforcer import iqcore_cost
    IQCORE_AVAILABLE = True
except ImportError:
    IQCORE_AVAILABLE = False
    def iqcore_cost(actor: str, cost: int):
        def decorator(fn):
            return fn
        return decorator

logger = logging.getLogger("organ_35_incall_budget")

# ─── Constants ───────────────────────────────────────────────────────────────

class BurnState(Enum):
    NORMAL = "normal"
    HIGH = "high"           # ≥70%
    CRITICAL = "critical"   # ≥90%
    EXHAUSTED = "exhausted" # ≥100%

class CallTier(Enum):
    STANDARD = "standard"
    PRIORITY = "priority"
    VIP = "vip"

# Budget tiers
BUDGET_TIERS = {
    CallTier.STANDARD.value: {"budget": 20, "throttle_pct": 0.80, "hard_stop_pct": 1.0},
    CallTier.PRIORITY.value: {"budget": 40, "throttle_pct": 0.80, "hard_stop_pct": 1.0},
    CallTier.VIP.value:      {"budget": 999, "throttle_pct": 1.0, "hard_stop_pct": 1.0},
}

# Per-organ IQcore costs (reference map)
ORGAN_COST_MAP = {
    "organ_24_retrieval": 2,
    "organ_25_handoff": 3,
    "organ_26_outbound": 1,
    "organ_27_language": 1,
    "organ_28_calendar": 2,
    "organ_29_inbound": 1,
    "organ_30_prosody": 1,
    "organ_31_objection_observe": 1,
    "organ_31_objection_cluster": 2,
    "organ_32_summarization": 2,
    "organ_33_crm": 1,
    "organ_34_competitive": 1,
}

# Throttle rules: which organs to disable at each burn level
THROTTLE_RULES = {
    BurnState.HIGH.value: {
        "disable": ["organ_31_objection_cluster"],
        "reduce": {"organ_30_prosody": 3},  # Analyze every 3rd frame
        "message": "High burn: reducing non-critical organs",
    },
    BurnState.CRITICAL.value: {
        "disable": [
            "organ_24_retrieval",
            "organ_31_objection_cluster",
            "organ_31_objection_observe",
            "organ_34_competitive",
        ],
        "reduce": {"organ_30_prosody": 5},  # Analyze every 5th frame
        "message": "Critical burn: disabling expensive organs",
    },
    BurnState.EXHAUSTED.value: {
        "disable": list(ORGAN_COST_MAP.keys()),  # Disable all
        "reduce": {},
        "message": "Budget exhausted: all IQcore operations halted",
    },
}

# Fallback strategies
FALLBACK_STRATEGIES = {
    BurnState.HIGH.value: [
        "Reduce reasoning depth",
        "Use simpler scripts",
        "Avoid retrieval unless necessary",
    ],
    BurnState.CRITICAL.value: [
        "Use fallback pacing and script",
        "Disable competitive intel",
        "No handoff unless merchant demands it",
        "Skip non-critical organs",
    ],
    BurnState.EXHAUSTED.value: [
        "Abort turn",
        "Log violation",
        "Enter Recovery Mode (RRG Section 31)",
        "Reset counters next turn",
    ],
}


class InCallBudgetOrgan:
    """
    Organ 35: In-call IQcore budget management.
    Governs per-turn cognitive spend within a live call.
    """

    def __init__(self):
        self._active_call: Optional[str] = None
        self._call_tier: str = CallTier.STANDARD.value
        self._budget: int = BUDGET_TIERS[CallTier.STANDARD.value]["budget"]
        self._spent: int = 0
        self._turn_count: int = 0
        self._current_turn_spend: int = 0
        self._burn_state: str = BurnState.NORMAL.value
        self._disabled_organs: List[str] = []
        self._reduced_organs: Dict[str, int] = {}  # organ -> every Nth frame
        self._scarcity_log: List[Dict] = []
        self._turn_log: List[Dict] = []
        self._fallback_active: bool = False
        logger.info("[Organ 35] InCallBudgetOrgan initialized")

    # ─── Lifecycle ───────────────────────────────────────────────────────

    def start_call(self, call_id: str, tier: str = "standard") -> Dict[str, Any]:
        """Initialize budget for a new call."""
        self._active_call = call_id
        self._call_tier = tier if tier in BUDGET_TIERS else CallTier.STANDARD.value
        tier_config = BUDGET_TIERS[self._call_tier]
        self._budget = tier_config["budget"]
        self._spent = 0
        self._turn_count = 0
        self._current_turn_spend = 0
        self._burn_state = BurnState.NORMAL.value
        self._disabled_organs = []
        self._reduced_organs = {}
        self._scarcity_log = []
        self._turn_log = []
        self._fallback_active = False

        logger.info(f"[Organ 35] Call started: {call_id}, tier={self._call_tier}, budget={self._budget}")
        return {
            "call_id": call_id,
            "tier": self._call_tier,
            "budget": self._budget,
            "burn_state": self._burn_state,
        }

    def end_call(self) -> Dict[str, Any]:
        """Generate budget report at call end."""
        report = self.get_budget_report()
        self._active_call = None
        self._spent = 0
        self._turn_count = 0
        logger.info(f"[Organ 35] Call ended. Total spend: {report['total_spent']}/{report['budget']}")
        return report

    # ─── Turn Management ─────────────────────────────────────────────────

    def start_turn(self) -> Dict[str, Any]:
        """Begin a new conversational turn."""
        self._turn_count += 1
        self._current_turn_spend = 0

        # Check burn state at turn start
        self._update_burn_state()

        return {
            "turn": self._turn_count,
            "budget_remaining": self._budget - self._spent,
            "burn_state": self._burn_state,
            "disabled_organs": self._disabled_organs[:],
            "reduced_organs": self._reduced_organs.copy(),
            "fallback_active": self._fallback_active,
        }

    def end_turn(self) -> Dict[str, Any]:
        """End the current turn and log spend."""
        turn_record = {
            "turn": self._turn_count,
            "spend": self._current_turn_spend,
            "total_spent": self._spent,
            "burn_state": self._burn_state,
            "disabled_organs": self._disabled_organs[:],
            "fallback_active": self._fallback_active,
            "timestamp": time.time(),
        }
        self._turn_log.append(turn_record)
        return turn_record

    # ─── Spend Tracking ──────────────────────────────────────────────────

    def record_spend(self, organ_name: str, cost: int) -> Dict[str, Any]:
        """
        Record IQcore spend for an organ invocation.

        Returns:
            Spend result with budget status
        """
        # Check if organ is disabled
        if organ_name in self._disabled_organs:
            return {
                "status": "blocked",
                "organ": organ_name,
                "reason": f"Organ disabled under {self._burn_state} burn state",
                "cost": 0,
            }

        # Check hard stop
        if self._burn_state == BurnState.EXHAUSTED.value:
            self._log_scarcity("hard_stop", organ_name, cost)
            return {
                "status": "exhausted",
                "organ": organ_name,
                "reason": "Budget exhausted — hard stop",
                "cost": 0,
                "total_spent": self._spent,
                "budget": self._budget,
            }

        # Record the spend
        self._spent += cost
        self._current_turn_spend += cost

        # Update burn state after spend
        self._update_burn_state()

        result = {
            "status": "recorded",
            "organ": organ_name,
            "cost": cost,
            "turn_spend": self._current_turn_spend,
            "total_spent": self._spent,
            "budget": self._budget,
            "remaining": self._budget - self._spent,
            "burn_pct": self._get_burn_pct(),
            "burn_state": self._burn_state,
        }

        logger.debug(f"[Organ 35] Spend: {organ_name}={cost}, total={self._spent}/{self._budget}")
        return result

    def can_afford(self, organ_name: str, cost: int) -> Dict[str, Any]:
        """Check if an organ invocation can be afforded."""
        if organ_name in self._disabled_organs:
            return {"allowed": False, "reason": "organ_disabled"}
        if self._spent + cost > self._budget:
            return {"allowed": False, "reason": "over_budget"}
        if self._burn_state == BurnState.EXHAUSTED.value:
            return {"allowed": False, "reason": "exhausted"}

        # Check reduced frequency
        if organ_name in self._reduced_organs:
            nth = self._reduced_organs[organ_name]
            if self._turn_count % nth != 0:
                return {"allowed": False, "reason": f"reduced_to_every_{nth}_turns"}

        return {"allowed": True, "remaining_after": self._budget - self._spent - cost}

    # ─── Burn State Management ───────────────────────────────────────────

    def _get_burn_pct(self) -> float:
        """Get current burn percentage."""
        if self._budget <= 0:
            return 0.0
        return self._spent / self._budget

    def _update_burn_state(self) -> None:
        """Update burn state and apply throttle rules."""
        pct = self._get_burn_pct()
        tier_config = BUDGET_TIERS[self._call_tier]
        old_state = self._burn_state

        if pct >= 1.0:
            self._burn_state = BurnState.EXHAUSTED.value
        elif pct >= 0.9:
            self._burn_state = BurnState.CRITICAL.value
        elif pct >= 0.7:
            self._burn_state = BurnState.HIGH.value
        else:
            self._burn_state = BurnState.NORMAL.value

        # Apply throttle rules if state changed
        if self._burn_state != old_state:
            self._apply_throttle_rules()
            if self._burn_state != BurnState.NORMAL.value:
                self._log_scarcity("state_change", f"{old_state} → {self._burn_state}", 0)

    def _apply_throttle_rules(self) -> None:
        """Apply organ throttle/disable rules based on burn state."""
        if self._burn_state == BurnState.NORMAL.value:
            self._disabled_organs = []
            self._reduced_organs = {}
            self._fallback_active = False
            return

        rules = THROTTLE_RULES.get(self._burn_state, {})
        self._disabled_organs = rules.get("disable", [])
        self._reduced_organs = rules.get("reduce", {})
        self._fallback_active = True

    def get_burn_state(self) -> "BurnState":
        """Get current burn state as BurnState enum member."""
        return BurnState(self._burn_state)

    def get_throttle_rules(self) -> Dict[str, Any]:
        """Get current throttle rules based on burn state."""
        return {
            "burn_state": self._burn_state,
            "disabled": self._disabled_organs[:],
            "reduced": self._reduced_organs.copy(),
            "fallback_active": self._fallback_active,
        }

    def get_fallback_strategy(self) -> Dict[str, Any]:
        """Get fallback strategy for current burn state."""
        strategies = FALLBACK_STRATEGIES.get(self._burn_state, [])
        return {
            "burn_state": self._burn_state,
            "strategies": strategies,
            "active": len(strategies) > 0,
        }

    def get_fallback_strategies(self) -> List[str]:
        """Get active fallback strategies for current burn state."""
        return FALLBACK_STRATEGIES.get(self._burn_state, [])

    # ─── Prompt Scaling ──────────────────────────────────────────────────

    def get_prompt_complexity(self) -> str:
        """Get recommended prompt complexity level."""
        if self._burn_state == BurnState.EXHAUSTED.value:
            return "minimal"
        elif self._burn_state == BurnState.CRITICAL.value:
            return "simple"
        elif self._burn_state == BurnState.HIGH.value:
            return "standard"
        else:
            return "full"

    # ─── Scarcity Logging ────────────────────────────────────────────────

    def _log_scarcity(self, event_type: str, detail: str, cost: int) -> None:
        entry = {
            "event": event_type,
            "detail": detail,
            "cost": cost,
            "spent": self._spent,
            "budget": self._budget,
            "burn_pct": self._get_burn_pct(),
            "burn_state": self._burn_state,
            "turn": self._turn_count,
            "timestamp": time.time(),
        }
        self._scarcity_log.append(entry)
        logger.warning(f"[Organ 35] Scarcity: {event_type} — {detail}")

    def get_scarcity_log(self) -> List[Dict]:
        return self._scarcity_log[:]

    # ─── Budget Report ───────────────────────────────────────────────────

    def get_budget_report(self) -> Dict[str, Any]:
        """Generate comprehensive budget report."""
        return {
            "call_id": self._active_call,
            "tier": self._call_tier,
            "budget": self._budget,
            "total_spent": self._spent,
            "remaining": max(0, self._budget - self._spent),
            "burn_pct": round(self._get_burn_pct() * 100, 1),
            "burn_state": self._burn_state,
            "turns": self._turn_count,
            "avg_spend_per_turn": round(self._spent / max(1, self._turn_count), 2),
            "scarcity_events": len(self._scarcity_log),
            "disabled_organs": self._disabled_organs[:],
            "fallback_active": self._fallback_active,
            "prompt_complexity": self.get_prompt_complexity(),
            "turn_log": self._turn_log[:],
        }

    # ─── Status ──────────────────────────────────────────────────────────

    def get_status(self) -> Dict[str, Any]:
        return {
            "organ": "Organ 35 — In-Call IQcore Budgeting",
            "version": "4.1.0",
            "iqcore_available": IQCORE_AVAILABLE,
            "active_call": self._active_call,
            "tier": self._call_tier,
            "budget": self._budget,
            "spent": self._spent,
            "burn_state": self._burn_state,
            "turn_count": self._turn_count,
            "disabled_organs": len(self._disabled_organs),
            "fallback_active": self._fallback_active,
            "scarcity_events": len(self._scarcity_log),
        }
