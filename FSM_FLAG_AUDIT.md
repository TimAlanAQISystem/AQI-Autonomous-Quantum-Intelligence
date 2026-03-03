# FSM FLAG AUDIT — Comprehensive Boolean & State Variable Catalog
## Files Audited
- `aqi_conversation_relay_server.py` (5498 lines)
- `agent_alan_business_ai.py` (5055 lines)

**Date:** 2026-02-19
**Purpose:** Identify every boolean flag, state variable, and session/context flag that controls conversation flow, session lifecycle, or behavioral state — candidates for FSM replacement.

---

## 1. SESSION LIFECYCLE FLAGS (Start/End of Call)

### `context['stream_ended']`
- **Type:** Boolean (`True`/`False`)
- **SET at:**
  - `relay:2177` — Conversation guard pre-call abort (government entity etc.)
  - `relay:1662` — IVR detector aborts call
  - `relay:2373` — Cost sentinel inbound abort
  - `relay:2389` — Cost sentinel max-duration abort
  - `relay:2456` — Cost sentinel abort
  - `relay:2485` — Cost sentinel IVR abort
  - `relay:2522` — Cost sentinel IVR+score abort
  - `relay:2544` — Cost sentinel abort
  - `relay:2556` — Cost sentinel abort
  - `relay:2735` — Inbound silence (dead air) abort
  - `relay:2863` — WebSocket disconnect (stream stop)
  - `relay:4651` — Conversation guard mid-call abort
  - `relay:5155` — Post-response repetition bail abort
- **READ at:**
  - `relay:1627` — Guard at top of `handle_stt_event`: skip processing if ended
  - `relay:2221` — Main loop break signal
  - `relay:2297` — Sentinel health check
  - `relay:2347,2349` — Sentinel loop exit condition
  - `relay:2586` — Sentinel exit log
  - `relay:4637` — Pre-turn conversation guard check
  - `relay:5096` — Post-analysis conversation guard check
  - `relay:5308` — Force end in cleanup
- **Controls:** Master kill switch for the entire call. When True, all processing stops, WebSocket closes, call ends.

### `context['stream_started']`
- **Type:** Boolean
- **SET at:**
  - `relay:2245` — When Twilio `start` event arrives with streamSid
- **READ at:**
  - `relay:2304` — Sentinel health logging
  - `relay:2654` — Guard: don't process audio until stream started
  - `relay:2665` — Guard: audio processing entry
- **Controls:** Gates all audio processing. Until Twilio sends the `start` event, no VAD/STT runs.

### `context['_killed_by']`
- **Type:** String (e.g., `'inbound_silence'`, `'sentinel'`, `'inbound_sentinel'`)
- **SET at:**
  - `relay:2375` — `'inbound_sentinel'`
  - `relay:2391` — `'sentinel'`
  - `relay:2458` — `'sentinel'`
  - `relay:2487` — `'sentinel'`
  - `relay:2524` — `'sentinel'`
  - `relay:2546` — `'sentinel'`
  - `relay:2558` — `'sentinel'`
  - `relay:2736` — `'inbound_silence'`
- **READ at:**
  - `relay:3187-3189` — End payload logging: records HOW the call died
- **Controls:** Forensic tag identifying the kill reason. Written to call outcome for analytics.

### `context['_system_abort']`
- **Type:** Boolean (inferred, never explicitly set in searched code — may be set by conversation guard)
- **READ at:**
  - `relay:3191` — End-of-call payload
  - `relay:3384` — Post-call CCNM gating
- **Controls:** Marks whether the call was system-aborted (vs. natural end or merchant hangup).

### `context['start_time']`
- **Type:** `datetime` object
- **SET at:**
  - `relay:2079` — Session initialization
- **READ at:**
  - `relay:2878` — Duration calculation at call end
  - `relay:4740` — SignatureExtractor call_start calibration
- **Controls:** Session duration tracking, elapsed-time calculations throughout the call.

### `context['replication_registered']`
- **Type:** Boolean
- **SET at:**
  - `relay:2267` — After successful replication registration
- **READ at:**
  - `relay:3559` — End-of-call replication sync
- **Controls:** Whether this call has been registered with the replication system for cross-device sync.

### `context['error_count']`
- **Type:** Integer (counter)
- **READ at:**
  - `relay:3169` — End payload error tally
- **Controls:** Running count of errors during this session. Read at call end for quality metrics.

---

## 2. CONVERSATIONAL STATE FLAGS (Greeting, Opening, Dialogue, Pitch)

### `context['conversation_state']`
- **Type:** String: `'greeting'` → `'FIRST_GREETING_PENDING'` → `'LISTENING_FOR_CALLER'` → `'dialogue'`
- **SET at:**
  - `relay:2083` — Init: `'greeting'`
  - `relay:3878` — After greeting text generated: `'FIRST_GREETING_PENDING'`
  - `relay:3926` — After greeting audio streamed: `'LISTENING_FOR_CALLER'`
  - `relay:3091` — Fallback greeting path: `'dialogue'`
  - `relay:4687` — First turn complete: `'dialogue'` (normalize)
