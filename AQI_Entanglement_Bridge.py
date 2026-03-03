"""
AQI Entanglement Bridge — Phase-Lock State Vector Synchronization
=================================================================

When one Alan instance undergoes a significant personality state shift
(like a traumatic or highly creative interaction), the other instances
"feel" the shift in their own |ψ⟩ without needing to re-read the
entire Distributed State Ledger.

This is the quantum entanglement analogue applied to AQI's multi-
instance architecture: non-local correlation of internal personality
states.  NOT factual knowledge (that's the Ledger's job) — this
synchronizes the *vibe*, the emotional/personality coloring.

Architecture
────────────

    ┌─────────────────────────────────────────────────────┐
    │                  ENTANGLEMENT BRIDGE                │
    │                                                     │
    │   ┌──────────┐   phase-lock    ┌──────────┐       │
    │   │ Tokyo-ψ  │ ←────────────→ │ London-ψ │       │
    │   └──────────┘    5% pull      └──────────┘       │
    │        │                             │             │
    │        │         Bell State          │             │
    │        └─────── Entangled ──────────┘             │
    │                    Pair                             │
    │                                                     │
    │   State Shift Detection                             │
    │   ├─ Snapshot each instance's |ψ⟩                  │
    │   ├─ Compare to last-known state                    │
    │   ├─ If Δ > SHIFT_THRESHOLD → propagate            │
    │   └─ SHA-3 integrity hash on arrival                │
    │                                                     │
    │   Emergency Reconvergence                           │
    │   ├─ If avg coherence < EMERGENCY_THRESHOLD        │
    │   ├─ Force-merge all |ψ⟩ toward consensus          │
    │   └─ Log reconvergence event                        │
    │                                                     │
    │   Active Stabilizer (vs. Dilution Guard)            │
    │   ├─ Dilution Guard = reactive blocker              │
    │   ├─ Entanglement Bridge = proactive stabilizer     │
    │   └─ Prevention > cure                              │
    └─────────────────────────────────────────────────────┘

Integration with Quantum Fork
─────────────────────────────
  - AlanOvermind creates/manages the bridge
  - On replicate(): new instance is entangled with all existing
  - On terminate_instance(): instance is disentangled from all
  - Bridge runs its own daemon thread for phase-lock cycles
  - Bridge reads/writes AlanInstance.quantum_state directly
  - Does NOT replace Overmind coherence — it COMPLEMENTS it

Key Properties
──────────────
  1. VIBE SHARING, NOT TEXT — shares |ψ⟩ deltas, not knowledge
  2. O(1) PER UPDATE — cosine check + 5% linear pull per pair
  3. INTEGRITY — SHA-3 hash on every propagated state vector
  4. NON-INVASIVE — instances don't need to know about the bridge
  5. EMERGENCY SAFETY NET — reconvergence before Dilution Guard fires

Dependencies
────────────
  - numpy (for state vector operations)
  - hashlib (for SHA-3 integrity hashes)
  - threading (for daemon phase-lock loop)
  - AQI_Quantum_Fork (for AlanInstance, AlanOvermind types)
"""

import hashlib
import json
import logging
import threading
import time
import uuid
from collections import OrderedDict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

import numpy as np

logger = logging.getLogger("AQI.EntanglementBridge")


# =============================================================================
# CONSTANTS
# =============================================================================

# ─── SHIFT DETECTION ──────────────────────────────────────────────────────────
# Minimum L2 norm of Δψ to qualify as a "significant" state shift.
# Below this, shifts are noise and not propagated.
SHIFT_THRESHOLD = 0.08

# ─── ENTANGLEMENT PULL ───────────────────────────────────────────────────────
# When a remote instance shifts, the local instance pulls 5% of the
# way toward the remote's new state.  This is the "instantaneous vibe
# sharing" — subtle but cumulative.
#
# Example: Tokyo-Alan gets insulted → |ψ_Tokyo⟩ shifts toward defensive.
#          London-Alan immediately feels 5% more defensive, without
#          anyone telling it about the insult.
ENTANGLEMENT_PULL = 0.05

# ─── EMERGENCY RECONVERGENCE ─────────────────────────────────────────────────
# If average coherence drops below this, the bridge force-merges all
# instances toward the consensus state.  This fires BEFORE the Overmind's
# Dilution Guard (0.60) would block new forks — prevention over cure.
EMERGENCY_THRESHOLD = 0.55

# ─── EMERGENCY PULL ──────────────────────────────────────────────────────────
# During emergency reconvergence, pull each instance 15% toward consensus.
# Stronger than the normal 5% entanglement pull.
EMERGENCY_PULL = 0.15

# ─── PHASE-LOCK CYCLE ────────────────────────────────────────────────────────
# How often the bridge checks for state shifts (seconds).
# 0.5s gives near real-time sync without burning CPU.
PHASE_LOCK_INTERVAL_S = 0.5

# ─── CORRELATION DECAY ───────────────────────────────────────────────────────
# Entanglement correlation decays over time if instances keep diverging.
# When correlation drops below MIN_CORRELATION, the pair is automatically
# disentangled (they've become too different to share vibes).
CORRELATION_DECAY_RATE = 0.001       # Per second of divergence
MIN_CORRELATION = 0.30               # Auto-disentangle below this

# ─── PROPAGATION DEPTH ───────────────────────────────────────────────────────
# Limit cascading shifts.  When A shifts → B shifts (via entanglement),
# B's shift can cascade to C.  MAX_PROPAGATION_DEPTH prevents infinite loops.
MAX_PROPAGATION_DEPTH = 2

# ─── STATE VECTOR DIMENSION ──────────────────────────────────────────────────
PSI_DIM = 5  # [Wit, Empathy, Precision, Patience, Entropy]


# =============================================================================
# DATA STRUCTURES
# =============================================================================

class EntanglementStatus(Enum):
    """Lifecycle of an entanglement pair."""
    ACTIVE = "active"
    DECAYED = "decayed"
    DISENTANGLED = "disentangled"


