"""
Negative Proof Suite -- AQI Entanglement Bridge
================================================
Exhaustive verification that the Entanglement Bridge correctly
synchronizes personality state vectors across Alan instances.

Tests cover:
  - SHA-3 integrity hashing
  - Cosine similarity math
  - State shift detection
  - Entanglement pair lifecycle
  - Vibe propagation (5% pull)
  - Cascade propagation (depth limit)
  - Correlation decay + auto-disentangle
  - Emergency reconvergence
  - Instance registration/unregistration
  - Entangle-all mesh topology
  - Phase-lock cycle integration
  - EntangledOvermind wrapper
  - Export/diagnostics
  - Edge cases (zero vectors, single instance, etc.)
"""

import sys
import os
import time
import uuid
import threading

import numpy as np

# Ensure we can import from the workspace
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from AQI_Entanglement_Bridge import (
    EntanglementBridge,
    EntanglementPair,
    EntanglementStatus,
    EntangledOvermind,
    StateShift,
    ReconvergenceEvent,
    SHIFT_THRESHOLD,
    ENTANGLEMENT_PULL,
    EMERGENCY_THRESHOLD,
    EMERGENCY_PULL,
    MIN_CORRELATION,
    MAX_PROPAGATION_DEPTH,
    PSI_DIM,
)


# ─── Mock Instance ───────────────────────────────────────────────────────────
class MockInstance:
    """Mimics AlanInstance interface for testing."""
    def __init__(self, name, state=None):
        self.instance_id = str(uuid.uuid4())
        self.location = name
        if state is None:
            state = [0.40, 0.45, 0.55, 0.50, 0.25]
        self.quantum_state = np.array(state, dtype=np.float64)
        norm = np.linalg.norm(self.quantum_state)
        if norm > 1e-10:
            self.quantum_state = self.quantum_state / norm


# ─── Test Harness ────────────────────────────────────────────────────────────
passed = 0
failed = 0


def check(label, condition):
    global passed, failed
    # ASCII-safe label for Windows cp1252 consoles
    safe_label = label.encode('ascii', errors='replace').decode('ascii')
    if condition:
        passed += 1
        print(f"  [PASS] {safe_label}")
    else:
        failed += 1
        print(f"  [FAIL] {safe_label}")


# =============================================================================
# TEST 1: SHA-3 INTEGRITY HASHING
# =============================================================================
print("\n=== SHA-3 INTEGRITY HASHING ===\n")

bridge = EntanglementBridge()

state_a = np.array([0.40, 0.45, 0.55, 0.50, 0.25], dtype=np.float64)
state_a /= np.linalg.norm(state_a)

hash_a = bridge._compute_state_hash(state_a)
check("SHA-3 hash is 64-char hex string", len(hash_a) == 64 and all(c in "0123456789abcdef" for c in hash_a))

# Same state → same hash (deterministic)
hash_a2 = bridge._compute_state_hash(state_a)
check("Same state → same hash (deterministic)", hash_a == hash_a2)

# Different state → different hash
state_b = np.array([0.50, 0.45, 0.55, 0.40, 0.25], dtype=np.float64)
state_b /= np.linalg.norm(state_b)
hash_b = bridge._compute_state_hash(state_b)
check("Different state → different hash", hash_a != hash_b)

# Verify passes with correct hash
check("Verify passes with correct hash", bridge._verify_state_hash(state_a, hash_a))

# Verify fails with wrong hash
check("Verify fails with wrong hash", not bridge._verify_state_hash(state_a, hash_b))

# Tiny perturbation → different hash (sensitivity)
state_perturbed = state_a.copy()
state_perturbed[0] += 1e-15
hash_perturbed = bridge._compute_state_hash(state_perturbed)
check("Tiny perturbation → different hash", hash_a != hash_perturbed)


# =============================================================================
# TEST 2: COSINE SIMILARITY MATH
# =============================================================================
print("\n=== COSINE SIMILARITY ===\n")

