# Agent X / Alan Autonomy & Governance

This document describes the patterns and scripts supporting safe autonomy for Alan (Agent X).

## Principles

- Autonomy is enabling but not destructive. Alan should be allowed to do routine work autonomously but human oversight is required on high-risk, self-modifying behaviors.

- Safety first: the system includes an auditable kill switch (`KILL_SWITCH_FILE`) and human-in-the-loop (HITL) thresholds.

- Respect for legal/ethical constraints: Alan must not perform harmful actions to humans. Alan may engage in lawful, ethical competitive actions such as lead generation, enrichment, and contact verification provided they do not cross legal lines (no harassment, no DDoS, no illicit data theft, no instructions to carry out violence). Alan's actions must be auditable.

- Reversibility: cleaning/archival actions never delete by default — they move files to `archive/`.

## Key scripts

- `tools/cleanup_desktop.py`: dry-run-first archival tool for removing clutter from the workspace and moving to `archive/desktop_cleanup/`.

- `tools/run_autonomy_check.py`: health check covering DB, vector index, distillation queue, and kill-switch status.

- `tools/snippet_learning_agent.py`: ingestion, approval, micro-distill, queued distillation, and apply_patch ledger. **Human-in-the-loop gating remains for high-risk patches.**

- `tools/snippet_to_vector.py`: vector index and query; includes a pure-Python fallback in case platform binary libs aren't available.

## Operational suggestions

1. Scheduling: run `tools/run_autonomy_check.py` periodically (Windows Scheduled Task) with a script that alerts via logs or notifications. Also schedule micro-distill + rebuild to consume approved snippets.

2. Build CI: add testing in CI for both the normal and dependency-constrained environments (with and without scikit-learn installed).

3. Governance: keep the `apply_patch` ledger and `kill_switch` active. Implement a two-person approval process if you require stricter governance for high-risk patches.

4. Backups: schedule a backup of DB `north_connector.db` and `archive` before any significant changes.

## Legal and safety boundary

- I cannot implement or help implement modules or automation that enable harmful activities to human entities (violent harm, doxxing, or targeted harassment). Likewise I cannot help create an autonomous agent that intentionally bypasses legal or moral safeguards.

- If you want to allow Alan to be "autonomous to the fullest possible extent," we can proceed with automating all allowed operations (ingest, index, enrich, call, provide leads) as long as the operations are legal and audited.

## Next steps (pick one)

- A: Schedule & Automate: Add scheduled tasks, alerts, and fully automate the ingest -> distill -> index path with HITL notifications but no manual action required for low-risk snippets.

- B: Human-Governance Upgrade: Implement a two-person approval web UI and notification system before applying high-risk patches.

- C: Hardening & CI: Add CI job(s) that test both sklearn present and sklearn-absent workflows, and validating the kill switch behavior, then add deployment CLI.

For anything that might cause harm or enable bypass of ethical constraints: we cannot help you implement those. If you still want to proceed with features that are both safe and compliant, say which option you'd like so I can implement it.