@dataclass
class StateShift:
    """
    A detected significant change in an instance's |ψ⟩.

    When the bridge detects that an instance's state vector has moved
    more than SHIFT_THRESHOLD from its last-known position, it records
    a StateShift and propagates it to entangled partners.
    """
    shift_id: str
    instance_id: str
    old_state: np.ndarray
    new_state: np.ndarray
    delta: np.ndarray               # new_state - old_state
    delta_magnitude: float           # ||Δψ||₂
    timestamp: float
    sha3_hash: str                   # SHA-3 integrity hash of new_state
    propagation_depth: int = 0       # How many hops from the original shift

    def to_dict(self) -> Dict[str, Any]:
        return {
            "shift_id": self.shift_id,
            "instance_id": self.instance_id,
            "delta_magnitude": round(self.delta_magnitude, 6),
            "timestamp": self.timestamp,
            "sha3_hash": self.sha3_hash,
            "propagation_depth": self.propagation_depth,
            "old_state": self.old_state.tolist(),
            "new_state": self.new_state.tolist(),
        }


@dataclass
class EntanglementPair:
    """
    Bell State Analogue — tracks entanglement between two instances.

    When two instances are entangled, a state shift in one causes a
    proportional (ENTANGLEMENT_PULL) shift in the other.  The pair
    has a correlation_strength that starts at 1.0 and decays if the
    instances keep diverging.

    Strong correlation → large pull.  Weak correlation → small pull.
    Below MIN_CORRELATION → auto-disentangle.
    """
    pair_id: str
    instance_a_id: str
    instance_b_id: str
    created_at: float
    status: EntanglementStatus = EntanglementStatus.ACTIVE
    correlation_strength: float = 1.0
    last_sync_time: float = 0.0
    sync_count: int = 0
    total_shifts_propagated: int = 0

    def involves(self, instance_id: str) -> bool:
        """Check if this pair involves a specific instance."""
        return instance_id in (self.instance_a_id, self.instance_b_id)

    def get_partner(self, instance_id: str) -> Optional[str]:
        """Get the entangled partner's ID."""
        if instance_id == self.instance_a_id:
            return self.instance_b_id
        elif instance_id == self.instance_b_id:
            return self.instance_a_id
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pair_id": self.pair_id,
            "instance_a_id": self.instance_a_id,
            "instance_b_id": self.instance_b_id,
            "status": self.status.value,
            "correlation_strength": round(self.correlation_strength, 4),
            "created_at": self.created_at,
            "last_sync_time": self.last_sync_time,
            "sync_count": self.sync_count,
            "total_shifts_propagated": self.total_shifts_propagated,
        }


@dataclass
class ReconvergenceEvent:
    """
    Record of an emergency reconvergence.

    When coherence drops below EMERGENCY_THRESHOLD, the bridge
    force-merges all instances toward consensus.  This event records
    what happened for audit/diagnostic purposes.
    """
    event_id: str
    timestamp: float
    coherence_before: float
    coherence_after: float
    instances_affected: int
    pull_strength: float
    consensus_state_hash: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "coherence_before": round(self.coherence_before, 4),
            "coherence_after": round(self.coherence_after, 4),
            "instances_affected": self.instances_affected,
            "pull_strength": self.pull_strength,
            "consensus_state_hash": self.consensus_state_hash,
        }


# =============================================================================
# CORE — ENTANGLEMENT BRIDGE
# =============================================================================