- **READ at:**
  - `relay:2682` — Audio processing state check
  - `relay:4619` — Top of `handle_user_speech`: reads current state
  - `relay:4685` — First-turn detection gate
  - `relay:4961` — Pitch suppression (checks if `'dialogue'`)
- **Controls:** The closest thing to an explicit state machine. Tracks the 4-phase progression of the call opening. Critical for FSM replacement.

### `context['greeting_sent']`
- **Type:** Boolean
- **SET at:**
  - `relay:2086` — Init: `False`
  - `relay:3081` — Greeting fired: `True`
  - `relay:3877` — Smart greeting routine: `True`
- **READ at:**
  - `relay:2305` — Sentinel health logging
  - `relay:2622,2634` — (commented out) old greeting path
  - `relay:3078,3080` — Guard: prevent double greeting
  - `relay:3845` — Smart greeting: if already sent, return early
- **Controls:** One-shot flag preventing the greeting from being sent twice. Classic candidate for FSM state.

### `context['first_turn_complete']`
- **Type:** Boolean
- **SET at:**
  - `relay:3092` — On greeting path: `False`
  - `relay:4686` — After first merchant speech: `True`
  - (commented: `relay:2645`)
- **READ at:**
  - `relay:1680` — Post-greeting ack suppression: if not complete, suppress acks
  - `relay:4685` — First-turn detection gate
- **Controls:** Marks the transition from "greeting just sent, waiting for response" to "active conversation". After this, pitch suppression and opener blocks disable.

### `context['fallback_suppressed_until']`
- **Type:** Float (Unix timestamp)
- **SET at:**
  - `relay:3093` — On greeting: `time.time() + 20.0`
  - (commented: `relay:2646`)
- **READ at:**
  - `relay:4962` — Pitch suppression check: `if time.time() < context.get('fallback_suppressed_until', 0)`
- **Controls:** Time-based gate that suppresses premature pitching for 20 seconds after the greeting. Prevents Alan from launching into a sales pitch before the human has had a chance to talk.

### `context['responding_ended_at']`
- **Type:** Float (Unix timestamp via `time.time()`)
- **SET at:**
  - `relay:3048` — Twilio `mark` event (playback complete)
  - `relay:3927` — After greeting audio streams
  - `relay:5318` — After normal turn response completes
- **READ at:**
  - `relay:2684` — Echo cooldown calculation: skip VAD for N seconds after speaking
- **Controls:** Echo suppression / cooldown. Prevents Alan from hearing his own audio echo as "user speech" immediately after he stops talking.

---

## 3. BEHAVIORAL CONTROL FLAGS (Suppression, Escalation, Off-Topic, Energy)

### `context['caller_energy']`
- **Type:** String: `'neutral'`, `'stressed'`, `'anxious'`, `'formal'`, `'casual'`, etc.
- **SET at:**
  - `relay:4714` — Overwritten if stressed or neutral
  - `relay:4716` — Overwritten if non-neutral
- **READ at:**
  - `relay:441` — Prosody engine reads energy for TTS tuning
  - `relay:4711` — Previous energy comparison
  - `relay:4718-4719` — Logging
  - `relay:5205` — CDC telemetry
  - `agent:4099` — LLM prompt energy block
- **Controls:** Behavioral tone adaptation. Maps to different prompt injections in `build_llm_prompt()` that tell Alan who he's talking with.

### `context['live_objection_type']`
- **Type:** String or `None` (e.g., `'timing'`, `'budget'`, `'competition'`, `'not_interested'`)
- **SET at:**
  - `relay:4724` — Set when objection detected
  - `relay:4728` — Popped (cleared) when no objection
- **READ at:**
  - `relay:445` — Prosody engine checks for objection
  - `relay:5206` — CDC telemetry
  - `agent:4124` — LLM prompt rebuttal injection
- **Controls:** Triggers rebuttal injection into Alan's prompt. When set, a specific rebuttal strategy block gets injected.

### `context['_ccnm_ignore']`
- **Type:** Boolean
- **SET at:**
  - `relay:1650` — IVR abort
  - `relay:1667` — IVR handling
  - `relay:2180` — Conversation guard abort
  - `relay:2392,2459,2488,2525,2547,2559` — Cost sentinel aborts
  - `relay:2934` — IVR quarantine on exit
  - `relay:4650` — Conversation guard mid-call
- **READ at:**
  - `relay:2516` — Sentinel IVR check
  - `relay:2870` — Post-call CCNM gating
  - `relay:3185` — End payload
  - `relay:3409` — Evolution coaching nudge gating
- **Controls:** Quarantine flag. When True, prevents the CCNM learning system from ingesting this call's data. Used for IVR calls, government entities, and other non-useful calls.

