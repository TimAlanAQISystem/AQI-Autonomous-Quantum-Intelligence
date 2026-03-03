# Agent X — Comprehensive Codebase Report

**Generated:** Auto-scan of all 48 root-level Python files  
**Workspace:** `c:\Users\signa\OneDrive\Desktop\Agent X`

---

## Table of Contents

| # | File | Lines | Category |
|---|------|-------|----------|
| 1 | adaptive_closing.py | ~50 | Sales / Conversation |
| 2 | adjustment_profiles.py | ~35 | Campaign Tuning |
| 3 | agent_assisted_payments.py | ~120 | Payments / Twilio |
| 4 | agent_sql_tracker.py | ~105 | Database / Logging |
| 5 | agent_x_avatar.py | ~1083 | GUI / Desktop |
| 6 | agent_x_resource_hunter.py | ~135 | Intelligence / RSS |
| 7 | aqi_alan_voice_responses.py | ~529 | Voice / NLP |
| 8 | aqi_compliance_framework.py | ~721 | Compliance / PCI |
| 9 | aqi_lead_importer.py | ~639 | Lead Management |
| 10 | aqi_redundancy_manager.py | ~100 | Health / Failover |
| 11 | aqi_stt_engine.py | ~310 | Speech-to-Text |
| 12 | aqi_voice_governance.py | ~370 | Voice Governor |
| 13 | aqi_voice_module.py | ~699 | Voice / WebSocket |
| 14 | aqi_voice_negproof_tests.py | ~596 | Testing / Voice |
| 15 | autonomous_campaign_runner.py | ~350 | Campaign Automation |
| 16 | budget_tracker.py | ~75 | Budget / Stats |
| 17 | config.py | ~13 | Configuration |
| 18 | continuum_engine.py | ~280 | QPC / Relational Fields |
| 19 | deploy_package.py | ~170 | Deployment |
| 20 | excel_lead_importer.py | ~370 | Lead Import (CLI) |
| 21 | lead_database.py | ~310 | Lead DB (SQLite) |
| 22 | logging_config.py | ~10 | Logging Setup |
| 23 | main.py | ~40 | Entrypoint / n8n |
| 24 | merchant_queue.py | ~350 | Lead Queue (JSON) |
| 25 | metrics.py | ~55 | CEM / Scoring |
| 26 | multi_turn_strategic_planning.py | ~145 | Conversation Strategy |
| 27 | n8n_client.py | ~45 | n8n REST Client |
| 28 | neg_proof_persistence.py | ~175 | Negative-Proof Tests |
| 29 | neg_proof_test.py | ~175 | Stress Tests |
| 30 | outbound_controller.py | ~165 | Outbound Calls |
| 31 | performance_monitor.py | ~175 | Perf Monitoring |
| 32 | qpc_kernel.py | ~290 | QPC Kernel |
| 33 | session_memory.py | ~165 | Session Memory |
| 34 | session_persistence.py | ~569 | Session Persistence (SQLite) |
| 35 | workflow_chargeback.py | ~95 | n8n Workflow |
| 36 | workflow_merchant_activate.py | ~50 | n8n Workflow |
| 37 | workflow_merchant_onboard.py | ~50 | n8n Workflow |
| 38 | workflow_merchant_release.py | ~50 | n8n Workflow |
| 39 | workflow_merchant_review.py | ~50 | n8n Workflow |
| 40 | workflow_merchant_suspend.py | ~50 | n8n Workflow |
| 41 | workflow_merchant_underwrite.py | ~50 | n8n Workflow |
| 42 | workflow_payout.py | ~95 | n8n Workflow |
| 43 | workflow_reconciliation_hub.py | ~70 | n8n Workflow |
| 44 | workflow_refund.py | ~80 | n8n Workflow |
| 45 | workflow_tx_create_capture.py | ~105 | n8n Workflow |
| 46 | alan_live_call_monitor.py | ~645 | Call Monitoring |
| 47 | _neg_proof_imports.py | ~130 | Module Load Test |
| 48 | _neg_proof_timing.py | ~120 | Pipeline Timing Test |

**Total estimated lines: ~9,613**

---

## Detailed File Reports

---

### 1. `adaptive_closing.py` (~50 lines)

**Category:** Sales / Conversation  
**Classes:** `ClosingStrategyEngine`  
**Functions:**
- `__init__(config_path="adaptive_closing_strategy.json")`
- `choose_style(analysis)` — maps merchant sentiment/personality to a closing style
- `pick_line(style)` — picks a random line from the chosen style

**Key Logic:** Loads closing strategies from a JSON config file. Matches merchant analysis (sentiment, personality indicators) to one of several closing styles (e.g., confident, empathetic, urgency). Selects a random closing line from the matched style.

**Constants:** Default config path `"adaptive_closing_strategy.json"`  
**Integration:** Standalone — reads JSON config. Used by relay server / sales conversation logic.

---

### 2. `adjustment_profiles.py` (~35 lines)

**Category:** Campaign Tuning  
**Classes/Functions:** None — pure constants module  
**Constants:**
- `CONSERVATIVE_PROFILE` — low CPS, wide intervals, low retry, increased VAD sensitivity
- `BALANCED_PROFILE` — moderate CPS, balanced lead ratios
- `AGGRESSIVE_PROFILE` — high CPS, tight intervals, high retry limits, reduced opener delay

Each profile is a dict controlling: `cps_delta`, `interval_delta`, `new_lead_ratio_delta`, `retry_ratio_delta`, `max_retries_delta`, `vad_sensitivity_delta`, `opener_delay_delta`.

**Integration:** Consumed by `autonomous_campaign_runner.py` pacing logic.

---

### 3. `agent_assisted_payments.py` (~120 lines)

**Category:** Payments / Twilio  
**Functions:**
- `create_payment_session(call_sid, url)` — starts a PCI-compliant payment session during a live call
- `update_payment_capture(payment_sid, call_sid, capture_type, url)` — prompts for card number, expiry, CVV, or postal code
- `complete_payment_session(payment_sid, call_sid, url)` — finalizes and charges
- `cancel_payment_session(payment_sid, call_sid, url)` — cancels payment
- `demonstrate_payment_workflow()` — demo script