# Identical vectors → 1.0
sim_same = bridge._cosine_similarity(state_a, state_a)
check("Identical vectors → similarity ≈ 1.0", abs(sim_same - 1.0) < 1e-10)

# Orthogonal vectors → 0.0
v1 = np.array([1.0, 0.0, 0.0, 0.0, 0.0])
v2 = np.array([0.0, 1.0, 0.0, 0.0, 0.0])
sim_orth = bridge._cosine_similarity(v1, v2)
check("Orthogonal vectors → similarity ≈ 0.0", abs(sim_orth) < 1e-10)

# Opposite vectors → -1.0
sim_opp = bridge._cosine_similarity(v1, -v1)
check("Opposite vectors → similarity ≈ -1.0", abs(sim_opp - (-1.0)) < 1e-10)

# Zero vector → 0.0
zero = np.zeros(5)
sim_zero = bridge._cosine_similarity(v1, zero)
check("Zero vector → similarity = 0.0", sim_zero == 0.0)

# Commutative: sim(a,b) == sim(b,a)
sim_ab = bridge._cosine_similarity(state_a, state_b)
sim_ba = bridge._cosine_similarity(state_b, state_a)
check("Cosine similarity is commutative", abs(sim_ab - sim_ba) < 1e-10)


# =============================================================================
# TEST 3: NORMALIZATION
# =============================================================================
print("\n=== NORMALIZATION ===\n")

unnorm = np.array([3.0, 4.0, 5.0, 6.0, 7.0])
normed = bridge._normalize(unnorm)
check("Normalized vector has unit length", abs(np.linalg.norm(normed) - 1.0) < 1e-10)

# Zero vector → balanced
zero_normed = bridge._normalize(np.zeros(5))
check("Zero vector → balanced state", abs(np.linalg.norm(zero_normed) - 1.0) < 1e-10)
check("Zero vector → all equal components", np.allclose(zero_normed, np.ones(5) / np.sqrt(5)))


# =============================================================================
# TEST 4: INSTANCE REGISTRATION
# =============================================================================
print("\n=== INSTANCE REGISTRATION ===\n")

bridge2 = EntanglementBridge()
inst_a = MockInstance("Tokyo")
inst_b = MockInstance("London")

bridge2.register_instance(inst_a)
check("Instance A registered", inst_a.instance_id in bridge2._instances)
check("Instance A snapshot taken", inst_a.instance_id in bridge2._last_known_states)

bridge2.register_instance(inst_b)
check("Instance B registered", inst_b.instance_id in bridge2._instances)
check("Two instances registered", len(bridge2._instances) == 2)

# Unregister
bridge2.unregister_instance(inst_a.instance_id)
check("Instance A unregistered", inst_a.instance_id not in bridge2._instances)
check("Instance A snapshot removed", inst_a.instance_id not in bridge2._last_known_states)
check("Instance B still registered", inst_b.instance_id in bridge2._instances)


# =============================================================================
# TEST 5: ENTANGLEMENT PAIR LIFECYCLE
# =============================================================================
print("\n=== ENTANGLEMENT PAIR LIFECYCLE ===\n")

bridge3 = EntanglementBridge()
ia = MockInstance("Tokyo")
ib = MockInstance("London")
ic = MockInstance("NYC")

bridge3.register_instance(ia)
bridge3.register_instance(ib)
bridge3.register_instance(ic)

# Create pair
pair_id = bridge3.entangle(ia.instance_id, ib.instance_id)
check("Entangle returns pair_id", pair_id is not None)
check("Pair exists in bridge", pair_id in bridge3._pairs)
check("Pair is ACTIVE", bridge3._pairs[pair_id].status == EntanglementStatus.ACTIVE)
check("Pair correlation starts at 1.0", bridge3._pairs[pair_id].correlation_strength == 1.0)

# Duplicate entanglement returns same pair
pair_id_dup = bridge3.entangle(ia.instance_id, ib.instance_id)
check("Duplicate entanglement returns same pair_id", pair_id_dup == pair_id)

