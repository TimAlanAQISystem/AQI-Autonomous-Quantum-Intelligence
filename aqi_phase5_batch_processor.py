"""
AQI Phase 5 — Batch Processor
================================
Processes directories of Phase 4 call traces (100+ calls)
and produces aggregated Phase 5 intelligence.

Part of the AQI 0.1mm Chip ecosystem.
"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from aqi_phase5_call_analyzer import Phase5CallAnalyzer
from aqi_phase5_dashboard import Phase5Dashboard
from phase4_validator import Phase4Validator


class Phase5BatchProcessor:
    """Batch process Phase 4 call traces for Phase 5 behavioral intelligence."""

    def __init__(self, validate: bool = True):
        self.analyzer = Phase5CallAnalyzer()
        self.dashboard = Phase5Dashboard()
        self.validator = Phase4Validator()
        self.validate = validate
        self.errors = []
        self.processed = 0

    def process_directory(self, dir_path: str) -> dict:
        """
        Process all JSONL/JSON files in a directory.

        Returns aggregated Phase 5 intelligence.
        """
        dp = Path(dir_path)
        if not dp.exists():
            raise FileNotFoundError(f"Directory not found: {dir_path}")

        for path in sorted(dp.glob("*.jsonl")):
            self._process_jsonl(path)

        for path in sorted(dp.glob("*.json")):
            if path.name.endswith(".schema.json"):
                continue
            self._process_single_json(path)

        return self.dashboard.aggregate()

    def process_file(self, file_path: str) -> dict:
        """Process a single JSONL file."""
        self._process_jsonl(Path(file_path))
        return self.dashboard.aggregate()

    def _process_jsonl(self, path: Path):
        with path.open("r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    trace = json.loads(line)
                    self._ingest(trace, f"{path}:{line_num}")
                except json.JSONDecodeError as e:
                    self.errors.append(f"{path}:{line_num} JSON error: {e}")
                except Exception as e:
                    self.errors.append(f"{path}:{line_num} error: {e}")

    def _process_single_json(self, path: Path):
        try:
            with path.open("r", encoding="utf-8") as f:
                trace = json.load(f)
            self._ingest(trace, str(path))
        except Exception as e:
            self.errors.append(f"{path} error: {e}")

    def _ingest(self, trace: dict, source: str):
        if self.validate:
            result = self.validator.validate(trace)
            if not result["valid"]:
                self.errors.append(f"{source} validation: {result['structural_errors']}")
                return

        profile = self.analyzer.analyze(trace)
        self.dashboard.add_call_profile(profile)
        self.processed += 1

    def get_per_call_profiles(self) -> list:
        """Return all individual call profiles."""
        return self.dashboard.call_profiles

    def get_summary(self) -> dict:
        """Quick summary of processing results."""
        return {
            "processed": self.processed,
            "errors": len(self.errors),
            "error_details": self.errors[:10],  # First 10 errors
        }