**Key Logic:** Uses Twilio's agent-assisted payment API. The capture flow is: create session → capture card number → capture expiry → capture CVV → capture postal code → complete. All via REST calls to Twilio.

**Constants:** Uses env vars `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`  
**Integration:** Twilio Payments REST API.

---

### 4. `agent_sql_tracker.py` (~105 lines)

**Category:** Database / Logging  
**Functions:**
- `init_db()` — creates/opens SQLite DB, creates `Alan_Communication_Logs` table
- `log_communication_event(call_sid, data)` — upserts a call record

**Table columns:** `call_sid`, `merchant_name`, `phone_number`, `status`, `duration`, `recording_url`, `timestamp`, `stealth_logic_version`, `vulture_reattempts`, `sentiment`, `result_code`, `notes`

**Key Logic:** Upsert — inserts new record or updates existing by `call_sid`.  
**Constants:** `DB_PATH = "database/alan_communication.db"`  
**Integration:** Called by `autonomous_campaign_runner.py` to track events. Auto-initializes on import.

---

### 5. `agent_x_avatar.py` (~1083 lines)

**Category:** GUI / Desktop  
**Classes:**
- `TTSWorker` — persistent COM worker thread wrapping `SAPI.SpVoice`. Has queue, flush, output device selection via `win32com.client`.
- `AgentXAvatar` — full Tkinter GUI application

**AgentXAvatar Functions:**
- `__init__()` — builds UI with chat display, input field, action buttons, mic/speaker selectors
- `add_message(role, text)` — adds messages to chat display
- `send_message()` / `process_message()` — sends user text to AQIAgentX, gets response
- `listen_once()` / `_capture_and_process_voice()` / `_capture_and_process_voice_am()` — voice input via SpeechRecognition or AudioManager
- `agent_action(action)` — dispatches Express Joy / Explore / Spontaneous Act / Show Ledger
- `animate_thinking()` / `reset_avatar()` — UI animations
- `_speak_sync(text)` — sends text to TTSWorker
- `_on_close()` — graceful shutdown
- `_init_mic_selector()` / `_refresh_mics()` / `_test_mic()` — microphone management
- `_init_speaker_selector()` / `_test_tts_startup()` — speaker management
- `run()` — starts Tkinter mainloop

**Action Buttons:** Express Joy, Explore, Spontaneous Act, Show Ledger, Listen, Hide, Test Voice, Flush Speech  
**Integration:** Imports `AudioManager`, `AutonomyEngine`, `AQIAgentX`, `speech_recognition`, `play_beep`

---

### 6. `agent_x_resource_hunter.py` (~135 lines)

**Category:** Intelligence / RSS  
**Classes:** `AgentXResourceHunter`  
**Functions:**
- `setup_database()` — creates `resource_opportunities` table in SQLite
- `start_hunting()` — continuous loop (every 30 min) fetching RSS
- `hunt_real_financial_news()` — fetches MarketWatch, CNBC, Reuters RSS feeds
- `report_findings(opp)` — logs findings to DB

**Key Logic:** Scans financial news RSS for keywords: loan, lending, fintech, payment, merchant, banking, digital payments, credit processing. Stores matches with title, source, URL, published date, matched keywords.

**Constants:** `FINANCIAL_KEYWORDS` set, RSS feed URLs  
**Integration:** `alan_backup_sync.AlanTeleportProtocol` for security checks, SQLite `aqi_merchant_services.db`

---

### 7. `aqi_alan_voice_responses.py` (~529 lines)

**Category:** Voice / NLP  
**Classes:** `AlanSession`  
**Functions:**
- `add_pause_markers(text)` — inserts SSML-like pause markers
- `get_initial_greeting()` — opening line with natural rhythm
- `get_silence_follow_up()` — handles silence gaps
- `get_acknowledgment(text)` — mirrors merchant words
- `get_thinking_out_loud()` — thinking filler
- `get_confirmation(context)` — confirms understanding
- `get_control_question()` — steers conversation
- `get_fallback_response()` — handles unexpected input
- `get_objection_rebuttal(objection, context)` — handles busy/not-interested/send-info/contract/fee objections
- `generate_alan_response(merchant_text, context)` — main response generator
- `_ensure_control_return(response)` — guarantees response ends with a question

**Behavior Tree Nodes:**
- NODE_1: Greeting
- NODE_2: Silence Window (2s timeout)
- NODE_3: Wait for Content
- NODE_4: Acknowledge & Mirror
- NODE_5: Intent Branch (Onboarding/Support/Diagnostics/Objection/Closure/Unknown)
- NODE_6–8: Follow-up nodes

**Constants:** `SILENCE_TIMEOUT=2.0`, `ONBOARDING_KEYWORDS`, `SUPPORT_KEYWORDS`, `OBJECTION_KEYWORDS`, `CLOSURE_KEYWORDS`, `PAUSE_TIMING` dict  
**Integration:** Used by voice module / relay server to generate Alan's dialogue.

---

### 8. `aqi_compliance_framework.py` (~721 lines)

**Category:** Compliance / PCI  
**Classes:** `AQIMerchantComplianceFramework`  
**Functions:**
- `setup_compliance_database()` — creates compliance tables
- `initialize_compliance_rules()` / `load_compliance_rules_to_db()` — seeds rules for PCI DSS, HIPAA, SOX, GDPR, etc.
- `setup_security_framework()` — configures AES-256, TLS 1.3, key rotation policies
- `initialize_audit_system()` — 7-year audit retention policy
- `assess_merchant_compliance()` — evaluates merchant PCI level
- `determine_pci_level(volume)` — PCI DSS level 1–4 based on transaction volume
- `check_compliance_requirement()` / `generate_compliance_recommendations()`
- `save_compliance_assessment()` / `log_security_event()`
- `generate_compliance_report()` / `check_compliance_expiry()`
- `encrypt_sensitive_data()` / `validate_pci_compliance()` / `get_compliance_status()`
- `demonstrate_compliance_framework()` — demo runner

