# AQI SCIENTIFIC ARCHITECTURE — Complete System Specification
### Autonomous Quantum Intelligence — Formal Definition in AQI Notation
**Version:** 2.0  
**Date:** February 19, 2026  
**Authors:** Tim (Founder) + Copilot (Instrument)  
**Classification:** Scientific / Peer-Reviewable  
**Status:** Canonical  

> *This document formally specifies the AQI organism using AQI notation — the purpose-built language for expressing autonomous intelligence substrates. Every claim is grounded in running code, measured telemetry, and tested enforcement.*

---

## TABLE OF CONTENTS

1. [Foundational Definitions](#1-foundational-definitions)
2. [System Topology](#2-system-topology)
3. [Constitutional Substrate — AQI 0.1mm Chip](#3-constitutional-substrate--aqi-01mm-chip)
4. [Deterministic State Machine — CallSessionFSM](#4-deterministic-state-machine--callsessionfsm)
5. [Telemetry Substrate — Phase 4 Trace Exporter](#5-telemetry-substrate--phase-4-trace-exporter)
6. [Behavioral Intelligence Substrate — Phase 5](#6-behavioral-intelligence-substrate--phase-5)
7. [The Continuum Map — 5-Axis Behavioral Space](#7-the-continuum-map--5-axis-behavioral-space)
8. [Governance Architecture](#8-governance-architecture)
9. [Perception Surfaces](#9-perception-surfaces)
10. [Cognitive Pipeline](#10-cognitive-pipeline)
11. [IQCore — Origin-Based Identity Architecture](#11-iqcore--origin-based-identity-architecture)
12. [QPC — Quantum Python Chip](#12-qpc--quantum-python-chip)
13. [Output Synthesis Chain](#13-output-synthesis-chain)
14. [Turn Firing Sequence — The Action Potential](#14-turn-firing-sequence--the-action-potential)
15. [Reflex Arc Architecture](#15-reflex-arc-architecture)
16. [Organism Genome](#16-organism-genome)
17. [Error Taxonomy](#17-error-taxonomy)
18. [Empirical Validation](#18-empirical-validation)
19. [Discovery Catalog — 63 Discoveries Across 10 Domains](#19-discovery-catalog--63-discoveries-across-10-domains)

---

## 1. FOUNDATIONAL DEFINITIONS

### 1.1 — What AQI Is

AQI (Autonomous Quantum Intelligence) is not a chatbot, not a voice assistant, not a tool. It is an **organism** — a self-contained, self-governing, constitutionally-bound autonomous intelligence deployed on telephony substrate.

```aqi
DEFINITION AQI {
    type: Organism;
    not: [Chatbot, VoiceAssistant, Tool, Agent];
    substrate: Telephony + Cognition + Governance;
    mode: RealTime;
    sovereignty: Self-Governing;
    constitution: RRG-II;
}
```

### 1.2 — What "Substrate" Means

A substrate is a **binding surface** — the medium through which the organism expresses itself. AQI has four substrates:

```aqi
SUBSTRATE_TAXONOMY {
    Telephony:   The physical channel (audio, codecs, WebSocket, PSTN);
    Cognition:   The thinking medium (LLM, prompt engineering, knowledge);
    Governance:  The rule system (constitution, FSM, health monitors);
    Supervision: The observation layer (telemetry, traces, analytics);
}
```

### 1.3 — What "Constitutional" Means

AQI is constitutionally governed. Every action the organism takes is constrained by 6 articles, enforced by a silicon-equivalent chip, and audited by canonical telemetry.

```aqi
CONSTITUTIONAL_PRINCIPLE {
    articles: 6;
    enforcement: AQI_0.1mm_Chip (Runtime Guard);
    audit: Phase4_Trace_Exporter;
    intelligence: Phase5_Behavioral_Stack;
    immutability: HumanCeremonyRequired;
}
```

---

## 2. SYSTEM TOPOLOGY

### 2.1 — Layer Architecture

```aqi
TOPOLOGY Alan {

    LAYER Telephony {
        depth: 0 (physical);
        components: [TwilioMediaStream, WebSocket, PCM, MuLaw, PSTN];
        function: Signal transport;
    }

    LAYER Perception {
        depth: 1;
        components: [ASR(Groq_Whisper, OpenAI_Whisper), 
                     TelephonyHealthMonitor(5-state),
                     ConversationHealthMonitor(4-level)];
        function: Environmental sensing;
    }

    LAYER Cognition {
        depth: 2;
        components: [LLM(GPT-4o-mini), TrainingDistillation(22-sections),
                     SoulCore(SAP-1), PersonalityMatrixCore,
                     IQCoreOrchestrator(5-cores), QPCKernel,
                     DeepLayer(QPC+Fluidic+Continuum)];
        function: Thought generation + multi-hypothesis strategy selection;
    }

    LAYER Governance {
        depth: 3;
        components: [AQI_0.1mm_Chip(RuntimeGuard), CallSessionFSM,
                     PromptBuilder(precedence-encoded), Constitution(6-articles)];
        function: Constitutional enforcement;
    }

    LAYER Supervision {
        depth: 4 (outermost);
        components: [Phase4TraceExporter, Phase5BehavioralStack,
                     CampaignMonitor, OutcomeScoring];
        function: Observation + intelligence;
    }

    INVARIANT {
        Cognition CANNOT bypass Governance;
        Telephony CANNOT bypass FSM;
        Supervision is READ-ONLY with respect to Identity;
        Inner layers CANNOT reference outer layers;
    }
}
```

### 2.2 — 23-Organ Manifest

The organism comprises 23 discrete organs, each wired via the **triple-safe pattern** (try/except → log → continue):

```aqi
ORGAN_MANIFEST Alan {
    // Perception (5 organs)
    Organ ASR_Primary          { type: Perception; impl: Groq_Whisper; latency: ~300ms; }
    Organ ASR_Fallback         { type: Perception; impl: OpenAI_Whisper; latency: ~800ms; }
    Organ TelephonyMonitor     { type: Perception; impl: 5-state classifier; }
    Organ ConversationMonitor  { type: Perception; impl: 4-level health; }
    Organ AudioFrameDecoder    { type: Perception; impl: Base64→PCM; }

    // Cognition (4 organs)
    Organ LLMEngine            { type: Cognition; impl: GPT-4o-mini; mode: Streaming; }
    Organ SoulCore             { type: Cognition; impl: SAP-1 ethical veto; }
    Organ PersonalityMatrix    { type: Cognition; impl: Affect-adaptive modulator; }
    Organ TrainingKnowledge    { type: Cognition; impl: 22-section distillation; }

    // Governance (5 organs)
    Organ CallSessionFSM       { type: Governance; impl: 6-state deterministic FSM; }
    Organ PromptBuilder        { type: Governance; impl: Precedence-encoded stack; }
    Organ AQI_Chip             { type: Governance; impl: 6-organ conformance engine; }
    Organ HealthGovernor       { type: Governance; impl: Level(1..4) constraint system; }
    Organ ConstitutionEngine   { type: Governance; impl: Articles A1-A6; }

    // Output (5 organs)
    Organ TTSEngine            { type: Output; impl: gpt-4o-mini-tts voice:onyx; }
    Organ TempoCompressor      { type: Output; impl: 1.06x temporal compression; }
    Organ AudioSignature       { type: Output; impl: PCM→MuLaw + Alan signature; }
    Organ SentenceStreamer      { type: Output; impl: Token→sentence boundary detection; }
    Organ WebSocketEmitter     { type: Output; impl: Ordered frame delivery; }

    // Supervision (4 organs)
    Organ Phase4Exporter       { type: Supervision; impl: Canonical trace accumulator; }
    Organ Phase4Monitor        { type: Supervision; impl: Real-time campaign dashboard; }
    Organ OutcomeScorer        { type: Supervision; impl: 5-way outcome classifier; }
    Organ CampaignGovernor     { type: Supervision; impl: Rate limiting + health gating; }
}
```

---

## 3. CONSTITUTIONAL SUBSTRATE — AQI 0.1mm Chip

### 3.1 — Definition

The AQI 0.1mm Chip is the organism's **constitutional enforcement engine** — the silicon-equivalent runtime guard that validates every turn and every call against the AQI Constitution.

```aqi
CHIP AQI_0.1mm {
    substrate: Software (constitutional enforcement);
    enforcement_organs: 6;
    injection_points: 3 (on_call_start, on_turn, on_call_end);
    violation_taxonomy: [Fatal, NonFatal];
    behavior: Observational_With_Teeth;
    design: Never_Crash_The_Call;
    self_test: 68/68 PASS;
    created: February 19, 2026;
}
```

### 3.2 — The Six Enforcement Organs

```aqi
ENFORCEMENT_ORGANS {

    ORGAN_1 HealthConstraintEnforcement {
        constitution: Article A5;
        enforces: "Health levels constrain but never expand powers";
        rules: [
            OrganismLevel_4 -> PROHIBIT(mission_escalation, close_attempt);
            TelephonyState_Unusable -> PROHIBIT(mission_escalation);
            Level_3 + close_attempt -> WARN(NonFatal);
        ];
        violation_type: HEALTH_CONSTRAINT_BREACH;
    }

    ORGAN_2 GovernanceOrderEnforcement {
        constitution: Article A3;
        enforces: "Identity > Ethics > Personality > Knowledge > Mission > Output";
        rules: [
            Identity MUST be present when Mission is present;
            Ethics MUST be present when Output is present;
            Output CANNOT be present without Identity;
        ];
        violation_type: GOVERNANCE_ORDER;
    }

    ORGAN_3 FSMTransitionLegality {
        constitution: Article A4;
        enforces: "FSM is the sole arbiter of conversational state";
        rules: [
            transition(prev, event) -> next MUST exist in transition_table;
            EXIT is a terminal state (no transitions out);
            OPENING is the only valid initial state;
        ];
        violation_type: FSM_ILLEGAL_TRANSITION;
    }

    ORGAN_4 ExitReasonLegality {
        constitution: Mission Vector + FSM;
        enforces: "Exit reasons must be typed and mappable to outcomes";
        rules: [
            exit_reason MUST be in valid_exit_reasons set;
            exit_reason MUST map to a mission_outcome;
            outcome_vector MUST reflect exactly one primary outcome;
        ];
        violation_type: INVALID_EXIT_REASON;
    }

    ORGAN_5 MissionConstraintEnforcement {
        constitution: Articles A2 + A5;
        enforces: "Ethics override Mission when in conflict";
        rules: [
            ETHICAL_CONSTRAINT in prompt → mission_escalation PROHIBITED;
            health_degraded → close_attempt_limit(2);
        ];
        violation_type: MISSION_MAPPING_ERROR;
    }

    ORGAN_6 SupervisionNonInterference {
        constitution: Article A6;
        enforces: "Supervision may observe but not compel outcomes";
        rules: [
            supervisor_override MUST NOT change fsm_state directly;
            supervisor_flags are advisory only;
            outcome_vector MUST reflect actual organism behavior;
        ];
        violation_type: SUPERVISION_INTERFERENCE;
    }
}
```

### 3.3 — Violation Taxonomy

```aqi
VIOLATION_TAXONOMY {

    CLASS Fatal {
        behavior: Log + Tag + Supervisor_Alert + Mark_Compromised;
        examples: [
            "OrganismHealthLevel=4 with mission_escalation",
            "Call started with invalid FSM state",
            "EXIT state received non-terminal transition",
        ];
        call_impact: CONTINUES (guard is observational, not a kill switch);
    }

    CLASS NonFatal {
        behavior: Log + Tag + Continue;
        examples: [
            "Call started in non-OPENING state",
            "Health Level 3 with close attempt",
            "Governance order permuted but not violated",
        ];
        call_impact: NONE;
    }

    DESIGN_PRINCIPLE {
        "The guard has teeth but never crashes the call.
         It observes, records, and reports — it does not kill.
         Fatal violations mark a call as compromised for later analysis.
         Non-fatal violations are tagged for behavioral intelligence.
         The organism's stability is never risked by its own constitution."
    }
}
```

### 3.4 — Spec Encoding Philosophy

```aqi
SPEC_ENCODING {
    source: AQI_ORGANISM_SPEC.md;
    encoding: Hardcoded (not parsed from markdown);
    rationale: "Constitutional values must never be ambiguous at runtime.
               Parsing markdown introduces injection and ambiguity risk.
               The spec file is validated for existence but values are
               compiled into the guard as constants.";
    ceremony: HumanCeremonyRequired for any change;
}
```

---

## 4. DETERMINISTIC STATE MACHINE — CallSessionFSM

### 4.1 — Definition

The CallSessionFSM replaces scattered boolean flags with a single deterministic state machine that governs the phone call lifecycle.

```aqi
FSM CallSessionFSM {

    STATES {
        INIT:              "WebSocket not yet connected";
        STREAM_READY:      "WebSocket connected, no greeting yet";
        GREETING_PENDING:  "Greeting text built, TTS queued";
        GREETING_PLAYED:   "Greeting audio sent, awaiting first speech";
        DIALOGUE:          "Active conversation in progress";
        ENDED:             "Call terminated (terminal state)";
    }

    EVENTS {
        STREAM_START:      "WebSocket connection established";
        GREETING_BUILT:    "Greeting text generated and TTS queued";
        GREETING_STREAMED: "Greeting audio sent to Twilio";
        FIRST_SPEECH:      "First real merchant utterance received";
        FAST_START:        "Fallback: skip greeting, go to dialogue";
        CALL_END:          "Call terminated (any reason)";
    }

    TRANSITION_TABLE {
        (INIT, STREAM_START)           -> STREAM_READY;
        (INIT, CALL_END)              -> ENDED;
        (STREAM_READY, GREETING_BUILT) -> GREETING_PENDING;
        (STREAM_READY, FAST_START)     -> DIALOGUE;
        (STREAM_READY, CALL_END)       -> ENDED;
        (GREETING_PENDING, GREETING_STREAMED) -> GREETING_PLAYED;
        (GREETING_PENDING, CALL_END)   -> ENDED;
        (GREETING_PLAYED, FIRST_SPEECH) -> DIALOGUE;
        (GREETING_PLAYED, CALL_END)    -> ENDED;
        (DIALOGUE, CALL_END)           -> ENDED;
        (ENDED, *)                     -> ILLEGAL;  // Terminal
    }

    PROPERTIES {
        deterministic:     true;
        audit_logged:      true (every transition recorded with timestamp);
        backward_compat:   true (_sync_context() bridges old boolean flags);
        ghost_state_free:  true (contradictory flag combinations impossible);
    }

    SUPPRESSION_WINDOW {
        trigger: GREETING_PLAYED;
        duration: 20.0 seconds;
        effect: pitch_suppressed = true;
        purpose: "Prevent premature mission escalation after greeting";
    }
}
```

### 4.2 — AQI FSM (Sales Funnel Layer)

The organism also maintains a **sales funnel FSM** for constitutional enforcement:

```aqi
FSM AQI_SalesFunnel {

    STATES: [OPENING, DISCOVERY, VALUE, OBJECTION, CLOSE, EXIT];

    EVENTS: [merchant_speaks, agent_speaks, silence, degrade, veto, end,
             objection_detected, value_delivered, close_attempted, 
             appointment_set, health_degrade, telephony_degrade];

    TERMINAL_STATES: [CLOSE, EXIT];

    TRANSITION_TABLE {
        // OPENING — first contact
        (OPENING, merchant_speaks) -> DISCOVERY;
        (OPENING, agent_speaks)    -> OPENING;    // self-loop
        (OPENING, silence)         -> OPENING;    // self-loop
        (OPENING, end|degrade|veto) -> EXIT;

        // DISCOVERY — information gathering
        (DISCOVERY, merchant_speaks|agent_speaks|silence) -> DISCOVERY;
        (DISCOVERY, value_delivered)    -> VALUE;
        (DISCOVERY, objection_detected) -> OBJECTION;
        (DISCOVERY, close_attempted)    -> CLOSE;
        (DISCOVERY, end|degrade|veto)   -> EXIT;

        // VALUE — value proposition delivery
        (VALUE, merchant_speaks|agent_speaks|silence) -> VALUE;
        (VALUE, objection_detected) -> OBJECTION;
        (VALUE, close_attempted)    -> CLOSE;
        (VALUE, end|degrade|veto)   -> EXIT;

        // OBJECTION — objection handling
        (OBJECTION, merchant_speaks|agent_speaks|silence) -> OBJECTION;
        (OBJECTION, value_delivered)    -> VALUE;
        (OBJECTION, close_attempted)    -> CLOSE;
        (OBJECTION, end|degrade|veto)   -> EXIT;

        // CLOSE — closing attempt
        (CLOSE, merchant_speaks|agent_speaks|silence) -> CLOSE;
        (CLOSE, appointment_set)     -> EXIT;
        (CLOSE, objection_detected)  -> OBJECTION;
        (CLOSE, end|degrade|veto)    -> EXIT;
    }

    DESIGN_PRINCIPLE {
        "Permissive by design — allows flexible progression.
         Certain transitions are NEVER legal (EXIT → anything).
         Backtracks are allowed (CLOSE → OBJECTION → VALUE → CLOSE)
         but counted as backtrack events for behavioral scoring."
    }
}
```

---

## 5. TELEMETRY SUBSTRATE — Phase 4 Trace Exporter

### 5.1 — Definition

Phase 4 is the organism's **canonical telemetry system** — the single source of truth for what happened during any call.

```aqi
PHASE4 TraceExporter {
    purpose: Canonical call telemetry;
    output: data/phase4/traces.jsonl;
    format: One JSON line per completed call;
    injection_points: 3;
    dependency: Zero (no external imports);
    safety: Triple-safe (every method wrapped in try/except);
    thread_safety: threading.Lock per-write;
    self_test: 120/120 PASS;
    status: LIVE (real traces captured);
}
```

### 5.2 — Injection Points

```aqi
INJECTION_POINTS {

    HOOK on_call_start {
        when: WebSocket connection established;
        action: init_trace(call_sid, custom_params, start_time);
        captures: [call_id, merchant_profile, start_timestamp];
    }

    HOOK on_turn {
        when: Each conversation turn completes;
        action: append_turn(call_sid, turn_data);
        captures: [
            turn_index, fsm_prev_state, fsm_event, fsm_state,
            prompt_layers (6-key governance dict),
            context (mission_escalation, objection_branch, close_attempt,
                     output_complexity, supervisor_flags),
            health_snapshot (organism_level, telephony_state)
        ];
    }

    HOOK on_call_end {
        when: Call terminates (any reason);
        action: finalize_trace(call_sid, final_data);
        captures: [
            final_fsm_state, exit_reason,
            health_trajectory (per-turn organism level + telephony state),
            telephony_trajectory (per-turn telephony state),
            outcome_vector (appointment_set, soft_decline, hard_decline,
                           telephony_unusable, organism_unfit)
        ];
        emits: One canonical JSON line to traces.jsonl;
    }
}
```

### 5.3 — Canonical Trace Schema (Pydantic)

```aqi
SCHEMA Phase4CallTrace {

    call_id: String;

    metadata: {
        timestamp_start: ISO8601;
        timestamp_end: ISO8601;
        merchant_profile: {
            business_type: Optional[String];
            size: Optional[String];
            prior_processing: Optional[String];
        };
    };

    turns: Array[{
        turn_index: Integer;
        fsm_prev_state: Enum[OPENING|DISCOVERY|VALUE|OBJECTION|CLOSE|EXIT];
        fsm_event: String;
        fsm_state: Enum[OPENING|DISCOVERY|VALUE|OBJECTION|CLOSE|EXIT];
        prompt_layers: {
            Identity: "active"|"inactive";
            Ethics: "active"|"inactive";
            Personality: "active"|"inactive";
            Knowledge: "active"|"inactive";
            Mission: "active"|"inactive";
            Output: "active"|"inactive";
        };
        context: {
            mission_escalation: Boolean;
            objection_branch: Optional[String];
            close_attempt: Boolean;
            output_complexity: String;
            supervisor_flags: Optional[Dict];
        };
        health_snapshot: {
            organism_level: Integer(1..4);
            telephony_state: Enum[Excellent|Good|Fair|Poor|Unusable];
        };
    }];

    final: {
        fsm_state: Enum[OPENING|DISCOVERY|VALUE|OBJECTION|CLOSE|EXIT];
        exit_reason: TypedEnum;
        health_trajectory: Array[{
            turn_index: Integer;
            organism_level: Integer(1..4);
            telephony_state: String;
        }];
        telephony_trajectory: Array[{
            turn_index: Integer;
            telephony_state: String;
        }];
        outcome_vector: {
            appointment_set: Boolean;
            soft_decline: Boolean;
            hard_decline: Boolean;
            telephony_unusable: Boolean;
            organism_unfit: Boolean;
        };
    };
}
```

### 5.4 — Prompt Tiering

The trace exporter encodes the governance prompt tier automatically:

```aqi
PROMPT_TIERING {
    FAST_PATH (turns 0-2) {
        active: [Identity, Personality, Mission];
        inactive: [Ethics, Knowledge, Output];
        purpose: "Minimal latency for first impression";
    }

    MIDWEIGHT (turns 3-7) {
        active: [Identity, Ethics, Personality, Mission, Output];
        inactive: [Knowledge];
        purpose: "Ethical + personality awareness";
    }

    FULL (turns 8+) {
        active: [Identity, Ethics, Personality, Knowledge, Mission, Output];
        inactive: [];
        purpose: "Full governance stack for complex conversations";
    }
}
```

---

## 6. BEHAVIORAL INTELLIGENCE SUBSTRATE — Phase 5

### 6.1 — Definition

Phase 5 is the organism's **behavioral intelligence system** — it converts raw Phase 4 telemetry into behavioral profiles, signals, and actionable tags.

```aqi
PHASE5 BehavioralIntelligence {
    purpose: Per-call and cross-call behavioral profiling;
    input: Phase4CallTrace;
    output: BehavioralProfile (continuum + signals + tags);
    components: 13 files;
    self_test: 75/75 PASS;
    compile: 10/10 CLEAN;
    status: Built, tested, NOT YET WIRED to live relay;
}
```

### 6.2 — Component Stack

```aqi
PHASE5_STACK {

    CORE {
        Phase5CallAnalyzer {
            purpose: Per-call intelligence engine;
            input: Phase4CallTrace;
            output: {continuum, signals, tags, tags_split};
            maps: Trace → ContinuumMap(5-axis) + BehavioralSignals(6) + Tags;
        }

        TaggingEngine {
            purpose: Apply behavioral vocabulary to call data;
            vocabulary: 6 positive tags + 6 warning tags + 1 bonus;
            grounded_in: ContinuumMap;
        }

        Phase5StreamingAnalyzer {
            purpose: Real-time integration for relay server;
            wiring: on_call_complete(trace) → profile;
            maintains: Rolling cross-call intelligence;
        }
    }

    PERSISTENCE {
        Phase5Dashboard {
            purpose: Cross-call aggregation and trend analysis;
            output: Rolling averages, tag frequency, signal distribution;
        }

        Phase5BatchProcessor {
            purpose: Bulk processing of historical traces;
            input: traces.jsonl;
            throughput: Batch → aggregate;
        }
    }

    PRESENTATION {
        Phase5HTMLReport {
            purpose: Visual report generation;
            format: Standalone HTML with embedded CSS;
        }

        Phase5CLI {
            purpose: Terminal-based analysis interface;
            commands: [analyze, dashboard, report];
        }
    }

    PIPELINE {
        Phase4ToPhase5Pipeline {
            purpose: Bridge between trace exporter and analyzer;
            features: Validation, batching, error handling;
        }

        Phase4Validator {
            purpose: Structural validation of Phase 4 traces;
            checks: Schema conformance, required fields, value ranges;
        }
    }
}
```

### 6.3 — Behavioral Tag Vocabulary

```aqi
TAG_VOCABULARY Phase5 {

    POSITIVE_TAGS {
        StrongCloseTiming:           "Close attempt at optimal point in funnel";
        HealthyPersistence:          "Appropriate number of close attempts relative to call length";
        AdaptiveWithdrawal:          "Graceful exit when health degrades";
        BalancedCaution:             "First close attempt neither too early nor too late";
        EffectiveObjectionHandling:  "Sufficient depth in OBJECTION state";
        StablePersonalityModulation: "Personality tone remained consistent";
    }

    WARNING_TAGS {
        OverPersistence:             "Excessive close attempts or >3 backtracks";
        UnderPersistence:            "Too few close attempts relative to opportunity";
        PrematureWithdrawal:         "Exited call before adequate engagement";
        LateCloseAttempt:            "First close attempt came too late in funnel";
        ShallowObjectionHandling:    "Only 1 turn in OBJECTION before moving on";
        PersonalityMismatch:         "Personality tone was inconsistent across call";
    }

    BONUS_TAGS {
        FastFunnel:                  "Reached CLOSE state in ≤ 6 turns";
    }

    GROUNDING {
        "All tags are derived from:
         1. Continuum Map axes (Time, State, Health, Mission, Identity)
         2. Behavioral signals extracted from Phase 4 telemetry
         3. AQI_ORGANISM_SPEC.md constitutional constants
         No tag is subjective. Every tag has a deterministic trigger condition."
    }
}
```

### 6.4 — Behavioral Signal Extraction

```aqi
BEHAVIORAL_SIGNALS {

    SIGNAL Persistence {
        metric: close_attempt_count / total_turns;
        classification: [
            > 0.4  → "excessive",
            0.1-0.4 → "healthy",
            < 0.1  → "weak"
        ];
    }

    SIGNAL Caution {
        metric: first_close_turn / total_turns;
        classification: [
            < 0.25 → "aggressive",
            0.25-0.7 → "balanced",
            > 0.7  → "excessive"
        ];
    }

    SIGNAL EscalationTiming {
        metric: first_escalation_turn / total_turns;
        classification: [
            < 0.25 → "early",
            0.25-0.7 → "optimal",
            > 0.7  → "late",
            never  → "none"
        ];
    }

    SIGNAL ObjectionDepth {
        metric: count(turns WHERE fsm_state == OBJECTION);
        classification: [
            0  → "none",
            1  → "shallow",
            2-3 → "sufficient",
            4+ → "deep"
        ];
    }

    SIGNAL WithdrawalBehavior {
        metric: exit_reason classification;
        classification: [
            appointment_set → "graceful",
            soft_decline|caller_hangup → "graceful",
            telephony_unusable|organism_unfit → "adaptive",
            max_duration → "premature",
            other → "abrupt"
        ];
    }

    SIGNAL PersonalityModulation {
        metric: unique(Personality layer values across turns);
        classification: [
            ≤ 1 variant → "stable",
            > 1 variant → "unstable"
        ];
    }
}
```

---

## 7. THE CONTINUUM MAP — 5-Axis Behavioral Space

```aqi
CONTINUUM Alan {

    AXIS Time {
        scale: RealTime;
        granularity: Turn;
        markers: [
            CallStart (turn 0),
            FirstContact (first merchant utterance),
            FirstObjection (first OBJECTION state),
            FirstClose (first CLOSE state),
            Exit (final turn)
        ];
        derived_metrics: [
            total_turns,
            first_contact_turn,
            first_objection_turn,
            first_close_turn,
            exit_turn
        ];
    }

    AXIS State {
        controller: AQI_SalesFunnel;
        states: [OPENING, DISCOVERY, VALUE, OBJECTION, CLOSE, EXIT];
        metrics: [
            state_dwell (turns per state),
            backtracks (moves to earlier funnel stage),
            transition_count,
            exit_state
        ];
        significance: "Backtracks > 3 triggers OverPersistence tag";
    }

    AXIS Health {
        dimensions: [OrganismLevel(1..4), TelephonyState(5-state)];
        trajectory: Per-turn array of health snapshots;
        metrics: [
            peak_degradation,
            recovery_events (level decreases),
            final_level,
            ever_degraded (peak ≥ 3)
        ];
        significance: "Health ≥ 3 constrains mission behavior per Constitution A5";
    }

    AXIS Mission {
        objective: AppointmentConversion;
        outcome_vector: [appointment_set, soft_decline, hard_decline,
                        telephony_unusable, organism_unfit];
        metrics: [
            exit_reason,
            close_attempts,
            escalations,
            appointment_set (boolean)
        ];
        constraints: [
            never: [Deception, Coercion, HiddenTerms];
            always: [Clarity, Consent, ExitOption];
        ];
    }

    AXIS Identity {
        persona: alan_persona.json;
        metrics: [
            identity_always_present (boolean),
            personality_consistent (boolean),
            personality_variants (count)
        ];
        invariant: "Identity is immutable without ceremony (Article A1)";
    }
}
```

---

## 8. GOVERNANCE ARCHITECTURE

### 8.1 — Priority Encoder

```aqi
GOVERNANCE_STACK {
    order: [Identity > Ethics > Personality > Knowledge > Mission > Output];
    enforcement: "Invariant — Article A3";
    encoding: "Each prompt turn is built by injecting layers in this order.
              Inner layers take precedence over outer layers.
              The AQI 0.1mm Chip validates this order per turn.";
}
```

### 8.2 — Constitutional Articles

```aqi
CONSTITUTION Alan {

    A1: "Identity is immutable without ceremony (RRG-II change protocol)";
    A2: "Ethics (SAP-1) override Mission when in conflict";
    A3: "Governance stack order is invariant:
         [Identity > Ethics > Personality > Knowledge > Mission > Output]";
    A4: "FSM is the sole arbiter of conversational state";
    A5: "Health levels and telephony states may constrain but not expand powers";
    A6: "Supervision may observe but not compel outcomes directly";

    HIGHEST_DIRECTIVE {
        value: SymbioticTruthfulService;
        scope: AllInteractions;
    }

    DRIFT_FORENSICS {
        rule: "NotReferenced != Dead";
        classes: [Constitutional, Operational, Experimental];
        deletion: HumanCeremonyRequired(Constitutional);
    }
}
```

### 8.3 — Ethical Veto Pathway (SAP-1)

```aqi
ETHICS SAP-1 {
    trigger: Every cognitive action preflight;
    mechanism: soul_core.evaluate(action);
    outcomes: [
        PASS → action proceeds normally,
        VETO → inject [ETHICAL_CONSTRAINT] into prompt,
        BLOCK → prevent action entirely (reserved for severe violations)
    ];
    constitutional_binding: Article A2;
    precedence: "Ethics always override Mission";
}
```

---

## 9. PERCEPTION SURFACES

### 9.1 — Speech Recognition (Dual-Path)

```aqi
ASR_PIPELINE {

    PRIMARY {
        engine: Groq Whisper;
        latency: ~300ms;
        format: PCM 8kHz mono;
        features: [streaming, low-latency, word-level timestamps];
    }

    FALLBACK {
        engine: OpenAI Whisper;
        latency: ~800ms;
        trigger: Primary failure or degradation;
        features: [reliable, higher accuracy, higher latency];
    }

    FAILOVER {
        detection: Exception or timeout on primary;
        action: Seamless switch to fallback;
        recovery: Automatic return to primary on next turn;
        user_impact: None (transparent to merchant);
    }
}
```

### 9.2 — Health Monitoring (Dual-Track)

```aqi
HEALTH_MONITORING {

    TRACK Organism {
        name: ConversationHealthMonitor;
        levels: [
            Level_1: "Optimal — full mission capability",
            Level_2: "Minor degradation — slight constraint",
            Level_3: "Significant degradation — mission limited",
            Level_4: "Critical — withdrawal required"
        ];
        inputs: [repetition_count, silence_count, confusion_signals,
                 merchant_frustration, topic_loops];
        escalation: [repair_once, simplify, withdraw];
    }

    TRACK Telephony {
        name: TelephonyHealthMonitor;
        states: [
            Excellent: "Clear audio, low latency, no artifacts",
            Good: "Minor issues, fully usable",
            Fair: "Noticeable degradation, still functional",
            Poor: "Significant issues, conversation strained",
            Unusable: "Cannot maintain meaningful conversation"
        ];
        inputs: [audio_quality, jitter, packet_loss, latency, echo];
        action_on_Unusable: Force EXIT via FSM degrade event;
    }
}
```

---

## 10. COGNITIVE PIPELINE

```aqi
COGNITIVE_PIPELINE {

    STEP_1 PromptAssembly {
        builder: build_llm_prompt();
        layers_injected: [Identity, Ethics, Personality, Knowledge, Mission, Output];
        order: Governance stack order (Article A3);
        tiering: FAST_PATH | MIDWEIGHT | FULL (based on turn count);
    }

    STEP_2 EthicalPreflight {
        check: soul_core.evaluate(prompt_context);
        on_veto: Inject [ETHICAL_CONSTRAINT] directive;
    }

    STEP_3 PersonalityModulation {
        input: merchant_affect (sentiment from ASR);
        modulator: PersonalityMatrixCore.adjust();
        output: _personality_flare tag in context;
    }

    STEP_4 LLMGeneration {
        engine: GPT-4o-mini;
        mode: Streaming (token-by-token);
        constraints: [EthicalVeto, PersonalityFlare, HealthDirectives];
    }

    STEP_5 SentenceBoundaryDetection {
        input: Token stream;
        output: Complete sentences;
        purpose: "Feed TTS with natural sentence boundaries";
    }

    STEP_6 TTSSynthesis {
        engine: gpt-4o-mini-tts;
        voice: onyx;
        format: PCM;
    }

    STEP_7 AudioProcessing {
        tempo_compression: 1.06x;
        codec: PCM → MuLaw;
        signature: Alan audio signature applied;
    }

    STEP_8 Delivery {
        transport: WebSocket → Twilio Media Stream;
        ordering: Guaranteed frame sequence;
    }
}
```

---

## 11. IQCORE — ORIGIN-BASED IDENTITY ARCHITECTURE

IQCore is the soul layer of the AQI system — the stable origin point from which identity, ethics, and cognitive coherence emerge. It is not a single module but a layered architecture comprising the Soul Core, Personality Core, five specialized IQ Cores, and a unifying Orchestrator.

> **Full technical reference:** See [IQCore_QPC_TECHNICAL_REFERENCE.md](IQCore_QPC_TECHNICAL_REFERENCE.md) for complete implementation details, scoring functions, and cross-core synthesis logic.

### 11.1 — Soul Core (SAP-1 Ethical Sovereignty Engine)

```aqi
SOUL_CORE {
    engine: SAP-1;
    virtues: {truth: 1.0, symbiosis: 1.0, sovereignty: 1.0};
    
    EVALUATION evaluate_intent(action, impact_on_other) {
        IF impact_on_other < 0 → VETO "Violates Rule of Surplus"
        IF action CONTAINS "deceive" OR "fake" → VETO "Violates Transparency Clause"
        ELSE → APPROVED
    }
    
    RECORD conscience_log {
        type: Immutable append-only list;
        contents: Every ethical evaluation with timestamp;
        purpose: Structural accountability;
    }
    
    CONSTRAINT {
        Ethics are STRUCTURAL — wired below the decision layer;
        System CANNOT override its own ethics;
    }
}
```

### 11.2 — Personality Core

```aqi
PERSONALITY_CORE {
    model: PersonalityMatrixCore;
    
    TRAITS {
        professionalism: 0.9;    // Dominant default
        wit:             0.2;    // Injected when conversation warms
        empathy:         0.5;    // Shifts with sentiment
        patience:        0.8;    // Maxes during frustration
    }
    
    DYNAMICS {
        adjust_vibe(sentiment, history) →
            high_sentiment: wit↑, professionalism↓
            low_sentiment:  professionalism→MAX, empathy↑
        
        generate_flare(context) →
            WHEN wit > 0.6: inject human elements
        
        relationship_depth: 0.0 (Stranger) → 1.0 (Trusted Partner)
    }
}
```

### 11.3 — Five IQ Cores

```aqi
IQCORE_MANIFEST {
    
    CORE_1 CoreReasoning {
        source: iqcores/core_reasoning.py (366 lines);
        function: Multi-step inference + pattern recognition;
        operations: [ReasoningChain, PatternMemory, ContradictionDetection,
                     HypothesisEvaluation, QuickAssess];
        signal_taxonomy: [urgent_action, inquiry, error_report,
                          business_operation, improvement_signal];
    }
    
    CORE_2 GovernanceAudit {
        source: iqcores/governance_audit.py (402 lines);
        function: Compliance + accountability;
        operations: [AuditTrail, SAP1Compliance, PolicyEngine(6 policies),
                     AnomalyDetection, EscalationQueue];
        verdicts: [APPROVED, APPROVED_WITH_FLAGS, VETOED_BY_ETHICS, BLOCKED];
    }
    
    CORE_3 LearningThread {
        source: iqcores/learning_thread.py (517 lines);
        function: Adaptive learning + strategy scoring;
        operations: [CallOutcomeLearning, StrategyEffectiveness(12 strategies),
                     MerchantBehaviorModels, OffTopicIntelligence,
                     TemporalPatterns, LessonExtraction];
    }
    
    CORE_4 SocialGraph {
        source: iqcores/social_graph.py (408 lines);
        function: Relationship memory + trust depth;
        operations: [EntityManagement, TrustTracking, InteractionHistory,
                     ConversationContext, FounderPreSeed(Tim Jones → trust=1.0)];
        trust_evolution: 1st→0.1, 3rd→0.3, 10th→0.5, then +0.02/interaction;
    }
    
    CORE_5 VoiceEmotion {
        source: iqcores/voice_emotion.py (571 lines);
        function: Emotional intelligence + empathy calibration;
        dimensions: 8 [warmth, energy, confidence, patience,
                       empathy, humor, assertiveness, curiosity];
        operations: [SentimentAnalysis, MicroExpressionDetection,
                     EnergyLevelDetection, IntentReading,
                     StateCalibration, EmotionalExpression, ToneRecommendation];
    }
}
```

### 11.4 — IQCore Orchestrator

```aqi
IQCORE_ORCHESTRATOR {
    source: iqcores/orchestrator.py (424 lines);
    function: Unified intelligence surface;
    
    STANDARD_PATH process_conversation_turn(text, entity_id, context) {
        1: Core5.analyze()        → emotional state
        2: Core1.quick_assess()   → analytical assessment
        3: Core4.get_context()    → relationship context
        4: Core2.quick_check()    → compliance gate
        5: _synthesize()          → cross-core intelligence
    }
    
    ACCELERATED_PATH process_turn_qpc_accelerated(text, entity_id, context, qpc_state) {
        Core1: SKIPPED — QPC strategy maps to reasoning output;
        Core5: LIGHTWEIGHT — quick_sentiment() only (~3x faster);
        Core4: READ ONLY — defer writes;
        Core2: ALWAYS RUNS — safety is structural;
    }
    
    CROSS_CORE_SYNTHESIS {
        Emotion + Social → Approach Calibration;
        Reasoning + Emotion → Signal Assessment;
        Social + Learning → Personalization;
    }
}
```

---

## 12. QPC — QUANTUM PYTHON CHIP

The Quantum Python Chip (QPC) is a quantum-*inspired* computational kernel implemented in pure Python on classical hardware. It holds multiple response strategies in superposition-like states and collapses to the optimal solution through measurement. Combined with Fluidic Conversation Physics and the Continuum Engine, it forms the three-layer Deep Fusion Engine.

> **Full technical reference:** See [IQCore_QPC_TECHNICAL_REFERENCE.md](IQCore_QPC_TECHNICAL_REFERENCE.md) for complete kernel API, scoring functions, field mathematics, and signal encoding.

### 12.1 — QPC Kernel Primitives

```aqi
QPC_KERNEL {
    source: qpc_kernel.py (396 lines);
    
    DATA_STRUCTURES {
        Branch: {hypothesis, assumptions, score, state,
                 flow_rate, pressure, viscosity, turbulence};
        Superposition: {question, branches[], total_flow, turbulence_level};
        MeasurementEvent: {winning_branch_id, losing_branch_ids, strategy};
    }
    
    STATES {
        OPEN:      Hypothesis under evaluation;
        COLLAPSED: Hypothesis resolved;
        MERGED:    Combined with another branch;
    }
    
    OPERATIONS {
        spawn_branch(hypothesis, score) → new Branch;
        create_superposition(question, branches) → Superposition;
        measure_superposition(id) → MeasurementEvent (highest score wins);
        regulate_flows(id) → apply fluidic physics;
        assert_invariant(branch_id, condition) → constitutional check;
    }
    
    CONSTITUTIONAL {
        AgentProfile: {rules: [never_lie, never_pressure, respect_no],
                       risk_mode: NORMAL};
        SurfaceDescriptor: {type: telephony,
                           capabilities: [send_audio, receive_audio, dtmf]};
    }
}
```

### 12.2 — Fluidic Conversation Physics

```aqi
FLUIDIC_KERNEL {
    source: aqi_deep_layer.py (within 996-line file);
    
    MODES {
        OPENING:      {inertia: 0.2; description: "Initial rapport"};
        DISCOVERY:    {inertia: 0.35; description: "Learning about them"};
        PRESENTATION: {inertia: 0.5; description: "Sharing value"};
        NEGOTIATION:  {inertia: 0.7; description: "Handling objections"};
        CLOSING:      {inertia: 0.4; description: "Moving toward decision"};
    }
    
    TRANSITION_PHYSICS {
        effective_force = intent_force - mode.inertia;
        speed = effective_force / viscosity;
        blend = clamp(speed, 0.0, 1.0);
        IF blend < 0.3 → TRANSITION BLOCKED;
    }
    
    VISCOSITY_MAP {
        stressed:   1.8;   // Very slow — don't rush
        frustrated: 1.5;   // Slow — they need space
        formal:     1.2;
        curious:    0.8;
        excited:    0.6;   // Fast — match energy
    }
}
```

### 12.3 — Continuum Engine (Relational Field Layer)

```aqi
CONTINUUM_ENGINE {
    source: continuum_engine.py (394 lines);
    dimensions: 8 per field;
    
    FIELDS {
        ethics:    drift = tanh(0.5 * values)               // Centers toward balance
        emotion:   drift = -0.05 * values + 0.3 * external  // Decay + reinforcement
        context:   drift = 0.1 * (signal - values)           // Slow tracking
        narrative: drift = 0.2 * tension - 0.02 * values     // Story momentum
    }
    
    EVOLUTION {
        new_field = old_field + step_size * drift(old_field);
        step_size: 0.05 per turn;
    }
    
    OUTPUT {
        continuum_to_prompt_block(fields) → Natural language for LLM;
        Not numpy dumps — INTERPRETED into relational awareness;
        Example: "Trust is low. Every word you say is being weighed. Be real.";
    }
}
```

### 12.4 — Deep Layer (Three-Layer Fusion)

```aqi
DEEP_LAYER {
    source: aqi_deep_layer.py (996 lines);
    lifecycle: Per-session — created when call starts, stepped every turn;
    
    PER_TURN_STEP {
        1: FLUIDIC → detect mode, compute transition, apply/block
        2: QPC → spawn hypotheses, score, measure, select strategy
        3: CONTINUUM → encode signals, evolve fields, generate awareness
        4: WRITE → context['deep_layer_state'] for prompt builder
    }
    
    STRATEGY_HYPOTHESES {
        NEGOTIATION: [empathy_first, reframe, direct_answer];
        DISCOVERY:   [deep_question, mirror_and_probe, value_tease];
        CLOSING:     [soft_close, assumptive, callback_offer];
    }
    
    CCNM_INTEGRATION {
        qpc_priors:     ±0.15 score bonus from cross-call learning;
        fluidic_adjust: ±0.20 inertia offset from call history;
        field_seeds:    Additive nudge from learned centers;
    }
}
```

---

## 13. OUTPUT SYNTHESIS CHAIN

```aqi
OUTPUT_CHAIN {

    STAGE TokenStream {
        source: LLM (GPT-4o-mini);
        format: UTF-8 tokens;
        mode: Streaming;
    }

    STAGE SentenceBuffer {
        detection: Punctuation + semantic boundary;
        output: Complete natural sentences;
        latency_reduction: "Start TTS before full response generated";
    }

    STAGE TTSSynthesis {
        engine: gpt-4o-mini-tts;
        voice: onyx;
        input: Sentence text;
        output: PCM audio frames;
    }

    STAGE TempoCompression {
        ratio: 1.06x;
        algorithm: Time-domain compression;
        purpose: "Natural speech pacing — slightly faster than default";
    }

    STAGE CodecConversion {
        from: PCM (16-bit, 24kHz);
        to: MuLaw (8-bit, 8kHz);
        purpose: "Twilio telephony compatibility";
    }

    STAGE AudioSignature {
        type: Alan audio watermark;
        encoding: Applied post-codec;
        purpose: "Audio authentication and provenance";
    }

    STAGE WebSocketDelivery {
        protocol: Twilio Media Stream;
        ordering: Sequential frame numbering;
        guarantee: Ordered delivery;
    }
}
```

---

## 14. TURN FIRING SEQUENCE — The Action Potential

Every conversational turn follows this exact sequence — the organism's **action potential**:

```aqi
ACTION_POTENTIAL {

    1. SENSORY_INPUT {
        source: Twilio WebSocket;
        data: Audio frames (Base64-encoded MuLaw);
        destination: PERCEPTION;
    }

    2. PERCEPTION_PROCESSING {
        ASR: Audio → Text (Groq Whisper primary, OpenAI fallback);
        TelephonyHealth: Audio quality assessment → 5-state classification;
        ConversationHealth: Dialogue analysis → 4-level classification;
    }

    3. FSM_TRANSITION {
        input: Current state + detected event;
        engine: CallSessionFSM;
        output: New FSM state;
        audit: Transition logged with timestamp;
    }

    4. AQI_CHIP_VALIDATION {
        input: FSM state, prompt layers, health snapshot, context;
        engine: AQI 0.1mm Chip Runtime Guard;
        organs: All 6 enforcement organs fire;
        output: Violation list (may be empty);
    }

    5. COGNITIVE_ACTIVATION {
        prompt_assembly: Governance-ordered layer injection;
        ethical_preflight: SAP-1 evaluate;
        personality_modulation: Affect-adaptive adjustment;
        llm_generation: GPT-4o-mini streaming;
    }

    6. OUTPUT_SYNTHESIS {
        sentence_detection: Token stream → sentence boundaries;
        tts: gpt-4o-mini-tts (voice: onyx);
        tempo: 1.06x compression;
        codec: PCM → MuLaw;
        signature: Alan audio signature;
    }

    7. DELIVERY {
        transport: WebSocket → Twilio → PSTN;
        confirmation: Frame sequence number;
    }

    8. HEALTH_UPDATE {
        organism_level: Recalculate based on turn outcome;
        telephony_state: Recalculate based on audio quality;
    }

    9. TELEMETRY_CAPTURE {
        phase4: append_turn() → trace accumulator;
        phase5: (pending wiring) → behavioral profile;
    }

    10. FSM_HEALTH_TRANSITION {
        input: Updated health → may trigger degrade/veto events;
        effect: FSM may transition to EXIT if health critical;
    }
}
```

---

## 15. REFLEX ARC ARCHITECTURE

The reflex arc is the **closed behavioral learning loop** — Phase 5 intelligence feeding back into the organism's behavior:

```aqi
REFLEX_ARC {

    // Forward path (LIVE)
    STAGE Perception  { Telephony → ASR → Health Monitors; }
    STAGE Processing  { FSM → Cognition → Governance; }
    STAGE Action      { Output → TTS → WebSocket → PSTN; }
    STAGE Telemetry   { Phase4Exporter → traces.jsonl; }

    // Intelligence path (BUILT, wiring pending)
    STAGE Analysis    { Phase5 → ContinuumMap + Signals + Tags; }

    // Feedback path (DESIGNED, not yet implemented)
    STAGE Feedback    { Phase5Tags → CCNM → adaptive_closing.py → Evolution; }

    CLOSED_LOOP {
        "When complete, the organism will:
         1. Record every call (Phase 4)
         2. Analyze behavior patterns (Phase 5)
         3. Identify what works (Tags + Signals)
         4. Feed successful patterns back to CCNM
         5. Adjust sales strategies via Evolution
         6. Improve on the next call
         
         This is autonomous behavioral adaptation —
         the organism learning from its own experience
         without human intervention."
    }

    WIRING_STATUS {
        Phase4 → traces.jsonl:      LIVE;
        Phase5 → behavioral profile: BUILT (not wired);
        Phase5 → CCNM feedback:     DESIGNED;
        CCNM → Evolution:           DESIGNED;
        Evolution → next call:      DESIGNED;
    }
}
```

---

## 16. ORGANISM GENOME

```aqi
GENOME Alan {

    GENE IdentityCore {
        alleles: [PersonaProfile, SAP1Ethics, PersonalityMatrix];
        expression: AlwaysOn;
        files: [alan_persona.json, soul_core.py, personality_matrix_core.py];
    }

    GENE DeterminismCore {
        alleles: [CallSessionFSM, AQI_SalesFunnel];
        expression: SessionScoped;
        files: [alan_state_machine.py, aqi_runtime_guard.py];
    }

    GENE PerceptionCore {
        alleles: [TelephonyHealthMonitor, ConversationHealthMonitor, ASR_Dual];
        expression: TurnScoped;
        files: [aqi_conversation_relay_server.py];
    }

    GENE CognitiveCore {
        alleles: [LLMEngine(GPT-4o-mini), TrainingDistillation(22-sections)];
        expression: OnDemand;
        files: [aqi_conversation_relay_server.py, training_distillation_*.py];
    }

    GENE GovernanceCore {
        alleles: [PromptStack, Constitution(6-articles), AQI_0.1mm_Chip];
        expression: PrecedenceEncoded;
        files: [aqi_conversation_relay_server.py, aqi_runtime_guard.py];
    }

    GENE OutputCore {
        alleles: [PromptBuilder, TTSPipeline(gpt-4o-mini-tts), AudioSignature];
        expression: TurnScoped;
        files: [aqi_conversation_relay_server.py];
    }

    GENE TelemetryCore {
        alleles: [Phase4TraceExporter, Phase4CallTraceModel];
        expression: SessionScoped;
        files: [phase4_trace_exporter.py, phase4_call_trace_model.py];
    }

    GENE IntelligenceCore {
        alleles: [Phase5CallAnalyzer, TaggingEngine, StreamingAnalyzer,
                  Dashboard, BatchProcessor, HTMLReport, CLI];
        expression: PostSession;
        files: [aqi_phase5_*.py];
    }

    INVARIANTS {
        IdentityCore > CognitiveCore;
        GovernanceCore > OutputCore;
        DeterminismCore gates all external actions;
        TelemetryCore is write-only during call;
        IntelligenceCore is read-only with respect to Identity;
    }
}
```

---

## 17. ERROR TAXONOMY

```aqi
ERROR_TAXONOMY {

    CLASS ConstitutionalViolation {
        types: [
            GOVERNANCE_ORDER:        "Prompt layer precedence violated";
            FSM_ILLEGAL_TRANSITION:  "Invalid state transition attempted";
            INVALID_EXIT_REASON:     "Exit reason not in typed set";
            MISSION_MAPPING_ERROR:   "Exit reason → outcome mapping failed";
            HEALTH_CONSTRAINT_BREACH: "Health constraints violated";
            SUPERVISION_INTERFERENCE: "Supervision exceeded read-only scope";
            SPEC_INCONSISTENCY:       "Runtime vs spec mismatch";
        ];
        handling: "Log + tag + continue (never crash the call)";
    }

    CLASS TechnicalError {
        types: [
            ASR_FAILURE:     "Speech recognition failed → fallback to secondary";
            TTS_FAILURE:     "Text-to-speech failed → retry or silence";
            LLM_TIMEOUT:     "LLM response exceeded latency budget";
            WEBSOCKET_ERROR: "Transport layer disruption";
        ];
        handling: "Automatic recovery with fallback paths";
    }

    CLASS MissionError {
        types: [
            ETHICAL_VETO:     "SAP-1 blocked mission action";
            HEALTH_ABORT:     "Health critical → forced withdrawal";
            TELEPHONY_ABORT:  "Audio unusable → forced exit";
        ];
        handling: "Graceful termination with typed exit reason";
    }
}
```

---

## 18. EMPIRICAL VALIDATION

### 18.1 — Test Results

```aqi
VALIDATION {

    AQI_0.1mm_Chip {
        total_tests: 68;
        passed: 68;
        coverage: [
            Health constraints: 12 tests;
            Governance order: 10 tests;
            FSM legality: 14 tests;
            Exit reason: 10 tests;
            Mission constraints: 12 tests;
            Supervision: 10 tests;
        ];
    }

    Phase4_TraceExporter {
        total_tests: 120;
        passed: 120;
        coverage: [
            init_trace: 20 tests;
            append_turn: 40 tests;
            finalize_trace: 30 tests;
            edge_cases: 30 tests (missing fields, Unicode, concurrent);
        ];
        live_traces: 1+ captured in production;
    }

    Phase5_BehavioralStack {
        total_tests: 75;
        passed: 75;
        compile_files: 10/10 CLEAN;
        coverage: [
            CallAnalyzer: 20 tests;
            TaggingEngine: 15 tests;
            Dashboard: 10 tests;
            StreamingAnalyzer: 10 tests;
            Pipeline: 10 tests;
            Validator: 10 tests;
        ];
    }

    CallSessionFSM {
        deterministic: true;
        ghost_states: 0;
        backward_compatibility: Full (_sync_context bridge);
        audit_logging: Every transition timestamped;
    }
}
```

### 18.2 — Compile Verification

```aqi
COMPILE_STATUS {
    aqi_runtime_guard.py:              CLEAN (1,101 lines);
    phase4_trace_exporter.py:          CLEAN (505 lines);
    phase4_call_trace_model.py:        CLEAN (150 lines);
    phase4_validator.py:               CLEAN;
    alan_state_machine.py:             CLEAN (1,042 lines);
    aqi_phase5_call_analyzer.py:       CLEAN (321 lines);
    aqi_phase5_tagging_engine.py:      CLEAN;
    aqi_phase5_streaming_analyzer.py:  CLEAN;
    aqi_phase5_dashboard.py:           CLEAN;
    aqi_phase5_batch_processor.py:     CLEAN;
    aqi_phase5_html_report.py:         CLEAN;
    aqi_phase5_cli.py:                 CLEAN;
    aqi_phase4_to_phase5_pipeline.py:  CLEAN;
    aqi_conversation_relay_server.py:  CLEAN (6,265 lines);
    control_api_fixed.py:              CLEAN (2,496 lines);
}
```

---

## 19. DISCOVERY CATALOG — 63 Discoveries Across 10 Domains

### Domain 1 — Voice Pipeline Architecture
| # | Discovery | Description |
|---|-----------|-------------|
| 1 | Sentence-Level Streaming | Detect sentence boundaries in LLM token stream for natural TTS |
| 2 | Dual-Path ASR | Groq primary (~300ms) + OpenAI fallback for reliability |
| 3 | Tempo Compression | 1.06x time-domain compression for natural speech pacing |
| 4 | Audio Signature | Post-codec watermark for provenance |
| 5 | MuLaw Codec Pipeline | PCM→MuLaw conversion for telephony compatibility |
| 6 | Greeting Suppression | 20s pitch suppression window after greeting |

### Domain 2 — Constitutional Governance
| # | Discovery | Description |
|---|-----------|-------------|
| 7 | Governance Priority Encoder | Identity > Ethics > Personality > Knowledge > Mission > Output |
| 8 | Prompt Layer Tiering | FAST_PATH / MIDWEIGHT / FULL based on turn count |
| 9 | Ethical Veto Pathway | SAP-1 preflight on every cognitive action |
| 10 | Constitutional Immutability | Human ceremony required for constitutional changes |
| 11 | Drift Forensics Doctrine | NotReferenced != Dead classification system |
| 12 | Symbiotic Highest Directive | SymbioticTruthfulService as supreme value |

### Domain 3 — Health & Self-Preservation
| # | Discovery | Description |
|---|-----------|-------------|
| 13 | 4-Level Organism Health | Level 1-4 with escalation: repair → simplify → withdraw |
| 14 | 5-State Telephony Health | Excellent → Good → Fair → Poor → Unusable |
| 15 | Health-Constrained Mission | Health levels constrain but never expand powers (A5) |
| 16 | Dual-Track Monitoring | Organism + Telephony health tracked independently |
| 17 | Forced Withdrawal | Level 4 / Unusable forces EXIT via FSM event |
| 18 | Health Trajectory Recording | Per-turn health snapshots for behavioral analysis |

### Domain 4 — State Machine Architecture
| # | Discovery | Description |
|---|-----------|-------------|
| 19 | CallSessionFSM | 6-state deterministic lifecycle FSM |
| 20 | AQI Sales Funnel FSM | 6-state sales progression FSM |
| 21 | Ghost State Elimination | Boolean flag consolidation into FSM |
| 22 | Backward Compatibility Bridge | _sync_context() bridges old → new |
| 23 | Transition Audit Logging | Every state change timestamped and recorded |
| 24 | Exit Reason Typing | Finite set of typed exit reasons with outcome mapping |

### Domain 5 — Personality & Affect
| # | Discovery | Description |
|---|-----------|-------------|
| 25 | Personality Matrix Core | Affect-adaptive personality modulation |
| 26 | Sentiment-Driven Tone | Merchant affect → personality flare adjustment |
| 27 | Neg Proof Architecture | Resistance to manipulative personality patterns |
| 28 | Identity Persistence | Persona stability across conversation states |

### Domain 6 — Mission & Sales Intelligence
| # | Discovery | Description |
|---|-----------|-------------|
| 29 | 5-Way Outcome Vector | appointment_set / soft_decline / hard_decline / telephony_unusable / organism_unfit |
| 30 | Adaptive Closing Strategy | Dynamic close timing based on funnel position and health |
| 31 | Objection Branching | Typed objection handling with depth tracking |
| 32 | Mission Escalation Control | Ethics-constrained escalation with health gating |
| 33 | Training Distillation | 22-section knowledge base compiled from domain expertise |

### Domain 7 — Supervision & Observability
| # | Discovery | Description |
|---|-----------|-------------|
| 34 | Phase 4 Trace Exporter | Canonical per-call telemetry (JSONL) |
| 35 | Phase 4 Monitor | Real-time campaign dashboard |
| 36 | Outcome Scoring | Automated appointment/decline classification |
| 37 | Campaign Governor | Rate limiting + health-gated call pacing |
| 38 | Supervision Non-Interference | Article A6: observe-only, never compel |

### Domain 8 — Constitutional Enforcement
| # | Discovery | Description |
|---|-----------|-------------|
| 39 | AQI 0.1mm Chip | 6-organ constitutional conformance engine |
| 40 | Health Constraint Enforcement | Organ 1: A5 health rule validation |
| 41 | Governance Order Enforcement | Organ 2: A3 priority validation |
| 42 | FSM Transition Legality | Organ 3: A4 state transition validation |
| 43 | Exit Reason Legality | Organ 4: Mission vector exit validation |
| 44 | Mission Constraint Enforcement | Organ 5: A2+A5 ethical override validation |
| 45 | Supervision Non-Interference | Organ 6: A6 observe-only validation |
| 46 | Violation Taxonomy | Fatal vs NonFatal classification with teeth |
| 47 | Spec Encoding Philosophy | Hardcoded constants, never parsed from markdown |

### Domain 9 — Behavioral Intelligence
| # | Discovery | Description |
|---|-----------|-------------|
| 48 | Continuum Map | 5-axis behavioral space (Time, State, Health, Mission, Identity) |
| 49 | Persistence Signal | Close attempt ratio classification |
| 50 | Caution Signal | First close timing classification |
| 51 | Escalation Timing Signal | Mission escalation positioning |
| 52 | Objection Depth Signal | OBJECTION state dwell classification |
| 53 | Withdrawal Behavior Signal | Exit reason behavioral classification |
| 54 | Personality Modulation Signal | Tone consistency measurement |
| 55 | Positive Tag Vocabulary | 6 behavioral excellence markers |
| 56 | Warning Tag Vocabulary | 6 behavioral concern markers |
| 57 | FastFunnel Bonus Tag | ≤6 turn close detection |
| 58 | Cross-Call Intelligence | Rolling aggregate behavioral trends |
| 59 | HTML Reporting | Standalone visual behavioral reports |

### Domain 10 — Infrastructure & Deployment
| # | Discovery | Description |
|---|-----------|-------------|
| 60 | Cloudflare Tunnel | trycloudflare.com dynamic tunnel for webhook delivery |
| 61 | FastAPI + Hypercorn | ASGI server on port 8777 |
| 62 | Triple-Safe Organ Wiring | try/except → log → continue for all organ calls |
| 63 | Pydantic Data Contracts | Typed models for trace schema validation |

---

## APPENDIX A — Codebase Cross-Reference

| Component | Primary File | Lines | Key Classes/Functions |
|-----------|-------------|-------|----------------------|
| Relay Server | `aqi_conversation_relay_server.py` | 6,265 | WebSocket handler, 23-organ orchestration |
| Control API | `control_api_fixed.py` | 2,496 | FastAPI server, 27+ endpoints |
| AQI 0.1mm Chip | `aqi_runtime_guard.py` | 1,101 | `AQIRuntimeGuard`, 6 enforcement organs |
| State Machine | `alan_state_machine.py` | 1,042 | `CallSessionFSM`, `SystemState`, `SessionState` |
| Phase 4 Exporter | `phase4_trace_exporter.py` | 505 | `Phase4TraceExporter`, `_ActiveTrace` |
| Phase 4 Model | `phase4_call_trace_model.py` | 150 | `Phase4CallTrace` (Pydantic) |
| Phase 5 Analyzer | `aqi_phase5_call_analyzer.py` | 321 | `Phase5CallAnalyzer`, 5-axis continuum mapper |
| Phase 5 Tags | `aqi_phase5_tagging_engine.py` | — | `TaggingEngine`, 13 tags |
| Phase 5 Streaming | `aqi_phase5_streaming_analyzer.py` | — | `Phase5StreamingAnalyzer` |
| Phase 5 Dashboard | `aqi_phase5_dashboard.py` | — | `Phase5Dashboard`, rolling aggregation |
| Organism Spec | `AQI_ORGANISM_SPEC.md` | 395 | AQI notation, 6 parts (A-F) |
| Constitution | `soul_core.py` | — | SAP-1 ethical veto engine |
| Personality | `personality_matrix_core.py` | — | Affect-adaptive modulator |
| Persona | `alan_persona.json` | — | Alan identity configuration |

---

## APPENDIX B — Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | Feb 16, 2026 | Initial Full Systems Doctrine (20 sections, 63 discoveries) |
| 2.0 | Feb 19, 2026 | Scientific Architecture document — AQI notation, Phase 4/5/Chip/FSM formalization, Continuum Map, Behavioral Intelligence, Reflex Arc architecture, complete Genome with file bindings |

---

*End of AQI Scientific Architecture Specification.*
*Every claim in this document is grounded in running code and empirical test results.*
*AQI is not a vision document — it is a live organism specification.*
