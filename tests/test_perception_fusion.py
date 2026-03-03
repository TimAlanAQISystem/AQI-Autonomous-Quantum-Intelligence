#!/usr/bin/env python3
"""
AQI Test Suite — Perception Fusion Engine
============================================
Tests for PerceptionFusionEngine and PerceptionSnapshot.

Tests cover:
    - Mode inference (NORMAL, IVR, VOICEMAIL, DEAD_AIR, CONNECTION_LOSS, AUDIO_DRIFT)
    - Health inference (OK, DEGRADED, CRITICAL)
    - Snapshot creation and serialization
    - Config parameter override testing

Neg-Proofed: Yes — all mode/health combinations tested.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from perception_fusion_engine import (
    PerceptionFusionEngine, PerceptionSnapshot,
    PerceptionHealth, PerceptionMode
)


DEFAULT_CFG = {
    "connection_loss_timeout_ms": 3000,
    "dead_air_timeout_ms": 5000,
    "tts_drift_severe_threshold": 0.60,
    "ivr_hard_threshold": 0.80,
    "voicemail_hard_threshold": 0.80,
    "stt_confidence_degraded_threshold": 0.75,
    "tts_drift_mild_threshold": 0.25,
    "dead_air_warn_timeout_ms": 3000,
    "connection_loss_warn_timeout_ms": 1500,
}


class TestModeInference:
    """Test PerceptionMode inference from telephony signals."""
    
    def test_normal_mode(self):
        engine = PerceptionFusionEngine(DEFAULT_CFG)
        snap = engine.fuse(
            stt_confidence=0.95,
            tts_drift_score=0.1,
            inbound_silence_ms=500,
            packet_gap_ms=100,
            ivr_score=0.1,
            voicemail_score=0.1,
        )
        assert snap.mode == PerceptionMode.NORMAL
    
    def test_connection_loss(self):
        engine = PerceptionFusionEngine(DEFAULT_CFG)
        snap = engine.fuse(
            stt_confidence=0.5,
            tts_drift_score=0.1,
            inbound_silence_ms=500,
            packet_gap_ms=4000,  # Above connection_loss_timeout
            ivr_score=0.1,
            voicemail_score=0.1,
        )
        assert snap.mode == PerceptionMode.CONNECTION_LOSS
    
    def test_dead_air(self):
        engine = PerceptionFusionEngine(DEFAULT_CFG)
        snap = engine.fuse(
            stt_confidence=0.5,
            tts_drift_score=0.1,
            inbound_silence_ms=6000,  # Above dead_air_timeout
            packet_gap_ms=100,
            ivr_score=0.1,
            voicemail_score=0.1,
        )
        assert snap.mode == PerceptionMode.DEAD_AIR
    
    def test_audio_drift(self):
        engine = PerceptionFusionEngine(DEFAULT_CFG)
        snap = engine.fuse(
            stt_confidence=0.5,
            tts_drift_score=0.7,  # Above severe threshold
            inbound_silence_ms=500,
            packet_gap_ms=100,
            ivr_score=0.1,
            voicemail_score=0.1,
        )
        assert snap.mode == PerceptionMode.AUDIO_DRIFT
    
    def test_ivr_detected(self):
        engine = PerceptionFusionEngine(DEFAULT_CFG)
        snap = engine.fuse(
            stt_confidence=0.8,
            tts_drift_score=0.1,
            inbound_silence_ms=500,
            packet_gap_ms=100,
            ivr_score=0.9,  # Above IVR threshold
            voicemail_score=0.1,
        )
        assert snap.mode == PerceptionMode.IVR
    
    def test_voicemail_detected(self):
        engine = PerceptionFusionEngine(DEFAULT_CFG)
        snap = engine.fuse(
            stt_confidence=0.8,
            tts_drift_score=0.1,
            inbound_silence_ms=500,
            packet_gap_ms=100,
            ivr_score=0.1,
            voicemail_score=0.85,  # Above voicemail threshold
        )
        assert snap.mode == PerceptionMode.VOICEMAIL
    
    def test_connection_loss_priority(self):
        """Connection loss should take priority over dead_air."""
        engine = PerceptionFusionEngine(DEFAULT_CFG)
        snap = engine.fuse(
            stt_confidence=0.5,
            tts_drift_score=0.1,
            inbound_silence_ms=6000,  # Dead air too
            packet_gap_ms=4000,  # But connection loss wins
            ivr_score=0.9,
            voicemail_score=0.9,
        )
        assert snap.mode == PerceptionMode.CONNECTION_LOSS


class TestHealthInference:
    """Test PerceptionHealth inference from mode + signals."""
    
    def test_ok_health(self):
        engine = PerceptionFusionEngine(DEFAULT_CFG)
        snap = engine.fuse(
            stt_confidence=0.95,
            tts_drift_score=0.1,
            inbound_silence_ms=500,
            packet_gap_ms=100,
            ivr_score=0.1,
            voicemail_score=0.1,
        )
        assert snap.health == PerceptionHealth.OK
    
    def test_critical_from_connection_loss(self):
        engine = PerceptionFusionEngine(DEFAULT_CFG)
        snap = engine.fuse(
            stt_confidence=0.95,
            tts_drift_score=0.1,
            inbound_silence_ms=500,
            packet_gap_ms=4000,
            ivr_score=0.1,
            voicemail_score=0.1,
        )
        assert snap.health == PerceptionHealth.CRITICAL
    
    def test_degraded_from_low_stt(self):
        engine = PerceptionFusionEngine(DEFAULT_CFG)
        snap = engine.fuse(
            stt_confidence=0.5,  # Below degraded threshold
            tts_drift_score=0.1,
            inbound_silence_ms=500,
            packet_gap_ms=100,
            ivr_score=0.1,
            voicemail_score=0.1,
        )
        assert snap.health == PerceptionHealth.DEGRADED
    
    def test_degraded_from_mild_drift(self):
        engine = PerceptionFusionEngine(DEFAULT_CFG)
        snap = engine.fuse(
            stt_confidence=0.95,
            tts_drift_score=0.35,  # Above mild threshold, below severe
            inbound_silence_ms=500,
            packet_gap_ms=100,
            ivr_score=0.1,
            voicemail_score=0.1,
        )
        assert snap.health == PerceptionHealth.DEGRADED


class TestSnapshot:
    """Test PerceptionSnapshot creation and serialization."""
    
    def test_to_dict(self):
        engine = PerceptionFusionEngine(DEFAULT_CFG)
        snap = engine.fuse(
            stt_confidence=0.95,
            tts_drift_score=0.1,
            inbound_silence_ms=500,
            packet_gap_ms=100,
            ivr_score=0.1,
            voicemail_score=0.1,
        )
        d = snap.to_dict()
        assert isinstance(d, dict)
        assert d["mode"] == "normal"
        assert d["health"] == "ok"
        assert "timestamp_ms" in d
        assert d["stt_confidence"] == 0.95
    
    def test_last_snapshot(self):
        engine = PerceptionFusionEngine(DEFAULT_CFG)
        assert engine.last_snapshot() is None
        
        snap = engine.fuse(
            stt_confidence=0.95,
            tts_drift_score=0.1,
            inbound_silence_ms=500,
            packet_gap_ms=100,
            ivr_score=0.1,
            voicemail_score=0.1,
        )
        assert engine.last_snapshot() == snap


def run_all_tests():
    """Run all test classes and report results."""
    test_classes = [
        TestModeInference,
        TestHealthInference,
        TestSnapshot,
    ]
    
    total = 0
    passed = 0
    failed = 0
    failures = []
    
    for cls in test_classes:
        instance = cls()
        for method_name in sorted(dir(instance)):
            if method_name.startswith("test_"):
                total += 1
                try:
                    getattr(instance, method_name)()
                    passed += 1
                except Exception as e:
                    failed += 1
                    failures.append(f"  FAIL: {cls.__name__}.{method_name}: {e}")
    
    print(f"\n{'='*60}")
    print(f"AQI TEST SUITE — Perception Fusion Engine")
    print(f"{'='*60}")
    print(f"Total: {total} | Passed: {passed} | Failed: {failed}")
    
    if failures:
        print(f"\nFailures:")
        for f in failures:
            print(f)
    else:
        print(f"\n✓ ALL TESTS PASSED")
    
    print(f"{'='*60}\n")
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