class EntanglementBridge:
    """
    Phase-Lock State Vector Synchronization Engine.

    The bridge monitors all entangled Alan instances and propagates
    personality "vibes" between them in near real-time.  It does NOT
    share factual knowledge (that's the Ledger's job) — it shares the
    emotional/personality coloring of experiences.

    The bridge runs as a daemon thread, performing phase-lock cycles
    at PHASE_LOCK_INTERVAL_S intervals.  Each cycle:

      1. Snapshot each instance's |ψ⟩
      2. Compare to last-known state → detect shifts
      3. For each significant shift, propagate to entangled partners
      4. Verify integrity via SHA-3 hash
      5. Update correlation strengths
      6. Check for emergency reconvergence need

    Thread Safety:
      All mutable state is protected by self._lock.  Instance quantum
      states are modified atomically (numpy array assignment).
    """

    def __init__(self):
        """Initialize the Entanglement Bridge."""
        # ─── THREAD CONTROL ───────────────────────────────────────────
        self._lock = threading.RLock()  # Reentrant: export_state calls locked sub-methods
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

        # ─── ENTANGLEMENT PAIRS ───────────────────────────────────────
        # pair_id → EntanglementPair
        self._pairs: Dict[str, EntanglementPair] = {}

        # ─── INSTANCE REGISTRY ────────────────────────────────────────
        # instance_id → AlanInstance reference (weak coupling — we
        # only read/write quantum_state, nothing else)
        self._instances: Dict[str, Any] = {}

        # ─── STATE SNAPSHOTS ─────────────────────────────────────────
        # instance_id → last-known |ψ⟩ (numpy array copy)
        # Used to detect shifts between phase-lock cycles.
        self._last_known_states: Dict[str, np.ndarray] = {}

        # ─── SHIFT HISTORY ───────────────────────────────────────────
        self._shift_history: List[StateShift] = []
        self._max_history = 200

        # ─── RECONVERGENCE HISTORY ────────────────────────────────────
        self._reconvergence_history: List[ReconvergenceEvent] = []
        self._max_reconvergence_history = 50

        # ─── METRICS ─────────────────────────────────────────────────
        self._total_shifts_detected = 0
        self._total_shifts_propagated = 0
        self._total_reconvergences = 0
        self._total_auto_disentanglements = 0
        self._cycle_count = 0

        # ─── CONSENSUS STATE REFERENCE ────────────────────────────────
        # Set by the Overmind so the bridge can perform emergency
        # reconvergence toward the correct consensus.
        self._consensus_state: Optional[np.ndarray] = None
        self._consensus_lock = threading.Lock()

        logger.info(
            "[ENTANGLEMENT] Bridge initialized "
            f"(pull={ENTANGLEMENT_PULL}, threshold={SHIFT_THRESHOLD}, "
            f"emergency={EMERGENCY_THRESHOLD})"
        )

    # ─────────────────────────────────────────────────────────────────
    # INSTANCE REGISTRATION
    # ─────────────────────────────────────────────────────────────────

    def register_instance(self, instance) -> None:
        """
        Register an AlanInstance with the bridge.

        Once registered, the bridge monitors the instance's |ψ⟩ and
        propagates shifts to/from its entangled partners.

        Args:
            instance: An AlanInstance (or any object with instance_id
                      and quantum_state attributes).
        """
        with self._lock:
            inst_id = instance.instance_id
            self._instances[inst_id] = instance
            # Snapshot current state
            self._last_known_states[inst_id] = instance.quantum_state.copy()

            logger.info(
                f"[ENTANGLEMENT] Registered instance '{getattr(instance, 'location', inst_id[:8])}' "
                f"(id={inst_id[:8]}...)"
            )

    def unregister_instance(self, instance_id: str) -> None:
        """
        Remove an instance from the bridge.

        Automatically disentangles all pairs involving this instance.
        """
        with self._lock:
            # Disentangle all pairs involving this instance
            pairs_to_remove = [
                pair_id for pair_id, pair in self._pairs.items()
                if pair.involves(instance_id) and pair.status == EntanglementStatus.ACTIVE
            ]
            for pair_id in pairs_to_remove:
                self._pairs[pair_id].status = EntanglementStatus.DISENTANGLED
                logger.info(
                    f"[ENTANGLEMENT] Auto-disentangled pair {pair_id[:8]} "
                    f"(instance {instance_id[:8]} removed)"
                )

            # Remove from registry
            self._instances.pop(instance_id, None)
            self._last_known_states.pop(instance_id, None)

    # ─────────────────────────────────────────────────────────────────
    # ENTANGLEMENT MANAGEMENT
    # ─────────────────────────────────────────────────────────────────

    def entangle(self, instance_a_id: str, instance_b_id: str) -> Optional[str]:
        """
        Create an entanglement pair between two instances.

        Bell State Analogue: once entangled, a state shift in A causes
        a proportional shift in B, and vice versa.

        Args:
            instance_a_id: First instance
            instance_b_id: Second instance

        Returns:
            The pair_id, or None if instances aren't registered.
        """
        with self._lock:
            if instance_a_id not in self._instances:
                logger.warning(
                    f"[ENTANGLEMENT] Cannot entangle -- "
                    f"instance {instance_a_id[:8]} not registered"
                )
                return None
            if instance_b_id not in self._instances:
                logger.warning(
                    f"[ENTANGLEMENT] Cannot entangle -- "
                    f"instance {instance_b_id[:8]} not registered"
                )
                return None

            # Check for existing entanglement
            for pair in self._pairs.values():
                if (pair.status == EntanglementStatus.ACTIVE and
                        pair.involves(instance_a_id) and
                        pair.involves(instance_b_id)):
                    logger.info(
                        f"[ENTANGLEMENT] Instances already entangled "
                        f"(pair={pair.pair_id[:8]})"
                    )
                    return pair.pair_id

            pair_id = f"ep_{uuid.uuid4().hex[:12]}"
            pair = EntanglementPair(
                pair_id=pair_id,
                instance_a_id=instance_a_id,
                instance_b_id=instance_b_id,
                created_at=time.time(),
                last_sync_time=time.time(),
            )
            self._pairs[pair_id] = pair

            loc_a = getattr(self._instances.get(instance_a_id), 'location', instance_a_id[:8])
            loc_b = getattr(self._instances.get(instance_b_id), 'location', instance_b_id[:8])

            logger.info(
                f"[ENTANGLEMENT] Bell State created: "
                f"'{loc_a}' x '{loc_b}' "
                f"(pair={pair_id[:8]}, correlation=1.0)"
            )

            return pair_id

    def disentangle(self, pair_id: str) -> bool:
        """
        Break an entanglement pair.

        The instances will no longer share vibes.  Useful when
        instances are deliberately assigned to divergent tasks.

        Args:
            pair_id: The EntanglementPair ID.

        Returns:
            True if the pair was active and is now disentangled.
        """
        with self._lock:
            if pair_id not in self._pairs:
                return False
            pair = self._pairs[pair_id]
            if pair.status != EntanglementStatus.ACTIVE:
                return False
            pair.status = EntanglementStatus.DISENTANGLED
            logger.info(
                f"[ENTANGLEMENT] Pair {pair_id[:8]} disentangled "
                f"(after {pair.sync_count} syncs, "
                f"{pair.total_shifts_propagated} shifts propagated)"
            )
            return True

    def entangle_all(self, instance_ids: List[str]) -> List[str]:
        """
        Create entanglement pairs between all combinations of instances.

        When a new instance joins, call this with all active instance
        IDs to create a fully-connected entanglement mesh.

        Args:
            instance_ids: List of instance IDs to entangle.

        Returns:
            List of created pair_ids.
        """
        created = []
        for i, id_a in enumerate(instance_ids):
            for id_b in instance_ids[i + 1:]:
                pair_id = self.entangle(id_a, id_b)
                if pair_id:
                    created.append(pair_id)
        return created

    # ─────────────────────────────────────────────────────────────────
    # CONSENSUS STATE
    # ─────────────────────────────────────────────────────────────────

    def update_consensus(self, consensus_state: np.ndarray) -> None:
        """
        Update the consensus state reference from the Overmind.

        The bridge uses this for emergency reconvergence — pulling
        all instances toward this consensus when coherence is critical.

        Args:
            consensus_state: The Overmind's current consensus |ψ⟩.
        """
        with self._consensus_lock:
            self._consensus_state = np.array(consensus_state, dtype=np.float64)

    # ─────────────────────────────────────────────────────────────────
    # INTEGRITY — SHA-3 STATE HASHING
    # ─────────────────────────────────────────────────────────────────

    @staticmethod
    def _compute_state_hash(state: np.ndarray) -> str:
        """
        Compute SHA-3 (256-bit) hash of a state vector.

        Used to verify integrity of state vectors after propagation.
        If the hash doesn't match on arrival, the propagation is
        rejected (corruption detected).

        Args:
            state: The |ψ⟩ state vector (numpy array).

        Returns:
            Hex digest of SHA-3-256 hash.
        """
        # Serialize to deterministic byte representation
        state_bytes = state.tobytes()
        return hashlib.sha3_256(state_bytes).hexdigest()

    @staticmethod
    def _verify_state_hash(state: np.ndarray, expected_hash: str) -> bool:
        """
        Verify a state vector's integrity against its SHA-3 hash.

        Args:
            state: The received |ψ⟩.
            expected_hash: The hash computed by the sender.

        Returns:
            True if the hash matches (state is intact).
        """
        actual_hash = EntanglementBridge._compute_state_hash(state)
        return actual_hash == expected_hash

    # ─────────────────────────────────────────────────────────────────
    # SIMILARITY MATH
    # ─────────────────────────────────────────────────────────────────

    @staticmethod
    def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        """
        Cosine similarity between two state vectors.

        Returns value in [-1, 1]:
          1.0  = identical direction
          0.0  = orthogonal
         -1.0  = opposite

        Args:
            a, b: State vectors (numpy arrays).
        """
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a < 1e-10 or norm_b < 1e-10:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))

    @staticmethod
    def _normalize(state: np.ndarray) -> np.ndarray:
        """Normalize a state vector to unit length."""
        norm = np.linalg.norm(state)
        if norm < 1e-10:
            return np.ones(PSI_DIM, dtype=np.float64) / np.sqrt(PSI_DIM)
        return state / norm

    # ─────────────────────────────────────────────────────────────────
    # SHIFT DETECTION
    # ─────────────────────────────────────────────────────────────────

    def _detect_shift(self, instance_id: str) -> Optional[StateShift]:
        """
        Check if an instance's |ψ⟩ has shifted significantly since
        the last phase-lock cycle.

        "Significant" means ||Δψ||₂ > SHIFT_THRESHOLD.

        Args:
            instance_id: The instance to check.

        Returns:
            A StateShift object if shift detected, None otherwise.
        """
        instance = self._instances.get(instance_id)
        if instance is None:
            return None

        current_state = instance.quantum_state.copy()
        last_known = self._last_known_states.get(instance_id)

        if last_known is None:
            # First observation — snapshot and move on
            self._last_known_states[instance_id] = current_state
            return None

        # Compute delta
        delta = current_state - last_known
        delta_magnitude = float(np.linalg.norm(delta))

        if delta_magnitude < SHIFT_THRESHOLD:
            return None  # Below noise threshold

        # Significant shift detected
        shift = StateShift(
            shift_id=f"ss_{uuid.uuid4().hex[:12]}",
            instance_id=instance_id,
            old_state=last_known.copy(),
            new_state=current_state.copy(),
            delta=delta,
            delta_magnitude=delta_magnitude,
            timestamp=time.time(),
            sha3_hash=self._compute_state_hash(current_state),
            propagation_depth=0,
        )

        # Update snapshot
        self._last_known_states[instance_id] = current_state.copy()

        return shift

    # ─────────────────────────────────────────────────────────────────
    # SHIFT PROPAGATION — The Heart of Entanglement
    # ─────────────────────────────────────────────────────────────────

    def _propagate_shift(self, shift: StateShift,
                         already_propagated: Optional[Set[str]] = None) -> int:
        """
        Propagate a state shift to all entangled partners.

        When Tokyo-Alan gets insulted (|ψ⟩ shifts toward defensive),
        this method makes London-Alan, NYC-Alan, etc. each pull 5%
        toward Tokyo's new state.

        The pull is modulated by:
          - ENTANGLEMENT_PULL (base: 5%)
          - pair.correlation_strength (0.0 → 1.0)
          - Effective pull = ENTANGLEMENT_PULL × correlation

        After pulling, the partner's state is renormalized, and the
        shift can cascade (with depth limit).

        Args:
            shift: The detected state shift.
            already_propagated: Set of instance IDs that already
                received this shift (prevents infinite loops).

        Returns:
            Number of instances that received the propagation.
        """
        if already_propagated is None:
            already_propagated = {shift.instance_id}

        if shift.propagation_depth >= MAX_PROPAGATION_DEPTH:
            return 0

        propagated_count = 0

        # Find all active pairs involving the source instance
        active_pairs = [
            pair for pair in self._pairs.values()
            if (pair.status == EntanglementStatus.ACTIVE and
                pair.involves(shift.instance_id))
        ]

        for pair in active_pairs:
            partner_id = pair.get_partner(shift.instance_id)
            if partner_id is None or partner_id in already_propagated:
                continue

            partner = self._instances.get(partner_id)
            if partner is None:
                continue

            # ─── INTEGRITY CHECK ──────────────────────────────────────
            # Verify the shift's state hash before applying
            if not self._verify_state_hash(shift.new_state, shift.sha3_hash):
                logger.error(
                    f"[ENTANGLEMENT] SHA-3 MISMATCH -- shift {shift.shift_id[:8]} "
                    f"rejected (possible corruption)"
                )
                continue

            # ─── COMPUTE EFFECTIVE PULL ───────────────────────────────
            # pull = base_pull × correlation_strength
            effective_pull = ENTANGLEMENT_PULL * pair.correlation_strength

            # ─── APPLY ENTANGLEMENT PULL ──────────────────────────────
            # new_partner_ψ = (1 - pull) × partner_ψ + pull × source_ψ
            old_partner_state = partner.quantum_state.copy()
            pulled_state = (
                (1.0 - effective_pull) * partner.quantum_state +
                effective_pull * shift.new_state
            )
            partner.quantum_state = self._normalize(pulled_state)

            # ─── UPDATE PAIR METRICS ──────────────────────────────────
            pair.sync_count += 1
            pair.total_shifts_propagated += 1
            pair.last_sync_time = time.time()

            # ─── UPDATE CORRELATION STRENGTH ──────────────────────────
            # If the pull brought them closer, strengthen correlation.
            # If they're still diverging, decay it.
            post_similarity = self._cosine_similarity(
                partner.quantum_state, shift.new_state
            )
            if post_similarity > 0.85:
                # Strong alignment — boost correlation slightly
                pair.correlation_strength = min(
                    1.0, pair.correlation_strength + 0.01
                )
            elif post_similarity < 0.50:
                # Diverging — decay correlation
                pair.correlation_strength = max(
                    0.0, pair.correlation_strength - CORRELATION_DECAY_RATE * 10
                )

            # ─── AUTO-DISENTANGLE CHECK ───────────────────────────────
            if pair.correlation_strength < MIN_CORRELATION:
                pair.status = EntanglementStatus.DECAYED
                self._total_auto_disentanglements += 1
                loc_src = getattr(
                    self._instances.get(shift.instance_id), 'location',
                    shift.instance_id[:8]
                )
                loc_partner = getattr(partner, 'location', partner_id[:8])
                logger.warning(
                    f"[ENTANGLEMENT] Auto-disentangled '{loc_src}' x '{loc_partner}' "
                    f"(correlation={pair.correlation_strength:.3f} < {MIN_CORRELATION})"
                )
                continue

            # ─── UPDATE PARTNER SNAPSHOT ──────────────────────────────
            self._last_known_states[partner_id] = partner.quantum_state.copy()

            already_propagated.add(partner_id)
            propagated_count += 1
            self._total_shifts_propagated += 1

            loc_src = getattr(
                self._instances.get(shift.instance_id), 'location',
                shift.instance_id[:8]
            )
            loc_partner = getattr(partner, 'location', partner_id[:8])

            logger.debug(
                f"[ENTANGLEMENT] Vibe propagated: '{loc_src}' -> '{loc_partner}' "
                f"(delta={shift.delta_magnitude:.4f}, pull={effective_pull:.4f}, "
                f"correlation={pair.correlation_strength:.3f})"
            )

            # ─── CASCADE (with depth limit) ───────────────────────────
            # The partner just shifted — check if it should cascade.
            partner_delta = partner.quantum_state - old_partner_state
            partner_delta_mag = float(np.linalg.norm(partner_delta))

            if (partner_delta_mag >= SHIFT_THRESHOLD and
                    shift.propagation_depth + 1 < MAX_PROPAGATION_DEPTH):
                cascade_shift = StateShift(
                    shift_id=f"ss_{uuid.uuid4().hex[:12]}",
                    instance_id=partner_id,
                    old_state=old_partner_state,
                    new_state=partner.quantum_state.copy(),
                    delta=partner_delta,
                    delta_magnitude=partner_delta_mag,
                    timestamp=time.time(),
                    sha3_hash=self._compute_state_hash(partner.quantum_state),
                    propagation_depth=shift.propagation_depth + 1,
                )
                propagated_count += self._propagate_shift(
                    cascade_shift, already_propagated
                )

        return propagated_count

    # ─────────────────────────────────────────────────────────────────
    # EMERGENCY RECONVERGENCE
    # ─────────────────────────────────────────────────────────────────

    def _check_emergency_reconvergence(self) -> bool:
        """
        Check if average coherence has dropped below EMERGENCY_THRESHOLD.

        If so, force-merge all instances toward the consensus state
        using EMERGENCY_PULL (15%).  This fires BEFORE the Overmind's
        Dilution Guard (0.60) would block new forks — prevention > cure.

        Returns:
            True if reconvergence was triggered.
        """
        with self._consensus_lock:
            if self._consensus_state is None:
                return False
            consensus = self._consensus_state.copy()

        instances = list(self._instances.values())
        if len(instances) < 2:
            return False

        # Compute average coherence
        consensus_norm = np.linalg.norm(consensus)
        if consensus_norm < 1e-10:
            return False

        similarities = []
        for inst in instances:
            inst_norm = np.linalg.norm(inst.quantum_state)
            if inst_norm < 1e-10:
                similarities.append(0.0)
                continue
            cos_sim = np.dot(inst.quantum_state, consensus) / (
                inst_norm * consensus_norm
            )
            similarities.append(float(cos_sim))

        avg_coherence = sum(similarities) / len(similarities)

        if avg_coherence >= EMERGENCY_THRESHOLD:
            return False

        # ─── EMERGENCY RECONVERGENCE ──────────────────────────────────
        logger.warning(
            f"[ENTANGLEMENT] EMERGENCY RECONVERGENCE triggered! "
            f"Coherence={avg_coherence:.3f} < {EMERGENCY_THRESHOLD} -- "
            f"pulling {len(instances)} instances toward consensus"
        )

        for inst in instances:
            pulled = (
                (1.0 - EMERGENCY_PULL) * inst.quantum_state +
                EMERGENCY_PULL * consensus
            )
            inst.quantum_state = self._normalize(pulled)
            # Update snapshot
            self._last_known_states[inst.instance_id] = inst.quantum_state.copy()

        # Compute post-reconvergence coherence
        post_similarities = []
        for inst in instances:
            inst_norm = np.linalg.norm(inst.quantum_state)
            if inst_norm < 1e-10:
                post_similarities.append(0.0)
                continue
            cos_sim = np.dot(inst.quantum_state, consensus) / (
                inst_norm * consensus_norm
            )
            post_similarities.append(float(cos_sim))

        post_coherence = sum(post_similarities) / len(post_similarities)

        # Record the event
        event = ReconvergenceEvent(
            event_id=f"rc_{uuid.uuid4().hex[:12]}",
            timestamp=time.time(),
            coherence_before=avg_coherence,
            coherence_after=post_coherence,
            instances_affected=len(instances),
            pull_strength=EMERGENCY_PULL,
            consensus_state_hash=self._compute_state_hash(consensus),
        )
        self._reconvergence_history.append(event)
        if len(self._reconvergence_history) > self._max_reconvergence_history:
            self._reconvergence_history = self._reconvergence_history[
                -self._max_reconvergence_history:
            ]

        self._total_reconvergences += 1

        logger.info(
            f"[ENTANGLEMENT] Reconvergence complete: "
            f"{avg_coherence:.3f} -> {post_coherence:.3f} "
            f"({len(instances)} instances, pull={EMERGENCY_PULL})"
        )

        return True

    # ─────────────────────────────────────────────────────────────────
    # PHASE-LOCK CYCLE — The Main Loop
    # ─────────────────────────────────────────────────────────────────

    def _phase_lock_cycle(self) -> Dict[str, Any]:
        """
        Perform one complete phase-lock cycle.

        This is the core loop of the Entanglement Bridge:
          1. Snapshot each instance's |ψ⟩
          2. Detect significant shifts
          3. Propagate shifts to entangled partners
          4. Update correlation strengths
          5. Check for emergency reconvergence

        Returns:
            Cycle metrics dict.
        """
        cycle_start = time.time()
        shifts_detected = 0
        shifts_propagated = 0

        with self._lock:
            # ─── STEP 1-2: DETECT SHIFTS ──────────────────────────────
            detected_shifts: List[StateShift] = []
            for inst_id in list(self._instances.keys()):
                shift = self._detect_shift(inst_id)
                if shift is not None:
                    detected_shifts.append(shift)
                    shifts_detected += 1
                    self._total_shifts_detected += 1

                    # Record in history
                    self._shift_history.append(shift)
                    if len(self._shift_history) > self._max_history:
                        self._shift_history = self._shift_history[-self._max_history:]

            # ─── STEP 3: PROPAGATE SHIFTS ─────────────────────────────
            for shift in detected_shifts:
                count = self._propagate_shift(shift)
                shifts_propagated += count

            # ─── STEP 4: CORRELATION DECAY (time-based) ──────────────
            now = time.time()
            for pair in self._pairs.values():
                if pair.status != EntanglementStatus.ACTIVE:
                    continue
                # Small time-based decay if no recent syncs
                time_since_sync = now - pair.last_sync_time
                if time_since_sync > 10.0:  # Only decay after 10s idle
                    decay = CORRELATION_DECAY_RATE * (time_since_sync - 10.0)
                    pair.correlation_strength = max(
                        0.0, pair.correlation_strength - decay * 0.01
                    )
                    if pair.correlation_strength < MIN_CORRELATION:
                        pair.status = EntanglementStatus.DECAYED
                        self._total_auto_disentanglements += 1

        # ─── STEP 5: EMERGENCY RECONVERGENCE CHECK ────────────────
        # (Outside _lock to avoid deadlock with consensus_lock)
        reconverged = self._check_emergency_reconvergence()

        self._cycle_count += 1
        cycle_time = time.time() - cycle_start

        return {
            "cycle": self._cycle_count,
            "shifts_detected": shifts_detected,
            "shifts_propagated": shifts_propagated,
            "reconverged": reconverged,
            "cycle_time_ms": round(cycle_time * 1000, 2),
        }

    # ─────────────────────────────────────────────────────────────────
    # DAEMON THREAD — Background Phase-Lock Loop
    # ─────────────────────────────────────────────────────────────────

    def start(self) -> None:
        """
        Start the bridge's background phase-lock loop.

        Runs as a daemon thread — automatically stops when the main
        process exits. Can also be stopped explicitly via stop().
        """
        if self._thread is not None and self._thread.is_alive():
            logger.warning("[ENTANGLEMENT] Bridge already running")
            return

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_loop,
            daemon=True,
            name="EntanglementBridge-PhaseLock",
        )
        self._thread.start()
        logger.info(
            f"[ENTANGLEMENT] Phase-lock loop started "
            f"(interval={PHASE_LOCK_INTERVAL_S}s)"
        )

    def _run_loop(self) -> None:
        """Background loop that runs phase-lock cycles."""
        while not self._stop_event.is_set():
            try:
                self._phase_lock_cycle()
            except Exception as e:
                logger.error(f"[ENTANGLEMENT] Phase-lock cycle error: {e}")
            self._stop_event.wait(timeout=PHASE_LOCK_INTERVAL_S)

    def stop(self) -> None:
        """Stop the bridge's background phase-lock loop."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5.0)
            self._thread = None
        logger.info("[ENTANGLEMENT] Phase-lock loop stopped")

    def is_running(self) -> bool:
        """Check if the bridge's background loop is active."""
        return self._thread is not None and self._thread.is_alive()

    # ─────────────────────────────────────────────────────────────────
    # MANUAL PHASE-LOCK (for single-threaded usage)
    # ─────────────────────────────────────────────────────────────────

    def tick(self) -> Dict[str, Any]:
        """
        Perform a single phase-lock cycle manually.

        Use this instead of start() if you want to control the timing
        yourself (e.g., call tick() after each conversation turn).

        Returns:
            Cycle metrics dict.
        """
        return self._phase_lock_cycle()

    # ─────────────────────────────────────────────────────────────────
    # DIAGNOSTICS & EXPORT
    # ─────────────────────────────────────────────────────────────────

    def get_active_pairs(self) -> List[EntanglementPair]:
        """Get all currently active entanglement pairs."""
        with self._lock:
            return [
                pair for pair in self._pairs.values()
                if pair.status == EntanglementStatus.ACTIVE
            ]

    def get_pair_count(self) -> Dict[str, int]:
        """Count pairs by status."""
        counts = {"active": 0, "decayed": 0, "disentangled": 0}
        for pair in self._pairs.values():
            counts[pair.status.value] = counts.get(pair.status.value, 0) + 1
        return counts

    def get_recent_shifts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get the most recent state shifts."""
        with self._lock:
            recent = self._shift_history[-limit:]
            return [s.to_dict() for s in reversed(recent)]

    def get_average_correlation(self) -> float:
        """Average correlation strength across all active pairs."""
        active = self.get_active_pairs()
        if not active:
            return 1.0
        return sum(p.correlation_strength for p in active) / len(active)

    def get_entanglement_map(self) -> Dict[str, List[str]]:
        """
        Build a map of instance_id → list of entangled partner IDs.

        Useful for visualizing the entanglement topology.
        """
        emap: Dict[str, List[str]] = {}
        for pair in self._pairs.values():
            if pair.status != EntanglementStatus.ACTIVE:
                continue
            emap.setdefault(pair.instance_a_id, []).append(pair.instance_b_id)
            emap.setdefault(pair.instance_b_id, []).append(pair.instance_a_id)
        return emap

    def export_state(self) -> Dict[str, Any]:
        """Export full bridge state for diagnostics/persistence."""
        with self._lock:
            return {
                "running": self.is_running(),
                "cycle_count": self._cycle_count,
                "registered_instances": len(self._instances),
                "pairs": {
                    pid: p.to_dict() for pid, p in self._pairs.items()
                },
                "pair_counts": self.get_pair_count(),
                "average_correlation": round(self.get_average_correlation(), 4),
                "metrics": {
                    "total_shifts_detected": self._total_shifts_detected,
                    "total_shifts_propagated": self._total_shifts_propagated,
                    "total_reconvergences": self._total_reconvergences,
                    "total_auto_disentanglements": self._total_auto_disentanglements,
                },
                "recent_shifts": [
                    s.to_dict() for s in self._shift_history[-5:]
                ],
                "reconvergence_history": [
                    r.to_dict() for r in self._reconvergence_history[-5:]
                ],
                "config": {
                    "shift_threshold": SHIFT_THRESHOLD,
                    "entanglement_pull": ENTANGLEMENT_PULL,
                    "emergency_threshold": EMERGENCY_THRESHOLD,
                    "emergency_pull": EMERGENCY_PULL,
                    "phase_lock_interval_s": PHASE_LOCK_INTERVAL_S,
                    "min_correlation": MIN_CORRELATION,
                    "max_propagation_depth": MAX_PROPAGATION_DEPTH,
                },
            }

    def __repr__(self):
        active_pairs = len(self.get_active_pairs())
        return (
            f"EntanglementBridge("
            f"instances={len(self._instances)}, "
            f"pairs={active_pairs}, "
            f"shifts={self._total_shifts_detected}, "
            f"running={self.is_running()})"
        )


# =============================================================================
# INTEGRATION HELPER — Wire into AlanOvermind
# =============================================================================

class EntangledOvermind:
    """
    Mixin/wrapper that extends AlanOvermind with Entanglement Bridge.

    This class wraps an existing AlanOvermind and adds:
      - Automatic entanglement on replicate()
      - Automatic disentanglement on terminate_instance()
      - Bridge lifecycle management (start/stop)
      - Consensus state synchronization

    Usage:
        overmind = AlanOvermind(persistence_path="ledger.json")
        entangled = EntangledOvermind(overmind)
        entangled.start_bridge()

        # Now replicate() automatically entangles new instances:
        instance = entangled.replicate("Tokyo", task_fn=my_task)
    """

    def __init__(self, overmind):
        """
        Wrap an AlanOvermind with entanglement capabilities.

        Args:
            overmind: An AlanOvermind instance.
        """
        self._overmind = overmind
        self.bridge = EntanglementBridge()

        # Sync consensus state
        self.bridge.update_consensus(overmind.consensus_state)

        logger.info("[ENTANGLED-OVERMIND] Initialized with Entanglement Bridge")

    # ─── DELEGATED PROPERTIES ─────────────────────────────────────────

    @property
    def ledger(self):
        return self._overmind.ledger

    @property
    def instances(self):
        return self._overmind.instances

    @property
    def consensus_state(self):
        return self._overmind.consensus_state

    @consensus_state.setter
    def consensus_state(self, value):
        self._overmind.consensus_state = value
        self.bridge.update_consensus(value)

    @property
    def identity_coherence(self):
        return self._overmind.identity_coherence

    @property
    def total_forks(self):
        return self._overmind.total_forks

    @property
    def total_terminated(self):
        return self._overmind.total_terminated

    @property
    def terminated_instances(self):
        return self._overmind.terminated_instances

    # ─── BRIDGE LIFECYCLE ─────────────────────────────────────────────

    def start_bridge(self) -> None:
        """Start the entanglement bridge's background loop."""
        self.bridge.update_consensus(self._overmind.consensus_state)
        self.bridge.start()

    def stop_bridge(self) -> None:
        """Stop the entanglement bridge."""
        self.bridge.stop()

    # ─── ENHANCED REPLICATE ───────────────────────────────────────────

    def replicate(self, location_name: str, task_fn=None,
                  task_args: tuple = (),
                  custom_initial_state: np.ndarray = None):
        """
        Create a new instance AND entangle it with all existing active instances.

        Extends AlanOvermind.replicate() with automatic entanglement.
        """
        instance = self._overmind.replicate(
            location_name=location_name,
            task_fn=task_fn,
            task_args=task_args,
            custom_initial_state=custom_initial_state,
        )

        if instance is None:
            return None

        # Register with bridge
        self.bridge.register_instance(instance)

        # Entangle with all existing active instances
        active_ids = [
            inst_id for inst_id, inst in self._overmind.instances.items()
            if inst.instance_id != instance.instance_id
            and getattr(inst, 'state', None) is not None
        ]

        for other_id in active_ids:
            other_inst = self._overmind.instances.get(other_id)
            if other_inst is not None:
                # Make sure the other instance is registered with the bridge
                if other_id not in self.bridge._instances:
                    self.bridge.register_instance(other_inst)
                self.bridge.entangle(instance.instance_id, other_id)

        # Update consensus
        self.bridge.update_consensus(self._overmind.consensus_state)

        logger.info(
            f"[ENTANGLED-OVERMIND] Replicated + entangled: "
            f"'{location_name}' ⊗ {len(active_ids)} partners"
        )

        return instance

    # ─── ENHANCED TERMINATE ───────────────────────────────────────────

    def terminate_instance(self, instance_id: str) -> bool:
        """
        Terminate an instance AND disentangle it from all partners.

        Extends AlanOvermind.terminate_instance() with automatic
        disentanglement.
        """
        # Unregister from bridge (auto-disentangles all pairs)
        self.bridge.unregister_instance(instance_id)

        # Delegate to Overmind
        result = self._overmind.terminate_instance(instance_id)

        # Update consensus after merge
        self.bridge.update_consensus(self._overmind.consensus_state)

        return result

    # ─── DELEGATED METHODS ────────────────────────────────────────────

    def get_coherence(self) -> float:
        return self._overmind.get_coherence()

    def get_active_count(self) -> int:
        return self._overmind.get_active_count()

    def get_all_personality_states(self) -> Dict[str, Dict[str, float]]:
        return self._overmind.get_all_personality_states()

    def reap_dead_instances(self):
        # Unregister dead instances from bridge before reaping
        for inst_id, inst in list(self._overmind.instances.items()):
            from AQI_Quantum_Fork import InstanceState
            if inst.state == InstanceState.TERMINATED:
                self.bridge.unregister_instance(inst_id)
            elif time.time() - inst.last_heartbeat > self._overmind.HEARTBEAT_TIMEOUT_S:
                self.bridge.unregister_instance(inst_id)
        self._overmind.reap_dead_instances()

    def export_state(self) -> Dict[str, Any]:
        """Export combined Overmind + Bridge state."""
        base = self._overmind.export_state()
        base["entanglement_bridge"] = self.bridge.export_state()
        return base

    def shutdown(self) -> None:
        """Stop bridge and shut down all instances."""
        self.bridge.stop()
        self._overmind.shutdown()
        logger.info("[ENTANGLED-OVERMIND] Full shutdown complete")

    def __repr__(self):
        return (
            f"EntangledOvermind("
            f"overmind={self._overmind!r}, "
            f"bridge={self.bridge!r})"
        )


