"""
AQI Phase 5 — Streaming Analyzer
===================================
Real-time Phase 5 analysis wired into the relay server.
Called once per completed call. Maintains rolling intelligence.

Integration point: on_call_end in aqi_conversation_relay_server.py

Part of the AQI 0.1mm Chip ecosystem.
"""

import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from aqi_phase5_call_analyzer import Phase5CallAnalyzer
from aqi_phase5_dashboard import Phase5Dashboard
from phase4_validator import Phase4Validator


class Phase5StreamingAnalyzer:
    """
    Real-time behavioral intelligence from completed calls.
    
    Wire into the relay server's on_call_end hook:
        analyzer = Phase5StreamingAnalyzer()
        ...
        profile = analyzer.on_call_complete(trace)
    """

    def __init__(self, output_dir: str = "data/aqi_phase5"):
        self.analyzer = Phase5CallAnalyzer()
        self.dashboard = Phase5Dashboard()
        self.validator = Phase4Validator()
        self.output_dir = output_dir
        self._call_count = 0

        os.makedirs(output_dir, exist_ok=True)

    def on_call_complete(self, trace: dict, validate: bool = False) -> dict:
        """
        Called once per completed call.

        Parameters
        ----------
        trace : dict — Phase 4 call trace (canonical schema)
        validate : bool — run structural validation first

        Returns
        -------
        dict — Phase 5 behavioral profile for this call
        """
        if validate:
            result = self.validator.validate(trace)
            if not result["valid"]:
                return {"error": "validation_failed", "details": result["structural_errors"]}

        profile = self.analyzer.analyze(trace)
        self.dashboard.add_call_profile(profile)
        self._call_count += 1

        # Persist profile
        self._persist_profile(profile)

        return profile

    def get_aggregate(self, window: int = 0) -> dict:
        """
        Current cross-call intelligence snapshot.
        window=0 = all calls, window=N = last N calls.
        """
        if window > 0:
            return self.dashboard.get_rolling_aggregate(window)
        return self.dashboard.aggregate()

    def get_latest_profile(self) -> dict:
        """Return the most recent call's profile."""
        if self.dashboard.call_profiles:
            return self.dashboard.call_profiles[-1]
        return {}

    @property
    def calls_analyzed(self) -> int:
        return self._call_count

    def _persist_profile(self, profile: dict):
        """Append profile to JSONL log."""
        try:
            log_path = os.path.join(self.output_dir, "phase5_profiles.jsonl")
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(profile, default=str) + "\n")
        except Exception:
            pass  # Non-critical — profile is already in memory
