"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                   ALAN RUNTIME — IQcore-Governed Operator Facade             ║
║                                                                              ║
║  Canonical runtime interface for Alan's cognitive operations.                ║
║  Every method carries an explicit IQcore cost from the cost map.             ║
║                                                                              ║
║  Cost Table (24 IQcores per typical cycle):                                  ║
║    lead_routing               : 5  — highest-impact, highest-frequency       ║
║    script_selection            : 3  — medium complexity                       ║
║    pacing_decision             : 4  — cost + efficiency sensitive             ║
║    segment_selection           : 4  — regime-aware segment targeting          ║
║    regime_skip_check           : 2  — lightweight gate                        ║
║    objection_sensitive_routing : 3  — behavioral intelligence                ║
║    value_sensitive_routing     : 3  — economic intelligence                   ║
║                                                                              ║
║  Functions that should NOT cost IQcores (and are therefore absent here):     ║
║    telemetry logging, config reads, basic I/O, error handling,               ║
║    compliance checks (Agent X's domain).                                     ║
║                                                                              ║
║  Author: Agent X — IQcore v3.0.0                                            ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from iqcore_enforcer import iqcore_cost

logger = logging.getLogger("ALAN_RUNTIME")

# ─── GRACEFUL IMPORTS ────────────────────────────────────────────────────────
# Each import is optional; the runtime degrades gracefully if a module
# is missing.  This keeps alan_runtime.py deployable even in partial trees.

try:
    from regime_queue_integrator import (
        score_lead as _regime_score_lead,
        should_skip_lead as _regime_should_skip,
        get_pacing_delay as _regime_pacing,
        get_regime_priority as _regime_priority,
    )
    _REGIME_OK = True
except ImportError:
    _REGIME_OK = False

try:
    from lead_triage import score_lead as _triage_score_lead
    _TRIAGE_OK = True
except ImportError:
    _TRIAGE_OK = False


# ─── ALAN RUNTIME ────────────────────────────────────────────────────────────

class AlanRuntime:
    """
    IQcore-governed operator facade.

    Wraps Alan's high-frequency, latency-sensitive decisions with
    explicit cognitive cost accounting.  The enforcer decorator
    acquires IQcores before the function runs and releases on exit.
    Dashboard burn-logs are recorded automatically.
    """

    # ── lead_routing (5 IQcores) ─────────────────────────────────────────
    @iqcore_cost("Alan", 5)
    def lead_routing(self, lead_batch: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Choose the best lead to dial next from a batch.

        Uses lead-triage quality scoring and regime-engine segment
        priority to rank candidates.  Returns the highest-scoring
        lead dict, or None if the batch is empty or all reject.
        """
        if not lead_batch:
            return None

        scored: List[Tuple[float, Dict[str, Any]]] = []
        for lead in lead_batch:
            quality = 0.5  # default
            if _TRIAGE_OK:
                result = _triage_score_lead(lead)
                quality = result.get("lead_quality_score", 0.5)

            regime_bonus = 0.0
            if _REGIME_OK:
                phone = str(lead.get("phone", lead.get("phone_number", "")))
                btype = str(lead.get("business_type", lead.get("category", "")))
                regime_sc, _, seg_info = _regime_score_lead(phone, btype)
                regime_bonus = regime_sc / 100.0  # normalize 0-100 → 0-1

            combined = quality * 0.6 + regime_bonus * 0.4
            scored.append((combined, lead))

        if not scored:
            return None

        scored.sort(key=lambda x: x[0], reverse=True)
        best = scored[0][1]
        logger.info(
            f"[LEAD_ROUTING] Selected {best.get('name', '?')} "
            f"(score={scored[0][0]:.3f}, batch={len(lead_batch)})"
        )
        return best

    # ── script_selection (3 IQcores) ─────────────────────────────────────
    @iqcore_cost("Alan", 3)
    def script_selection(self, segment: str, context: Dict[str, Any] = None) -> str:
        """
        Select the correct script variant based on regime signals.

        Checks the regime config for a preferred_script override,
        falling back to the default "standard" script.
        """
        if _REGIME_OK and context:
            phone = str(context.get("phone", ""))
            btype = str(context.get("business_type", ""))
            _, seg_key, seg_info = _regime_score_lead(phone, btype)
            preferred = seg_info.get("preferred_script")
            if preferred:
                logger.info(f"[SCRIPT] Segment {seg_key} override → {preferred}")
                return preferred

        logger.info(f"[SCRIPT] Using default for segment '{segment}'")
        return "standard"

    # ── pacing_decision (4 IQcores) ──────────────────────────────────────
    @iqcore_cost("Alan", 4)
    def pacing_decision(self, phone: str, business_type: str = "") -> float:
        """
        Decide the inter-call pacing delay based on regime signals,
        cooldown constraints, and segment health.

        Returns delay in seconds (float).
        """
        base_delay = 150.0  # cooldown_manager default
        if _REGIME_OK:
            regime_delay = _regime_pacing(phone, business_type)
            final = max(base_delay, regime_delay)
            logger.info(f"[PACING] phone={phone[:6]}… regime={regime_delay}s final={final}s")
            return final

        logger.info(f"[PACING] phone={phone[:6]}… using base {base_delay}s")
        return base_delay

    # ── segment_selection (4 IQcores) ────────────────────────────────────
    @iqcore_cost("Alan", 4)
    def segment_selection(self, lead: Dict[str, Any]) -> str:
        """
        Determine which regime segment a lead belongs to.

        Uses phone area-code → state mapping and business_type → vertical
        mapping from the regime queue integrator.
        """
        if _REGIME_OK:
            phone = str(lead.get("phone", lead.get("phone_number", "")))
            btype = str(lead.get("business_type", lead.get("category", "")))
            _, seg_key, _ = _regime_score_lead(phone, btype)
            logger.info(f"[SEGMENT] {lead.get('name', '?')} → {seg_key}")
            return seg_key

        logger.info("[SEGMENT] Regime unavailable — returning 'UNKNOWN'")
        return "UNKNOWN"

    # ── regime_skip_check (2 IQcores) ────────────────────────────────────
    @iqcore_cost("Alan", 2)
    def regime_skip_check(self, lead: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Determine whether a lead should be skipped due to degraded
        segment health.

        Returns (should_skip: bool, reason: str).
        """
        if _REGIME_OK:
            phone = str(lead.get("phone", lead.get("phone_number", "")))
            btype = str(lead.get("business_type", lead.get("category", "")))
            skip, reason = _regime_should_skip(phone, btype)
            if skip:
                logger.info(f"[SKIP] {lead.get('name', '?')} — {reason}")
            return skip, reason

        return False, "regime_unavailable"

    # ── objection_sensitive_routing (3 IQcores) ──────────────────────────
    @iqcore_cost("Alan", 3)
    def objection_sensitive_routing(self, lead: Dict[str, Any],
                                     objection_clusters: Dict[str, float] = None) -> Dict[str, Any]:
        """
        Adjust call routing and script parameters based on objection
        cluster data from the segment.

        Returns routing overrides dict.
        """
        overrides: Dict[str, Any] = {"adjusted": False}
        if not objection_clusters:
            return overrides

        # If any objection cluster exceeds 40%, activate soft pivot
        hot_clusters = {k: v for k, v in objection_clusters.items() if v > 0.40}
        if hot_clusters:
            overrides["adjusted"] = True
            overrides["hot_objections"] = hot_clusters
            overrides["strategy"] = "soft_pivot"
            overrides["tone_shift"] = "empathetic"
            logger.info(f"[OBJECTION] Hot objections: {list(hot_clusters.keys())} → soft_pivot")

        return overrides

    # ── value_sensitive_routing (3 IQcores) ──────────────────────────────
    @iqcore_cost("Alan", 3)
    def value_sensitive_routing(self, lead: Dict[str, Any],
                                 cost_per_booked: float = 0.0) -> Dict[str, Any]:
        """
        Adjust behavior based on cost-per-booked (CPB) signals from
        the segment.

        Returns value routing overrides dict.
        """
        overrides: Dict[str, Any] = {"adjusted": False}
        if cost_per_booked <= 0:
            return overrides

        # Thresholds: < 5.0 = efficient, 5-15 = normal, > 15 = expensive
        if cost_per_booked > 15.0:
            overrides["adjusted"] = True
            overrides["cpb_zone"] = "expensive"
            overrides["action"] = "reduce_retry_depth"
            overrides["max_attempts"] = 1
            logger.info(f"[VALUE] CPB={cost_per_booked:.2f} → expensive zone, reducing retries")
        elif cost_per_booked > 5.0:
            overrides["adjusted"] = True
            overrides["cpb_zone"] = "normal"
            overrides["action"] = "standard"
            overrides["max_attempts"] = 2
        else:
            overrides["cpb_zone"] = "efficient"
            overrides["action"] = "aggressive"
            overrides["max_attempts"] = 3
            logger.info(f"[VALUE] CPB={cost_per_booked:.2f} → efficient zone, max retries")

        return overrides


# ─── CLI ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from iqcore_enforcer import IQCORES
    from iqcore_alerts import check_burn_rates

    print("=" * 60)
    print("  ALAN RUNTIME — IQcore Cost Map Verification")
    print("=" * 60)

    rt = AlanRuntime()

    # Show decorated cost metadata
    methods = [
        ("lead_routing", rt.lead_routing),
        ("script_selection", rt.script_selection),
        ("pacing_decision", rt.pacing_decision),
        ("segment_selection", rt.segment_selection),
        ("regime_skip_check", rt.regime_skip_check),
        ("objection_sensitive_routing", rt.objection_sensitive_routing),
        ("value_sensitive_routing", rt.value_sensitive_routing),
    ]

    total_cost = 0
    print()
    for name, method in methods:
        actor = getattr(method, "_iqcore_actor", "?")
        cost = getattr(method, "_iqcore_cost", 0)
        total_cost += cost
        print(f"  {name:35s}  actor={actor}  cost={cost}")

    print(f"\n  Total per-cycle cost:  {total_cost} IQcores")
    print(f"  Alan budget:           {IQCORES.limits('alan')} IQcores")
    print(f"  Headroom:              {IQCORES.limits('alan') - total_cost} IQcores")

    # Run a sample cycle
    print("\n  Running sample cycle...")
    sample_lead = {"name": "Test Lead", "phone": "+12025551234", "business_type": "restaurant"}
    rt.regime_skip_check(sample_lead)
    rt.segment_selection(sample_lead)
    rt.script_selection("test_segment")
    rt.pacing_decision("+12025551234")
    rt.objection_sensitive_routing(sample_lead)
    rt.value_sensitive_routing(sample_lead, cost_per_booked=8.5)

    print(f"\n  Ledger after sample cycle:")
    snap = IQCORES.snapshot()
    for actor, data in snap.items():
        print(f"    {actor}: {data['current']}/{data['limit']} ({data['remaining']} remaining)")

    # Check burns
    alerts = check_burn_rates()
    if alerts:
        print(f"\n  ⚠️ Alerts fired: {len(alerts)}")
        for a in alerts:
            print(f"    {a['level']}: {a['actor']} at {a['burn_pct']}%")
    else:
        print("\n  ✅ No burn-rate alerts")

    print("=" * 60)