### `context['_personality_flare']`
- **Type:** String or absent
- **SET at:**
  - `relay:5055` — Set when personality matrix generates a flare
  - `relay:5058` — Popped when no flare
- **READ at:**
  - `agent:3912` — `build_llm_prompt()` injects flare into system prompt
- **Controls:** Dynamic personality text injection. Gives Alan a touch of wit/warmth based on current sentiment.

### `context['_ethical_constraint']`
- **Type:** String (reason text) or absent
- **SET at:**
  - `relay:5077` — Set when SoulCore vetoes an action
  - `relay:5080` — Popped when approved
- **READ at:**
  - `agent:3919` — `build_llm_prompt()` injects ethical constraint into system prompt
- **Controls:** Ethical guardrail. Prevents Alan from using deceptive or zero-sum framing when SoulCore detects a problematic situation.

### `context['_repetition_escalation']`
- **Type:** String (`'anchor'`, `'reframe'`) or `None`
- **SET at:**
  - `relay:5002` — Set to `'anchor'` on 2nd repeat
  - `relay:5014` — Set to `'reframe'` on 3rd+ repeat
  - `relay:5022` — Reset to `None` when no repeat
- **READ at:**
  - (Used internally; escalation directive is built and injected into analysis)
- **Controls:** Strategy shift when merchant asks the same question multiple times.

### `context['_repetition_history']`
- **Type:** List of strings (recent user text hashes)
- **SET at:**
  - `relay:4998` — Updated each turn with current text
- **READ at:**
  - `relay:4978` — Read for repeat detection
- **Controls:** Memory buffer for repetition detection. Tracks recent messages to identify repeated questions.

### `context['_coaching_nudge']`
- **Type:** Dict or absent
- **SET at:**
  - `relay:3412` — Set when evolution engine produces a coaching nudge
- **READ at:**
  - (Used in post-call analysis)
- **Controls:** Post-call coaching feedback from the evolution system.

### `context['_conv_intel_rephrase_directive']`
- **Type:** String (directive text) or `None`
- **SET at:**
  - `relay:5160` — When ConvIntel detects repetition → bail
  - `relay:5163` — When ConvIntel detects repetition → rephrase
- **READ at:**
  - `agent:4195-4198` — Injected into LLM prompt, then cleared
- **Controls:** One-shot directive from Conversation Intelligence. Tells Alan to rephrase his answer to avoid repeating himself.

### `context['off_topic_turn_count']`
- **Type:** Integer (counter, set by Agent X support externally)
- **READ at:**
  - `relay:4941` — Logging
- **Controls:** Tracks consecutive off-topic turns. Used by Agent X support to decide when to pivot back to business.

### `context['conversation_guidance']`
- **Type:** String (prompt guidance text, set by Agent X support externally)
- **READ at:**
  - `agent:4187-4188` — Injected into LLM prompt
- **Controls:** Dynamic conversation steering from Agent X when off-topic handling is active.

---

## 4. PIPELINE CONTROL FLAGS (Stream Management, TTS Control)

### `context['audio_playing']`
- **Type:** Boolean
- **SET at:**
  - `relay:1785` — Set `False` when clearing before new turn
  - `relay:2793` — Set `False` on barge-in interrupt
  - `relay:4399` — Set `True` when TTS audio starts streaming
  - `relay:4542` — Set `False` when audio mark event received (send complete)
  - `relay:5316` — Set `False` at turn cleanup end
- **READ at:**
  - `relay:2693` — Echo gate: determines if Twilio is currently playing audio
- **Controls:** Mutex flag: is audio currently being sent to Twilio? Used for barge-in detection. If True, user speech triggers interruption handling.

### `context['twilio_playback_done']`
- **Type:** Boolean
- **SET at:**
  - `relay:1786` — Set `True` when clearing for new turn
  - `relay:2794` — Set `True` on barge-in
  - `relay:3047` — Set `True` on Twilio `mark` event (confirmed playback complete)
  - `relay:4400` — Set `False` when audio starts streaming
- **READ at:**
  - `relay:2694` — Echo gate: if False, Twilio is still playing → suppress VAD
- **Controls:** Companion to `audio_playing`. Distinguishes between "we sent audio" and "Twilio confirmed it finished playing". Prevents echo detection during Twilio's audio playback window.

### `context['first_audio_produced']`
- **Type:** Boolean
- **SET at:**
  - `relay:1771` — Reset `False` for new turn
  - `relay:4404` — Set `True` when first TTS chunk produced for current turn
- **READ at:**
  - `relay:1727` — Accumulation gate: if first audio already sent, decide whether to defer or append
- **Controls:** Tracks whether the first audio chunk for the current response has been sent. Affects whether late-arriving STT can still be accumulated or must start a new turn.