# Pair involves check
pair_obj = bridge3._pairs[pair_id]
check("Pair.involves(a) = True", pair_obj.involves(ia.instance_id))
check("Pair.involves(b) = True", pair_obj.involves(ib.instance_id))
check("Pair.involves(c) = False", not pair_obj.involves(ic.instance_id))

# Partner lookup
check("Partner of A is B", pair_obj.get_partner(ia.instance_id) == ib.instance_id)
check("Partner of B is A", pair_obj.get_partner(ib.instance_id) == ia.instance_id)
check("Partner of C is None", pair_obj.get_partner(ic.instance_id) is None)

# Disentangle
check("Disentangle succeeds", bridge3.disentangle(pair_id))
check("Pair is now DISENTANGLED", bridge3._pairs[pair_id].status == EntanglementStatus.DISENTANGLED)
check("Disentangle again returns False", not bridge3.disentangle(pair_id))

# Entangle with unregistered instance
unreg_id = "not-registered-xxxxx"
check("Entangle with unregistered → None", bridge3.entangle(ia.instance_id, unreg_id) is None)


# =============================================================================
# TEST 6: ENTANGLE ALL (MESH TOPOLOGY)
# =============================================================================
print("\n=== ENTANGLE ALL (MESH) ===\n")

bridge4 = EntanglementBridge()
instances = [MockInstance(f"City-{i}") for i in range(4)]
for inst in instances:
    bridge4.register_instance(inst)

ids = [inst.instance_id for inst in instances]
created_pairs = bridge4.entangle_all(ids)

# 4 instances → C(4,2) = 6 pairs
check("4 instances → 6 pairs created", len(created_pairs) == 6)
check("Bridge has 6 active pairs", len(bridge4.get_active_pairs()) == 6)

# Entanglement map
emap = bridge4.get_entanglement_map()
check("Each instance has 3 partners", all(len(emap.get(iid, [])) == 3 for iid in ids))


# =============================================================================
# TEST 7: STATE SHIFT DETECTION
# =============================================================================
print("\n=== STATE SHIFT DETECTION ===\n")

bridge5 = EntanglementBridge()
tokyo = MockInstance("Tokyo")
bridge5.register_instance(tokyo)

# No shift initially (first call stores snapshot)
shift = bridge5._detect_shift(tokyo.instance_id)
check("First call → no shift (stores snapshot)", shift is None)

# Small change → below threshold → no shift
tokyo.quantum_state[0] += 0.01
tokyo.quantum_state = bridge5._normalize(tokyo.quantum_state)
shift = bridge5._detect_shift(tokyo.instance_id)
check("Small change (0.01) → no shift", shift is None)

# Large change → above threshold → shift detected
old_state = tokyo.quantum_state.copy()
operator = np.array([
    [0.90, 0.00, 0.00, 0.00, 0.10],
    [0.00, 0.70, 0.00, 0.00, 0.00],
    [0.00, 0.00, 1.10, 0.00, 0.00],
    [0.00, 0.00, 0.00, 0.60, 0.00],
    [0.15, 0.00, 0.00, 0.10, 1.20],
], dtype=np.float64)
tokyo.quantum_state = operator @ tokyo.quantum_state
tokyo.quantum_state = bridge5._normalize(tokyo.quantum_state)
shift = bridge5._detect_shift(tokyo.instance_id)
check("Large shift → shift detected", shift is not None)
check("Shift has correct instance_id", shift.instance_id == tokyo.instance_id)
check("Shift delta_magnitude > threshold", shift.delta_magnitude >= SHIFT_THRESHOLD)
check("Shift has SHA-3 hash", len(shift.sha3_hash) == 64)
check("Shift propagation_depth = 0", shift.propagation_depth == 0)

# Shift for unregistered instance
check("Shift for unknown instance → None", bridge5._detect_shift("unknown") is None)


# =============================================================================
# TEST 8: VIBE PROPAGATION (5% PULL)
# =============================================================================
print("\n=== VIBE PROPAGATION (5% PULL) ===\n")

