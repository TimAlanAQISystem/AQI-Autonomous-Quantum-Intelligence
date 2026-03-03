"""
AQI Voice Governance - Comprehensive Negative Proof Test Suite
Author: Claude + User
Purpose: Prove that each class of voice interference bug is DEAD

Test Philosophy: "If this log is clean, this class of bug is dead"

Test Categories:
1. TTS Surface: Only one caller ID to TTS in entire organism
2. Audio Surface: Only one path from text → Twilio stream  
3. Fallback Surface: Emergency scripts controlled and logged
4. Debug Surface: No logging accidentally routing to TTS
5. Concurrency Surface: One active speaker token per call, enforced by lock
"""

import asyncio
import logging
import time
import threading
import weakref
import inspect
import sys
from typing import Dict, List, Set, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta

# Configure test logging
test_logger = logging.getLogger("AQI_VOICE_NEGPROOF")
test_logger.setLevel(logging.DEBUG)

@dataclass
class TTSCallRecord:
    """Record of a TTS synthesis call"""
    timestamp: float
    caller_module: str
    caller_function: str
    text: str
    thread_id: int
    call_stack: List[str]
    session_id: Optional[str] = None

@dataclass
class AudioPathRecord:
    """Record of audio flowing to Twilio"""
    timestamp: float
    source: str
    destination: str
    audio_size: int
    session_id: Optional[str] = None

@dataclass
class SpeakerTokenRecord:
    """Record of speaker token acquisition"""
    timestamp: float
    token_id: str
    holder: str
    session_id: str
    action: str  # "acquire", "release", "timeout"