### `context['response_generation']`
- **Type:** Integer (monotonically incrementing counter)
- **SET at:**
  - `relay:1751` — Incremented on accumulated turn retry
  - `relay:1777` — Incremented on new turn start
  - `relay:2792` — Incremented on barge-in (invalidates current response)
  - `relay:2865` — Incremented on stream stop
- **READ at:**
  - `relay:1693` — Back-channel ignore logging
  - `relay:4327` — Supersession check during sentence-by-sentence streaming
  - `relay:4492` — Supersession check during orchestration
  - `relay:4625` — Supersession check at turn start
  - `relay:5315` — Supersession check at cleanup
- **Controls:** Generation counter for response invalidation. Each new user input increments the counter; ongoing response pipelines compare their generation to the current one and abort if superseded. Critical concurrency control.

### `context['response_task']`
- **Type:** `asyncio.Task` object or `None`
- **SET at:**
  - `relay:1760` — Set when accumulated response task launches
  - `relay:1792` — Set when new response task launches
- **READ at:**
  - `relay:1691` — Check for existing active task (back-channel handling)
- **Controls:** Handle to the current running response pipeline task. Used to detect if a response is already in-flight.

### `context['pending_stt_text']`
- **Type:** String
- **SET at:**
  - `relay:1552` — Cleared after combining with STT
  - `relay:1711` — Set when VAD is speaking (accumulate text)
- **READ at:**
  - `relay:1549` — Read pending text
  - `relay:1709` — Read for combination
- **Controls:** Text buffer for partial STT results that arrive while VAD detects continued speech.

### `context['accumulated_stt_text']`
- **Type:** String
- **SET at:**
  - `relay:1747` — Updated with accumulated transcription
  - `relay:1770` — Fresh start on new turn
- **READ at:**
  - `relay:1745` — Previous accumulation read
- **Controls:** Running transcription buffer for the current turn. Combines partial STT results.

### `context['_deferred_text']`
- **Type:** String
- **SET at:**
  - `relay:1741` — Set when STT arrives during active pipeline
- **READ at:**
  - (Consumed by deferred processing logic)
- **Controls:** Holds late-arriving STT text that couldn't interrupt the current pipeline.

### `context['_pipeline_start']`
- **Type:** Float (Unix timestamp)
- **SET at:**
  - `relay:1753` — Reset on accumulated retry
  - `relay:1772` — Set at turn start
- **READ at:**
  - `relay:1731` — Pipeline age calculation
- **Controls:** Timestamp marking when the current response pipeline started. Used to determine if a late STT should defer or start fresh.

### `context['_pipeline_start_time']`
- **Type:** Float (Unix timestamp)
- **SET at:**
  - `relay:4931` — Set before Agent X and analysis processing
- **READ at:**
  - (Passed to context for Agent X latency estimation)
- **Controls:** Secondary pipeline timer for latency estimation in Agent X support.

### `context['_last_turn_latency_ms']`
- **Type:** Float (milliseconds)
- **SET at:**
  - `relay:5236` — Set after full turn completes
- **READ at:**
  - (Available for telemetry/logging)
- **Controls:** Records total turn latency for performance monitoring.

---

## 5. VAD (VOICE ACTIVITY DETECTION) STATE

### `context['vad_state']`
- **Type:** String: `'silence'` or `'speaking'`
- **SET at:**
  - `relay:2812` — Set `'speaking'` when speech detected
  - `relay:2828` — Set `'silence'` when speech ends
  - `relay:5319` — Reset to `'silence'` at turn cleanup
- **READ at:**
  - `relay:1708` — STT handler: if speaking, accumulate
  - `relay:2306` — Sentinel health logging
  - `relay:2770` — VAD processing loop
  - `relay:2777,2813,2822,2833,2838` — VAD state machine transitions
- **Controls:** The VAD mini-state-machine. Tracks whether the merchant is currently speaking. Drives barge-in detection, STT accumulation, and echo suppression.

### `context['vad_speech_frames']`
- **Type:** Integer (frame counter)
- **SET at:**
  - `relay:2699` — Reset to 0 in cooldown
  - `relay:2775` — Incremented on speech frame
  - `relay:2824` — Reset to 0 on silence transition
  - `relay:2836` — Reset to 0 on sustained silence
  - `relay:3928` — Reset to 0 after greeting
  - `relay:5320` — Reset to 0 at cleanup
- **READ at:**
  - `relay:2777` — Barge-in threshold check
  - `relay:2781,2810` — Logging
- **Controls:** Counter for sustained speech frames. Must exceed threshold to trigger barge-in or speech state transition. Prevents noise bursts from being treated as speech.

### `context['vad_last_speech']`
- **Type:** Float (Unix timestamp)
- **SET at:**
  - `relay:2820` — Updated on each speech frame
- **READ at:**
  - `relay:2771` — End-of-speech detection (silence duration)
- **Controls:** Timestamp of last speech. Used to detect end-of-utterance (silence exceeding threshold after speech).

