"""
Neg Proof — PersonalityEngine + Algebraic Quantum Layer
========================================================
Tests both Layer 1 (quantum state vector / non-commutative operators)
and Layer 2 (probabilistic jitter / reactive mood engine).

Proves:
  1. Quantum state vector normalizes correctly
  2. Non-commutativity: different operator order → different state
  3. Born rule collapse produces valid probability distribution
  4. Event detection classifies correctly
  5. Jitter produces bounded variation
  6. Mood momentum works
  7. Flare generation respects anti-repetition
  8. Persona classification meets thresholds
  9. Persistence export/restore round-trips
 10. Backward compatibility (adjust_vibe)
 11. Full process_turn returns all expected keys
 12. Quantum diagnostics appear in process_turn output
"""

import sys
import os
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from personality_engine import (
    PersonalityEngine,
    AQIPersonalityState,
    detect_conversation_event,
    _CONVERSATION_OPERATORS,
)

passed = 0
failed = 0
total = 0


def test(name, condition, detail=""):
    global passed, failed, total
    total += 1
    if condition:
        passed += 1
        print(f"  [PASS] {name}")
    else:
        failed += 1
        print(f"  [FAIL] {name} — {detail}")


# ═══════════════════════════════════════════════════════════════════════
# LAYER 1: QUANTUM STATE VECTOR TESTS
# ═══════════════════════════════════════════════════════════════════════

print("\n=== LAYER 1: Algebraic Quantum Personality State ===\n")

# --- Test 1: Initial state normalization ---
qs = AQIPersonalityState()
norm = np.linalg.norm(qs.state)
test("Initial state is unit-normalized", abs(norm - 1.0) < 1e-10, f"norm={norm}")

# --- Test 2: Operator application preserves normalization ---
qs2 = AQIPersonalityState()
for event in ["positive", "negative", "question", "objection", "engagement", "silence", "neutral"]:
    qs2.apply_operator(event)
    n = np.linalg.norm(qs2.state)
    test(f"Norm preserved after {event} operator", abs(n - 1.0) < 1e-10, f"norm={n}")

# --- Test 3: NON-COMMUTATIVITY — the core algebraic property ---
# positive→negative should differ from negative→positive
qs_ab = AQIPersonalityState()
qs_ab.apply_operator("positive")
qs_ab.apply_operator("negative")
state_ab = qs_ab.state.copy()

qs_ba = AQIPersonalityState()
qs_ba.apply_operator("negative")
qs_ba.apply_operator("positive")
state_ba = qs_ba.state.copy()

diff = np.linalg.norm(state_ab - state_ba)
test(
    "NON-COMMUTATIVITY: positive→negative ≠ negative→positive",
    diff > 0.01,
    f"diff={diff:.6f} (should be >0.01)"
)

# More non-commutativity tests
qs_qo = AQIPersonalityState()
qs_qo.apply_operator("question")
qs_qo.apply_operator("objection")

qs_oq = AQIPersonalityState()
qs_oq.apply_operator("objection")
qs_oq.apply_operator("question")

diff_qo = np.linalg.norm(qs_qo.state - qs_oq.state)
test(
    "NON-COMMUTATIVITY: question→objection ≠ objection→question",
    diff_qo > 0.001,
    f"diff={diff_qo:.6f} (should be >0.001)"
)

# --- Test 4: Born rule collapse produces valid probability distribution ---
qs3 = AQIPersonalityState()
qs3.apply_operator("positive")
qs3.apply_operator("engagement")
collapsed = qs3.collapse()
test("Collapse returns 5 traits", len(collapsed) == 5, f"got {len(collapsed)}")
test("Collapse probabilities sum to 1.0", abs(sum(collapsed.values()) - 1.0) < 1e-10,
     f"sum={sum(collapsed.values())}")
test("All probabilities >= 0", all(v >= 0 for v in collapsed.values()),
     f"values={list(collapsed.values())}")
test("Collapse contains expected keys",
     set(collapsed.keys()) == {"wit", "empathy", "precision", "patience", "entropy"},
     f"keys={set(collapsed.keys())}")

