# metrics.py

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import time


@dataclass
class RunMetrics:
    """Metrics for a single run/intent processing."""
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None

    # DMA counters
    dmas_spawned: int = 0
    dmas_completed: int = 0
    dmas_terminated: int = 0
    dmas_error: int = 0

    # Form counters
    forms_created: int = 0
    forms_reused: int = 0

    # Governance
    mengine_violations: int = 0

    # Timing
    dma_execution_times: List[float] = field(default_factory=list)

    # Status
    container_health: Dict[str, str] = field(default_factory=dict)  # container_id -> "healthy"/"error"/etc
    last_errors: Dict[str, str] = field(default_factory=dict)  # container_id -> last error msg

    def record_dma_spawn(self) -> None:
        self.dmas_spawned += 1

    def record_dma_complete(self, execution_time: float) -> None:
        self.dmas_completed += 1
        self.dma_execution_times.append(execution_time)

    def record_dma_terminate(self) -> None:
        self.dmas_terminated += 1

    def record_dma_error(self) -> None:
        self.dmas_error += 1

    def record_form_created(self) -> None:
        self.forms_created += 1

    def record_form_reused(self) -> None:
        self.forms_reused += 1

    def record_mengine_violation(self) -> None:
        self.mengine_violations += 1

    def set_container_health(self, container_id: str, status: str) -> None:
        self.container_health[container_id] = status

    def record_error(self, container_id: str, error_msg: str) -> None:
        self.last_errors[container_id] = error_msg
        self.set_container_health(container_id, "error")

    def finalize_run(self) -> None:
        self.end_time = time.time()

    @property
    def total_run_time(self) -> float:
        if self.end_time is None:
            return time.time() - self.start_time
        return self.end_time - self.start_time

    @property
    def avg_dma_execution_time(self) -> float:
        if not self.dma_execution_times:
            return 0.0
        return sum(self.dma_execution_times) / len(self.dma_execution_times)

    def snapshot(self) -> Dict[str, any]:
        return {
            "run_duration_sec": round(self.total_run_time, 3),
            "dmas": {
                "spawned": self.dmas_spawned,
                "completed": self.dmas_completed,
                "terminated": self.dmas_terminated,
                "error": self.dmas_error,
                "avg_execution_time_sec": round(self.avg_dma_execution_time, 3),
            },
            "forms": {
                "created": self.forms_created,
                "reused": self.forms_reused,
            },
            "governance": {
                "mengine_violations": self.mengine_violations,
            },
            "containers": {
                "health": self.container_health,
                "last_errors": self.last_errors,
            },
        }


class Metrics:
    """Global metrics manager."""
    _current_run: Optional[RunMetrics] = None

    @classmethod
    def start_run(cls) -> None:
        cls._current_run = RunMetrics()

    @classmethod
    def get_current_run(cls) -> Optional[RunMetrics]:
        return cls._current_run

    @classmethod
    def end_run(cls) -> None:
        if cls._current_run:
            cls._current_run.finalize_run()

    @classmethod
    def snapshot(cls) -> Dict[str, any]:
        if cls._current_run:
            return cls._current_run.snapshot()
        return {"error": "No active run"}

    # Convenience methods that delegate to current run
    @classmethod
    def record_dma_spawn(cls) -> None:
        if cls._current_run:
            cls._current_run.record_dma_spawn()

    @classmethod
    def record_dma_complete(cls, execution_time: float) -> None:
        if cls._current_run:
            cls._current_run.record_dma_complete(execution_time)

    @classmethod
    def record_dma_terminate(cls) -> None:
        if cls._current_run:
            cls._current_run.record_dma_terminate()

    @classmethod
    def record_dma_error(cls) -> None:
        if cls._current_run:
            cls._current_run.record_dma_error()

    @classmethod
    def record_form_created(cls) -> None:
        if cls._current_run:
            cls._current_run.record_form_created()

    @classmethod
    def record_form_reused(cls) -> None:
        if cls._current_run:
            cls._current_run.record_form_reused()

    @classmethod
    def record_mengine_violation(cls) -> None:
        if cls._current_run:
            cls._current_run.record_mengine_violation()

    @classmethod
    def set_container_health(cls, container_id: str, status: str) -> None:
        if cls._current_run:
            cls._current_run.set_container_health(container_id, status)

    @classmethod
    def record_error(cls, container_id: str, error_msg: str) -> None:
        if cls._current_run:
            cls._current_run.record_error(container_id, error_msg)