### `context['last_speech_time']`
- **Type:** Float (Unix timestamp or `0`)
- **SET at:**
  - `relay:2085` — Init: `0`
  - `relay:4616` — Updated on each user speech event
- **READ at:**
  - (Available for dead-air detection, timeout logic)
- **Controls:** Top-level speech timestamp for overall call flow. Different from `vad_last_speech` which is frame-level.

---

## 6. EVOLUTION / OUTCOME TRACKING FLAGS

### `context['_evolution_outcome']`
- **Type:** String (e.g., `'ivr_system'`, `'government_entity'`, `'repetition_bail'`, `'sale'`, `'not_interested'`, etc.)
- **SET at:**
  - `relay:1645` — IVR detection outcome
  - `relay:2178` — Conversation guard outcome
  - `relay:2872` — Default on CCNM-ignored exit
  - `relay:2968` — CoC classification outcome
  - `relay:3159` — NFC reclassification
  - `relay:4648` — Conversation guard mid-call
  - `relay:5156` — Post-response bail
- **READ at:**
  - `relay:1663` — Logging
  - `relay:2872` — Default fill
  - `relay:3155` — End-of-call NFC reclassification
  - `relay:3180` — End payload
- **Controls:** The final classification of how this call ended. Critical for analytics and CCNM learning.

### `context['_evolution_confidence']`
- **Type:** Float (0.0-1.0)
- **SET at:**
  - `relay:1646` — IVR score
  - `relay:2873` — Default 0.0
  - `relay:2969` — CoC confidence
- **READ at:**
  - `relay:3181` — End payload
- **Controls:** Confidence of the outcome classification.

### `context['_evolution_band']`
- **Type:** String (`'high'`, `'quarantined'`, `'low'`, etc.)
- **SET at:**
  - `relay:1647` — `'high'` for IVR
  - `relay:2874` — `'quarantined'`
  - `relay:2970` — CoC band
- **READ at:**
  - `relay:3182` — End payload
- **Controls:** Confidence band for outcome classification.

### `context['_evolution_engagement']`
- **Type:** Float (0.0-1.0)
- **SET at:**
  - `relay:1648` — `0.0` for IVR
  - `relay:2875` — `0.0`
  - `relay:2971` — CoC engagement
- **READ at:**
  - `relay:3183` — End payload
- **Controls:** Engagement score of the merchant during the call.

### `context['_guard_outcome']`
- **Type:** String (outcome label)
- **SET at:**
  - `relay:2179` — Conversation guard pre-call abort
  - `relay:4649` — Conversation guard mid-call
  - `relay:5157` — Post-response bail
- **READ at:**
  - (Used in end-of-call reporting)
- **Controls:** Separate outcome tag from conversation guard (distinct from evolution outcome).

---

## 7. MASTER CLOSER / SALES STATE (Nested Dict)

### `context['master_closer_state']`
- **Type:** Dict with keys:
  - `'trajectory'`: String (`'neutral'`, `'warming'`, `'cooling'`, etc.)
  - `'merchant_type'`: String (`'unknown'`, `'impatient'`, `'analytical'`, etc.)
  - `'temperature'`: Integer (0-100)
  - `'confidence_score'`: Integer (0-100)
  - `'endgame_state'`: String (`'not_ready'`, `'ready'`)
- **SET at:**
  - `relay:4696-4703` — Initialized with defaults
  - `relay:4783-4832` — Updated every turn by master closer engine
- **READ at:**
  - `relay:443-444` — Prosody engine reads trajectory + endgame
  - `relay:2883` — CDC signals
  - `relay:2886` — Endgame check in signals
  - `relay:2943` — Call memory objections
  - `relay:2954-2955` — CoC context
  - `relay:3161-3167` — End payload
  - `relay:3454-3455` — Call outcome
  - `relay:3485` — Trajectory
  - `relay:3522-3523` — Health check
  - `relay:4734` — Signature extractor
  - `relay:5172` — CDC turn telemetry
  - `relay:5246-5247` — Closing readiness
  - `agent:4079` — Default behavior profile reference
- **Controls:** The sales pipeline state. Tracks how "warm" the merchant is, what type of merchant, and whether it's time to attempt a close. This is a sub-state-machine on its own.

---

## 8. BEHAVIORAL ADAPTATION / PROFILE (Nested Dict)

### `context['behavior_profile']`
- **Type:** Dict with keys: `tone`, `pacing`, `formality`, `assertiveness`, `rapport_level`, `pivot_style`, `closing_bias`, `compression_mode`, `expansion_mode`, `deep_layer_mode`, `deep_layer_strategy`
- **SET at:**
  - `relay:4838-4848` — Locked to stable consultative defaults each turn
  - `relay:4872-4873` — Deep layer mode/strategy injected
  - `relay:5033` — NFC dynamic behavior overwrite
