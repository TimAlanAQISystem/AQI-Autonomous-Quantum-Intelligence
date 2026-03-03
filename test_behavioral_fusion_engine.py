import unittest
from behavioral_fusion_engine import (
    BehavioralFusionEngine,
    BehavioralMode,
    BehavioralHealth,
)

BASE_CFG = {
    "stall_velocity_threshold": 0.05,
    "stall_turn_threshold": 8,
    "high_viscosity_threshold": 1.4,
    "high_objection_threshold": 3,
    "collapse_drift_threshold": -0.6,
    "recovery_velocity_threshold": 0.25,
    "high_drift_threshold": 0.7,
    "low_drift_threshold": 0.2,
    "optimal_velocity_threshold": 0.4,
}

class TestBehavioralFusionEngine(unittest.TestCase):
    def setUp(self):
        self.eng = BehavioralFusionEngine(BASE_CFG)

    def test_normal_stable(self):
        snap = self.eng.fuse(
            fluidic_state="DISCOVERY",
            trajectory_velocity=0.3,
            trajectory_drift=0.1,
            emotional_viscosity=1.0,
            objection_count=0,
            objections_resolved=0,
            turn_count=4,
            perception_mode="normal",
            perception_health="ok",
        )
        self.assertEqual(snap.mode, BehavioralMode.NORMAL)
        self.assertEqual(snap.health, BehavioralHealth.STABLE)

    def test_stalled(self):
        snap = self.eng.fuse(
            fluidic_state="DISCOVERY",
            trajectory_velocity=0.01,
            trajectory_drift=0.1,
            emotional_viscosity=1.0,
            objection_count=1,
            objections_resolved=0,
            turn_count=10,
            perception_mode="normal",
            perception_health="ok",
        )
        self.assertEqual(snap.mode, BehavioralMode.STALLED)

    def test_high_friction(self):
        snap = self.eng.fuse(
            fluidic_state="NEGOTIATION",
            trajectory_velocity=0.2,
            trajectory_drift=0.3,
            emotional_viscosity=1.6,
            objection_count=4,
            objections_resolved=1,
            turn_count=6,
            perception_mode="normal",
            perception_health="ok",
        )
        self.assertEqual(snap.mode, BehavioralMode.HIGH_FRICTION)
        # Viscosity 1.6 > 1.4 -> FRAGILE
        self.assertEqual(snap.health, BehavioralHealth.FRAGILE)

    def test_collapsed_failed(self):
        snap = self.eng.fuse(
            fluidic_state="CLOSING",
            trajectory_velocity=0.05,
            trajectory_drift=-0.8,
            emotional_viscosity=1.2,
            objection_count=2,
            objections_resolved=0,
            turn_count=5,
            perception_mode="normal",
            perception_health="ok",
        )
        self.assertEqual(snap.mode, BehavioralMode.COLLAPSED)
        self.assertEqual(snap.health, BehavioralHealth.FAILED)

    def test_optimal(self):
        snap = self.eng.fuse(
            fluidic_state="NEGOTIATION",
            trajectory_velocity=0.5,
            trajectory_drift=0.05,
            emotional_viscosity=0.9,
            objection_count=1,
            objections_resolved=1,
            turn_count=7,
            perception_mode="normal",
            perception_health="ok",
        )
        self.assertEqual(snap.health, BehavioralHealth.OPTIMAL)

if __name__ == "__main__":
    unittest.main()