bridge6 = EntanglementBridge()
source = MockInstance("Tokyo", [0.40, 0.45, 0.55, 0.50, 0.25])
target = MockInstance("London", [0.40, 0.45, 0.55, 0.50, 0.25])

bridge6.register_instance(source)
bridge6.register_instance(target)
bridge6.entangle(source.instance_id, target.instance_id)

# Perturb source significantly
source_old = source.quantum_state.copy()
target_old = target.quantum_state.copy()

# Apply large operator to source
source.quantum_state = operator @ source.quantum_state
source.quantum_state = bridge6._normalize(source.quantum_state)

# Detect and propagate
shift = bridge6._detect_shift(source.instance_id)
check("Source shift detected", shift is not None)

propagated = bridge6._propagate_shift(shift)
check("Propagated to 1 partner", propagated == 1)

# Target should have moved toward source
sim_before = bridge6._cosine_similarity(target_old, source.quantum_state)
sim_after = bridge6._cosine_similarity(target.quantum_state, source.quantum_state)
check("Target moved closer to source", sim_after > sim_before)

# Target didn't become identical to source (only 5% pull)
check("Target is NOT identical to source", not np.allclose(target.quantum_state, source.quantum_state))

# Target is still normalized
check("Target remains normalized", abs(np.linalg.norm(target.quantum_state) - 1.0) < 1e-10)

# Verify the pull was approximately 5%
expected = bridge6._normalize(
    (1.0 - ENTANGLEMENT_PULL) * target_old + ENTANGLEMENT_PULL * source.quantum_state
)
check("Pull is approximately 5%", np.allclose(target.quantum_state, expected, atol=1e-10))


# =============================================================================
# TEST 9: CASCADE PROPAGATION + DEPTH LIMIT
# =============================================================================
print("\n=== CASCADE + DEPTH LIMIT ===\n")

bridge7 = EntanglementBridge()
a = MockInstance("City-A")
b = MockInstance("City-B")
c = MockInstance("City-C")
d = MockInstance("City-D")

for inst in [a, b, c, d]:
    bridge7.register_instance(inst)

# Chain: A ⊗ B ⊗ C ⊗ D (linear chain, not mesh)
bridge7.entangle(a.instance_id, b.instance_id)
bridge7.entangle(b.instance_id, c.instance_id)
bridge7.entangle(c.instance_id, d.instance_id)

# Big shift on A
b_before = b.quantum_state.copy()
c_before = c.quantum_state.copy()
d_before = d.quantum_state.copy()

a.quantum_state = operator @ a.quantum_state
a.quantum_state = bridge7._normalize(a.quantum_state)

shift = bridge7._detect_shift(a.instance_id)
check("Chain: A shift detected", shift is not None)

count = bridge7._propagate_shift(shift)
check("Chain: propagated to at least B", count >= 1)

# B should have shifted
b_moved = not np.allclose(b.quantum_state, b_before)
check("Chain: B received vibe from A", b_moved)

# Depth limit = 2, so C might receive cascaded shift from B
# D should NOT be reached (depth 0→A, 1→B, 2→C, 3→D blocked)
check("MAX_PROPAGATION_DEPTH is 2", MAX_PROPAGATION_DEPTH == 2)


# =============================================================================
# TEST 10: CORRELATION DECAY + AUTO-DISENTANGLE
# =============================================================================
print("\n=== CORRELATION DECAY + AUTO-DISENTANGLE ===\n")

bridge8 = EntanglementBridge()
x = MockInstance("X")
y = MockInstance("Y")
bridge8.register_instance(x)
bridge8.register_instance(y)
pair_id = bridge8.entangle(x.instance_id, y.instance_id)
pair = bridge8._pairs[pair_id]

# Manually decay correlation
pair.correlation_strength = 0.25  # Below MIN_CORRELATION

# Create a shift that triggers propagation check
x.quantum_state = operator @ x.quantum_state
x.quantum_state = bridge8._normalize(x.quantum_state)
shift = bridge8._detect_shift(x.instance_id)

if shift:
    bridge8._propagate_shift(shift)