- **READ at:**
  - `relay:2997-2998` — CDC bias matching
  - `relay:3176-3178` — End payload
  - `relay:5032` — NFC integration check
  - `relay:5173,5175-5176` — CDC turn telemetry
  - `relay:5213` — Deep layer blend
  - `relay:5253-5254` — Closing style override
  - `agent:4073-4079` — LLM prompt behavior block
- **Controls:** Per-turn behavioral adaptation parameters. Currently locked to defaults but can be dynamically overridden by NFC and Deep Layer.

### `context['behavior_profile']['compression_mode']`
- **Type:** Boolean
- **Default:** `False`
- **Controls:** When True, instructs Alan to use shorter, more compressed responses. Activated by behavior adaptation.

### `context['behavior_profile']['expansion_mode']`
- **Type:** Boolean
- **Default:** `False`
- **Controls:** When True, instructs Alan to use longer, more detailed responses. Opposite of compression_mode.

---

## 9. PERCEPTION & INTELLIGENCE ENGINE FLAGS

### `context['_last_analysis']`
- **Type:** Dict (full analysis output from `analyze_business_response`)
- **SET at:**
  - `relay:4771` — Stored after analysis
- **READ at:**
  - (Available for cross-turn comparison)
- **Controls:** Cached analysis from the previous turn. Allows comparison between turns.

### `context['last_predicted_intent']`
- **Type:** String (intent name)
- **SET at:**
  - `relay:4921` — From predictive engine
- **READ at:**
  - `relay:5177` — CDC telemetry
- **Controls:** Most recently predicted intent from the predictive engine.

### `context['last_predicted_objection_type']`
- **Type:** String (objection type)
- **SET at:**
  - `relay:4922` — From predictive engine
- **READ at:**
  - `relay:5178` — CDC telemetry
- **Controls:** Most recently predicted objection type.

### `context['reasoning_block']`
- **Type:** String (CRG reasoning text)
- **SET at:**
  - `relay:4857` — Built by Cognitive Reasoning Governor
- **READ at:**
  - `agent:4093-4094` — Injected into LLM prompt
  - `relay:5228` — CDC telemetry (truncated)
- **Controls:** Per-turn reasoning directive from the CRG that shapes Alan's response strategy.

---

## 10. DEEP LAYER / NFC FLAGS

### `context['deep_layer']`
- **Type:** `DeepLayer` object or `None`
- **SET at:**
  - `relay:2130` — Initialized on session start
  - `relay:2135` — Set `None` if init fails
- **READ at:**
  - `relay:4864-4868` — Called each turn to get deep state
  - `relay:5174` — CDC telemetry
- **Controls:** Per-session deep layer engine instance. Provides QPC strategy, fluidic mode, and continuum fields.

### `context['_nfc']`
- **Type:** NFC (Neural Flow Cortex) instance or `None`
- **SET at:**
  - `relay:2154` — Initialized on session start
  - `relay:2157` — Set `None` if init fails
- **READ at:**
  - `relay:5025` — Called each turn to harmonize state
- **Controls:** Per-session NFC instance that harmonizes all behavioral organs.

### `context['_conversation_guard']`
- **Type:** ConversationGuard object
- **SET at:**
  - `relay:2171` — Initialized on session start
- **READ at:**
  - `relay:3390` — Post-call evolution report
  - `relay:4638` — Pre-turn guard check
  - `relay:5097,5145,5184` — Post-turn guard checks
- **Controls:** Conversation intelligence guard that can abort calls (repetition, government entity, etc.).

---

## 11. MERCHANT IDENTITY & PERSISTENCE FLAGS

### `context['merchant_id']`
- **Type:** String
- **SET at:**
  - `relay:2595` — From Twilio parameters
- **READ at:**
  - `relay:3449,3487-3488` — MIP profile save
  - `relay:3572` — Replication payload
- **Controls:** Unique merchant identifier for MIP profile persistence.

### `context['merchant_profile']`
- **Type:** Dict (MIP profile)
- **SET at:**
  - `relay:2603` — Loaded from MIP
- **READ at:**
  - `agent:4778` — process_conversation MTSP
- **Controls:** Loaded merchant profile from persistence.

### `context['mtsp_plan']`
- **Type:** Dict (MTSP plan)
- **SET at:**
  - `relay:2612` — Loaded from MIP
- **READ at:**
  - `agent:4768` — process_conversation plan injection
- **Controls:** Merchant-specific sales strategy plan.

### `context['preferences']`
- **Type:** Dict (MerchantPreferences)
- **SET at:**
  - `relay:2607` — Restored from MIP
  - `relay:4692` — Default initialization
  - `relay:4780` — Updated each turn
- **READ at:**
  - `relay:3468` — Call outcome
  - `relay:4776-4779` — Preference update
  - `relay:5255-5256` — Closing style bias
  - `agent:3993-3994` — LLM prompt preferences
- **Controls:** Running merchant preference model (communication style, interests, pace).

