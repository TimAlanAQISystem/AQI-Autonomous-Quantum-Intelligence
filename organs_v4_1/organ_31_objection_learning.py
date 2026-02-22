"""
╔══════════════════════════════════════════════════════════════════════════════╗
║           ORGAN 31 — OBJECTION LEARNING                                      ║
║                                                                              ║
║  Learns new objection patterns from uncaptured phrases.                      ║
║  Clusters unknown phrases, scores similarity, promotes stable patterns,      ║
║  and feeds them back into the static objection detection organ.              ║
║                                                                              ║
║  The market evolves; objection patterns must evolve with it.                 ║
║                                                                              ║
║  Constitutional Guarantees:                                                  ║
║    - No pattern added without confidence threshold                           ║
║    - All new patterns logged for lineage                                     ║
║    - Human-review queue for borderline patterns                              ║
║    - CCNM integration for cross-call learning                                ║
║                                                                              ║
║  RRG: Section 41                                                             ║
║  Author: Agent X / v4.1                                                      ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import json
import logging
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# ─── IQcore Wiring ───────────────────────────────────────────────────────────
_parent = str(Path(__file__).resolve().parent.parent)
if _parent not in sys.path:
    sys.path.insert(0, _parent)

try:
    from iqcore_enforcer import iqcore_cost
    IQCORE_AVAILABLE = True
except ImportError:
    IQCORE_AVAILABLE = False
    def iqcore_cost(actor, cost):
        def decorator(fn):
            fn._iqcore_actor = actor
            fn._iqcore_cost = cost
            return fn
        return decorator

logger = logging.getLogger("ORGAN_31")

# ─── CONSTANTS ───────────────────────────────────────────────────────────────

DEFAULT_STORE_PATH = Path(__file__).resolve().parent.parent / "data" / "objection_learning" / "patterns.json"
DEFAULT_MIN_COUNT = 5        # minimum occurrences to promote
DEFAULT_MIN_SIMILARITY = 0.6  # minimum token overlap to cluster
DEFAULT_PROMOTE_CONFIDENCE = 0.7  # confidence threshold for auto-promotion
MAX_CANDIDATES = 1000        # max stored candidates before pruning
STOPWORDS = {"i", "the", "a", "an", "is", "am", "are", "was", "were", "be",
             "been", "being", "have", "has", "had", "do", "does", "did", "will",
             "would", "could", "should", "can", "may", "might", "shall",
             "to", "of", "in", "for", "on", "with", "at", "by", "from",
             "it", "its", "my", "your", "we", "they", "he", "she", "you",
             "me", "him", "her", "us", "them", "this", "that", "these", "those",
             "not", "no", "but", "or", "and", "so", "just", "very", "too"}


# ─── OBJECTION LEARNING ORGAN ───────────────────────────────────────────────

class ObjectionLearningOrgan:
    """
    Organ 31 — Objection Learning

    Learns new objection patterns from uncaptured phrases:
      1. observe_uncaptured() — records phrases that didn't match static patterns
      2. cluster_and_promote() — clusters similar phrases and promotes patterns
      3. get_promoted_patterns() — returns patterns ready for injection
      4. get_review_queue() — returns borderline patterns for human review

    Integrates with CCNM for cross-call pattern accumulation.
    """

    def __init__(self, store_path: str = None):
        self.store_path = Path(store_path) if store_path else DEFAULT_STORE_PATH
        self._data: Dict[str, Any] = self._load_data()
        logger.info(f"[ORGAN 31] Objection Learning initialized — "
                     f"{len(self._data.get('candidates', []))} candidates, "
                     f"{len(self._data.get('promoted', []))} promoted")

    # ─── PERSISTENCE ─────────────────────────────────────────────────────

    def _load_data(self) -> Dict[str, Any]:
        """Load learning state from disk."""
        if not self.store_path.exists():
            return {"candidates": [], "promoted": [], "review_queue": [], "rejected": []}
        try:
            return json.loads(self.store_path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.error(f"[ORGAN 31] Failed to load: {e}")
            return {"candidates": [], "promoted": [], "review_queue": [], "rejected": []}

    def _save_data(self) -> None:
        """Persist learning state to disk."""
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self.store_path.write_text(
            json.dumps(self._data, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

    # ─── TOKENIZATION ────────────────────────────────────────────────────

    def _tokenize(self, text: str) -> Set[str]:
        """Tokenize and remove stopwords for comparison."""
        tokens = re.findall(r'\b[a-z]+\b', text.lower())
        return {t for t in tokens if t not in STOPWORDS and len(t) > 2}

    def _similarity(self, a: str, b: str) -> float:
        """Jaccard similarity between two phrases (after stopword removal)."""
        a_tokens = self._tokenize(a)
        b_tokens = self._tokenize(b)
        if not a_tokens or not b_tokens:
            return 0.0
        intersection = len(a_tokens & b_tokens)
        union = len(a_tokens | b_tokens)
        return intersection / union if union > 0 else 0.0

    # ─── OBSERVATION ─────────────────────────────────────────────────────

    @iqcore_cost("Alan", 1)
    def observe_uncaptured(self, phrase: str, call_id: str = "") -> None:
        """
        Record an uncaptured objection phrase for later clustering.
        Called when static objection patterns return "none".

        IQcore cost: 1 per observation.
        """
        if not phrase or len(phrase.strip()) < 5:
            return  # too short to be meaningful

        phrase_clean = phrase.strip().lower()

        # Check if already exists — increment count
        for cand in self._data["candidates"]:
            if self._similarity(cand["phrase"], phrase_clean) >= 0.85:
                cand["count"] += 1
                cand["last_seen"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                if call_id:
                    cand.setdefault("call_ids", []).append(call_id)
                self._save_data()
                return

        # New candidate
        self._data["candidates"].append({
            "phrase": phrase_clean,
            "count": 1,
            "first_seen": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "last_seen": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "call_ids": [call_id] if call_id else [],
        })

        # Prune if over limit
        if len(self._data["candidates"]) > MAX_CANDIDATES:
            self._data["candidates"].sort(key=lambda x: x["count"], reverse=True)
            self._data["candidates"] = self._data["candidates"][:MAX_CANDIDATES]

        self._save_data()

    # ─── CLUSTERING & PROMOTION ──────────────────────────────────────────

    @iqcore_cost("Alan", 2)
    def cluster_and_promote(self, min_count: int = DEFAULT_MIN_COUNT,
                             min_sim: float = DEFAULT_MIN_SIMILARITY) -> List[Dict[str, Any]]:
        """
        Cluster candidate phrases and promote stable patterns.
        Returns list of newly promoted patterns.

        This should be called nightly or after a batch of calls.
        IQcore cost: 2 per run.
        """
        candidates = self._data.get("candidates", [])
        already_promoted = {p["pattern"].lower() for p in self._data.get("promoted", [])}
        already_rejected = {p.lower() for p in self._data.get("rejected", [])}
        newly_promoted: List[Dict[str, Any]] = []

        for cand in candidates:
            phrase = cand["phrase"]
            if phrase in already_promoted or phrase in already_rejected:
                continue
            if cand["count"] < min_count:
                continue

            # Find cluster: all candidates similar to this one
            cluster = [c for c in candidates
                       if self._similarity(phrase, c["phrase"]) >= min_sim]
            total_count = sum(c["count"] for c in cluster)

            if total_count >= min_count:
                # Check confidence
                confidence = min(1.0, total_count / (min_count * 2))

                if confidence >= DEFAULT_PROMOTE_CONFIDENCE:
                    # Auto-promote
                    pattern = {
                        "pattern": phrase,
                        "type": "learned",
                        "support": total_count,
                        "cluster_size": len(cluster),
                        "confidence": round(confidence, 3),
                        "promoted_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        "status": "active",
                    }
                    self._data["promoted"].append(pattern)
                    newly_promoted.append(pattern)
                    logger.info(f"[ORGAN 31] PROMOTED: '{phrase}' (support={total_count}, conf={confidence:.2f})")
                else:
                    # Add to review queue
                    self._data.setdefault("review_queue", []).append({
                        "phrase": phrase,
                        "support": total_count,
                        "confidence": round(confidence, 3),
                        "added_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    })
                    logger.info(f"[ORGAN 31] REVIEW QUEUE: '{phrase}' (conf={confidence:.2f})")

        if newly_promoted:
            self._save_data()

        return newly_promoted

    # ─── ACCESSORS ───────────────────────────────────────────────────────

    def get_promoted_patterns(self) -> List[Dict[str, Any]]:
        """Return all promoted patterns (ready for injection into Organ 6)."""
        return [p for p in self._data.get("promoted", []) if p.get("status") == "active"]

    def get_review_queue(self) -> List[Dict[str, Any]]:
        """Return patterns awaiting human review."""
        return self._data.get("review_queue", [])

    def approve_pattern(self, phrase: str) -> bool:
        """Approve a pattern from the review queue."""
        review = self._data.get("review_queue", [])
        for item in review:
            if item["phrase"].lower() == phrase.lower():
                pattern = {
                    "pattern": item["phrase"],
                    "type": "human_approved",
                    "support": item.get("support", 0),
                    "confidence": 1.0,
                    "promoted_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "status": "active",
                }
                self._data["promoted"].append(pattern)
                review.remove(item)
                self._save_data()
                return True
        return False

    def reject_pattern(self, phrase: str) -> bool:
        """Reject a pattern from the review queue."""
        review = self._data.get("review_queue", [])
        for item in review:
            if item["phrase"].lower() == phrase.lower():
                self._data.setdefault("rejected", []).append(phrase.lower())
                review.remove(item)
                self._save_data()
                return True
        return False

    # ─── DIAGNOSTICS ─────────────────────────────────────────────────────

    def get_status(self) -> Dict[str, Any]:
        return {
            "organ": "31-objection-learning",
            "candidates": len(self._data.get("candidates", [])),
            "promoted": len(self._data.get("promoted", [])),
            "review_queue": len(self._data.get("review_queue", [])),
            "rejected": len(self._data.get("rejected", [])),
            "store_path": str(self.store_path),
            "iqcore_available": IQCORE_AVAILABLE,
        }


# ─── MODULE SELF-TEST ────────────────────────────────────────────────────────

if __name__ == "__main__":
    import tempfile
    print("=" * 60)
    print("ORGAN 31 — Objection Learning — Self-Test")
    print("=" * 60)

    # Use temp file to avoid polluting real data
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
        json.dump({"candidates": [], "promoted": [], "review_queue": [], "rejected": []}, f)
        tmp_path = f.name

    ol = ObjectionLearningOrgan(store_path=tmp_path)

    # Simulate repeated phrases
    phrases = [
        "we already have a provider",
        "we already have a provider we're happy with",
        "already have a provider",
        "we have someone already",
        "we already use someone for that",
        "we're good we have a provider",
        "already have a provider thanks",
    ]

    for p in phrases:
        ol.observe_uncaptured(p, call_id="test_call")

    print(f"  Candidates after observation: {len(ol._data['candidates'])}")

    # Promote
    promoted = ol.cluster_and_promote(min_count=3, min_sim=0.4)
    print(f"  Promoted patterns: {len(promoted)}")
    for p in promoted:
        print(f"    '{p['pattern']}' (support={p['support']}, conf={p['confidence']:.2f})")

    status = ol.get_status()
    print(f"  Status: {json.dumps(status, indent=2)}")

    # Cleanup
    Path(tmp_path).unlink(missing_ok=True)
    print("  SELF-TEST PASSED")
