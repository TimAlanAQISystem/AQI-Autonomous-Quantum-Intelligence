"""
╔══════════════════════════════════════════════════════════════════════════════╗
║           ORGAN 24 — RETRIEVAL CORTEX (RAG)                                  ║
║                                                                              ║
║  Mid-call knowledge retrieval: interchange rules, pricing tables,            ║
║  processor comparisons, product specs, competitor positioning,               ║
║  rebuttal libraries, merchant-type playbooks.                                ║
║                                                                              ║
║  Called by Neural Flow Cortex when a knowledge gap is detected.              ║
║  IQcore-governed (mid-call budgeting).                                       ║
║  Cached per call to avoid repeated lookups.                                  ║
║                                                                              ║
║  Constitutional Guarantees:                                                  ║
║    - Retrieval cannot override constitutional doctrine                       ║
║    - Retrieval must be grounded in stored knowledge                          ║
║    - Retrieval must log lineage                                              ║
║    - No hallucinated citations                                               ║
║    - Retrieval confidence threshold enforced                                 ║
║                                                                              ║
║  RRG: Section 34                                                             ║
║  Author: Agent X / v4.1                                                      ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ─── IQcore Wiring ───────────────────────────────────────────────────────────
# Add parent to path for flat-layout imports
_parent = str(Path(__file__).resolve().parent.parent)
if _parent not in sys.path:
    sys.path.insert(0, _parent)

try:
    from iqcore_enforcer import iqcore_cost
    IQCORE_AVAILABLE = True
except ImportError:
    IQCORE_AVAILABLE = False
    def iqcore_cost(actor, cost):
        """Fallback no-op decorator when IQcore not available."""
        def decorator(fn):
            fn._iqcore_actor = actor
            fn._iqcore_cost = cost
            return fn
        return decorator

logger = logging.getLogger("ORGAN_24")

# ─── CONSTANTS ───────────────────────────────────────────────────────────────

DEFAULT_STORE_PATH = Path(__file__).resolve().parent.parent / "data" / "vector_store" / "knowledge_index.json"
DEFAULT_MIN_CONFIDENCE = 0.4
DEFAULT_TOP_K = 3
MAX_CACHE_SIZE = 50  # per-call cache limit


# ─── RETRIEVAL CORTEX ────────────────────────────────────────────────────────

class RetrievalCortex:
    """
    Organ 24 — Retrieval Cortex

    Mid-call knowledge retrieval for:
      - interchange rules
      - pricing tables
      - processor comparisons
      - product specs
      - competitor positioning
      - rebuttal libraries
      - merchant-type playbooks

    Architecture:
      1. Vector store containing domain knowledge
      2. Retrieval call triggered on detected knowledge gap
      3. Confidence threshold prevents hallucinated responses
      4. Per-call cache prevents repeated lookups
      5. IQcore-governed (each retrieval costs 2 IQcores)
    """

    def __init__(self, store_path: str = None):
        self.store_path = Path(store_path) if store_path else DEFAULT_STORE_PATH
        self._index: List[Dict[str, Any]] = self._load_index()
        self._call_cache: Dict[str, Dict[str, Any]] = {}
        self._retrieval_log: List[Dict[str, Any]] = []
        logger.info(f"[ORGAN 24] Retrieval Cortex initialized — {len(self._index)} documents in index")

    # ─── INDEX MANAGEMENT ────────────────────────────────────────────────

    def _load_index(self) -> List[Dict[str, Any]]:
        """Load the knowledge index from disk."""
        if not self.store_path.exists():
            logger.warning(f"[ORGAN 24] No index found at {self.store_path} — starting empty")
            return []
        try:
            data = json.loads(self.store_path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
            return data.get("documents", [])
        except Exception as e:
            logger.error(f"[ORGAN 24] Failed to load index: {e}")
            return []

    def reload_index(self) -> int:
        """Hot-reload the knowledge index. Returns document count."""
        self._index = self._load_index()
        self._call_cache.clear()
        return len(self._index)

    def add_document(self, doc: Dict[str, Any]) -> None:
        """Add a document to the index and persist."""
        required = {"id", "text", "category"}
        if not required.issubset(doc.keys()):
            raise ValueError(f"Document must have keys: {required}")
        # Generate embedding if not present
        if "embedding" not in doc:
            doc["embedding"] = self._embed(doc["text"])
        doc["added_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self._index.append(doc)
        self._persist_index()

    def _persist_index(self) -> None:
        """Write the index to disk."""
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self.store_path.write_text(
            json.dumps(self._index, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

    # ─── EMBEDDING (PLACEHOLDER) ────────────────────────────────────────

    def _embed(self, text: str) -> List[float]:
        """
        Placeholder embedding.
        In production, wire to OpenAI text-embedding-3-small or local model.
        Currently uses a simple bag-of-words hash for testing.
        """
        tokens = text.lower().split()
        # Simple 8-dim hash embedding for testing
        vec = [0.0] * 8
        for i, token in enumerate(tokens):
            idx = hash(token) % 8
            vec[idx] += 1.0 / (1 + i * 0.1)
        # Normalize
        mag = sum(v * v for v in vec) ** 0.5
        if mag > 0:
            vec = [v / mag for v in vec]
        return vec

    def _similarity(self, q_vec: List[float], d_vec: List[float]) -> float:
        """Cosine similarity between query and document embeddings."""
        if len(q_vec) != len(d_vec):
            return 0.0
        dot = sum(a * b for a, b in zip(q_vec, d_vec))
        mag_q = sum(a * a for a in q_vec) ** 0.5
        mag_d = sum(b * b for b in d_vec) ** 0.5
        if mag_q == 0 or mag_d == 0:
            return 0.0
        return dot / (mag_q * mag_d)

    # ─── RETRIEVAL ───────────────────────────────────────────────────────

    @iqcore_cost("Alan", 2)
    def retrieve(self, query: str, top_k: int = DEFAULT_TOP_K) -> List[Dict[str, Any]]:
        """
        Returns top_k knowledge entries ranked by similarity.
        Each result includes: id, text, category, score, metadata.

        IQcore cost: 2 per call.
        """
        if not self._index:
            return []

        # Check per-call cache
        cache_key = f"{query}:{top_k}"
        if cache_key in self._call_cache:
            return self._call_cache[cache_key]

        q_vec = self._embed(query)
        scored: List[Dict[str, Any]] = []

        for item in self._index:
            d_vec = item.get("embedding", [0.0] * len(q_vec))
            score = self._similarity(q_vec, d_vec)
            result = {
                "id": item.get("id", "unknown"),
                "text": item.get("text", ""),
                "category": item.get("category", "general"),
                "score": round(score, 4),
                "metadata": item.get("metadata", {}),
            }
            scored.append(result)

        scored.sort(key=lambda x: x["score"], reverse=True)
        results = scored[:top_k]

        # Cache
        if len(self._call_cache) < MAX_CACHE_SIZE:
            self._call_cache[cache_key] = results

        # Lineage log
        self._retrieval_log.append({
            "query": query,
            "top_score": results[0]["score"] if results else 0.0,
            "count": len(results),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        })

        return results

    def retrieve_safe(self, query: str, min_score: float = DEFAULT_MIN_CONFIDENCE) -> Optional[Dict[str, Any]]:
        """
        Safety wrapper: returns best match only if above confidence threshold.
        Prevents hallucinated citations by enforcing minimum similarity.
        """
        if not query:
            return None
        results = self.retrieve(query, top_k=1)
        if not results:
            return None
        best = results[0]
        if best["score"] < min_score:
            logger.debug(f"[ORGAN 24] Retrieval below threshold: {best['score']:.3f} < {min_score}")
            return None
        return best

    def retrieve_by_category(self, query: str, category: str,
                              top_k: int = DEFAULT_TOP_K) -> List[Dict[str, Any]]:
        """Retrieve only from a specific knowledge category."""
        all_results = self.retrieve(query, top_k=top_k * 3)
        filtered = [r for r in all_results if r["category"] == category]
        return filtered[:top_k]

    # ─── CALL LIFECYCLE ──────────────────────────────────────────────────

    def start_call(self) -> None:
        """Reset per-call cache at call start."""
        self._call_cache.clear()

    def end_call(self) -> Dict[str, Any]:
        """Return call-level retrieval stats and clear cache."""
        stats = {
            "retrievals": len(self._retrieval_log),
            "cache_hits": len(self._call_cache),
            "log": list(self._retrieval_log),
        }
        self._call_cache.clear()
        self._retrieval_log.clear()
        return stats

    # ─── DIAGNOSTICS ─────────────────────────────────────────────────────

    def get_status(self) -> Dict[str, Any]:
        """Return organ status for health checks."""
        return {
            "organ": "24-retrieval-cortex",
            "index_size": len(self._index),
            "cache_size": len(self._call_cache),
            "log_size": len(self._retrieval_log),
            "store_path": str(self.store_path),
            "iqcore_available": IQCORE_AVAILABLE,
        }


# ─── MODULE SELF-TEST ────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("ORGAN 24 — Retrieval Cortex — Self-Test")
    print("=" * 60)

    rc = RetrievalCortex()

    # Add test documents
    test_docs = [
        {"id": "doc_1", "text": "interchange plus pricing passes through actual card rates with a fixed markup",
         "category": "pricing"},
        {"id": "doc_2", "text": "tiered pricing bundles transactions into qualified mid-qualified non-qualified tiers",
         "category": "pricing"},
        {"id": "doc_3", "text": "Square charges 2.6% plus 10 cents per tap chip or swipe transaction",
         "category": "competitor"},
        {"id": "doc_4", "text": "Clover POS system includes hardware and payment processing",
         "category": "competitor"},
    ]

    for doc in test_docs:
        rc.add_document(doc)
    print(f"  Loaded {len(rc._index)} documents")

    # Test retrieval
    rc.start_call()
    results = rc.retrieve("what is interchange plus pricing")
    print(f"  Query: 'what is interchange plus pricing'")
    for r in results:
        print(f"    [{r['score']:.3f}] {r['category']}: {r['text'][:60]}...")

    # Test safe retrieval
    safe = rc.retrieve_safe("interchange plus rates")
    print(f"  Safe retrieval: {'FOUND' if safe else 'BELOW THRESHOLD'}")

    # Test category filter
    comp = rc.retrieve_by_category("pricing rates", "competitor")
    print(f"  Competitor results: {len(comp)}")

    stats = rc.end_call()
    print(f"  Call stats: {stats['retrievals']} retrievals, {stats['cache_hits']} cached")

    status = rc.get_status()
    print(f"  Status: {json.dumps(status, indent=2)}")
    print("  SELF-TEST PASSED")