### `context['call_memory']`
- **Type:** Dict (CallMemory serialized)
- **SET at:**
  - `relay:4705` — Default initialization
  - `relay:4826` — Updated each turn
- **READ at:**
  - `relay:2943` — Objection check
  - `relay:3464` — Call outcome
  - `relay:4811` — CallMemory deserialization
  - `agent:4007-4008` — LLM prompt memory block
- **Controls:** Persistent call memory tracking objections, key moments, named entities.

### `context['is_returning']`
- **Type:** Boolean (inferred — not explicitly set in relay, may come from MIP)
- **READ at:**
  - `agent:4058` — Previous conversation injection
  - `agent:4277` — Greeting generation
- **Controls:** Whether this merchant has been called before.

---

## 12. AUDIO/SIGNATURE FLAGS

### `context['_effective_signature']`
- **Type:** VocalSignature object or `None`
- **SET at:**
  - `relay:2201` — Computed on session start
  - `relay:2208` — Set `None` if init fails
  - `relay:4743` — Updated each turn
- **READ at:**
  - `relay:2203-2204` — Logging
  - `relay:3162` — End payload
  - `relay:4048` — Prosody engine
- **Controls:** Merchant's vocal signature (speed bias, silence bias). Affects TTS speed and pause timing.

### `context['_signature_extractor']`
- **Type:** SignatureExtractor object or `None`
- **SET at:**
  - `relay:2198` — Initialized on session start
  - `relay:2207` — Set `None` if init fails
- **READ at:**
  - `relay:3439` — Post-call analysis
  - `relay:4546` — Audio complete processing
  - `relay:4731` — Per-turn update
- **Controls:** Engine that analyzes merchant's voice to extract signature features.

### `context['_turn_telemetry']`
- **Type:** Dict
- **SET at:**
  - `relay:4569` — After audio completes
- **READ at:**
  - `relay:5187` — Guard post-turn
  - `relay:5209-5210` — CDC turn report
- **Controls:** Per-turn performance metrics (LLM latency, TTS latency, total time).

### `context['alan_turn_count']`
- **Type:** Integer (counter)
- **READ at:**
  - `relay:4573` — Turn number calculation
- **Controls:** Running count of Alan's response turns.

### `context['_last_dead_air_log']`
- **Type:** Float (Unix timestamp)
- **SET at:**
  - `relay:2731` — Throttled dead-air logging
- **READ at:**
  - `relay:2728` — 5-second throttle check
- **Controls:** Prevents dead-air warning logs from spamming (one log every 5 seconds max).

### `context['_early_media_buffer']`
- **Type:** List
- **SET at:**
  - `relay:2660` — Audio buffer before stream_started
- **READ at:**
  - `relay:2658` — Check for existing buffer
- **Controls:** Buffers audio frames received before stream officially starts.

---

## 13. PROSPECT / SESSION IDENTITY FLAGS

### `context['streamSid']`
- **Type:** String (Twilio stream ID)
- **SET at:**
  - `relay:2238` — From Twilio start event
  - `relay:3669` — From conversation start handler
- **READ at:**
  - `relay:1657,1784` — Audio streaming
  - `relay:2183` — Guard abort
  - `relay:2709,2786,2797,2801,2831` — VAD/STT operations
  - `relay:3036` — STT session close
  - `relay:3882,4027` — Greeting/response streaming
  - Many more
- **Controls:** Twilio's media stream identifier. Required for all audio operations.

### `context['call_sid']`
- **Type:** String (Twilio call SID)
- **SET at:**
  - `relay:2239` — From Twilio start event
- **READ at:**
  - `relay:2720,2747,2852` — Monitoring
  - `relay:3012,3138` — Call tracking
  - `relay:3252,3276,3379,3395,3421` — CDC/Evolution
  - `relay:4667,4753,4757` — Turn tracking
  - `relay:5200,5262,5264,5268,5282,5289` — Telemetry
- **Controls:** Twilio's call identifier. Used for all monitoring, logging, and tracking.

### `context['prospect_info']`
- **Type:** Dict with keys: `name`, `company`, `phone`, `business`, `call_direction`, `rse_data`, `signal`, `strategy`
- **SET at:**
  - `relay:3672-3692` — From conversation start handler
- **READ at:**
  - `relay:3084,3684-3692` — Greeting generation
  - `relay:3518-3523,3570-3571` — Call outcome
  - `relay:3782-3791` — Smart greeting
  - `agent:4259-4260,4340` — LLM prompt
- **Controls:** Who is being called. Includes name, company, RSE intelligence, call direction.

### `context['client_id']`
- **Type:** String/UUID
- **SET at:**
  - `relay:2078` — Session initialization
- **READ at:**
  - `relay:4028,4605` — Behavioral fusion lookups
- **Controls:** Internal session identifier.

### `context['websocket']`
- **Type:** WebSocket connection object
- **SET at:**
  - `relay:2246` — On stream start