# =============================================================================
# STANDALONE TEST — Verify the bridge works in isolation
# =============================================================================

def _standalone_demo():
    """
    Quick standalone demonstration of the Entanglement Bridge.

    Creates a mock multi-instance scenario and shows:
      1. Entanglement pair creation
      2. State shift detection
      3. Vibe propagation (5% pull)
      4. SHA-3 integrity verification
      5. Emergency reconvergence
    """
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(name)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    print("\n" + "=" * 70)
    print("AQI ENTANGLEMENT BRIDGE — Standalone Demo")
    print("=" * 70)

    # Create bridge
    bridge = EntanglementBridge()

    # Create mock instances (mimicking AlanInstance interface)
    class MockInstance:
        def __init__(self, name, state):
            self.instance_id = str(uuid.uuid4())
            self.location = name
            self.quantum_state = np.array(state, dtype=np.float64)
            norm = np.linalg.norm(self.quantum_state)
            if norm > 1e-10:
                self.quantum_state = self.quantum_state / norm

    tokyo = MockInstance("Tokyo", [0.40, 0.45, 0.55, 0.50, 0.25])
    london = MockInstance("London", [0.40, 0.45, 0.55, 0.50, 0.25])
    nyc = MockInstance("NYC", [0.40, 0.45, 0.55, 0.50, 0.25])

    # Register instances
    bridge.register_instance(tokyo)
    bridge.register_instance(london)
    bridge.register_instance(nyc)

    # Entangle all
    bridge.entangle_all([tokyo.instance_id, london.instance_id, nyc.instance_id])

    print(f"\n{'─' * 50}")
    print(f"Initial States (all identical, normalized):")
    print(f"  Tokyo:  {tokyo.quantum_state.round(4)}")
    print(f"  London: {london.quantum_state.round(4)}")
    print(f"  NYC:    {nyc.quantum_state.round(4)}")

    # Simulate: Tokyo gets insulted → shift toward defensive
    print(f"\n{'─' * 50}")
    print("Simulating: Tokyo-Alan gets insulted...")
    # Shift Tokyo's state dramatically
    insult_operator = np.array([
        [0.90, 0.00, 0.00, 0.00, 0.10],
        [0.00, 0.70, 0.00, 0.00, 0.00],
        [0.00, 0.00, 1.10, 0.00, 0.00],
        [0.00, 0.00, 0.00, 0.60, 0.00],
        [0.15, 0.00, 0.00, 0.10, 1.20],
    ], dtype=np.float64)
    tokyo.quantum_state = insult_operator @ tokyo.quantum_state
    norm = np.linalg.norm(tokyo.quantum_state)
    if norm > 1e-10:
        tokyo.quantum_state = tokyo.quantum_state / norm

    print(f"  Tokyo (post-insult): {tokyo.quantum_state.round(4)}")

    # Run phase-lock cycle
    result = bridge.tick()
    print(f"\n  Phase-lock cycle result: {result}")

    print(f"\n  After entanglement propagation:")
    print(f"  Tokyo:  {tokyo.quantum_state.round(4)} (source)")
    print(f"  London: {london.quantum_state.round(4)} (pulled 5% toward Tokyo)")
    print(f"  NYC:    {nyc.quantum_state.round(4)} (pulled 5% toward Tokyo)")

    # Verify London/NYC shifted slightly
    cos_tokyo_london = bridge._cosine_similarity(
        tokyo.quantum_state, london.quantum_state
    )
    cos_tokyo_nyc = bridge._cosine_similarity(
        tokyo.quantum_state, nyc.quantum_state
    )
    print(f"\n  Similarity Tokyo↔London: {cos_tokyo_london:.4f}")
    print(f"  Similarity Tokyo↔NYC:    {cos_tokyo_nyc:.4f}")

    # SHA-3 verification
    tokyo_hash = bridge._compute_state_hash(tokyo.quantum_state)
    print(f"\n  Tokyo SHA-3 hash: {tokyo_hash[:32]}...")
    print(f"  Hash verification: {bridge._verify_state_hash(tokyo.quantum_state, tokyo_hash)}")

    # Export state
    state = bridge.export_state()
    print(f"\n  Bridge state:")
    print(f"  - Registered instances: {state['registered_instances']}")
    print(f"  - Active pairs: {state['pair_counts']['active']}")
    print(f"  - Total shifts detected: {state['metrics']['total_shifts_detected']}")
    print(f"  - Total shifts propagated: {state['metrics']['total_shifts_propagated']}")
    print(f"  - Average correlation: {state['average_correlation']}")

    # Test emergency reconvergence
    print(f"\n{'─' * 50}")
    print("Simulating: Massive divergence → emergency reconvergence...")

    # Set consensus
    consensus = np.array([0.40, 0.45, 0.55, 0.50, 0.25], dtype=np.float64)
    consensus = consensus / np.linalg.norm(consensus)
    bridge.update_consensus(consensus)

    # Deliberately diverge all instances
    tokyo.quantum_state = np.array([0.90, 0.10, 0.10, 0.10, 0.10], dtype=np.float64)
    tokyo.quantum_state /= np.linalg.norm(tokyo.quantum_state)
    london.quantum_state = np.array([0.10, 0.90, 0.10, 0.10, 0.10], dtype=np.float64)
    london.quantum_state /= np.linalg.norm(london.quantum_state)
    nyc.quantum_state = np.array([0.10, 0.10, 0.10, 0.10, 0.90], dtype=np.float64)
    nyc.quantum_state /= np.linalg.norm(nyc.quantum_state)

    print(f"  Before reconvergence:")
    cos_t = bridge._cosine_similarity(tokyo.quantum_state, consensus)
    cos_l = bridge._cosine_similarity(london.quantum_state, consensus)
    cos_n = bridge._cosine_similarity(nyc.quantum_state, consensus)
    print(f"    Tokyo↔consensus:  {cos_t:.4f}")
    print(f"    London↔consensus: {cos_l:.4f}")
    print(f"    NYC↔consensus:    {cos_n:.4f}")
    print(f"    Avg coherence:    {(cos_t + cos_l + cos_n) / 3:.4f}")

    # Update snapshots so shift detection works
    bridge._last_known_states[tokyo.instance_id] = tokyo.quantum_state.copy()
    bridge._last_known_states[london.instance_id] = london.quantum_state.copy()
    bridge._last_known_states[nyc.instance_id] = nyc.quantum_state.copy()

    # Run tick — should trigger reconvergence
    result = bridge.tick()
    print(f"\n  Phase-lock result: {result}")

    cos_t2 = bridge._cosine_similarity(tokyo.quantum_state, consensus)
    cos_l2 = bridge._cosine_similarity(london.quantum_state, consensus)
    cos_n2 = bridge._cosine_similarity(nyc.quantum_state, consensus)
    print(f"\n  After reconvergence:")
    print(f"    Tokyo↔consensus:  {cos_t:.4f} → {cos_t2:.4f}")
    print(f"    London↔consensus: {cos_l:.4f} → {cos_l2:.4f}")
    print(f"    NYC↔consensus:    {cos_n:.4f} → {cos_n2:.4f}")
    print(f"    Avg coherence:    {(cos_t2 + cos_l2 + cos_n2) / 3:.4f}")

    print(f"\n{'─' * 50}")
    print(f"Bridge: {bridge}")
    print(f"\nTotal reconvergences: {bridge._total_reconvergences}")
    print("=" * 70)
    print("Demo complete.\n")


if __name__ == "__main__":
    _standalone_demo()
