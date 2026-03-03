# test_voice_sensitizer.py
"""
Voice Sensitizer Unit Tests
============================
Neg-proofs all Voice Sensitizer behaviors:
  - Drift classification at every severity level
  - Prosody boundary checks
  - Override/action mapping
  - Per-window accumulation
  - Post-call summary generation
  - Config loading fallback
  - Edge cases (empty windows, boundary values)

Run: .\.venv\Scripts\python.exe -m pytest test_voice_sensitizer.py -v
"""

import unittest
import json
from voice_sensitizer import (
    VoiceSensitizer,
    VoiceSensitizerConfig,
    VoiceWindowMetrics,
    VoiceDriftEvent,
    DEFAULT_VOICE_SENSITIZER_CONFIG,
)


class TestDriftClassification(unittest.TestCase):
    """Test drift score -> severity classification."""

    def setUp(self):
        self.config = VoiceSensitizerConfig(config=DEFAULT_VOICE_SENSITIZER_CONFIG)
        self.vs = VoiceSensitizer(self.config)

    def test_no_drift(self):
        """Spectral similarity 1.0 = zero drift = severity 'none'."""
        w = VoiceWindowMetrics(spectral_similarity=1.0, pitch_variance=0.15,
                               energy_variance=0.15, speaking_rate_wpm=150)
        result = self.vs.analyze_window_and_maybe_correct(w)
        self.assertEqual(result["severity"], "none")
        self.assertAlmostEqual(result["drift_score"], 0.0, places=2)
        self.assertEqual(result["action"], "none")

    def test_mild_drift(self):
        """Drift 0.15-0.24 = mild severity."""
        w = VoiceWindowMetrics(spectral_similarity=0.82, pitch_variance=0.15,
                               energy_variance=0.15, speaking_rate_wpm=150)
        result = self.vs.analyze_window_and_maybe_correct(w)
        self.assertEqual(result["severity"], "mild")
        self.assertEqual(result["action"], "log_only")

    def test_moderate_drift(self):
        """Drift 0.25-0.34 = moderate severity."""
        w = VoiceWindowMetrics(spectral_similarity=0.72, pitch_variance=0.15,
                               energy_variance=0.15, speaking_rate_wpm=150)
        result = self.vs.analyze_window_and_maybe_correct(w)
        self.assertEqual(result["severity"], "moderate")
        self.assertEqual(result["action"], "log_and_warn")

    def test_severe_drift(self):
        """Drift 0.35-0.44 = severe severity, TTS adjustments returned."""
        w = VoiceWindowMetrics(spectral_similarity=0.60, pitch_variance=0.15,
                               energy_variance=0.15, speaking_rate_wpm=150)
        result = self.vs.analyze_window_and_maybe_correct(w)
        self.assertEqual(result["severity"], "severe")
        self.assertEqual(result["action"], "adjust_tts_params")
        self.assertIn("stability_delta", result["tts_adjustments"])
        self.assertIn("similarity_boost_delta", result["tts_adjustments"])

    def test_catastrophic_drift(self):
        """Drift >= 0.45 = catastrophic severity, abort action."""
        w = VoiceWindowMetrics(spectral_similarity=0.50, pitch_variance=0.15,
                               energy_variance=0.15, speaking_rate_wpm=150)
        result = self.vs.analyze_window_and_maybe_correct(w)
        self.assertEqual(result["severity"], "catastrophic")
        self.assertEqual(result["action"], "abort_call_and_alert")
        self.assertEqual(result["tts_adjustments"], {})  # No adjustments on abort