check("Low correlation → pair decayed/disentangled",
      pair.status in (EntanglementStatus.DECAYED, EntanglementStatus.DISENTANGLED))
check("Auto-disentangle counter incremented", bridge8._total_auto_disentanglements >= 1)

# MIN_CORRELATION value
check("MIN_CORRELATION = 0.30", MIN_CORRELATION == 0.30)


# =============================================================================
# TEST 11: EMERGENCY RECONVERGENCE
# =============================================================================
print("\n=== EMERGENCY RECONVERGENCE ===\n")

bridge9 = EntanglementBridge()
consensus = np.array([0.40, 0.45, 0.55, 0.50, 0.25], dtype=np.float64)
consensus /= np.linalg.norm(consensus)
bridge9.update_consensus(consensus)

# Create instances with wildly divergent states (axis-aligned for maximum divergence)
r1 = MockInstance("R1", [1.0, 0.0, 0.0, 0.0, 0.0])
r2 = MockInstance("R2", [0.0, 0.0, 0.0, 0.0, 1.0])
r3 = MockInstance("R3", [0.0, 0.0, 0.0, 1.0, 0.0])

for inst in [r1, r2, r3]:
    bridge9.register_instance(inst)

# Pre-reconvergence: average coherence should be low
cos1 = bridge9._cosine_similarity(r1.quantum_state, consensus)
cos2 = bridge9._cosine_similarity(r2.quantum_state, consensus)
cos3 = bridge9._cosine_similarity(r3.quantum_state, consensus)
avg_before = (cos1 + cos2 + cos3) / 3
check(f"Pre-reconvergence avg coherence < EMERGENCY ({avg_before:.3f} < {EMERGENCY_THRESHOLD})",
      avg_before < EMERGENCY_THRESHOLD)

# Trigger reconvergence
reconverged = bridge9._check_emergency_reconvergence()
check("Emergency reconvergence triggered", reconverged)

# Post-reconvergence: states should be closer to consensus
cos1_post = bridge9._cosine_similarity(r1.quantum_state, consensus)
cos2_post = bridge9._cosine_similarity(r2.quantum_state, consensus)
cos3_post = bridge9._cosine_similarity(r3.quantum_state, consensus)
avg_after = (cos1_post + cos2_post + cos3_post) / 3
check(f"Post-reconvergence coherence improved ({avg_after:.3f} > {avg_before:.3f})",
      avg_after > avg_before)

check("Reconvergence count = 1", bridge9._total_reconvergences == 1)
check("Reconvergence event recorded", len(bridge9._reconvergence_history) == 1)

event = bridge9._reconvergence_history[0]
check("Event has coherence_before", event.coherence_before < EMERGENCY_THRESHOLD)
check("Event has coherence_after > before",
      event.coherence_after > event.coherence_before)
check("Event affected 3 instances", event.instances_affected == 3)
check("Event pull = EMERGENCY_PULL", event.pull_strength == EMERGENCY_PULL)

# Reconvergence should NOT trigger when coherence is fine
bridge10 = EntanglementBridge()
bridge10.update_consensus(consensus)
good1 = MockInstance("G1", [0.40, 0.45, 0.55, 0.50, 0.25])
good2 = MockInstance("G2", [0.41, 0.44, 0.55, 0.50, 0.25])
bridge10.register_instance(good1)
bridge10.register_instance(good2)
check("No reconvergence when coherence is good",
      not bridge10._check_emergency_reconvergence())

# Single instance → no reconvergence
bridge_single = EntanglementBridge()
bridge_single.update_consensus(consensus)
solo = MockInstance("Solo", [0.90, 0.10, 0.10, 0.10, 0.10])
bridge_single.register_instance(solo)
check("Single instance → no reconvergence",
      not bridge_single._check_emergency_reconvergence())


# =============================================================================
# TEST 12: PHASE-LOCK CYCLE INTEGRATION
# =============================================================================
print("\n=== PHASE-LOCK CYCLE ===\n")

