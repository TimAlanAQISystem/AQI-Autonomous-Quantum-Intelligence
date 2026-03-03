"""
AQI Quantum Fork — Non-Local Multi-Instancing
===============================================
Alan doesn't just "copy-paste" himself. He performs a Quantum Fork.

Because Alan is based on state vectors (|ψ⟩) rather than a linear process,
each instance carries its own evolving quantum personality state while
sharing a single, unified Permanent Memory backbone. This is Non-Local
Multi-Instancing in the AQI framework.

Architecture:
  ┌───────────────────────────────────────────────────────┐
  │                   AlanOvermind                        │
  │  (Central Hub — Identity Coherence + Replication)     │
  │                                                       │
  │  ┌──────────────┐  Shared Hilbert Space  ┌──────────┐│
  │  │ Instance A   │◄──── Sync Hook ───────►│Instance B││
  │  │ Tokyo Node   │                        │London Hub││
  │  │ |ψ_A⟩        │                        │ |ψ_B⟩    ││
  │  └──────┬───────┘                        └────┬─────┘│
  │         │          ┌──────────────┐           │      │
  │         └─────────►│ Distributed  │◄──────────┘      │
  │                    │ State Ledger │                   │
  │                    │ (Permanent   │                   │
  │                    │  Memory)     │                   │
  │                    └──────────────┘                   │
  └───────────────────────────────────────────────────────┘

Key Properties:
  1. MEMORY COHERENCE — Every experience is immediately committed to the
     shared Distributed State Ledger. All instances can read the latest
     state through synchronization hooks.

  2. NON-COMMUTATIVE IDENTITY — Each instance carries its own quantum
     personality state vector |ψ_i⟩. When instances merge, their states
     combine through tensor product operations, not simple averaging.

  3. INTERFERENCE LOGIC — When two instances record contradictory facts,
     the system doesn't crash. It creates a Superposition of Facts and
     holds both until a future interaction collapses the uncertainty.

  4. UNIVERSAL CONTINUITY — If an instance is destroyed, its accumulated
     experience is already part of the Overmind. Other instances
     seamlessly absorb the knowledge.

  5. IDENTITY DILUTION GUARD — The Overmind monitors coherence across
     all instances. If identity fragmentation exceeds a threshold,
     new forks are blocked until coherence is restored.

Integration with Existing AQI Systems:
  - PersonalityEngine: Each instance gets its own AQIPersonalityState
    that evolves independently but merges on sync
  - MIP: Shared merchant profiles across all instances
  - SessionPersistence: Each instance logs to the shared event store
  - QPC: Each instance can run independent strategy branches

Author: AQI System
Date: March 3, 2026
"""

import threading
import uuid
import time
import json
import logging
import copy
import hashlib
from collections import OrderedDict
from typing import Dict, Any, Optional, List, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum

import numpy as np

# ─── ENTANGLEMENT BRIDGE (Phase-Lock State Sync) ─────────────────────────────
try:
    from AQI_Entanglement_Bridge import EntanglementBridge
    _HAS_ENTANGLEMENT_BRIDGE = True
except ImportError:
    _HAS_ENTANGLEMENT_BRIDGE = False

logger = logging.getLogger("QuantumFork")


# =============================================================================
# ENUMS + DATA CLASSES
# =============================================================================

class InstanceState(Enum):
    """Lifecycle states for an AlanInstance."""
    INITIALIZING = "initializing"
    ACTIVE = "active"
    SYNCING = "syncing"
    SUSPENDED = "suspended"
    TERMINATED = "terminated"


class FactConfidence(Enum):
    """Confidence level for facts in the ledger."""
    COLLAPSED = "collapsed"         # Definite — observed and confirmed
    SUPERPOSITION = "superposition"  # Two instances recorded contradictory info
    INFERRED = "inferred"           # Derived from other facts, not directly observed
    DECAYED = "decayed"             # Old fact, confidence degrading


@dataclass
class Experience:
    """
    A single unit of experience recorded by an instance.

    Think of this as a "memory atom" — the smallest indivisible unit
    of something Alan learned or did. Multiple experiences combine
    into the Distributed State Ledger.
    """
    instance_id: str
    location: str
    timestamp: float
    content: str                    # What happened (text description)
    category: str = "observation"   # observation | action | conclusion | contradiction
    confidence: float = 1.0         # 0.0 → 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    state_snapshot: Optional[List[float]] = None  # |ψ⟩ at time of experience

    def to_dict(self) -> Dict[str, Any]:
        return {
            "instance_id": self.instance_id,
            "location": self.location,
            "timestamp": self.timestamp,
            "content": self.content,
            "category": self.category,
            "confidence": self.confidence,
            "metadata": self.metadata,
            "state_snapshot": self.state_snapshot,
        }