**DB:** `aqi_compliance.db` with tables: `compliance_requirements`, `merchant_compliance`, `security_audit_log`, `pci_dss_compliance`, `regulatory_filings`  
**Integration:** Standalone compliance engine; referenced during merchant onboarding.

---

### 9. `aqi_lead_importer.py` (~639 lines)

**Category:** Lead Management  
**Classes:** `AQILeadImporter`  
**Functions:**
- `import_batch_files()` / `import_excel_batch()` — batch import from data/ directory
- `_process_lead_row()` / `_determine_priority()` — row-by-row processing with auto-priority
- `_is_duplicate_prospect()` — dedup by phone + company name
- `_save_new_prospects()` / `_save_new_leads()` / `_mark_batch_processed()`
- `import_leads_from_excel()` / `_read_rse_csv_file()` / `_parse_rse_row()`
- `_read_excel_file()` / `_parse_excel_row()`
- `_clean_phone_number()` — normalizes to E.164
- `save_leads_to_database()` / `get_import_stats()` / `import_excel_leads()`

**Key Logic:** Supports Excel (.xlsx) and RSE Cloud CSV exports. Auto-detects column headers. Priority assignment: critical (>$100K volume), high ($50K–$100K), medium ($10K–$50K), low (<$10K). Deduplication on phone + company.

**Integration:** pandas, SQLite, JSON tracking files in `data/`

---

### 10. `aqi_redundancy_manager.py` (~100 lines)

**Category:** Health / Failover  
**Classes:** `AQIRedundancyManager`  
**Functions:**
- `_load_backup_keys()` — loads backup API keys from JSON
- `check_vital_signs()` — checks Internet, OpenAI, Twilio
- `_check_openai()` / `_check_twilio()` — individual service health
- `get_brain_state()` — returns `FULL_AI` or `LOBOTOMY_MODE`
- `get_voice_state()` — returns `ACTIVE_VOICE` or `TEXT_ONLY`
- `activate_emergency_fallback(service)` — rotates to backup keys

**Integration:** Env vars for API keys, backup key JSON file.

---

### 11. `aqi_stt_engine.py` (~310 lines)

**Category:** Speech-to-Text  
**Classes:** `STTSessionBuffer`  
**Functions:**
- `_get_groq_client()` / `_get_stt_client()` — lazy Groq/OpenAI client init
- `register_stt_callback(cb)` / `create_stt_session(session_id)` / `close_stt_session()` / `clear_buffer()` / `finalize_and_clear()`
- `process_audio_chunk(raw_bytes)` — accumulates PCM audio in buffer
- `_transcribe_and_emit(audio_bytes)` — runs cloud STT (Groq then OpenAI fallback)
- `_run_cloud_stt_sync()` / `_run_cloud_stt_internal()` — actual Whisper API calls
- `inject_transcript(text)` — manually injects text as transcript

**Key Logic:**
- Manual WAV header construction (to bypass ffmpeg latency)
- Groq Whisper primary (200–400ms), OpenAI Whisper fallback (1–2s)
- Server-side VAD commit model
- Whisper hallucination filtering (`WHISPER_HALLUCINATIONS` set with ~15 known hallucination strings)
- Min RMS energy check (150) — ignores silence
- Audio trimming to 6s max
- Whisper prompt engineering: "This is a merchant services conversation about payment processing..."

**Constants:** `STT_MIN_BUFFER_MS=500`, `STT_MIN_AUDIO_DURATION=0.3`, `STT_MIN_RMS_ENERGY=150`  
**Integration:** Called by `aqi_voice_module.py`, emits transcripts via registered callbacks.

---

### 12. `aqi_voice_governance.py` (~370 lines)

**Category:** Voice Governor  
**Classes:**
- `SpeakerRole` (Enum): CORE, SAFETY, BARGE_IN, GREETING
- `CoreHealth` (Enum): ALIVE, DEGRADED, DEAD
- `SpeechRequest` (dataclass): role, text, priority, is_safety_override
- `VoiceGovernanceError`, `CoreFailureDetected`, `ArchitecturalViolation` (Exceptions)
- `VoiceGovernor` — singleton speech coordinator

**VoiceGovernor Functions:**
- `get_voice_governor()` — singleton factory
- `core_heartbeat()` — signals core is alive
- `governed_speech(role, text, priority, is_safety)` — async speech with lock
- `governed_speech_sync(...)` — sync version

**Key Logic:** Only one speaker layer at a time. Emergency failover when core dies. Safety overrides bypass all checks. Timeout-based lock (5s default) prevents deadlocks. Heartbeat tracking for health monitoring.

**Integration:** Used by `aqi_voice_module.py` for speech permission.

---

### 13. `aqi_voice_module.py` (~699 lines)

**Category:** Voice / WebSocket  
**Classes:** `VoiceSession`  
**FastAPI Router Endpoints:**
- `POST /aqi/internal/voice` — internal voice control
- `POST /voice-session/start` — creates a voice session
- `GET /voice-session/{session_id}/metadata` — session metadata
- `WS /voice-session/ws/{session_id}` — WebSocket for streaming audio

**Functions:**
- `preload_text_to_voice()` / `cancel_speech()` / `send_hybrid_greeting()` / `send_text_to_voice()`
- `register_stt_callback()` / `register_connect_callback()` / `register_session_start_callback()`

**Key Logic:**
- Turn-taking governor with phases: Golden Rule, Silence Window, One-Response Lock, Closing Guard, Drift Guard, Echo Shield
- Session lifecycle management
- Barge-in support
- Energy-sovereign snap (RMS-based voice activity detection)
- TTS purified — all TTS handled by relay server's OpenAI realtime TTS
- WebSocket binary audio streaming with μ-law encoding

**Integration:** `aqi_stt_engine`, `aqi_voice_governance`, FastAPI

---

### 14. `aqi_voice_negproof_tests.py` (~596 lines)

