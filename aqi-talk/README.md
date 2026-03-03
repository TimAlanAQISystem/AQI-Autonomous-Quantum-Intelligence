# AQI TALK

TALK protocol implementation for AQI:  
canonical schema, interpreter, and pipeline integration hooks.

This is **not** human conversation.  
TALK is the **structured exchange of state, intent, constraints, and lineage** between systems.

---

## Core concepts

- **TalkStateChange** – what changed in the world (resource, operation, payload)
- **IntentType** – why this change exists (create, update, correct, sync, etc.)
- **ConstraintType** – how this change is governed (require_ack, immutable, etc.)
- **Lineage** – who/what/where this change came from
- **TalkPacket** – canonical container for all of the above
- **TalkInterpreter** – universal device to:
  - ingest raw events
  - decode into TalkPacket
  - verify constraints
  - re-encode for any target

---

## Installation

From the project root (`aqi-talk/`):

```bash
pip install .
```

or in editable/development mode:

```bash
pip install -e .
```

Requires Python 3.10+.

---

## Usage overview

### 1. Create a TALK Interpreter

```python
from aqi_talk import TalkInterpreter

ti = TalkInterpreter()
```

### 2. Register decoders and encoders

```python
from aqi_talk import RawEvent, TalkPacket

# Use the default filesystem decoder
ti.register_decoder("filesystem", "file_changed", TalkInterpreter.default_filesystem_decoder)

# Example encoder: encode TALK into a simple dict for logging
def log_encoder(packet: TalkPacket) -> dict:
    return packet.to_dict()

ti.register_encoder("log", log_encoder)
```

### 3. Decode a raw event

```python
from aqi_talk import RawEvent

raw = RawEvent(
    source="filesystem",
    event_type="file_changed",
    payload={
        "path": "docs/example.txt",
        "operation": "update",
        "content_hash": "abc123",
        "size": 1024,
    },
    metadata={"context": "watcher-1"},
)

packet = ti.decode(raw)
print(packet.to_dict())
```

### 4. Encode for a target

```python
encoded = ti.encode(packet, target="log")
print(encoded)
```

---

## Integration with an AQI-style pipeline

You can wrap your module outputs into TALK packets using helper functions.

### Inventory → TALK

```python
from aqi_talk import pipeline_hooks

packet = pipeline_hooks.talk_from_inventory_event(
    file_path="data/input.json",
    operation="create",  # or "update" / "delete"
)
```

### Graph → TALK

```python
from aqi_talk import pipeline_hooks, IntentType

packet = pipeline_hooks.talk_for_graph_mutation(
    node_id="node-123",
    operation="update",
    payload={"tags": ["customer", "active"]},
    intent=IntentType.UPDATE,
)
```

From there, you can:

- send `packet` through the TALK Interpreter
- log it
- propagate it
- enforce constraints
- attach additional lineage

---

## Extending TALK

You can:

- add new `IntentType` values (e.g. "lock", "unlock")
- add new `ConstraintType` values (e.g. "requires_human_review")
- add more decoders for:
  - HTTP API events
  - message queue events
  - graph mutations
- add encoders for:
  - AQI audit logs
  - external systems
  - governance engines

All without changing the canonical `TalkPacket` structure.

---

## Why this exists

This package gives AQI a **relational protocol**:

- not human language
- not a chatbot
- not "conversation"

Just a **deterministic way to express:**

- what changed
- why it changed
- under what constraints
- under whose authority

And to translate that across systems.