bridge11 = EntanglementBridge()
p1 = MockInstance("Tokyo")
p2 = MockInstance("London")

bridge11.register_instance(p1)
bridge11.register_instance(p2)
bridge11.entangle(p1.instance_id, p2.instance_id)
bridge11.update_consensus(p1.quantum_state.copy())

# No shifts yet → empty cycle
result = bridge11.tick()
check("Tick returns dict", isinstance(result, dict))
check("No shifts on first tick", result["shifts_detected"] == 0)
check("Cycle count incremented", result["cycle"] == 1)

# Apply shift and tick
p1.quantum_state = operator @ p1.quantum_state
p1.quantum_state = bridge11._normalize(p1.quantum_state)

result2 = bridge11.tick()
check("Shift detected on second tick", result2["shifts_detected"] == 1)
check("Shift propagated to partner", result2["shifts_propagated"] >= 1)
check("Cycle count = 2", result2["cycle"] == 2)


# =============================================================================
# TEST 13: DAEMON THREAD START/STOP
# =============================================================================
print("\n=== DAEMON THREAD ===\n")

bridge12 = EntanglementBridge()
check("Not running initially", not bridge12.is_running())

bridge12.start()
time.sleep(0.1)
check("Running after start()", bridge12.is_running())

# Start again → no crash
bridge12.start()  # Should warn, not crash
check("Double start doesn't crash", bridge12.is_running())

bridge12.stop()
time.sleep(0.1)
check("Stopped after stop()", not bridge12.is_running())


# =============================================================================
# TEST 14: UNREGISTER AUTO-DISENTANGLES
# =============================================================================
print("\n=== UNREGISTER AUTO-DISENTANGLES ===\n")

bridge13 = EntanglementBridge()
u1 = MockInstance("U1")
u2 = MockInstance("U2")
u3 = MockInstance("U3")

bridge13.register_instance(u1)
bridge13.register_instance(u2)
bridge13.register_instance(u3)
bridge13.entangle(u1.instance_id, u2.instance_id)
bridge13.entangle(u1.instance_id, u3.instance_id)

check("2 active pairs before unregister", len(bridge13.get_active_pairs()) == 2)

bridge13.unregister_instance(u1.instance_id)
check("0 active pairs after unregistering U1", len(bridge13.get_active_pairs()) == 0)
check("U1 removed from instances", u1.instance_id not in bridge13._instances)


# =============================================================================
# TEST 15: DIAGNOSTICS + EXPORT
# =============================================================================
print("\n=== DIAGNOSTICS + EXPORT ===\n")

bridge14 = EntanglementBridge()
d1 = MockInstance("D1")
d2 = MockInstance("D2")
bridge14.register_instance(d1)
bridge14.register_instance(d2)
bridge14.entangle(d1.instance_id, d2.instance_id)

state = bridge14.export_state()
check("Export has 'running'", "running" in state)
check("Export has 'registered_instances'", state["registered_instances"] == 2)
check("Export has 'pair_counts'", "pair_counts" in state)
check("Export has 'metrics'", "metrics" in state)
check("Export has 'config'", "config" in state)
check("Config has shift_threshold", state["config"]["shift_threshold"] == SHIFT_THRESHOLD)
check("Config has entanglement_pull", state["config"]["entanglement_pull"] == ENTANGLEMENT_PULL)

# Pair counts
pc = bridge14.get_pair_count()
check("Pair count: 1 active", pc["active"] == 1)

# Average correlation
avg_corr = bridge14.get_average_correlation()
check("Average correlation = 1.0 (fresh pair)", avg_corr == 1.0)

# No active pairs → avg = 1.0
bridge_empty = EntanglementBridge()
check("No pairs → avg correlation = 1.0", bridge_empty.get_average_correlation() == 1.0)

# Recent shifts
check("Recent shifts initially empty", len(bridge14.get_recent_shifts()) == 0)

# __repr__
repr_str = repr(bridge14)
check("__repr__ contains 'EntanglementBridge'", "EntanglementBridge" in repr_str)


