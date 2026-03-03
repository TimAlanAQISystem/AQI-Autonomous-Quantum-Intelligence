# AQI Governance Engine

The Governance Engine enforces authority and constraints on AQI state changes, making the system accountable and governed.

## Overview

The Governance Engine is the third pillar of AQI's evolution from a modular pipeline to a stateful, governed intelligence system. It consumes TalkPackets from the Delta Engine and enforces:

- **Authority Validation**: Ensures operations have sufficient authority levels
- **Constraint Enforcement**: Prevents invalid state transitions
- **Decision Tracking**: Records all governance decisions for audit trails
- **Escalation Handling**: Routes insufficient-authority operations to higher levels

## Architecture

### Core Components

- **GovernanceEngine**: Main engine that evaluates TalkPackets and makes decisions
- **DecisionPacket**: Schema for governance decisions (approve, reject, escalate, modify)
- **GovernanceRules**: Rule engine with AQI-specific policies
- **AuthorityManager**: Manages authority levels and validation

### Decision Types

- **APPROVE**: Packet passes all checks, proceed with processing
- **REJECT**: Packet violates constraints, do not process
- **ESCALATE**: Insufficient authority, route to higher authority
- **MODIFY**: Packet needs modifications before approval

## Usage

```python
from aqi_governance import GovernanceEngine
from talk import TalkInterpreter

# Initialize governance engine
interpreter = TalkInterpreter()
governance = GovernanceEngine(interpreter)

# Evaluate a packet
decision = governance.evaluate_packet(talk_packet)

# Process the decision
governance.process_decision(decision)
```

## Governance Rules

The engine enforces specific AQI policies:

- **Immutable Normalization**: Normalization results cannot be overridden
- **Authority Requirements**: Graph mutations require higher authority levels
- **Metadata Constraints**: Metadata cannot override inventory data
- **Lineage Integrity**: Authority chains must be valid and unbroken

## Authority Levels

- **Level 1**: Basic operations (inventory, metadata extraction)
- **Level 2**: Structural changes (cross-references, graph building)
- **Level 3**: Normalization and finalization
- **Level 4**: System administration and overrides

## Installation

```bash
pip install -e .
```

## Dependencies

- `talk>=0.1.0`: Universal relational protocol
- `pydantic>=2.0.0`: Data validation and serialization