**Category:** Testing / Voice  
**Classes:**
- `TTSCallRecord`, `AudioPathRecord`, `SpeakerTokenRecord` (dataclasses)
- `VoiceNegativeProofSuite`

**Functions:**
- `record_tts_call()` / `test_tts_surface_isolation()`
- `record_audio_path()` / `test_audio_surface_unity()`
- `record_speaker_token()` / `test_concurrency_surface_exclusion()`
- `record_fallback_activation()` / `test_fallback_surface_control()`
- `record_debug_tts_accident()` / `test_debug_surface_isolation()`
- `run_full_negative_proof_suite()` / `get_neg_proof_suite()`

**Key Logic:** 5 negative-proof test categories proving voice interference bugs are dead:
1. TTS Surface — only relay server TTS allowed
2. Audio Surface — all audio flows through single path
3. Concurrency Surface — no two speakers at once
4. Fallback Surface — controlled fallback chain
5. Debug Surface — debug code cannot trigger TTS

Real-time violation monitoring with counters.

---

### 15. `autonomous_campaign_runner.py` (~350 lines)

**Category:** Campaign Automation  
**Classes:** `SafeCampaignRunner`  
**Functions:**
- `warm_up_agent()` — pre-call agent warmup
- `is_business_hours()` — 8am–5pm Mon–Sat
- `update_heartbeat()` — writes heartbeat timestamp
- `refresh_tunnel_url()` — reads ngrok URL from `active_tunnel_url.txt`
- `process_callback_requests()` — handles scheduled callbacks
- `make_call()` — places a single outbound call
- `run_cycle()` — one campaign cycle: pick lead → call → record
- `start()` — main loop with cooldown management

**Key Logic:**
- Continuous campaign loop during business hours
- Cooldown manager (150s between calls)
- VERITAS protocol (truth audit every ~20 cycles)
- Entropy injection (area code diversity for lead selection)
- Vulture protocol (rapid re-dial for URGENT priority leads)
- System lock file check for pause/resume
- Beta mode override flag

**Constants:** `POLL_INTERVAL=15`, `ERROR_SLEEP=300`  
**Integration:** `merchant_queue`, `cooldown_manager`, `agent_sql_tracker`, control API at port 8777

---

### 16. `budget_tracker.py` (~75 lines)

**Category:** Budget / Stats  
**Functions:**
- `get_today_key()` / `get_daily_stats()` / `save_daily_stats()`
- `compute_cem()` — Contact Efficiency Metric
- `increment_stat(stat_name)` — atomic increment
- `has_budget_for_new_leads()` / `has_budget_for_retry_leads()` / `has_overall_budget()`

**Key Logic:** Tracks daily stats: new leads dialed, retry leads, unique leads touched, transcripts generated, contact efficiency. Auto-resets on date change. Budget limits from `voice_box.config`.

**Integration:** `voice_box.config` for limits, JSON file `data/daily_stats.json`

---

### 17. `config.py` (~13 lines)

**Category:** Configuration  
**Classes:** `N8NConfig` (dataclass)  
**Functions:** `from_env()` — classmethod loading from env vars  
**Fields:** `base_url`, `api_key`  
**Integration:** Used by `n8n_client.py`

---

### 18. `continuum_engine.py` (~280 lines)

**Category:** QPC / Relational Fields  
**Classes:**
- `Field` — continuous vector field (numpy array)
- `RelationalFields` — container for ethics, emotion, context, narrative fields
- `ContinuumEngine` — field evolution via drift functions
- `RelationalDynamics` — smooth interpolation and nonlinearity
- `NarrativeState` — tracks narrative arcs
- `ContinuumRelationalLayer` — top-level orchestrator

**Key Logic:** QPC Layer 2 — Relational Field Layer. Models continuous vector fields for ethics, emotion, context, narrative. Fields evolve via drift functions. Smooth interpolation across dimensions. Nonlinear activation for field values. Designed as middleware between sensory input (Layer 1) and quantum/packet engine (Layer 3).

**Integration:** numpy, part of QPC architecture, used by `aqi_deep_layer.py`

---

### 19. `deploy_package.py` (~170 lines)

**Category:** Deployment  
**Functions:** `build_package()`  
**Key Logic:** Creates a deployment tarball (`agentx-deploy-YYYYMMDD.tar.gz`) with specified production files. Generates a VPS setup script (`vps_setup.sh`) for Ubuntu with:
- systemd services: `agentx.service` and cloudflared tunnel
- Python venv setup
- pip install requirements

**Constants:** `INCLUDE_PATTERNS` (list of production files), `EXCLUDE_DIRS`, `SETUP_SCRIPT` (bash template)

---

### 20. `excel_lead_importer.py` (~370 lines)

**Category:** Lead Import (CLI)  
**Functions:**
- `normalize_phone(raw)` — E.164 normalization
- `normalize_priority(raw)` — maps to standard priority levels
- `detect_columns(headers)` — auto-detects column purposes from header names
- `read_excel(path)` / `read_csv(path)` — file readers
- `import_leads(path, source, dry_run, limit)` — main import pipeline
- `main()` — CLI entrypoint with argparse

**Constants:** `COLUMN_MAPPINGS` — aliases for phone, name, business_type, contact, volume, priority, source, email, address, notes (15+ aliases per column).

**Integration:** `lead_database.LeadDB`, openpyxl, csv module. CLI tool.

---

### 21. `lead_database.py` (~310 lines)

**Category:** Lead DB (SQLite)  
**Classes:** `LeadDB`  
**Functions:**
- `_conn()` — thread-safe SQLite connection (WAL mode)
- `_init_db()` — creates `leads` and `call_history` tables
- `_count()` / `_migrate_from_json()` — initial setup and migration from `merchant_queue.json`
- `get_next_lead()` — priority-based lead selection
- `record_attempt(lead_id, outcome, notes)` — records call attempt
- `add_lead(phone, name, ...)` — inserts new lead
- `mark_dnc(phone)` — marks Do Not Call
- `get_lead_by_phone()` / `get_lead()` / `get_stats()` / `get_call_history()` / `get_daily_stats()`

