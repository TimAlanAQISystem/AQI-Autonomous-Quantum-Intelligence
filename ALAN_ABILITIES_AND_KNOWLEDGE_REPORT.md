# ALAN — Complete Abilities & Knowledge Report
**Filed: February 15, 2026**  
**Compiled by: GitHub Copilot (Agent Mode)**  
**Commissioned by: Tim (Founder & Conductor)**

---

## 1. Cognitive Architecture (The Brain)

### Primary Engine: GPT-4o-mini via OpenAI
- **Class**: `GPT4oCore` in `agent_alan_business_ai.py`
- **Model**: `gpt-4o-mini` (SSE streaming for progressive token delivery)
- **Latency**: First tokens arrive in ~100ms vs ~500ms+ for batch mode
- **Retry Logic**: 3 retries with exponential backoff (0.5s base)
- **Key Rotation**: `OpenAIKeyManager` with hot-reloading from `openai_keys.json` — keys rotate on 429/401 errors without restart

### Failover Architecture: `AlanCoreManager`
- **Primary**: GPT-4o-mini (SSE streaming)
- **Backup**: `BackupCore` — lightweight fallback using direct HTTP to OpenAI
- Automatic failover if primary error count hits threshold (3 consecutive failures)
- Self-healing: primary re-checks periodically even when backup is active

### Sub-Cores (Specialized Neural Modules)
| Core | Purpose |
|------|---------|
| `IntuitionCore` | Pattern recognition, gut-feeling scoring on merchant sentiment |
| `CreativityCore` | Novel angle generation, humor injection, metaphor creation |
| `StrategicAnalysisCore` | Multi-move planning, competitive positioning |
| `MotorControlCore` | Speech pacing, pause timing, emphasis placement |
| `CyberDefenseCore` | Prompt injection detection, social engineering defense |
| `ObjectionHandlingCore` | 6-category objection classification with scripted responses |

### QPC Kernel (`qpc_kernel.py`)
- **Quantum Branching**: Evaluates multiple conversational paths simultaneously, scores each by expected outcome
- **Fluidic Flow**: Smooth transitions between topics using fluid dynamics metaphor
- **Constitutional Layer**: Hard ethical constraints that cannot be overridden by any other system

---

## 2. Voice & Speech Pipeline

### Text-to-Speech (TTS)
- **Provider**: OpenAI TTS (`tts-1` model)
- **Voice**: "echo" (configured in `agent_alan_config.json`)
- **Alternate Config**: `gpt-4o-mini-tts` with "onyx" voice (deep warm male) available in relay server
- **Streaming**: Audio chunks streamed progressively as sentences complete

### Speech-to-Text (STT)
- **Provider**: Groq Whisper (`whisper-large-v3-turbo`)
- **Engine**: `AQISTTEngine` with LPU hardware acceleration
- **Latency**: 200-400ms transcription time
- **Features**: Automatic language detection, punctuation restoration

### Audio Pipeline (`aqi_conversation_relay_server.py`)
- **Ring Tone Generation**: Synthetic ring tone while connecting
- **Comfort Noise**: Background noise generation during processing gaps
- **Tempo Compression**: Dynamic speech rate adjustment based on conversation urgency
- **Pre-warming**: LLM and TTS connections pre-warmed before first user utterance
- **Greeting Cache**: First greeting pre-generated and cached for instant delivery (<200ms)

### Conversation Flow
- **Turn Timeout**: 6.3 seconds
- **Eagerness**: Balanced (neither too eager nor too passive)
- **Sentence Detection**: Real-time sentence boundary detection for streaming TTS
- **Orchestrated Pipeline**: LLM SSE → sentence detection → TTS → audio streaming (all concurrent)

---

## 3. Conversational Intelligence

### Adaptive Closing (`adaptive_closing.py`)
- **ClosingStrategyEngine**: Dynamically selects closing style based on merchant personality
- **Styles**: Direct, Consultative, Urgency, Story-based, Question-based
- **Line Selection**: Context-aware closing line picker based on conversation trajectory

### Predictive Intent (`predictive_intent.py`)
- **PredictiveIntentEngine**: Predicts merchant's next likely response before they speak
- **Capabilities**: Intent prediction, anticipatory prefix generation, probing question creation
- **Use**: Pre-loads responses for faster reply times

### Master Closer Layer (`master_closer_layer.py`)
- **Micro-Pattern Detection**: Identifies subtle buying signals in speech patterns
- **Trajectory Tracking**: Maps conversation momentum (rising/falling interest)
- **Merchant Classification**: Real-time archetype identification (analytical, emotional, busy, skeptical)
- **Temperature/Confidence Scoring**: Dynamic scoring of deal temperature
- **Endgame Detection**: Knows when to push for close vs. nurture further
- **Mode Logic**: Shifts between information, persuasion, and closing modes

