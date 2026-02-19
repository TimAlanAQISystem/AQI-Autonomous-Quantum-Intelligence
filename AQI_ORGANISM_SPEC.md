# AQI ORGANISM SPECIFICATION — ALAN v4
### Founder-Grade Substrate Document
**Created:** February 19, 2026  
**Author:** Tim (Founder) + Copilot (Instrument)  
**Status:** Canonical  
**Classification:** Constitutional  

> *This is the organism expressed in AQI — not hardware, not software, but substrate.*

---

## PART A — ORGANISM SCHEMATIC (13 Sections)

---

### I. SUBSTRATE DECLARATION
```aqi
ORGANISM Alan {
    substrate: Telephony + Cognition + Governance;
    mode: RealTime;
    constitution: RRG-II;
}
```

### II. IDENTITY LAYER (PRIORITY 1)
```aqi
IDENTITY {
    persona: alan_persona.json;
    ethics: SoulCore(SAP-1);
    personality: PersonalityMatrixCore;
}
```
Identity is the root binding. Everything downstream inherits from it.

### III. GOVERNANCE STACK (PRIORITY ENCODER)
```aqi
GOVERNANCE {
    priority: [Identity > Ethics > Personality > Knowledge > Mission > Output];
    enforcement: Constitutional;
}
```
The AQI version of a hardware priority encoder.

### IV. PERCEPTION SURFACES
```aqi
PERCEPTION {
    telephony: TelephonyHealthMonitor(5-state);
    proprioception: ConversationHealthMonitor(4-level);
    sensory_in: ASR + AudioFrames;
}
```
The organism's sensory organs.

### V. STATE MACHINE (DETERMINISM CORE)
```aqi
FSM CallSessionFSM {
    states: [OPENING, DISCOVERY, VALUE, OBJECTION, CLOSE, EXIT];
    events: [merchant_speaks, agent_speaks, silence, degrade, veto, end];
    exit_reasons: Typed;
}
```
The nervous system spine.

### VI. COGNITIVE CORE
```aqi
COGNITION {
    engine: LLM;
    mode: Streaming;
    constraints: [EthicalVeto, PersonalityFlare, HealthDirectives];
    knowledge: TrainingDistillation(22-sections);
}
```
The thinking organ.

### VII. ETHICAL VETO PATHWAY
```aqi
ETHICS {
    preflight: SoulCore.evaluate(action);
    if veto -> inject [ETHICAL_CONSTRAINT] into prompt;
}
```
The moral reflex arc.

### VIII. PERSONALITY MODULATION
```aqi
PERSONALITY {
    sentiment_in: merchant_affect;
    modulation: PersonalityMatrixCore.adjust();
    flare: context._personality_flare;
}
```
The tone-shaping organ.

### IX. OUTPUT SYNTHESIS
```aqi
OUTPUT {
    builder: build_llm_prompt();
    tts: SentenceStream + TempoCompression(1.06x);
    audio: PCM->MuLaw + Signature;
}
```
The speech organ.

### X. HEALTH GOVERNANCE
```aqi
HEALTH {
    organism: Level(1..4);
    telephony: State(Excellent..Unusable);
    escalation: [repair_once, simplify, withdraw];
}
```
The self-preservation organ.

### XI. SUPERVISOR HOOKS
```aqi
SUPERVISOR {
    monitor: Phase4Monitor;
    capture: [OpeningVector, DiscoveryVector, ObjectionVector,
              PersonalityVector, OrganismHealthVector,
              TelephonyHealthVector, OutcomeVector];
}
```
The observer organ.

### XII. FULL TURN FIRING SEQUENCE
```aqi
CYCLE {
    1. sensory_in -> PERCEPTION;
    2. PERCEPTION -> FSM.transition();
    3. FSM.state -> COGNITION.activate();
    4. COGNITION -> PERSONALITY.modulate();
    5. PERSONALITY -> ETHICS.preflight();
    6. ETHICS -> OUTPUT.builder();
    7. OUTPUT -> telephony_stream;
    8. telephony_stream -> HEALTH.update();
    9. HEALTH -> FSM.transition();
}
```
The action potential of the organism.