**Tables:** `leads` (phone, name, business_type, contact, volume, priority, source, status, attempts, last_attempt, next_retry, notes, created_at), `call_history` (lead_id, outcome, notes, timestamp)  
**Constants:** `DB_PATH = "data/leads.db"`, `JSON_PATH = "merchant_queue.json"`  
**Integration:** Used by `excel_lead_importer.py`, `control_api_fixed.py`

---

### 22. `logging_config.py` (~10 lines)

**Category:** Logging Setup  
**Functions:** `configure_logging()` — basic logging to stdout with timestamp format  
**Integration:** Called at application startup

---

### 23. `main.py` (~40 lines)

**Category:** Entrypoint / n8n  
**Functions:**
- `create_and_activate()` — creates 11 n8n workflows via N8NClient
- `bootstrap_all_internal_finance_workflows()` — orchestrator

**Workflows Created:**
1. Tx Create & Capture
2. Refund Processor
3. Chargeback Handler
4. Payout Engine
5. Reconciliation Hub
6. Merchant Onboarding
7. Merchant Underwriting
8. Merchant Activation
9. Merchant Review
10. Merchant Suspension
11. Merchant Release

**Integration:** `N8NClient`, all `workflow_*.py` builder modules

---

### 24. `merchant_queue.py` (~350 lines)

**Category:** Lead Queue (JSON)  
**Classes:**
- `CallOutcome` (Enum): PENDING, ANSWERED, CONNECTED, CALLBACK_SCHEDULED, VOICEMAIL, NO_ANSWER, BUSY, FAILED, INTERESTED, DECLINED, QUALIFIED, CLOSED_WON, DO_NOT_CALL, CANCELLED_BY_USER
- `Merchant` (dataclass): phone, name, business_type, priority, status, attempts, last_attempt, callback_time, notes, area_code, source
- `MerchantQueue`

**MerchantQueue Functions:**
- `load()` / `save()` — JSON persistence with atomic writes
- `add_merchant()` / `remove_merchant()` / `update_status()`
- `get_next()` — priority-sorted, retry-aware lead selection
- `get_stats()` / `get_all()` / `get_by_phone()` / `get_by_area_code()`
- Vulture protocol for URGENT leads, circuit breaker for duplicate squelch

**Key Logic:** Priority sorting (URGENT > high > normal), retry scheduling (45min, 90min), rapid redial prevention (10min).  
**Constants:** `QUEUE_FILE = "merchant_queue.json"`  
**Integration:** Used by `autonomous_campaign_runner.py`, `outbound_controller.py`

---

### 25. `metrics.py` (~55 lines)

**Category:** CEM / Scoring  
**Functions:**
- `get_cem()` — Contact Efficiency Metric (leads / transcripts)
- `get_cem_score()` — normalized CEM 0–5 scale
- `get_surplus_score()` — unified surplus 0–35 scale
- `get_transcript_count()` / `get_hangup_density()`

**Integration:** `budget_tracker`

---

### 26. `multi_turn_strategic_planning.py` (~145 lines)

**Category:** Conversation Strategy  
**Classes:**
- `ConversationPlan` (Pydantic BaseModel)
- `FollowUpTask` (Pydantic BaseModel)
- `MultiTurnStrategicPlanner`

**Functions:**
- `initialize_plan(merchant_id, context)` — creates micro/meso/macro plan
- `_generate_initial_moves()` — first 2–3 conversational moves
- `update_plan(plan_id, turn_data)` — updates plan after each turn
- `add_callback_task()` / `get_due_tasks()` / `complete_task()` / `fail_task()`
- `get_daily_plan()` / `get_weekly_plan()` / `update_async()`

**Key Logic:** Planning at 3 horizons:
- Micro: next 2–3 turns
- Meso: rest of call
- Macro: day/week objectives

Phases: trust → diagnose → position → close. Task queue persisted to JSON.

**Integration:** Used by relay server for conversation planning.

---

### 27. `n8n_client.py` (~45 lines)

**Category:** n8n REST Client  
**Classes:** `N8NClient`  
**Functions:** `list_workflows()`, `get_workflow(id)`, `create_workflow(data)`, `update_workflow(id, data)`, `execute_workflow(id)`  
**Integration:** `config.N8NConfig`, requests library

---

### 28. `neg_proof_persistence.py` (~175 lines)

**Category:** Negative-Proof Tests  
**Functions (11 tests):**
1. `MerchantProfile` schema validation
2. `CallMemory` persistence (save → load roundtrip)
3. `Preferences` persistence (save → load roundtrip)
4. Conversation summaries storage
5. Context seeding from history
6. Bounded growth — max 3 call memories
7. Bounded growth — max 2 conversation summaries
8. Preference decay (>90 days old entries purged)
9. `do_not_store_profile` flag respected
10. Server health check
11. Disk persistence (write → delete → verify)

**Integration:** `merchant_identity_persistence.MerchantIdentityPersistence`

---

### 29. `neg_proof_test.py` (~175 lines)

**Category:** Stress Tests  
**Functions (11 tests):**
1. Rapid-fire health checks (50 sequential hits)
2. 404 handling
3. Malformed POST resilience
4. SimpleMetrics memory bounds
5. MIP coordinator wiring
6. Graceful shutdown verification
7. `sys.path` sanity (no double entries)
8. Duplicate import check
9. Port consistency (8777)
10. Server health
11. Full test runner

**Integration:** `system_coordinator`, `merchant_identity_persistence`, `emergency_override_system`, `post_generation_hallucination_scanner`

---

### 30. `outbound_controller.py` (~165 lines)

**Category:** Outbound Calls  
**Classes:** `OutboundController`  
**Functions:**
- `load_call_list()` — loads merchants from queue
- `place_outbound_call(phone, merchant_name)` — places a Twilio call with AMD (answering machine detection)
- `run_campaign()` — loops through merchants with configurable delay and max calls
- `add_test_merchants()` — seeds test data
- `run_campaign()` (standalone function) — convenience wrapper

