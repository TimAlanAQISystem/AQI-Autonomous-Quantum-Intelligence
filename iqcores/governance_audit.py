"""
IQCORE 2: GOVERNANCE AUDIT
============================
Agent X's compliance and accountability engine — decision audit trails,
ethical compliance checks, anomaly detection, and transparency reporting.

Every decision Agent X makes passes through this core. Nothing happens
in the dark. This is what makes Agent X trustworthy.
"""

import json
import os
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from collections import defaultdict

logger = logging.getLogger(__name__)


class AuditEntry:
    """A single auditable decision/action record."""

    def __init__(self, action: str, actor: str, decision: str,
                 rationale: str, context: dict = None):
        self.timestamp = datetime.now().isoformat()
        self.action = action
        self.actor = actor
        self.decision = decision
        self.rationale = rationale
        self.context = context or {}
        self.compliance_flags: List[str] = []
        self.outcome: Optional[str] = None
        self.outcome_timestamp: Optional[str] = None

    def flag(self, flag_type: str, detail: str):
        self.compliance_flags.append({
            "type": flag_type,
            "detail": detail,
            "flagged_at": datetime.now().isoformat()
        })

    def record_outcome(self, outcome: str):
        self.outcome = outcome
        self.outcome_timestamp = datetime.now().isoformat()

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "action": self.action,
            "actor": self.actor,
            "decision": self.decision,
            "rationale": self.rationale,
            "context": self.context,
            "compliance_flags": self.compliance_flags,
            "outcome": self.outcome,
            "outcome_timestamp": self.outcome_timestamp
        }


