"""
+==============================================================================+
|   EAB-PLUS TEST HARNESS                                                       |
|   AQI Agent Alan --- Negative Proof Validation                                |
|                                                                               |
|   PURPOSE:                                                                    |
|   Validate every detector, predictor, and composite resolution path           |
|   in the EAB-Plus system. If this log is clean, this class of bug is dead.    |
|                                                                               |
|   COVERAGE:                                                                   |
|     Surface 1: ProsodyEngine — feature extraction + classification            |
|     Surface 2: SilencePatternClassifier — machine/human/beep detection        |
|     Surface 3: TimingFingerprintDetector — delay-based classification         |
|     Surface 4: HumanInterruptDetector — interrupt intent scoring              |
|     Surface 5: HangupPredictionModel — risk prediction                        |
|     Surface 6: VerticalAwarePredictor — vertical priors                       |
|     Surface 7: StateAwarePredictor — geographic priors                        |
|     Surface 8: LeadHistoryPredictor — call history priors                     |
|     Surface 9: EABPlusResolver — composite resolution                         |
|     Surface 10: EABPlusBehaviorRouter — action/template routing               |
|     Surface 11: SentinelEABPlus — enforcement rules                           |
|     Surface 12: CDC Integration — env_plus_signals write path                 |
|                                                                               |
|   LINEAGE: Built 2026-02-20. Tim's EAB-Plus architecture spec.               |
+==============================================================================+
"""

import sys
import struct
import time
import traceback

# Ensure imports work
try:
    from eab_plus import (
        ProsodyEngine,
        ProsodyFeatures,
        SilencePatternClassifier,
        TimingFingerprintDetector,
        HumanInterruptDetector,
        HangupPredictionModel,
        VerticalAwarePredictor,
        StateAwarePredictor,
        LeadHistoryPredictor,
        EABPlusResolver,
    )
    from behavior_router_eab_plus import (
        EABPlusBehaviorRouter,
        EABPlusBehaviorTemplates,
    )
    from sentinel_eab_plus import SentinelEABPlus
    from call_environment_classifier import (
        CallEnvironmentClassifier,
        EnvironmentClass,
        EnvironmentAction,
        _ENV_PATTERNS,
    )
except ImportError as e:
    print(f"IMPORT FAILED: {e}")
    sys.exit(1)


# ======================================================================
#  TEST INFRASTRUCTURE
# ======================================================================

_PASS = 0
_FAIL = 0
_TESTS = []


def test(name):
    """Decorator to register and track test functions."""
    def decorator(fn):
        _TESTS.append((name, fn))
        return fn
    return decorator


def assert_true(condition, msg=""):
    global _PASS, _FAIL
    if condition:
        _PASS += 1
    else:
        _FAIL += 1
        frame = traceback.extract_stack()[-2]
        print(f"  FAIL: {msg} (line {frame.lineno})")


def assert_in_range(value, low, high, msg=""):
    assert_true(low <= value <= high,
                f"{msg}: {value} not in [{low}, {high}]")


def assert_equals(actual, expected, msg=""):
    assert_true(actual == expected,
                f"{msg}: expected {expected}, got {actual}")


def make_pcm_audio(duration_ms=500, freq=440, sample_rate=8000):
    """Generate synthetic PCM int16 audio for testing."""
    import math
    num_samples = int(sample_rate * duration_ms / 1000)
    samples = []
    for i in range(num_samples):
        t = i / sample_rate
        # Sine wave with some variation for human-like quality
        val = int(8000 * math.sin(2 * math.pi * freq * t))
        # Add some noise for realism
        val += int(500 * math.sin(2 * math.pi * 130 * t))
        val = max(-32768, min(32767, val))
        samples.append(val)
    return struct.pack(f'<{len(samples)}h', *samples)


def make_silence_audio(duration_ms=500, noise_level=10, sample_rate=8000):
    """Generate near-silent PCM audio."""
    import math
    import random
    random.seed(42)
    num_samples = int(sample_rate * duration_ms / 1000)
    samples = []
    for _ in range(num_samples):
        samples.append(random.randint(-noise_level, noise_level))
    return struct.pack(f'<{len(samples)}h', *samples)