**Key Logic:** Uses Twilio Client to place calls. Constructs TwiML callback URL from `TUNNEL_URL`. AMD enabled with `MachineDetection="DetectMessageEnd"`.

**Integration:** Twilio Client, `merchant_queue`, env vars `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER`, `TUNNEL_URL`

---

### 31. `performance_monitor.py` (~175 lines)

**Category:** Perf Monitoring  
**Functions:**
- `timing_decorator(name, threshold_ms)` — generic timing decorator
- `log_performance(category, operation, duration_ms)` — records metric
- `get_performance_stats(category)` — retrieves stats
- `clear_performance_metrics()` / `export_performance_report()`
- `monitor_session_save()` / `monitor_session_load()` / `monitor_session_recovery()` / `monitor_conversation_save()` — specific decorators

**Key Logic:** Metrics stored in dict with 100-entry cap per category. Categories: session_saves, session_loads, session_recoveries, conversation_saves. Logs warnings when thresholds exceeded.

**Integration:** Used by `session_persistence.py` as decorators.

---

### 32. `qpc_kernel.py` (~290 lines)

**Category:** QPC Kernel  
**Classes:**
- `BranchState` (Enum): OPEN, COLLAPSED, MERGED
- `EventType` (Enum): BRANCH_SPAWNED, BRANCH_COLLAPSED, SUPERPOSITION_CREATED, MEASUREMENT_COMMITTED, SURFACE_REGISTERED, SURFACE_ACTION_REQUESTED, INVARIANT_VIOLATION
- `RiskMode` (Enum): STRICT, NORMAL, EXPLORATORY
- `Branch` (dataclass) — hypothesis with score, fluidic properties (flow_rate, pressure, viscosity, turbulence)
- `Superposition` (dataclass) — collection of branches for a question
- `MeasurementEvent` (dataclass) — records a measurement/collapse
- `AgentProfile` (dataclass) — agent identity + constitution rules + permissions
- `SurfaceDescriptor` (dataclass) — surface type (telephony/browser/cli/ui/api) + capabilities
- `KernelEvent` (dataclass) — event log entry
- `QPCKernel` — main kernel class

**QPCKernel Functions:**
- `register_agent(profile)` / `register_surface(descriptor)`
- `spawn_branch(hypothesis, ...)` — creates a quantum branch with fluidic properties
- `create_superposition(question, branches)` — groups branches
- `collapse_branch(branch_id, reason)` — marks branch as collapsed
- `measure_superposition(superposition_id)` — picks winner by score (default strategy)
- `assert_invariant(branch_id, invariant)` — constitutional check
- `regulate_flows()` — adjusts flow_rate based on pressure/turbulence
- `get_branch()` / `get_superposition()` / `get_measurement()` / `snapshot_state()`

**Key Logic:** Quantum + Fluidic + Constitutional kernel. Branches are hypotheses with scores and fluidic properties. Superpositions hold competing branches. Measurement collapses to the highest-scoring branch. Flow regulation: high pressure = more flow, high turbulence = capped flow.

**Integration:** Standalone kernel — used by QPC subsystem modules (`qpc.state`, `qpc.program`, etc.)

---

### 33. `session_memory.py` (~165 lines)

**Category:** Session Memory  
**Classes:**
- `CallSession` (dataclass): call_sid, direction, merchant_number, merchant_name, call_stage, last_utterance, alan_response, conversation_history, merchant_state, compliance_acknowledged, timestamps
- `SessionManager`

**SessionManager Functions:**
- `_load_sessions()` / `_save_sessions()` — JSON file persistence
- `get_session(call_sid, direction, merchant_number)` — get or create
- `update_session(call_sid, **updates)` — update fields
- `add_conversation_turn(call_sid, speaker, message)` — append to history
- `get_conversation_context(call_sid)` — formatted context string (last 5 turns)
- `end_session(call_sid)` — marks stage as "ended"
- `cleanup_old_sessions(days_old=7)` — garbage collection

**Key Logic:** Thread-safe (threading.Lock). JSON file persistence (`call_sessions.json`). Provides formatted conversation context for Alan's response generation.

**Global Instance:** `session_manager = SessionManager()`  
**Integration:** Used by voice pipeline for conversation state tracking.

---

### 34. `session_persistence.py` (~569 lines)

**Category:** Session Persistence (SQLite)  
**Classes:** `SessionPersistenceManager`  
**Functions:**
- `_init_database()` — creates `sessions`, `session_events`, `conversation_turns` tables with indexes
- `save_session(session)` — upsert session state (decorated with `@monitor_session_save`)
- `load_session(session_id)` — retrieves session data (decorated with `@monitor_session_load`)
- `recover_active_sessions()` — finds all active non-terminated sessions (decorated with `@monitor_session_recovery`)
- `log_session_event(session_id, event_type, from_state, to_state, details)` — audit trail
- `save_conversation_turn(session_id, speaker, text, metadata)` — persist conversation (decorated with `@monitor_conversation_save`)
- `get_conversation_history(session_id, limit=50)` — retrieve turns in chronological order
- `terminate_session(session_id)` — marks session inactive
- `cleanup_old_sessions(days=30)` — purges old terminated sessions + orphaned events/turns
- `get_stats()` — total sessions, active sessions, total turns, total events, DB size

**Tables:**
- `sessions`: session_id, user_id, state, created_at, updated_at, terminated_at, metadata (JSON), is_active
- `session_events`: session_id, event_type, from_state, to_state, timestamp, details (JSON)
- `conversation_turns`: session_id, speaker, text, timestamp, metadata (JSON)

**Global Factory:** `get_persistence_manager(db_path)` — singleton  
**DB:** `alan_sessions.db`  
**Integration:** `performance_monitor` decorators, `alan_state_machine.SessionStateMachine`

---

### 35. `workflow_chargeback.py` (~95 lines)