class TestProsodyChecks(unittest.TestCase):
    """Test prosody boundary detection."""

    def setUp(self):
        self.config = VoiceSensitizerConfig(config=DEFAULT_VOICE_SENSITIZER_CONFIG)
        self.vs = VoiceSensitizer(self.config)

    def test_prosody_all_ok(self):
        """All prosody dimensions in range = no flags."""
        w = VoiceWindowMetrics(spectral_similarity=0.95, pitch_variance=0.20,
                               energy_variance=0.25, speaking_rate_wpm=155)
        result = self.vs.analyze_window_and_maybe_correct(w)
        self.assertEqual(result["prosody_flags"], [])

    def test_pitch_too_flat(self):
        """Pitch variance below min = pitch_too_flat."""
        w = VoiceWindowMetrics(spectral_similarity=0.95, pitch_variance=0.02,
                               energy_variance=0.25, speaking_rate_wpm=155)
        result = self.vs.analyze_window_and_maybe_correct(w)
        self.assertIn("pitch_too_flat", result["prosody_flags"])

    def test_pitch_too_erratic(self):
        """Pitch variance above max = pitch_too_erratic."""
        w = VoiceWindowMetrics(spectral_similarity=0.95, pitch_variance=0.50,
                               energy_variance=0.25, speaking_rate_wpm=155)
        result = self.vs.analyze_window_and_maybe_correct(w)
        self.assertIn("pitch_too_erratic", result["prosody_flags"])

    def test_energy_too_flat(self):
        """Energy variance below min = energy_too_flat."""
        w = VoiceWindowMetrics(spectral_similarity=0.95, pitch_variance=0.20,
                               energy_variance=0.02, speaking_rate_wpm=155)
        result = self.vs.analyze_window_and_maybe_correct(w)
        self.assertIn("energy_too_flat", result["prosody_flags"])

    def test_too_slow(self):
        """Speaking rate below min = too_slow."""
        w = VoiceWindowMetrics(spectral_similarity=0.95, pitch_variance=0.20,
                               energy_variance=0.25, speaking_rate_wpm=80)
        result = self.vs.analyze_window_and_maybe_correct(w)
        self.assertIn("too_slow", result["prosody_flags"])

    def test_too_fast(self):
        """Speaking rate above max = too_fast."""
        w = VoiceWindowMetrics(spectral_similarity=0.95, pitch_variance=0.20,
                               energy_variance=0.25, speaking_rate_wpm=250)
        result = self.vs.analyze_window_and_maybe_correct(w)
        self.assertIn("too_fast", result["prosody_flags"])

    def test_prosody_penalty_increases_drift(self):
        """Out-of-range prosody adds 0.05 penalty per dimension."""
        # All prosody in range - baseline drift
        w_ok = VoiceWindowMetrics(spectral_similarity=0.90, pitch_variance=0.20,
                                  energy_variance=0.25, speaking_rate_wpm=155)
        r_ok = self.vs.analyze_window_and_maybe_correct(w_ok)

        self.vs.reset_call()

        # All 3 prosody dimensions out of range -> +0.15 penalty
        w_bad = VoiceWindowMetrics(spectral_similarity=0.90, pitch_variance=0.02,
                                   energy_variance=0.02, speaking_rate_wpm=80)
        r_bad = self.vs.analyze_window_and_maybe_correct(w_bad)

        self.assertGreater(r_bad["drift_score"], r_ok["drift_score"])
        self.assertAlmostEqual(r_bad["drift_score"] - r_ok["drift_score"], 0.15, places=2)