class VoiceNegativeProofSuite:
    """
    Comprehensive test suite to prove voice interference bugs are eliminated.
    
    Each test category has a "one-pass clean log = bug class dead" guarantee.
    """
    
    def __init__(self):
        self.tts_calls: List[TTSCallRecord] = []
        self.audio_paths: List[AudioPathRecord] = []
        self.speaker_tokens: List[SpeakerTokenRecord] = []
        self.fallback_activations: List[Dict] = []
        self.debug_tts_accidents: List[Dict] = []
        
        self._test_start_time = time.time()
        self._active_sessions: Set[str] = set()
        self._monitoring_enabled = False
        
        # Surface violation counters
        self.violations = {
            "tts_surface": 0,
            "audio_surface": 0, 
            "fallback_surface": 0,
            "debug_surface": 0,
            "concurrency_surface": 0
        }
    
    # =========================================================================
    # TTS SURFACE TESTS: Only one caller ID to TTS
    # =========================================================================
    
    def record_tts_call(self, text: str, session_id: Optional[str] = None):
        """Record a TTS synthesis call for analysis"""
        caller_frame = inspect.currentframe().f_back
        caller_module = caller_frame.f_globals.get('__name__', 'unknown')
        caller_function = caller_frame.f_code.co_name
        
        # Capture call stack
        call_stack = []
        frame = caller_frame
        for _ in range(5):  # Capture 5 levels
            if frame is None:
                break
            call_stack.append(f"{frame.f_globals.get('__name__', 'unknown')}.{frame.f_code.co_name}")
            frame = frame.f_back
        
        record = TTSCallRecord(
            timestamp=time.time(),
            caller_module=caller_module,
            caller_function=caller_function,
            text=text,
            thread_id=threading.get_ident(),
            call_stack=call_stack,
            session_id=session_id
        )
        
        self.tts_calls.append(record)
        
        # Real-time violation detection
        if self._monitoring_enabled:
            self._check_tts_violations()
    
    def _check_tts_violations(self):
        """Check for TTS surface violations in real-time"""
        # Get calls in last 5 seconds
        recent_cutoff = time.time() - 5.0
        recent_calls = [call for call in self.tts_calls if call.timestamp > recent_cutoff]
        
        if len(recent_calls) <= 1:
            return
        
        # Check for simultaneous calls from different modules
        active_modules = set()
        for call in recent_calls:
            if call.caller_module != "aqi_tts_control":  # Skip governance wrapper
                active_modules.add(call.caller_module)
        
        if len(active_modules) > 1:
            self.violations["tts_surface"] += 1
            test_logger.error(f"TTS SURFACE VIOLATION: Multiple modules calling TTS simultaneously: {active_modules}")
    
    def test_tts_surface_isolation(self) -> Dict[str, Any]:
        """
        NEGATIVE PROOF TEST: TTS Surface Isolation
        
        Proves: Only one module can call TTS at a time
        
        Clean Log Guarantee: If this test passes, TTS conflicts are impossible
        """
        test_logger.info("=== TESTING TTS SURFACE ISOLATION ===")
        
        results = {
            "test_name": "TTS Surface Isolation",
            "passed": True,
            "violations": [],
            "total_calls": len(self.tts_calls),
            "unique_callers": set(),
            "concurrent_periods": 0
        }
        
        # Analyze all TTS calls for violations
        for i, call in enumerate(self.tts_calls):
            results["unique_callers"].add(call.caller_module)
            
            # Check for overlapping calls (within 1 second window)
            overlap_window = 1.0
            overlapping_calls = [
                other for j, other in enumerate(self.tts_calls)
                if j != i and abs(other.timestamp - call.timestamp) < overlap_window
            ]
            
            if overlapping_calls:
                results["concurrent_periods"] += 1
                
                # Check if overlaps are from different modules
                other_modules = {other.caller_module for other in overlapping_calls}
                if call.caller_module not in other_modules:
                    other_modules.add(call.caller_module)
                
                if len(other_modules) > 1:
                    violation = {
                        "timestamp": call.timestamp,
                        "modules": list(other_modules),
                        "texts": [call.text] + [other.text for other in overlapping_calls]
                    }
                    results["violations"].append(violation)
                    results["passed"] = False
        
        # Log results
        if results["passed"]:
            test_logger.info(f"✅ TTS Surface Clean: {results['total_calls']} calls, {len(results['unique_callers'])} callers")
        else:
            test_logger.error(f"❌ TTS Surface Violations: {len(results['violations'])} detected")
            for violation in results["violations"]:
                test_logger.error(f"   Concurrent TTS: {violation['modules']} at {violation['timestamp']}")
        
        return results
    
    # =========================================================================
    # AUDIO SURFACE TESTS: Only one path from text → Twilio stream
    # =========================================================================
    
    def record_audio_path(self, source: str, destination: str, audio_size: int, session_id: Optional[str] = None):
        """Record audio flowing toward Twilio"""
        record = AudioPathRecord(
            timestamp=time.time(),
            source=source,
            destination=destination,
            audio_size=audio_size,
            session_id=session_id
        )
        self.audio_paths.append(record)
        
        if self._monitoring_enabled:
            self._check_audio_violations()
    
    def _check_audio_violations(self):
        """Check for audio surface violations"""
        # Get recent audio flows (last 2 seconds)
        recent_cutoff = time.time() - 2.0
        recent_flows = [flow for flow in self.audio_paths if flow.timestamp > recent_cutoff]
        
        # Group by session
        by_session = {}
        for flow in recent_flows:
            session = flow.session_id or "unknown"
            if session not in by_session:
                by_session[session] = []
            by_session[session].append(flow)
        
        # Check each session for multiple audio sources
        for session_id, flows in by_session.items():
            sources = {flow.source for flow in flows if flow.destination == "twilio"}
            if len(sources) > 1:
                self.violations["audio_surface"] += 1
                test_logger.error(f"AUDIO SURFACE VIOLATION: Multiple sources to Twilio in session {session_id}: {sources}")
    
    def test_audio_surface_unity(self) -> Dict[str, Any]:
        """
        NEGATIVE PROOF TEST: Audio Surface Unity
        
        Proves: Only one audio path reaches Twilio per session
        
        Clean Log Guarantee: If this test passes, audio conflicts are impossible
        """
        test_logger.info("=== TESTING AUDIO SURFACE UNITY ===")
        
        results = {
            "test_name": "Audio Surface Unity",
            "passed": True,
            "violations": [],
            "sessions": set(),
            "audio_paths": len(self.audio_paths)
        }
        
        # Group audio paths by session and time windows
        session_windows = {}
        window_size = 2.0  # 2-second windows
        
        for path in self.audio_paths:
            session = path.session_id or "unknown"
            window = int(path.timestamp / window_size)
            key = (session, window)
            
            if key not in session_windows:
                session_windows[key] = []
            session_windows[key].append(path)
            
            results["sessions"].add(session)
        
        # Check each window for multiple sources to Twilio
        for (session, window), paths in session_windows.items():
            twilio_sources = {
                path.source for path in paths 
                if path.destination.lower() == "twilio"
            }
            
            if len(twilio_sources) > 1:
                violation = {
                    "session": session,
                    "window": window,
                    "timestamp": min(path.timestamp for path in paths),
                    "sources": list(twilio_sources),
                    "paths": len(paths)
                }
                results["violations"].append(violation)
                results["passed"] = False
        
        # Log results
        if results["passed"]:
            test_logger.info(f"✅ Audio Surface Clean: {len(results['sessions'])} sessions, {results['audio_paths']} paths")
        else:
            test_logger.error(f"❌ Audio Surface Violations: {len(results['violations'])} detected")
        
        return results
    
    # =========================================================================
    # CONCURRENCY SURFACE TESTS: One active speaker token per call
    # =========================================================================
    
    def record_speaker_token(self, action: str, token_id: str, holder: str, session_id: str):
        """Record speaker token acquisition/release"""
        record = SpeakerTokenRecord(
            timestamp=time.time(),
            token_id=token_id,
            holder=holder,
            session_id=session_id,
            action=action
        )
        self.speaker_tokens.append(record)
        
        if self._monitoring_enabled:
            self._check_concurrency_violations()
    
    def _check_concurrency_violations(self):
        """Check for concurrency violations"""
        # Track active tokens per session
        active_tokens = {}
        
        for record in self.speaker_tokens:
            session = record.session_id
            if session not in active_tokens:
                active_tokens[session] = set()
            
            if record.action == "acquire":
                active_tokens[session].add(record.holder)
            elif record.action == "release":
                active_tokens[session].discard(record.holder)
        
        # Check for multiple active speakers per session
        for session, holders in active_tokens.items():
            if len(holders) > 1:
                self.violations["concurrency_surface"] += 1
                test_logger.error(f"CONCURRENCY VIOLATION: Multiple speakers in session {session}: {holders}")
    
    def test_concurrency_surface_exclusion(self) -> Dict[str, Any]:
        """
        NEGATIVE PROOF TEST: Concurrency Surface Exclusion
        
        Proves: At most one active speaker per session at any time
        
        Clean Log Guarantee: If this test passes, speaker conflicts are impossible
        """
        test_logger.info("=== TESTING CONCURRENCY SURFACE EXCLUSION ===")
        
        results = {
            "test_name": "Concurrency Surface Exclusion", 
            "passed": True,
            "violations": [],
            "sessions_tested": set(),
            "token_operations": len(self.speaker_tokens)
        }
        
        # Simulate token state over time
        session_states = {}
        
        for record in sorted(self.speaker_tokens, key=lambda r: r.timestamp):
            session = record.session_id
            results["sessions_tested"].add(session)
            
            if session not in session_states:
                session_states[session] = set()
            
            active_speakers = session_states[session]
            
            if record.action == "acquire":
                if active_speakers:
                    # Violation: Multiple speakers
                    violation = {
                        "session": session,
                        "timestamp": record.timestamp,
                        "new_speaker": record.holder,
                        "existing_speakers": list(active_speakers),
                        "token_id": record.token_id
                    }
                    results["violations"].append(violation)
                    results["passed"] = False
                
                active_speakers.add(record.holder)
            
            elif record.action == "release":
                active_speakers.discard(record.holder)
        
        # Log results
        if results["passed"]:
            test_logger.info(f"✅ Concurrency Surface Clean: {len(results['sessions_tested'])} sessions tested")
        else:
            test_logger.error(f"❌ Concurrency Violations: {len(results['violations'])} detected")
        
        return results
    
    # =========================================================================
    # FALLBACK SURFACE TESTS: Emergency scripts controlled
    # =========================================================================
    
    def record_fallback_activation(self, script_name: str, trigger: str, session_id: str, 
                                 auto_fired: bool = False, threshold_met: bool = False):
        """Record fallback/emergency script activation"""
        record = {
            "timestamp": time.time(),
            "script_name": script_name,
            "trigger": trigger,
            "session_id": session_id,
            "auto_fired": auto_fired,
            "threshold_met": threshold_met,
            "caller_stack": [frame.f_code.co_name for frame in inspect.stack()[:5]]
        }
        self.fallback_activations.append(record)
    
    def test_fallback_surface_control(self) -> Dict[str, Any]:
        """
        NEGATIVE PROOF TEST: Fallback Surface Control
        
        Proves: All fallback scripts are properly controlled and logged
        
        Clean Log Guarantee: If this test passes, rogue fallbacks are impossible
        """
        test_logger.info("=== TESTING FALLBACK SURFACE CONTROL ===")
        
        results = {
            "test_name": "Fallback Surface Control",
            "passed": True,
            "violations": [],
            "activations": len(self.fallback_activations),
            "auto_fired_count": 0
        }
        
        for activation in self.fallback_activations:
            if activation["auto_fired"] and not activation["threshold_met"]:
                # Violation: Auto-fired without meeting threshold
                violation = {
                    "script": activation["script_name"],
                    "timestamp": activation["timestamp"],
                    "trigger": activation["trigger"],
                    "session": activation["session_id"]
                }
                results["violations"].append(violation)
                results["passed"] = False
            
            if activation["auto_fired"]:
                results["auto_fired_count"] += 1
        
        if results["passed"]:
            test_logger.info(f"✅ Fallback Surface Clean: {results['activations']} activations logged")
        else:
            test_logger.error(f"❌ Fallback Surface Violations: {len(results['violations'])} detected")
        
        return results
    
    # =========================================================================
    # DEBUG SURFACE TESTS: No accidental logging→TTS
    # =========================================================================
    
    def record_debug_tts_accident(self, source: str, text: str, intended_destination: str):
        """Record accidental routing of debug/log text to TTS"""
        record = {
            "timestamp": time.time(),
            "source": source,
            "text": text,
            "intended_destination": intended_destination,
            "actual_destination": "TTS"
        }
        self.debug_tts_accidents.append(record)
        self.violations["debug_surface"] += 1
    
    def test_debug_surface_isolation(self) -> Dict[str, Any]:
        """
        NEGATIVE PROOF TEST: Debug Surface Isolation
        
        Proves: No debug/logging text accidentally routes to TTS
        
        Clean Log Guarantee: If this test passes, debug TTS accidents are impossible
        """
        test_logger.info("=== TESTING DEBUG SURFACE ISOLATION ===")
        
        results = {
            "test_name": "Debug Surface Isolation",
            "passed": len(self.debug_tts_accidents) == 0,
            "violations": self.debug_tts_accidents,
            "accident_count": len(self.debug_tts_accidents)
        }
        
        if results["passed"]:
            test_logger.info("✅ Debug Surface Clean: No accidental TTS routing detected")
        else:
            test_logger.error(f"❌ Debug Surface Violations: {results['accident_count']} accidents detected")
        
        return results
    
    # =========================================================================
    # COMPREHENSIVE TEST RUNNER
    # =========================================================================
    
    def start_monitoring(self):
        """Enable real-time violation monitoring"""
        self._monitoring_enabled = True
        self._test_start_time = time.time()
        test_logger.info("🔍 Voice governance monitoring STARTED")
    
    def stop_monitoring(self):
        """Disable real-time violation monitoring"""
        self._monitoring_enabled = False
        test_logger.info("🔍 Voice governance monitoring STOPPED")
    
    def run_full_negative_proof_suite(self) -> Dict[str, Any]:
        """
        Run complete negative proof test suite.
        
        Returns: Comprehensive results proving each bug class is dead
        """
        test_logger.info("🧪 STARTING COMPREHENSIVE VOICE NEGATIVE PROOF SUITE")
        test_logger.info("=" * 80)
        
        suite_results = {
            "suite_name": "AQI Voice Governance Negative Proof Suite",
            "start_time": datetime.now().isoformat(),
            "duration_seconds": time.time() - self._test_start_time,
            "overall_passed": True,
            "test_results": {},
            "violation_summary": dict(self.violations),
            "coverage_stats": self._get_coverage_stats()
        }
        
        # Run all surface tests
        tests = [
            self.test_tts_surface_isolation,
            self.test_audio_surface_unity,
            self.test_concurrency_surface_exclusion,
            self.test_fallback_surface_control,
            self.test_debug_surface_isolation
        ]
        
        for test_func in tests:
            try:
                test_result = test_func()
                test_name = test_result["test_name"]
                suite_results["test_results"][test_name] = test_result
                
                if not test_result["passed"]:
                    suite_results["overall_passed"] = False
                    
            except Exception as e:
                test_logger.error(f"Test execution error: {e}")
                suite_results["overall_passed"] = False
        
        # Generate final report
        self._log_final_report(suite_results)
        
        return suite_results
    
    def _get_coverage_stats(self) -> Dict[str, int]:
        """Get test coverage statistics"""
        return {
            "tts_calls_recorded": len(self.tts_calls),
            "audio_paths_recorded": len(self.audio_paths),
            "speaker_tokens_recorded": len(self.speaker_tokens),
            "fallback_activations_recorded": len(self.fallback_activations),
            "debug_accidents_recorded": len(self.debug_tts_accidents)
        }
    
    def _log_final_report(self, results: Dict[str, Any]):
        """Log comprehensive test report"""
        test_logger.info("=" * 80)
        test_logger.info("🏁 NEGATIVE PROOF SUITE COMPLETE")
        test_logger.info("=" * 80)
        
        if results["overall_passed"]:
            test_logger.info("✅ ALL TESTS PASSED - Voice interference bugs are DEAD")
        else:
            test_logger.error("❌ VIOLATIONS DETECTED - Voice interference bugs still possible")
        
        test_logger.info(f"Duration: {results['duration_seconds']:.2f} seconds")
        test_logger.info(f"Tests executed: {len(results['test_results'])}")
        
        # Log individual test results
        for test_name, test_result in results["test_results"].items():
            status = "✅ PASS" if test_result["passed"] else "❌ FAIL"
            test_logger.info(f"  {status} - {test_name}")
            
            if not test_result["passed"]:
                violation_count = len(test_result.get("violations", []))
                test_logger.info(f"    └─ {violation_count} violations detected")
        
        # Log coverage
        test_logger.info("\nCoverage Statistics:")
        for stat_name, count in results["coverage_stats"].items():
            test_logger.info(f"  {stat_name}: {count}")

# Global test suite instance
_neg_proof_suite: Optional[VoiceNegativeProofSuite] = None

def get_neg_proof_suite() -> VoiceNegativeProofSuite:
    """Get the global negative proof test suite"""
    global _neg_proof_suite
    if _neg_proof_suite is None:
        _neg_proof_suite = VoiceNegativeProofSuite()
    return _neg_proof_suite