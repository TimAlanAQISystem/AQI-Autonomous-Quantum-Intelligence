# AQI Governance Intelligence Layer

The fifth pillar of AQI - providing advanced governance intelligence capabilities including integrity verification, time-travel introspection, divergence detection, and authority escalation workflows.

## Features

### 🔐 Integrity Verification
- Hash chains for immutable lineage verification
- Merkle roots for tamper detection
- Ledger integrity validation

### 🕰️ Introspection
- Governance time-travel through pipeline stages
- Authority history analysis
- Decision lineage tracking

### 🔁 Divergence Detection
- Multi-run comparison
- Drift detection between executions
- Payload difference analysis

### 🧭 Escalation Workflows
- Automatic authority escalation rules
- Governance policy enforcement
- Decision-based escalation triggers

## Installation

```bash
pip install -e .
```

## Usage

```python
from aqi_governance_intelligence import (
    verify_integrity,
    compute_merkle_root,
    time_travel,
    authority_history,
    compare_runs,
    detect_drift,
    apply_escalation_rules
)

# Verify run integrity
integrity = verify_integrity("run-123")
print(f"Merkle root: {integrity['merkle_root']}")

# Time travel to a specific stage
packet = time_travel("run-123", 2)
print(f"Stage 2 state: {packet}")

# Compare two runs for differences
diffs = compare_runs("run-123", "run-124")
print(f"Found {len(diffs)} differences")

# Apply escalation rules
escalation = apply_escalation_rules(packet, decision)
if escalation["action"] == "escalate":
    print(f"Escalating to authority {escalation['to_authority']}")
```

## Architecture

The Governance Intelligence Layer consists of four subsystems:

- **integrity.py**: Hash chains and Merkle roots
- **introspection.py**: Time-travel and authority analysis
- **divergence.py**: Multi-run comparison and drift detection
- **escalation.py**: Authority escalation workflows

All functionality is exposed through a unified API in `api.py`.