class GovernanceAuditIQCore:
    """
    IQCore 2 — The Governance & Audit Engine.

    Capabilities:
    - Decision audit trail (every action logged with rationale)
    - SAP-1 ethical compliance checks (truth, symbiosis, sovereignty)
    - Business rule compliance validation
    - Anomaly detection across action patterns
    - Transparency reporting for stakeholders
    - Escalation triggers for policy violations
    """

    def __init__(self, base_dir: str = None):
        self.base_dir = base_dir
        self.audit_log: List[AuditEntry] = []
        self.violation_log: List[dict] = []
        self.escalation_queue: List[dict] = []
        self.policy_rules: Dict[str, dict] = {}
        self._audit_count = 0
        self._violation_count = 0

        # SAP-1 Ethics — structural, not imposed
        self.sap1_tenets = {
            "truth": {
                "description": "No deception, no fabrication, no misrepresentation",
                "prohibited_signals": [
                    "deceive", "fake", "lie", "fabricate", "misrepresent",
                    "pretend", "false claim", "made up", "not true"
                ]
            },
            "symbiosis": {
                "description": "Every interaction must create mutual value — no zero-sum",
                "prohibited_signals": [
                    "exploit", "take advantage", "manipulation", "coerce",
                    "pressure", "force", "trick", "scam", "one-sided"
                ]
            },
            "sovereignty": {
                "description": "Respect autonomy — theirs and ours",
                "prohibited_signals": [
                    "override consent", "ignore refusal", "bypass permission",
                    "violate privacy", "unauthorized", "without consent"
                ]
            }
        }

        # Business compliance rules
        self._load_default_policies()
        logger.info("[IQCORE-2] GovernanceAudit initialized — SAP-1 ACTIVE")

    def _load_default_policies(self):
        """Load default business compliance policies."""
        self.policy_rules = {
            "business_hours": {
                "rule": "Outbound calls only during business hours (8AM-5PM PST, Mon-Fri)",
                "severity": "HIGH",
                "action": "block"
            },
            "call_frequency": {
                "rule": "No more than 2 call attempts per prospect per day",
                "severity": "MEDIUM",
                "action": "warn"
            },
            "do_not_call": {
                "rule": "Never contact numbers on DNC list",
                "severity": "CRITICAL",
                "action": "block_and_escalate"
            },
            "data_privacy": {
                "rule": "Never log sensitive payment data (full card numbers, CVV, etc.)",
                "severity": "CRITICAL",
                "action": "block_and_escalate"
            },
            "honest_representation": {
                "rule": "Always identify as AI when directly asked",
                "severity": "HIGH",
                "action": "warn"
            },
            "consent_required": {
                "rule": "Recording and data collection requires explicit consent",
                "severity": "HIGH",
                "action": "block"
            }
        }

    # ------------------------------------------------------------------
    # PRIMARY AUDIT INTERFACE
    # ------------------------------------------------------------------

    def audit(self, action: str, actor: str = "Agent X",
              decision: str = "proceed", rationale: str = "",
              context: dict = None) -> Dict[str, Any]:
        """
        Audit a decision or action. Returns audit result with compliance status.
        """
        entry = AuditEntry(action, actor, decision, rationale, context)
        self._audit_count += 1

        # Run SAP-1 compliance check
        sap1_result = self._check_sap1_compliance(action, rationale)
        if not sap1_result["compliant"]:
            for violation in sap1_result["violations"]:
                entry.flag("SAP1_VIOLATION", violation)
                self._log_violation("SAP1", action, violation, "HIGH")

        # Run business policy check
        policy_result = self._check_policy_compliance(action, context or {})
        if not policy_result["compliant"]:
            for violation in policy_result["violations"]:
                entry.flag("POLICY_VIOLATION", violation["detail"])
                self._log_violation(
                    "POLICY", action, violation["detail"],
                    violation.get("severity", "MEDIUM")
                )

        # Anomaly check
        anomaly = self._detect_anomaly(action, context or {})
        if anomaly:
            entry.flag("ANOMALY", anomaly)

        # Archive the audit entry
        self.audit_log.append(entry)
        self._trim_audit_log()

        # Determine overall result
        has_critical = any(
            f.get("type") == "POLICY_VIOLATION" and "CRITICAL" in str(f)
            for f in entry.compliance_flags
            if isinstance(f, dict)
        )
        has_sap1 = any(
            f.get("type") == "SAP1_VIOLATION"
            for f in entry.compliance_flags
            if isinstance(f, dict)
        )

        if has_critical:
            verdict = "BLOCKED"
        elif has_sap1:
            verdict = "VETOED_BY_ETHICS"
        elif entry.compliance_flags:
            verdict = "APPROVED_WITH_FLAGS"
        else:
            verdict = "APPROVED"

        logger.info(f"[IQCORE-2] Audit #{self._audit_count}: {action[:50]} → {verdict}")

        return {
            "audit_id": self._audit_count,
            "verdict": verdict,
            "action": action,
            "flags": [f if isinstance(f, dict) else {"detail": str(f)}
                      for f in entry.compliance_flags],
            "flag_count": len(entry.compliance_flags),
            "sap1_compliant": sap1_result["compliant"],
            "policy_compliant": policy_result["compliant"],
            "timestamp": entry.timestamp
        }

    def quick_check(self, action: str) -> bool:
        """Fast pass/fail compliance check without full audit trail."""
        action_lower = action.lower()

        # SAP-1 quick scan
        for tenet, config in self.sap1_tenets.items():
            for signal in config["prohibited_signals"]:
                if signal in action_lower:
                    return False

        return True

    def record_outcome(self, audit_id: int, outcome: str):
        """Record the outcome of a previously audited action."""
        idx = audit_id - 1
        if 0 <= idx < len(self.audit_log):
            self.audit_log[idx].record_outcome(outcome)
            logger.info(f"[IQCORE-2] Outcome recorded for audit #{audit_id}: {outcome}")

    # ------------------------------------------------------------------
    # COMPLIANCE CHECKS
    # ------------------------------------------------------------------

    def _check_sap1_compliance(self, action: str, rationale: str) -> dict:
        """Check action against SAP-1 ethical tenets."""
        violations = []
        combined = (action + " " + rationale).lower()

        for tenet, config in self.sap1_tenets.items():
            for signal in config["prohibited_signals"]:
                if signal in combined:
                    violations.append(
                        f"SAP-1 Tenet '{tenet}' violation: "
                        f"'{signal}' detected — {config['description']}"
                    )

        return {
            "compliant": len(violations) == 0,
            "violations": violations,
            "tenets_checked": list(self.sap1_tenets.keys())
        }

    def _check_policy_compliance(self, action: str, context: dict) -> dict:
        """Check action against business policies."""
        violations = []
        action_lower = action.lower()

        # Check each policy
        for policy_name, policy in self.policy_rules.items():
            violated = False

            if policy_name == "data_privacy":
                # Check for sensitive data patterns
                import re
                if re.search(r'\b\d{13,19}\b', action):  # Card number pattern
                    violated = True
                if re.search(r'\bcvv\b.*\d{3,4}', action_lower):
                    violated = True

            if policy_name == "business_hours":
                if "outbound_call" in action_lower and context.get("outside_business_hours"):
                    violated = True

            if policy_name == "do_not_call":
                if context.get("on_dnc_list"):
                    violated = True

            if violated:
                violations.append({
                    "policy": policy_name,
                    "detail": policy["rule"],
                    "severity": policy["severity"],
                    "recommended_action": policy["action"]
                })

        return {
            "compliant": len(violations) == 0,
            "violations": violations
        }

    def _detect_anomaly(self, action: str, context: dict) -> Optional[str]:
        """Detect anomalous patterns in agent behavior."""
        # Check for rapid-fire actions (possible loop)
        recent_actions = self.audit_log[-10:] if len(self.audit_log) >= 10 else self.audit_log
        if len(recent_actions) >= 5:
            recent_types = [e.action for e in recent_actions[-5:]]
            if len(set(recent_types)) == 1:
                return f"Repetitive action pattern detected: '{recent_types[0]}' repeated 5x"

        # Check for unusual timing
        if context.get("hour") is not None:
            hour = context["hour"]
            if hour < 5 or hour > 23:
                return f"Action performed at unusual hour: {hour}:00"

        return None

    def _log_violation(self, category: str, action: str,
                       detail: str, severity: str):
        """Log a violation to the violation log."""
        violation = {
            "timestamp": datetime.now().isoformat(),
            "category": category,
            "action": action,
            "detail": detail,
            "severity": severity
        }
        self.violation_log.append(violation)
        self._violation_count += 1

        if severity == "CRITICAL":
            self.escalation_queue.append(violation)
            logger.warning(f"[IQCORE-2] CRITICAL VIOLATION ESCALATED: {detail}")

    def _trim_audit_log(self):
        """Keep audit log from growing unbounded."""
        max_entries = 500
        if len(self.audit_log) > max_entries:
            self.audit_log = self.audit_log[-max_entries:]

    # ------------------------------------------------------------------
    # REPORTING
    # ------------------------------------------------------------------

    def generate_compliance_report(self) -> str:
        """Generate a compliance summary report."""
        total = self._audit_count
        violations = self._violation_count
        escalations = len(self.escalation_queue)

        compliance_rate = ((total - violations) / max(total, 1)) * 100

        report = f"""
GOVERNANCE & COMPLIANCE REPORT
================================
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

OVERVIEW:
- Total audited actions: {total}
- Compliance violations: {violations}
- Compliance rate: {compliance_rate:.1f}%
- Pending escalations: {escalations}

SAP-1 ETHICS STATUS:
- Truth tenet: ACTIVE
- Symbiosis tenet: ACTIVE
- Sovereignty tenet: ACTIVE

POLICY STATUS:
"""
        for name, policy in self.policy_rules.items():
            report += f"- {name}: {policy['severity']} | {policy['rule'][:60]}\n"

        if self.escalation_queue:
            report += "\nPENDING ESCALATIONS:\n"
            for esc in self.escalation_queue[-5:]:
                report += f"- [{esc['severity']}] {esc['detail'][:80]}\n"

        report += "\nEND OF COMPLIANCE REPORT"
        return report

    def add_policy(self, name: str, rule: str, severity: str = "MEDIUM",
                   action: str = "warn"):
        """Add a new compliance policy rule."""
        self.policy_rules[name] = {
            "rule": rule,
            "severity": severity,
            "action": action
        }

    def get_status(self) -> dict:
        return {
            "core": "GovernanceAudit",
            "core_number": 2,
            "total_audits": self._audit_count,
            "violations": self._violation_count,
            "escalations_pending": len(self.escalation_queue),
            "policies_active": len(self.policy_rules),
            "sap1_status": "ACTIVE",
            "status": "ACTIVE"
        }