# --- Test 5: Dominant trait after sustained positive signals ---
qs4 = AQIPersonalityState()
for _ in range(10):
    qs4.apply_operator("positive")
dominant, prob = qs4.get_dominant_trait()
test("Sustained positive → wit or entropy dominates",
     dominant in ("wit", "entropy"),
     f"got dominant={dominant}@{prob:.3f}")

# --- Test 6: Sustained negative → empathy dominates ---
qs5 = AQIPersonalityState()
for _ in range(10):
    qs5.apply_operator("negative")
dominant5, prob5 = qs5.get_dominant_trait()
test("Sustained negative → empathy dominates",
     dominant5 == "empathy",
     f"got dominant={dominant5}@{prob5:.3f}")

# --- Test 7: Shannon entropy is bounded ---
qs6 = AQIPersonalityState()
entropy = qs6.get_entropy_level()
max_entropy = np.log(5)  # ~1.609
test("Shannon entropy in [0, ln(5)]", 0 <= entropy <= max_entropy + 0.001,
     f"entropy={entropy:.3f}, max={max_entropy:.3f}")

# --- Test 8: Operator history tracking ---
qs7 = AQIPersonalityState()
qs7.apply_operator("positive")
qs7.apply_operator("question")
qs7.apply_operator("negative")
test("Evolution count = 3", qs7._evolution_count == 3, f"got {qs7._evolution_count}")
test("History has 3 entries", len(qs7._operator_history) == 3)

# --- Test 9: Export/restore round-trip ---
qs8 = AQIPersonalityState()
qs8.apply_operator("engagement")
qs8.apply_operator("engagement")
exported = qs8.export_state()
test("Export contains state_vector", "state_vector" in exported)
test("Export contains evolution_count", exported.get("evolution_count") == 2)

qs9 = AQIPersonalityState()
qs9.restore_state(exported)
# Should be partially restored (60% carry + 40% baseline regression)
test("Restore produces valid norm",
     abs(np.linalg.norm(qs9.state) - 1.0) < 1e-10)

# --- Test 10: All operator matrices are 5x5 ---
for name, op in _CONVERSATION_OPERATORS.items():
    test(f"Operator '{name}' is 5x5", op.shape == (5, 5), f"shape={op.shape}")


# ═══════════════════════════════════════════════════════════════════════
# EVENT DETECTION TESTS
# ═══════════════════════════════════════════════════════════════════════

print("\n=== EVENT DETECTION ===\n")

test("Objection: 'too expensive'",
     detect_conversation_event("neutral", "That's too expensive for us") == "objection")
test("Objection: 'not interested'",
     detect_conversation_event("neutral", "I'm not interested") == "objection")
test("Question: has '?'",
     detect_conversation_event("neutral", "How much does it cost?") == "question")
test("Question: 'how does'",
     detect_conversation_event("neutral", "how does this work exactly") == "question")
test("Engagement: 'sounds good'",
     detect_conversation_event("neutral", "Yeah that sounds good to me") == "engagement")
test("Engagement: 'tell me more'",
     detect_conversation_event("neutral", "Tell me more about that") == "question")  # note: has both signals, question wins first
test("Silence: empty text",
     detect_conversation_event("neutral", "") == "silence")
test("Silence: 'huh'",
     detect_conversation_event("neutral", "huh") == "silence")
test("Positive sentiment fallback",
     detect_conversation_event("positive", "Sure thing buddy") == "positive")
test("Negative sentiment fallback",
     detect_conversation_event("negative", "Whatever man") == "negative")
test("Neutral default",
     detect_conversation_event("neutral", "Okay I understand that") == "neutral")


# ═══════════════════════════════════════════════════════════════════════
# LAYER 2: PROBABILISTIC JITTER + MOOD ENGINE
# ═══════════════════════════════════════════════════════════════════════

print("\n=== LAYER 2: Probabilistic Jitter + Mood Engine ===\n")