**Category:** n8n Workflow Builder  
**Functions:** `build_chargeback_workflow(name, internal_base_url)`  
**Flow:** Webhook Event → Fetch Evidence → Submit Evidence → Reconcile Chargeback  
**Nodes:** 4 (webhook + 3 HTTP requests to processor.internal)  
**Integration:** Used by `main.py` to create n8n workflow

---

### 36. `workflow_merchant_activate.py` (~50 lines)

**Category:** n8n Workflow Builder  
**Functions:** `build_merchant_activate_workflow(name, internal_base_url)`  
**Flow:** Webhook → Activate Merchant  
**Nodes:** 2 (webhook + HTTP request)  
**Integration:** Used by `main.py`

---

### 37. `workflow_merchant_onboard.py` (~50 lines)

**Category:** n8n Workflow Builder  
**Functions:** `build_merchant_onboard_workflow(name, internal_base_url)`  
**Flow:** Webhook → Create Merchant  
**Nodes:** 2 (webhook + HTTP request)  
**Integration:** Used by `main.py`

---

### 38. `workflow_merchant_release.py` (~50 lines)

**Category:** n8n Workflow Builder  
**Functions:** `build_merchant_release_workflow(name, internal_base_url)`  
**Flow:** Webhook → Release Merchant  
**Nodes:** 2 (webhook + HTTP request)  
**Integration:** Used by `main.py`

---

### 39. `workflow_merchant_review.py` (~50 lines)

**Category:** n8n Workflow Builder  
**Functions:** `build_merchant_review_workflow(name, internal_base_url)`  
**Flow:** Webhook → Update Merchant  
**Nodes:** 2 (webhook + HTTP request)  
**Integration:** Used by `main.py`

---

### 40. `workflow_merchant_suspend.py` (~50 lines)

**Category:** n8n Workflow Builder  
**Functions:** `build_merchant_suspend_workflow(name, internal_base_url)`  
**Flow:** Webhook → Suspend Merchant  
**Nodes:** 2 (webhook + HTTP request)  
**Integration:** Used by `main.py`

---

### 41. `workflow_merchant_underwrite.py` (~50 lines)

**Category:** n8n Workflow Builder  
**Functions:** `build_merchant_underwrite_workflow(name, internal_base_url)`  
**Flow:** Webhook → Update Merchant Risk  
**Nodes:** 2 (webhook + HTTP request)  
**Integration:** Used by `main.py`

---

### 42. `workflow_payout.py` (~95 lines)

**Category:** n8n Workflow Builder  
**Functions:** `build_payout_workflow(name, internal_base_url)`  
**Flow:** Cron Trigger (daily 1:00 AM) → Compute Payouts → Execute Payouts → Reconcile  
**Nodes:** 4 (cron trigger + 3 HTTP requests)  
**Integration:** Used by `main.py`

---

### 43. `workflow_reconciliation_hub.py` (~70 lines)

**Category:** n8n Workflow Builder  
**Functions:** `build_reconciliation_hub_workflow(name, internal_base_url)`  
**Flow:** Webhook → Normalize Payload (JS function node) → Post to Reconciliation Engine  
**Nodes:** 3 (webhook + function + HTTP request)  
**Integration:** Used by `main.py`

---

### 44. `workflow_refund.py` (~80 lines)

**Category:** n8n Workflow Builder  
**Functions:** `build_refund_workflow(name, internal_base_url)`  
**Flow:** Webhook → Create Refund → Reconcile Refund  
**Nodes:** 3 (webhook + 2 HTTP requests)  
**Integration:** Used by `main.py`

---

### 45. `workflow_tx_create_capture.py` (~105 lines)

**Category:** n8n Workflow Builder  
**Functions:** `build_tx_create_and_capture_workflow(name, internal_base_url)`  
**Flow:** Webhook → Create Transaction → Capture Transaction → Reconcile  
**Nodes:** 4 (webhook + 3 HTTP requests)  
**Integration:** Used by `main.py`

---

### 46. `alan_live_call_monitor.py` (~645 lines)

**Category:** Call Monitoring  
**Classes:**
- `CallMetrics` (dataclass) — per-call metrics: turns, words, response times, sentiment, quality, flow validation flags
- `TranscriptEntry` (dataclass) — timestamped transcript entry with sentiment/tone/word count
- `ToneAnalyzer` — regex-based tone classification (excited, frustrated, curious, guarded, neutral)
- `SentimentAnalyzer` — TextBlob-based sentiment (positive/negative/neutral), keyword fallback
- `LiveCallMonitor` — main monitoring engine

**LiveCallMonitor Functions:**
- `start_call(call_sid, session_id, merchant_phone)` — begin monitoring
- `log_greeting_sent()` / `log_agent_wired()` — flow checkpoints
- `log_merchant_speech(call_sid, text, response_time)` — processes merchant speech with tone/sentiment analysis
- `log_alan_response(call_sid, text, response_time)` — tracks Alan's responses with quality checks
- `log_error()` / `log_warning()` — error/warning tracking
- `end_call(call_sid)` — computes final quality score, saves transcript
- `get_call_metrics()` / `get_active_calls()` / `get_transcript()` / `get_recent_alerts()`
- `_check_merchant_alerts()` — alerts on frustration, hang-up phrases, confusion
- `_check_alan_quality()` — alerts on slow responses, very short responses, repetition
- `_calculate_call_quality()` — scoring: flow completion, engagement, errors, warnings, sentiment
- `_save_transcript()` — JSON to `logs/call_transcripts/`

**Quality Score:** Starts at 100, deductions for: no greeting (-30), no agent wired (-30), no merchant response (-20), low engagement (-15), errors (-10 each), warnings (-5 each), negative sentiment (-10). Maps to excellent/good/fair/poor.

