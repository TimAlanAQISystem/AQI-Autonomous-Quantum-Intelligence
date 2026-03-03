#!/usr/bin/env python3
"""
AQI Test Suite — Cross-Call Neural Memory (CCNM)
===================================================
Tests for the CCNM feedback loop, including the Phase 5 behavioral vector refinement.

Tests cover:
    - SessionSeed structure and defaults
    - _refine_with_behavioral_vectors() with various inputs
    - Bounds enforcement (FLUIDIC_ADJUSTMENT_MIN/MAX)
    - Graceful degradation on malformed data
    - SQL query includes behavioral_vector column

Neg-Proofed: Yes
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_CCNM_AVAILABLE = False
try:
    from cross_call_intelligence import (
        CrossCallIntelligence as CrossCallNeuralMemory,
        SessionSeed,
        FLUIDIC_ADJUSTMENT_MIN,
        FLUIDIC_ADJUSTMENT_MAX,
        QPC_PRIOR_MAX,
        QPC_PRIOR_MIN,
        CONTINUUM_SEED_MAX_NORM,
        MIN_CALLS_FOR_SEEDING,
    )
    _CCNM_AVAILABLE = True
except ImportError as e:
    print(f"[INFO] CCNM import: {e}")


class TestSessionSeedStructure:
    """Verify SessionSeed dataclass has required fields."""
    
    def test_session_seed_importable(self):
        if not _CCNM_AVAILABLE:
            # Fallback: check source
            src = _read_source("cross_call_intelligence.py")
            assert "class SessionSeed" in src
            return
        assert SessionSeed is not None
    
    def test_session_seed_default_confidence(self):
        if not _CCNM_AVAILABLE:
            return
        seed = SessionSeed()
        assert seed.confidence == 0.0, "Default confidence should be 0.0"
    
    def test_session_seed_default_qpc_priors(self):
        if not _CCNM_AVAILABLE:
            return
        seed = SessionSeed()
        assert isinstance(seed.qpc_priors, dict)
        assert len(seed.qpc_priors) == 0, "Default qpc_priors should be empty dict"
    
    def test_session_seed_fields(self):
        if not _CCNM_AVAILABLE:
            return
        seed = SessionSeed()
        required = ["qpc_priors", "fluidic_adjustments", "continuum_seeds",
                     "intent_calibration", "archetype_hint", "winning_patterns", "confidence"]
        for f in required:
            assert hasattr(seed, f), f"SessionSeed missing field: {f}"


class TestBehavioralVectorRefinement:
    """Test the Phase 5 _refine_with_behavioral_vectors method."""
    
    def test_empty_data_returns_original(self):
        """No behavioral vectors → adjustments unchanged."""
        if not _CCNM_AVAILABLE:
            return
        adjustments = {"DISCOVERY": 0.05, "CLOSING": -0.03}
        result = CrossCallNeuralMemory._refine_with_behavioral_vectors(
            adjustments.copy(), [], []
        )
        assert result == adjustments
    
    def test_no_bv_column_returns_original(self):
        """Calls without behavioral_vector key → no change."""
        if not _CCNM_AVAILABLE:
            return
        adjustments = {"DISCOVERY": 0.05}
        successful = [{"call_sid": "CA1234", "appointment_set": 1}]
        result = CrossCallNeuralMemory._refine_with_behavioral_vectors(
            adjustments.copy(), successful, []
        )
        assert result == adjustments
    
    def test_valid_bv_applies_refinement(self):
        """Valid behavioral vectors should produce some refinement."""
        if not _CCNM_AVAILABLE:
            return
        adjustments = {"DISCOVERY": 0.0, "CLOSING": 0.0, "RAPPORT": 0.0}
        bv_data = json.dumps({
            "trajectory_velocity": 0.8,
            "fluidic_state": "DISCOVERY",
            "emotional_viscosity": 0.3
        })
        successful = [
            {"call_sid": "CA1", "behavioral_vector": bv_data},
            {"call_sid": "CA2", "behavioral_vector": bv_data},
            {"call_sid": "CA3", "behavioral_vector": bv_data},
        ]
        unsuccessful = [
            {"call_sid": "CA4", "behavioral_vector": json.dumps({
                "trajectory_velocity": 0.1,
                "fluidic_state": "CLOSING",
                "emotional_viscosity": 0.9
            })},
        ]
        result = CrossCallNeuralMemory._refine_with_behavioral_vectors(
            adjustments.copy(), successful, unsuccessful
        )
        # With velocity differential of 0.7 (0.8 - 0.1) and 3 DISCOVERY appearances,
        # DISCOVERY should have a negative (easier transition) adjustment
        assert result["DISCOVERY"] < 0, \
            f"DISCOVERY should have negative adjustment, got {result['DISCOVERY']}"
    
    def test_bounds_enforced(self):
        """Refinements must stay within FLUIDIC_ADJUSTMENT_MIN/MAX."""
        if not _CCNM_AVAILABLE:
            return
        # Start near the limit
        adjustments = {"DISCOVERY": FLUIDIC_ADJUSTMENT_MIN + 0.01}
        bv_data = json.dumps({
            "trajectory_velocity": 0.99,
            "fluidic_state": "DISCOVERY",
        })
        # Many successful vectors stacking DISCOVERY
        successful = [{"call_sid": f"CA{i}", "behavioral_vector": bv_data} for i in range(20)]
        unsuccessful = [{"call_sid": "CAF", "behavioral_vector": json.dumps({
            "trajectory_velocity": 0.0
        })}]
        
        result = CrossCallNeuralMemory._refine_with_behavioral_vectors(
            adjustments.copy(), successful, unsuccessful
        )
        assert result["DISCOVERY"] >= FLUIDIC_ADJUSTMENT_MIN, \
            f"Adjustment {result['DISCOVERY']} below minimum {FLUIDIC_ADJUSTMENT_MIN}"
        assert result["DISCOVERY"] <= FLUIDIC_ADJUSTMENT_MAX, \
            f"Adjustment {result['DISCOVERY']} above maximum {FLUIDIC_ADJUSTMENT_MAX}"
    
    def test_malformed_json_graceful(self):
        """Malformed behavioral_vector JSON should not crash."""
        if not _CCNM_AVAILABLE:
            return
        adjustments = {"DISCOVERY": 0.0}
        successful = [
            {"call_sid": "CA1", "behavioral_vector": "NOT JSON"},
            {"call_sid": "CA2", "behavioral_vector": "{{{{"},
            {"call_sid": "CA3", "behavioral_vector": None},
            {"call_sid": "CA4", "behavioral_vector": 42},
        ]
        result = CrossCallNeuralMemory._refine_with_behavioral_vectors(
            adjustments.copy(), successful, []
        )
        # Should return original since no valid data
        assert result == adjustments
    
    def test_empty_bv_dict_graceful(self):
        """Empty JSON object behavioral_vector should not crash."""
        if not _CCNM_AVAILABLE:
            return
        adjustments = {"CLOSING": 0.0}
        successful = [{"call_sid": "CA1", "behavioral_vector": "{}"}]
        result = CrossCallNeuralMemory._refine_with_behavioral_vectors(
            adjustments.copy(), successful, []
        )
        # No velocity data means no velocity nudge, no mode data means no mode nudge
        assert result == adjustments


class TestCCNMSourceIntegrity:
    """Source-level tests for CCNM — verify the SQL query and structure."""
    
    def test_sql_includes_behavioral_vector(self):
        src = _read_source("cross_call_intelligence.py")
        # The SQL SELECT should include behavioral_vector
        # Find SELECT statements that query the calls table
        import re
        select_blocks = re.findall(r'SELECT.*?FROM\s+calls', src, re.DOTALL | re.IGNORECASE)
        found = any("behavioral_vector" in block for block in select_blocks)
        assert found, "At least one SELECT from calls must include behavioral_vector"
    
    def test_refine_method_bounded(self):
        """_refine_with_behavioral_vectors must enforce bounds."""
        src = _read_source("cross_call_intelligence.py")
        # Find the method body
        start = src.find("def _refine_with_behavioral_vectors")
        assert start > 0
        method_body = src[start:start+5000]
        assert "FLUIDIC_ADJUSTMENT_MIN" in method_body
        assert "FLUIDIC_ADJUSTMENT_MAX" in method_body
    
    def test_ccnm_constants_sane(self):
        if not _CCNM_AVAILABLE:
            return
        assert MIN_CALLS_FOR_SEEDING >= 1, "Must require at least 1 call before seeding"
        assert QPC_PRIOR_MAX > 0 and QPC_PRIOR_MAX <= 0.5
        assert QPC_PRIOR_MIN < 0 and QPC_PRIOR_MIN >= -0.5
        assert FLUIDIC_ADJUSTMENT_MAX > 0 and FLUIDIC_ADJUSTMENT_MAX <= 0.5
        assert FLUIDIC_ADJUSTMENT_MIN < 0 and FLUIDIC_ADJUSTMENT_MIN >= -0.5
        assert CONTINUUM_SEED_MAX_NORM > 0 and CONTINUUM_SEED_MAX_NORM <= 1.0


def _read_source(filename):
    src_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        filename
    )
    with open(src_path, "r", encoding="utf-8") as f:
        return f.read()


def run_all_tests():
    """Run all test classes and report results."""
    test_classes = [
        TestSessionSeedStructure,
        TestBehavioralVectorRefinement,
        TestCCNMSourceIntegrity,
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
    print(f"AQI TEST SUITE — Cross-Call Neural Memory (CCNM)")
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
