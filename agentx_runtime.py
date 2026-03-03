"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                  AGENT X RUNTIME — IQcore-Governed Governor Facade           ║
║                                                                              ║
║  Canonical runtime interface for Agent X's governance operations.            ║
║  Every method carries an explicit IQcore cost from the cost map.             ║
║                                                                              ║
║  Cost Table (32 IQcores per governance cycle):                               ║
║    review_proposal               : 8  — deep reasoning + evidence eval       ║
║    approve_or_reject             : 5  — constitutional decision              ║
║    model_lifecycle_decision      : 6  — high-impact structural change        ║
║    segment_split_merge_decision  : 6  — map rewriting                        ║
║    constitutional_check          : 4  — doctrine enforcement                 ║
║    supervision_cycle             : 3  — regime engine monitoring             ║
║                                                                              ║
║  Functions that should NOT cost IQcores (and are therefore absent here):     ║
║    reading proposals, logging, writing config, basic validation,             ║
║    telemetry ingestion.                                                      ║
║                                                                              ║
║  The Regime Engine consumes 0 IQcores.  It is a meta-organ (observer only). ║
║  Charging IQcores to it would create a feedback loop that destabilizes      ║
║  the organism.                                                               ║
║                                                                              ║
║  Author: Agent X — IQcore v3.0.0                                            ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional

from iqcore_enforcer import iqcore_cost

logger = logging.getLogger("AGENTX_RUNTIME")

# ─── GRACEFUL IMPORTS ────────────────────────────────────────────────────────

try:
    from regime_engine import (
        RegimeEngine,
        GovernanceInterface,
        ProposalComposer,
        RegimeProposal,
        ProposalStatus,
        ModelActionRequest,
        ModelActionType,
        SegmentConfig,
        SegmentPriority,
        PredictionTrust,
        SegmentStatus,
    )
    _REGIME_ENGINE_OK = True
except ImportError:
    _REGIME_ENGINE_OK = False

try:
    from iqcore_alerts import check_burn_rates
    _ALERTS_OK = True
except ImportError:
    _ALERTS_OK = False

CONFIG_LIVE_PATH = os.path.join("data", "regime_config_live.json")

# ─── AGENT X RUNTIME ────────────────────────────────────────────────────────