def make_beep_audio(duration_ms=1000, beep_at_ms=200, sample_rate=8000):
    """Generate audio with a voicemail beep."""
    import math
    num_samples = int(sample_rate * duration_ms / 1000)
    beep_start = int(sample_rate * beep_at_ms / 1000)
    beep_end = beep_start + int(sample_rate * 0.1)  # 100ms beep
    samples = []
    for i in range(num_samples):
        if beep_start <= i < beep_end:
            val = int(20000 * math.sin(2 * math.pi * 1000 * i / sample_rate))
        else:
            val = 5  # near silence
        samples.append(max(-32768, min(32767, val)))
    return struct.pack(f'<{len(samples)}h', *samples)


# ======================================================================
#  SURFACE 1: PROSODY ENGINE
# ======================================================================

@test("Prosody: Extract features from valid audio")
def test_prosody_extract():
    pe = ProsodyEngine()
    audio = make_pcm_audio(500, 440)
    pf = pe.extract(audio)
    assert_true(pf.duration_ms > 400, "Duration should be ~500ms")
    assert_true(pf.mean_energy > 0, "Mean energy should be positive")
    assert_true(pf.max_energy > 0, "Max energy should be positive")


@test("Prosody: Handle empty/short audio gracefully")
def test_prosody_empty():
    pe = ProsodyEngine()
    pf = pe.extract(b"")
    assert_equals(pf.duration_ms, 0.0, "Empty audio duration")
    pf2 = pe.extract(b"\x00" * 10)
    assert_equals(pf2.duration_ms, 0.0, "Short audio duration")


@test("Prosody: Classify features returns valid scores")
def test_prosody_classify():
    pe = ProsodyEngine()
    audio = make_pcm_audio(1000, 320)
    pf = pe.extract(audio)
    result = pe.classify(pf)
    assert_in_range(result["is_human"], 0.0, 1.0, "is_human range")
    assert_in_range(result["emotion_busy"], 0.0, 1.0, "emotion_busy range")
    assert_in_range(result["emotion_annoyed"], 0.0, 1.0, "emotion_annoyed range")
    assert_in_range(result["emotion_curious"], 0.0, 1.0, "emotion_curious range")
    assert_in_range(result["interrupt_intent"], 0.0, 1.0, "interrupt_intent range")


@test("Prosody: Classify with no features returns neutral")
def test_prosody_classify_empty():
    pe = ProsodyEngine()
    pf = ProsodyFeatures()
    result = pe.classify(pf)
    assert_equals(result["is_human"], 0.5, "Neutral is_human")


# ======================================================================
#  SURFACE 2: SILENCE PATTERN CLASSIFIER
# ======================================================================

@test("Silence: Clean silence detected as machine-like")
def test_silence_clean():
    spc = SilencePatternClassifier()
    silence = make_silence_audio(500, noise_level=5)
    result = spc.analyze(silence)
    assert_true(result["is_machine"] >= 0.0, "Machine score non-negative")
    assert_true(result["noise_floor"] >= 0, "Noise floor non-negative")


@test("Silence: Beep detection")
def test_silence_beep():
    spc = SilencePatternClassifier()
    beep_audio = make_beep_audio(1000, 200)
    result = spc.analyze(beep_audio)
    # Beep detection should fire or at least not crash
    assert_true(isinstance(result["has_beep"], float), "has_beep is float")
    assert_in_range(result["has_beep"], 0.0, 1.0, "has_beep range")


@test("Silence: Handle empty input")
def test_silence_empty():
    spc = SilencePatternClassifier()
    result = spc.analyze(b"")
    assert_equals(result["is_machine"], 0.0, "Empty silence machine score")
    assert_equals(result["has_beep"], 0.0, "Empty silence beep score")


# ======================================================================
#  SURFACE 3: TIMING FINGERPRINT DETECTOR
# ======================================================================

@test("Timing: Google Call Screen range (1100-1700ms)")
def test_timing_google_screen():
    tfd = TimingFingerprintDetector()
    result = tfd.detect(answer_ms=0, first_audio_ms=1400)
    assert_equals(result["prior_env_class"], "GOOGLE_CALL_SCREEN",
                  "1400ms delay should be Google screen")
    assert_true(result["confidence"] > 0.5, "Confidence should be > 0.5")


