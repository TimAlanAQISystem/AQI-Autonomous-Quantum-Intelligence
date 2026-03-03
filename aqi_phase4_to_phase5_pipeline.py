"""
AQI Phase 4 → Phase 5 Ingestion Pipeline
==========================================
End-to-end pipeline: validates Phase 4 traces, runs Phase 5 analysis,
aggregates intelligence, and optionally writes reports.

Part of the AQI 0.1mm Chip ecosystem.
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from phase4_validator import Phase4Validator
from aqi_phase5_call_analyzer import Phase5CallAnalyzer
from aqi_phase5_dashboard import Phase5Dashboard


class Phase4ToPhase5Pipeline:
    """Complete pipeline from Phase 4 telemetry to Phase 5 behavioral intelligence."""

    def __init__(self):
        self.validator = Phase4Validator()
        self.analyzer = Phase5CallAnalyzer()
        self.dashboard = Phase5Dashboard()
        self._processed = 0
        self._rejected = 0
        self._errors = []

    def ingest_trace(self, trace: dict, validate: bool = True) -> dict:
        """
        Ingest a single call trace through the full pipeline.

        Returns the Phase 5 profile, or None if validation failed.
        """
        if validate:
            result = self.validator.validate(trace)
            if not result["valid"]:
                self._rejected += 1
                self._errors.extend(result["structural_errors"])
                return None

        profile = self.analyzer.analyze(trace)
        self.dashboard.add_call_profile(profile)
        self._processed += 1
        return profile

    def ingest_file(self, path: str, validate: bool = True):
        """Ingest all traces from a JSONL file."""
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    trace = json.loads(line)
                    self.ingest_trace(trace, validate)
                except Exception as e:
                    self._errors.append(f"{path}: {e}")
                    self._rejected += 1

    def ingest_directory(self, dir_path: str, validate: bool = True):
        """Ingest all JSONL/JSON files from a directory."""
        dp = Path(dir_path)
        for p in sorted(dp.glob("*.jsonl")):
            self.ingest_file(str(p), validate)
        for p in sorted(dp.glob("*.json")):
            if p.name.endswith(".schema.json"):
                continue
            try:
                with p.open("r", encoding="utf-8") as f:
                    trace = json.load(f)
                self.ingest_trace(trace, validate)
            except Exception as e:
                self._errors.append(f"{p}: {e}")
                self._rejected += 1

    def aggregate(self, window: int = 0) -> dict:
        """
        Produce Phase 5 intelligence.
        window=0 means all calls; window=N means last N calls.
        """
        if window > 0:
            return self.dashboard.get_rolling_aggregate(window)
        return self.dashboard.aggregate()

    def export_profiles(self, output_dir: str):
        """Write individual call profiles as JSON files."""
        os.makedirs(output_dir, exist_ok=True)
        for profile in self.dashboard.call_profiles:
            call_id = profile.get("call_id", "unknown")
            safe_id = call_id.replace("/", "_").replace("\\", "_")
            path = os.path.join(output_dir, f"{safe_id}.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(profile, f, indent=2, default=str)

    @property
    def stats(self) -> dict:
        return {
            "processed": self._processed,
            "rejected": self._rejected,
            "errors": self._errors[:10],
            "total_in_dashboard": self.dashboard.total_calls,
        }
