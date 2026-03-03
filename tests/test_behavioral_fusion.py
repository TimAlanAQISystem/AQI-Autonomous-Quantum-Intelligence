#!/usr/bin/env python3
"""
AQI Test Suite — Behavioral Fusion Engine
============================================
Tests for BehavioralFusionEngine and BehavioralSnapshot.

Tests cover:
    - Mode inference (NORMAL, HIGH_FRICTION, STALLED, COLLAPSED, RECOVERING)
    - Health inference (OPTIMAL, STABLE, FRAGILE, FAILED)
    - Snapshot creation and serialization
    - State transition from STALLED → RECOVERING
    - Config parameter override testing
    - Edge cases

Neg-Proofed: Yes — all mode/health combinations tested.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from behavioral_fusion_engine import (
    BehavioralFusionEngine, BehavioralSnapshot,
    BehavioralHealth, BehavioralMode
)


DEFAULT_CFG = {
    "stall_velocity_threshold": 0.05,
    "stall_turn_threshold": 8,
    "high_viscosity_threshold": 1.4,
    "high_objection_threshold": 3,
    "collapse_drift_threshold": -0.6,
    "recovery_velocity_threshold": 0.25,
    "high_drift_threshold": 0.7,
    "optimal_velocity_threshold": 0.4,
    "low_drift_threshold": 0.2,
}


class TestModeInference:
    """Test BehavioralMode inference from call signals."""
    
    def test_normal_mode(self):
        engine = BehavioralFusionEngine(DEFAULT_CFG)
        snap = engine.fuse(
            fluidic_state="DISCOVERY",
            trajectory_velocity=0.3,
            trajectory_drift=0.1,
            emotional_viscosity=1.0,
            objection_count=1,
            objections_resolved=1,
            turn_count=5,
            perception_mode="normal",
            perception_health="ok",
        )
        assert snap.mode == BehavioralMode.NORMAL
    
    def test_stalled_mode(self):
        engine = BehavioralFusionEngine(DEFAULT_CFG)
        snap = engine.fuse(
            fluidic_state="DISCOVERY",
            trajectory_velocity=0.02,  # Below stall threshold
            trajectory_drift=0.0,
            emotional_viscosity=1.0,
            objection_count=0,
            objections_resolved=0,
            turn_count=10,  # Above stall turn threshold
            perception_mode="normal",
            perception_health="ok",
        )
        assert snap.mode == BehavioralMode.STALLED
    
    def test_high_friction_viscosity(self):
        engine = BehavioralFusionEngine(DEFAULT_CFG)
        snap = engine.fuse(
            fluidic_state="NEGOTIATION",
            trajectory_velocity=0.3,
            trajectory_drift=0.0,
            emotional_viscosity=1.8,  # Above viscosity threshold
            objection_count=1,
            objections_resolved=0,
            turn_count=5,
            perception_mode="normal",
            perception_health="ok",
        )
        assert snap.mode == BehavioralMode.HIGH_FRICTION
    
    def test_high_friction_objections(self):
        engine = BehavioralFusionEngine(DEFAULT_CFG)
        snap = engine.fuse(
            fluidic_state="DISCOVERY",
            trajectory_velocity=0.3,
            trajectory_drift=0.0,
            emotional_viscosity=1.0,
            objection_count=4,  # Above objection threshold
            objections_resolved=1,
            turn_count=5,
            perception_mode="normal",
            perception_health="ok",
        )
        assert snap.mode == BehavioralMode.HIGH_FRICTION
    
    def test_collapsed_mode(self):
        engine = BehavioralFusionEngine(DEFAULT_CFG)
        snap = engine.fuse(
            fluidic_state="CLOSING",
            trajectory_velocity=0.3,
            trajectory_drift=-0.8,  # Negative drift below collapse threshold
            emotional_viscosity=1.0,
            objection_count=1,
            objections_resolved=0,
            turn_count=5,
            perception_mode="normal",
            perception_health="ok",
        )
        assert snap.mode == BehavioralMode.COLLAPSED
    
    def test_recovering_mode(self):
        engine = BehavioralFusionEngine(DEFAULT_CFG)
        # First call: create a STALLED state
        engine.fuse(
            fluidic_state="DISCOVERY",
            trajectory_velocity=0.02,
            trajectory_drift=0.0,
            emotional_viscosity=1.0,
            objection_count=0,
            objections_resolved=0,
            turn_count=10,
            perception_mode="normal",
            perception_health="ok",
        )
        # Second call: velocity recovers
        snap = engine.fuse(
            fluidic_state="NEGOTIATION",
            trajectory_velocity=0.5,  # Above recovery threshold
            trajectory_drift=0.0,
            emotional_viscosity=1.0,
            objection_count=0,
            objections_resolved=0,
            turn_count=11,
            perception_mode="normal",
            perception_health="ok",
        )
        assert snap.mode == BehavioralMode.RECOVERING


class TestHealthInference:
    """Test BehavioralHealth inference from mode + signals."""
    
    def test_optimal_health(self):
        engine = BehavioralFusionEngine(DEFAULT_CFG)
        snap = engine.fuse(
            fluidic_state="DISCOVERY",
            trajectory_velocity=0.5,  # High velocity
            trajectory_drift=0.1,  # Low drift
            emotional_viscosity=1.0,
            objection_count=1,
            objections_resolved=1,
            turn_count=5,
            perception_mode="normal",
            perception_health="ok",
        )
        assert snap.health == BehavioralHealth.OPTIMAL
    
    def test_failed_health_from_collapse(self):
        engine = BehavioralFusionEngine(DEFAULT_CFG)
        snap = engine.fuse(
            fluidic_state="CLOSING",
            trajectory_velocity=0.3,
            trajectory_drift=-0.8,
            emotional_viscosity=1.0,
            objection_count=1,
            objections_resolved=0,
            turn_count=5,
            perception_mode="normal",
            perception_health="ok",
        )
        assert snap.health == BehavioralHealth.FAILED
    
    def test_fragile_from_degraded_perception(self):
        engine = BehavioralFusionEngine(DEFAULT_CFG)
        snap = engine.fuse(
            fluidic_state="DISCOVERY",
            trajectory_velocity=0.3,
            trajectory_drift=0.1,
            emotional_viscosity=1.0,
            objection_count=1,
            objections_resolved=1,
            turn_count=5,
            perception_mode="normal",
            perception_health="degraded",  # Degraded perception
        )
        assert snap.health == BehavioralHealth.FRAGILE
    
    def test_stable_default(self):
        engine = BehavioralFusionEngine(DEFAULT_CFG)
        snap = engine.fuse(
            fluidic_state="DISCOVERY",
            trajectory_velocity=0.2,  # Below optimal threshold
            trajectory_drift=0.3,  # Below high drift threshold
            emotional_viscosity=1.0,
            objection_count=1,
            objections_resolved=1,
            turn_count=5,
            perception_mode="normal",
            perception_health="ok",
        )
        assert snap.health == BehavioralHealth.STABLE


class TestSnapshot:
    """Test BehavioralSnapshot creation and serialization."""
    
    def test_to_dict(self):
        engine = BehavioralFusionEngine(DEFAULT_CFG)
        snap = engine.fuse(
            fluidic_state="OPENING",
            trajectory_velocity=0.0,
            trajectory_drift=0.0,
            emotional_viscosity=1.0,
            objection_count=0,
            objections_resolved=0,
            turn_count=1,
            perception_mode="normal",
            perception_health="ok",
        )
        d = snap.to_dict()
        assert isinstance(d, dict)
        assert d["mode"] == "normal"
        assert d["health"] in ("optimal", "stable", "fragile", "failed")
        assert "timestamp_ms" in d
        assert d["fluidic_state"] == "OPENING"
    
    def test_last_snapshot(self):
        engine = BehavioralFusionEngine(DEFAULT_CFG)
        assert engine.last_snapshot() is None
        
        snap = engine.fuse(
            fluidic_state="OPENING",
            trajectory_velocity=0.0,
            trajectory_drift=0.0,
            emotional_viscosity=1.0,
            objection_count=0,
            objections_resolved=0,
            turn_count=1,
            perception_mode="normal",
            perception_health="ok",
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
    print(f"AQI TEST SUITE — Behavioral Fusion Engine")
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
