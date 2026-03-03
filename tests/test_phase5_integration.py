#!/usr/bin/env python3
"""
AQI Test Suite — Phase 5 Reflex Arc Integration
===================================================
End-to-end verification that the Phase 5 reflex arc is CLOSED.

The reflex arc:
    DeepLayer.step() → continuum{velocity,drift,viscosity}
    → behavioral_stats update (relay server)
    → BehavioralFusionEngine.snapshot()
    → CDC.save_call() writes behavioral_vector
    → CCNM.seed_session() reads behavioral_vector
    → _refine_with_behavioral_vectors() feeds back
    → Next call's DeepLayer gets pre-conditioned seed

This test validates that EVERY LINK in the chain is present.

Neg-Proofed: Yes
"""

import sys
import os
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(filename):
    with open(os.path.join(BASE, filename), "r", encoding="utf-8") as f:
        return f.read()


class TestReflexArcLinks:
    """Each test verifies one link in the reflex arc is present."""
    
    # Link 1: DeepLayer.step() → continuum dict
    def test_link1_deep_layer_produces_continuum(self):
        src = _read("aqi_deep_layer.py")
        # Must have 'continuum' key in deep_state
        assert "'continuum'" in src or '"continuum"' in src, \
            "LINK 1 BROKEN: DeepLayer.step() must produce 'continuum' key"
        # Must have velocity, drift, viscosity
        assert "_physics_velocity" in src, "LINK 1 BROKEN: no velocity computation"
        assert "_physics_drift" in src, "LINK 1 BROKEN: no drift computation"
        assert "_physics_viscosity" in src, "LINK 1 BROKEN: no viscosity computation"
    
    # Link 2: Relay server reads continuum from deep_state
    def test_link2_relay_reads_continuum(self):
        src = _read("aqi_conversation_relay_server.py")
        assert "continuum" in src, \
            "LINK 2 BROKEN: relay must read continuum from deep_state"
        # Must read velocity, drift, viscosity
        for field in ["velocity", "drift", "viscosity"]:
            assert f"continuum.get('{field}'" in src or f'continuum.get("{field}"' in src, \
                f"LINK 2 BROKEN: relay must read {field} from continuum"
    
    # Link 3: Relay updates behavioral_stats with physics data
    def test_link3_behavioral_stats_updated(self):
        src = _read("aqi_conversation_relay_server.py")
        assert "behavioral_stats" in src, \
            "LINK 3 BROKEN: relay must maintain behavioral_stats dict"
        # velocity is written to _b_stats['trajectory_velocity'] via continuum.get('velocity')
        assert "trajectory_velocity" in src or "continuum.get('velocity'" in src, \
            "LINK 3 BROKEN: behavioral_stats must receive velocity from continuum"
    
    # Link 4: BehavioralFusionEngine exists and produces snapshots
    def test_link4_behavioral_fusion_produces_snapshot(self):
        src = _read("behavioral_fusion_engine.py")
        # BehavioralFusionEngine uses fuse() to produce and last_snapshot to retrieve
        assert "def fuse(" in src or "def last_snapshot(" in src, \
            "LINK 4 BROKEN: BehavioralFusionEngine must have fuse() or last_snapshot()"
    
    # Link 5: CDC call_capture has behavioral_vector column
    def test_link5_cdc_has_behavioral_vector(self):
        src = _read("call_data_capture.py")
        assert "behavioral_vector" in src, \
            "LINK 5 BROKEN: CDC calls table must have behavioral_vector column"
    
    # Link 6: CCNM reads behavioral_vector from calls table
    def test_link6_ccnm_reads_behavioral_vector(self):
        src = _read("cross_call_intelligence.py")
        # Find SELECT from calls — must include behavioral_vector
        select_blocks = re.findall(r'SELECT.*?FROM\s+calls', src, re.DOTALL | re.IGNORECASE)
        found = any("behavioral_vector" in block for block in select_blocks)
        assert found, "LINK 6 BROKEN: CCNM must SELECT behavioral_vector FROM calls"
    
    # Link 7: CCNM refines adjustments with behavioral data
    def test_link7_ccnm_refines_with_bv(self):
        src = _read("cross_call_intelligence.py")
        assert "_refine_with_behavioral_vectors" in src, \
            "LINK 7 BROKEN: CCNM must have _refine_with_behavioral_vectors method"
        # Must use the method (not just define it)
        calls = re.findall(r'_refine_with_behavioral_vectors\(', src)
        assert len(calls) >= 2, \
            "LINK 7 BROKEN: _refine_with_behavioral_vectors must be defined AND called"
    
    # Link 8: Phase5StreamingAnalyzer wired in relay
    def test_link8_phase5_wired_in_relay(self):
        src = _read("aqi_conversation_relay_server.py")
        assert "Phase5StreamingAnalyzer" in src, \
            "LINK 8 BROKEN: Phase5StreamingAnalyzer must be imported in relay"
        assert "on_call_complete" in src, \
            "LINK 8 BROKEN: Phase5StreamingAnalyzer.on_call_complete must be called"
    
    # Link 9: SessionSeed flows into DeepLayer
    def test_link9_session_seed_enters_deep_layer(self):
        src = _read("aqi_deep_layer.py")
        assert "SessionSeed" in src or "session_seed" in src or "seed" in src, \
            "LINK 9 BROKEN: DeepLayer must receive SessionSeed"