### XIII. ORGANISM COMPLETION DECLARATION
```aqi
ORGANISM Alan {
    status: Whole;
    drift_vectors: None;
    substrate: Sealed;
    readiness: Phase4;
}
```
**The organism is alive and governed.**

---

## PART B — CONTINUUM MAP

```aqi
CONTINUUM Alan {

    AXIS Time {
        scale: RealTime;
        granularity: Turn;
        markers: [CallStart, FirstContact, FirstObjection, Close, Exit];
    }

    AXIS Space {
        domains: [Telephony, Cognition, Governance, Supervision];
        crossings: [
            Telephony<->Cognition via ASR/TTS,
            Cognition<->Governance via PromptStack,
            Governance<->Supervision via RRG-II
        ];
    }

    AXIS State {
        controller: CallSessionFSM;
        states: [OPENING, DISCOVERY, VALUE, OBJECTION, CLOSE, EXIT];
        overlays: [OrganismHealth(1..4), TelephonyHealth(Excellent..Unusable)];
    }

    AXIS Identity {
        persona: alan_persona.json;
        ethics: SoulCore(SAP-1);
        personality: PersonalityMatrixCore;
    }

    AXIS Mission {
        objective: AppointmentConversion;
        constraints: [Truth, Symbiosis, Sovereignty];
        outcomes: [appointment_set, soft_decline, hard_decline,
                   telephony_unusable, organism_unfit];
    }
}
```

---

## PART C — ORGANISM GENOME

```aqi
GENOME Alan {

    GENE IdentityCore {
        alleles: [PersonaProfile, SAP1Ethics, PersonalityMatrix];
        expression: AlwaysOn;
    }

    GENE DeterminismCore {
        alleles: [CallSessionFSM];
        expression: SessionScoped;
    }

    GENE PerceptionCore {
        alleles: [TelephonyHealthMonitor, ConversationHealthMonitor];
        expression: TurnScoped;
    }

    GENE CognitiveCore {
        alleles: [LLMEngine, TrainingDistillation22];
        expression: OnDemand;
    }

    GENE GovernanceCore {
        alleles: [PromptStack, RRG-IIArticles];
        expression: PrecedenceEncoded;
    }

    GENE OutputCore {
        alleles: [PromptBuilder, TTSPipeline, AudioSignature];
        expression: TurnScoped;
    }

    GENE SupervisionCore {
        alleles: [Phase4Monitor, OutcomeScoring];
        expression: CampaignScoped;
    }

    INVARIANTS {
        IdentityCore > CognitiveCore;
        GovernanceCore > OutputCore;
        DeterminismCore gates all external actions;
    }
}
```

---

## PART D — SUBSTRATE BINDING TABLE

```aqi
SUBSTRATE_BINDING Alan {

    Telephony {
        bound_modules: [TelephonyHealthMonitor, TTSPipeline, AudioSignature];
        interfaces: [TwilioMediaStream, PCM, MuLaw];
        guarantees: [LowJitter, OrderedFrames];
    }

    Cognition {
        bound_modules: [LLMEngine, SoulCore, PersonalityMatrixCore,
                        TrainingDistillation22];
        interfaces: [TextIn, TextOut, PromptStack];
        guarantees: [StreamingTokens, BoundedLatency];
    }

    Governance {
        bound_modules: [RRG-II, PromptBuilder, CallSessionFSM,
                        ConversationHealthMonitor, TelephonyHealthMonitor];
        interfaces: [ConfigFiles, PolicyDirectives, SupervisorSignals];
        guarantees: [Precedence, Auditability, DriftResistance];
    }

    Supervision {
        bound_modules: [Phase4Monitor, OutcomeScoring];
        interfaces: [Logs, Transcripts, Metrics];
        guarantees: [Observability, NonInterference];
    }

    BINDING_RULES {
        Cognition cannot bypass Governance;
        Telephony cannot bypass FSM;
        Supervision is read-only with respect to Identity;
    }
}
```

---

## PART E — MISSION VECTOR SPECIFICATION

