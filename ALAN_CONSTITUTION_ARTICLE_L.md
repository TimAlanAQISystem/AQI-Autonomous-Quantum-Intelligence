# ALAN CONSTITUTION ARTICLE L: Logging & Lineage

## 1. Mandate
Every governance decision, state transition, and boundary interaction MUST be recorded in a structured, queryable format to ensure full traceability and accountability of the Alan AI system.

## 2. The Golden Rule of Lineage
**"If it is not in the logs, it did not happen. If it cannot be traced, it cannot be governed."**

## 3. Surface-Specific Logging Requirements

### 3.1 Surface 1: Opening Intent
- MUST Log the classified intent and confidence score.
- MUST Log the latency (ms) from audio start to classification.
- MUST Log any fallback or retry attempts.

### 3.2 Surface 2: Conversational State
- MUST Log every state transition (e.g., S0 -> S1).
- MUST Log the specific trigger/utterance causing the transition.
- MUST Log prohibited transition attempts (e.g., S1 -> S7 illegal jump).

### 3.3 Surface 3: Identity & Role
- MUST Log every assertion of identity (e.g., "I am Alan").
- MUST Log any user challenge to identity ("Are you a robot?").
- MUST Log the response template ID selected.

### 3.4 Surface 4: Compliance & Legitimacy
- MUST Log any block trigger (e.g., user asks for guarantee).
- MUST Log the specific deflection strategy used.
- MUST Log confirmation of disclosure delivery.

### 3.5 Surface 5: Escalation & Termination
- MUST Log the escalation level change (L0 -> L1 -> L4).
- MUST Log the detected hostility type (Profanity, Refusal).
- MUST Log the method of termination (Standard goodbye vs. Emergency cut).

## 4. Versioning & Auditability
- All logs MUST carry a `GovernanceVersion` tag.
- Logs MUST be immutable once written.
- A "Lineage Reconstruction" MUST be capable of replaying the decision path of any call without audio.

## 5. Violation
Failure to log a decision is a Critical Failure. A silent system is an unsafe system.