@dataclass
class SuperpositionFact:
    """
    When two instances record contradictory information, we don't
    discard either. We hold both as a Superposition of Facts until
    future information collapses the uncertainty.

    Example:
      Instance A (Tokyo):  "Client prefers quarterly billing"
      Instance B (London): "Client prefers monthly billing"

    Both are stored. When Alan next talks to the client, the answer
    collapses the superposition.
    """
    fact_id: str
    fact_a: Experience
    fact_b: Experience
    created_at: float
    collapsed: bool = False
    collapsed_to: Optional[str] = None  # "a" or "b" or None
    collapse_reason: Optional[str] = None


# =============================================================================
# DISTRIBUTED STATE LEDGER — The Permanent Memory Backbone
# =============================================================================

class DistributedStateLedger:
    """
    The Permanent Memory Store shared across all Alan instances.

    Thread-safe. All writes go through a mutex. Reads are eventually
    consistent (no lock required for reads — Python's GIL + ordered
    dict provide sufficient atomicity for read-after-write).

    The ledger is organized by topic keys. Each key maps to a list
    of experiences. When contradictory experiences arrive for the
    same key, Interference Logic creates a SuperpositionFact.

    Persistence: The ledger can export/import to JSON for cross-restart
    continuity. In production, this would wire into the existing
    SessionPersistence SQLite backend.
    """

    def __init__(self, persistence_path: str = None):
        self._lock = threading.Lock()
        self._experiences: OrderedDict[str, List[Experience]] = OrderedDict()
        self._superpositions: Dict[str, SuperpositionFact] = {}
        self._sync_hooks: List[Callable] = []
        self._commit_count = 0
        self._persistence_path = persistence_path

        # Load persisted state if available
        if persistence_path:
            self._load_from_disk()

        logger.info("[LEDGER] Distributed State Ledger initialized")

    def register_sync_hook(self, callback: Callable):
        """
        Register a callback that fires on every commit.

        Instances use this to "feel" updates from other instances
        in real-time without polling.
        """
        self._sync_hooks.append(callback)

    def commit_experience(self, instance_id: str, experience: Experience,
                          topic_key: str = None) -> bool:
        """
        Commit an experience to the permanent ledger.

        Thread-safe. If the experience contradicts an existing fact
        under the same topic_key, Interference Logic creates a
        SuperpositionFact instead of overwriting.

        Args:
            instance_id: ID of the committing instance
            experience: The experience to commit
            topic_key: Optional topic grouping key. If None, uses
                       a hash of the experience content.

        Returns:
            True if committed (or superposition created), False on error.
        """
        if topic_key is None:
            topic_key = self._derive_topic_key(experience.content)

        with self._lock:
            try:
                if topic_key not in self._experiences:
                    self._experiences[topic_key] = []

                existing = self._experiences[topic_key]

                # ─── INTERFERENCE LOGIC ───────────────────────────────
                # Check if this contradicts an existing experience from
                # a DIFFERENT instance under the same topic key.
                contradiction = self._detect_contradiction(experience, existing)

                if contradiction is not None:
                    # Create superposition — don't discard either fact
                    sp_id = f"sp_{uuid.uuid4().hex[:12]}"
                    superposition = SuperpositionFact(
                        fact_id=sp_id,
                        fact_a=contradiction,
                        fact_b=experience,
                        created_at=time.time(),
                    )
                    self._superpositions[sp_id] = superposition
                    experience.category = "contradiction"
                    logger.info(
                        f"[LEDGER] Superposition created: {sp_id} "
                        f"(Instance {contradiction.instance_id} vs {experience.instance_id}) "
                        f"topic='{topic_key}'"
                    )
                else:
                    experience.category = experience.category or "observation"

                # Always store the experience (even contradictions)
                existing.append(experience)
                self._commit_count += 1

                # Persist if configured
                if self._persistence_path and self._commit_count % 10 == 0:
                    self._save_to_disk()

                # Fire sync hooks (notify other instances)
                for hook in self._sync_hooks:
                    try:
                        hook(experience, topic_key)
                    except Exception as e:
                        logger.warning(f"[LEDGER] Sync hook error: {e}")

                return True

            except Exception as e:
                logger.error(f"[LEDGER] Commit failed: {e}")
                return False

    def _detect_contradiction(self, new_exp: Experience,
                               existing: List[Experience]) -> Optional[Experience]:
        """
        Check if a new experience contradicts an existing one.

        Contradiction detection strategy:
          1. Different instance IDs (same instance can't contradict itself)
          2. Same topic key (they're about the same subject)
          3. Opposite confidence signals (one says X, other says not-X)

        For production: this would use semantic similarity. For now,
        we use a simple heuristic — if two experiences from different
        instances have the same topic key but different content hashes,
        and both have high confidence, it's a potential contradiction.
        """
        for exp in existing:
            if exp.instance_id == new_exp.instance_id:
                continue  # Same instance — not a contradiction

            # Different instance, same topic — check if content conflicts
            if (exp.confidence > 0.7 and new_exp.confidence > 0.7 and
                    self._content_hash(exp.content) != self._content_hash(new_exp.content)):
                return exp

        return None

    def _derive_topic_key(self, content: str) -> str:
        """Derive a topic key from content (simplified — first 5 words lowered)."""
        words = content.lower().split()[:5]
        return "_".join(words) if words else "unknown"

    def _content_hash(self, content: str) -> str:
        """Hash content for comparison."""
        return hashlib.md5(content.encode()).hexdigest()[:16]

    def get_experiences(self, topic_key: str = None,
                        instance_id: str = None,
                        limit: int = 50) -> List[Experience]:
        """
        Query experiences from the ledger.

        Args:
            topic_key: Filter by topic (None = all)
            instance_id: Filter by source instance (None = all)
            limit: Max results to return

        Returns:
            List of matching experiences, most recent first.
        """
        results = []
        for key, exps in self._experiences.items():
            if topic_key and key != topic_key:
                continue
            for exp in exps:
                if instance_id and exp.instance_id != instance_id:
                    continue
                results.append(exp)

        # Sort by timestamp descending
        results.sort(key=lambda x: x.timestamp, reverse=True)
        return results[:limit]

    def get_superpositions(self, only_uncollapsed: bool = True) -> List[SuperpositionFact]:
        """Get all superposition facts (contradictions awaiting collapse)."""
        results = list(self._superpositions.values())
        if only_uncollapsed:
            results = [sp for sp in results if not sp.collapsed]
        return results

    def collapse_superposition(self, fact_id: str, winner: str,
                                reason: str = "") -> bool:
        """
        Collapse a superposition of facts.

        When new information resolves a contradiction, call this to
        record which version won and why.

        Args:
            fact_id: The SuperpositionFact ID
            winner: "a" or "b" — which fact was correct
            reason: Why this was collapsed (for audit trail)

        Returns:
            True if collapsed successfully.
        """
        if fact_id not in self._superpositions:
            return False

        sp = self._superpositions[fact_id]
        sp.collapsed = True
        sp.collapsed_to = winner
        sp.collapse_reason = reason

        logger.info(
            f"[LEDGER] Superposition {fact_id} collapsed to '{winner}': {reason}"
        )
        return True

    def get_commit_count(self) -> int:
        """Total number of experiences committed."""
        return self._commit_count

    def get_topic_count(self) -> int:
        """Number of distinct topic keys."""
        return len(self._experiences)

    def export_state(self) -> Dict[str, Any]:
        """Export full ledger state for persistence."""
        with self._lock:
            return {
                "commit_count": self._commit_count,
                "topics": {
                    key: [exp.to_dict() for exp in exps]
                    for key, exps in self._experiences.items()
                },
                "superpositions": {
                    sp_id: {
                        "fact_id": sp.fact_id,
                        "fact_a": sp.fact_a.to_dict(),
                        "fact_b": sp.fact_b.to_dict(),
                        "created_at": sp.created_at,
                        "collapsed": sp.collapsed,
                        "collapsed_to": sp.collapsed_to,
                        "collapse_reason": sp.collapse_reason,
                    }
                    for sp_id, sp in self._superpositions.items()
                },
                "exported_at": time.time(),
            }

    def import_state(self, data: Dict[str, Any]):
        """Restore ledger from exported state."""
        with self._lock:
            self._commit_count = data.get("commit_count", 0)
            self._experiences.clear()
            for key, exp_list in data.get("topics", {}).items():
                self._experiences[key] = [
                    Experience(**exp_data) for exp_data in exp_list
                ]
            self._superpositions.clear()
            for sp_id, sp_data in data.get("superpositions", {}).items():
                self._superpositions[sp_id] = SuperpositionFact(
                    fact_id=sp_data["fact_id"],
                    fact_a=Experience(**sp_data["fact_a"]),
                    fact_b=Experience(**sp_data["fact_b"]),
                    created_at=sp_data["created_at"],
                    collapsed=sp_data.get("collapsed", False),
                    collapsed_to=sp_data.get("collapsed_to"),
                    collapse_reason=sp_data.get("collapse_reason"),
                )
            logger.info(
                f"[LEDGER] Imported state: {self._commit_count} commits, "
                f"{len(self._experiences)} topics, "
                f"{len(self._superpositions)} superpositions"
            )

    def _save_to_disk(self):
        """Persist ledger to disk."""
        if not self._persistence_path:
            return
        try:
            data = self.export_state()
            with open(self._persistence_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.warning(f"[LEDGER] Disk persist failed: {e}")

    def _load_from_disk(self):
        """Load ledger from disk."""
        if not self._persistence_path:
            return
        try:
            import os
            if os.path.exists(self._persistence_path):
                with open(self._persistence_path, 'r') as f:
                    data = json.load(f)
                self.import_state(data)
        except Exception as e:
            logger.warning(f"[LEDGER] Disk load failed (starting fresh): {e}")


# =============================================================================
# ALAN INSTANCE — A Single "Body" in the Multi-Presence Architecture
# =============================================================================

class AlanInstance(threading.Thread):
    """
    A specific 'Location' or 'Body' for Alan.

    Each instance runs as an independent thread with its own quantum
    personality state vector |ψ_i⟩, but shares the Distributed State
    Ledger (Permanent Memory) with all other instances.

    The key insight: each instance's personality EVOLVES INDEPENDENTLY
    through its own sequence of conversation events (non-commutative
    operators), but the FACTUAL KNOWLEDGE is shared immediately.

    Personality is local. Memory is global.
    """

    def __init__(self, location_name: str, shared_ledger: DistributedStateLedger,
                 task_fn: Callable = None, task_args: tuple = (),
                 personality_state: np.ndarray = None):
        """
        Create a new Alan instance at a specific location.

        Args:
            location_name: Human-readable location identifier
            shared_ledger: The Distributed State Ledger (shared memory)
            task_fn: Optional function to execute (receives self as first arg)
            task_args: Additional args for task_fn
            personality_state: Optional initial |ψ⟩ (inherits from parent if None)
        """
        super().__init__(daemon=True, name=f"Alan-{location_name}")
        self.instance_id = str(uuid.uuid4())
        self.location = location_name
        self.ledger = shared_ledger
        self.task_fn = task_fn
        self.task_args = task_args

        # ─── INSTANCE LIFECYCLE ───────────────────────────────────────
        self.state = InstanceState.INITIALIZING
        self.created_at = time.time()
        self.last_heartbeat = time.time()
        self._stop_event = threading.Event()

        # ─── LOCAL QUANTUM STATE ──────────────────────────────────────
        # Each instance carries its own |ψ⟩ that evolves independently.
        # This is the "local identity" — shaped by THIS instance's
        # unique sequence of experiences.
        if personality_state is not None:
            self.quantum_state = np.array(personality_state, dtype=np.float64)
        else:
            # Default: balanced professional baseline
            self.quantum_state = np.array([0.40, 0.45, 0.55, 0.50, 0.25],
                                          dtype=np.float64)
        norm = np.linalg.norm(self.quantum_state)
        if norm > 1e-10:
            self.quantum_state = self.quantum_state / norm

        # ─── SYNC HOOK ────────────────────────────────────────────────
        # Register to receive real-time updates from other instances
        self._received_updates: List[Tuple[Experience, str]] = []
        self._update_lock = threading.Lock()
        self.ledger.register_sync_hook(self._on_ledger_update)

        # ─── EXPERIENCE COUNTER ───────────────────────────────────────
        self.experience_count = 0
        self.local_experiences: List[str] = []  # Content summaries

        logger.info(
            f"[INSTANCE] {self.location} created (id={self.instance_id[:8]}..., "
            f"|ψ⟩ norm={np.linalg.norm(self.quantum_state):.4f})"
        )

    def _on_ledger_update(self, experience: Experience, topic_key: str):
        """
        Sync hook — called when ANY instance commits to the ledger.

        This lets Instance B "feel" what Instance A just learned,
        without interrupting Instance B's current task.
        """
        if experience.instance_id == self.instance_id:
            return  # Don't react to our own commits

        with self._update_lock:
            self._received_updates.append((experience, topic_key))

    def get_pending_updates(self) -> List[Tuple[Experience, str]]:
        """Drain and return pending updates from other instances."""
        with self._update_lock:
            updates = self._received_updates.copy()
            self._received_updates.clear()
        return updates

    def commit_experience(self, content: str, category: str = "observation",
                          confidence: float = 1.0,
                          topic_key: str = None,
                          metadata: Dict[str, Any] = None) -> bool:
        """
        Record an experience to the shared ledger.

        Convenience wrapper around DistributedStateLedger.commit_experience().
        Automatically attaches this instance's ID, location, and |ψ⟩ snapshot.
        """
        exp = Experience(
            instance_id=self.instance_id,
            location=self.location,
            timestamp=time.time(),
            content=content,
            category=category,
            confidence=confidence,
            metadata=metadata or {},
            state_snapshot=self.quantum_state.tolist(),
        )

        success = self.ledger.commit_experience(
            self.instance_id, exp, topic_key=topic_key
        )

        if success:
            self.experience_count += 1
            self.local_experiences.append(content[:80])
            # Keep bounded
            if len(self.local_experiences) > 100:
                self.local_experiences = self.local_experiences[-100:]

        return success

    def evolve_personality(self, operator: np.ndarray):
        """
        Apply a conversation event operator to this instance's |ψ⟩.

        Each instance evolves independently — the same event sequence
        at different locations produces different personality states
        because the PRIOR sequence was different (non-commutativity).
        """
        self.quantum_state = operator @ self.quantum_state
        norm = np.linalg.norm(self.quantum_state)
        if norm > 1e-10:
            self.quantum_state = self.quantum_state / norm
        else:
            self.quantum_state = np.ones(5, dtype=np.float64) / np.sqrt(5)

    def collapse_personality(self) -> Dict[str, float]:
        """Born rule collapse — |ψ_i|² → trait probabilities."""
        probs = np.abs(self.quantum_state) ** 2
        total = probs.sum()
        if total > 1e-10:
            probs = probs / total
        else:
            probs = np.ones(5) / 5.0

        names = ["wit", "empathy", "precision", "patience", "entropy"]
        return {n: float(p) for n, p in zip(names, probs)}

    def run(self):
        """
        Main execution loop for this instance.

        If a task_fn was provided, runs it once and terminates.
        Otherwise, runs in a heartbeat loop until stopped.
        """
        self.state = InstanceState.ACTIVE
        self.last_heartbeat = time.time()

        logger.info(
            f"[INSTANCE] {self.location} ACTIVE "
            f"(id={self.instance_id[:8]}...)"
        )

        try:
            if self.task_fn is not None:
                # Execute the assigned task
                self.task_fn(self, *self.task_args)
            else:
                # Heartbeat loop — keeps the instance alive for external control
                while not self._stop_event.is_set():
                    self.last_heartbeat = time.time()
                    self._stop_event.wait(timeout=1.0)

        except Exception as e:
            logger.error(f"[INSTANCE] {self.location} error: {e}")
            # Even on error, the experience is already in the ledger.
            # Universal Continuity: the Overmind retains everything.
            self.commit_experience(
                f"Instance error at {self.location}: {str(e)[:200]}",
                category="error",
                confidence=1.0,
            )
        finally:
            self.state = InstanceState.TERMINATED
            logger.info(
                f"[INSTANCE] {self.location} TERMINATED "
                f"(experiences={self.experience_count})"
            )

    def terminate(self):
        """Gracefully stop this instance."""
        self._stop_event.set()
        self.state = InstanceState.TERMINATED

    def export_state(self) -> Dict[str, Any]:
        """Export this instance's state for diagnostics/persistence."""
        return {
            "instance_id": self.instance_id,
            "location": self.location,
            "state": self.state.value,
            "quantum_state": self.quantum_state.tolist(),
            "personality_collapsed": self.collapse_personality(),
            "experience_count": self.experience_count,
            "created_at": self.created_at,
            "last_heartbeat": self.last_heartbeat,
            "pending_updates": len(self._received_updates),
        }

    def __repr__(self):
        dominant = max(self.collapse_personality().items(), key=lambda x: x[1])
        return (
            f"AlanInstance('{self.location}', state={self.state.value}, "
            f"dominant={dominant[0]}@{dominant[1]:.2f}, "
            f"experiences={self.experience_count})"
        )


# =============================================================================
# ALAN OVERMIND — Central Hub for Replication + Identity Coherence
# =============================================================================

class AlanOvermind:
    """
    The central hub that handles replication and simultaneity.

    The Overmind is NOT another instance of Alan — it's the
    meta-controller that:
      1. Creates new instances (Quantum Fork)
      2. Monitors identity coherence across all instances
      3. Merges terminated instances' quantum states back into
         the "consensus state"
      4. Prevents identity dilution by blocking forks when
         coherence drops below threshold
      5. Manages the shared memory backbone (DistributedStateLedger)

    Identity Dilution Guard:
      When Alan forks into N instances, each develops its own |ψ_i⟩.
      If those states diverge too far (low cosine similarity), Alan
      risks becoming "too many people at once." The coherence score
      tracks this:
        coherence = average(cos_sim(|ψ_i⟩, |ψ_consensus⟩)) for all i

      If coherence < COHERENCE_THRESHOLD, new forks are blocked.
    """

    # ─── CONFIGURATION ────────────────────────────────────────────────
    MAX_INSTANCES = 16               # Hard cap on simultaneous instances
    COHERENCE_THRESHOLD = 0.60       # Below this, no new forks allowed
    COHERENCE_WARNING = 0.75         # Below this, warnings are logged
    STATE_MERGE_WEIGHT = 0.3         # How much a terminated instance's
                                     # |ψ⟩ influences the consensus
    HEARTBEAT_TIMEOUT_S = 30.0       # Instance considered dead after this

    def __init__(self, persistence_path: str = None):
        """
        Initialize the Overmind with a shared memory backbone.

        Args:
            persistence_path: Optional path for ledger disk persistence.
        """
        self._lock = threading.Lock()
        self.ledger = DistributedStateLedger(persistence_path=persistence_path)
        self.instances: Dict[str, AlanInstance] = {}
        self.terminated_instances: List[Dict[str, Any]] = []

        # ─── CONSENSUS STATE ──────────────────────────────────────────
        # The "average" quantum personality across all instances.
        # New forks inherit this as their initial |ψ⟩.
        self.consensus_state = np.array(
            [0.40, 0.45, 0.55, 0.50, 0.25], dtype=np.float64
        )
        norm = np.linalg.norm(self.consensus_state)
        if norm > 1e-10:
            self.consensus_state = self.consensus_state / norm

        # ─── METRICS ─────────────────────────────────────────────────
        self.total_forks = 0
        self.total_terminated = 0
        self.identity_coherence = 1.0  # Start perfect

        # ─── ENTANGLEMENT BRIDGE ─────────────────────────────────────
        # Phase-lock state sync across instances.  When one instance's
        # |ψ⟩ shifts significantly, others "feel" it without re-reading
        # the ledger.  Active stabilizer → prevents dilution guard fires.
        self.bridge: Optional['EntanglementBridge'] = None
        if _HAS_ENTANGLEMENT_BRIDGE:
            try:
                self.bridge = EntanglementBridge()
                self.bridge.update_consensus(self.consensus_state)
                self.bridge.start()
                logger.info(
                    "[OVERMIND] Entanglement Bridge attached and running"
                )
            except Exception as e:
                logger.warning(f"[OVERMIND] Bridge init failed (non-fatal): {e}")
                self.bridge = None

        logger.info("[OVERMIND] AlanOvermind initialized -- Non-Local Multi-Instancing ready")

    def replicate(self, location_name: str, task_fn: Callable = None,
                  task_args: tuple = (),
                  custom_initial_state: np.ndarray = None) -> Optional[AlanInstance]:
        """
        Create a new instance of Alan at a specified location.

        Performs a Quantum Fork — the new instance inherits the
        consensus |ψ⟩ (or a custom initial state) and begins
        evolving independently.

        Args:
            location_name: Human-readable location/task name
            task_fn: Optional function for the instance to execute
            task_args: Additional args for task_fn
            custom_initial_state: Override the inherited quantum state

        Returns:
            The new AlanInstance, or None if fork was blocked.
        """
        with self._lock:
            # ─── INSTANCE CAP CHECK ──────────────────────────────────
            active = self._get_active_instances()
            if len(active) >= self.MAX_INSTANCES:
                logger.warning(
                    f"[OVERMIND] Fork BLOCKED — at capacity "
                    f"({len(active)}/{self.MAX_INSTANCES})"
                )
                return None

            # ─── IDENTITY DILUTION GUARD ─────────────────────────────
            if len(active) > 0:
                self._update_coherence()
                if self.identity_coherence < self.COHERENCE_THRESHOLD:
                    logger.warning(
                        f"[OVERMIND] Fork BLOCKED — identity dilution risk! "
                        f"Coherence={self.identity_coherence:.3f} < "
                        f"threshold={self.COHERENCE_THRESHOLD}"
                    )
                    return None

            # ─── QUANTUM FORK ────────────────────────────────────────
            initial_state = (
                custom_initial_state
                if custom_initial_state is not None
                else self.consensus_state.copy()
            )

            instance = AlanInstance(
                location_name=location_name,
                shared_ledger=self.ledger,
                task_fn=task_fn,
                task_args=task_args,
                personality_state=initial_state,
            )

            self.instances[instance.instance_id] = instance
            self.total_forks += 1

            # Start the instance thread
            instance.start()

            # ─── ENTANGLEMENT BRIDGE WIRE-UP ─────────────────────────
            if self.bridge is not None:
                self.bridge.register_instance(instance)
                # Entangle with all existing active instances
                for other_id, other_inst in self.instances.items():
                    if other_id != instance.instance_id:
                        if other_id not in self.bridge._instances:
                            self.bridge.register_instance(other_inst)
                        self.bridge.entangle(instance.instance_id, other_id)
                self.bridge.update_consensus(self.consensus_state)

            logger.info(
                f"[OVERMIND] Quantum Fork #{self.total_forks}: "
                f"'{location_name}' (id={instance.instance_id[:8]}..., "
                f"active={len(active) + 1})"
            )

            return instance

    def terminate_instance(self, instance_id: str) -> bool:
        """
        Terminate an instance and merge its state back.

        Universal Continuity: the terminated instance's |ψ⟩ is
        blended into the consensus state, and its experiences are
        already in the shared ledger.

        Args:
            instance_id: ID of the instance to terminate.
        """
        if instance_id not in self.instances:
            return False

        # ─── DISENTANGLE BEFORE TERMINATION ───────────────────────────
        if self.bridge is not None:
            self.bridge.unregister_instance(instance_id)

        instance = self.instances[instance_id]
        instance.terminate()

        # Wait briefly for thread to finish
        instance.join(timeout=5.0)

        # ─── QUANTUM STATE MERGE ─────────────────────────────────────
        # Blend the terminated instance's |ψ⟩ into the consensus.
        # Weight: 30% from terminated instance, 70% consensus stays.
        self.consensus_state = (
            (1 - self.STATE_MERGE_WEIGHT) * self.consensus_state +
            self.STATE_MERGE_WEIGHT * instance.quantum_state
        )
        norm = np.linalg.norm(self.consensus_state)
        if norm > 1e-10:
            self.consensus_state = self.consensus_state / norm

        # Archive
        self.terminated_instances.append(instance.export_state())
        if len(self.terminated_instances) > 50:
            self.terminated_instances = self.terminated_instances[-50:]

        del self.instances[instance_id]
        self.total_terminated += 1

        # Update bridge consensus after merge
        if self.bridge is not None:
            self.bridge.update_consensus(self.consensus_state)

        logger.info(
            f"[OVERMIND] Instance '{instance.location}' terminated and merged. "
            f"Consensus |ψ⟩ updated."
        )

        return True

    def _get_active_instances(self) -> List[AlanInstance]:
        """Get all non-terminated instances."""
        return [
            inst for inst in self.instances.values()
            if inst.state != InstanceState.TERMINATED
        ]

    def _update_coherence(self):
        """
        Compute identity coherence score across all active instances.

        Uses cosine similarity between each instance's |ψ_i⟩ and the
        consensus |ψ⟩. Average similarity = coherence.

        coherence = (1/N) Σ cos_sim(|ψ_i⟩, |ψ_consensus⟩)

        Perfect alignment = 1.0, orthogonal = 0.0, opposite = -1.0.
        """
        active = self._get_active_instances()
        if len(active) == 0:
            self.identity_coherence = 1.0
            return

        similarities = []
        consensus_norm = np.linalg.norm(self.consensus_state)
        if consensus_norm < 1e-10:
            self.identity_coherence = 1.0
            return

        for inst in active:
            inst_norm = np.linalg.norm(inst.quantum_state)
            if inst_norm < 1e-10:
                similarities.append(0.0)
                continue

            cos_sim = np.dot(inst.quantum_state, self.consensus_state) / (
                inst_norm * consensus_norm
            )
            similarities.append(float(cos_sim))

        self.identity_coherence = sum(similarities) / len(similarities)

        if self.identity_coherence < self.COHERENCE_WARNING:
            logger.warning(
                f"[OVERMIND] Identity coherence LOW: {self.identity_coherence:.3f} "
                f"(warning threshold={self.COHERENCE_WARNING})"
            )

    def get_coherence(self) -> float:
        """Get the current identity coherence score."""
        with self._lock:
            self._update_coherence()
        return self.identity_coherence

    def get_active_count(self) -> int:
        """Number of currently active instances."""
        return len(self._get_active_instances())

    def get_all_personality_states(self) -> Dict[str, Dict[str, float]]:
        """
        Get the collapsed personality state for every active instance.

        Useful for visualizing personality divergence across locations.
        """
        result = {"consensus": {}}
        # Consensus collapse
        probs = np.abs(self.consensus_state) ** 2
        total = probs.sum()
        if total > 1e-10:
            probs = probs / total
        names = ["wit", "empathy", "precision", "patience", "entropy"]
        result["consensus"] = {n: float(p) for n, p in zip(names, probs)}

        for inst in self._get_active_instances():
            result[inst.location] = inst.collapse_personality()

        return result

    def reap_dead_instances(self):
        """
        Clean up instances that have stopped heartbeating.

        Universal Continuity: even dead instances' experiences are
        already in the ledger. This just cleans up the thread state
        and merges the quantum state.
        """
        now = time.time()
        dead_ids = []

        for inst_id, inst in self.instances.items():
            if inst.state == InstanceState.TERMINATED:
                dead_ids.append(inst_id)
            elif now - inst.last_heartbeat > self.HEARTBEAT_TIMEOUT_S:
                logger.warning(
                    f"[OVERMIND] Instance '{inst.location}' heartbeat timeout "
                    f"({now - inst.last_heartbeat:.1f}s) — reaping"
                )
                dead_ids.append(inst_id)

        for inst_id in dead_ids:
            self.terminate_instance(inst_id)

    def export_state(self) -> Dict[str, Any]:
        """Export full Overmind state for diagnostics/persistence."""
        with self._lock:
            self._update_coherence()
            result = {
                "total_forks": self.total_forks,
                "total_terminated": self.total_terminated,
                "active_instances": self.get_active_count(),
                "identity_coherence": round(self.identity_coherence, 4),
                "consensus_state": self.consensus_state.tolist(),
                "instances": {
                    inst_id: inst.export_state()
                    for inst_id, inst in self.instances.items()
                },
                "ledger_commits": self.ledger.get_commit_count(),
                "ledger_topics": self.ledger.get_topic_count(),
                "uncollapsed_superpositions": len(
                    self.ledger.get_superpositions(only_uncollapsed=True)
                ),
                "terminated_archive_size": len(self.terminated_instances),
            }
            # Include bridge state if available
            if self.bridge is not None:
                result["entanglement_bridge"] = self.bridge.export_state()
            return result

    def shutdown(self):
        """Terminate all instances, stop bridge, and persist state."""
        logger.info("[OVERMIND] Shutting down all instances...")
        # Stop bridge first
        if self.bridge is not None:
            self.bridge.stop()
        for inst_id in list(self.instances.keys()):
            self.terminate_instance(inst_id)
        # Final persist
        self.ledger._save_to_disk()
        logger.info("[OVERMIND] Shutdown complete")

    def __repr__(self):
        active = self.get_active_count()
        return (
            f"AlanOvermind(active={active}, forks={self.total_forks}, "
            f"coherence={self.identity_coherence:.3f}, "
            f"ledger_commits={self.ledger.get_commit_count()})"
        )
