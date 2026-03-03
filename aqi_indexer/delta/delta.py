"""Delta report generation for AQI indexing system."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class DeltaConfig:
    delta_report_path: Path
    previous_inventory_path: Path


class DeltaReporter:
    def __init__(self, config: DeltaConfig) -> None:
        self.config = config

    def generate(self) -> None:
        """Create a delta report by comparing current state to previous runs."""
        raise NotImplementedError

    def _load_previous(self) -> dict:
        raise NotImplementedError

    def _load_current(self) -> dict:
        raise NotImplementedError