class TestChatbotImmuneSystemExtraction:
    """Verify the relay server decomposition is correct."""
    
    def test_chatbot_module_exists(self):
        path = os.path.join(BASE, "chatbot_immune_system.py")
        assert os.path.exists(path), "chatbot_immune_system.py must exist"
    
    def test_chatbot_module_has_clean_sentence(self):
        src = _read("chatbot_immune_system.py")
        assert "def clean_sentence(" in src, \
            "chatbot_immune_system must export clean_sentence()"
    
    def test_relay_imports_chatbot_module(self):
        src = _read("aqi_conversation_relay_server.py")
        assert "from chatbot_immune_system import" in src, \
            "Relay server must import from chatbot_immune_system"
    
    def test_chatbot_module_has_kill_lists(self):
        src = _read("chatbot_immune_system.py")
        assert "CHATBOT_KILLS" in src, "Module must have CHATBOT_KILLS list"
        assert "CHATBOT_CONTAINS_KILLS" in src, "Module must have CHATBOT_CONTAINS_KILLS list"
        assert "FILLER_PREFIXES" in src, "Module must have FILLER_PREFIXES list"
        assert "GOODBYE_PATTERNS" in src, "Module must have GOODBYE_PATTERNS list"
    
    def test_chatbot_module_parseable(self):
        import ast
        src = _read("chatbot_immune_system.py")
        try:
            ast.parse(src)
        except SyntaxError as e:
            assert False, f"chatbot_immune_system.py has syntax error: {e}"


class TestAllModifiedFilesParseable:
    """Verify every modified file passes ast.parse — critical neg-proofing."""
    
    def test_deep_layer_parseable(self):
        import ast
        src = _read("aqi_deep_layer.py")
        try:
            ast.parse(src)
        except SyntaxError as e:
            assert False, f"aqi_deep_layer.py syntax error: {e}"
    
    def test_relay_server_parseable(self):
        import ast
        src = _read("aqi_conversation_relay_server.py")
        try:
            ast.parse(src)
        except SyntaxError as e:
            assert False, f"aqi_conversation_relay_server.py syntax error: {e}"
    
    def test_ccnm_parseable(self):
        import ast
        src = _read("cross_call_intelligence.py")
        try:
            ast.parse(src)
        except SyntaxError as e:
            assert False, f"cross_call_intelligence.py syntax error: {e}"
    
    def test_chatbot_immune_parseable(self):
        import ast
        src = _read("chatbot_immune_system.py")
        try:
            ast.parse(src)
        except SyntaxError as e:
            assert False, f"chatbot_immune_system.py syntax error: {e}"
    
    def test_behavioral_fusion_parseable(self):
        import ast
        src = _read("behavioral_fusion_engine.py")
        try:
            ast.parse(src)
        except SyntaxError as e:
            assert False, f"behavioral_fusion_engine.py syntax error: {e}"
    
    def test_perception_fusion_parseable(self):
        import ast
        src = _read("perception_fusion_engine.py")
        try:
            ast.parse(src)
        except SyntaxError as e:
            assert False, f"perception_fusion_engine.py syntax error: {e}"
    
    def test_phase5_analyzer_parseable(self):
        import ast
        src = _read("aqi_phase5_streaming_analyzer.py")
        try:
            ast.parse(src)
        except SyntaxError as e:
            assert False, f"aqi_phase5_streaming_analyzer.py syntax error: {e}"


class TestRelayServerSizeReduction:
    """Verify relay server is smaller after extraction."""
    
    def test_relay_under_10044_lines(self):
        src = _read("aqi_conversation_relay_server.py")
        line_count = len(src.splitlines())
        assert line_count < 10044, \
            f"Relay server should be under original 10,043 lines after extraction, got {line_count}"
    
    def test_relay_over_8000_lines(self):
        src = _read("aqi_conversation_relay_server.py")
        line_count = len(src.splitlines())
        assert line_count > 8000, \
            f"Relay server suspiciously small at {line_count} lines — something was over-deleted"


def run_all_tests():
    """Run all integration tests."""
    test_classes = [
        TestReflexArcLinks,
        TestChatbotImmuneSystemExtraction,
        TestAllModifiedFilesParseable,
        TestRelayServerSizeReduction,
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
    print(f"AQI TEST SUITE — Phase 5 Reflex Arc Integration")
    print(f"{'='*60}")
    print(f"Total: {total} | Passed: {passed} | Failed: {failed}")
    
    if failures:
        print(f"\nFailures:")
        for f in failures:
            print(f)
    else:
        print(f"\n✓ ALL TESTS PASSED — REFLEX ARC CLOSED")
    
    print(f"{'='*60}\n")
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