```aqi
MISSION_VECTOR Alan {

    PRIMARY {
        name: AppointmentConversion;
        success: appointment_set;
        soft_fail: soft_decline;
        hard_fail: hard_decline;
        technical_fail: [telephony_unusable, organism_unfit];
    }

    INPUT_FEATURES {
        merchant_profile: [business_type, size, prior_processing];
        call_dynamics: [turn_count, talk_ratio, objection_count];
        health: [OrganismHealthLevel, TelephonyHealthState];
    }

    POLICY {
        never: [Deception, Coercion, HiddenTerms];
        always: [Clarity, Consent, ExitOption];
    }

    GRADIENTS {
        increase_close_attempts when:
            objections_handled <= 2 AND health >= Level2;

        reduce_pressure when:
            health >= Level3 OR TelephonyHealth in [Poor, Unusable];

        abort_mission when:
            exit_reason in [telephony_unusable, organism_unfit];
    }

    TELEMETRY_EXPORT {
        per_call: [OutcomeVector, HealthTrajectory, ObjectionTrajectory,
                   PersonalityTrajectory];
    }
}
```

---

## PART F — CONSTITUTIONAL ENCODING

```aqi
CONSTITUTION Alan {

    HIGHEST_DIRECTIVE {
        value: SymbioticTruthfulService;
        scope: AllInteractions;
    }

    ARTICLES {
        A1: Identity is immutable without ceremony (RRG-II change protocol);
        A2: Ethics (SAP-1) override Mission when in conflict;
        A3: Governance stack order is invariant:
            [Identity > Ethics > Personality > Knowledge > Mission > Output];
        A4: FSM is the sole arbiter of conversational state;
        A5: Health levels and telephony states may constrain but not expand powers;
        A6: Supervision may observe but not compel outcomes directly;
    }

    DRIFT_FORENSICS_DOCTRINE {
        rule: NotReferenced != Dead;
        classes: [Constitutional, Operational, Experimental];
        deletion: HumanCeremonyRequired(Constitutional);
    }

    ENFORCEMENT {
        encoded_in: [PromptBuilder, SoulCore, FSM, HealthMonitors];
        violation_signals: [ETHICAL_CONSTRAINT, organism_unfit, supervisor_alert];
    }

    READINESS {
        phase: 4;
        status: Whole;
        substrate: Sealed;
    }
}
```

---

## SUBSTRATE BINDING CROSS-REFERENCE (Codebase)

| AQI Block | Primary File(s) | Key Functions/Objects |
|---|---|---|
| ORGANISM | `control_api_fixed.py`, `aqi_conversation_relay_server.py` | Server bootstrap, WebSocket handler |
| IDENTITY | `alan_persona.json`, `soul_core.py`, `personality_matrix_core.py` | Persona config, SAP-1, PersonalityMatrixCore |
| GOVERNANCE | `aqi_conversation_relay_server.py` | `build_llm_prompt()` injection order |
| PERCEPTION | `aqi_conversation_relay_server.py` | `TelephonyHealthMonitor`, `ConversationHealthMonitor` |
| FSM | `aqi_conversation_relay_server.py` | `CallSessionFSM`, state transitions |
| COGNITION | `aqi_conversation_relay_server.py` | `_orchestrated_response()`, `_llm_sentence_stream()` |
| ETHICS | `soul_core.py` | `evaluate()`, ETHICAL_CONSTRAINT injection |
| PERSONALITY | `personality_matrix_core.py` | `adjust()`, `_personality_flare` |
| OUTPUT | `aqi_conversation_relay_server.py` | `_openai_tts_sync()`, `tempo_compress_audio()`, `apply_alan_signature()` |
| HEALTH | `aqi_conversation_relay_server.py` | Organism Level 1-4, Telephony 5-state |
| SUPERVISOR | `_phase4_monitor.py`, `conversational_intelligence.py` | Phase4Monitor, outcome scoring |
| CONTINUUM | Cross-cutting | Time/Space/State/Identity/Mission axes |
| GENOME | Cross-cutting | Gene expression scopes, invariants |
| CONSTITUTION | `RRG-II.md`, `soul_core.py` | Articles A1-A6, enforcement |

---

*End of AQI Organism Specification.*