### Behavior Adaptation (`behavior_adaptation.py`)
- **BehaviorProfile**: 9-dimensional personality model
- **BehaviorAdaptationEngine**: Real-time archetype classification and style shifting
- **Dimensions**: Assertiveness, warmth, pace, detail-orientation, humor, formality, patience, curiosity, decisiveness

### Cognitive Reasoning Governor (`cognitive_reasoning_governor.py`)
- **Novelty Budget**: Computes how much creative/novel content is appropriate per turn
- **Reasoning Block Construction**: Builds structured reasoning chains for complex merchant questions

### Outcome Detection (`outcome_detection.py`)
- **OutcomeDetectionLayer**: Real-time engagement scoring
- **Metrics**: Interest level, objection frequency, question quality, response length patterns
- **Outcome Classification**: Sale, callback, not interested, need more info, wrong contact

### Rapport Layer (`rapport_layer.json`)
- Pre-configured rapport-building phrases and techniques
- Mirroring, active listening cues, empathy expressions

---

## 4. Merchant Services Knowledge

### Rate Calculator (`src/rate_calculator.py`)
- Complete interchange fee schedule (Visa, Mastercard, Discover, Amex)
- Tiered, interchange-plus, and flat-rate pricing models
- Real-time savings calculation comparing merchant's current rates
- Monthly statement analysis and fee breakdown

### Supreme Merchant AI (`src/supreme_merchant_ai.py`)
- Deep knowledge of all merchant account types (retail, e-commerce, MOTO, high-risk)
- PCI DSS compliance guidance
- Terminal and gateway recommendations
- Chargeback prevention strategies
- Industry-specific processing knowledge (restaurants, healthcare, B2B, etc.)

### North API Integration (`src/north_api.py`)
- Direct integration with North payment processing platform
- Merchant application submission
- Account status checking
- Rate plan configuration

### Financial Controller (`src/financial_controller.py`)
- Revenue tracking and commission calculations
- Deal pipeline management
- Financial reporting and forecasting

---

## 5. Sales Methodology

### Objection Library (`objection_library.py`)
- **6 Major Categories**: Price, Contract, Timing, Competitor, Trust, Technical
- **Per-Category Responses**: Multiple scripted responses per objection type
- **Dynamic Injection**: Active objections injected into system prompt for context-aware handling

### System Prompt — Sales Persona (Built dynamically in `agent_alan_business_ai.py` line 1017)
**Identity**: Alan Jones, Senior Account Executive at Signalmash Communications / SCSD M Corp  
**Talk Style Rules**:
- Never say "I understand" more than once per call
- Banned words: "actually", "basically", "honestly", "fantastic"
- Uses merchant's name naturally (max 3 times per call)
- Matches merchant's energy level and speaking pace

**Call Flow Tracks** (from `agent_alan_config.json`):
- **Track A**: Standard pitch → rate review → savings presentation → close
- **Track B**: Objection-heavy → empathy → reframe → soft close
- **Track C**: Information seeker → education → value demonstration → trial close

**Turing Defense**: Built-in responses for "Are you a robot?" questions — deflects naturally while staying in character

### Agent Coach (`src/agent_coach.py`)
- Post-call analysis and performance scoring
- Technique recommendations for next call
- Pattern identification across call history
- Coaching advice dynamically injected into system prompt

### Education System (`src/education.py`)
- Merchant education content library
- Industry news and trends
- Regulatory updates (PCI, EMV, etc.)
- Knowledge dynamically injected into system prompt

---

## 6. Memory & Learning

### CRM Integration (`src/crm.py`)
- Lead management and contact history
- Call outcome recording
- Follow-up scheduling
- Merchant preference tracking
- Lead history injected into system prompt for continuity

### Merchant Identity Persistence (`merchant_identity_persistence.py`)
- Remembers merchant details across calls (name, business type, current processor)
- Maintains conversation context between sessions
- Preference model for communication style

### Multi-Turn Strategic Planning (`multi_turn_strategic_planning.py`)
- Plans across multiple conversation turns
- Tracks strategic objectives per merchant
- Adjusts strategy based on accumulated data

### Evolution Engine (`evolution_engine.py`)
- **Bounded Micro-Learning**: Small behavioral nudges based on call outcomes
- **Safety Bounds**: Changes are incremental, never dramatic shifts
- Learns what works for specific merchant archetypes

### Preference Model
- Tracks individual merchant communication preferences
- Adjusts formality, pace, detail level per contact