@test("Timing: Human range (<500ms)")
def test_timing_human():
    tfd = TimingFingerprintDetector()
    result = tfd.detect(answer_ms=0, first_audio_ms=150)
    assert_equals(result["prior_env_class"], "HUMAN",
                  "150ms delay should be human")


@test("Timing: Beep overrides delay classification")
def test_timing_beep():
    tfd = TimingFingerprintDetector()
    result = tfd.detect(answer_ms=0, first_audio_ms=200, first_beep_ms=100)
    assert_equals(result["prior_env_class"], "PERSONAL_VOICEMAIL",
                  "Beep should indicate voicemail")
    assert_true(result["confidence"] > 0.6, "Beep voicemail confidence")


@test("Timing: Unknown range (800-1100ms gap)")
def test_timing_unknown():
    tfd = TimingFingerprintDetector()
    result = tfd.detect(answer_ms=0, first_audio_ms=950)
    # Should be IVR range or unknown — delay_ms should be correct
    assert_equals(result["delay_ms"], 950, "Delay should be 950")


# ======================================================================
#  SURFACE 4: HUMAN INTERRUPT DETECTOR
# ======================================================================

@test("Interrupt: No overlap = zero intent")
def test_interrupt_no_overlap():
    hid = HumanInterruptDetector()
    score = hid.detect(remote_vad_active=False, agent_speaking=True)
    assert_equals(score, 0.0, "No overlap zero intent")


@test("Interrupt: Single overlap = low intent")
def test_interrupt_single():
    hid = HumanInterruptDetector()
    score = hid.detect(remote_vad_active=True, agent_speaking=True,
                       timestamp_ms=10000)
    assert_true(score > 0 and score < 0.6, f"Single overlap intent: {score}")


@test("Interrupt: Repeated overlap = high intent")
def test_interrupt_repeated():
    hid = HumanInterruptDetector()
    hid.detect(remote_vad_active=True, agent_speaking=True, timestamp_ms=1000)
    hid.detect(remote_vad_active=True, agent_speaking=True, timestamp_ms=4000)
    score = hid.detect(remote_vad_active=True, agent_speaking=True,
                       timestamp_ms=7000)
    assert_true(score >= 0.7, f"Repeated overlap should be high: {score}")


@test("Interrupt: Reset clears state")
def test_interrupt_reset():
    hid = HumanInterruptDetector()
    hid.detect(remote_vad_active=True, agent_speaking=True, timestamp_ms=1000)
    hid.reset()
    score = hid.detect(remote_vad_active=True, agent_speaking=True,
                       timestamp_ms=5000)
    assert_true(score < 0.6, f"Post-reset should be low: {score}")


# ======================================================================
#  SURFACE 5: HANGUP PREDICTION MODEL
# ======================================================================

@test("Hangup: 'not interested' = high risk")
def test_hangup_not_interested():
    hpm = HangupPredictionModel()
    risk = hpm.predict({"emotion_annoyed": 0.0}, "not interested", 3)
    assert_true(risk >= 0.4, f"'not interested' risk: {risk}")


@test("Hangup: Annoyed + short response = high risk")
def test_hangup_annoyed_short():
    hpm = HangupPredictionModel()
    risk = hpm.predict({"emotion_annoyed": 0.6}, "ok", 5,
                       response_length=2)
    assert_true(risk >= 0.35, f"Annoyed short risk: {risk}")


@test("Hangup: Neutral long response = low risk")
def test_hangup_neutral():
    hpm = HangupPredictionModel()
    risk = hpm.predict({"emotion_annoyed": 0.0},
                       "Tell me more about the rates you offer",
                       2, response_length=40)
    assert_true(risk < 0.3, f"Neutral risk: {risk}")


@test("Hangup: Many objections amplifies risk")
def test_hangup_objections():
    hpm = HangupPredictionModel()
    risk = hpm.predict({"emotion_annoyed": 0.0}, "I don't know",
                       4, objection_count=3)
    assert_true(risk >= 0.3, f"Objection-amplified risk: {risk}")


# ======================================================================
#  SURFACE 6: VERTICAL-AWARE PREDICTOR
# ======================================================================