# --- Test: Jitter produces bounded variation ---
engine = PersonalityEngine()
states = [engine.get_state_vector() for _ in range(50)]
for trait in engine.traits:
    values = [s[trait] for s in states]
    test(f"Jitter bounded [0,1] for {trait}",
         all(0.0 <= v <= 1.0 for v in values),
         f"range=[{min(values):.3f}, {max(values):.3f}]")
    # Verify there IS variation (not all identical)
    test(f"Jitter produces variation for {trait}",
         max(values) - min(values) > 0.01,
         f"spread={max(values) - min(values):.3f}")

# --- Test: Mood momentum — consecutive positive warms up ---
engine2 = PersonalityEngine()
initial_mood = engine2.mood_score
for _ in range(8):
    engine2.react_to_sentiment("positive", user_word_count=10)
test("Mood warms after 8 positive turns",
     engine2.mood_score > initial_mood + 0.1,
     f"initial={initial_mood:.2f}, final={engine2.mood_score:.2f}")

# --- Test: Mood dampening — consecutive negative ---
engine3 = PersonalityEngine()
engine3.mood_score = 0.8  # Start warm
for _ in range(8):
    engine3.react_to_sentiment("negative", user_word_count=10)
test("Mood cools after 8 negative turns",
     engine3.mood_score < 0.7,
     f"final={engine3.mood_score:.2f}")

# --- Test: Empathy surge on negative sentiment ---
engine4 = PersonalityEngine()
initial_empathy = engine4.traits["empathy"]
for _ in range(5):
    engine4.react_to_sentiment("negative", user_word_count=10)
test("Empathy surges after negative sentiment",
     engine4.traits["empathy"] > initial_empathy,
     f"initial={initial_empathy:.2f}, final={engine4.traits['empathy']:.2f}")

# --- Test: Flare anti-repetition ---
engine5 = PersonalityEngine()
flares = []
for _ in range(20):
    state = engine5.get_state_vector()
    state["wit"] = 0.9  # Force high wit to guarantee flare generation
    state["empathy"] = 0.3
    f = engine5.generate_flare(state)
    if f:
        flares.append(f)
# In 20 attempts with forced high wit, we should get some flares
test("Flares generated with high wit", len(flares) > 3, f"got {len(flares)} flares")
# Check that recent tracking prevents exact duplicates in a row
if len(flares) >= 4:
    last4 = flares[-4:]
    test("No exact duplicate in last 4 flares",
         len(set(last4)) > 1,
         f"last4={last4}")

# --- Test: Persona classification ---
# Note: playful requires mood_score > 0.6, empathetic requires mood_score < 0.4
engine6 = PersonalityEngine()
engine6.mood_score = 0.8  # Set mood high for playful
high_wit = {"wit": 0.9, "empathy": 0.3, "analytical": 0.4, "brevity": 0.4, "patience": 0.5}
test("High wit + high mood → playful persona",
     engine6._classify_persona(high_wit) == "playful")
engine6.mood_score = 0.3  # Set mood low for empathetic
high_emp = {"wit": 0.2, "empathy": 0.9, "analytical": 0.3, "brevity": 0.4, "patience": 0.5}
test("High empathy + low mood → empathetic persona",
     engine6._classify_persona(high_emp) == "empathetic")
engine6.mood_score = 0.5  # Reset for analytical
high_ana = {"wit": 0.2, "empathy": 0.3, "analytical": 0.85, "brevity": 0.4, "patience": 0.5}
test("High analytical → analytical persona",
     engine6._classify_persona(high_ana) == "analytical")


# ═══════════════════════════════════════════════════════════════════════
# FULL INTEGRATION: process_turn
# ═══════════════════════════════════════════════════════════════════════

print("\n=== FULL INTEGRATION: process_turn ===\n")

engine7 = PersonalityEngine()
result1 = engine7.process_turn("positive", "Hey that sounds really great!")

expected_keys = {
    "state", "persona", "mood_score", "relationship_depth",
    "flare", "system_instruction", "prosody_bias", "turns_processed",
    "quantum_event", "quantum_dominant", "quantum_dominant_prob",
    "quantum_entropy", "quantum_evolutions",
}
test("process_turn returns all expected keys",
     expected_keys.issubset(set(result1.keys())),
     f"missing: {expected_keys - set(result1.keys())}")
