# AQI Storage

The persistence and replay system for AQI's governed intelligence pipeline.

## Overview

AQI Storage provides immutable lineage storage and deterministic replay capabilities for the AQI governance system. Every packet, delta, and decision is permanently stored with full forensic traceability.

## Features

- **Immutable Ledger**: All governance artifacts are permanently stored
- **Deterministic Replay**: Reconstruct any past pipeline run exactly
- **Forensic Debugging**: Inspect every decision and state transition
- **Governance Integrity**: Prove authority rules were followed
- **Multi-level Storage**: Global chronological + per-run organization

## Architecture

### Directory Structure

```
aqi_storage/
├── packets/          # All TalkPackets chronologically
├── deltas/           # All DeltaPackets chronologically
├── decisions/        # All DecisionPackets chronologically
├── snapshots/        # Pipeline run snapshots
└── runs/
    └── <run_id>/     # Per-run forensic storage
        ├── packets/
        ├── deltas/
        ├── decisions/
        └── summary.json
```

### Storage Format

All artifacts are stored as JSON with canonical structure:

- **Packets**: TalkPackets with stage metadata
- **Deltas**: Semantic changes between states
- **Decisions**: Governance decisions (approve/reject/escalate/modify)
- **Snapshots**: Complete pipeline run summaries

## Usage

### Persistence

```python
from aqi_storage import persist_packet, persist_delta, persist_decision, persist_snapshot

# During pipeline execution
persist_packet(packet_data, run_id, stage_index)
persist_delta(delta_data, run_id, stage_index)
persist_decision(decision_data, run_id, stage_index)

# At pipeline completion
persist_snapshot(snapshot_data)
```

### Replay

```python
from aqi_storage import replay_run

# Reconstruct a past run
replay_data = replay_run(run_id)
print(replay_data["reconstructed_state"])
```

## Installation

```bash
pip install -e .
```

## Integration

The storage system integrates seamlessly with the AQI governance pipeline:

1. **Pipeline Stage**: Generate TalkPacket
2. **Governance**: Evaluate and decide
3. **Storage**: Persist all artifacts
4. **Replay**: Reconstruct state from storage

This creates an immutable audit trail of AQI's intelligence evolution.