**Tone Patterns:** 4 categories with regex — excited (!, wow, great), frustrated (not interested, don't want, busy), curious (?, tell me more, how does), guarded (who is this, how did you get)

**Global Convenience Functions:** `start_monitoring()`, `log_greeting()`, `log_agent_ready()`, `log_merchant()`, `log_alan()`, `log_call_error()`, `log_call_warning()`, `end_monitoring()`, `get_active_calls()`, `get_call_status()`, `get_call_transcript()`, `get_alerts()`

**Integration:** TextBlob (optional), standalone module with global `live_monitor` instance

---

### 47. `_neg_proof_imports.py` (~130 lines)

**Category:** Module Load Test  
**Functions:** `check(name, category)` — attempts `__import__(name)` and records pass/fail with timing

**Module Categories Tested:**
- **CORE PIPELINE** (13 modules): aqi_stt_engine, supervisor, predictive_intent, adaptive_closing, preference_model, master_closer_layer, behavior_adaptation, cognitive_reasoning_governor, outcome_detection, evolution_engine, call_outcome_confidence, outcome_attribution, review_aggregation
- **ALAN V2 ORGANS** (7 modules): system_coordinator, emergency_override_system, post_generation_hallucination_scanner, merchant_identity_persistence, multi_turn_strategic_planning, bias_auditing_system, human_override_api
- **SOFT IMPORTS** (3 modules): alan_replication, alan_call_monitor_integration, aqi_deep_layer
- **BUSINESS AI** (6 modules): agent_alan_business_ai, aqi_agent_x, aqi_redundancy_manager, qpc_kernel, alan_cloaking_protocol, alan_backup_sync
- **QPC SUBSYSTEM** (4 modules): qpc.state, qpc.program, qpc.coherence, qpc.identity
- **SRC MODULES** (12 modules): rate_calculator, crm, memory, context_sovereign_governance, conversation, agent_coach, education, twilio_account_manager, financial_controller, supreme_merchant_ai, north_api, email_service
- **RESTORED MODULES** (11 modules): budget_tracker, autonomous_campaign_runner, merchant_queue, outbound_controller, aqi_lead_importer, aqi_compliance_framework, alan_guardian_engine, alan_live_call_monitor, aqi_voice_governance, alan_state_machine, continuum_engine
- **SUPPORT/UTILITIES** (3 modules): tunnel_sync, lead_database, excel_lead_importer
- **PACKAGES** (4 modules): tools, tools.cooldown_manager, voice_box, voice_box.config
- **CONTROL API** (1 module): control_api_fixed
- **RELAY SERVER** (1 module): aqi_conversation_relay_server

**Output:** Pass/fail count, timing per module, slow module report (>500ms), total import time.

---

### 48. `_neg_proof_timing.py` (~120 lines)

**Category:** Pipeline Timing Test  
**Key Logic:** Measures per-turn latency overhead of the `DeepLayer` module across 10 simulated conversation turns.

**Simulated Turns:** 10 realistic merchant interactions from greeting through close, each with:
- Merchant text
- Sentiment analysis dict (sentiment, signals, objections)
- Master closer state (trajectory, temperature, confidence, endgame_state, merchant_type, caller_energy)

**Metrics Collected:**
- Per-turn `DeepLayer.step()` execution time (μs precision via `time.perf_counter()`)
- Mode and strategy for each turn
- Mode transitions log
- Final continuum field norms (numpy)
- QPC branch count

**Budget:** Deep layer must be <10ms per turn (pass), <50ms marginal, >50ms fail.

**Integration:** `aqi_deep_layer.DeepLayer`, numpy

---

## Architecture Summary

### System Overview

**Agent X** is an AI-powered outbound merchant services sales system with an AI agent named **Alan** that autonomously calls merchants, engages in sales conversations, handles objections, and closes deals.

### Core Pipeline

```
Lead Import → Campaign Runner → Outbound Controller → Twilio Call
    ↓
Voice Session (WebSocket) → STT Engine (Groq/OpenAI Whisper)
    ↓
Alan Response Generator → Voice Governance → TTS (OpenAI Realtime)
    ↓
Call Monitor → SQL Tracker → Transcript Storage
```

### Technology Stack

| Layer | Technology |
|-------|-----------|
| Voice Calls | Twilio (outbound, AMD, payments) |
| STT | Groq Whisper (primary), OpenAI Whisper (fallback) |
| TTS | OpenAI Realtime TTS via relay server |
| LLM | OpenAI GPT (conversation generation) |
| Web Server | FastAPI + WebSocket |
| Desktop GUI | Tkinter + SAPI TTS + SpeechRecognition |
| Database | SQLite (WAL mode, multiple DBs) |
| Lead Queue | JSON file + SQLite migration |
| Workflow Automation | n8n (11 financial/merchant workflows) |
| Tunnel | ngrok (dynamic URL in active_tunnel_url.txt) |
| Deployment | tar.gz + systemd on Ubuntu VPS |

### Database Files

| DB | Purpose |
|----|---------|
| `data/leads.db` | Lead queue and call history |
| `database/alan_communication.db` | Call event tracking |
| `aqi_merchant_services.db` | Resource hunter findings |
| `aqi_compliance.db` | PCI/HIPAA compliance |
| `alan_sessions.db` | Session persistence |
| `call_sessions.json` | In-memory session state |
| `merchant_queue.json` | Legacy lead queue |
| `data/daily_stats.json` | Budget tracking |

### Key Subsystems

1. **QPC (Quantum Processing Core)** — qpc_kernel.py + continuum_engine.py + qpc.* submodules. Quantum branching, fluidic flow regulation, constitutional invariants.
2. **Voice Governance** — Single-speaker lock, heartbeat monitoring, emergency failover, safety overrides.
3. **Campaign Automation** — Business hours enforcement, cooldown management, VERITAS protocol, Vulture protocol, entropy injection.
4. **Compliance** — PCI DSS levels, HIPAA, SOX, GDPR rules, security framework (AES-256, TLS 1.3), 7-year audit retention.
5. **Negative Proof Suite** — Module load verification, pipeline timing, voice interference testing, persistence testing, stress testing.
6. **n8n Workflows** — 11 financial workflows: transactions, refunds, chargebacks, payouts, reconciliation, merchant lifecycle (onboard, underwrite, activate, review, suspend, release).

---

*End of report — all 48 files fully read and documented.*