- **READ at:**
  - `relay:1541` — STT handler
- **Controls:** Reference to the active WebSocket for sending audio back to Twilio.

---

## 14. FLAGS IN `agent_alan_business_ai.py` (Internal Agent State)

### `analysis['is_off_topic']`
- **Type:** Boolean
- **SET at:**
  - `agent:2798` — Init `False`
  - `agent:2811` — Set `True` on off-topic keyword match
- **READ at:**
  - `relay:4938,4942` — Agent X support processing
  - `relay:4953` — Negative sentiment gate
  - `relay:5220` — CDC telemetry
- **Controls:** Whether the merchant's response is off-topic (weather, personal life, etc.). Triggers rapport handling.

### `analysis['pitch_intent']`
- **Type:** String or `None` (set by Agent X support)
- **READ at:**
  - `relay:4961` — Phase 1.7 pitch suppression
  - `relay:4964` — Cleared when suppressed
- **Controls:** Whether the analysis detects Alan should pitch. Suppressed during the opening lock period.

### `analysis['interest_level']`
- **Type:** String: `'unknown'`, `'high'`, `'low'`
- **SET at:**
  - `agent:2800` — Init `'unknown'`
  - `agent:2841-2845` — Set based on keywords
- **READ at:**
  - `relay:5247` — Closing readiness check
- **Controls:** Merchant's interest level. When `'high'`, triggers closing strategy activation.

### `analysis['sentiment']`
- **Type:** String: `'neutral'`, `'positive'`, `'negative'`, `'extravagant'`
- **SET at:**
  - `agent:2797` — Init `'neutral'`
  - `agent:2836-2839` — Set by keyword analysis
- **READ at:**
  - `relay:4953` — Negative sentiment handling
  - (Many places for tone adaptation)
- **Controls:** Merchant sentiment. Drives personality matrix, energy mirroring, and tone adaptation.

### `context['previous_conversations']`
- **Type:** List of previous conversation dicts (from MIP)
- **READ at:**
  - `agent:4058,4060` — Previous conversation injection
  - `agent:4277` — Greeting generation
- **Controls:** History of previous calls with this merchant. Enables relationship continuity.

### `context['previous_call_memories']`
- **Type:** List of CallMemory dicts (from MIP)
- **READ at:**
  - `agent:4033,4036` — Previous call memory injection
- **Controls:** Structured memories from previous calls (objections, interests, key moments).

### `context['deep_layer_state']`
- **Type:** Dict (from deep_layer.step())
- **READ at:**
  - `agent:4162` — Deep layer prompt injection
- **Controls:** Deep layer strategy state passed to LLM prompt builder.

### `context['_nfc_guidance']`
- **Type:** String (inferred from agent code)
- **READ at:**
  - `agent:4253-4254` — Injected into LLM prompt
- **Controls:** NFC's direct guidance text for the LLM.

---

## SUMMARY STATISTICS

| Category | Flag Count |
|---|---|
| 1. Session Lifecycle | 7 |
| 2. Conversational State | 5 |
| 3. Behavioral Control | 12 |
| 4. Pipeline Control | 10 |
| 5. VAD State | 4 |
| 6. Evolution/Outcome | 5 |
| 7. Master Closer State | 5 (nested) |
| 8. Behavior Profile | 11 (nested) |
| 9. Perception/Intelligence | 4 |
| 10. Deep Layer/NFC | 3 |
| 11. Merchant Identity | 7 |
| 12. Audio/Signature | 6 |
| 13. Session Identity | 5 |
| 14. Agent Analysis | 6 |
| **TOTAL** | **~90 flags** |

---

## FSM REPLACEMENT PRIORITY

### Tier 1 — Core FSM States (replace first)
These are the flags that directly model a linear state progression and are the strongest candidates for FSM states:

1. **`conversation_state`** — Already acts as a string state: `greeting` → `FIRST_GREETING_PENDING` → `LISTENING_FOR_CALLER` → `dialogue`
2. **`greeting_sent`** — Redundant with `conversation_state` being past `greeting`
3. **`first_turn_complete`** — Redundant with `conversation_state` being `dialogue` after first turn
4. **`stream_ended`** — Terminal state
5. **`stream_started`** — Pre-start state
6. **`audio_playing`** / **`twilio_playback_done`** — Sub-FSM for audio pipeline state

### Tier 2 — Sub-FSMs (model as nested state machines)
7. **`vad_state`** — Already a 2-state FSM (`silence`/`speaking`)
8. **`master_closer_state`** — Sales pipeline sub-FSM with trajectory/endgame
9. **`_repetition_escalation`** — 3-state escalation (`None`/`anchor`/`reframe`)

### Tier 3 — Context variables (keep as context data, not FSM states)
10. Everything else — these are data values that influence behavior but don't represent states. They should be attached as context data to FSM states.