class TestPostCallSummary(unittest.TestCase):
    """Test post-call summary generation."""

    def setUp(self):
        self.config = VoiceSensitizerConfig(config=DEFAULT_VOICE_SENSITIZER_CONFIG)
        self.vs = VoiceSensitizer(self.config)

    def test_empty_call(self):
        """Call with no windows = zero drift."""
        summary = self.vs.analyze_call("CA_TEST_EMPTY")
        self.assertEqual(summary["total_windows"], 0)
        self.assertEqual(summary["avg_drift"], 0.0)
        self.assertEqual(summary["max_drift"], 0.0)
        self.assertEqual(summary["drift_event_count"], 0)
        self.assertEqual(summary["prosody_flag_count"], 0)

    def test_accumulated_windows(self):
        """Windows accumulated via analyze_window get summarized."""
        windows = [
            VoiceWindowMetrics(spectral_similarity=0.95, pitch_variance=0.20,
                               energy_variance=0.25, speaking_rate_wpm=155),
            VoiceWindowMetrics(spectral_similarity=0.90, pitch_variance=0.20,
                               energy_variance=0.25, speaking_rate_wpm=155),
            VoiceWindowMetrics(spectral_similarity=0.70, pitch_variance=0.20,
                               energy_variance=0.25, speaking_rate_wpm=155),
        ]
        for w in windows:
            self.vs.analyze_window_and_maybe_correct(w)

        summary = self.vs.analyze_call("CA_TEST_ACCUM")
        self.assertEqual(summary["total_windows"], 3)
        self.assertGreater(summary["avg_drift"], 0.0)
        self.assertGreater(summary["max_drift"], summary["avg_drift"])
        # Window 3 (0.70 similarity = 0.30 drift) should trigger moderate event
        self.assertGreater(summary["drift_event_count"], 0)

    def test_batch_analyze(self):
        """Batch analysis with explicit window list."""
        windows = [
            VoiceWindowMetrics(spectral_similarity=0.98, pitch_variance=0.15,
                               energy_variance=0.20, speaking_rate_wpm=150),
            VoiceWindowMetrics(spectral_similarity=0.50, pitch_variance=0.15,
                               energy_variance=0.20, speaking_rate_wpm=150),
        ]
        summary = self.vs.analyze_call("CA_TEST_BATCH", windows)
        self.assertEqual(summary["total_windows"], 2)
        self.assertAlmostEqual(summary["max_drift"], 0.50, places=2)
        # Window 2 should be catastrophic
        self.assertTrue(any(e["severity"] == "catastrophic" for e in summary["drift_events"]))

    def test_reset_call(self):
        """reset_call clears accumulators."""
        w = VoiceWindowMetrics(spectral_similarity=0.90, pitch_variance=0.15,
                               energy_variance=0.15, speaking_rate_wpm=150)
        self.vs.analyze_window_and_maybe_correct(w)
        self.assertEqual(len(self.vs._call_windows), 1)

        self.vs.reset_call()
        self.assertEqual(len(self.vs._call_windows), 0)
        self.assertEqual(len(self.vs._drift_events), 0)

    def test_summary_cdc_fields(self):
        """Summary has all fields needed for CDC storage."""
        w = VoiceWindowMetrics(spectral_similarity=0.90, pitch_variance=0.15,
                               energy_variance=0.15, speaking_rate_wpm=150)
        self.vs.analyze_window_and_maybe_correct(w)
        summary = self.vs.analyze_call("CA_TEST_CDC")

        required_fields = [
            "call_id", "total_windows", "avg_drift", "max_drift",
            "drift_events", "drift_event_count",
            "prosody_flags", "prosody_flag_count",
        ]
        for field in required_fields:
            self.assertIn(field, summary, f"Missing field: {field}")

        # Verify JSON-serializable
        json_str = json.dumps(summary)
        self.assertIsInstance(json_str, str)