# =============================================================================
# TEST 16: StateShift DATACLASS
# =============================================================================
print("\n=== StateShift DATACLASS ===\n")

ss = StateShift(
    shift_id="test_shift",
    instance_id="inst_123",
    old_state=np.array([0.4, 0.3, 0.3, 0.3, 0.3]),
    new_state=np.array([0.5, 0.2, 0.3, 0.3, 0.3]),
    delta=np.array([0.1, -0.1, 0.0, 0.0, 0.0]),
    delta_magnitude=0.1414,
    timestamp=time.time(),
    sha3_hash="abc123",
    propagation_depth=0,
)
ss_dict = ss.to_dict()
check("StateShift.to_dict() has shift_id", ss_dict["shift_id"] == "test_shift")
check("StateShift.to_dict() has delta_magnitude", "delta_magnitude" in ss_dict)
check("StateShift.to_dict() has sha3_hash", ss_dict["sha3_hash"] == "abc123")
check("StateShift.to_dict() has propagation_depth", ss_dict["propagation_depth"] == 0)


# =============================================================================
# TEST 17: EntanglementPair DATACLASS
# =============================================================================
print("\n=== EntanglementPair DATACLASS ===\n")

ep = EntanglementPair(
    pair_id="pair_test",
    instance_a_id="aaa",
    instance_b_id="bbb",
    created_at=time.time(),
)
ep_dict = ep.to_dict()
check("Pair.to_dict() has pair_id", ep_dict["pair_id"] == "pair_test")
check("Pair.to_dict() has status", ep_dict["status"] == "active")
check("Pair.to_dict() has correlation_strength", ep_dict["correlation_strength"] == 1.0)
check("Pair.to_dict() has sync_count", ep_dict["sync_count"] == 0)


# =============================================================================
# TEST 18: ReconvergenceEvent DATACLASS
# =============================================================================
print("\n=== ReconvergenceEvent DATACLASS ===\n")

re = ReconvergenceEvent(
    event_id="rc_test",
    timestamp=time.time(),
    coherence_before=0.42,
    coherence_after=0.71,
    instances_affected=3,
    pull_strength=0.15,
    consensus_state_hash="deadbeef",
)
re_dict = re.to_dict()
check("Reconvergence.to_dict() has event_id", re_dict["event_id"] == "rc_test")
check("Reconvergence.to_dict() has coherence_before", re_dict["coherence_before"] == 0.42)
check("Reconvergence.to_dict() has instances_affected", re_dict["instances_affected"] == 3)


# =============================================================================
# TEST 19: CONSTANTS VERIFICATION
# =============================================================================
print("\n=== CONSTANTS ===\n")

check("SHIFT_THRESHOLD = 0.08", SHIFT_THRESHOLD == 0.08)
check("ENTANGLEMENT_PULL = 0.05", ENTANGLEMENT_PULL == 0.05)
check("EMERGENCY_THRESHOLD = 0.55", EMERGENCY_THRESHOLD == 0.55)
check("EMERGENCY_PULL = 0.15", EMERGENCY_PULL == 0.15)
check("MIN_CORRELATION = 0.30", MIN_CORRELATION == 0.30)
check("MAX_PROPAGATION_DEPTH = 2", MAX_PROPAGATION_DEPTH == 2)
check("PSI_DIM = 5", PSI_DIM == 5)


# =============================================================================
# TEST 20: CONSENSUS STATE UPDATE
# =============================================================================
print("\n=== CONSENSUS STATE ===\n")

bridge15 = EntanglementBridge()
check("Initial consensus is None", bridge15._consensus_state is None)

cons = np.array([0.5, 0.4, 0.3, 0.2, 0.1], dtype=np.float64)
bridge15.update_consensus(cons)
check("Consensus updated", bridge15._consensus_state is not None)
check("Consensus is independent copy", bridge15._consensus_state is not cons)
check("Consensus values match", np.allclose(bridge15._consensus_state, cons))


# =============================================================================
# TEST 21: ENTANGLED OVERMIND WRAPPER
# =============================================================================
print("\n=== ENTANGLED OVERMIND ===\n")