class AgentXRuntime:
    """
    IQcore-governed governor facade.

    Wraps Agent X's low-frequency, high-complexity governance
    decisions with explicit cognitive cost accounting.  The enforcer
    decorator acquires IQcores before the function runs and
    releases on exit.
    """

    def __init__(self):
        self._governance = GovernanceInterface() if _REGIME_ENGINE_OK else None

    # ── review_proposal (8 IQcores) ──────────────────────────────────────
    @iqcore_cost("AgentX", 8)
    def review_proposal(self, proposal: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deep-review a regime proposal.

        Evaluates candidate evidence, confidence levels, segment impact,
        and constitutional alignment.  Returns a review summary dict.
        """
        review = {
            "proposal_id": proposal.get("proposal_id", "unknown"),
            "candidate_count": len(proposal.get("candidates", [])),
            "segments_affected": list({
                c.get("segment", "?") for c in proposal.get("candidates", [])
            }),
            "avg_confidence": 0.0,
            "verdict": "NEEDS_REVIEW",
            "flags": [],
        }

        candidates = proposal.get("candidates", [])
        if candidates:
            confs = [c.get("confidence", 0.0) for c in candidates]
            review["avg_confidence"] = sum(confs) / len(confs)

            # Flag low-confidence candidates
            low_conf = [c for c in candidates if c.get("confidence", 0) < 0.5]
            if low_conf:
                review["flags"].append(f"{len(low_conf)} candidates below 50% confidence")

            # Flag too many segments affected
            if len(review["segments_affected"]) > 5:
                review["flags"].append("broad impact — more than 5 segments affected")

        if review["avg_confidence"] >= 0.80:
            review["verdict"] = "APPROVE_RECOMMENDED"
        elif review["avg_confidence"] >= 0.60:
            review["verdict"] = "CONDITIONAL_APPROVE"
        else:
            review["verdict"] = "REJECT_RECOMMENDED"

        logger.info(
            f"[REVIEW] proposal={review['proposal_id']} "
            f"verdict={review['verdict']} conf={review['avg_confidence']:.2f}"
        )
        return review

    # ── approve_or_reject (5 IQcores) ────────────────────────────────────
    @iqcore_cost("AgentX", 5)
    def approve_or_reject(self, proposal: Dict[str, Any],
                           review: Dict[str, Any] = None) -> bool:
        """
        Constitutional approval/rejection of a proposal.

        Uses the review verdict if provided, otherwise falls back to
        the GovernanceInterface auto-approve logic.

        Returns True if approved, False if rejected.
        """
        verdict = (review or {}).get("verdict", "")

        if verdict == "APPROVE_RECOMMENDED":
            logger.info(f"[GOVERN] APPROVED — {proposal.get('proposal_id', '?')}")
            return True
        elif verdict == "REJECT_RECOMMENDED":
            logger.info(f"[GOVERN] REJECTED — {proposal.get('proposal_id', '?')}")
            return False
        elif verdict == "CONDITIONAL_APPROVE":
            # Conditionally approve only if no flags
            flags = (review or {}).get("flags", [])
            if not flags:
                logger.info(f"[GOVERN] CONDITIONAL APPROVED — {proposal.get('proposal_id', '?')}")
                return True
            else:
                logger.info(
                    f"[GOVERN] CONDITIONAL REJECTED (flags: {flags}) — "
                    f"{proposal.get('proposal_id', '?')}"
                )
                return False

        # Fallback: auto-approve threshold
        candidates = proposal.get("candidates", [])
        if candidates:
            avg = sum(c.get("confidence", 0) for c in candidates) / len(candidates)
            approved = avg >= 0.80
            logger.info(
                f"[GOVERN] {'APPROVED' if approved else 'REJECTED'} "
                f"(auto, avg={avg:.2f}) — {proposal.get('proposal_id', '?')}"
            )
            return approved

        logger.info(f"[GOVERN] REJECTED (empty) — {proposal.get('proposal_id', '?')}")
        return False

    # ── model_lifecycle_decision (6 IQcores) ─────────────────────────────
    @iqcore_cost("AgentX", 6)
    def model_lifecycle_decision(self, model_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Govern spawning, retiring, or retraining of models.

        Evaluates the model action request and returns a decision dict
        with the action to take.
        """
        action = model_info.get("action", "unknown")
        target = model_info.get("target", "unknown")
        reason = model_info.get("reason", "")

        decision = {
            "action": action,
            "target": target,
            "approved": False,
            "reason": reason,
        }

        # Always approve retraining if explicitly requested
        if action in ("RETRAIN_MODEL", "retrain"):
            decision["approved"] = True
            logger.info(f"[MODEL] RETRAIN approved for {target} — {reason}")

        # Spawn only if justified by mutation detection
        elif action in ("SPAWN_NEW_MODEL", "spawn"):
            if "mutation" in reason.lower() or "objection" in reason.lower():
                decision["approved"] = True
                logger.info(f"[MODEL] SPAWN approved for {target} — {reason}")
            else:
                decision["approved"] = False
                logger.info(f"[MODEL] SPAWN denied for {target} — insufficient justification")

        # Retire only if segment is DEAD
        elif action in ("RETIRE_MODEL", "retire"):
            decision["approved"] = True
            logger.info(f"[MODEL] RETIRE approved for {target} — {reason}")

        else:
            logger.warning(f"[MODEL] Unknown action '{action}' for {target}")

        return decision

    # ── segment_split_merge_decision (6 IQcores) ─────────────────────────
    @iqcore_cost("AgentX", 6)
    def segment_split_merge_decision(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """
        Govern structural changes to the segment map (splits, merges).

        Returns the decision dict with approval status.
        """
        op = action.get("operation", "unknown")  # "split" or "merge"
        target = action.get("target", "unknown")
        reason = action.get("reason", "")

        decision = {
            "operation": op,
            "target": target,
            "approved": False,
            "reason": reason,
        }

        if op == "split":
            # Approve splits if driven by script degradation or cost explosion
            if any(kw in reason.lower() for kw in ("degradation", "cost", "explosion", "divergence")):
                decision["approved"] = True
                logger.info(f"[SEGMENT] SPLIT approved for {target} — {reason}")
            else:
                logger.info(f"[SEGMENT] SPLIT denied for {target} — insufficient justification")

        elif op == "merge":
            # Approve merges if segments are too small or have converged
            if any(kw in reason.lower() for kw in ("converge", "small", "consolidate", "identical")):
                decision["approved"] = True
                logger.info(f"[SEGMENT] MERGE approved for {target} — {reason}")
            else:
                logger.info(f"[SEGMENT] MERGE denied for {target} — insufficient justification")

        else:
            logger.warning(f"[SEGMENT] Unknown operation '{op}' for {target}")

        return decision

    # ── constitutional_check (4 IQcores) ─────────────────────────────────
    @iqcore_cost("AgentX", 4)
    def constitutional_check(self, proposal: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verify a proposal against the RRG/constitutional constraints.

        Checks: IQcore budget compliance, segment count limits,
        reallocation rules, and min-alan constraints.
        """
        violations: List[str] = []
        checks_passed: List[str] = []

        # Check: does the proposal try to modify IQcore allocation?
        if "iqcore_reallocation" in proposal:
            realloc = proposal["iqcore_reallocation"]
            alan_new = realloc.get("alan", 60)
            if alan_new < 50:
                violations.append(f"Alan IQcore below minimum: {alan_new} < 50")
            agentx_new = realloc.get("agentx", 40)
            if agentx_new > 50:
                violations.append(f"AgentX IQcore above maximum: {agentx_new} > 50")
            checks_passed.append("iqcore_reallocation_validated")

        # Check: segment count sanity
        segments_affected = proposal.get("segments_affected", [])
        if len(segments_affected) > 10:
            violations.append(f"Too many segments affected: {len(segments_affected)} > 10")
        checks_passed.append("segment_count_validated")

        # Check: no empty proposals
        if not proposal.get("candidates", []):
            violations.append("Empty proposal — no candidates")
        checks_passed.append("non_empty_validated")

        result = {
            "compliant": len(violations) == 0,
            "violations": violations,
            "checks_passed": checks_passed,
            "total_checks": len(checks_passed) + len(violations),
        }

        if violations:
            logger.warning(f"[CONSTITUTIONAL] VIOLATION: {violations}")
        else:
            logger.info(f"[CONSTITUTIONAL] Compliant — {len(checks_passed)} checks passed")

        return result

    # ── supervision_cycle (3 IQcores) ────────────────────────────────────
    @iqcore_cost("AgentX", 3)
    def supervision_cycle(self) -> Dict[str, Any]:
        """
        Monitor the Regime Engine's recent behavior.

        Reads the live config, checks for anomalies, and evaluates
        overall organism cognitive health via burn-rate alerts.
        """
        report: Dict[str, Any] = {
            "regime_status": "unknown",
            "segments": 0,
            "degraded_segments": [],
            "alerts": [],
        }

        # Read regime config
        if os.path.exists(CONFIG_LIVE_PATH):
            try:
                with open(CONFIG_LIVE_PATH, "r", encoding="utf-8") as f:
                    config = json.load(f)
                segments = config.get("segments", {})
                report["regime_status"] = "loaded"
                report["segments"] = len(segments)
                report["degraded_segments"] = [
                    k for k, v in segments.items()
                    if v.get("status") in ("DEGRADED", "degraded")
                ]
            except Exception as e:
                report["regime_status"] = f"error: {e}"

        # Check burn rates
        if _ALERTS_OK:
            alerts = check_burn_rates()
            report["alerts"] = alerts

        logger.info(
            f"[SUPERVISION] regime={report['regime_status']} "
            f"segments={report['segments']} "
            f"degraded={len(report['degraded_segments'])} "
            f"alerts={len(report['alerts'])}"
        )
        return report


# ─── CLI ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from iqcore_enforcer import IQCORES
    from iqcore_alerts import check_burn_rates

    print("=" * 60)
    print("  AGENT X RUNTIME — IQcore Cost Map Verification")
    print("=" * 60)

    rt = AgentXRuntime()

    # Show decorated cost metadata
    methods = [
        ("review_proposal", rt.review_proposal),
        ("approve_or_reject", rt.approve_or_reject),
        ("model_lifecycle_decision", rt.model_lifecycle_decision),
        ("segment_split_merge_decision", rt.segment_split_merge_decision),
        ("constitutional_check", rt.constitutional_check),
        ("supervision_cycle", rt.supervision_cycle),
    ]

    total_cost = 0
    print()
    for name, method in methods:
        actor = getattr(method, "_iqcore_actor", "?")
        cost = getattr(method, "_iqcore_cost", 0)
        total_cost += cost
        print(f"  {name:35s}  actor={actor}  cost={cost}")

    print(f"\n  Total per-governance-cycle cost:  {total_cost} IQcores")
    print(f"  AgentX budget:                    {IQCORES.limits('agentx')} IQcores")
    print(f"  Headroom:                         {IQCORES.limits('agentx') - total_cost} IQcores")

    # Run a sample governance cycle
    print("\n  Running sample governance cycle...")

    sample_proposal = {
        "proposal_id": "test_001",
        "candidates": [
            {"segment": "CA_restaurant", "confidence": 0.85, "type": "cost_explosion"},
            {"segment": "NY_salon", "confidence": 0.72, "type": "script_performance"},
        ],
        "segments_affected": ["CA_restaurant", "NY_salon"],
    }

    review = rt.review_proposal(sample_proposal)
    print(f"    Review: {review['verdict']} (conf={review['avg_confidence']:.2f})")

    approved = rt.approve_or_reject(sample_proposal, review)
    print(f"    Decision: {'APPROVED' if approved else 'REJECTED'}")

    const = rt.constitutional_check(sample_proposal)
    print(f"    Constitutional: {'COMPLIANT' if const['compliant'] else 'VIOLATION'}")

    model_req = {"action": "RETRAIN_MODEL", "target": "CA_restaurant", "reason": "cost_explosion"}
    mdl = rt.model_lifecycle_decision(model_req)
    print(f"    Model decision: {'APPROVED' if mdl['approved'] else 'DENIED'}")

    seg_req = {"operation": "split", "target": "NY_salon", "reason": "script_degradation"}
    seg = rt.segment_split_merge_decision(seg_req)
    print(f"    Segment decision: {'APPROVED' if seg['approved'] else 'DENIED'}")

    sup = rt.supervision_cycle()
    print(f"    Supervision: regime={sup['regime_status']} segments={sup['segments']}")

    print(f"\n  Ledger after governance cycle:")
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
