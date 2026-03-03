# AQI Master Index Schema (Public Blueprint)

## Purpose
This document provides a public, non-sensitive blueprint of the AQI Master Index Schema and indexing system. It is designed for transparency, stewardship, and open-source collaboration—without exposing confidential or operational secrets.

---

## AQI Indexing Layers (Schema Overview)

1. **Inventory Layer**
   - Captures all artifacts (documents, code, data, diagrams, exports, etc.)
   - Assigns unique IDs and computes checksums
   - Immutable: updates create new versions

2. **Metadata Layer**
   - Classifies each artifact by domain, subdomain, module, tags, lineage, version, weights, and governance relevance
   - Ensures deterministic, schema-compliant metadata

3. **Relational Graph Layer**
   - Maps conceptual relationships, dependencies, and contradictions
   - Links artifacts across domains and assigns relationship types/strengths
   - Maintains a coherent, acyclic graph (unless marked as paradox)

4. **Summaries Layer**
   - Generates short, medium, long, doctrine, technical, and relational summaries for each artifact
   - Summaries use canonical terms and normalized structure

5. **Normalization Layer**
   - Applies canonical vocabulary, resolves aliases, enforces invariants, and tracks deltas
   - Ensures structural consistency before retrieval

6. **Retrieval Layer**
   - Enables deterministic, reversible queries (concept, domain, module, lineage, relational, governance, time, version, similarity)

---

## Example Metadata Schema (YAML)

```yaml
- identifier: "Inventory/AQI_MASTER_INDEX.md"
  canonical_name: "AQI_MASTER_INDEX.md"
  extension: ".md"
  relative_path: "Agent X/AQI_MASTER_INDEX.md"
  schema_layer: "Inventory"
  module_name: "N/A"
  artifact_role: "doctrine-blueprint"
  artifact_type: "document"
  status: "active"
  origin: "manual"
  generation_method: "manual"
  parent_artifacts: []
  child_artifacts: []
  primary_topics: ["index", "schema", "blueprint"]
  key_concepts: ["AQI Master Index", "schema", "governance"]
  related_doctrines: ["AQI Governance Charter"]
  sensitivity: "public"
  summary_1line: "Master index and schema for AQI system artifacts."
```

---

## Implementation Blueprint (Excerpt)

- **Artifact Discovery:** Scan all designated sources (doctrine, architecture, exports, logs, directives, outputs, etc.)
- **Artifact Capture:** Assign IDs, compute checksums, store raw content, timestamp creation/update
- **Metadata Assignment:** Classify by schema fields (see above)
- **Relational Graph Construction:** Map relationships, dependencies, contradictions
- **Summary Generation:** Produce multi-length summaries for each artifact
- **Normalization:** Apply canonical terms, resolve aliases, enforce invariants
- **Retrieval Interface Activation:** Enable all query endpoints

---

## Sample Index Entry (Public)

```yaml
- identifier: "Inventory/Alan_Complete_Schematic.md"
  canonical_name: "Alan_Complete_Schematic.md"
  extension: ".md"
  relative_path: "Agent X/Alan_Complete_Schematic.md"
  schema_layer: "Inventory"
  module_name: "Alan"
  artifact_role: "schematic"
  artifact_type: "document"
  status: "active"
  origin: "manual"
  generation_method: "manual"
  parent_artifacts: []
  child_artifacts: []
  primary_topics: ["Alan", "schematic", "architecture"]
  key_concepts: ["Alan system", "architecture"]
  related_doctrines: ["AQI Master Index"]
  sensitivity: "public"
  summary_1line: "Complete schematic for the Alan subsystem."
```

---

## Governance & Stewardship
- All public index entries are reviewed for sensitivity before publication.
- No operational credentials, private data, or internal-only artifacts are included.
- This schema is open for stewardship, audit, and collaborative improvement.

---

*For full operational details, see the private AQI Master Index in the Agent X system.*