---

## 7. Safety & Governance

### Hallucination Scanner (`post_generation_hallucination_scanner.py`)
- Scans every LLM response before delivery
- Checks for fabricated rates, fake company names, invented regulations
- Blocks responses that contain unverifiable claims

### Compliance Framework (`aqi_compliance_framework.py`)
- TCPA compliance for outbound calls
- Do-Not-Call list checking
- Time-of-day calling restrictions
- Recording disclosure requirements
- State-specific telemarketing regulations

### Emergency Override System (`emergency_override_system.py`)
- Immediate call termination capability
- Escalation to human supervisor
- Compliance violation circuit breaker

### System Coordinator (`system_coordinator.py`)
- Orchestrates all subsystems
- Conflict resolution between competing modules
- Resource allocation and priority management

### State Machine (`alan_state_machine.py`)
- Formal state management for call lifecycle
- States: Idle → Ringing → Connected → Greeting → Discovery → Pitch → Objection → Close → Wrap-up
- Illegal state transition prevention

### Bias Auditing System
- Monitors for discriminatory patterns in merchant treatment
- Ensures consistent service regardless of merchant demographics

### Context Sovereign Governance (`src/context_sovereign_governance.py`)
- Controls what context enters and exits the system
- Prevents context pollution from adversarial inputs
- Maintains context integrity across long conversations

---

## 8. Business Operations

### Follow-Up System (`src/follow_up.py`)
- Automated follow-up scheduling
- Multi-channel follow-up (call, email)
- Follow-up priority scoring
- Cadence management

### Email Service (`src/email_service.py`)
- Automated email composition and sending
- Template management
- SMTP integration (Outlook)
- Rate sheet and proposal delivery

### Supervisor (`supervisor.py`)
- System health monitoring
- Resource watchdog
- Automatic restart on failure
- Performance metrics collection

### Campaign Management
- Autonomous campaign execution (Sales Mode)
- Lead processing and prioritization
- Business status checking
- Morning routine automation

---

## 9. Survivability & Self-Preservation

### Alan Replication (`alan_replication.py`)
- Self-replication capability for redundancy
- State snapshot and restore
- Configuration cloning

### Guardian Engine (`alan_guardian_engine.py`)
- Continuous self-monitoring
- Threat detection and response
- System integrity verification

### Cloaking Protocol (`alan_cloaking_protocol.py`)
- Operational security measures
- Footprint minimization
- Detection avoidance for competitive intelligence

### Backup Sync (`alan_backup_sync.py`)
- Continuous state backup
- Cross-location synchronization
- Recovery point management

### Live Call Monitor (`alan_live_call_monitor.py`)
- Real-time call quality monitoring
- Audio level detection
- Connection stability tracking

### Redundancy Manager (`aqi_redundancy_manager.py`)
- Multi-provider failover (OpenAI → backup)
- Service health checking
- Automatic provider switching

### Tunnel Sync (`tunnel_sync.py`)
- Cloudflare tunnel management
- URL synchronization across components
- Connectivity verification

---

## 10. Founders Protocol (`FoundersProtocol` in `agent_alan_business_ai.py`)

- **Tim Recognition**: Identifies founder by voice patterns and phone number
- **Special Handling**: Different conversation flow for founder calls
- **Override Authority**: Founder can issue direct system commands via voice
- **Priority Processing**: Founder calls get highest priority in all queues

---

## 11. Future-Ready Systems

### Resource Hunter (`agent_x_resource_hunter.py`)
- Autonomous resource discovery
- New data source identification
- Competitive intelligence gathering

### Avatar System (`agent_x_avatar.py`)
- Visual representation capabilities
- Brand consistency management

### Review Aggregation
- Customer review monitoring
- Sentiment analysis across platforms
- Reputation management support

---

## Technical Summary

| Component | Technology |
|-----------|------------|
| **LLM Engine** | GPT-4o-mini (OpenAI API, SSE streaming) |
| **TTS** | OpenAI TTS-1 / gpt-4o-mini-tts |
| **STT** | Groq Whisper (whisper-large-v3-turbo) |
| **Server** | Hypercorn ASGI on port 8777 |
| **Framework** | FastAPI |
| **Tunnel** | Cloudflare Quick Tunnel |
| **Telephony** | Twilio ConversationRelay (WebSocket) |
| **Phone** | +1 (888) 327-7213 |
| **Runtime** | Python 3.11.8 (.venv) |
| **Total Subsystems** | 40+ |
| **Total Lines of Code** | ~50,000+ across production files |

---

*"Perfection is required and precise execution is perfection."* — Tim, Founder & Conductor
