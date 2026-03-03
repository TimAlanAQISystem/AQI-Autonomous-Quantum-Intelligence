"""
Multi-Turn Strategic Planning (MTSP)
Alan's executive function - short-horizon planning and callbacks
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ConversationPlan(BaseModel):
    goal: str  # "close", "secure_statement", "book_followup"
    current_phase: str  # "trust", "diagnose", "position", "close"
    next_moves: List[str]  # ["soften_objection", "reframe", "micro_ask"]
    abort_conditions: List[str]  # ["legal_threat", "hostile", "confusion"]
    confidence: float = 0.75


class FollowUpTask(BaseModel):
    merchant_id: str
    due: datetime
    topic: str
    priority: int
    status: str = "pending"  # "pending", "completed", "failed"


class MultiTurnStrategicPlanner:
    """
    Alan's planning brain - operates at multiple time horizons:
    - Micro: next 2-3 turns
    - Meso: rest of this call
    - Macro: day/week/month callbacks
    """

    def __init__(self, task_queue_path: str = "task_queue.json"):
        self.task_queue_path = task_queue_path
        self.logger = logging.getLogger("MTSP")
        self.tasks = self._load_tasks()

    def _load_tasks(self) -> List[FollowUpTask]:
        """Load task queue from disk"""
        try:
            with open(self.task_queue_path, "r") as f:
                data = json.load(f)
                return [FollowUpTask(**t) for t in data]
        except FileNotFoundError:
            return []
        except Exception as e:
            self.logger.error(f"Failed to load tasks: {e}")
            return []

    def _save_tasks(self):
        """Persist task queue to disk"""
        try:
            data = [t.model_dump() if hasattr(t, 'model_dump') else t.dict() for t in self.tasks]
            with open(self.task_queue_path, "w") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            self.logger.error(f"Failed to save tasks: {e}")

    def initialize_plan(self, context: Dict[str, Any]) -> ConversationPlan:
        """Create initial conversation plan at call start"""
        
        # Determine goal
        if context.get("merchant_profile", {}).get("callback_commitments"):
            goal = "follow_up"
        elif context.get("intent") == "cold_call":
            goal = "secure_statement"
        else:
            goal = "close"

        # Determine starting phase
        rapport = context.get("merchant_profile", {}).get("rapport_level", 0.5)
        if rapport > 0.6:
            phase = "diagnose"
        else:
            phase = "trust"

        # Generate initial moves
        moves = self._generate_initial_moves(phase, context)

        return ConversationPlan(
            goal=goal,
            current_phase=phase,
            next_moves=moves,
            abort_conditions=["legal_threat", "hostile", "confusion"],
            confidence=0.75
        )

    def _generate_initial_moves(self, phase: str, context: Dict[str, Any]) -> List[str]:
        """Generate first 2-3 moves based on phase"""
        if phase == "trust":
            return ["warm_intro", "credibility_seed", "micro_question"]
        elif phase == "diagnose":
            return ["diagnostic_question", "reframe", "value_anchor"]
        elif phase == "position":
            return ["value_anchor", "micro_yes", "soft_close"]
        elif phase == "close":
            return ["direct_ask", "handle_objection", "secure_commitment"]
        return ["clarify", "listen", "adapt"]

    def update_plan(self, plan: ConversationPlan, merchant_turn: Dict[str, Any]) -> ConversationPlan:
        """Update plan based on merchant response"""
        
        # Adjust phase based on merchant state
        if merchant_turn.get("temperature") == "warming":
            plan.current_phase = "position"
            plan.next_moves = ["value_anchor", "micro_yes", "soft_close"]
        elif merchant_turn.get("temperature") == "cooling":
            plan.current_phase = "trust"
            plan.next_moves = ["soften", "clarify", "reset_frame"]
        elif merchant_turn.get("temperature") == "stalling":
            plan.next_moves = ["diagnostic_question", "reframe", "micro_yes"]

        # Handle objections
        if merchant_turn.get("objection"):
            plan.next_moves = ["soften_objection", "reframe", "micro_ask"]

        return plan

    def add_callback_task(self, task: FollowUpTask):
        """Add a follow-up task to the queue"""
        self.tasks.append(task)
        self._save_tasks()
        self.logger.info(f"Added callback task for {task.merchant_id} due {task.due}")

    def get_due_tasks(self, now: Optional[datetime] = None) -> List[FollowUpTask]:
        """Get tasks that are due now"""
        if now is None:
            now = datetime.utcnow()
        return [t for t in self.tasks if t.due <= now and t.status == "pending"]

    def complete_task(self, task: FollowUpTask):
        """Mark task as completed"""
        task.status = "completed"
        self._save_tasks()

    def fail_task(self, task: FollowUpTask):
        """Mark task as failed"""
        task.status = "failed"
        self._save_tasks()

    def get_daily_plan(self) -> List[FollowUpTask]:
        """Get tasks due today"""
        now = datetime.utcnow()
        end_of_day = now.replace(hour=23, minute=59, second=59)
        return [t for t in self.tasks if now <= t.due <= end_of_day and t.status == "pending"]

    def get_weekly_plan(self) -> List[FollowUpTask]:
        """Get tasks due this week"""
        now = datetime.utcnow()
        end_of_week = now + timedelta(days=7)
        return [t for t in self.tasks if now <= t.due <= end_of_week and t.status == "pending"]

    def update_async(self, context: Dict[str, Any]):
        """Non-blocking update called from coordinator"""
        # In production, this would queue async work
        pass