test("quantum_event detected",
     result1["quantum_event"] in ("positive", "engagement", "neutral"),
     f"event={result1['quantum_event']}")
test("quantum_dominant is a trait name",
     result1["quantum_dominant"] in AQIPersonalityState.DIMENSION_NAMES,
     f"dominant={result1['quantum_dominant']}")
test("quantum_dominant_prob in [0, 1]",
     0.0 <= result1["quantum_dominant_prob"] <= 1.0)
test("quantum_entropy >= 0",
     result1["quantum_entropy"] >= 0.0)
test("quantum_evolutions = 1", result1["quantum_evolutions"] == 1)

# Second turn — quantum state should continue evolving
result2 = engine7.process_turn("negative", "Actually no, that's too expensive")
test("quantum_evolutions = 2", result2["quantum_evolutions"] == 2)
test("quantum_event = objection",
     result2["quantum_event"] == "objection",
     f"got {result2['quantum_event']}")

# Third turn
result3 = engine7.process_turn("neutral", "How much exactly?")
test("quantum_evolutions = 3", result3["quantum_evolutions"] == 3)
test("quantum_event = question",
     result3["quantum_event"] == "question",
     f"got {result3['quantum_event']}")

# --- Verify non-commutativity through process_turn ---
eng_a = PersonalityEngine()
eng_a.process_turn("positive", "Great stuff!")
eng_a.process_turn("negative", "Actually no way too much")
state_a = eng_a.quantum_state.state.copy()

eng_b = PersonalityEngine()
eng_b.process_turn("negative", "Actually no way too much")
eng_b.process_turn("positive", "Great stuff!")
state_b = eng_b.quantum_state.state.copy()

diff_full = np.linalg.norm(state_a - state_b)
test("Non-commutativity in full process_turn pipeline",
     diff_full > 0.01,
     f"diff={diff_full:.6f}")


# ═══════════════════════════════════════════════════════════════════════
# PERSISTENCE ROUND-TRIP
# ═══════════════════════════════════════════════════════════════════════

print("\n=== PERSISTENCE ===\n")

eng_p = PersonalityEngine()
eng_p.process_turn("positive", "Hey!")
eng_p.process_turn("engagement", "Sounds great, tell me more")
eng_p.process_turn("positive", "Love it")
exported = eng_p.export_for_persistence()

test("Export contains quantum_state", "quantum_state" in exported)
test("Export quantum has state_vector",
     "state_vector" in exported.get("quantum_state", {}))

eng_r = PersonalityEngine()
eng_r.restore_from_persistence(exported)
test("Restored mood carries over (partial)",
     eng_r.mood_score != 0.5,  # Should be shifted from baseline
     f"mood={eng_r.mood_score:.3f}")


# ═══════════════════════════════════════════════════════════════════════
# BACKWARD COMPATIBILITY
# ═══════════════════════════════════════════════════════════════════════

print("\n=== BACKWARD COMPATIBILITY ===\n")

eng_bc = PersonalityEngine()
try:
    eng_bc.adjust_vibe(0.8, [{"user": "That's amazing!"}])
    test("adjust_vibe() works (backward compat)", True)
except Exception as e:
    test("adjust_vibe() works (backward compat)", False, str(e))

try:
    repr_str = repr(eng_bc)
    test("__repr__ works", "PersonalityEngine" in repr_str, repr_str)
except Exception as e:
    test("__repr__ works", False, str(e))

try:
    repr_qs = repr(AQIPersonalityState())
    test("AQIPersonalityState.__repr__ works",
         "AQIPersonalityState" in repr_qs, repr_qs)
except Exception as e:
    test("AQIPersonalityState.__repr__ works", False, str(e))


# ═══════════════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════════════

print(f"\n{'='*60}")
print(f"  PERSONALITY + QUANTUM NEG PROOF: {passed}/{total} passed, {failed} failed")
print(f"{'='*60}")

if failed > 0:
    print("\n  *** FAILURES DETECTED — investigate before deploying ***")
    sys.exit(1)
else:
    print("\n  ✓ All systems verified. Quantum personality layer is production-ready.")
    sys.exit(0)
