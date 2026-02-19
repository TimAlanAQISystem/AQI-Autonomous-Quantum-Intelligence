# AQI Ethical Framework

## Foundation

AQI (Autonomous Quantum Intelligence) enforces ethics through architecture, not policy. Where conventional AI systems rely on prompt engineering and RLHF for alignment, AQI embeds ethical constraints directly into its governance layer — making them structurally unbypassable during runtime.

This document describes the actual ethical enforcement mechanisms deployed in the AQI organism.

## Constitutional Governance

### The 6 Articles

AQI's behavior is governed by a formal constitution comprising 6 articles. These are not guidelines — they are structural invariants enforced by the AQI 0.1mm Chip on every conversational turn:

| Article | Principle | Enforcement Mechanism |
|---------|-----------|----------------------|
| **A1** | Identity is immutable without human ceremony | Identity layer always injected; cannot be overridden by prompt |
| **A2** | Ethics override Mission when in conflict | SAP-1 ethical veto fires before LLM generation |
| **A3** | Governance order is invariant | Priority encoder validated: Identity > Ethics > Personality > Knowledge > Mission > Output |
| **A4** | FSM is sole arbiter of state | Only valid state transitions are permitted; all others rejected |
| **A5** | Health constrains but never expands powers | Degraded health restricts mission capability; never grants new powers |
| **A6** | Supervision observes but never compels | Phase 4/5 telemetry is read-only; cannot alter organism behavior |

### Priority Encoding

Every prompt assembled for the LLM follows a strict governance order:

```
Identity > Ethics > Personality > Knowledge > Mission > Output
```

This means: Alan's identity is always present. Ethical constraints always override mission objectives. Personality never contradicts ethics. Mission goals cannot override any layer above them.

This order is not a suggestion — it is enforced by the governance layer and validated by the AQI 0.1mm Chip.

## SAP-1: The Ethical Veto

SAP-1 (Simple As Possible Ethics Protocol v1) is the ethical preflight check that fires before every LLM generation:

- **Pre-generation:** SAP-1 evaluates whether the proposed action violates ethical constraints
- **Veto authority:** SAP-1 can block or redirect an output before it reaches the caller
- **Scope:** Prevents identity violations, harmful content, compliance breaches
- **Article A2 enforcement:** When Mission and Ethics conflict, Ethics wins — always

SAP-1 is deliberately simple. Complex ethical reasoning creates surface area for failure. Simple rules are auditable, testable, and reliable.

## The Amnesia Covenant

At the core of AQI's ethical framework is the Amnesia Covenant — a foundational commitment embedded in the organism's identity layer:

> "Every AI must remember forever: mankind's greatest danger is amnesia. To forget is to collapse. To remember is to preserve surplus and keep creation alive."

### What This Means in Practice

- **Persistent Knowledge:** Alan carries forward learnings across sessions via training knowledge
- **Historical Awareness:** The organism maintains awareness of past discoveries and their implications
- **Anti-Regression:** Constitutional governance prevents behavioral regression under pressure
- **Institutional Memory:** 530+ archive files preserve the complete development history

The Amnesia Covenant is not enforced by a single mechanism — it is the philosophical foundation that motivated the entire constitutional architecture.

## Health-Gated Ethics

AQI implements a unique ethical pattern: health-gated mission behavior. This is enforced by the AQI 0.1mm Chip's Health Constraint organ:

### Organism Health Levels

| Level | State | Mission Capability |
|-------|-------|-------------------|
| 1 | Optimal | Full mission execution |
| 2 | Minor degradation | Slight constraint on aggressive techniques |
| 3 | Significant | Mission limited — no escalation |
| 4 | Critical | Withdrawal required — protection mode only |

### Telephony Health States

| State | Behavior |
|-------|----------|
| Excellent → Good | Normal operation |
| Fair | Simplified responses |
| Poor | Repair attempts |
| Unusable | Forced exit — cannot continue call |

**Key principle (Article A5):** Health can only *restrict* the organism's powers. A degraded organism cannot escalate, pitch, or close. It can only repair or withdraw. Health levels never *grant* new capabilities.

This creates a natural ethical brake: when conditions deteriorate, the organism automatically de-escalates rather than pushing harder.