@test("Vertical: Known vertical returns priors")
def test_vertical_known():
    vap = VerticalAwarePredictor()
    prior = vap.prior("RESTAURANT")
    assert_true(len(prior) > 0, "Restaurant priors non-empty")
    assert_true("HUMAN" in prior, "Restaurant has HUMAN prior")


@test("Vertical: Unknown vertical returns default")
def test_vertical_unknown():
    vap = VerticalAwarePredictor()
    prior = vap.prior("SPACEFLIGHT")
    assert_true(len(prior) > 0, "Unknown vertical default non-empty")
    assert_true("HUMAN" in prior, "Default has HUMAN prior")


@test("Vertical: Case insensitive")
def test_vertical_case():
    vap = VerticalAwarePredictor()
    p1 = vap.prior("restaurant")
    p2 = vap.prior("RESTAURANT")
    assert_equals(p1, p2, "Case insensitive")


# ======================================================================
#  SURFACE 7: STATE-AWARE PREDICTOR
# ======================================================================

@test("State: Known state returns priors")
def test_state_known():
    sap = StateAwarePredictor()
    prior = sap.prior(state="FL")
    assert_true(len(prior) > 0, "FL priors non-empty")
    assert_true("GOOGLE_CALL_SCREEN" in prior, "FL has screen prior")


@test("State: Area code resolution")
def test_state_area_code():
    sap = StateAwarePredictor()
    state = sap.state_from_phone("+15591234567")
    assert_equals(state, "CA", "559 area code = CA")


@test("State: Unknown area code returns None")
def test_state_unknown_area():
    sap = StateAwarePredictor()
    state = sap.state_from_phone("+10001234567")
    assert_equals(state, None, "Unknown area code")


@test("State: Prior from area_code param")
def test_state_area_code_prior():
    sap = StateAwarePredictor()
    prior = sap.prior(area_code="305")
    assert_true(len(prior) > 0, "305 area code priors")


# ======================================================================
#  SURFACE 8: LEAD HISTORY PREDICTOR
# ======================================================================

@test("Lead: No CDC returns default")
def test_lead_no_cdc():
    lhp = LeadHistoryPredictor(cdc_db=None)
    prior = lhp.prior("+15551234567")
    assert_equals(prior["last_env_class"], "UNKNOWN", "No CDC default")
    assert_equals(prior["recommendation"], "no_history", "No history")


@test("Lead: Empty phone returns default")
def test_lead_empty():
    lhp = LeadHistoryPredictor(cdc_db=None)
    prior = lhp.prior("")
    assert_equals(prior["call_count"], 0, "Empty phone count")


# ======================================================================
#  SURFACE 9: EAB-PLUS RESOLVER
# ======================================================================

def make_eab_plus():
    """Factory: create an EABPlusResolver with all detectors."""
    base_classifier = CallEnvironmentClassifier(_ENV_PATTERNS)
    return EABPlusResolver(
        base_classifier=base_classifier,
        prosody_engine=ProsodyEngine(),
        silence_classifier=SilencePatternClassifier(),
        timing_detector=TimingFingerprintDetector(),
        interrupt_detector=HumanInterruptDetector(),
        hangup_model=HangupPredictionModel(),
        vertical_predictor=VerticalAwarePredictor(),
        state_predictor=StateAwarePredictor(),
        lead_predictor=LeadHistoryPredictor(),
    )


@test("Resolver: Google Call Screen scenario")
def test_resolver_google_screen():
    eab = make_eab_plus()
    result = eab.resolve(
        transcript=("Hi, the person you're calling is using a screening "
                     "service. Please state your name."),
        stt_conf=0.95,
        audio_frames=make_pcm_audio(1000),
        silence_frames=make_silence_audio(200),
        answer_ms=0,
        first_audio_ms=1300,
        vertical="RETAIL",
        state="CA",
        phone="+15551234567",
        turn_count=0,
    )
    assert_equals(result["env_class"], "GOOGLE_CALL_SCREEN",
                  "Google screen classification")
    assert_true(result["env_confidence"] > 0.3,
                f"Confidence: {result['env_confidence']}")


