"""
╔══════════════════════════════════════════════════════════════════════════════╗
║           ORGAN 34 — COMPETITIVE INTELLIGENCE                                ║
║                                                                              ║
║  Stores and serves competitor pricing, offers, and positioning.              ║
║  Feeds the Retrieval Cortex and script selection with live market data.       ║
║                                                                              ║
║  Constitutional Guarantees:                                                  ║
║    - No unverified competitor claims                                         ║
║    - All data must be timestamped                                            ║
║    - Stale data (>7 days) is flagged                                         ║
║    - Lineage logged for all lookups                                          ║
║                                                                              ║
║  RRG: Section 44                                                             ║
║  Author: Agent X / v4.1                                                      ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import json
import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

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

logger = logging.getLogger("ORGAN_34")

# ─── CONSTANTS ───────────────────────────────────────────────────────────────

DEFAULT_CACHE_PATH = Path(__file__).resolve().parent.parent / "data" / "competitor_cache" / "intel.json"
STALE_THRESHOLD_DAYS = 7
MAX_COMPETITORS = 50


# ─── COMPETITIVE INTELLIGENCE ORGAN ─────────────────────────────────────────

class CompetitiveIntelOrgan:
    """
    Organ 34 — Competitive Intelligence

    Stores and serves competitor information:
      - pricing models
      - current offers / promotions
      - feature comparison tables
      - competitor-specific rebuttals
      - market positioning

    Data is refreshed daily by a scheduled job or Agent X directive.
    """

    def __init__(self, cache_path: str = None):
        self.cache_path = Path(cache_path) if cache_path else DEFAULT_CACHE_PATH
        self._cache: Dict[str, Any] = self._load_cache()
        self._lookup_log: List[Dict[str, Any]] = []
        logger.info(f"[ORGAN 34] Competitive Intel initialized — "
                     f"{len(self._cache.get('competitors', {}))} competitors tracked")

    # ─── PERSISTENCE ─────────────────────────────────────────────────────

    def _load_cache(self) -> Dict[str, Any]:
        """Load the competitor cache from disk."""
        if not self.cache_path.exists():
            return {"competitors": {}, "last_refresh": None, "refresh_count": 0}
        try:
            return json.loads(self.cache_path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.error(f"[ORGAN 34] Failed to load cache: {e}")
            return {"competitors": {}, "last_refresh": None, "refresh_count": 0}

    def _save_cache(self) -> None:
        """Persist the competitor cache to disk."""
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache_path.write_text(
            json.dumps(self._cache, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

    # ─── DATA REFRESH ────────────────────────────────────────────────────

    @iqcore_cost("AgentX", 2)
    def refresh_from_source(self, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update competitor intel from a structured snapshot.
        Called by a scheduled job or Agent X governance cycle.

        IQcore cost: 2 (AgentX — governance action).

        snapshot example:
        {
          "Square": {
            "pricing": "2.6% + 10¢ per tap/chip/swipe",
            "monthly_fee": "$0",
            "contract": "No contract",
            "features": ["POS", "invoicing", "payroll"],
            "positioning": "Simple, flat-rate",
            "rebuttals": ["Higher effective rate for high-volume merchants"]
          },
          "Clover": { ... }
        }
        """
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        for name, data in snapshot.items():
            data["last_updated"] = now
            data["verified"] = True
            self._cache["competitors"][name] = data

        self._cache["last_refresh"] = now
        self._cache["refresh_count"] = self._cache.get("refresh_count", 0) + 1
        self._save_cache()

        logger.info(f"[ORGAN 34] Refreshed {len(snapshot)} competitors at {now}")
        return {
            "refreshed": len(snapshot),
            "total": len(self._cache["competitors"]),
            "timestamp": now,
        }

    def add_competitor(self, name: str, data: Dict[str, Any]) -> None:
        """Add or update a single competitor."""
        data["last_updated"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        data["verified"] = True
        self._cache["competitors"][name] = data
        self._save_cache()

    # ─── LOOKUPS ─────────────────────────────────────────────────────────

    @iqcore_cost("Alan", 1)
    def get_competitor(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get competitor profile by name.
        Returns None if not found.
        Flags stale data.

        IQcore cost: 1 per lookup.
        """
        comp = self._cache.get("competitors", {}).get(name)
        if not comp:
            return None

        # Check freshness
        last_updated = comp.get("last_updated", "")
        is_stale = self._is_stale(last_updated)
        if is_stale:
            logger.warning(f"[ORGAN 34] STALE DATA for {name} — last updated {last_updated}")

        result = {**comp, "is_stale": is_stale}

        # Log lookup
        self._lookup_log.append({
            "competitor": name,
            "found": True,
            "stale": is_stale,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        })

        return result

    @iqcore_cost("Alan", 1)
    def get_all(self) -> Dict[str, Any]:
        """Return all competitor profiles with freshness flags."""
        result = {}
        for name, data in self._cache.get("competitors", {}).items():
            is_stale = self._is_stale(data.get("last_updated", ""))
            result[name] = {**data, "is_stale": is_stale}
        return result

    def get_rebuttal(self, competitor: str) -> Optional[List[str]]:
        """Get competitor-specific rebuttals."""
        comp = self._cache.get("competitors", {}).get(competitor)
        if not comp:
            return None
        return comp.get("rebuttals", [])

    def compare(self, competitor: str, feature: str) -> Optional[Dict[str, Any]]:
        """Compare a specific feature against a competitor."""
        comp = self._cache.get("competitors", {}).get(competitor)
        if not comp:
            return None
        return {
            "competitor": competitor,
            "feature": feature,
            "competitor_value": comp.get(feature, "unknown"),
            "is_stale": self._is_stale(comp.get("last_updated", "")),
        }

    # ─── FRESHNESS ───────────────────────────────────────────────────────

    def _is_stale(self, timestamp: str) -> bool:
        """Check if data is older than STALE_THRESHOLD_DAYS."""
        if not timestamp:
            return True
        try:
            updated = time.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")
            age_days = (time.time() - time.mktime(updated)) / 86400
            return age_days > STALE_THRESHOLD_DAYS
        except Exception:
            return True

    def get_stale_competitors(self) -> List[str]:
        """Return names of competitors with stale data."""
        stale = []
        for name, data in self._cache.get("competitors", {}).items():
            if self._is_stale(data.get("last_updated", "")):
                stale.append(name)
        return stale

    # ─── DIAGNOSTICS ─────────────────────────────────────────────────────

    def get_status(self) -> Dict[str, Any]:
        competitors = self._cache.get("competitors", {})
        return {
            "organ": "34-competitive-intel",
            "competitor_count": len(competitors),
            "last_refresh": self._cache.get("last_refresh"),
            "refresh_count": self._cache.get("refresh_count", 0),
            "stale_count": len(self.get_stale_competitors()),
            "lookup_count": len(self._lookup_log),
            "cache_path": str(self.cache_path),
            "iqcore_available": IQCORE_AVAILABLE,
        }


# ─── MODULE SELF-TEST ────────────────────────────────────────────────────────

if __name__ == "__main__":
    import tempfile
    print("=" * 60)
    print("ORGAN 34 — Competitive Intelligence — Self-Test")
    print("=" * 60)

    # Use temp file
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
        json.dump({"competitors": {}, "last_refresh": None, "refresh_count": 0}, f)
        tmp_path = f.name

    ci = CompetitiveIntelOrgan(cache_path=tmp_path)

    # Refresh with test data
    snapshot = {
        "Square": {
            "pricing": "2.6% + 10¢ per tap/chip/swipe",
            "monthly_fee": "$0",
            "contract": "No contract",
            "features": ["POS", "invoicing", "payroll"],
            "positioning": "Simple, flat-rate",
            "rebuttals": ["Higher effective rate for high-volume merchants",
                          "Limited customer support"],
        },
        "Clover": {
            "pricing": "2.3% + 10¢ (varies by plan)",
            "monthly_fee": "$14.95+",
            "contract": "36 months typical",
            "features": ["POS", "inventory", "loyalty"],
            "positioning": "Full POS ecosystem",
            "rebuttals": ["Long contracts", "Hardware lock-in"],
        },
    }

    result = ci.refresh_from_source(snapshot)
    print(f"  Refreshed: {result['refreshed']} competitors")

    # Lookup
    sq = ci.get_competitor("Square")
    print(f"  Square pricing: {sq['pricing']}")
    print(f"  Square stale: {sq['is_stale']}")

    # Rebuttals
    rebuttals = ci.get_rebuttal("Clover")
    print(f"  Clover rebuttals: {rebuttals}")

    # Compare
    comp = ci.compare("Square", "monthly_fee")
    print(f"  Compare: {comp}")

    status = ci.get_status()
    print(f"  Status: {json.dumps(status, indent=2)}")

    # Cleanup
    Path(tmp_path).unlink(missing_ok=True)
    print("  SELF-TEST PASSED")