class TestConfigLoading(unittest.TestCase):
    """Test config loading and fallback."""

    def test_default_config(self):
        """Loading with no args falls back to DEFAULT_VOICE_SENSITIZER_CONFIG."""
        config = VoiceSensitizerConfig()
        self.assertEqual(config.thresholds["mild_drift"], 0.15)
        self.assertEqual(config.actions["on_catastrophic_drift"], "abort_call_and_alert")

    def test_dict_config(self):
        """Loading from dict overrides defaults."""
        custom = {
            "thresholds": {"mild_drift": 0.20, "moderate_drift": 0.30,
                           "severe_drift": 0.40, "catastrophic_drift": 0.50,
                           "min_pitch_variance": 0.05, "max_pitch_variance": 0.40,
                           "min_energy_variance": 0.05, "max_energy_variance": 0.50,
                           "min_speaking_rate_wpm": 110, "max_speaking_rate_wpm": 190},
            "actions": {"on_mild_drift": "log_only", "on_moderate_drift": "log_and_warn",
                        "on_severe_drift": "adjust_tts_params",
                        "on_catastrophic_drift": "abort_call_and_alert"},
            "tts_adjustments": {"stability_delta": -0.2, "similarity_boost_delta": 0.2,
                                "speaking_rate_delta": -0.1},
            "baseline": {"voiceprint_path": "", "prosody_profile_path": ""},
            "logging": {"enable_per_window_logging": True, "enable_per_call_summary": True},
        }
        config = VoiceSensitizerConfig(config=custom)
        self.assertEqual(config.thresholds["mild_drift"], 0.20)
        self.assertEqual(config.tts_adjustments["stability_delta"], -0.2)

    def test_reload_config(self):
        """Hot-reload via reload_config changes thresholds live."""
        config = VoiceSensitizerConfig()
        vs = VoiceSensitizer(config)

        # Initially mild_drift = 0.15
        w = VoiceWindowMetrics(spectral_similarity=0.82, pitch_variance=0.15,
                               energy_variance=0.15, speaking_rate_wpm=150)
        result = vs.analyze_window_and_maybe_correct(w)
        self.assertEqual(result["severity"], "mild")

        # Reload with higher threshold -> same window should be 'none'
        new_cfg = dict(DEFAULT_VOICE_SENSITIZER_CONFIG)
        new_cfg["thresholds"] = dict(new_cfg["thresholds"])
        new_cfg["thresholds"]["mild_drift"] = 0.30
        vs.reload_config(new_cfg)
        vs.reset_call()

        result2 = vs.analyze_window_and_maybe_correct(w)
        self.assertEqual(result2["severity"], "none")


class TestEdgeCases(unittest.TestCase):
    """Edge case neg-proofs."""

    def setUp(self):
        self.config = VoiceSensitizerConfig(config=DEFAULT_VOICE_SENSITIZER_CONFIG)
        self.vs = VoiceSensitizer(self.config)

    def test_spectral_similarity_zero(self):
        """Complete identity loss (0.0 similarity) = max drift."""
        w = VoiceWindowMetrics(spectral_similarity=0.0, pitch_variance=0.15,
                               energy_variance=0.15, speaking_rate_wpm=150)
        result = self.vs.analyze_window_and_maybe_correct(w)
        self.assertEqual(result["severity"], "catastrophic")
        self.assertGreaterEqual(result["drift_score"], 0.45)

    def test_spectral_similarity_clamped(self):
        """Values > 1.0 clamped to 1.0."""
        w = VoiceWindowMetrics(spectral_similarity=1.5, pitch_variance=0.15,
                               energy_variance=0.15, speaking_rate_wpm=150)
        result = self.vs.analyze_window_and_maybe_correct(w)
        self.assertEqual(result["severity"], "none")
        self.assertAlmostEqual(result["drift_score"], 0.0, places=2)

    def test_negative_spectral_similarity_clamped(self):
        """Negative values clamped to 0.0."""
        w = VoiceWindowMetrics(spectral_similarity=-0.5, pitch_variance=0.15,
                               energy_variance=0.15, speaking_rate_wpm=150)
        result = self.vs.analyze_window_and_maybe_correct(w)
        self.assertLessEqual(result["drift_score"], 1.0)

    def test_drift_score_capped_at_1(self):
        """Total drift score never exceeds 1.0 even with max penalties."""
        w = VoiceWindowMetrics(spectral_similarity=0.0, pitch_variance=0.01,
                               energy_variance=0.01, speaking_rate_wpm=50)
        result = self.vs.analyze_window_and_maybe_correct(w)
        self.assertLessEqual(result["drift_score"], 1.0)

    def test_exact_boundary_mild(self):
        """Drift score exactly at mild threshold."""
        # 1.0 - 0.85 = 0.15 exactly
        w = VoiceWindowMetrics(spectral_similarity=0.85, pitch_variance=0.15,
                               energy_variance=0.15, speaking_rate_wpm=150)
        result = self.vs.analyze_window_and_maybe_correct(w)
        self.assertEqual(result["severity"], "mild")


if __name__ == "__main__":
    unittest.main()