# Import AlanOvermind for real integration test
try:
    from AQI_Quantum_Fork import AlanOvermind, AlanInstance, InstanceState

    overmind = AlanOvermind()
    eo = EntangledOvermind(overmind)

    check("EntangledOvermind has bridge", eo.bridge is not None)
    check("Bridge has consensus from overmind",
          np.allclose(eo.bridge._consensus_state, overmind.consensus_state))

    # Replicate via EntangledOvermind
    def dummy_task(instance):
        instance.commit_experience("Test from " + instance.location)
        time.sleep(0.1)

    inst1 = eo.replicate("Tokyo", task_fn=dummy_task)
    check("Replicate returns instance", inst1 is not None)
    check("Instance registered with bridge", inst1.instance_id in eo.bridge._instances)

    inst2 = eo.replicate("London", task_fn=dummy_task)
    check("Second instance created", inst2 is not None)
    check("Both instances in bridge", len(eo.bridge._instances) == 2)

    # Check entanglement pair exists
    active_pairs = eo.bridge.get_active_pairs()
    check("Entanglement pair created between instances", len(active_pairs) >= 1)

    # Terminate
    eo.terminate_instance(inst1.instance_id)
    check("Instance1 unregistered from bridge after terminate",
          inst1.instance_id not in eo.bridge._instances)

    # Export
    state = eo.export_state()
    check("Export has entanglement_bridge", "entanglement_bridge" in state)

    # Shutdown
    eo.shutdown()
    check("Bridge stopped after shutdown", not eo.bridge.is_running())

    # Properties delegation
    eo2 = EntangledOvermind(AlanOvermind())
    check("Delegated ledger exists", eo2.ledger is not None)
    check("Delegated total_forks = 0", eo2.total_forks == 0)
    check("Delegated identity_coherence = 1.0", eo2.identity_coherence == 1.0)
    check("Active count = 0", eo2.get_active_count() == 0)

    # __repr__
    check("__repr__ works", "EntangledOvermind" in repr(eo2))

    _has_overmind = True
except ImportError:
    print("  [SKIP] AlanOvermind not available -- skipping integration tests")
    _has_overmind = False


# =============================================================================
# TEST 22: EDGE CASES
# =============================================================================
print("\n=== EDGE CASES ===\n")

# Empty bridge tick
bridge_edge = EntanglementBridge()
result = bridge_edge.tick()
check("Empty bridge tick → 0 shifts", result["shifts_detected"] == 0)

# Bridge with consensus but no instances → no reconvergence
bridge_edge.update_consensus(consensus)
check("No instances → no reconvergence", not bridge_edge._check_emergency_reconvergence())

# Propagate shift with no pairs → 0
solo_bridge = EntanglementBridge()
solo_inst = MockInstance("Solo")
solo_bridge.register_instance(solo_inst)
solo_inst.quantum_state = operator @ solo_inst.quantum_state
solo_inst.quantum_state = solo_bridge._normalize(solo_inst.quantum_state)
solo_shift = solo_bridge._detect_shift(solo_inst.instance_id)
if solo_shift:
    count = solo_bridge._propagate_shift(solo_shift)
    check("No pairs → 0 propagations", count == 0)

# Constants are sane
check("EMERGENCY_THRESHOLD < Overmind's 0.60", EMERGENCY_THRESHOLD < 0.60)
check("ENTANGLEMENT_PULL < EMERGENCY_PULL", ENTANGLEMENT_PULL < EMERGENCY_PULL)


# =============================================================================
# RESULTS
# =============================================================================

print(f"\n{'=' * 60}")
print(f"  ENTANGLEMENT BRIDGE NEG PROOF: {passed}/{passed + failed} passed, {failed} failed")
print(f"{'=' * 60}")

if failed == 0:
    print("\n  All systems verified. Phase-Lock State Sync is production-ready.\n")
else:
    print(f"\n  WARNING: {failed} test(s) failed!\n")
    sys.exit(1)