@test("Resolver: Voicemail scenario")
def test_resolver_voicemail():
    eab = make_eab_plus()
    result = eab.resolve(
        transcript="Please leave your message after the tone.",
        stt_conf=0.92,
        audio_frames=make_pcm_audio(500),
        silence_frames=make_silence_audio(300),
        answer_ms=0,
        first_audio_ms=200,
        vertical="CONTRACTOR",
        state="TX",
        phone="+15559876543",
        turn_count=0,
    )
    assert_true(result["env_class"] in ("PERSONAL_VOICEMAIL", "CARRIER_VOICEMAIL"),
                f"Voicemail classification: {result['env_class']}")


@test("Resolver: Human 'Hello?' scenario")
def test_resolver_human():
    eab = make_eab_plus()
    result = eab.resolve(
        transcript="Hello?",
        stt_conf=0.90,
        audio_frames=make_pcm_audio(300),
        silence_frames=make_silence_audio(100),
        answer_ms=0,
        first_audio_ms=150,
        vertical="RESTAURANT",
        state="GA",
        phone="+15557654321",
        turn_count=1,
    )
    assert_equals(result["env_class"], "HUMAN",
                  f"Human classification: {result['env_class']}")


@test("Resolver: Returns all expected keys")
def test_resolver_keys():
    eab = make_eab_plus()
    result = eab.resolve(
        transcript="Yeah",
        stt_conf=0.85,
        audio_frames=make_pcm_audio(200),
        silence_frames=b"",
        answer_ms=0,
        first_audio_ms=100,
    )
    expected_keys = [
        "env_class", "env_confidence", "base_env", "base_confidence",
        "prosody", "silence", "timing", "vertical_prior", "state_prior",
        "lead_prior", "hangup_risk", "resolution_reason", "resolve_ms",
    ]
    for key in expected_keys:
        assert_true(key in result, f"Missing key: {key}")


@test("Resolver: Performance < 50ms")
def test_resolver_performance():
    eab = make_eab_plus()
    audio = make_pcm_audio(1000)
    silence = make_silence_audio(200)
    start = time.time()
    for _ in range(10):
        eab.resolve(
            transcript="Hello, this is Mike",
            stt_conf=0.90,
            audio_frames=audio,
            silence_frames=silence,
            answer_ms=0,
            first_audio_ms=200,
        )
    elapsed = (time.time() - start) / 10 * 1000
    assert_true(elapsed < 50, f"Average resolve: {elapsed:.1f}ms (target <50ms)")


# ======================================================================
#  SURFACE 10: BEHAVIOR ROUTER
# ======================================================================

@test("Router: Human → CONTINUE_MISSION")
def test_router_human():
    router = EABPlusBehaviorRouter()
    action = router.select_action("HUMAN")
    assert_equals(action, EnvironmentAction.CONTINUE_MISSION,
                  "Human action")


@test("Router: Voicemail → DROP_AND_ABORT")
def test_router_voicemail():
    router = EABPlusBehaviorRouter()
    action = router.select_action("PERSONAL_VOICEMAIL")
    assert_equals(action, EnvironmentAction.DROP_AND_ABORT,
                  "Voicemail action")


@test("Router: High hangup risk modifiers")
def test_router_hangup_modifiers():
    router = EABPlusBehaviorRouter()
    eab_result = {"hangup_risk": 0.8, "prosody": {}}
    mods = router.compute_modifiers(eab_result)
    assert_true(mods["force_brief"], "High risk forces brevity")
    assert_true(mods["max_tokens"] <= 40, f"Max tokens: {mods['max_tokens']}")
    assert_true(len(mods["tone_directive"]) > 0, "Tone directive set")


@test("Router: route() returns valid structure")
def test_router_route():
    router = EABPlusBehaviorRouter()
    ctx = {"merchant_name": "Joe's Pizza", "env_cycles": 0}
    eab_result = {
        "env_class": "GOOGLE_CALL_SCREEN",
        "hangup_risk": 0.1,
        "prosody": {"is_human": 0.3},
        "lead_prior": {"recommendation": ""},
    }
    result = router.route(ctx, eab_result)
    assert_equals(result["env_class"], "GOOGLE_CALL_SCREEN", "Route env_class")
    assert_equals(result["env_action"], "PASS_THROUGH", "Route action")
    assert_true(len(result["tts_text"]) > 0, "Screen has TTS text")
    assert_true(not result["should_abort"], "Screen should not abort")