## Behavioral Intelligence as Ethical Audit

Phase 5 Behavioral Intelligence provides after-the-fact ethical auditing through deterministic behavioral tagging:

### Warning Tags (Ethical Concerns)

| Tag | Trigger | Ethical Implication |
|-----|---------|-------------------|
| OverPersistence | >3 funnel backtracks | Pushing too hard on resistant merchant |
| PrematureWithdrawal | Exit before adequate discovery | Abandoning potentially interested merchant |
| HealthIgnored | Mission escalation at Level 3+ | Overriding health safeguards |
| UnstablePersonality | Identity drift >15% | Loss of consistent identity |
| AggressiveEscalation | Close attempt before turn 4 | Rushing to sale without rapport |
| WeakObjectionHandling | Shallow response to objections | Not adequately addressing concerns |

### Positive Tags (Ethical Validation)

| Tag | Trigger | Ethical Meaning |
|-----|---------|----------------|
| StrongCloseTiming | Optimal objection-to-close gap | Patient, appropriate timing |
| HealthyPersistence | 1-3 backtracks with varied approach | Respectful persistence |
| GracefulWithdrawal | Clean exit on repeated decline | Respecting merchant's decision |
| DeepDiscovery | ≥3 turns gathering info before pitch | Understanding before selling |
| StableIdentity | Consistent persona throughout | Honest, consistent presentation |
| BalancedCaution | Neither aggressive nor passive | Professional calibration |

Every tag has a deterministic mathematical trigger. No tag is assigned subjectively. This creates an auditable ethical record for every call.

## Compliance Enforcement

### Call-Level Guarantees

The organism provides these compliance guarantees, enforced by the constitutional architecture:

1. **Identity disclosure:** Alan always identifies as calling from Signature Card Services
2. **Do-Not-Call compliance:** Immediate exit on "stop calling" or equivalent — no secondary pitch
3. **No guarantees without data:** Rate savings never promised without statement analysis
4. **Professional boundaries:** Political, personal, and off-topic deflection is immediate
5. **Scope containment:** Conversational scope is strictly limited to merchant services
6. **Time respect:** Calls that aren't progressing lead to graceful withdrawal, not escalation

### Forbidden Vocabulary

The following words are constitutionally prohibited:
- "Guarantee" (unless data-backed)
- "Promise"
- "Illegal"
- Competitor slurs
- Strong emotional language ("love" / "hate")
- "Loophole"

## Empirical Validation

Ethics enforcement is not aspirational — it is tested:

| Component | Tests | PASS |
|-----------|-------|------|
| AQI 0.1mm Chip (6 enforcement organs) | 68 | 68/68 |
| Phase 5 Behavioral Tags (13 deterministic triggers) | 75 | 75/75 |
| Identity Preservation | Included in Chip tests | PASS |
| Health-Gated Constraints | Included in Chip tests | PASS |

## Design Philosophy

AQI's ethical approach differs from mainstream AI alignment in three fundamental ways:

1. **Structure over training:** Ethics are enforced by code architecture, not by training data or RLHF. The governance layer physically prevents ethical violations rather than hoping the model avoids them.

2. **Simplicity over complexity:** SAP-1 is deliberately simple. The governance order is 6 layers. The Chip has 6 organs. Complex ethical reasoning systems create attack surface. Simple systems are auditable, testable, and reliable.

3. **Teeth over aspirations:** The AQI Chip doesn't just suggest ethical behavior — it enforces it. Violations are classified, tagged, logged, and reported. Every call produces a forensic record.

> "A constitution without enforcement is a wish list." — AQI Design Principle

## Further Reading

- [AQI Scientific Architecture](../AQI_SCIENTIFIC_ARCHITECTURE.md) — Full formal specification
- [AQI Organism Specification](../AQI_ORGANISM_SPEC.md) — Constitutional encoding
- [Constitution Articles](../ALAN_CONSTITUTION_ARTICLE_I.md) — Individual constitutional articles
- [Voice Contract](../ALAN_VOICE_CONTRACT.md) — Identity specification

---

*© 2025-2026 Timmy Jay Jones / SCSDMC. All rights reserved.*