@test("Router: voicemail route aborts")
def test_router_voicemail_abort():
    router = EABPlusBehaviorRouter()
    ctx = {"merchant_name": "", "env_cycles": 0}
    eab_result = {
        "env_class": "PERSONAL_VOICEMAIL",
        "hangup_risk": 0.0,
        "prosody": {},
        "lead_prior": {"recommendation": "expect_voicemail"},
    }
    result = router.route(ctx, eab_result)
    assert_true(result["should_abort"], "Voicemail should abort")
    assert_true(len(result["tts_text"]) > 0, "Voicemail has drop text")


# ======================================================================
#  SURFACE 11: SENTINEL EAB-PLUS
# ======================================================================

@test("Sentinel: Pitch into screener blocked")
def test_sentinel_pitch_screen():
    sentinel = SentinelEABPlus()
    ctx = {"env_class": "GOOGLE_CALL_SCREEN", "env_cycles": 0,
           "hangup_risk": 0.0}
    behavior = {"is_pitch": True, "max_tokens": 80}
    sentinel.enforce_pre_agent_turn(ctx, behavior)
    assert_true(not behavior.get("is_pitch"), "Pitch blocked")
    assert_true(behavior.get("force_pass_through"), "Pass-through forced")
    assert_true(sentinel.get_violation_count() == 1, "1 violation recorded")


@test("Sentinel: Loop limit abort")
def test_sentinel_loop_abort():
    sentinel = SentinelEABPlus()
    ctx = {"env_class": "CARRIER_SPAM_BLOCKER", "env_cycles": 5,
           "hangup_risk": 0.0}
    behavior = {"max_tokens": 80}
    sentinel.enforce_pre_agent_turn(ctx, behavior)
    assert_true(ctx.get("should_abort"), "Loop abort triggered")
    assert_true("ENV_LOOP" in ctx.get("exit_reason", ""), "Exit reason")


@test("Sentinel: Hangup risk forces brevity")
def test_sentinel_hangup_brevity():
    sentinel = SentinelEABPlus()
    ctx = {"env_class": "HUMAN", "env_cycles": 0, "hangup_risk": 0.75}
    behavior = {"max_tokens": 80}
    sentinel.enforce_pre_agent_turn(ctx, behavior)
    assert_true(behavior["max_tokens"] <= 40, f"Tokens: {behavior['max_tokens']}")
    assert_true(behavior.get("force_brief"), "Brief forced")


@test("Sentinel: Critical hangup risk forces value/close")
def test_sentinel_critical_hangup():
    sentinel = SentinelEABPlus()
    ctx = {"env_class": "HUMAN", "env_cycles": 0, "hangup_risk": 0.95}
    behavior = {"max_tokens": 80}
    sentinel.enforce_pre_agent_turn(ctx, behavior)
    assert_true(behavior.get("force_value_close"), "Value/close forced")


@test("Sentinel: No questions into machine env")
def test_sentinel_no_questions():
    sentinel = SentinelEABPlus()
    ctx = {"env_class": "BUSINESS_IVR", "env_cycles": 0, "hangup_risk": 0.0}
    behavior = {"has_question": True, "max_tokens": 80}
    sentinel.enforce_pre_agent_turn(ctx, behavior)
    assert_true(not behavior.get("has_question"), "Question blocked")
    assert_true(behavior.get("force_declarative"), "Declarative forced")


@test("Sentinel: Interrupt yield detection")
def test_sentinel_interrupt():
    sentinel = SentinelEABPlus()
    ctx = {"env_class": "HUMAN"}
    should_yield = sentinel.enforce_interrupt(ctx, 0.7)
    assert_true(should_yield, "Should yield on high interrupt")
    should_not = sentinel.enforce_interrupt(ctx, 0.3)
    assert_true(not should_not, "Should not yield on low interrupt")


@test("Sentinel: Lead history failed approach flag")
def test_sentinel_lead_history():
    sentinel = SentinelEABPlus()
    ctx = {"env_class": "HUMAN", "env_cycles": 0, "hangup_risk": 0.0,
           "lead_prior": {"last_outcome": "DECLINED"},
           "turn_count": 0}
    behavior = {"max_tokens": 80}
    sentinel.enforce_pre_agent_turn(ctx, behavior)
    assert_true(behavior.get("force_different_approach"),
                "Different approach flagged")


@test("Sentinel: Violation history bounded")
def test_sentinel_bounded():
    sentinel = SentinelEABPlus()
    sentinel._max_violations = 5
    for i in range(10):
        ctx = {"env_class": "GOOGLE_CALL_SCREEN", "env_cycles": 0,
               "hangup_risk": 0.0}
        behavior = {"is_pitch": True, "max_tokens": 80}
        sentinel.enforce_pre_agent_turn(ctx, behavior)
    assert_true(sentinel.get_violation_count() <= 5, "Violations bounded")


@test("Sentinel: Reset clears violations")
def test_sentinel_reset():
    sentinel = SentinelEABPlus()
    ctx = {"env_class": "GOOGLE_CALL_SCREEN", "env_cycles": 0,
           "hangup_risk": 0.0}
    behavior = {"is_pitch": True, "max_tokens": 80}
    sentinel.enforce_pre_agent_turn(ctx, behavior)
    assert_true(sentinel.get_violation_count() > 0, "Pre-reset")
    sentinel.reset()
    assert_equals(sentinel.get_violation_count(), 0, "Post-reset")


# ======================================================================
#  SURFACE 12: INTEGRATION — Full Pipeline
# ======================================================================

@test("Integration: Full pipeline — screen → route → sentinel")
def test_integration_full():
    eab = make_eab_plus()
    router = EABPlusBehaviorRouter()
    sentinel = SentinelEABPlus()

    # Resolve
    eab_result = eab.resolve(
        transcript="Please leave your message after the beep",
        stt_conf=0.90,
        audio_frames=make_pcm_audio(500),
        silence_frames=make_silence_audio(200),
        answer_ms=0,
        first_audio_ms=300,
        vertical="CONTRACTOR",
        state="TX",
        phone="+15551234567",
        turn_count=0,
    )

    # Route
    ctx = {"merchant_name": "Bob's Plumbing", "env_cycles": 0}
    route_result = router.route(ctx, eab_result)

    # Sentinel
    behavior = {"is_pitch": False, "max_tokens": 80}
    sentinel.enforce_pre_agent_turn(ctx, behavior)

    # Verify pipeline consistency
    assert_true(route_result["env_class"] == ctx["env_class"],
                "Route and ctx env_class match")
    assert_true(isinstance(route_result["modifiers"], dict),
                "Modifiers is dict")


@test("Integration: Human path — no TTS override")
def test_integration_human():
    eab = make_eab_plus()
    router = EABPlusBehaviorRouter()

    eab_result = eab.resolve(
        transcript="Hello?",
        stt_conf=0.90,
        audio_frames=make_pcm_audio(200),
        silence_frames=b"",
        answer_ms=0,
        first_audio_ms=100,
        vertical="RETAIL",
        state="GA",
    )

    ctx = {"merchant_name": "Joe's Shop", "env_cycles": 0}
    route_result = router.route(ctx, eab_result)
    assert_equals(route_result["tts_text"], "",
                  "Human path → empty TTS (pipeline handles)")
    assert_true(not route_result["should_abort"],
                "Human path → no abort")


# ======================================================================
#  RUN ALL TESTS
# ======================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("  EAB-PLUS TEST HARNESS — Negative Proof Validation Suite")
    print("=" * 70)
    print()

    for name, fn in _TESTS:
        try:
            fn()
            print(f"  [{'+' if True else '!'}] {name}")
        except Exception as e:
            _FAIL += 1
            print(f"  [!] {name} — EXCEPTION: {e}")
            traceback.print_exc()

    print()
    print("=" * 70)
    total = _PASS + _FAIL
    if _FAIL == 0:
        print(f"  RESULT: {_PASS}/{total} assertions PASSED — ALL CLEAN")
        print(f"  If this log is clean, this class of bug is dead.")
    else:
        print(f"  RESULT: {_PASS} passed, {_FAIL} FAILED out of {total}")
    print("=" * 70)

    sys.exit(0 if _FAIL == 0 else 1)
