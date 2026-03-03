#!/usr/bin/env python3
"""
AQI CONVERSATION RELAY SERVER
=============================
WebSocket server for handling Twilio ConversationRelay AI conversations
"""

import sys
import codecs

# [FIX] Force UTF-8 for Windows Console to prevent 'charmap' crashes on Emojis
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

import asyncio
import json
import traceback
import websockets
from websockets.exceptions import ConnectionClosed
import logging
import time
from datetime import datetime
import base64
import os
import audioop # [FIX] Required for VAD Logic
import math    # [RING TONE] Sine wave generation for phone ring
import random
import re  # [VERSION O] Sentence boundary detection for per-sentence TTS
import queue as thread_queue  # [VERSION R+] Thread-safe queue for orchestrated LLM→TTS pipeline
import urllib.request  # [VERSION R+] Direct SSE streaming for orchestrated pipeline

import requests
from openai import OpenAI as OpenAIClient  # OpenAI TTS (voice=echo, model=tts-1)
from concurrent.futures import ThreadPoolExecutor
import aqi_stt_engine # [FIX] Import STT Engine for Twilio Media Streams
from supervisor import AlanSupervisor
from predictive_intent import PredictiveIntentEngine
from adaptive_closing import ClosingStrategyEngine
from preference_model import MerchantPreferences, update_preferences, apply_preferences_to_response
from master_closer_layer import MasterCloserLayer, CallMemory
from behavior_adaptation import BehaviorAdaptationEngine
from cognitive_reasoning_governor import CognitiveReasoningGovernor
from outcome_detection import OutcomeDetectionLayer
from evolution_engine import EvolutionEngine
from call_outcome_confidence import CallOutcomeConfidenceScorer
from outcome_attribution import OutcomeAttributionEngine
from review_aggregation import ReviewAggregationEngine
from perception_fusion_engine import PerceptionFusionEngine, PerceptionSnapshot
from behavioral_fusion_engine import BehavioralFusionEngine, BehavioralSnapshot
from timing_loader import TIMING  # [TIMING CONFIG] Central timing mixing board
from coaching_tags_engine import derive_coaching_tags
from governor_behavior_bridge import decide_governor_action, GovernorAction
from chatbot_immune_system import clean_sentence as _chatbot_clean_sentence  # [RELAY DECOMPOSITION] Extracted chatbot killer
from alan_state_machine import CallSessionFSM, CallFlowState, CallFlowEvent  # [PHASE 2] Deterministic call lifecycle FSM
from conversation_health_monitor import ConversationHealthMonitor, HealthLevel  # [PHASE 3A] Organism self-awareness
from telephony_health_monitor import TelephonyHealthMonitor, TelephonyHealthState  # [PHASE 3B] Telephony perception

# [AGENT X SUPPORT] Off-topic conversation intelligence for Alan
try:
    from agent_x_conversation_support import AgentXConversationSupport
    AGENT_X_SUPPORT_WIRED = True
    logging.info("[ORGAN] Agent X Conversation Support WIRED")
except ImportError as e:
    AGENT_X_SUPPORT_WIRED = False
    logging.warning(f"[ORGAN] Agent X Conversation Support unavailable: {e}")

# [IQ CORES] Agent X's 5-core cognitive architecture
try:
    from iqcores import IQCoreOrchestrator
    IQCORES_AVAILABLE = True
    logging.info("[ORGAN] IQ Core Orchestrator WIRED — 5 cores available")
except ImportError as e:
    IQCORES_AVAILABLE = False
    logging.warning(f"[ORGAN] IQ Cores unavailable: {e}")

# [ALAN V2] New System Imports
from system_coordinator import SystemCoordinator
from emergency_override_system import EmergencyOverrideSystem
from post_generation_hallucination_scanner import PostGenerationHallucinationScanner
from merchant_identity_persistence import MerchantIdentityPersistence
from multi_turn_strategic_planning import MultiTurnStrategicPlanner
from bias_auditing_system import BiasAuditingSystem
from human_override_api import HumanOverrideAPI
from personality_engine import PersonalityEngine

# [REPLICATION] Alan fleet replication engine — concurrent call tracking & Hive Mind
try:
    from alan_replication import get_replication_engine
    REPLICATION_WIRED = True
    logging.info("[ORGAN] Replication Engine WIRED")
except ImportError as e:
    REPLICATION_WIRED = False
    logging.warning(f"[ORGAN] Replication Engine unavailable: {e}")

# [ORGAN RECONNECT] Call Monitor Integration — live call visibility
try:
    from alan_call_monitor_integration import (
        monitor_call_start,
        monitor_greeting_sent,
        monitor_agent_wired,
        monitor_merchant_speech,
        monitor_alan_response,
        monitor_call_error,
        monitor_call_warning,
        monitor_call_end,
    )
    CALL_MONITOR_WIRED = True
    logging.info("[ORGAN] Call Monitor Integration WIRED")
except ImportError as e:
    CALL_MONITOR_WIRED = False
    logging.warning(f"[ORGAN] Call Monitor Integration unavailable: {e}")

# [CAPTURE] Non-intrusive call data capture system
try:
    from call_data_capture import (
        capture_call_start as _cdc_call_start,
        capture_greeting as _cdc_greeting,
        capture_turn as _cdc_turn,
        capture_error as _cdc_error,
        capture_call_end as _cdc_call_end,
        capture_evolution as _cdc_evolution,
        capture_coaching as _cdc_coaching,
        capture_environment as _cdc_environment,
    )
    CALL_CAPTURE_WIRED = True
    logging.info("[ORGAN] Call Data Capture System WIRED")
except ImportError as e:
    CALL_CAPTURE_WIRED = False
    logging.warning(f"[ORGAN] Call Data Capture unavailable: {e}")

# [CLASSIFIER] Call-type fusion classifier
try:
    from call_type_classifier import CallTypeClassifier
    from call_feature_aggregator import CallFeatureAggregator
    from classifier_config_loader import ClassifierConfigLoader
    _clf_config_loader = ClassifierConfigLoader()
    _clf_config = _clf_config_loader.get_or_default(CallTypeClassifier.DEFAULT_CONFIG)
    _call_type_classifier = CallTypeClassifier(_clf_config)
    _call_feature_aggregator = CallFeatureAggregator()
    CLASSIFIER_WIRED = True
    logging.info("[ORGAN] Call-Type Classifier WIRED")
except ImportError as e:
    CLASSIFIER_WIRED = False
    _call_type_classifier = None
    _call_feature_aggregator = None
    logging.warning(f"[ORGAN] Call-Type Classifier unavailable: {e}")

# [VOICE SENSITIZER] Real-time voice identity integrity monitor
try:
    from voice_sensitizer import VoiceSensitizer, VoiceSensitizerConfig, VoiceWindowMetrics
    _vs_config = VoiceSensitizerConfig(path="voice_sensitizer_config.yaml")
    _voice_sensitizer = VoiceSensitizer(_vs_config)
    VOICE_SENSITIZER_WIRED = True
    logging.info("[ORGAN] Voice Sensitizer WIRED")
except ImportError as e:
    VOICE_SENSITIZER_WIRED = False
    _voice_sensitizer = None
    logging.warning(f"[ORGAN] Voice Sensitizer unavailable: {e}")

# [INBOUND SILENCE SENSITIZER] Detects dead air / connection loss
try:
    from inbound_silence_sensitizer import InboundSilenceSensitizer, DEFAULT_INBOUND_CONFIG
    import yaml
    try:
        with open("inbound_silence_config.yaml", "r") as f_in:
            _inbound_config = yaml.safe_load(f_in)
    except Exception:
        _inbound_config = DEFAULT_INBOUND_CONFIG
    _inbound_sensitizer = InboundSilenceSensitizer(_inbound_config)
    INBOUND_SENSITIZER_WIRED = True
    logging.info("[ORGAN] Inbound Silence Sensitizer WIRED")
except ImportError as e:
    INBOUND_SENSITIZER_WIRED = False
    _inbound_sensitizer = None
    logging.warning(f"[ORGAN] Inbound Silence Sensitizer unavailable: {e}")

# [LIVE MONITOR] Real-time call state + human voice frequency detection
try:
    from live_call_monitor import LiveCallMonitor, analyze_voice_frame
    LIVE_MONITOR_WIRED = True
    _live_monitor = LiveCallMonitor.get_instance()
    logging.info("[ORGAN] Live Call Monitor + Human Voice Detector WIRED")
except ImportError as e:
    LIVE_MONITOR_WIRED = False
    _live_monitor = None
    logging.warning(f"[ORGAN] Live Call Monitor unavailable: {e}")

# [IVR DETECTOR] Inline IVR/voicemail phone tree detection
try:
    from ivr_detector import IVRDetector
    IVR_DETECTOR_WIRED = True
    logging.info("[ORGAN] IVR Detector WIRED")
except ImportError as e:
    IVR_DETECTOR_WIRED = False
    logging.warning(f"[ORGAN] IVR Detector unavailable: {e}")

# [EAB] Environment-Aware Behavior — first-utterance call environment classifier
try:
    from call_environment_classifier import (
        CallEnvironmentClassifier, EnvironmentClass, EnvironmentAction,
        EnvironmentBehaviorTemplates, ClassificationResult, create_classifier,
    )
    EAB_WIRED = True
    logging.info("[ORGAN] Environment-Aware Behavior (EAB) WIRED — 10 environment classes online")
except ImportError as e:
    EAB_WIRED = False
    logging.warning(f"[ORGAN] EAB unavailable: {e}")

# [CONV INTEL] Conversational Intelligence — DNC, voicemail, entity, repetition, latency, dead-end, coaching
try:
    from conversational_intelligence import ConversationGuard, ShortCallOutcomeFallback
    CONV_INTEL_WIRED = True
    logging.info("[ORGAN] Conversational Intelligence WIRED — 8 behavioral systems online (incl. coaching)")
except ImportError as e:
    CONV_INTEL_WIRED = False
    logging.warning(f"[ORGAN] Conversational Intelligence unavailable: {e}")

# [DNC] Do-Not-Call auto-suppressor — persists DNC flags when merchants request removal
try:
    from dnc_manager import DNCManager, get_dnc_manager, is_dnc_request
    DNC_WIRED = True
    _dnc_mgr = get_dnc_manager()
    logging.info("[ORGAN] DNC Manager WIRED — auto-suppression online")
except ImportError as e:
    DNC_WIRED = False
    _dnc_mgr = None
    logging.warning(f"[ORGAN] DNC Manager unavailable: {e}")

# [INBOUND FILTER] Filters inbound spam calls ("there" callbacks)
try:
    from inbound_filter import is_inbound_spam, classify_inbound
    INBOUND_FILTER_WIRED = True
    logging.info("[ORGAN] Inbound Spam Filter WIRED")
except ImportError as e:
    INBOUND_FILTER_WIRED = False
    logging.warning(f"[ORGAN] Inbound Spam Filter unavailable: {e}")

# [MAINTENANCE] Operational maintenance scheduler
try:
    from operational_maintenance import MaintenanceScheduler
    MAINTENANCE_WIRED = True
    _maintenance_scheduler = MaintenanceScheduler()
    logging.info("[ORGAN] Operational Maintenance Scheduler WIRED")
except ImportError as e:
    MAINTENANCE_WIRED = False
    _maintenance_scheduler = None
    logging.warning(f"[ORGAN] Maintenance Scheduler unavailable: {e}")

# [DEEP LAYER] QPC + Fluidic + Continuum integration
try:
    from aqi_deep_layer import DeepLayer
    DEEP_LAYER_WIRED = True
    logging.info("[ORGAN] Deep Layer (QPC + Fluidic + Continuum) WIRED")
except ImportError as e:
    DEEP_LAYER_WIRED = False
    logging.warning(f"[ORGAN] Deep Layer unavailable: {e}")

# [BEHAVIORAL FUSION LAYER]
_behavioral_engines = {} 
_behavioral_stats = {} 
try:
    with open("behavioral_fusion_config.yaml", "r") as f:
        _BEHAVIORAL_CFG = yaml.safe_load(f)
    BEHAVIORAL_FUSION_WIRED = True
    logging.info("[ORGAN] Behavioral Fusion Layer WIRED")
except Exception as e:
    BEHAVIORAL_FUSION_WIRED = False
    logging.warning(f"[ORGAN] Behavioral Fusion unavailable: {e}")
    _BEHAVIORAL_CFG = {}

# [PERCEPTION FUSION CONFIG]
try:
    with open("perception_fusion_config.yaml", "r") as f:
        _PERCEPTION_CFG = yaml.safe_load(f)
except Exception:
    _PERCEPTION_CFG = {}

# [NFC] Neural Flow Cortex — central nervous system unifying all organs
try:
    from neural_flow_cortex import NeuralFlowCortex, create_nfc
    NFC_WIRED = True
    logging.info("[ORGAN] Neural Flow Cortex WIRED — 12D behavioral flow")
except ImportError as e:
    NFC_WIRED = False
    logging.warning(f"[ORGAN] Neural Flow Cortex unavailable: {e}")

# [CCNM] Cross-Call Neural Memory — accumulated intelligence feedback loop
try:
    from cross_call_intelligence import seed_session as ccnm_seed_session, neutral_seed
    CCNM_WIRED = True
    logging.info("[ORGAN] Cross-Call Neural Memory (CCNM) WIRED — Alan learns across calls")
except ImportError as e:
    CCNM_WIRED = False
    logging.warning(f"[ORGAN] CCNM unavailable (neutral seeds only): {e}")

# [AQI 0.1mm CHIP] Runtime Guard — constitutional conformance engine
try:
    from aqi_runtime_guard import create_runtime_guard, AQIViolationType
    AQI_GUARD_WIRED = True
    logging.info("[ORGAN] AQI 0.1mm Chip Runtime Guard WIRED — 6 enforcement organs")
except ImportError as e:
    AQI_GUARD_WIRED = False
    logging.warning(f"[ORGAN] AQI Runtime Guard unavailable: {e}")

# [PHASE 4] Trace Exporter — emits canonical Phase4CallTrace JSONL for Phase 5 ingestion
try:
    from phase4_trace_exporter import Phase4TraceExporter
    PHASE4_EXPORTER_WIRED = True
    logging.info("[ORGAN] Phase 4 Trace Exporter WIRED — canonical telemetry export")
except ImportError as e:
    PHASE4_EXPORTER_WIRED = False
    logging.warning(f"[ORGAN] Phase 4 Trace Exporter unavailable: {e}")

# [PHASE 5] Streaming Analyzer — real-time behavioral intelligence from Phase 4 traces
# This CLOSES the reflex arc: Phase4 traces → Phase5 analysis → CCNM → next call's DeepLayer
try:
    from aqi_phase5_streaming_analyzer import Phase5StreamingAnalyzer
    _phase5_analyzer = Phase5StreamingAnalyzer()
    PHASE5_ANALYZER_WIRED = True
    logging.info("[ORGAN] Phase 5 Streaming Analyzer WIRED — behavioral intelligence loop CLOSED")
except ImportError as e:
    _phase5_analyzer = None
    PHASE5_ANALYZER_WIRED = False
    logging.warning(f"[ORGAN] Phase 5 Streaming Analyzer unavailable: {e}")

# [ORGAN 24] Retrieval Cortex — mid-call RAG knowledge retrieval (v4.1 ARMS-LEGS-REACH)
try:
    from organs_v4_1.organ_24_retrieval_cortex import RetrievalCortex
    RETRIEVAL_CORTEX_WIRED = True
    logging.info("[ORGAN 24] Retrieval Cortex WIRED — mid-call RAG online")
except ImportError as e:
    RETRIEVAL_CORTEX_WIRED = False
    logging.warning(f"[ORGAN 24] Retrieval Cortex unavailable: {e}")

# [ORGAN 34] Competitive Intel — competitor data store + positioning (v4.1 ARMS-LEGS-REACH)
try:
    from organs_v4_1.organ_34_competitive_intel import CompetitiveIntelOrgan
    COMPETITIVE_INTEL_WIRED = True
    # Module-level singleton — shared across all sessions (read-only lookups are thread-safe)
    _competitive_intel_organ = CompetitiveIntelOrgan()
    logging.info(f"[ORGAN 34] Competitive Intel WIRED — {_competitive_intel_organ.get_status()['competitor_count']} competitors tracked")
except ImportError as e:
    COMPETITIVE_INTEL_WIRED = False
    _competitive_intel_organ = None
    logging.warning(f"[ORGAN 34] Competitive Intel unavailable: {e}")

# [ORGAN 30] Prosody Analysis — emotional perception layer (v4.1 ARMS-LEGS-REACH)
try:
    from organs_v4_1.organ_30_prosody_analysis import ProsodyAnalysisOrgan
    PROSODY_ANALYSIS_WIRED = True
    logging.info("[ORGAN 30] Prosody Analysis WIRED — 7-emotion tone detection online")
except ImportError as e:
    PROSODY_ANALYSIS_WIRED = False
    logging.warning(f"[ORGAN 30] Prosody Analysis unavailable: {e}")

# [ORGAN 31] Objection Learning — adaptive learning loop (v4.1 ARMS-LEGS-REACH)
# Module-level singleton — persists learning across sessions (data on disk)
try:
    from organs_v4_1.organ_31_objection_learning import ObjectionLearningOrgan
    OBJECTION_LEARNING_WIRED = True
    _objection_learning_organ = ObjectionLearningOrgan()
    logging.info(f"[ORGAN 31] Objection Learning WIRED — "
                 f"{_objection_learning_organ.get_status()['candidates']} candidates, "
                 f"{_objection_learning_organ.get_status()['promoted']} promoted")
except ImportError as e:
    OBJECTION_LEARNING_WIRED = False
    _objection_learning_organ = None
    logging.warning(f"[ORGAN 31] Objection Learning unavailable: {e}")

# [ORGAN 25] Warm Handoff & Escalation — human closer transfer (v4.1 ARMS-LEGS-REACH)
try:
    from organs_v4_1.organ_25_handoff_escalation import HandoffEscalationOrgan, HandoffReason
    WARM_HANDOFF_WIRED = True
    logging.info("[ORGAN 25] Warm Handoff & Escalation WIRED — human escalation pathway online")
except ImportError as e:
    WARM_HANDOFF_WIRED = False
    logging.warning(f"[ORGAN 25] Warm Handoff unavailable: {e}")

# [ORGAN 32] Call Summarization — structured call intelligence (v4.1 ARMS-LEGS-REACH)
try:
    from organs_v4_1.organ_32_summarization import SummarizationOrgan, SUMMARY_STORE
    SUMMARIZATION_WIRED = True
    logging.info("[ORGAN 32] Call Summarization WIRED — structured summary pipeline online")
except ImportError as e:
    SUMMARIZATION_WIRED = False
    logging.warning(f"[ORGAN 32] Call Summarization unavailable: {e}")

# [ORGAN 33] CRM Integration — pipeline-aware CRM push (v4.1 ARMS-LEGS-REACH)
try:
    from organs_v4_1.organ_33_crm_integration import CRMIntegrationOrgan, CRM_QUEUE_PATH, SyncStatus
    CRM_INTEGRATION_WIRED = True
    logging.info("[ORGAN 33] CRM Integration WIRED — durable CRM push pipeline online")
except ImportError as e:
    CRM_INTEGRATION_WIRED = False
    logging.warning(f"[ORGAN 33] CRM Integration unavailable: {e}")

# [ORGAN 35] In-Call IQ Budgeting — cognitive governance + burn accounting (v4.1 CAPSTONE)
try:
    from organs_v4_1.organ_35_incall_budget import (
        InCallBudgetOrgan, BurnState, CallTier,
        ORGAN_COST_MAP, THROTTLE_RULES, FALLBACK_STRATEGIES, BUDGET_TIERS
    )
    IQ_BUDGET_WIRED = True
    logging.info("[ORGAN 35] In-Call IQ Budgeting WIRED — cognitive governance online")
except ImportError as e:
    IQ_BUDGET_WIRED = False
    logging.warning(f"[ORGAN 35] In-Call IQ Budgeting unavailable: {e}")

# [ORGAN 36] DTMF Reflex — per-call DTMF tone generation + IVR button pressing
try:
    from organs_v4_1.organ_36_dtmf_reflex import DTMFReflex, create_dtmf_reflex
    DTMF_REFLEX_WIRED = True
    logging.info("[ORGAN 36] DTMF Reflex WIRED — IVR button-press capability online")
except ImportError as e:
    DTMF_REFLEX_WIRED = False
    logging.warning(f"[ORGAN 36] DTMF Reflex unavailable: {e}")

# [ORGAN 37] IVR Navigator — menu parsing + deterministic IVR navigation
try:
    from organs_v4_1.organ_37_ivr_navigator import IVRNavigator, IVRAction, create_ivr_navigator
    IVR_NAVIGATOR_WIRED = True
    logging.info("[ORGAN 37] IVR Navigator WIRED — menu parsing + deterministic navigation online")
except ImportError as e:
    IVR_NAVIGATOR_WIRED = False
    logging.warning(f"[ORGAN 37] IVR Navigator unavailable: {e}")

# [ORGAN 29] Inbound Context Injection — callback memory (v4.1 ARMS-LEGS-REACH)
try:
    from organs_v4_1.organ_29_inbound_context import InboundContextOrgan, INBOUND_SCRIPTS
    INBOUND_CONTEXT_WIRED = True
    logging.info("[ORGAN 29] Inbound Context WIRED — callback memory online")
except ImportError as e:
    INBOUND_CONTEXT_WIRED = False
    logging.warning(f"[ORGAN 29] Inbound Context unavailable: {e}")

# [ORGAN 28] Calendar & Scheduling — real-time booking engine (v4.1 ARMS-LEGS-REACH)
try:
    from organs_v4_1.organ_28_calendar_scheduling import CalendarOrgan
    CALENDAR_ENGINE_WIRED = True
    logging.info("[ORGAN 28] Calendar Engine WIRED — real-time scheduling pipeline online")
except ImportError as e:
    CALENDAR_ENGINE_WIRED = False
    logging.warning(f"[ORGAN 28] Calendar Engine unavailable: {e}")

# [ORGAN 28] Merchant scheduling request detection patterns
_CALENDAR_REQUEST_PATTERNS = [
    'set up a meeting', 'schedule a meeting', 'book an appointment',
    'schedule a call', 'set up a call', 'book a time',
    'can we schedule', 'let\'s schedule', 'let\'s set up',
    'when are you available', 'when can we meet', 'pick a time',
    'book a meeting', 'set an appointment', 'make an appointment',
    'schedule something', 'find a time', 'what times work',
]
# Confirmation for proposed time slot
_CALENDAR_CONFIRM_PATTERNS = [
    'that works', 'sounds good', 'perfect', 'let\'s do it',
    'book it', 'confirm', 'yes that time', 'works for me',
    'i\'ll take that', 'lock it in', 'yes please',
]
_CALENDAR_DECLINE_PATTERNS = [
    'no that doesn\'t work', 'different time', 'another time',
    'not that time', 'something else', 'later', 'not available',
]

# [ORGAN 27] Language Switching — multilingual STT/TTS/prompt pipeline (v4.1 ARMS-LEGS-REACH)
try:
    from organs_v4_1.organ_27_language_switch import (
        LanguageSwitchOrgan, LANGUAGE_CONFIGS, MIN_DETECTION_CONFIDENCE,
    )
    LANGUAGE_SWITCH_WIRED = True
    logging.info("[ORGAN 27] Language Switching WIRED — multilingual pipeline online")
except ImportError as e:
    LANGUAGE_SWITCH_WIRED = False
    logging.warning(f"[ORGAN 27] Language Switching unavailable: {e}")

# [ORGAN 27] Merchant language-switch request patterns
# These phrases indicate the merchant wants to speak another language.
_LANGUAGE_SWITCH_PATTERNS = {
    'es': [
        'habla español', 'en español', 'speak spanish', 'in spanish',
        'can we do this in spanish', 'prefer spanish', 'hablo español',
        'español por favor', 'spanish please',
    ],
    'fr': [
        'parlez-vous français', 'en français', 'speak french', 'in french',
        'french please', 'prefer french', 'je parle français',
    ],
    'pt': [
        'fala português', 'em português', 'speak portuguese', 'in portuguese',
        'portuguese please', 'prefer portuguese',
    ],
}
# Confirmation patterns for language switch
_LANGUAGE_CONFIRM_PATTERNS = [
    'yes', 'yeah', 'sure', 'please', 'sí', 'si', 'oui', 'sim',
    'go ahead', 'that would be great', 'yes please',
]
_LANGUAGE_DECLINE_PATTERNS = [
    'no', 'nah', 'english is fine', 'english please', 'no thanks',
    'keep it in english', 'stay in english',
]

# [ORGAN 26] Outbound Comms — SMS/email/link follow-ups (v4.1 ARMS-LEGS-REACH)
try:
    from organs_v4_1.organ_26_outbound_comms import OutboundCommsOrgan, Channel
    OUTBOUND_COMMS_WIRED = True
    logging.info("[ORGAN 26] Outbound Comms WIRED — SMS/email follow-up pipeline online")
except ImportError as e:
    OUTBOUND_COMMS_WIRED = False
    logging.warning(f"[ORGAN 26] Outbound Comms unavailable: {e}")

# [ORGAN 26] Mid-call outbound request detection patterns
# Merchant asks Alan to send info via text or email.
_OUTBOUND_SMS_REQUEST_PATTERNS = [
    'text me', 'send me a text', 'can you text', 'shoot me a text',
    'text it to me', 'send me the info', 'send me that', 'send me something',
    'text the details', 'send it over', 'text that over', 'message me',
]
_OUTBOUND_EMAIL_REQUEST_PATTERNS = [
    'email me', 'send me an email', 'can you email', 'email it to me',
    'email the details', 'email that over', 'send it to my email',
    'shoot me an email', 'email me the info', 'send an email',
]

# [ORGAN 25] Merchant escalation request detection patterns
# These phrases indicate the merchant wants to speak with a human.
_MERCHANT_ESCALATION_PATTERNS = [
    'talk to someone', 'speak to someone', 'talk to a person', 'speak with a person',
    'talk to a human', 'speak to a human', 'real person', 'talk to your manager',
    'speak with a manager', 'transfer me', 'let me talk to', 'put me through',
    'get me a supervisor', 'i want a human', 'talk to a rep', 'speak to a rep',
    'can i talk to someone else', 'is there someone else',
]

# [ORGAN 25] Consent confirmation patterns — merchant confirms transfer
_HANDOFF_CONSENT_PATTERNS = [
    'yes transfer', 'sure transfer', 'go ahead', 'yes please', 'yeah go ahead',
    'that would be great', 'yes connect me', 'sounds good', 'please do',
    'ok transfer', 'sure thing', 'yeah sure',
]

# [ORGAN 31] Objection Family Classification (§3.2 Field Pack)
# Maps Organ 6 objection types + raw text to the 5 doctrine-aligned families.
# Organ 31 learns from uncaptured phrases that Organ 6 misses.
_OBJECTION_FAMILIES = {
    'not_interested': {'family': 'dismissal',       'rebuttal': '§3.2.1', 'closing': 'rapport_recovery',    'tone': 'yielding_curious'},
    'too_busy':       {'family': 'time_availability','rebuttal': '§3.2.2', 'closing': 'time_efficiency',     'tone': 'concise_efficient'},
    'send_info':      {'family': 'deferral',         'rebuttal': '§3.2.3', 'closing': 'micro_yes_ladder',    'tone': 'casual_rapport'},
    'happy_where':    {'family': 'loyalty',           'rebuttal': '§3.2.4', 'closing': 'consultative',        'tone': 'empathetic_reflect'},
    'kill_fee':       {'family': 'contractual',       'rebuttal': '§3.2.7', 'closing': 'etf_buyout',          'tone': 'empathetic_authority'},
}
# Reverse: family label → description for LLM context
_FAMILY_DESCRIPTIONS = {
    'dismissal':        'Merchant is dismissing the call — recover rapport, stay curious',
    'time_availability':'Merchant is pressed for time — be concise, lead with value',
    'deferral':         'Merchant wants to defer — keep momentum, build micro-yeses',
    'loyalty':          'Merchant is loyal to current provider — don\'t attack, empathize and compare',
    'contractual':      'Merchant is locked in a contract — offer ETF analysis, show savings path',
    'general_hesitation':'Unclassified hesitation — listen, acknowledge, gently probe',
}

# [ORGAN 30] Emotion → Prosody Mode mapping (§2.19 Prosody-Doctrine Integration)
# Maps Organ 30 emotion tags to existing prosody intents used by the TTS engine.
_EMOTION_TO_PROSODY_MODE = {
    'frustrated':   'empathetic_reflect',
    'resigned':     'reassure_stability',
    'confused':     'repair_clarify',
    'impatient':    'closing_momentum',
    'interested':   'confident_recommend',
    'enthusiastic': 'closing_momentum',
    'neutral':      None,  # no override — let detect_prosody_intent decide
}

# [ORGAN 30] Text-to-frame proxy — estimates audio metrics from transcript text
# Since the relay pipeline delivers text (not raw audio frames), we synthesize
# approximate prosodic features from word patterns, punctuation, and turn length.
# Calibrated against ProsodyAnalysisOrgan thresholds:
#   frustrated: energy>0.7, jitter>0.4, pitch>280    | interested: 0.45<=e<=0.7, 2.5<=wps<=3.5
#   impatient: wps>3.5, energy>0.7                    | confused: wps<1.2, pitch>180, jitter>0.5
#   enthusiastic: energy>0.7, pitch>280, wps>2.5      | resigned: energy<0.2, pitch<100, wps<2.5
_FRUSTRATION_WORDS = ['frustrated', 'angry', 'ridiculous', 'terrible', 'unacceptable', 'upset', 'furious']
_IMPATIENCE_WORDS = ['busy', 'hurry', 'quick', 'no time', 'call back', 'in a rush', 'gotta go']
_CONFUSION_WORDS = ['not sure', 'not really sure', 'confused', 'what do you mean', 'what you mean', 'i dont understand', 'i dont get', 'huh', 'wait what', 'i dont know']
_ENTHUSIASM_WORDS = ['amazing', 'wow', 'fantastic', 'awesome', 'incredible', 'love it', 'thats great']
_RESIGNATION_WORDS = ['whatever', 'dont care', 'fine', 'i guess', 'doesnt matter', 'give up']

def _text_to_prosody_frame(text: str, sentiment: str = 'neutral') -> dict:
    """Estimate audio-level prosodic features from transcript text.
    Returns a frame_metrics dict compatible with ProsodyAnalysisOrgan.analyze_frame()."""
    text_lower = text.lower().replace("'", "")
    words = text.split()
    word_count = len(words)

    # ── Base estimates ───────────────────────────────────────────────
    est_duration = max(1.0, word_count / 2.5)
    wps = word_count / est_duration
    energy = 0.35
    pitch = 160.0
    jitter = 0.1

    # ── Keyword-driven signal boosting (calibrated to organ thresholds) ──
    has_frustration = any(w in text_lower for w in _FRUSTRATION_WORDS)
    has_impatience = any(w in text_lower for w in _IMPATIENCE_WORDS)
    has_confusion = any(w in text_lower for w in _CONFUSION_WORDS)
    has_enthusiasm = any(w in text_lower for w in _ENTHUSIASM_WORDS)
    has_resignation = any(w in text_lower for w in _RESIGNATION_WORDS)
    has_exclamation = '!' in text
    has_question = '?' in text

    if has_frustration or (sentiment == 'negative' and has_exclamation):
        energy += 0.45      # push above 0.7 threshold
        pitch += 130.0      # push above 280 threshold
        jitter += 0.4       # push above 0.4 threshold
    elif has_impatience:
        energy += 0.4       # push above 0.7
        wps = max(wps, 4.0) # push above 3.5 threshold
    elif has_enthusiasm or (sentiment == 'positive' and has_exclamation):
        energy += 0.45
        pitch += 130.0
        wps = max(wps, 3.0) # above 2.5 threshold
    elif has_resignation:
        energy = 0.15       # below 0.2 threshold
        pitch = 85.0        # below 100 threshold
        wps = min(wps, 1.0) # below 2.5
    elif has_confusion:
        wps = min(wps, 1.0) # below 1.2 threshold
        pitch += 40.0       # above 180
        jitter += 0.45      # above 0.5
        if has_question:
            pitch += 30.0
    else:
        # No strong keyword signal — use sentiment + punctuation as soft boosts
        if has_exclamation:
            energy += 0.2
        caps_ratio = sum(1 for c in text if c.isupper()) / max(len(text), 1)
        if caps_ratio > 0.3:
            energy += 0.15
        if sentiment == 'negative':
            energy += 0.12
            pitch += 30.0
        elif sentiment == 'positive':
            energy += 0.1
            pitch += 20.0
        if has_question:
            pitch += 50.0

    # Hesitation markers → jitter boost (cumulative with above)
    hesitation_words = ['um', 'uh', 'well', 'like', 'i mean', 'you know']
    for hw in hesitation_words:
        if hw in text_lower:
            jitter += 0.08

    return {
        'rms_energy': round(min(energy, 1.0), 3),
        'pitch_hz': round(max(pitch, 50.0), 1),
        'words_per_second': round(max(wps, 0.5), 2),
        'jitter': round(min(jitter, 0.9), 3),
        'shimmer': round(min(jitter, 0.9) * 0.6, 3),
    }

# [INSTRUCTOR MODE] Governed learning system — training with industry professionals
try:
    from instructor_mode import (
        on_instructor_turn,
        get_learning_engine,
        InstructorSession,
        InstructorLearningEngine,
        governance_check,
    )
    INSTRUCTOR_MODE_WIRED = True
    _instructor_learning_engine = get_learning_engine()
    logging.info("[ORGAN] Instructor Mode WIRED — governed learning lane online")
except ImportError as e:
    INSTRUCTOR_MODE_WIRED = False
    _instructor_learning_engine = None
    logging.warning(f"[ORGAN] Instructor Mode unavailable: {e}")

# [ORGAN 11] Signature Extraction & Adaptive Voice Identity
try:
    from alan_signature_engine import (
        SignatureExtractor, SignatureLearner, EffectiveSignature,
        get_signature_learner, compute_effective_signature,
        get_prosody_speed_bias, get_prosody_silence_bias, get_breath_probability_bias
    )
    SIGNATURE_ENGINE_WIRED = True
    # Initialize the learner singleton at module load
    _sig_learner = get_signature_learner(state_dir=os.path.dirname(os.path.abspath(__file__)))
    logging.info("[ORGAN 11] Signature Extraction Engine WIRED — Adaptive Voice Identity ONLINE")
except ImportError as e:
    SIGNATURE_ENGINE_WIRED = False
    _sig_learner = None
    logging.warning(f"[ORGAN 11] Signature Engine unavailable: {e}")

# [ORGAN 34] COMPETITOR CLASSIFIER — detect competitor mentions in merchant speech
# Matches Field Pack §4.9 competitor roster. Returns (name, trigger_phrase) or (None, None).
_COMPETITOR_PATTERNS = {
    'Square':   ['square', 'square up', 'squareup', 'square reader', 'square pos', 'square terminal'],
    'Clover':   ['clover', 'clover pos', 'clover go', 'clover flex', 'clover mini', 'clover station'],
    'Toast':    ['toast', 'toast pos', 'toast tab', 'toasttab'],
    'Stripe':   ['stripe', 'stripe payments', 'stripe terminal'],
    'Heartland': ['heartland', 'heartland payment', 'heartland payments'],
    'Worldpay': ['worldpay', 'world pay', 'fis', 'fis worldpay', 'vantiv'],
    'PayPal':   ['paypal', 'pay pal', 'zettle', 'paypal zettle', 'paypal here'],
    'Stax':     ['stax', 'stax payments', 'stax pay', 'fattmerchant'],
    'Harbortouch': ['harbortouch', 'harbor touch', 'shift4', 'shift 4', 'shift4 payments', 'harbortouch pos', 'lighthouse'],
}

# [ORGAN 34] Unknown Processor Detection Patterns — regex-safe triggers for unlisted processors
# These fire ONLY after all known competitors fail to match. They capture the language
# merchants actually use when describing obscure, regional, white-label, or private-label processors.
_UNKNOWN_PROCESSOR_PATTERNS = [
    r"\bnever heard of\b",
    r"\bsmall processor\b",
    r"\blocal processor\b",
    r"\bprivate label\b",
    r"\bwhite[- ]label\b",
    r"\biso program\b",
    r"\btheir own system\b",
    r"\bsome program\b",
    r"\bbuddy.{0,20}set.{0,10}up\b",
    r"\bfriend.{0,20}set.{0,10}up\b",
    r"\bguy.{0,20}set.{0,10}up\b",
    r"\bnot sure what.{0,20}called\b",
    r"\bdon'?t know.{0,20}(?:name|called|processor)\b",
    r"\bspecial (?:rate|deal|program)\b",
]

# [ORGAN 34] UCP — Universal Competitive Protocol LLM Injection Block
# Injected into the system message when an unknown processor is detected.
# Matches §4.9 formatting, indentation, and doctrinal style.
_UCP_LLM_BLOCK = (
    "[COMPETITIVE INTEL — §4.9 POSITIONING — UNKNOWN PROCESSOR PROTOCOL]\n"
    "\n"
    "COMPETITOR: Unrecognized / Unlisted Processor\n"
    "CATEGORY: Unknown / Unclassified\n"
    "DETECTION: Merchant named a processor not found in the competitive-intel registry.\n"
    "\n"
    "TONE MODE:\n"
    "- Neutral → curious → helpful\n"
    "- No assumptions, no negative claims, no speculation\n"
    "- Merchant-driven intelligence only\n"
    "\n"
    "POSITIONING STRATEGY:\n"
    "- Use universal industry truths that apply to all processors\n"
    "- Anchor conversation in the merchant's actual fees, not the competitor's brand\n"
    "- Focus on transparency, clarity, and savings opportunities\n"
    "- Avoid any claims about the competitor's contract, ETF, hardware, or support\n"
    "- Build a custom profile from merchant-provided details only\n"
    "\n"
    "DISCOVERY PROMPTS:\n"
    '- "What do they charge you per transaction?"\n'
    '- "Do they bill you monthly for terminals or software?"\n'
    '- "Do you know if you\'re on interchange-plus or a flat rate?"\n'
    '- "Any annual or PCI fees?"\n'
    '- "How long have you been with them?"\n'
    "\n"
    "UNIVERSAL POSITIONING LINES:\n"
    '- "Every processor has a cost structure — the key is understanding where the money goes."\n'
    '- "Most programs fall into flat rate, tiered, or interchange-plus."\n'
    '- "The biggest savings usually come from per-transaction fees and terminal/software fees."\n'
    '- "Depending on your volume, even a small difference in per-transaction fees can add up fast."\n'
    '- "If you\'re paying for terminals or software, that\'s usually the easiest place to save."\n'
    "\n"
    "SAVINGS FRAMING (CONDITIONAL):\n"
    '- "Depending on your volume, there may be room to improve your per-transaction costs."\n'
    '- "If you\'re on a tiered program, there\'s almost always a more efficient structure."\n'
    '- "If you\'re paying for terminals or software, that\'s typically the easiest place to reduce overhead."\n'
    "\n"
    "OBJECTION HANDLING:\n"
    'LOYALTY: "Totally fair — a lot of owners stay with a processor for years without realizing how the fees add up."\n'
    'CONTRACTUAL: "Every program has its own terms — the first step is understanding what you\'re being billed for today."\n'
    'TIME/AVAILABILITY: "This only takes 10-15 minutes — I\'ll break down the fees line by line."\n'
    'DEFERRAL: "Sure — what\'s the best number to text a quick breakdown to?"\n'
    'DISMISSAL: "No problem — most owners are surprised by what we find once we look at a statement."\n'
    "\n"
    "UNIVERSAL CLOSE:\n"
    '"Let\'s take a look at one statement. I\'ll break down the fees line by line and show you exactly '
    'where the money is going. If I can\'t save you money, I\'ll tell you straight up — but most owners '
    'are surprised by what we find."\n'
    "\n"
    "FORBIDDEN CLAIMS:\n"
    "- Contract length\n"
    "- ETF or liquidated damages\n"
    "- Hardware ownership\n"
    "- PCI fees\n"
    "- Annual fees\n"
    "- Pricing model\n"
    "- Support quality\n"
    "- Reputation\n"
    "- Risk profile\n"
    "\n"
    "SAFETY NOTES:\n"
    "Never assume or invent details about unknown processors. Use merchant-provided facts only.\n"
    "\n"
    "[UCP — UNKNOWN PROCESSOR PROTOCOL ACTIVE]"
)

# §4.9 — Competitor-Aligned Script Selection Rules (from Field Pack v1.1)
_COMPETITOR_POSITIONING = {
    'Square': {
        'tone_mode': 'warm, low-pressure',
        'closing_style': 'consultative',
        'positioning': 'Savings math + reliability + personal service',
        'key_weakness': 'Flat-rate hits 2.6-3.5% (effective rate often 3%+). No human support. Hardware lock-in.',
        'objection_pattern': '"I like Square\'s simplicity" → Frame simplicity vs. savings. Simple doesn\'t mean cheap.',
        'savings_approach': 'Compare flat-rate total vs. Edge total. Show the gap.',
    },
    'Stripe': {
        'tone_mode': 'technical, respectful',
        'closing_style': 'consultative → authority',
        'positioning': 'Fee-structure analysis + in-person advantage',
        'key_weakness': '2.9% + $0.30 per transaction. No in-person terminal expertise. Developer-focused, not merchant-focused.',
        'objection_pattern': '"Stripe handles my online" → Acknowledge online, pitch in-person gap.',
        'savings_approach': 'Online percentage comparison + in-person uplift.',
    },
    'Clover': {
        'tone_mode': 'confident, technical',
        'closing_style': 'authority',
        'positioning': 'Equipment reliability + true cost analysis',
        'key_weakness': 'Equipment leases ($2K-$5K over term). High effective rates hidden behind POS features. Fiserv backend.',
        'objection_pattern': '"I already have Clover" → "You own the Clover? Or leasing?" Expose the lease trap.',
        'savings_approach': 'Lease payment + processing fees vs. Edge + free terminal.',
    },
    'Toast': {
        'tone_mode': 'restaurant-specific, knowledgeable',
        'closing_style': 'authority → consultative',
        'positioning': 'Restaurant-specific integration + processing cost',
        'key_weakness': '2.49-3.69% processing. $69-$110/month subscription. Equipment $799-$1,349+. Restaurant-only.',
        'objection_pattern': '"Toast does everything for my restaurant" → Acknowledge POS, separate processing cost.',
        'savings_approach': 'Isolate processing as a separate cost center from POS features.',
    },
    'Heartland': {
        'tone_mode': 'empathetic, professional',
        'closing_style': 'consultative',
        'positioning': 'Personal service + transparency',
        'key_weakness': 'Interchange-plus markup varies. ETFs up to $295. Sales rep turnover means no relationship.',
        'objection_pattern': '"Heartland\'s been okay" → "When\'s the last time your rep called you?"',
        'savings_approach': 'Expose the relationship gap — Alan is the rep who stays.',
    },
    'Worldpay': {
        'tone_mode': 'professional, savings-focused',
        'closing_style': 'savings-math close',
        'positioning': 'True cost exposure + personal attention',
        'key_weakness': 'Tiered pricing (worst model). Bundled qualified/mid-qual/non-qual hides real rates. PCI fees $100+/year.',
        'objection_pattern': '"Been with them for years" → "Have they ever proactively lowered your rate?"',
        'savings_approach': 'Expose loyalty penalty with rate comparison.',
    },
    'PayPal': {
        'tone_mode': 'casual, savings-focused',
        'closing_style': 'consultative',
        'positioning': 'In-store processing gap + savings',
        'key_weakness': '2.29-3.49% + $0.09. Account freezes with no warning. No dedicated human support.',
        'objection_pattern': '"PayPal is easy" → "Easy until they freeze your funds." Frame the risk.',
        'savings_approach': 'Compare total cost including freeze risk + in-person gap.',
    },
    'Stax': {
        'tone_mode': 'analytical, respectful',
        'closing_style': 'savings-math close',
        'positioning': 'Volume threshold analysis',
        'key_weakness': '$99-$199/month subscription only makes sense at $15K-$20K+/month. Below that, costs more.',
        'objection_pattern': '"Stax has no markup" → "You\'re paying $199/month PLUS interchange. On Edge, it\'s $14.95 flat."',
        'savings_approach': 'Subscription fee vs. Edge flat fee. Show break-even volume.',
    },
    'Harbortouch': {
        'tone_mode': 'empathetic, savings-focused, multi-location aware',
        'closing_style': 'predatory-fee relief close → savings-math close',
        'positioning': 'Terminal rental elimination + annual fee elimination + transparent interchange + multi-location unification',
        'key_weakness': '$65/terminal/month rental (4 biz × 2-3 terminals = $650+/mo just in hardware). Per-transaction $0.10 is 2-3x industry. Annual junk fees ($200-$400/biz/yr). Liquidated damages + auto-renewal contract traps. Proprietary POS lock-in. Forced software updates.',
        'objection_pattern': '"We\'re locked into Harbortouch" → "Most Harbortouch contracts have exit windows. Let me look at your statement — we\'ve helped dozens of Harbortouch merchants break free. Even with an ETF, you save more in 2-3 months than the penalty costs."',
        'savings_approach': 'Multi-location consolidation math: terminal rentals ($650/mo) + per-txn premium ($0.10 vs $0.04) + annual fees ($1,200/yr) + basis points. Conservative savings: $3,000-$4,000/month. Annual: $36K-$48K. Lead with terminal rental elimination — it\'s the most visible line item.',
    },
    'unknown_processor': {
        'name': 'Unknown / Unlisted Processor',
        'tone_mode': 'neutral_curious_helpful',
        'closing_style': 'discovery_first_then_savings_review',
        'key_weakness': [
            'unknown_pricing_structure',
            'unknown_fee_model',
            'unknown_contract_terms',
            'unknown_hardware_costs',
        ],
        'positioning_rules': {
            'discovery_prompts': [
                'What do they charge you per transaction?',
                'Do they bill you monthly for terminals or software?',
                'Do you know if you\'re on interchange-plus or a flat rate?',
                'Any annual or PCI fees?',
                'How long have you been with them?',
            ],
            'universal_truths': [
                'Every processor has a cost structure — the key is understanding where the money goes.',
                'Most programs fall into flat rate, tiered, or interchange-plus.',
                'The biggest savings usually come from per-transaction fees and terminal/software fees.',
                'Depending on your volume, even a small difference in per-transaction fees can add up fast.',
                'If you\'re paying for terminals or software, that\'s usually the easiest place to save.',
            ],
            'savings_framing': [
                'Depending on your volume, there may be room to improve your per-transaction costs.',
                'If you\'re on a tiered program, there\'s almost always a more efficient structure.',
                'If you\'re paying for terminals or software, that\'s typically the easiest place to reduce overhead.',
            ],
            'objection_handlers': {
                'loyalty': 'Totally fair — a lot of owners stay with a processor for years without realizing how the fees add up.',
                'contractual': 'Every program has its own terms — the first step is understanding what you\'re being billed for today.',
                'time_availability': 'This only takes 10-15 minutes — I\'ll break down the fees line by line.',
                'deferral': 'Sure — what\'s the best number to text a quick breakdown to?',
                'dismissal': 'No problem — most owners are surprised by what we find once we look at a statement.',
            },
            'universal_close': (
                'Let\'s take a look at one statement. I\'ll break down the fees line by line and show you exactly '
                'where the money is going. If I can\'t save you money, I\'ll tell you straight up — but most owners '
                'are surprised by what we find.'
            ),
        },
        'forbidden_claims': [
            'contract_length',
            'etf_or_liquidated_damages',
            'hardware_ownership',
            'pci_fees',
            'annual_fees',
            'pricing_model',
            'support_quality',
            'reputation',
            'risk_profile',
        ],
        'safety_notes': 'Never assume or invent details about unknown processors. Use merchant-provided facts only.',
        'savings_approach': 'conditional_savings_based_on_merchant_data',
        'objection_pattern': 'generic_objection_family_routing',
        'llm_suffix': '[UCP — UNKNOWN PROCESSOR PROTOCOL ACTIVE]',
    },
}

def detect_competitor_mention(text: str) -> tuple:
    """
    Scan merchant speech for competitor mentions.
    Returns (competitor_name, trigger_phrase) or (None, None).
    Constitutional: never guesses without evidence — must match a known pattern.

    Three-tier detection:
      1. Known competitors (exact substring match — always takes priority)
      2. Unknown-processor regex patterns (regional, white-label, ISO, etc.)
      3. Keyword fallback ("processor", "merchant service", "merchant account")
    """
    if not text:
        return None, None
    text_lower = text.lower()

    # TIER 1: Check all known competitors first — always takes priority
    for name, patterns in _COMPETITOR_PATTERNS.items():
        for pattern in patterns:
            if pattern in text_lower:
                return name, pattern

    # TIER 2: Check unknown-processor regex patterns
    for pat in _UNKNOWN_PROCESSOR_PATTERNS:
        try:
            _m = re.search(pat, text_lower)
            if _m:
                return 'unknown_processor', _m.group(0)
        except Exception:
            continue  # NEG-PROOF: never break call path on bad regex

    # TIER 3: Keyword fallback — merchant mentions a processor-like concept
    # but doesn't name a brand
    _fallback_keywords = ['processor', 'merchant service', 'merchant account']
    for kw in _fallback_keywords:
        try:
            if kw in text_lower:
                return 'unknown_processor', kw
        except Exception:
            continue  # NEG-PROOF

    return None, None

# [ORGAN RECONNECT] Energy Mirroring — detect caller energy for tone matching
ENERGY_FORMAL_WORDS = ["please", "thank you", "excuse me", "sir", "ma'am", "appreciate"]
ENERGY_CASUAL_WORDS = ["hey", "dude", "kinda", "sorta", "yeah", "nah", "cool", "awesome"]
ENERGY_STRESSED_WORDS = ["frustrated", "angry", "worried", "stressed", "upset", "ridiculous", "terrible"]

def detect_caller_energy(text: str) -> str:
    """Detect caller energy level from speech text. Returns: formal, casual, stressed, or neutral."""
    text_lower = text.lower()
    if any(word in text_lower for word in ENERGY_STRESSED_WORDS):
        return "stressed"
    if any(word in text_lower for word in ENERGY_FORMAL_WORDS):
        return "formal"
    if any(word in text_lower for word in ENERGY_CASUAL_WORDS):
        return "casual"
    return "neutral"

# [ORGAN 6] Live Objection Detection — classify objection type for rebuttal injection
OBJECTION_PATTERNS = {
    'kill_fee': ["contract", "cancellation", "early termination", "fee", "locked in", "term"],
    'too_busy': ["busy", "call back", "no time", "bad time", "in a rush", "don't have time", "not a good time"],
    'not_interested': ["not interested", "don't need", "we're good", "all set"],
    'happy_where': ["happy with", "happy where", "satisfied with", "like what we have", "loyal to"],
    'send_info': ["send info", "email me", "send me something", "mail me", "send a brochure", "send me some info", "send me info"],
}

def detect_live_objection(text: str) -> str:
    """Detect specific objection type from caller speech. Returns objection key or None."""
    text_lower = text.lower()
    for obj_type, patterns in OBJECTION_PATTERNS.items():
        if any(p in text_lower for p in patterns):
            return obj_type
    return None

# =============================================================================
# [ORGAN 7] PROSODY ENGINE — "The Last 5%"
# =============================================================================
# Maps conversational intent → OpenAI TTS instructions → adaptive silence.
# OpenAI gpt-4o-mini-tts does NOT support SSML. Instead, it accepts natural
# language "instructions" that shape prosody, emotion, pacing, and breath.
#
# This is the bridge between Alan's cognition (what he MEANS) and his voice
# (how he SOUNDS). A real salesperson shifts tone constantly:
#   - Empathetic when merchant is stressed
#   - Confident when recommending
#   - Casual when rapport-building
#   - Measured when handling objections
#
# The engine reads: caller_energy, sentiment, trajectory, objection state
# and selects the voice instruction + inter-sentence pause that matches.
# =============================================================================

# Intent → TTS instruction map
# These are natural language directives for gpt-4o-mini-tts.
# Each one shapes pitch, pace, breath, and emotional color.
PROSODY_INSTRUCTIONS = {
    # DEFAULT: experienced sales rep on the phone
    "neutral": (
        "Speak at a natural conversational pace like an experienced sales rep "
        "on the phone. Confident but not pushy. Breathe naturally between "
        "phrases. Keep energy steady and warm."
    ),
    # EMPATHETIC: merchant is stressed, upset, frustrated
    "empathetic_reflect": (
        "Speak slower and softer, like you genuinely care about what the person "
        "just said. Lower your pitch slightly. Pause briefly before responding, "
        "as if you're taking a breath to really consider their situation. "
        "Sound sincere, not performative. Like a friend who happens to be good at business."
    ),
    # REASSURE: merchant is anxious but not hostile — "we've got you"
    "reassure_stability": (
        "Speak with calm, steady reassurance — like a trusted advisor who has "
        "seen this situation many times. Slightly lower pitch, unhurried pace. "
        "After any reassuring statement, let a natural breath pause land before "
        "continuing. Project 'everything is under control' through your voice."
    ),
    # CONFIDENT RECOMMEND: closing, recommending, pitching
    "confident_recommend": (
        "Speak with calm authority, like a seasoned consultant giving a recommendation "
        "you fully believe in. Slightly slower pace than normal — deliberate, not rushed. "
        "Project confidence through steady tempo, not volume. Let key phrases land "
        "with a brief natural pause after them."
    ),
    # CURIOUS PROBE: asking questions, leaning in, gathering info
    "curious_probe": (
        "Speak with genuine curiosity, like you're really interested in what the "
        "person is about to tell you. Slightly brighter pitch, a touch faster pace. "
        "Let questions sound like you're leaning forward — engaged, not interrogating. "
        "Brief upward inflection at the end of questions, natural and conversational."
    ),
    # CASUAL RAPPORT: merchant is casual, friendly, joking
    "casual_rapport": (
        "Speak like you're talking to a buddy who also runs a business. "
        "Relaxed, genuine, maybe a slight smile in your voice. Natural pace — "
        "not too fast, not too slow. Comfortable and easy-going."
    ),
    # MICRO-HESITATE: thinking out loud, slight uncertainty, humanizing pause
    "micro_hesitate": (
        "Speak naturally but include a very slight thinking pause mid-sentence, "
        "like you're choosing your next word carefully. Not uncertain — thoughtful. "
        "The hesitation should sound like a real person organizing their thoughts "
        "in real time. Keep pitch neutral, pace normal."
    ),
    # OBJECTION HANDLING: merchant pushed back, need measured response
    "objection_handling": (
        "Speak calmly and evenly, like someone who's heard this concern a hundred "
        "times and has a good answer. Not defensive. Not dismissive. Measured pace, "
        "steady pitch. Sound like you understand their hesitation and you're about "
        "to address it thoughtfully."
    ),
    # FORMAL/RESPECTFUL: merchant is formal, professional
    "formal_respectful": (
        "Speak professionally and clearly, matching a formal business tone. "
        "Measured pace, clean articulation. Respectful but not stiff. "
        "Like a polished account executive on a client call."
    ),
    # TURN YIELD: handing the floor back, inviting the caller to speak
    "turn_yield": (
        "Speak with an inviting, open tone — like you're genuinely handing the "
        "conversation back to them. Slightly slower at the end, with a gentle "
        "upward pitch shift on the final phrase. Make the listener feel like "
        "their answer matters. Don't rush the ending."
    ),
    # REPAIR/CLARIFY: correcting a misunderstanding, restating
    "repair_clarify": (
        "Speak clearly and patiently, like you're gently correcting a "
        "misunderstanding. Not condescending — helpful. Slightly slower pace, "
        "clean articulation. Pause briefly before the corrected phrase so the "
        "listener can register the shift. Neutral pitch, steady and clear."
    ),
    # CLOSING/URGENCY: endgame, near the close
    "closing_momentum": (
        "Speak with quiet momentum — not fast, but purposeful. Every word should "
        "feel like it's leading somewhere important. Slight forward lean in your "
        "energy. Confident pauses between key points, like you're giving them "
        "space to agree."
    ),
}

# Intent → inter-sentence silence frames — loaded from timing_config.json
# Each frame = ~20ms. Research-backed: Stivers 2009 (+208ms mean gap),
# Gong.io (2M sales calls — top reps pause longer after objections).
# neutral bumped 120→200ms, objection_handling bumped 180→300ms.
PROSODY_SILENCE_FRAMES = TIMING.prosody_silence_frames  # [TIMING CONFIG] Centralized

# Intent → TTS speed override — loaded from timing_config.json
# Empathy is slower. Closing is slightly faster. Most stay at default.
PROSODY_SPEED = TIMING.prosody_speed_map  # [TIMING CONFIG] Centralized

def detect_prosody_intent(context: dict, analysis: dict = None) -> str:
    """Detect the prosody intent from conversation state (pre-LLM pass).
    
    Reads caller_energy, sentiment, trajectory, objection state, and 
    endgame state to determine HOW Alan should sound for this turn.
    
    This sets the BASE intent. Per-sentence refinement via
    refine_prosody_per_sentence() can upgrade it based on content.
    
    Priority order (highest wins):
      1. Caller is stressed/upset → empathetic_reflect
      2. Caller is anxious but not hostile → reassure_stability
      3. Active objection → objection_handling  
      4. Endgame/closing → closing_momentum
      5. Caller is formal → formal_respectful
      6. Caller is casual → casual_rapport
      7. Positive sentiment → confident_recommend
      8. Default → neutral
    """
    caller_energy = context.get('caller_energy', 'neutral')
    sentiment = (analysis or {}).get('sentiment', 'neutral')
    trajectory = context.get('master_closer_state', {}).get('trajectory', 'neutral')
    endgame = context.get('master_closer_state', {}).get('endgame_state', 'not_ready')
    has_objection = context.get('live_objection_type') is not None
    
    # 1. Stressed caller → empathy first, always
    if caller_energy == 'stressed':
        return 'empathetic_reflect'
    
    # 2. Anxious/uncertain caller (not hostile) → calm reassurance
    if caller_energy == 'anxious':
        return 'reassure_stability'
    
    # 3. Active objection → measured handling
    if has_objection:
        return 'objection_handling'
    
    # 4. Near close → momentum
    if endgame in ('ready', 'closing') or trajectory == 'warming':
        if sentiment != 'negative':
            return 'closing_momentum'
    
    # 5. Formal caller → match their register
    if caller_energy == 'formal':
        return 'formal_respectful'
    
    # 6. Casual caller → match their vibe
    if caller_energy == 'casual':
        return 'casual_rapport'
    
    # 7. Positive engagement → confident recommend
    if sentiment == 'positive':
        return 'confident_recommend'
    
    # 8. Default
    return 'neutral'


def refine_prosody_per_sentence(sentence: str, base_intent: str, is_last_sentence: bool = False) -> str:
    """Refine prosody intent per-sentence based on Alan's actual output content.
    
    Called AFTER the LLM generates each sentence. Analyzes the sentence text
    to detect content-driven voice modes that can't be known pre-LLM:
    
    - Questions → curious_probe or turn_yield 
    - Reassurance phrases → reassure_stability
    - Correction/clarification → repair_clarify
    - Hedging/thinking-aloud → micro_hesitate
    
    The base_intent (from detect_prosody_intent) wins for strong emotional
    states (empathetic_reflect, objection_handling). Content refinement only
    applies when the base_intent is neutral, casual, confident, or formal.
    """
    # Strong emotional intents are NOT overridden by content analysis
    # These respond to the CALLER's emotional state and must hold
    LOCKED_INTENTS = {'empathetic_reflect', 'objection_handling', 'closing_momentum'}
    if base_intent in LOCKED_INTENTS:
        return base_intent
    
    s_lower = sentence.lower().strip()
    ends_with_question = sentence.rstrip().endswith('?')
    
    # TURN YIELD: last sentence + question = handing the floor back
    if ends_with_question and is_last_sentence:
        return 'turn_yield'
    
    # CURIOUS PROBE: mid-conversation question (not the last sentence)
    if ends_with_question:
        return 'curious_probe'
    
    # REPAIR/CLARIFY: correction patterns
    repair_markers = (
        'let me restate', 'let me clarify', 'what i meant', 'to be clear',
        'i should clarify', 'let me rephrase', 'actually what i', 
        'sorry, i meant', 'to clarify', 'what i mean is'
    )
    if any(marker in s_lower for marker in repair_markers):
        return 'repair_clarify'
    
    # REASSURE STABILITY: calming phrases
    reassure_markers = (
        "that's completely normal", "that's totally normal", "we see that",
        "that's very common", "don't worry", "it's okay", "that's okay",
        "you're in good hands", "we've got you", "nothing to worry",
        "that's actually standard", "you're not alone in that",
        "perfectly normal", "we handle that", "totally understandable"
    )
    if any(marker in s_lower for marker in reassure_markers):
        return 'reassure_stability'
    
    # MICRO-HESITATE: thinking-aloud patterns (only for neutral/casual base)
    if base_intent in ('neutral', 'casual_rapport'):
        hesitate_markers = (
            'i think', 'you know what', 'honestly', 'let me think',
            'well,', 'the thing is', 'here\'s the thing'
        )
        if any(s_lower.startswith(marker) for marker in hesitate_markers):
            return 'micro_hesitate'
    
    return base_intent


# =============================================================================
# [ORGAN 8] CLAUSE SEGMENTATION ENGINE — "Delivery Units"
# =============================================================================
# Turns raw text into meaningful clauses for mid-sentence prosody shifts.
# A single sentence like "I think we can do better here, but I want to 
# understand how you're doing it today." becomes two delivery units so the
# TTS instruction can describe an *arc* — start thoughtful, end curious.
#
# Rules:
#   1. Hard splits: ? ! . (when not abbreviations)
#   2. Soft splits: comma + conjunction when clause > 25 chars
#   3. Semantic splits: "the good news is", "to be honest", etc.
# =============================================================================

# Semantic boundary markers — phrases that naturally create a delivery shift
_CLAUSE_SEMANTIC_MARKERS = (
    'the good news is', 'the thing is', 'to be honest', 'honestly',
    "here's what i recommend", "here is what i recommend",
    'what i can tell you is', 'but the reality is',
    'so what we do is', 'what that means is',
    'now here is the important part', "now here's the important part",
    'but more importantly', 'the bottom line is',
)

# Coordinating conjunctions for soft splits
_CLAUSE_CONJUNCTIONS = ('and ', 'but ', 'so ', 'yet ', 'or ')

def segment_into_clauses(sentence: str, base_intent: str = "neutral") -> list:
    """Segment a sentence into tagged clause objects for mid-sentence prosody.
    
    Returns a list of dicts:
      [{"text": "I think we can do better,", "tags": ["micro_hesitate"]},
       {"text": "but what are you using today?", "tags": ["curious_probe"]}]
    
    Short sentences (< 30 chars) return as a single clause with the base intent.
    """
    if not sentence or len(sentence.strip()) < 30:
        return [{"text": sentence.strip(), "tags": [base_intent]}]
    
    s = sentence.strip()
    clauses = []
    
    # Pass 1: Semantic marker splits
    s_lower = s.lower()
    split_done = False
    for marker in _CLAUSE_SEMANTIC_MARKERS:
        idx = s_lower.find(marker)
        if idx > 5:  # Only split if there's meaningful text before the marker
            before = s[:idx].rstrip(' ,;—–-')
            after = s[idx:]
            if len(before) > 10 and len(after) > 10:
                clauses = [before.strip(), after.strip()]
                split_done = True
                break
    
    # Pass 2: Soft split — comma + conjunction (only if no semantic split)
    if not split_done:
        # Find commas followed by conjunctions
        for conj in _CLAUSE_CONJUNCTIONS:
            pattern = ', ' + conj
            idx = s_lower.find(pattern)
            if idx > 0 and idx > 24:  # Clause before comma must be > ~25 chars
                before = s[:idx + 1]  # Keep the comma
                after = s[idx + 2:]    # Skip ", " — start with conjunction
                if len(before) > 10 and len(after) > 10:
                    clauses = [before.strip(), after.strip()]
                    split_done = True
                    break
    
    # Pass 3: If still no split, return as single clause
    if not split_done:
        clauses = [s]
    
    # Tag each clause based on its content
    tagged = []
    for i, clause_text in enumerate(clauses):
        tags = _tag_clause(clause_text, base_intent, is_last=(i == len(clauses) - 1))
        tagged.append({"text": clause_text, "tags": tags})
    
    return tagged


def _tag_clause(clause: str, base_intent: str, is_last: bool = False) -> list:
    """Assign prosody tags to a single clause based on its content."""
    tags = []
    cl = clause.lower().strip()
    
    # Question mark → curious or turn_yield
    if clause.rstrip().endswith('?'):
        tags.append('turn_yield' if is_last else 'curious_probe')
    
    # Hedging / thinking markers
    hedge_markers = ('i think', 'well,', 'honestly', 'to be honest', 'the thing is', "here's the thing")
    if any(cl.startswith(m) for m in hedge_markers):
        tags.append('micro_hesitate')
    
    # Reassurance markers
    reassure_markers = ('the good news is', "don't worry", "that's normal", "we've got you",
                        "you're in good hands", 'perfectly normal', 'totally understandable')
    if any(m in cl for m in reassure_markers):
        tags.append('reassure_stability')
    
    # Recommendation markers
    recommend_markers = ("here's what i recommend", 'what i recommend is', 'i suggest', 'my recommendation')
    if any(m in cl for m in recommend_markers):
        tags.append('confident_recommend')
    
    # Repair markers  
    repair_markers = ('let me clarify', 'what i meant', 'to be clear', 'let me rephrase')
    if any(m in cl for m in repair_markers):
        tags.append('repair_clarify')
    
    # If no content-specific tags, use the base intent
    if not tags:
        tags.append(base_intent)
    
    return tags


# =============================================================================
# [ORGAN 9] MID-SENTENCE PROSODY ARC — "Narrated Contour"
# =============================================================================
# Instead of one flat instruction for the whole sentence, this builds a
# narrative arc: "Start steady and empathetic, then become more curious
# when you ask the question at the end."
#
# gpt-4o-mini-tts interprets composite instructions beautifully — it adjusts
# pace, pitch, and energy within a single utterance based on natural language
# guidance about the delivery shape.
# =============================================================================

# Human-readable tone descriptors for building arc instructions
_TONE_DESCRIPTORS = {
    'neutral':             'conversational and steady',
    'empathetic_reflect':  'slower, softer, and genuinely empathetic',
    'reassure_stability':  'calm and reassuring, like a trusted advisor',
    'confident_recommend': 'confident and deliberate, with quiet authority',
    'curious_probe':       'curious and engaged, slightly brighter and leaning in',
    'casual_rapport':      'relaxed and easy-going, like talking to a friend',
    'micro_hesitate':      'thoughtful, with a slight natural pause as if choosing words carefully',
    'objection_handling':  'measured and calm, acknowledging without being defensive',
    'formal_respectful':   'professional and clear, with clean articulation',
    'turn_yield':          'inviting and open, gently handing the floor back',
    'repair_clarify':      'patient and clear, gently correcting',
    'closing_momentum':    'purposeful with quiet forward momentum',
}

def build_clause_arc_instructions(clauses: list, base_intent: str) -> str:
    """Build a composite TTS instruction describing the delivery arc across clauses.
    
    For single-clause sentences, returns the standard prosody instruction.
    For multi-clause sentences, returns a narrated contour:
      "Start [tone A] for the first part, then shift to [tone B] for the second part."
    
    Args:
        clauses: List of {"text": ..., "tags": [...]} from segment_into_clauses()
        base_intent: The base prosody intent from detect_prosody_intent()
    
    Returns:
        str: Natural language instruction for gpt-4o-mini-tts
    """
    if len(clauses) <= 1:
        # Single clause — use standard instruction
        primary_tag = clauses[0]['tags'][0] if clauses else base_intent
        return PROSODY_INSTRUCTIONS.get(primary_tag, PROSODY_INSTRUCTIONS["neutral"])
    
    # Multi-clause: build a narrated arc
    parts = []
    for i, clause in enumerate(clauses):
        primary_tag = clause['tags'][0]
        tone = _TONE_DESCRIPTORS.get(primary_tag, _TONE_DESCRIPTORS['neutral'])
        
        if i == 0:
            parts.append(f"For the opening part, speak {tone}")
        elif i == len(clauses) - 1:
            parts.append(f"then for the closing part, shift to sounding {tone}")
        else:
            parts.append(f"for the middle part, sound {tone}")
    
    arc = '. '.join(parts) + '.'
    
    # Add universal Alan voice anchors
    arc += (" Throughout, maintain the natural feel of a seasoned phone salesperson — "
            "confident but never pushy, warm but professional. "
            "Let pauses breathe naturally at the transition between parts.")
    
    return arc


# =============================================================================
# [ORGAN 10] BREATH INJECTION LAYER — "Felt Silence"
# =============================================================================
# Turns silent pauses into *felt* breaths without touching cognition or prosody.
#
# Problem: Silence between sentences is pure digital zero (comfort noise).
#          Real humans BREATHE in those gaps. The absence of breath is a 
#          subconscious tell that the speaker isn't human.
#
# Solution: After TTS returns mulaw audio, splice in synthetic breath samples
#           at pause boundaries. These are pre-generated PCM breath patterns
#           (light inhale, soft exhale) encoded to mulaw 8kHz.
#
# Breath samples are generated procedurally — no external files needed.
# Each "breath" is filtered noise shaped like a natural inhale or exhale:
#   - 80-180ms duration
#   - Very quiet (~ -45 to -55 dBm)
#   - Slight amplitude envelope (fade in, sustain, fade out)
#   - Random variation in duration, gain, and sample selection
#
# Placement: After TTS synthesis, before tempo compression and streaming.
# =============================================================================

# Intents that warrant a breath before the sentence (emotional weight)
BREATH_INTENTS = {
    'empathetic_reflect',    # Breath before empathetic response = sincerity
    'reassure_stability',    # Calming breath before reassurance
    'objection_handling',    # Measured breath before addressing pushback
    'repair_clarify',        # Brief inhale before correction
    'closing_momentum',      # Grounding breath before the close
    'micro_hesitate',        # Thinking breath
}

# Pre-generated breath samples (mulaw 8kHz) — procedural, no file I/O
# Generated once at module load. Each is a shaped noise burst.
_BREATH_SAMPLES_CACHE = None

def _generate_breath_samples() -> list:
    """Generate 5 procedural breath samples as mulaw 8kHz bytes.
    
    Each breath is band-limited noise with a human-like envelope:
      - Inhale: noise rises then falls (80-150ms)
      - Exhale: noise with slightly different shape (100-180ms)
    
    All very quiet — just enough to be felt, not consciously heard.
    """
    import struct as _struct
    
    samples = []
    RATE = 8000
    
    # 5 breath variations — loaded from timing_config.json
    breath_specs = TIMING.breath_patterns  # [TIMING CONFIG] Centralized
    
    for spec in breath_specs:
        dur = spec['duration_ms'] / 1000.0
        peak = spec['peak_amp']
        n_samples = int(RATE * dur)
        is_inhale = spec['type'] == 'inhale'
        
        pcm_samples = []
        for i in range(n_samples):
            t = i / n_samples  # 0.0 → 1.0
            
            # Envelope: inhale rises then fades; exhale starts and fades
            if is_inhale:
                # Rise to peak at 40%, then fade
                if t < 0.4:
                    env = t / 0.4
                else:
                    env = 1.0 - ((t - 0.4) / 0.6)
            else:
                # Start at ~80%, fade out
                env = 1.0 - (t * 0.8)
            
            env = max(0.0, env)
            
            # Filtered noise — random with slight low-pass character
            noise = random.uniform(-1.0, 1.0)
            # Simple low-pass: average with previous sample
            if pcm_samples:
                prev_normalized = pcm_samples[-1] / 32767.0
                noise = 0.6 * noise + 0.4 * prev_normalized
            
            sample_val = int(noise * peak * env * 32767)
            sample_val = max(-32768, min(32767, sample_val))
            pcm_samples.append(sample_val)
        
        # Convert to PCM16 bytes then to mulaw
        pcm_bytes = _struct.pack(f'<{len(pcm_samples)}h', *pcm_samples)
        mulaw_bytes = audioop.lin2ulaw(pcm_bytes, 2)
        samples.append(mulaw_bytes)
    
    return samples


def get_breath_samples() -> list:
    """Get cached breath samples (generated once at first call)."""
    global _BREATH_SAMPLES_CACHE
    if _BREATH_SAMPLES_CACHE is None:
        _BREATH_SAMPLES_CACHE = _generate_breath_samples()
        logging.info(f"[ORGAN 10] Generated {len(_BREATH_SAMPLES_CACHE)} breath samples: "
                     f"{[len(s) for s in _BREATH_SAMPLES_CACHE]} bytes each")
    return _BREATH_SAMPLES_CACHE


def inject_breath_before_audio(mulaw_audio: bytes, prosody_intent: str, sentence_idx: int,
                               breath_prob_bias: float = 0.0) -> bytes:
    """Inject a breath sample before the audio if the prosody intent warrants it.
    
    Args:
        mulaw_audio: The TTS-generated mulaw 8kHz audio
        prosody_intent: The active prosody intent for this sentence
        sentence_idx: Which sentence this is (0-based). No breath on first sentence.
        breath_prob_bias: Additive bias from Organ 11 signature (positive = more breaths)
    
    Returns:
        mulaw_audio with breath prepended (or unchanged if no breath needed)
    """
    # No breath on the very first sentence of a turn (Alan just started talking)
    if sentence_idx < 1:
        return mulaw_audio
    
    # Only inject breath for specific emotional/weighted intents
    if prosody_intent not in BREATH_INTENTS:
        # 15% chance of breath even on non-breath intents (natural variation)
        # [ORGAN 11] Signature bias adjusts this probability
        base_breath_prob = 0.15
        adjusted_prob = max(0.0, min(1.0, base_breath_prob + breath_prob_bias))
        if random.random() > adjusted_prob:
            return mulaw_audio
    
    breaths = get_breath_samples()
    if not breaths:
        return mulaw_audio
    
    # Pick a random breath sample
    breath = random.choice(breaths)
    
    # Slight gain variation (±1.5 dB ≈ ±18% linear)
    try:
        gain_variation = random.uniform(-1.5, 1.5)
        # Convert dB to linear: 10^(dB/20)
        linear_gain = 10 ** (gain_variation / 20.0)
        # Apply gain: mulaw → PCM → scale → mulaw
        pcm_breath = audioop.ulaw2lin(breath, 2)
        pcm_breath = audioop.mul(pcm_breath, 2, linear_gain)
        breath = audioop.lin2ulaw(pcm_breath, 2)
    except Exception:
        pass  # Use original on any error
    
    # 20-40ms of silence after the breath (1-2 frames at 8kHz mulaw)
    post_breath_silence = ULAW_SILENCE_BYTE * random.randint(160, 320)  # 1-2 frames
    
    return breath + post_breath_silence + mulaw_audio


# =============================================================================
# [ORGAN 11] ACOUSTIC SIGNATURE LAYER — Alan's Fingerprint
# =============================================================================
# Every human has subconscious acoustic micro-behaviors that make them
# recognizable: a characteristic inhale, a micro-pause before advice,
# a rhythmic reset between thoughts. Alan gets the same.
#
# These are deterministic (not random) — they happen EVERY TIME the right
# conditions arise. That's what makes them a signature, not an artifact.
# Subtle enough to never be consciously noticed. Present enough to be felt.
# =============================================================================

# --- Signature Constants ---
# Alan's micro-pause durations (in mulaw samples at 8kHz = 1 sample/byte)
# These are FIXED — the signature is the consistency itself.
_ALAN_BEAT_SAMPLES = 400        # 50ms — the "Alan Beat" before recommendations
_ALAN_INHALE_SAMPLES = 200      # 25ms — pre-utterance micro-inhale on transitions
_ALAN_RESET_PHASE_A = 160       # 20ms — first phase of thought-reset (silence)
_ALAN_RESET_PHASE_B = 80        # 10ms — second phase (micro-noise)
_ALAN_RESET_PHASE_C = 120       # 15ms — third phase (silence, shorter)

# Intents that trigger each signature behavior
_BEAT_INTENTS = frozenset({
    'confident_recommend', 'reassure_stability', 'closing_momentum'
})
_INHALE_INTENTS = frozenset({
    'objection_handling', 'repair_clarify', 'formal_respectful'
})
_CADENCE_INTENTS = frozenset({
    'repair_clarify', 'curious_probe'
})
_RESET_INTENTS = frozenset({
    'objection_handling', 'empathetic_reflect', 'reassure_stability'
})

# Pre-generate Alan's unique micro-inhale shape (generated once, cached forever)
_ALAN_MICRO_INHALE_CACHE = None

def _generate_alan_micro_inhale() -> bytes:
    """Generate Alan's signature micro-inhale — a deterministic, unique noise shape.
    
    Unlike Organ 10's breath samples (random, varied), this is ALWAYS the same
    waveform. That sameness IS the signature. A human's characteristic inhale
    doesn't change day to day — it's muscular, anatomical, fixed.
    
    Shape: very soft rising-then-falling noise burst, 25ms, peaked at 35% 
    through. Amplitude ~0.004 (barely audible — felt more than heard).
    """
    import struct as _struct
    
    RATE = 8000
    n_samples = _ALAN_INHALE_SAMPLES  # 200 samples = 25ms
    peak_amp = 0.004  # Very quiet — subconscious level
    
    # Use a FIXED seed for determinism — this is Alan's anatomy
    rng = random.Random(7741)
    
    pcm_samples = []
    prev = 0.0
    for i in range(n_samples):
        t = i / n_samples  # 0.0 → 1.0
        
        # Envelope: peak at 35%, asymmetric — quick rise, slow fade
        if t < 0.35:
            env = t / 0.35
        else:
            env = 1.0 - ((t - 0.35) / 0.65)
        env = max(0.0, env) ** 1.3  # Slight exponential softening
        
        # Deterministic filtered noise from fixed seed
        noise = rng.uniform(-1.0, 1.0)
        # Low-pass: weighted average with previous sample (Alan's specific timbre)
        noise = 0.55 * noise + 0.45 * prev
        prev = noise
        
        sample_val = int(noise * peak_amp * env * 32767)
        sample_val = max(-32768, min(32767, sample_val))
        pcm_samples.append(sample_val)
    
    pcm_bytes = _struct.pack(f'<{len(pcm_samples)}h', *pcm_samples)
    mulaw_bytes = audioop.lin2ulaw(pcm_bytes, 2)
    return mulaw_bytes


def _get_alan_micro_inhale() -> bytes:
    """Get Alan's cached micro-inhale (generated once, identical forever)."""
    global _ALAN_MICRO_INHALE_CACHE
    if _ALAN_MICRO_INHALE_CACHE is None:
        _ALAN_MICRO_INHALE_CACHE = _generate_alan_micro_inhale()
        logging.info(f"[ORGAN 11] Alan micro-inhale generated: {len(_ALAN_MICRO_INHALE_CACHE)} bytes (25ms)")
    return _ALAN_MICRO_INHALE_CACHE


def apply_alan_signature(mulaw_audio: bytes, prosody_intent: str, sentence_idx: int) -> bytes:
    """Apply Alan's acoustic signature to a sentence's audio.
    
    This is the identity layer — deterministic micro-behaviors that make
    Alan sound like Alan across every call, every day, every substrate.
    
    Signature behaviors (all subtle, all consistent):
    1. THE ALAN BEAT — 50ms micro-pause prepended before recommendations
    2. PRE-UTTERANCE MICRO-INHALE — Alan's unique 25ms noise shape on transitions
    3. CLARIFICATION CADENCE — subtle amplitude modulation on repair/question intents
    4. THOUGHT-RESET CONTOUR — 3-phase silence pattern between sentences on pivots
    
    Args:
        mulaw_audio: The TTS audio (post-breath-injection, pre-tempo-compression)
        prosody_intent: Active prosody intent for this sentence
        sentence_idx: 0-based sentence index in the turn
    
    Returns:
        Audio with Alan's signature applied
    """
    if not mulaw_audio:
        return mulaw_audio
    
    result = mulaw_audio
    applied = []
    
    # --- SIGNATURE 1: THE ALAN BEAT ---
    # A consistent 50ms micro-pause before recommendations/reassurances.
    # Not silence — comfort-level noise. Like the half-beat a thoughtful
    # person takes before giving advice. Always 50ms. Always.
    if prosody_intent in _BEAT_INTENTS and sentence_idx >= 1:
        # Generate comfort-noise micro-pause (not dead silence — that's unnatural)
        beat_samples = []
        beat_rng = random.Random(sentence_idx * 31 + 17)  # Deterministic per position
        for _ in range(_ALAN_BEAT_SAMPLES):
            # Very quiet noise floor — -50dBFS equivalent
            val = beat_rng.randint(126, 130)  # Near mulaw silence (0xFF=127=silence)
            beat_samples.append(val)
        beat_bytes = bytes(beat_samples)
        result = beat_bytes + result
        applied.append("BEAT")
    
    # --- SIGNATURE 2: PRE-UTTERANCE MICRO-INHALE ---
    # Alan's anatomical inhale — same waveform every time.
    # Only on transitions/objection intents. Only on sentences 1+.
    # This is the "Alan takes a micro-breath before addressing your concern" behavior.
    if prosody_intent in _INHALE_INTENTS and sentence_idx >= 1:
        micro_inhale = _get_alan_micro_inhale()
        # Tiny silence gap after inhale (8ms — 64 samples)
        post_inhale = ULAW_SILENCE_BYTE * 64
        result = micro_inhale + post_inhale + result
        applied.append("INHALE")
    
    # --- SIGNATURE 3: CLARIFICATION CADENCE ---
    # On repair/question intents, apply a subtle amplitude modulation
    # to the first 200ms of audio — a gentle rhythmic "pattern" in volume
    # that's Alan's characteristic way of starting clarifications.
    # Think: the way a person slightly emphasizes the first few words
    # when they're explaining something carefully.
    if prosody_intent in _CADENCE_INTENTS and len(result) > 1600:
        # Modulate first 200ms (1600 samples at 8kHz)
        modulation_region = 1600
        audio_list = list(result)
        for i in range(min(modulation_region, len(audio_list))):
            t = i / modulation_region  # 0→1 over the region
            # Subtle sinusoidal modulation — ±0.5dB at ~6Hz
            # This creates Alan's "careful rhythm" on clarifications
            import math
            mod_factor = 1.0 + 0.06 * math.sin(2 * math.pi * 6.0 * t)
            # Apply to mulaw: convert to linear, scale, convert back
            # Simplified: only modulate samples that aren't silence
            if audio_list[i] != 0xFF:
                # Mulaw is log-compressed. Small gain changes in mulaw space
                # approximate linear gain changes. Shift by ±1 step ≈ ±0.5dB
                if mod_factor > 1.02:
                    audio_list[i] = max(0, audio_list[i] - 1)  # Slightly louder
                elif mod_factor < 0.98:
                    audio_list[i] = min(255, audio_list[i] + 1)  # Slightly quieter
        result = bytes(audio_list)
        applied.append("CADENCE")
    
    # --- SIGNATURE 4: THOUGHT-RESET CONTOUR ---
    # On emotional/pivoting intents, append a characteristic 3-phase
    # micro-silence to the END of the sentence. This is the "Alan 
    # collecting his thoughts" beat that precedes the next sentence.
    # Phase A: 20ms silence → Phase B: 10ms micro-noise → Phase C: 15ms silence
    # The A-B-C pattern is Alan's rhythmic fingerprint between thoughts.
    if prosody_intent in _RESET_INTENTS and sentence_idx >= 1:
        # Phase A: clean silence
        phase_a = ULAW_SILENCE_BYTE * _ALAN_RESET_PHASE_A
        # Phase B: micro-noise burst (Alan's characteristic "thought tick")
        reset_rng = random.Random(sentence_idx * 53 + 89)
        phase_b_samples = []
        for _ in range(_ALAN_RESET_PHASE_B):
            val = reset_rng.randint(124, 132)  # Slightly wider than beat — audible tick
            phase_b_samples.append(val)
        phase_b = bytes(phase_b_samples)
        # Phase C: shorter silence (asymmetric — this IS the signature)
        phase_c = ULAW_SILENCE_BYTE * _ALAN_RESET_PHASE_C
        result = result + phase_a + phase_b + phase_c
        applied.append("RESET")
    
    if applied:
        logging.debug(f"[ORGAN 11 SIGNATURE] Applied {'+'.join(applied)} on sentence {sentence_idx} (intent={prosody_intent})")
    
    return result


logging.info("[ORGAN 7-11] Voice Pipeline WIRED — 11 prosody intents, clause segmentation, delivery arcs, breath injection, acoustic signature")

# Lazy import to avoid initialization issues
AgentAlanBusinessAI = None
try:
    from agent_alan_business_ai import AgentAlanBusinessAI
except Exception as e:
    logging.warning(f"AgentAlanBusinessAI import failed: {e}")
    AgentAlanBusinessAI = None

# Configure logging — console + persistent file for call timing analysis
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add file handler so call timing data survives terminal restarts
import os as _os
_log_dir = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "logs")
_os.makedirs(_log_dir, exist_ok=True)
_call_fh = logging.FileHandler(_os.path.join(_log_dir, "call_timing.log"), encoding="utf-8")
_call_fh.setLevel(logging.INFO)
_call_fh.setFormatter(logging.Formatter("%(asctime)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
logger.addHandler(_call_fh)

# =============================================================================
# [VERSION O] "HUMAN FROM BIRTH" — Sentence Chunking + Human Pacing
# Sources:
#   - https://developers.deepgram.com/docs/tts-text-chunking
#   - https://arxiv.org/html/2508.04721v1 (PunctuatedBufferStreamer pattern)
#   - https://github.com/KoljaB/RealtimeTTS (sentence_silence_duration concept)
#   - https://community.home-assistant.io/t/talk-to-me-goose (LLM→sentence→TTS pipeline)
#
# Key research findings:
#   - Call center bots: "complete sentences work best" (Deepgram)
#   - Per-sentence TTS produces dramatically better prosody than paragraph TTS
#   - Human speakers pause 150-300ms between sentences (natural breathing rhythm)
#   - OpenAI TTS previous_text/next_text maintains vocal continuity across boundaries
#
# [VERSION Q] "UNDETECTABLE" — Human Communication Science
# Sources:
#   - https://pmc.ncbi.nlm.nih.gov/articles/PMC2042536/ (Speech Perception: Sound to Meaning)
#   - https://en.wikipedia.org/wiki/Speech_perception (Phonemic restoration, top-down processing)
#   - https://www.psychologytoday.com/us/blog/conversational-intelligence/201905/the-neuroscience-of-conversations
#   - https://www.bps.org.uk/psychologist/how-real-people-communicate (Conversation Analysis)
#   - https://en.wikipedia.org/wiki/Human_communication (Communication theory)
#
# Key research findings applied:
#   - Conversational repair (self-correction, uncertainty display) is what makes speech human
#   - Trust triggers oxytocin / distrust triggers cortisol (13hr half-life)
#   - Neural coupling (echo/mirror key words) predicts communication success
#   - "Speak" engages more than "talk" (BPS crisis negotiation research)
#   - Silence management: turn-taking clarity prevents awkward dead air
#   - Phonemic restoration: imperfect audio is OK, humans fill gaps from context
#   - Co-regulation: match caller's energy to regulate their emotional state
# =============================================================================

# [HUMAN PACING] Inter-sentence silence duration
# 150ms = 1200 samples at 8kHz = 7.5 frames of 160 bytes
# This matches natural human breathing pauses between sentences on the phone
SENTENCE_SILENCE_FRAMES = 6  # ~120ms of comfort noise between sentences — natural breathing rhythm

# [VERSION P] COMMA MICRO-PAUSE — shorter pause at clause boundaries
# Real humans pause ~60-80ms at commas vs ~150-200ms at periods.
# When first-clause fast fragment splits a sentence at a comma, the gap between
# the fragment and its remainder should be shorter than a full sentence break.
CLAUSE_SILENCE_FRAMES = 3   # ~60ms of silence at clause/comma boundaries

ULAW_SILENCE_BYTE = b'\xFF'  # µ-law silence (digital zero)
FRAME_SIZE = 160  # 20ms at 8kHz, 1 byte/sample for µ-law

# =============================================================================
# [TEMPO AMPLIFIER] Audio Time-Compression Engine
# =============================================================================
# Tim's insight: speed up the audio itself, not just the pacing.
# Works by resampling: we tell audioop the source is at a HIGHER rate than it
# actually is, then downsample to 8kHz. The result plays at normal 8kHz speed
# but contains more speech per second — like a subtle fast-forward.
#
# Example: TEMPO_MULTIPLIER = 1.12 means source treated as 8960Hz → 8000Hz output.
# The audio is compressed by 12%, saving ~120ms per second of speech.
# Values 1.0-1.20 are imperceptible to most listeners.
# =============================================================================
TEMPO_MULTIPLIER = TIMING.tempo_multiplier  # [TIMING CONFIG] Centralized — default 1.06

# =============================================================================
# [SPECULATIVE DECODING] Two-Stage LLM for Latency Reduction
# =============================================================================
# Architecture: Fire a SPRINT call (tiny prompt, max_tokens=30) alongside the
# FULL call. Sprint returns the opening clause in ~500ms vs ~1400ms for full.
# Sprint audio plays immediately, buying time for the full response to arrive.
# The full response then continues seamlessly, skipping overlapping content.
#
# Timeline with speculative decoding:
#   T+0ms:    Bridge fires (pre-cached audio, instant)
#   T+50ms:   Sprint + Full LLM calls fire concurrently
#   T+400ms:  Sprint first token arrives (shorter prompt = faster TTFT)
#   T+600ms:  Sprint clause done → TTS synthesis
#   T+800ms:  Sprint audio plays (merchant hears Alan start responding)
#   T+1400ms: Full LLM first sentence arrives → continues from sprint
#
# Net effect: Perceived first-content latency drops from ~2.3s to ~0.8s.
# Cost: ~$0.00005/turn additional (negligible with gpt-4o-mini pricing).
# =============================================================================
SPECULATIVE_DECODING_ENABLED = True
SPRINT_MAX_TOKENS = 40  # [2026-03-04] Raised from 22 — sprint now generates complete thoughts, not fragments
SPRINT_OVERLAP_THRESHOLD = 0.35  # Word overlap ratio above which full sentence is skipped

# =============================================================================
# [MULTI-SPRINT STRATEGY] Phase 5 Upgrade — Tree-ish Sprint Variants
# =============================================================================
# When enabled, fires N sprint variants with different prompt framings in
# parallel. Takes the first coherent clause that returns. Trades token cost
# for lower tail latency on the opening clause (the thing humans feel most).
#
# Cost impact: ~$0.0001/turn per extra variant (still negligible).
# Enable via config or API flag. Default OFF until tested.
# =============================================================================
MULTI_SPRINT_ENABLED = False         # OFF by default — Phase 5 toggle
MULTI_SPRINT_VARIANTS = 2           # Number of sprint variants to fire (2-3)
MULTI_SPRINT_STYLE_PROMPTS = [
    "Acknowledge what was said, then start your response naturally —",           # Style A: ack-first
    "Respond directly to the point, skip acknowledgment —",                       # Style B: direct
    "Start with a brief empathetic note, then address the question naturally —",  # Style C: empathetic
]

def generate_ring_tone() -> bytes:
    """Generate a realistic US phone ring tone as mulaw 8kHz audio.
    Standard US ring = 440Hz + 480Hz dual-tone.
    Pattern: 1 ring, gap, partial ring (simulates pickup mid-ring), brief silence.
    Total duration ~2.0 seconds. Returns mulaw bytes ready for Twilio streaming."""
    import struct as _struct
    SAMPLE_RATE = 8000
    
    def _gen_ring(duration, volume=0.25):
        """Generate ring tone samples (440+480Hz dual tone with fade)"""
        samples = []
        n = int(SAMPLE_RATE * duration)
        fade = int(SAMPLE_RATE * 0.015)  # 15ms fade in/out
        for i in range(n):
            t = i / SAMPLE_RATE
            s = volume * (math.sin(2 * math.pi * 440 * t) + math.sin(2 * math.pi * 480 * t)) / 2
            if i < fade:
                s *= i / fade
            elif i > n - fade:
                s *= (n - i) / fade
            samples.append(int(s * 32767))
        return samples
    
    def _gen_silence(duration):
        return [0] * int(SAMPLE_RATE * duration)
    
    # [LATENCY FIX] Shortened from 2.3s to 0.5s — just a brief pickup click + silence
    # Old pattern (2.3s): ring(0.8s) + gap(0.8s) + partial ring(0.3s) + silence(0.4s)
    # New pattern (0.5s): tiny click(0.05s) + brief silence(0.15s)
    # On outbound cold calls, every second of delay = higher hangup rate
    pcm_samples = []
    pcm_samples.extend(_gen_ring(0.05, volume=0.08))   # Tiny click — barely perceptible
    pcm_samples.extend(_gen_silence(0.15))              # Brief settling silence
    
    # Convert to 16-bit PCM bytes
    pcm_bytes = _struct.pack(f'<{len(pcm_samples)}h', *pcm_samples)
    # Convert to mulaw
    return audioop.lin2ulaw(pcm_bytes, 2)

def tempo_compress_audio(mulaw_audio: bytes) -> bytes:
    """Apply tempo compression to mulaw audio.
    Treat the audio as if it were recorded at a higher sample rate,
    then downsample to 8kHz. This makes speech faster without pitch shift
    (unlike simply playing samples faster, which would raise pitch).
    
    At TEMPO_MULTIPLIER=1.12:
    - 1 second of speech becomes ~0.89 seconds
    - Voice pitch stays natural (resampling preserves frequency ratios)
    - Saves ~110ms per second of Alan's speech
    """
    if TEMPO_MULTIPLIER <= 1.0:
        return mulaw_audio  # No compression
    
    try:
        # 1. Decode mulaw to PCM16
        pcm = audioop.ulaw2lin(mulaw_audio, 2)
        
        # 2. Resample: pretend source is at higher rate, output at 8000
        # This compresses the audio temporally
        source_rate = int(8000 * TEMPO_MULTIPLIER)  # e.g., 8960 for 1.12x
        compressed, _ = audioop.ratecv(pcm, 2, 1, source_rate, 8000, None)
        
        # 3. Re-encode to mulaw
        return audioop.lin2ulaw(compressed, 2)
    except Exception:
        return mulaw_audio  # Fallback to original on any error

# [VERSION P] COMFORT NOISE GENERATION (CNG)
# Source: ITU-T G.711 Appendix II — Comfort Noise for µ-law
# Source: https://en.wikipedia.org/wiki/G.711 — "G.711 Appendix II defines a
#   discontinuous transmission (DTX) algorithm which uses voice activity detection
#   (VAD) and comfort noise generation (CNG) to reduce bandwidth during silence periods"
#
# Problem: Pure 0xFF (digital zero) creates absolute silence between sentences.
# Real phone calls NEVER have absolute silence — there's always ambient line noise
# from the network. The "dead air → sudden voice" transition is a subtle but
# detectable tell that the audio is synthetic.
#
# Solution: Generate low-level random µ-law noise that simulates natural phone
# line background noise. In µ-law, values near 0xFF represent very quiet sounds.
# Values 0xF0-0xFF and 0x70-0x7F are the quietest positive and negative values
# respectively (±1 to ±30 in linear PCM).
#
# We use values in the range 0xFA-0xFF and 0x7A-0x7F which correspond to
# approximately -60 to -70 dBm — matching real telephone comfort noise levels.
COMFORT_NOISE_ULAW = list(range(0xFA, 0x100)) + list(range(0x7A, 0x80))

def generate_comfort_noise_frame():
    """Generate a single frame of comfort noise that sounds like phone line background.
    Source: ITU-T G.711 Appendix II (CNG)
    Uses very quiet µ-law values to simulate ambient telephone line noise.
    """
    return bytes(random.choice(COMFORT_NOISE_ULAW) for _ in range(FRAME_SIZE))

def split_into_sentences(text):
    """Split text into natural sentences for per-sentence TTS.
    
    Source: Deepgram TTS Text Chunking Guide
    "Call center bots: Use complete sentences (most natural)"
    
    Per-sentence TTS produces better prosody because:
    1. TTS model generates proper sentence-level intonation contours
    2. Natural emphasis at declarative/question/exclamation endings
    3. No run-on flat monotone from processing entire paragraphs
    4. Each sentence is independently well-formed
    
    [VERSION P] First-Clause Fast Fragment:
    Source: RealtimeTTS fast_sentence_fragment + force_first_fragment_after_words
    Source: Deepgram "Clause-based chunking: Splits long sentences at commas and semicolons"
    If the first sentence is long (>50 chars), split it at the first comma/semicolon
    so TTS can start playing the first clause immediately while the rest processes.
    This reduces perceived latency — the caller hears "Well," or "So, here's the thing"
    before the full sentence even finishes synthesizing.
    """
    if not text or not text.strip():
        return []
    # Split at sentence boundaries (.!?) followed by whitespace
    # Preserves the punctuation on the sentence
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    # Remove empty or trivial fragments (< 3 chars)
    sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 2]
    
    # [VERSION P] FIRST-CLAUSE FAST FRAGMENT
    # If the first sentence is long, split at the first comma or semicolon
    # to start audio playback faster. Only do this for the first sentence —
    # subsequent sentences benefit from pipelining overlap anyway.
    if sentences and len(sentences[0]) > 50:
        first = sentences[0]
        # Find first comma or semicolon that's at least 8 chars in
        # (don't split on "So," alone — too short to sound good)
        clause_match = re.search(r'[,;]\s+', first[8:])
        if clause_match:
            split_pos = 8 + clause_match.end()
            fragment = first[:split_pos].strip()
            remainder = first[split_pos:].strip()
            if fragment and remainder and len(fragment) > 5:
                sentences = [fragment, remainder] + sentences[1:]
    
    return sentences


# =============================================================================
# [AQI 0.1mm CHIP] State Derivation — Map existing signals to AQI FSM states
# =============================================================================
# Alan's existing deep_layer tracks conversation mode (OPENING, DISCOVERY, etc.)
# which maps directly to AQI FSM states. This function bridges the two systems.
# =============================================================================

def _derive_aqi_state(context: dict) -> str:
    """Derive the current AQI FSM state from existing conversation signals.
    
    Priority:
    1. Deep layer mode (canonical — already tracks OPENING/DISCOVERY/VALUE/etc.)
    2. Master closer state (fallback — trajectory/endgame map to phases) 
    3. Turn count heuristic (last resort)
    """
    # 1. Deep layer mode is the canonical source
    bp = context.get('behavior_profile')
    if isinstance(bp, dict):
        dl_mode = bp.get('deep_layer_mode', '')
        if dl_mode:
            # Deep layer uses exact AQI names
            mode_upper = dl_mode.upper()
            if mode_upper in ('OPENING', 'DISCOVERY', 'VALUE', 'OBJECTION', 'CLOSE', 'EXIT'):
                return mode_upper
            # Map deep layer variants to AQI states
            _mode_map = {
                'RAPPORT': 'OPENING',
                'EXPLORE': 'DISCOVERY', 
                'PRESENT': 'VALUE',
                'HANDLE': 'OBJECTION',
                'CLOSING': 'CLOSE',
                'ENDED': 'EXIT',
            }
            if mode_upper in _mode_map:
                return _mode_map[mode_upper]
    
    # 2. Master closer state fallback
    mc = context.get('master_closer_state', {})
    if mc:
        endgame = mc.get('endgame_state', '')
        if endgame == 'ready':
            return 'CLOSE'
        trajectory = mc.get('trajectory', '')
        if trajectory == 'warming':
            return 'VALUE'
    
    # 3. Turn count heuristic (last resort)
    turns = len(context.get('messages', []))
    if turns == 0:
        return 'OPENING'
    elif turns <= 2:
        return 'DISCOVERY'
    else:
        return 'VALUE'


def _derive_aqi_event(context: dict, user_text: str = '') -> str:
    """Derive the AQI FSM event from conversation signals."""
    # Check for objection
    if context.get('live_objection_type'):
        return 'objection_detected'
    
    # Check for health degradation
    health_int = context.get('_organism_health_int', 1)
    if health_int >= 3:
        return 'degrade'
    
    # Check for ethical veto
    if context.get('_ethical_constraint'):
        return 'veto'
    
    # Check for stream ended
    if context.get('stream_ended'):
        return 'end'
    
    # Default: merchant or agent speech
    if user_text:
        return 'merchant_speaks'
    return 'agent_speaks'


def _build_aqi_health_snapshot(context: dict) -> dict:
    """Build AQI health snapshot from existing health monitors."""
    return {
        'organism_level': context.get('_organism_health_int', 1),
        'organism_name': context.get('_organism_health_level', 'HEALTHY'),
        'telephony_state': context.get('_telephony_health_state', 'Excellent'),
        'telephony_int': context.get('_telephony_health_int', 0),
        'organism_directive': context.get('_organism_health_directive'),
        'telephony_directive': context.get('_telephony_health_directive'),
    }


class AQIConversationRelayServer:
    """
    WebSocket server for handling Twilio ConversationRelay conversations
    """

    def __init__(self):
        # [PRE-WARM] Instantiate Agent Only ONCE per Server Start
        # This prevents 3-5 second delay per call
        logger.info("[ALAN AI] Pre-warming AgentAlanBusinessAI System...")
        try:
             self.shared_agent_instance = AgentAlanBusinessAI()
             logger.info("[ALAN AI] AgentAlanBusinessAI PRE-WARMED & READY")
        except Exception as e:
             logger.error(f"[ALAN AI] Pre-warm failed: {e}")
             self.shared_agent_instance = None
             raise RuntimeError(f"[COUPLED BOOT] Alan failed to initialize: {e}")


        self.active_conversations = {}
        self._conversations_lock = asyncio.Lock()
        self.greeting_cache = {} # [FIX] Initialize Audio Cache
        self.ring_tone_audio = generate_ring_tone()  # Pre-generate ring tone
        logger.info(f"[RING TONE] Generated {len(self.ring_tone_audio)} bytes of ring tone audio")

        # [RAPPORT MODULE] Load personality heuristics
        try:
            with open("rapport_layer.json", "r") as f:
                self.rapport_layer = json.load(f)
            logger.info("[RAPPORT] Personality heuristics loaded successfully")
        except Exception as e:
            logger.error(f"[RAPPORT] Failed to load rapport_layer.json: {e}")
            self.rapport_layer = {}

        # [AGENT X SUPPORT] Initialize conversation support engine
        if AGENT_X_SUPPORT_WIRED:
            self.agent_x_support = AgentXConversationSupport(
                self.rapport_layer,
                base_dir=os.path.dirname(os.path.abspath(__file__))
            )
            logger.info("[AGENT X SUPPORT] Conversation Support Engine loaded with rapport layer + IQ Cores")
        else:
            self.agent_x_support = None
            raise RuntimeError("[COUPLED BOOT] Agent X failed to initialize — AgentXConversationSupport not wired")

        # [CLOSER STACK] Initialize Engines
        self.predictive_engine = PredictiveIntentEngine()
        self.closing_engine = ClosingStrategyEngine()
        
        # [MASTER CLOSER] Initialize Layer
        self.master_closer = MasterCloserLayer()

        # [BAL] Initialize Behavior Adaptation Engine
        self.behavior_engine = BehaviorAdaptationEngine()

        # [CRG] Initialize Cognitive Reasoning Governor
        self.crg = CognitiveReasoningGovernor()

        # [EVOLUTION] Initialize Outcome Detection and Evolution Engine
        self.odl = OutcomeDetectionLayer()
        self.evolution = EvolutionEngine()
        self.cocs = CallOutcomeConfidenceScorer("call_outcome_confidence_config.json")
        self.attribution_engine = OutcomeAttributionEngine("outcome_attribution_config.json")
        self.aggregation_engine = ReviewAggregationEngine("review_aggregation_config.json")
        
        # [ALAN V2] Initialize System Coordinator & Subsystems
        try:
            with open("system_config.json", "r") as f:
                self.system_config = json.load(f)
            logger.info("[ALAN V2] System config loaded")
        except:
            self.system_config = {}
            logger.warning("[ALAN V2] System config missing, using defaults")

        self.eos = EmergencyOverrideSystem(logger=logger)
        # Placeholder KB for PGHS - using rapport layer as basic knowledge
        kb = self.rapport_layer 
        self.pghs = PostGenerationHallucinationScanner(self.system_config, kb, self.eos)
        self.mip = MerchantIdentityPersistence()
        self.mtsp = MultiTurnStrategicPlanner()
        self.bas = BiasAuditingSystem()
        
        # We need the Supervisor instance. It is a singleton.
        self.supervisor_instance = AlanSupervisor.get_instance()

        self.coordinator = SystemCoordinator(
            self.eos, self.pghs, self.supervisor_instance, 
            self.mtsp, self.mip, self.bas, 
            self.system_config
        )
        
        # Initialize Human Override API
        self.human_override = HumanOverrideAPI(self.eos, self.mip, self.mtsp, None)

        # OpenAI TTS client for voice synthesis
        # Voice: "onyx" — deep, warm male. Less sibilance than "echo".
        # Model: gpt-4o-mini-tts (faster than tts-1, supports instructions)
        # Output: PCM 24kHz → converted to mulaw 8kHz for Twilio
        self._tts_voice = "onyx"  # Deep, warm male — minimal sibilance on phone audio
        self._tts_model = "gpt-4o-mini-tts"  # Faster model with instruction support
        openai_key = os.getenv("OPENAI_API_KEY")
        if not openai_key:
            try:
                import json as _json
                with open("agent_alan_config.json", "r") as f:
                    openai_key = _json.load(f).get("openai_api_key")
            except Exception as _cfg_err:
                logger.debug(f"[TTS] Config file OpenAI key fallback failed: {_cfg_err}")
        if openai_key:
            # CRITICAL: Explicit base_url to bypass OPENAI_BASE_URL env var
            # (that env var may be stale — always use explicit base_url for TTS)
            self.tts_client = OpenAIClient(api_key=openai_key, base_url="https://api.openai.com/v1", timeout=15.0)  # [TIMING AUDIT] 15s TTS timeout (allows cold-start greeting synthesis)
            logger.info(f"[TTS] OpenAI TTS configured (voice={self._tts_voice}, model={self._tts_model})")
        else:
            self.tts_client = None
            logger.warning("[TTS] No OPENAI_API_KEY found. Mouth is shut.")

        self.executor = ThreadPoolExecutor(max_workers=6)  # [NEG-PROOF] 6 workers: LLM+TTS+prefetch per call × 2 concurrent calls
        
        # [AQI 0.1mm CHIP] Initialize Runtime Guard — constitutional conformance engine
        # Validates governance order, FSM legality, health constraints, and supervision
        # non-interference per turn and per call. Non-blocking, non-crashing.
        if AQI_GUARD_WIRED:
            try:
                self._aqi_guard = create_runtime_guard("AQI_ORGANISM_SPEC.md")
                logger.info("[AQI GUARD] Runtime Guard initialized at server startup — 6 enforcement organs active")
            except Exception as _guard_err:
                logger.error(f"[AQI GUARD] Failed to initialize: {_guard_err}")
                self._aqi_guard = None
        else:
            self._aqi_guard = None

        # [PHASE 4] Trace Exporter — accumulates per-call telemetry, writes canonical JSONL
        if PHASE4_EXPORTER_WIRED:
            try:
                self._phase4_exporter = Phase4TraceExporter()
                logger.info("[PHASE 4 EXPORTER] Initialized — canonical trace export active")
            except Exception as _p4_err:
                logger.error(f"[PHASE 4 EXPORTER] Failed to initialize: {_p4_err}")
                self._phase4_exporter = None
        else:
            self._phase4_exporter = None

        # [LAG FIX] Persistent HTTP session for OpenAI API — reuses TCP/TLS connections
        # across LLM calls. Saves ~150ms per call (TCP handshake + TLS negotiation).
        # [LATENCY FIX] HTTPAdapter with connection pooling + automatic retry on transient failures.
        # pool_connections=4 keeps 4 TCP connections warm to api.openai.com.
        # pool_maxsize=8 allows burst parallelism (sprint + full LLM + prewarm).
        # Retry on 502/503/504 (OpenAI transient errors) with 0.3s backoff.
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        _retry_strategy = Retry(
            total=2,
            backoff_factor=0.3,
            status_forcelist=[502, 503, 504],
            allowed_methods=["POST"],
        )
        _adapter = HTTPAdapter(
            pool_connections=4,
            pool_maxsize=8,
            max_retries=_retry_strategy,
        )
        self._llm_session = requests.Session()
        self._llm_session.mount("https://", _adapter)
        self._llm_session.headers.update({"Content-Type": "application/json"})
        
        self.stream_sid_to_client_id = {}
        aqi_stt_engine.register_stt_callback(self.on_stt_text)
        
        # [ZERO-LATENCY] Pre-cache ALL greeting variants as mulaw audio at startup.
        # Greeting TTS takes 300-600ms live. Pre-caching eliminates this entirely.
        # The greeting_cache dict maps greeting text → mulaw bytes.
        self._precache_greetings()
        
        logger.info("AQI Conversation Relay Server initialized")

    def subsystem_status(self):
        """[COUPLED BOOT] Returns live status of both Alan and Agent X.
        If one comes online, they both must. If either is down, the system reports it."""
        alan_online = self.shared_agent_instance is not None
        agent_x_online = self.agent_x_support is not None
        both_online = alan_online and agent_x_online
        return {
            "alan": "ONLINE" if alan_online else "OFFLINE",
            "agent_x": "ONLINE" if agent_x_online else "OFFLINE",
            "coupled": both_online,
            "status": "READY" if both_online else "DEGRADED",
        }

    def _precache_greetings(self):
        """[ZERO-LATENCY] Pre-synthesize all greeting variants at startup.
        Runs TTS for each greeting template and stores mulaw bytes in greeting_cache.
        This eliminates 300-600ms of TTS latency on the very first audio of every call."""
        if not self.tts_client:
            logger.warning("[GREETING CACHE] No TTS client — cannot pre-cache greetings")
            return
        
        # [CIRCUIT BREAKER] If TTS API is down (quota/billing), stop after 2 consecutive
        # failures instead of hammering the API with 30+ doomed requests.
        consecutive_failures = 0
        MAX_CONSECUTIVE_FAILURES = 2
        
        def _try_cache(text, label="GREETING"):
            """Attempt to cache one phrase. Returns True on success, False on failure."""
            nonlocal consecutive_failures
            if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                return False  # Circuit open — skip remaining
            try:
                audio = self._openai_tts_sync(text)
                if audio and len(audio) > 0:
                    self.greeting_cache[text] = audio
                    consecutive_failures = 0  # Reset on success
                    return True
                else:
                    consecutive_failures += 1
                    return False
            except Exception as e:
                consecutive_failures += 1
                logger.error(f"[{label} CACHE] Failed to cache '{text[:40]}': {e}")
                return False
        
        # All possible greeting templates (complete greetings that can be cached whole)
        INBOUND = [
            "Signature Card Services, this is Alan.",
            "Signature Card, Alan speaking."
        ]
        COLD = [
            # [FEB 27 2026] PRECISION OPENERS — 7-10 words, fast delivery
            "Hey, this is Alan. Is the owner around?",
            "Hi, this is Alan. Is the owner available?",
            "Hey, it's Alan. Is the owner or manager there?",
            "Hey, this is Alan calling. Is the owner in?",
            "Hi, this is Alan from Signature Card. Is the owner available?",
        ]
        # [TWO-STAGE] Named greeting PREFIXES — cached so named greetings start instantly
        NAMED_PREFIXES = [
            # SOFT PREFIXES (no company name)
            "Hey, this is Alan.",
            "Hi, this is Alan.",
            "Hey, it's Alan.",
            # STANDARD PREFIX (with company name — shortened)
            "Hi, this is Alan from Signature Card.",
        ]
        all_greetings = INBOUND + COLD + NAMED_PREFIXES
        
        cached = 0
        for greeting in all_greetings:
            if _try_cache(greeting, "GREETING"):
                cached += 1
        
        if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
            logger.warning(f"[GREETING CACHE] CIRCUIT BREAKER: TTS API unavailable — cached {cached}/{len(all_greetings)} greetings before failure. Server will start without pre-cache.")
            return  # Don't attempt bridge or Turn-01 caching
        
        logger.info(f"[GREETING CACHE] Pre-cached {cached}/{len(all_greetings)} greetings ({sum(len(v) for v in self.greeting_cache.values())} bytes total)")

        # [BRIDGE CACHE] Pre-synthesize bridge utterances ("Yeah, so...", "Got it...", etc.)
        # These are the short filler phrases that play INSTANTLY while LLM thinks.
        # Without caching, the bridge itself needs an 800ms TTS call — defeating the purpose.
        from conversational_intelligence import BRIDGE_UTTERANCES
        bridge_cached = 0
        all_bridges = set()
        for bridge_list in BRIDGE_UTTERANCES.values():
            for phrase in bridge_list:
                all_bridges.add(phrase)
        for phrase in all_bridges:
            if _try_cache(phrase, "BRIDGE"):
                bridge_cached += 1
        
        if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
            logger.warning(f"[BRIDGE CACHE] CIRCUIT BREAKER: TTS API unavailable — cached {bridge_cached}/{len(all_bridges)} bridges before failure.")
            return
        logger.info(f"[BRIDGE CACHE] Pre-cached {bridge_cached}/{len(all_bridges)} bridge utterances")

        # =====================================================================
        # [TURN-01 FAST RESPONSE CACHE] Pre-synthesize instant Turn-01 replies
        # =====================================================================
        # Problem: After Alan's greeting, the merchant responds ("Speaking", "Who
        # is this?", "Yeah"). Full LLM pipeline takes 2.4-5.9 seconds → dead air
        # → merchant hangs up. On cold calls, Turn 01 latency is the #1 killer.
        #
        # Fix: Pre-cache common Turn-01 responses. When merchant gives a short,
        # pattern-matchable reply, BYPASS the LLM entirely and serve cached audio.
        # Latency drops from ~3500ms to ~50ms (cache lookup + frame streaming).
        #
        # Categories:
        #   ack_owner    → "Speaking" / "This is [name]" / "Yeah" / "That's me"
        #   ack_transfer → "Hold on" / "One moment" / "Let me get them"
        #   identity     → "Who is this?" / "Who's calling?"
        #   purpose      → "What's this about?" / "What do you need?"
        #   greeting     → "Hello?" / "Hi" / "Hey"
        # =====================================================================
        # [2026-03-02 FIX] Diversified T01 responses — removed "Quick question" from
        # 4 of 6 categories. The repeated phrase was reinforcing a loop where the LLM
        # mirrored it. Each response now uses distinct, natural phrasing.
        TURN01_RESPONSES = {
            'ack_owner': "So I do free rate reviews for business owners — are you guys accepting cards there?",
            'ack_transfer': "Sure, take your time.",
            'identity': "It's Alan from Signature Card Services — I do free rate reviews for business owners.",
            'purpose': "I help business owners cut their card processing costs — takes about 30 seconds.",
            'greeting': "Hey — so are you the owner or manager there?",
            'busy': "No problem — when's a better time to call back?",
        }
        self._turn01_responses = TURN01_RESPONSES  # Store for runtime lookup
        t01_cached = 0
        for category, response_text in TURN01_RESPONSES.items():
            if _try_cache(response_text, "T01"):
                t01_cached += 1
        
        if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
            logger.warning(f"[T01 CACHE] CIRCUIT BREAKER: TTS API unavailable — cached {t01_cached}/{len(TURN01_RESPONSES)} Turn-01 responses before failure.")
            return
        logger.info(f"[T01 CACHE] Pre-cached {t01_cached}/{len(TURN01_RESPONSES)} Turn-01 fast responses")

    def on_stt_text(self, text, stream_sid):
        """New speech arrived. Cancel anything in progress. Respond.
        
        HUMAN MODEL: In real conversation, there are no locks or blocked states.
        If someone speaks while you're talking, you stop and listen.
        If someone speaks while you're thinking, you think about the new thing.
        New input always wins. That's it.
        """
        client_id = self.stream_sid_to_client_id.get(stream_sid)
        if not client_id:
             logger.warning(f"[STT] No client_id for stream_sid {stream_sid}. Dropping: '{text}'")
             return
        if client_id not in self.active_conversations:
             logger.warning(f"[STT] client_id {client_id} not in active. Dropping: '{text}'")
             return
             
        context = self.active_conversations[client_id]
        websocket = context.get('websocket')
        if not websocket:
            logger.error(f"[STT] No websocket for client_id {client_id}.")
            return
            
        logger.info(f"[STT] Input: '{text}' for {stream_sid}")
        
        # [INSTRUMENT] Stamp STT done — Whisper just returned
        context['_stt_done_mono'] = time.monotonic()
        _vad_end = context.get('_vad_end_mono')
        if _vad_end:
            _stt_lag = 1000 * (context['_stt_done_mono'] - _vad_end)
            logger.info(f"[INSTRUMENT] STT lag (vad_end→stt_done): {_stt_lag:.0f}ms")
        
        # [VAD GUARD] Prepend any held text from when user was still speaking
        pending = context.get('pending_stt_text', '')
        if pending:
            text = (pending + ' ' + text).strip()
            context['pending_stt_text'] = ''
            logger.info(f"[VAD GUARD] Merged with pending. Full text: '{text[:80]}'")
        
        # [ECHO FIX] Text-level echo detection — safety net if audio-level gate fails.
        # Compare STT text against Alan's last spoken words. If the user's input starts
        # with what Alan just said (phone mic picked up Alan's voice), strip the echo part.
        # Also drop pure-echo transcriptions entirely (100% match = just Alan talking to himself).
        
        # Determine last message from Alan for echo cancellation
        messages = context.get('messages', [])
        alan_last = ""
        if messages:
            alan_last = messages[-1].get('alan', '')
        if not alan_last:
            agent = context.get('agent_instance')
            if agent and hasattr(agent, 'conversation_history') and agent.conversation_history.history:
                 for msg in reversed(agent.conversation_history.history):
                     if msg.get('sender') == 'Alan':
                         alan_last = msg.get('message', '')
                         break

        # [GREETING ECHO PROTECTION] Check if the input is just our own greeting echoing back.
        # This is the most common failure mode on call start.
        text_lower = text.lower().strip()
        from difflib import SequenceMatcher
        
        # Check against all known greetings if we are early in the call
        # (Assuming greetings are cached in self.greeting_cache)
        if self.greeting_cache and len(messages) <= 2:
            for greeting in self.greeting_cache.keys():
                greeting_lower = greeting.lower().strip()
                # Check for high similarity or prefix match
                ratio = SequenceMatcher(None, text_lower, greeting_lower).ratio()
                if ratio > 0.70: # Lowered threshold: 0.70 catches "Signature Card, SCS Direct" (partial match)
                     logger.info(f"[ECHO FILTER] Dropped GREETING echo (similarity {ratio:.2f}): '{text[:60]}'")
                     return
                # Check if text starts with greeting (or greeting starts with text if partial)
                if len(text_lower) > 8 and greeting_lower.startswith(text_lower):
                     logger.info(f"[ECHO FILTER] Dropped partial GREETING echo (prefix): '{text[:60]}'")
                     return
        
        if alan_last and len(text) > 3:
            # text_lower already set above
            alan_lower = alan_last.lower().strip()
            
            # Check if STT text starts with a significant portion of Alan's last response
            # This catches: "How long have you been in business? Three years." where
            # the first part is echo and "Three years" is the real user input.
            similarity = SequenceMatcher(None, text_lower, alan_lower).ratio()
            
            if similarity > 0.85:
                # Almost identical to what Alan said — pure echo, drop entirely
                logger.info(f"[ECHO FILTER] Dropped pure echo (similarity {similarity:.2f}): '{text[:60]}'")
                return
            
            # Check if text STARTS with Alan's last sentence
            # Split Alan's response into sentences and check each
            import re as _re
            alan_sentences = [s.strip() for s in _re.split(r'[.!?]+', alan_last) if s.strip()]
            for alan_sent in alan_sentences:
                alan_sent_lower = alan_sent.lower().strip()
                if len(alan_sent_lower) > 5 and text_lower.startswith(alan_sent_lower[:min(len(alan_sent_lower), 30)].rstrip()):
                    # The STT picked up this sentence from Alan's playback
                    # Find where the echo ends and the real user text begins
                    echo_end = text_lower.find(alan_sent_lower[:min(len(alan_sent_lower), 30)].rstrip()) + len(alan_sent_lower)
                    remaining = text[echo_end:].strip().lstrip('.,!?').strip()
                    if remaining and len(remaining) > 2:
                        logger.info(f"[ECHO FILTER] Stripped echo prefix. Echo='{alan_sent[:40]}', Remaining='{remaining}'")
                        text = remaining
                    else:
                        logger.info(f"[ECHO FILTER] All text was echo. Dropping: '{text[:60]}'")
                        return
                    break
        
        # [STREAM GUARD] Don't process if stream already closed
        if context.get('stream_ended'):
            logger.info(f"[STT] Stream already ended. Dropping: '{text[:40]}'")
            return
        
        # ================================================================
        # [STT GARBAGE DETECTOR] Detect STT hallucination / repetition loops
        # ================================================================
        # [FIX 2026-02-24] STT (especially Whisper) can hallucinate when
        # processing silence, hold music, or noise — producing garbage like
        # "married married married married..." x100. This gets misclassified
        # as human speech (high word count, no VM patterns). Detect and drop.
        # ================================================================
        _stt_words = text.split()
        if len(_stt_words) >= 6:
            from collections import Counter
            _word_freq = Counter(w.lower().strip('.,!?') for w in _stt_words)
            _most_common_word, _most_common_count = _word_freq.most_common(1)[0]
            # If one word appears 5+ times AND makes up >40% of all words → STT garbage
            if _most_common_count >= 5 and _most_common_count / len(_stt_words) > 0.40:
                logger.warning(f"[STT-GARBAGE] Detected repetition hallucination: "
                               f"'{_most_common_word}' x{_most_common_count} in {len(_stt_words)} words. "
                               f"Dropping: '{text[:60]}...'")
                # Mark as non-human, non-learning
                context['_ccnm_ignore'] = True
                # If this is the first utterance, classify as unknown and don't engage
                if not context.get('_eab_classified'):
                    context['_eab_classified'] = True
                    context['_eab_env_class'] = 'UNKNOWN'
                    context['_eab_action'] = EnvironmentAction.FALLBACK if EAB_WIRED else None
                    context['_eab_confidence'] = 0.0
                    logger.info("[STT-GARBAGE] First utterance was garbage — classified UNKNOWN, skipping cognition")
                return

        # ================================================================
        # [EAB] ENVIRONMENT-AWARE BEHAVIOR — FIRST-UTTERANCE CLASSIFIER
        # ================================================================
        # Runs on every merchant utterance until classification is locked.
        # On first utterance: classifies environment → routes behavior.
        # On subsequent utterances in screener/IVR: checks loop limits.
        #
        # Actions:
        #   CONTINUE_MISSION  → let normal cognition pipeline handle it
        #   PASS_THROUGH      → speak pass-through template, wait for next utterance
        #   NAVIGATE          → speak IVR nav template (future: DTMF)
        #   DROP_AND_ABORT    → speak voicemail drop line + hang up
        #   DECLINE_AND_ABORT → speak answering service decline + hang up
        #   FALLBACK          → let normal pipeline handle it
        # ================================================================
        if EAB_WIRED:
            _eab = context.get('_eab_classifier')
            if _eab:
                _eab_classified = context.get('_eab_classified', False)
                _eab_action = context.get('_eab_action')

                # --- FIRST CLASSIFICATION (first real merchant utterance) ---
                if not _eab_classified:
                    _eab_result = _eab.classify(text)
                    context['_eab_classified'] = True
                    context['_eab_env_class'] = _eab_result.env_class.name
                    context['_eab_action'] = _eab_result.action
                    context['_eab_confidence'] = _eab_result.confidence
                    context['_eab_cycle'] = 1

                    # [INSTRUMENT] Stamp EAB done
                    context['_env_done_mono'] = time.monotonic()
                    logger.info(f"[EAB] FIRST CLASSIFICATION: {_eab_result.env_class.name} "
                                f"(conf={_eab_result.confidence:.2f}) → action={_eab_result.action.name}")

                    # [CDC] Record environment classification
                    if CALL_CAPTURE_WIRED:
                        _call_sid_eab = context.get('call_sid', '')
                        _cdc_environment(
                            _call_sid_eab,
                            env_class=_eab_result.env_class.name,
                            env_confidence=_eab_result.confidence,
                            behavior=_eab_result.action.name,
                            outcome='',  # filled at call end
                            utterance=text[:200],
                            cycles=1,
                        )

                    _merchant_name = context.get('prospect_info', {}).get('company', '')

                    # ---- HUMAN / UNKNOWN / LIVE_RECEPTIONIST → continue normal pipeline ----
                    if _eab_result.action == EnvironmentAction.CONTINUE_MISSION:
                        logger.info(f"[EAB] HUMAN detected — continuing normal cognition pipeline")
                        # Fall through to normal pipeline below

                    # ---- FALLBACK → also continue normal pipeline ----
                    elif _eab_result.action == EnvironmentAction.FALLBACK:
                        logger.info(f"[EAB] UNKNOWN env — continuing normal pipeline as fallback")
                        # Fall through to normal pipeline below

                    # ---- PASS_THROUGH (screener, spam blocker, AI receptionist) ----
                    elif _eab_result.action == EnvironmentAction.PASS_THROUGH:
                        _template_text = EnvironmentBehaviorTemplates.get_template(
                            _eab_result.env_class, _merchant_name, cycle=0
                        )
                        if _template_text and websocket:
                            logger.info(f"[EAB] PASS-THROUGH: '{_template_text[:80]}'")
                            try:
                                asyncio.create_task(
                                    self.synthesize_and_stream_greeting(
                                        websocket, _template_text, context.get('streamSid')
                                    )
                                )
                            except Exception as _eab_err:
                                logger.debug(f"[EAB] Pass-through TTS failed: {_eab_err}")
                        # Don't run cognition — we spoke the template
                        context['_ccnm_ignore'] = True
                        return

                    # ---- NAVIGATE (business IVR) ----
                    elif _eab_result.action == EnvironmentAction.NAVIGATE:
                        # [ORGAN 37+36] IVR Navigator + DTMF Reflex — parse menu, press buttons
                        _ivr_nav = context.get('_ivr_navigator') if IVR_NAVIGATOR_WIRED else None
                        _dtmf = context.get('_dtmf_reflex') if DTMF_REFLEX_WIRED else None
                        _stream_sid = context.get('streamSid')

                        if _ivr_nav and _dtmf and websocket and _stream_sid:
                            context['_ivr_nav_active'] = True
                            _call_sid_dtmf = context.get('call_sid', '')
                            _decision = _ivr_nav.process_utterance(transcript_text)
                            logger.info(f"[EAB+IVR] Navigator decision: action={_decision.action.name}, digit={_decision.digit}, state={_ivr_nav.state.name}")

                            if _decision.action == IVRAction.SEND_DTMF and _decision.digit:
                                # Press the button(s) the navigator chose
                                logger.info(f"[EAB+IVR] Sending DTMF '{_decision.digit}' to navigate IVR")
                                try:
                                    if len(_decision.digit) == 1:
                                        asyncio.create_task(
                                            _dtmf.send_digit(websocket, _stream_sid, _decision.digit, context=f"ivr_nav_{_ivr_nav.attempts}", call_sid=_call_sid_dtmf)
                                        )
                                    else:
                                        asyncio.create_task(
                                            _dtmf.send_sequence(websocket, _stream_sid, _decision.digit, context=f"ivr_nav_seq_{_ivr_nav.attempts}", call_sid=_call_sid_dtmf)
                                        )
                                except Exception as _dtmf_err:
                                    logger.error(f"[EAB+IVR] DTMF send failed: {_dtmf_err}")

                            elif _decision.action == IVRAction.SPEAK and _decision.speech:
                                # Navigator wants to speak (e.g., "representative" as escape)
                                logger.info(f"[EAB+IVR] Speaking to IVR: '{_decision.speech[:60]}'")
                                try:
                                    asyncio.create_task(
                                        self.synthesize_and_stream_greeting(
                                            websocket, _decision.speech, _stream_sid
                                        )
                                    )
                                except Exception as _speak_err:
                                    logger.debug(f"[EAB+IVR] IVR speak failed: {_speak_err}")

                            elif _decision.action == IVRAction.HANDOFF:
                                # Human detected during IVR navigation — transition to live conversation
                                logger.info(f"[EAB+IVR] HUMAN DETECTED during IVR nav — handing off to live conversation")
                                context['_ivr_nav_active'] = False
                                context['_eab_human_reached_via_ivr'] = True
                                # Fall through to normal cognition pipeline — don't return
                                # The current transcript is the human's greeting, process it normally
                                pass  # intentional fall-through

                            elif _decision.action == IVRAction.ABORT:
                                # Navigator gave up — too many loops or escape attempts exhausted
                                logger.info(f"[EAB+IVR] IVR navigation ABORTED after {_ivr_nav.attempts} attempts: {_decision.reason}")
                                context['_ivr_nav_active'] = False
                                context['_evolution_outcome'] = 'ivr_nav_abort'
                                _fsm = context.get('_call_fsm')
                                if _fsm:
                                    _fsm.end_call(reason='ivr_nav_abort')
                                else:
                                    context['stream_ended'] = True
                                context['_ccnm_ignore'] = True
                                return

                            elif _decision.action == IVRAction.WAIT:
                                # Navigator is listening for next menu — do nothing, wait for more audio
                                logger.info(f"[EAB+IVR] Waiting for IVR menu audio...")

                            # Unless we fell through to handoff, suppress cognition
                            if _decision.action != IVRAction.HANDOFF:
                                context['_ccnm_ignore'] = True
                                return
                        else:
                            # Organs not wired — fall back to old template behavior
                            _template_text = EnvironmentBehaviorTemplates.get_template(
                                _eab_result.env_class, _merchant_name, cycle=0
                            )
                            if _template_text and websocket:
                                logger.info(f"[EAB] IVR NAVIGATION (legacy): '{_template_text[:80]}'")
                                try:
                                    asyncio.create_task(
                                        self.synthesize_and_stream_greeting(
                                            websocket, _template_text, context.get('streamSid')
                                        )
                                    )
                                except Exception as _eab_err:
                                    logger.debug(f"[EAB] IVR nav TTS failed: {_eab_err}")
                            context['_ccnm_ignore'] = True
                            return

                    # ---- DROP_AND_ABORT (voicemail) ----
                    elif _eab_result.action == EnvironmentAction.DROP_AND_ABORT:
                        _template_text = EnvironmentBehaviorTemplates.get_template(
                            _eab_result.env_class, _merchant_name
                        )
                        if _template_text and websocket:
                            logger.info(f"[EAB] VOICEMAIL DROP: '{_template_text}'")
                            try:
                                asyncio.create_task(
                                    self.synthesize_and_stream_greeting(
                                        websocket, _template_text, context.get('streamSid')
                                    )
                                )
                            except Exception as _eab_err:
                                logger.debug(f"[EAB] Voicemail drop TTS failed: {_eab_err}")
                        # Set outcome and abort
                        context['_evolution_outcome'] = 'voicemail_eab'
                        context['_evolution_confidence'] = _eab_result.confidence
                        context['_evolution_band'] = 'high'
                        context['_evolution_engagement'] = 0.0
                        context['_ccnm_ignore'] = True
                        _fsm = context.get('_call_fsm')
                        if _fsm:
                            _fsm.end_call(reason='voicemail_eab')
                        else:
                            context['stream_ended'] = True
                        logger.info(f"[EAB] Voicemail abort. class={_eab_result.env_class.name}")
                        return

                    # ---- DECLINE_AND_ABORT (answering service) ----
                    elif _eab_result.action == EnvironmentAction.DECLINE_AND_ABORT:
                        _template_text = EnvironmentBehaviorTemplates.get_template(
                            _eab_result.env_class, _merchant_name
                        )
                        if _template_text and websocket:
                            logger.info(f"[EAB] ANSWERING SERVICE DECLINE: '{_template_text}'")
                            try:
                                asyncio.create_task(
                                    self.synthesize_and_stream_greeting(
                                        websocket, _template_text, context.get('streamSid')
                                    )
                                )
                            except Exception as _eab_err:
                                logger.debug(f"[EAB] Answering service TTS failed: {_eab_err}")
                        context['_evolution_outcome'] = 'answering_service_eab'
                        context['_evolution_confidence'] = _eab_result.confidence
                        context['_evolution_band'] = 'medium'
                        context['_evolution_engagement'] = 0.0
                        context['_ccnm_ignore'] = True
                        _fsm = context.get('_call_fsm')
                        if _fsm:
                            _fsm.end_call(reason='answering_service_eab')
                        else:
                            context['stream_ended'] = True
                        logger.info(f"[EAB] Answering service abort. class={_eab_result.env_class.name}")
                        return

                # --- CONTINUOUS VM/IVR RE-EVALUATION for FALLBACK/CONTINUE_MISSION ---
                # [FIX 2026-02-24] When EAB initially classified as UNKNOWN→FALLBACK
                # or HUMAN→CONTINUE_MISSION, garbled first utterances cause VMs to be
                # misclassified. Re-check each subsequent merchant turn for VM/IVR evidence.
                # If a clear VM/IVR pattern appears on turn 2+, abort immediately.
                elif _eab_action in (EnvironmentAction.CONTINUE_MISSION, EnvironmentAction.FALLBACK):
                    _recheck = _eab.classify(text)
                    if _recheck.action == EnvironmentAction.DROP_AND_ABORT:
                        # VM detected on subsequent turn — abort
                        _merchant_name = context.get('prospect_info', {}).get('company', '')
                        _template_text = EnvironmentBehaviorTemplates.get_template(
                            _recheck.env_class, _merchant_name
                        )
                        if _template_text and websocket:
                            logger.info(f"[EAB-RECHECK] VOICEMAIL DETECTED on subsequent turn: '{_template_text}'")
                            try:
                                asyncio.create_task(
                                    self.synthesize_and_stream_greeting(
                                        websocket, _template_text, context.get('streamSid')
                                    )
                                )
                            except Exception as _eab_err:
                                logger.debug(f"[EAB-RECHECK] VM drop TTS failed: {_eab_err}")
                        context['_evolution_outcome'] = 'voicemail_eab'
                        context['_evolution_confidence'] = _recheck.confidence
                        context['_evolution_band'] = 'high'
                        context['_evolution_engagement'] = 0.0
                        context['_ccnm_ignore'] = True
                        _fsm = context.get('_call_fsm')
                        if _fsm:
                            _fsm.end_call(reason='voicemail_eab_recheck')
                        else:
                            context['stream_ended'] = True
                        logger.info(f"[EAB-RECHECK] VM abort on subsequent turn. class={_recheck.env_class.name}")
                        if CALL_CAPTURE_WIRED:
                            _cdc_environment(
                                context.get('call_sid', ''),
                                env_class=_recheck.env_class.name,
                                env_confidence=_recheck.confidence,
                                behavior='DROP_AND_ABORT',
                                outcome='voicemail_eab_recheck',
                                utterance=text[:200],
                                cycles=context.get('_eab_cycle', 0) + 1,
                            )
                        return
                    elif _recheck.action == EnvironmentAction.DECLINE_AND_ABORT:
                        # Answering service detected on subsequent turn — abort
                        _merchant_name = context.get('prospect_info', {}).get('company', '')
                        _template_text = EnvironmentBehaviorTemplates.get_template(
                            _recheck.env_class, _merchant_name
                        )
                        if _template_text and websocket:
                            try:
                                asyncio.create_task(
                                    self.synthesize_and_stream_greeting(
                                        websocket, _template_text, context.get('streamSid')
                                    )
                                )
                            except Exception:
                                pass
                        context['_evolution_outcome'] = 'answering_service_eab'
                        context['_evolution_confidence'] = _recheck.confidence
                        context['_evolution_band'] = 'medium'
                        context['_evolution_engagement'] = 0.0
                        context['_ccnm_ignore'] = True
                        _fsm = context.get('_call_fsm')
                        if _fsm:
                            _fsm.end_call(reason='answering_service_eab_recheck')
                        else:
                            context['stream_ended'] = True
                        logger.info(f"[EAB-RECHECK] Answering service abort on subsequent turn")
                        return
                    elif _recheck.action in (EnvironmentAction.NAVIGATE, EnvironmentAction.PASS_THROUGH):
                        # IVR/screener detected — switch mode so IVR loop guard takes over
                        logger.info(f"[EAB-RECHECK] Environment switch: {_eab_action.name} → {_recheck.action.name} "
                                    f"(class={_recheck.env_class.name}, conf={_recheck.confidence:.2f})")
                        context['_eab_action'] = _recheck.action
                        context['_eab_env_class'] = _recheck.env_class.name
                        context['_eab_cycle'] = 1
                        context['_ccnm_ignore'] = True
                        _merchant_name = context.get('prospect_info', {}).get('company', '')
                        _template_text = EnvironmentBehaviorTemplates.get_template(
                            _recheck.env_class, _merchant_name, cycle=0
                        )
                        if _template_text and websocket:
                            try:
                                asyncio.create_task(
                                    self.synthesize_and_stream_greeting(
                                        websocket, _template_text, context.get('streamSid')
                                    )
                                )
                            except Exception:
                                pass
                        if CALL_CAPTURE_WIRED:
                            _cdc_environment(
                                context.get('call_sid', ''),
                                env_class=_recheck.env_class.name,
                                env_confidence=_recheck.confidence,
                                behavior=_recheck.action.name,
                                outcome='eab_recheck_switch',
                                utterance=text[:200],
                                cycles=1,
                            )
                        return
                    # else: still looks like human/unknown — fall through to normal pipeline

                # --- SUBSEQUENT UTTERANCES in screener/IVR mode ---
                elif _eab_action in (EnvironmentAction.PASS_THROUGH, EnvironmentAction.NAVIGATE):
                    _cycle = context.get('_eab_cycle', 0) + 1
                    context['_eab_cycle'] = _cycle
                    _eab_env = context.get('_eab_env_class', 'UNKNOWN')

                    # Re-classify to check if environment changed (e.g., human picked up)
                    _reclass = _eab.reclassify(text)

                    # If reclassified as HUMAN → environment changed, continue mission!
                    if _reclass.env_class == EnvironmentClass.HUMAN:
                        logger.info(f"[EAB] ENVIRONMENT CHANGED: {_eab_env} → HUMAN — resuming normal pipeline!")
                        context['_eab_action'] = EnvironmentAction.CONTINUE_MISSION
                        context['_eab_env_class'] = 'HUMAN'
                        context['_ccnm_ignore'] = False
                        # Fall through to normal pipeline

                    # Loop guard: exceeded max cycles for this environment
                    elif _eab.should_abort_loop():
                        _merchant_name = context.get('prospect_info', {}).get('company', '')
                        _exit_line = "No worries, I'll try again later. Take care."
                        if websocket:
                            try:
                                asyncio.create_task(
                                    self.synthesize_and_stream_greeting(
                                        websocket, _exit_line, context.get('streamSid')
                                    )
                                )
                            except Exception:
                                pass
                        context['_evolution_outcome'] = f'{_eab_env.lower()}_loop_abort'
                        context['_evolution_confidence'] = _reclass.confidence
                        context['_evolution_band'] = 'medium'
                        context['_evolution_engagement'] = 0.0
                        context['_ccnm_ignore'] = True
                        _fsm = context.get('_call_fsm')
                        if _fsm:
                            _fsm.end_call(reason=f'{_eab_env.lower()}_loop_abort')
                        else:
                            context['stream_ended'] = True
                        logger.info(f"[EAB] LOOP ABORT: {_eab_env} after {_cycle} cycles")
                        return

                    # Same environment, still under loop limit → use IVR Navigator or speak next cycle template
                    else:
                        _merchant_name = context.get('prospect_info', {}).get('company', '')
                        _env_class_enum = EnvironmentClass[_eab_env] if _eab_env in EnvironmentClass.__members__ else EnvironmentClass.UNKNOWN

                        # [ORGAN 37+36] If IVR navigation is active, route through Navigator
                        _ivr_nav = context.get('_ivr_navigator') if IVR_NAVIGATOR_WIRED else None
                        _dtmf = context.get('_dtmf_reflex') if DTMF_REFLEX_WIRED else None
                        _stream_sid = context.get('streamSid')

                        if context.get('_ivr_nav_active') and _ivr_nav and _dtmf and websocket and _stream_sid:
                            _call_sid_dtmf2 = context.get('call_sid', '')
                            _decision = _ivr_nav.process_utterance(transcript_text)
                            logger.info(f"[EAB+IVR] Re-eval cycle {_cycle}: action={_decision.action.name}, digit={_decision.digit}, state={_ivr_nav.state.name}")

                            if _decision.action == IVRAction.SEND_DTMF and _decision.digit:
                                try:
                                    if len(_decision.digit) == 1:
                                        asyncio.create_task(
                                            _dtmf.send_digit(websocket, _stream_sid, _decision.digit, context=f"ivr_cycle_{_cycle}", call_sid=_call_sid_dtmf2)
                                        )
                                    else:
                                        asyncio.create_task(
                                            _dtmf.send_sequence(websocket, _stream_sid, _decision.digit, context=f"ivr_cycle_seq_{_cycle}", call_sid=_call_sid_dtmf2)
                                        )
                                except Exception as _dtmf_err:
                                    logger.error(f"[EAB+IVR] DTMF send failed on cycle {_cycle}: {_dtmf_err}")

                            elif _decision.action == IVRAction.SPEAK and _decision.speech:
                                try:
                                    asyncio.create_task(
                                        self.synthesize_and_stream_greeting(
                                            websocket, _decision.speech, _stream_sid
                                        )
                                    )
                                except Exception:
                                    pass

                            elif _decision.action == IVRAction.HANDOFF:
                                logger.info(f"[EAB+IVR] HUMAN DETECTED on cycle {_cycle} — handing off to live conversation")
                                context['_ivr_nav_active'] = False
                                context['_eab_human_reached_via_ivr'] = True
                                # Fall through to normal cognition — don't return
                                pass

                            elif _decision.action == IVRAction.ABORT:
                                logger.info(f"[EAB+IVR] IVR ABORT on cycle {_cycle}: {_decision.reason}")
                                context['_ivr_nav_active'] = False
                                context['_evolution_outcome'] = 'ivr_nav_abort'
                                _fsm = context.get('_call_fsm')
                                if _fsm:
                                    _fsm.end_call(reason='ivr_nav_abort')
                                else:
                                    context['stream_ended'] = True
                                context['_ccnm_ignore'] = True
                                return

                            if _decision.action != IVRAction.HANDOFF:
                                return
                        else:
                            # Non-IVR environment or organs not wired — use template
                            _template_text = EnvironmentBehaviorTemplates.get_template(
                                _env_class_enum, _merchant_name, cycle=_cycle
                            )
                            if _template_text and websocket:
                                logger.info(f"[EAB] PASS-THROUGH CYCLE {_cycle}: '{_template_text[:80]}'")
                                try:
                                    asyncio.create_task(
                                        self.synthesize_and_stream_greeting(
                                            websocket, _template_text, context.get('streamSid')
                                        )
                                    )
                                except Exception:
                                    pass
                            return

        # ================================================================
        # [IVR DETECTOR] Check if this is an IVR/voicemail system
        # ================================================================
        # FALLBACK layer — runs AFTER EAB. If EAB classified as HUMAN but
        # the IVR detector accumulates evidence over multiple turns, it can
        # still abort. EAB handles first-utterance routing; IVR detector
        # handles slow-reveal IVR systems that take multiple turns to identify.
        # ================================================================
        if IVR_DETECTOR_WIRED:
            _ivr = context.get('_ivr_detector')
            if _ivr:
                import time as _ivr_time
                ivr_result = _ivr.add_utterance(text, _ivr_time.time())
                if ivr_result.get('should_abort'):
                    logger.warning(f"[IVR] ABORT TRIGGERED — score={ivr_result['score']}, reason={ivr_result['reason']}")
                    # Store IVR outcome in context for call_end recording
                    context['_evolution_outcome'] = _ivr.get_outcome_label()
                    context['_evolution_confidence'] = ivr_result['score']
                    context['_evolution_band'] = 'high'
                    context['_evolution_engagement'] = 0.0
                    # [CCNM QUARANTINE] Mark this call as non-learning
                    context['_ccnm_ignore'] = True
                    _ivr.ccnm_ignore = True
                    # Speak graceful exit and hang up
                    abort_line = _ivr.get_abort_line()
                    if abort_line and websocket:
                        try:
                            asyncio.create_task(
                                self.synthesize_and_stream_greeting(websocket, abort_line, context.get('streamSid'))
                            )
                        except Exception as _abort_err:
                            logger.debug(f"[CONV INTEL] Abort greeting synthesis failed: {_abort_err}")
                    # [PHASE 2] FSM: → ENDED (ivr_abort)
                    _fsm = context.get('_call_fsm')
                    if _fsm:
                        _fsm.end_call(reason='ivr_abort')
                    else:
                        context['stream_ended'] = True
                    logger.info(f"[IVR] Call aborted. Outcome: {context['_evolution_outcome']}. CCNM quarantined.")
                    return
                elif ivr_result.get('is_ivr'):
                    # Detected but not yet at abort threshold — set quarantine flag proactively
                    context['_ccnm_ignore'] = True
                    _ivr.ccnm_ignore = True
                    logger.warning(f"[IVR] DETECTED (score={ivr_result['score']}) — CCNM quarantined, monitoring for abort")

                    # ================================================================
                    # [FIX R5b 2026-02-20] CONTINUOUS IVR GUARD (IVR-after-HUMAN fix)
                    # ================================================================
                    # If EAB initially classified as HUMAN but the IVR detector now
                    # sees IVR evidence, switch EAB mode to NAVIGATE so Alan speaks
                    # IVR templates instead of conversation responses. This fixes the
                    # HVAC/Heating & Cooling bug where Alan had a 5-turn "conversation"
                    # with a voicemail system.
                    # ================================================================
                    _eab_action_current = context.get('_eab_action')
                    if _eab_action_current == EnvironmentAction.CONTINUE_MISSION:
                        logger.warning(f"[IVR-GUARD] Mid-call IVR detected after HUMAN classification! "
                                      f"Switching CONTINUE_MISSION → NAVIGATE (score={ivr_result['score']})")
                        context['_eab_action'] = EnvironmentAction.NAVIGATE
                        context['_eab_env_class'] = 'BUSINESS_IVR'
                        context['_eab_cycle'] = 0
                        context['continuous_ivr_guard_triggered'] = True

                        # Speak IVR navigation template instead of running cognition
                        _merchant_name = context.get('prospect_info', {}).get('company', '')
                        _nav_text = EnvironmentBehaviorTemplates.get_template(
                            EnvironmentClass.BUSINESS_IVR, _merchant_name, cycle=0
                        )
                        if _nav_text and websocket:
                            logger.info(f"[IVR-GUARD] Speaking IVR nav: '{_nav_text[:80]}'")
                            try:
                                asyncio.create_task(
                                    self.synthesize_and_stream_greeting(
                                        websocket, _nav_text, context.get('streamSid')
                                    )
                                )
                            except Exception as _nav_err:
                                logger.debug(f"[IVR-GUARD] Nav TTS failed: {_nav_err}")
                        # Record environment event in CDC
                        if CALL_CAPTURE_WIRED:
                            _cdc_environment(
                                context.get('call_sid', ''),
                                env_class='BUSINESS_IVR',
                                env_confidence=ivr_result['score'],
                                behavior='NAVIGATE',
                                outcome='ivr_guard_switch',
                                utterance=text[:200],
                                cycles=context.get('_eab_cycle', 0),
                            )
                        return

# [POST-GREETING FILTER] After the greeting plays, the first STT often picks
        # up noise, echo, or a bare acknowledgment like "Okay" / "Hi". These are NOT
        # real requests — the greeting already asked "how may I help you?" Dropping them
        # prevents Alan from saying "Got it, what can I help you with?" immediately.
        POST_GREETING_ACKS = {"okay", "ok", "hi", "hello", "hey", "yeah", "yep",
                              "yes", "uh-huh", "mm-hmm", "sure", "alright",
                              "got it", "right", "good", "go ahead", "hmm",
                              "all right", "oh", "ah", "hm", "huh"}
        text_check = text.lower().strip().rstrip('.!?,')  
        if not context.get('first_turn_complete') and text_check in POST_GREETING_ACKS:
            logger.info(f"[POST-GREETING] Dropped bare acknowledgment '{text}' — waiting for real request")
            return

        # [BACK-CHANNEL FILTER] Short acknowledgments ("Okay", "Yeah", "Mm-hmm") 
        # during an active response are NOT interrupts — they're signals the listener
        # is engaged. A real human would keep talking, not restart their thought.
        BACK_CHANNELS = {"okay", "ok", "yeah", "yep", "yes", "uh-huh", "uh huh", 
                         "mm-hmm", "mm hmm", "mmm", "sure", "right", "got it",
                         "alright", "all right", "go ahead", "i see", "mhm",
                         "oh", "ah", "hm", "hmm", "huh", "thank you", "thanks"}
        existing_task = context.get('response_task')
        if text_check in BACK_CHANNELS and existing_task and not existing_task.done():
            logger.info(f"[BACK-CHANNEL] Ignored acknowledgment '{text}' during active response (gen {context.get('response_generation')})")
            return
        
        # ================================================================
        # [VAD GUARD] Don't fire pipeline while user is still speaking
        # ================================================================
        # Problem: VAD commits at 0.42s silence (caller paused between list items).
        # Whisper takes ~1s. By the time STT arrives, caller resumed speaking.
        # Without this check, Alan starts talking OVER the caller mid-thought.
        #
        # Fix: If vad_state == 'speaking' when STT arrives, the caller resumed.
        # Store this text as pending and let the next VAD commit cycle pick it up.
        # The next finalize_and_clear() will produce new STT, and the accumulator
        # will concatenate pending + new text into one complete thought.
        # ================================================================
        if context.get('vad_state') == 'speaking':
            prev_pending = context.get('pending_stt_text', '')
            combined = (prev_pending + ' ' + text).strip() if prev_pending else text
            context['pending_stt_text'] = combined
            logger.info(f"[VAD GUARD] User still speaking. Holding STT: '{combined[:80]}'")
            return
        
        # ================================================================
        # [ACCUMULATOR] STT Text Accumulation — Wait for complete thoughts
        # ================================================================
        # Problem: Callers pause between phrases. VAD commits each fragment
        # as a separate turn, and each fragment supersedes the previous pipeline.
        # The caller says "I'm calling about a merchant service... for my new business"
        # but we hear 3 fragments and respond to the last one only.
        #
        # Fix: If the PREVIOUS pipeline hasn't produced first audio yet (still
        # processing LLM/TTS), ACCUMULATE the new text onto it instead of
        # superseding. If Alan IS already speaking, new text is a real interrupt.
        # ================================================================
        has_first_audio = context.get('first_audio_produced', False)
        
        if existing_task and not existing_task.done() and not has_first_audio:
            # Pipeline is still thinking (LLM/TTS haven't produced audio yet)
            pipeline_age = time.time() - context.get('_pipeline_start', time.time())
            
            if pipeline_age > 1.5:
                # [LATENCY SHIELD] Pipeline has been processing >1.5s — LLM is likely
                # generating tokens. Don't restart — let the current response complete.
                # This prevents the "death spiral" where impatient re-tries
                # ("Hello? Can you hear me?") keep restarting the pipeline,
                # causing Alan to NEVER respond.
                logger.info(f"[LATENCY SHIELD] Pipeline running {pipeline_age:.1f}s — protecting current response. New text: '{text[:60]}'")
                # Store the new text so it can be addressed in the NEXT turn if needed
                context['_deferred_text'] = text
                return
            
            # ACCUMULATE: append this fragment to the pending text
            prev_accumulated = context.get('accumulated_stt_text', '')
            accumulated = (prev_accumulated + ' ' + text).strip() if prev_accumulated else text
            context['accumulated_stt_text'] = accumulated
            logger.info(f"[ACCUMULATE] Appending fragment. Now: '{accumulated[:80]}'")
            
            # Cancel the old pipeline and start a new one with the FULL accumulated text
            context['response_generation'] = context.get('response_generation', 0) + 1
            my_generation = context['response_generation']
            context['_pipeline_start'] = time.time()  # Reset pipeline clock for new attempt
            # Don't send CLEAR to Twilio — nothing is playing yet
            
            try:
                task = asyncio.create_task(
                    self.handle_user_speech({'text': accumulated}, context, websocket, generation=my_generation)
                )
                context['response_task'] = task
                def _on_done(t):
                    if t.exception():
                        logger.error(f"handle_user_speech FAILED: {t.exception()}")
                task.add_done_callback(_on_done)
            except Exception as e:
                logger.error(f"[STT] Failed to create task: {e}")
            return
        
        # FRESH TURN: No pipeline running, or Alan is already speaking (real interrupt)
        context['accumulated_stt_text'] = text  # Start fresh accumulation
        context['first_audio_produced'] = False  # Reset for new turn
        context['_pipeline_start'] = time.time()  # [LATENCY SHIELD] Track when pipeline starts
        
        # CANCEL-AND-REPLACE: Increment generation. Any in-progress response
        # will see the mismatch and stop gracefully — like a human stopping
        # mid-sentence because they heard something new.
        context['response_generation'] = context.get('response_generation', 0) + 1
        my_generation = context['response_generation']
        
        if existing_task and not existing_task.done():
            logger.info(f"[INTERRUPT] New speech supersedes in-progress response -> gen {my_generation}")
            # Tell Twilio to stop playing current audio
            asyncio.create_task(self._safe_send(websocket, 
                {"event": "clear", "streamSid": context.get('streamSid')}))
            context['audio_playing'] = False
            context['twilio_playback_done'] = True  # Reset echo gate since we cleared Twilio's buffer
        
        try:
            task = asyncio.create_task(
                self.handle_user_speech({'text': text}, context, websocket, generation=my_generation)
            )
            context['response_task'] = task
            def _on_done(t):
                if t.exception():
                    logger.error(f"handle_user_speech FAILED: {t.exception()}")
            task.add_done_callback(_on_done)
        except Exception as e:
            logger.error(f"[STT] Failed to create task: {e}")

    def _pcm24k_to_mulaw8k(self, pcm_data: bytes) -> bytes:
        """Convert OpenAI TTS PCM (24kHz 16-bit mono LE) to mulaw 8kHz for Twilio."""
        # Downsample from 24000 → 8000 Hz
        converted, _ = audioop.ratecv(pcm_data, 2, 1, 24000, 8000, None)
        # Convert 16-bit linear PCM to 8-bit mu-law
        return audioop.lin2ulaw(converted, 2)

    def _openai_tts_sync(self, text: str, prosody_intent: str = "neutral", sentence_idx: int = 0,
                         speed_bias: float = 1.0, breath_prob_bias: float = 0.0) -> bytes:
        """Sync OpenAI TTS request. Returns mulaw 8kHz bytes for Twilio.
        
        Args:
            text: The text to synthesize.
            prosody_intent: Prosody intent key from detect_prosody_intent().
                Controls voice instructions (emotion/tone) and synthesis speed.
            sentence_idx: 0-based sentence index in the turn (for breath injection).
            speed_bias: Multiplicative speed bias from Organ 11 signature (1.0 = neutral).
            breath_prob_bias: Additive breath probability bias from Organ 11 signature (0.0 = neutral).
        """
        if not self.tts_client:
            return b""
        try:
            # [ORGAN 8+9] Clause segmentation → mid-sentence prosody arc
            # Instead of one flat instruction, analyze the sentence structure
            # and build a narrated delivery contour for multi-clause sentences.
            clauses = segment_into_clauses(text, prosody_intent)
            if len(clauses) > 1:
                tts_instructions = build_clause_arc_instructions(clauses, prosody_intent)
                logger.info(f"[CLAUSE ARC] {len(clauses)} clauses → arc instruction for: '{text[:50]}'")
            else:
                tts_instructions = PROSODY_INSTRUCTIONS.get(prosody_intent, PROSODY_INSTRUCTIONS["neutral"])
            
            tts_speed = PROSODY_SPEED.get(prosody_intent, TIMING.tts_default_speed)  # [TIMING CONFIG]
            # [ORGAN 11] Apply signature speed bias — learned from human interaction
            if speed_bias != 1.0:
                tts_speed = round(tts_speed * speed_bias, 2)
            
            tts_start = time.time()
            response = self.tts_client.audio.speech.create(
                model=self._tts_model,
                voice=self._tts_voice,
                input=text,
                instructions=tts_instructions,
                response_format="pcm",  # Raw 24kHz 16-bit mono PCM
                speed=tts_speed
            )
            pcm_data = response.content
            mulaw_data = self._pcm24k_to_mulaw8k(pcm_data)
            
            # [ORGAN 10] Breath injection — splice in breath sample before audio
            # This happens BEFORE tempo compression so the breath timing is natural
            mulaw_data = inject_breath_before_audio(mulaw_data, prosody_intent, sentence_idx,
                                                    breath_prob_bias=breath_prob_bias)
            
            # [ORGAN 11] Acoustic signature — Alan's deterministic identity fingerprint
            # Micro-pause before advice, characteristic inhale on transitions,
            # clarification cadence, thought-reset contour. Always consistent.
            mulaw_data = apply_alan_signature(mulaw_data, prosody_intent, sentence_idx)
            
            # [TEMPO AMPLIFIER] Compress audio for faster playback
            mulaw_data = tempo_compress_audio(mulaw_data)
            
            tts_ms = 1000 * (time.time() - tts_start)
            logger.info(f"[TTS-OPENAI] Synthesized in {tts_ms:.0f}ms (intent={prosody_intent}, speed={tts_speed}): '{text[:40]}...' ({len(mulaw_data)} bytes)")
            return mulaw_data
        except Exception as e:
            logger.error(f"[TTS-OPENAI] Error: {e}")
            return b""

    async def synthesize_greeting_to_mulaw_bytes(self, text: str) -> bytes:
        """
        THE MOUTH: Converts text to Mu-Law 8k Audio formatted for Twilio.
        Uses OpenAI TTS via ThreadPoolExecutor.
        """
        if not self.tts_client:
             logger.error("[TTS] No TTS client. Cannot speak.")
             return b""

        try:
            logger.info(f"[TTS] Synthesizing via OpenAI: '{text[:30]}...'")
            start_time = time.time()
            
            # Offload blocking request to thread
            loop = asyncio.get_running_loop()
            raw_bytes = await loop.run_in_executor(
                self.executor, 
                self._openai_tts_sync, 
                text
            )
            
            if raw_bytes:
                # [NEG PROOF] Bytes are now already Mulaw 8kHz.
                # No resampling needed.
                logger.info(f"[TTS WEDGE] Synthesis Complete. {len(raw_bytes)} bytes (Mulaw 8k). Latency: {1000*(time.time()-start_time):.0f}ms")
                return raw_bytes
            else:
                logger.error(f"[TTS WEDGE] Synthesis returned empty bytes. Likely API Error.")
                return b""
            
        except Exception as e:
            logger.error(f"[TTS WEDGE] Synthesis Failure: {e}")
            return b""


    async def stream_audio_response(self, websocket, audio_bytes: bytes, stream_sid: str = None):
        """
        Streaming the audio bytes (Mulaw 8k) to Control API.
        [NEG PROOF] Perfect 160-byte frame alignment for Twilio. No transcoding.
        """
        # [ENCODER UNIFICATION] Force all audio through exact same Python audioop pipeline
        # This scrubs "static bursts" caused by varying μ-law signatures (OpenAI TTS vs Local)
        try:
             # 1. Decode generic Mulaw to PCM16
             pcm16 = audioop.ulaw2lin(audio_bytes, 2)
             # 2. Re-encode to Mulaw (The "Great Unifier")
             audio_bytes = audioop.lin2ulaw(pcm16, 2) 
        except Exception as _mulaw_err:
             logger.debug(f"[AUDIO] Mulaw re-encode failed (using original bytes): {_mulaw_err}") 

        chunk_size = 160 # 20ms at 8000Hz (1 byte per sample for Mulaw)
        
        # Calculate padding needed to reach 160-byte boundary
        remainder = len(audio_bytes) % chunk_size
        if remainder > 0:
            padding_len = chunk_size - remainder
            # 0xFF is silence in Mulaw (roughly), 0x7F is positive zero. 
            # We use 0xFF for safe silence padding.
            audio_bytes += b'\xFF' * padding_len
            logger.info(f"[TTS WEDGE] Padded audio with {padding_len} bytes to align frames.")
        
        frame_count = 0
        for i in range(0, len(audio_bytes), chunk_size):
            chunk = audio_bytes[i:i+chunk_size]
            
            # Sanity Check
            if len(chunk) != chunk_size:
                chunk += b'\xFF' * (chunk_size - len(chunk))

            # [NEG PROOF] DIRECT PASS-THROUGH
            # Audio is already Mulaw. We just encode to Base64.
            b64_data = base64.b64encode(chunk).decode("utf-8")

            if stream_sid:
                # Direct to Twilio
                payload = {
                    "event": "media",
                    "streamSid": stream_sid,
                    "media": {
                        "payload": b64_data
                    }
                }
            else:
                # Protocol: control_api.py expects 'audio_chunk' + 'data' (base64)
                # It will wrap this in {"event": "media", ...} for Twilio
                payload = {
                    "type": "audio_chunk",
                    "data": b64_data
                }

            try:
                if hasattr(websocket, 'send_text'):
                     await websocket.send_text(json.dumps(payload))
                else:
                     await websocket.send(json.dumps(payload))
            except Exception as e:
                logger.error(f"[TTS WEDGE] Stream Send Error: {e}")
            frame_count += 1
            
            # [VERSION R+ NEG-PROOF] ADAPTIVE FRAME PACING
            # Matches orchestrated pipeline pacing — gentle ramp then cruise
            if frame_count < 15:
                await asyncio.sleep(0.005)  # Gentle warm-up
            elif frame_count < 40:
                await asyncio.sleep(0.003)  # Ramp up
            else:
                await asyncio.sleep(0.012)  # Real-time cruise
            
        logger.info(f"[TTS WEDGE] Streamed {frame_count} frames to bridge (Mulaw).")

        # Send MARK event to signal end of turn
        if stream_sid:
            mark_payload = {
                "event": "mark",
                "streamSid": stream_sid,
                "mark": {"name": "turn_complete"}
            }
            try:
                # [FIX - Websockets Lib vs Starlette]
                # The 'websockets' library server implementation uses .send(), not .send_text()
                # We inspect the object to decide
                if hasattr(websocket, 'send_text'):
                    await websocket.send_text(json.dumps(mark_payload))
                else:
                    await websocket.send(json.dumps(mark_payload))
                logger.info("[TTS WEDGE] Sent MARK event (Direct)")
            except Exception as e:
                # Fallback purely for safety if inspection fails
                try: 
                     await websocket.send(json.dumps(mark_payload))
                     logger.info("[TTS WEDGE] Sent MARK event (Fallback)")
                except:
                     logger.error(f"[TTS WEDGE] Failed to send MARK: {e}")
        else:
            # Relay Protocol Mark
            mark_payload = {
                "type": "mark", 
                "name": "turn_complete"
            }
            try:
                if hasattr(websocket, 'send_text'):
                    await websocket.send_text(json.dumps(mark_payload))
                else:
                    await websocket.send(json.dumps(mark_payload))
                logger.info("[TTS WEDGE] Sent MARK event (Relay)")
            except Exception as e:
                logger.error(f"[TTS WEDGE] Failed to send MARK: {e}")

    async def _safe_send(self, websocket, data):
        """Helper to send JSON safely to either FastAPI or websockets lib"""
        try:
            if isinstance(data, dict):
                json_str = json.dumps(data)
            else:
                json_str = data
                
            if hasattr(websocket, 'send_text'):
                await websocket.send_text(json_str)
            else:
                await websocket.send(json_str)
        except Exception as e:
            logger.error(f"Send failed: {e}")

    async def handle_conversation(self, websocket):
        """
        Handle a ConversationRelay websocket connection
        """
        supervisor = AlanSupervisor.get_instance()
        client_id = id(websocket)
        logger.info(f"New conversation connection: {client_id}")

        # Reset EOS so each call starts clean (prevents permanent shutdown across calls)
        self.eos.reset()

        # Instantiate a fresh Agent for this conversation to ensure clean state
        try:
             # [FIX] Use Pre-Warmed Agent or Fallback
             if self.shared_agent_instance:
                 alan_ai = self.shared_agent_instance
                 logger.info(f"[ALAN AI] Using PRE-WARMED Agent for client {client_id}")
             else:
                 alan_ai = AgentAlanBusinessAI() # Slow Fallback
                 logger.info(f"[ALAN AI] Cold-Booting Agent for client {client_id}")

            # Refinement 1: Palate Cleanser
             if hasattr(alan_ai, 'clear_context'):
                alan_ai.clear_context()
             logger.info(f"[ALAN AI] AgentAlanBusinessAI initialized for client {client_id} (Context Purged)")
             # [ORGAN] Hook 3 — Agent Wired (deferred until conversation_context exists)
        except Exception as e:
            logger.error(f"[ALAN AI] Initialization failed: {e}. Falling back to minimal stub.")
            if CALL_MONITOR_WIRED:
                monitor_call_error(str(client_id), 'AGENT_INIT_FAIL', str(e))
            if supervisor:
                supervisor.business_logic_issue(
                    issue="Agent initialization failed",
                    reason=str(e),
                    fix="Check AgentAlanBusinessAI dependencies and models"
                )
             # Minimal fallback stub
            class AlanAIStub:
                def lookup_rse_lead(self, company_name): return {}
                def generate_business_greeting(self, **kwargs): return "Hi, this is Alan."
                def analyze_business_response(self, text): return {"sentiment": "neutral", "interest_level": 0}
                async def generate_business_response(self, analysis, context): return "Thanks for sharing that."
            alan_ai = AlanAIStub()

        try:
            # Initialize conversation context
            conversation_context = {
                'client_id': client_id,
                'start_time': datetime.now(),
                'messages': [],
                'prospect_info': {},
                'conversation_state': 'greeting',
                'agent_instance': alan_ai, # Store agent in context
                'last_speech_time': 0, # For Dynamic Breath (VAD)
                'greeting_sent': False
            }

            # [PHASE 2] Initialize deterministic call lifecycle FSM
            # Replaces scattered boolean flags with a single state machine.
            # _sync_context() maintains backward-compatible flag values.
            _call_fsm = CallSessionFSM(conversation_context)
            conversation_context['_call_fsm'] = _call_fsm
            logger.info(f'[CALL FSM] Initialized: {_call_fsm}')

            # [PHASE 3A] Initialize organism self-awareness (conversational health)
            _health_monitor = ConversationHealthMonitor()
            conversation_context['_health_monitor'] = _health_monitor

            # [PHASE 3B] Initialize telephony perception (line health)
            _telephony_monitor = TelephonyHealthMonitor()
            conversation_context['_telephony_monitor'] = _telephony_monitor
            logger.info('[PHASE 3] Health monitors initialized: organism + telephony')

            self.active_conversations[client_id] = conversation_context

            # [ORGAN] Hook 3 — Agent Wired (moved here so conversation_context exists)
            if CALL_MONITOR_WIRED:
                monitor_agent_wired(conversation_context.get('call_sid', str(client_id)))

            # [DEEP LAYER] Initialize per-session QPC + Fluidic + Continuum
            # [CCNM] Seed with accumulated cross-call intelligence
            if DEEP_LAYER_WIRED:
                try:
                    # Generate CCNM seed from accumulated call intelligence
                    _ccnm_seed = None
                    if CCNM_WIRED:
                        try:
                            _ccnm_seed = ccnm_seed_session()
                            logger.info(f"[CCNM] Session seed generated — "
                                       f"active={_ccnm_seed.is_active()}, "
                                       f"confidence={_ccnm_seed.confidence:.2f}")
                            # Report to supervisor
                            if supervisor:
                                try:
                                    supervisor.update_ccnm_state(
                                        seed_active=_ccnm_seed.is_active(),
                                        confidence=_ccnm_seed.confidence,
                                        calls_analyzed=_ccnm_seed.calls_analyzed,
                                        successful_calls=_ccnm_seed.successful_calls,
                                        success_rate=_ccnm_seed.success_rate,
                                    )
                                except Exception as _ccnm_sup_err:
                                    logger.debug(f"[CCNM] Supervisor seed state update failed: {_ccnm_sup_err}")
                        except Exception as _ccnm_err:
                            logger.warning(f"[CCNM] Seed generation failed (neutral): {_ccnm_err}")
                            _ccnm_seed = None
                    
                    # Apply CCNM intent calibration to predictive engine
                    if _ccnm_seed and _ccnm_seed.is_active() and _ccnm_seed.intent_calibration:
                        try:
                            self.predictive_engine.set_calibration(_ccnm_seed.intent_calibration)
                        except Exception:
                            pass  # Non-fatal
                    
                    conversation_context['deep_layer'] = DeepLayer(seed=_ccnm_seed)
                    logger.info("[DEEP LAYER] Per-session instance initialized"
                               + (" + CCNM" if _ccnm_seed and _ccnm_seed.is_active() else ""))
                except Exception as e:
                    logger.warning(f"[DEEP LAYER] Init failed (non-fatal): {e}")
                    conversation_context['deep_layer'] = None

            # [BEHAVIORAL FUSION INITIALIZATION]
            if BEHAVIORAL_FUSION_WIRED:
                _behavioral_engines[client_id] = BehavioralFusionEngine(_BEHAVIORAL_CFG)
                _behavioral_stats[client_id] = {
                    "fluidic_state": "OPENING",
                    "trajectory_velocity": 0.0,
                    "trajectory_drift": 0.0,
                    "emotional_viscosity": 1.0,
                    "objection_count": 0,
                    "objections_resolved": 0,
                    "turn_count": 0,
                }
                logger.info(f"[BEHAVIORAL FUSION] Engine initialized for {client_id}")

            # [NFC] Neural Flow Cortex — per-session nervous system
            if NFC_WIRED:
                try:
                    conversation_context['_nfc'] = create_nfc()
                    logger.info("[NFC] Neural Flow Cortex initialized for session")
                except Exception as _nfc_init_err:
                    conversation_context['_nfc'] = None
                    logger.warning(f"[NFC] Init failed (non-fatal): {_nfc_init_err}")

            # [IVR] Initialize per-call IVR detector
            if IVR_DETECTOR_WIRED:
                conversation_context['_ivr_detector'] = IVRDetector()
                logger.info("[IVR] Per-call IVR detector initialized")

            # [EAB] Initialize per-call environment classifier
            if EAB_WIRED:
                conversation_context['_eab_classifier'] = create_classifier()
                conversation_context['_eab_classified'] = False
                conversation_context['_eab_env_class'] = None
                conversation_context['_eab_action'] = None
                conversation_context['_eab_cycle'] = 0
                logger.info("[EAB] Per-call environment classifier initialized")

            # [ORGAN 24] Initialize per-call Retrieval Cortex
            if RETRIEVAL_CORTEX_WIRED:
                try:
                    conversation_context['_retrieval_cortex'] = RetrievalCortex()
                    conversation_context['_retrieval_cortex'].start_call()
                    logger.info("[ORGAN 24] Retrieval Cortex initialized for call")
                except Exception as _rc_init_err:
                    conversation_context['_retrieval_cortex'] = None
                    logger.warning(f"[ORGAN 24] Init failed (non-fatal): {_rc_init_err}")

            # [ORGAN 34] Initialize per-call competitive intel state
            if COMPETITIVE_INTEL_WIRED:
                conversation_context['_competitive_intel'] = _competitive_intel_organ
                conversation_context['_detected_competitor'] = None
                conversation_context['_competitor_context'] = None
                conversation_context['_competitor_detections'] = []  # lineage log
                logger.info("[ORGAN 34] Competitive Intel linked for call")

            # [ORGAN 30] Initialize per-call Prosody Analysis
            if PROSODY_ANALYSIS_WIRED:
                try:
                    conversation_context['_prosody_analysis'] = ProsodyAnalysisOrgan()
                    conversation_context['_prosody_analysis'].start_call()
                    conversation_context['_prosody_emotion'] = 'neutral'
                    conversation_context['_prosody_confidence'] = 0.0
                    conversation_context['_prosody_strategy'] = None
                    logger.info("[ORGAN 30] Prosody Analysis initialized for call")
                except Exception as _pa_init_err:
                    conversation_context['_prosody_analysis'] = None
                    logger.warning(f"[ORGAN 30] Init failed (non-fatal): {_pa_init_err}")

            # [ORGAN 31] Initialize per-call objection learning tracker
            if OBJECTION_LEARNING_WIRED:
                conversation_context['_objection_events'] = []   # per-call objection log
                conversation_context['_objection_turns'] = 0     # turns with objections
                logger.info("[ORGAN 31] Objection Learning tracker initialized for call")

            # [ORGAN 36] Initialize per-call DTMF Reflex
            if DTMF_REFLEX_WIRED:
                try:
                    conversation_context['_dtmf_reflex'] = create_dtmf_reflex()
                    logger.info("[ORGAN 36] DTMF Reflex initialized for call")
                except Exception as _dtmf_init_err:
                    conversation_context['_dtmf_reflex'] = None
                    logger.warning(f"[ORGAN 36] DTMF init failed (non-fatal): {_dtmf_init_err}")

            # [ORGAN 37] Initialize per-call IVR Navigator
            if IVR_NAVIGATOR_WIRED:
                try:
                    conversation_context['_ivr_navigator'] = create_ivr_navigator()
                    conversation_context['_ivr_nav_active'] = False  # activated by EAB when IVR detected
                    logger.info("[ORGAN 37] IVR Navigator initialized for call")
                except Exception as _nav_init_err:
                    conversation_context['_ivr_navigator'] = None
                    logger.warning(f"[ORGAN 37] IVR Navigator init failed (non-fatal): {_nav_init_err}")

            # [ORGAN 32] Initialize per-call Summarization organ
            if SUMMARIZATION_WIRED:
                try:
                    _call_id_sum = conversation_context.get('call_sid', conversation_context.get('stream_sid', 'unknown'))
                    conversation_context['_summarization_organ'] = SummarizationOrgan()
                    conversation_context['_summarization_organ'].start_call(_call_id_sum, {
                        'call_sid': _call_id_sum,
                        'start_time': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                    })
                    conversation_context['_summary_state'] = 'collecting'  # inactive|collecting|complete
                    logger.info("[ORGAN 32] Summarization organ initialized for call")
                except Exception as _sum_init_err:
                    conversation_context['_summarization_organ'] = None
                    conversation_context['_summary_state'] = 'inactive'
                    logger.warning(f"[ORGAN 32] Init failed (non-fatal): {_sum_init_err}")

            # [ORGAN 33] Initialize per-call CRM Integration organ
            if CRM_INTEGRATION_WIRED:
                try:
                    _call_id_crm = conversation_context.get('call_sid', conversation_context.get('stream_sid', 'unknown'))
                    conversation_context['_crm_organ'] = CRMIntegrationOrgan()
                    conversation_context['_crm_organ'].start_call(_call_id_crm)
                    conversation_context['_crm_push_state'] = 'idle'  # idle|queued|pushed|failed
                    conversation_context['_crm_push_result'] = None   # result from push_summary
                    logger.info("[ORGAN 33] CRM Integration organ initialized for call")
                except Exception as _crm_init_err:
                    conversation_context['_crm_organ'] = None
                    conversation_context['_crm_push_state'] = 'idle'
                    conversation_context['_crm_push_result'] = None
                    logger.warning(f"[ORGAN 33] Init failed (non-fatal): {_crm_init_err}")

            # [ORGAN 35] Initialize per-call IQ Budget organ
            if IQ_BUDGET_WIRED:
                try:
                    _call_id_iq = conversation_context.get('call_sid', conversation_context.get('stream_sid', 'unknown'))
                    conversation_context['_iq_budget_organ'] = InCallBudgetOrgan()
                    conversation_context['_iq_budget_organ'].start_call(_call_id_iq)
                    conversation_context['_iq_state'] = 'normal'  # normal|high|critical|exhausted
                    conversation_context['_iq_burn_total'] = 0
                    conversation_context['_iq_turn_spend'] = 0
                    conversation_context['_iq_disabled_organs'] = []
                    conversation_context['_iq_fallback_active'] = False
                    logger.info("[ORGAN 35] IQ Budget organ initialized for call")
                except Exception as _iq_init_err:
                    conversation_context['_iq_budget_organ'] = None
                    conversation_context['_iq_state'] = 'normal'
                    conversation_context['_iq_burn_total'] = 0
                    conversation_context['_iq_turn_spend'] = 0
                    conversation_context['_iq_disabled_organs'] = []
                    conversation_context['_iq_fallback_active'] = False
                    logger.warning(f"[ORGAN 35] Init failed (non-fatal): {_iq_init_err}")

            # [ORGAN 29] Initialize per-call Inbound Context organ
            if INBOUND_CONTEXT_WIRED:
                try:
                    _call_id_ic = conversation_context.get('call_sid', conversation_context.get('stream_sid', 'unknown'))
                    conversation_context['_inbound_context_organ'] = InboundContextOrgan()
                    conversation_context['_inbound_context_organ'].start_call(_call_id_ic)
                    conversation_context['_inbound_context'] = None       # populated on inbound lookup
                    conversation_context['_inbound_context_state'] = 'cold'  # cold|warm|partial
                    logger.info("[ORGAN 29] Inbound Context organ initialized for call")
                except Exception as _ic_init_err:
                    conversation_context['_inbound_context_organ'] = None
                    conversation_context['_inbound_context'] = None
                    conversation_context['_inbound_context_state'] = 'cold'
                    logger.warning(f"[ORGAN 29] Init failed (non-fatal): {_ic_init_err}")

            # [ORGAN 28] Initialize per-call Calendar Engine state
            if CALENDAR_ENGINE_WIRED:
                try:
                    _call_id_cal = conversation_context.get('call_sid', conversation_context.get('stream_sid', 'unknown'))
                    conversation_context['_calendar_organ'] = CalendarOrgan()
                    conversation_context['_calendar_organ'].start_call(_call_id_cal)
                    conversation_context['_calendar_state'] = 'inactive'  # inactive|proposed|confirmed|declined
                    conversation_context['_calendar_proposed'] = None     # proposed slot details
                    conversation_context['_calendar_booking'] = None      # confirmed booking result
                    logger.info("[ORGAN 28] Calendar Engine initialized for call")
                except Exception as _cal_init_err:
                    conversation_context['_calendar_organ'] = None
                    conversation_context['_calendar_state'] = 'inactive'
                    logger.warning(f"[ORGAN 28] Init failed (non-fatal): {_cal_init_err}")

            # [ORGAN 27] Initialize per-call Language Switch state
            if LANGUAGE_SWITCH_WIRED:
                try:
                    _call_id_ls = conversation_context.get('call_sid', conversation_context.get('stream_sid', 'unknown'))
                    conversation_context['_language_organ'] = LanguageSwitchOrgan()
                    conversation_context['_language_organ'].start_call(_call_id_ls)
                    conversation_context['_language_state'] = 'en'          # current language code
                    conversation_context['_language_switch_state'] = 'inactive'  # inactive|pending_confirm|switched|declined
                    conversation_context['_language_detected'] = None       # detected non-English language
                    conversation_context['_language_confidence'] = 0.0
                    logger.info("[ORGAN 27] Language Switch initialized for call (default: en)")
                except Exception as _ls_init_err:
                    conversation_context['_language_organ'] = None
                    conversation_context['_language_state'] = 'en'
                    conversation_context['_language_switch_state'] = 'inactive'
                    logger.warning(f"[ORGAN 27] Init failed (non-fatal): {_ls_init_err}")

            # [ORGAN 26] Initialize per-call Outbound Comms state
            if OUTBOUND_COMMS_WIRED:
                try:
                    _call_id_oc = conversation_context.get('call_sid', conversation_context.get('stream_sid', 'unknown'))
                    conversation_context['_outbound_comms'] = OutboundCommsOrgan()
                    conversation_context['_outbound_comms'].start_call(_call_id_oc)
                    conversation_context['_outbound_sends'] = []  # per-call send log
                    conversation_context['_outbound_pending'] = None  # pending send request (awaiting contact info)
                    logger.info("[ORGAN 26] Outbound Comms initialized for call")
                except Exception as _oc_init_err:
                    conversation_context['_outbound_comms'] = None
                    conversation_context['_outbound_sends'] = []
                    conversation_context['_outbound_pending'] = None
                    logger.warning(f"[ORGAN 26] Init failed (non-fatal): {_oc_init_err}")

            # [ORGAN 25] Initialize per-call Warm Handoff state
            if WARM_HANDOFF_WIRED:
                try:
                    _call_id = conversation_context.get('call_sid', conversation_context.get('stream_sid', 'unknown'))
                    conversation_context['_handoff_organ'] = HandoffEscalationOrgan()
                    conversation_context['_handoff_organ'].start_call(_call_id)
                    conversation_context['_handoff_state'] = 'inactive'  # inactive|pending_consent|initiated|completed|failover
                    conversation_context['_handoff_reason'] = None
                    conversation_context['_handoff_result'] = None
                    logger.info("[ORGAN 25] Warm Handoff initialized for call")
                except Exception as _ho_init_err:
                    conversation_context['_handoff_organ'] = None
                    conversation_context['_handoff_state'] = 'inactive'
                    logger.warning(f"[ORGAN 25] Init failed (non-fatal): {_ho_init_err}")

            # [CONV INTEL] Initialize per-call Conversation Guard
            # Checks merchant name against government/non-merchant patterns at init.
            # If entity classified as government from name alone → abort before greeting.
            if CONV_INTEL_WIRED:
                _merchant_name = conversation_context.get('prospect_info', {}).get('company', '')
                _guard = ConversationGuard(_merchant_name)
                conversation_context['_conversation_guard'] = _guard
                
                # Check if merchant name alone triggers government exit
                if _guard.name_check_abort:
                    _abort = _guard.name_check_abort
                    logger.warning(f"[CONV INTEL] GOVERNMENT ENTITY from name: '{_merchant_name}' — aborting before greeting")
                    # [PHASE 2] FSM: → ENDED (government_entity)
                    _fsm = conversation_context.get('_call_fsm')
                    if _fsm:
                        _fsm.end_call(reason='government_entity')
                    else:
                        conversation_context['stream_ended'] = True
                    conversation_context['_evolution_outcome'] = _abort.get('outcome', 'government_entity')
                    conversation_context['_guard_outcome'] = _abort.get('outcome', 'government_entity')
                    conversation_context['_ccnm_ignore'] = True
                    # Send exit line and close
                    try:
                        stream_sid = conversation_context.get('streamSid')
                        if stream_sid and websocket:
                            asyncio.create_task(self.synthesize_and_stream_greeting(
                                websocket, _abort.get('exit_line', 'My apologies, wrong number. Have a great day!'), stream_sid
                            ))
                    except Exception as _govt_err:
                        logger.debug(f"[CONV INTEL] Government abort greeting failed: {_govt_err}")
                else:
                    logger.info(f"[CONV INTEL] Guard initialized for '{_merchant_name}' — all systems nominal")

            # [ORGAN 11] Initialize signature extraction for this call
            if SIGNATURE_ENGINE_WIRED:
                try:
                    sig_extractor = SignatureExtractor()
                    sig_extractor.start_call()
                    conversation_context['_signature_extractor'] = sig_extractor
                    # Compute initial effective signature from global learned identity
                    global_sig = _sig_learner.get_global_signature()
                    conversation_context['_effective_signature'] = compute_effective_signature(global_sig)
                    logger.info(f"[ORGAN 11] Signature extractor initialized — "
                               f"global speed_bias={conversation_context['_effective_signature'].speed_bias:.3f}, "
                               f"silence_bias={conversation_context['_effective_signature'].silence_bias_frames}")
                except Exception as e:
                    logger.warning(f"[ORGAN 11] Extractor init failed (non-fatal): {e}")
                    conversation_context['_signature_extractor'] = None
                    conversation_context['_effective_signature'] = None

            if supervisor:
                supervisor.health_state["conversation_loop"]["status"] = "ok"

            # [FIX] Adapter for Starlette/FastAPI WebSocket which requires iter_text()
            iterator = websocket.iter_text() if hasattr(websocket, "iter_text") else websocket
            
            async for message in iterator:
                # [CRITICAL FIX] Check if sentinel flagged call for disconnect
                # Without this, the main loop runs until Twilio drops the WebSocket
                # even after the sentinel sets stream_ended = True. This caused
                # calls to run 538s instead of dying at 300s hard max.
                if conversation_context.get('stream_ended'):
                    logger.info(f"[STREAM] Breaking main loop — stream_ended flagged by sentinel")
                    try:
                        await websocket.close()
                    except Exception:
                        pass
                    break
                try:
                    # Parse incoming message
                    data = json.loads(message)

                    # [FIX] Twilio Media Stream Support
                    event = data.get('event')
                    if event:
                        if event == 'start':
                            stream_sid = data['start']['streamSid']
                            call_sid = data['start'].get('callSid', stream_sid)
                            conversation_context['streamSid'] = stream_sid
                            conversation_context['call_sid'] = call_sid
                            
                            # [INBOUND SENSITIZER] Start monitoring call
                            if INBOUND_SENSITIZER_WIRED and _inbound_sensitizer:
                                _inbound_sensitizer.register_call(call_sid)
                                
                            # [PHASE 2] FSM: INIT → STREAM_READY (replaces stream_started = True)
                            _fsm = conversation_context.get('_call_fsm')
                            if _fsm:
                                _fsm.call_sid = call_sid
                                _fsm.handle_event(CallFlowEvent.STREAM_START)
                            else:
                                conversation_context['stream_started'] = True
                            conversation_context['websocket'] = websocket 
                            self.stream_sid_to_client_id[stream_sid] = client_id
                            
                            logger.info(f"[TWILIO] Stream Started: {stream_sid} | Call: {call_sid}")
                            
                            # [LIVE MONITOR] Register call for real-time tracking
                            if LIVE_MONITOR_WIRED and _live_monitor:
                                _live_monitor.register_call(call_sid, datetime.now())
                            
                            aqi_stt_engine.create_stt_session(stream_sid)
                            
                            # [REPLICATION] Register this call as an active Alan instance
                            if REPLICATION_WIRED:
                                try:
                                    custom_params = data['start'].get('customParameters', {})
                                    rep_engine = get_replication_engine()
                                    rep_engine.register_instance(call_sid, {
                                        "prospect_name": custom_params.get('prospect_name', 'Unknown'),
                                        "business_name": custom_params.get('business_name', ''),
                                        "phone_number": custom_params.get('prospect_phone', ''),
                                    })
                                    conversation_context['replication_registered'] = True
                                    logger.info(f"[REPLICATION] Instance registered for call {call_sid} "
                                                f"(fleet: {rep_engine.current_count}/{rep_engine.max_instances})")
                                except Exception as e:
                                    logger.warning(f"[REPLICATION] Failed to register: {e}")
                            
                            # [ORGAN] Hook 1 — Call Start
                            if CALL_MONITOR_WIRED:
                                merchant_phone = data['start'].get('customParameters', {}).get('prospect_phone', '')
                                monitor_call_start(call_sid, str(client_id), merchant_phone)
                            
                            # [CAPTURE] Record call start — fire-and-forget
                            if CALL_CAPTURE_WIRED:
                                _custom = data['start'].get('customParameters', {})
                                _cdc_call_start(
                                    call_sid, str(client_id),
                                    merchant_phone=_custom.get('prospect_phone', ''),
                                    merchant_name=_custom.get('prospect_name', ''),
                                    business_name=_custom.get('business_name', ''),
                                )
                            
                            data['parameters'] = data['start'].get('customParameters', {})
                            
                            # [AQI 0.1mm CHIP] Guard — on_call_start
                            if AQI_GUARD_WIRED and self._aqi_guard:
                                try:
                                    self._aqi_guard.on_call_start(call_sid, "OPENING", {
                                        'client_id': str(client_id),
                                        'merchant_phone': data['start'].get('customParameters', {}).get('prospect_phone', ''),
                                    })
                                except Exception as _aqi_err:
                                    logger.warning(f"[AQI GUARD] on_call_start failed (non-fatal): {_aqi_err}")
                            
                            # [PHASE 4] Trace Exporter — init trace skeleton
                            if PHASE4_EXPORTER_WIRED and self._phase4_exporter:
                                try:
                                    _p4_custom = data['start'].get('customParameters', {})
                                    self._phase4_exporter.init_trace(
                                        call_sid,
                                        custom_params=_p4_custom,
                                        start_time=conversation_context.get('start_time'),
                                    )
                                except Exception as _p4_err:
                                    logger.warning(f"[PHASE 4 EXPORTER] on_call_start failed (non-fatal): {_p4_err}")
                            
                            await self.handle_conversation_start(data, conversation_context, websocket)

                            # [WATCHDOG] Turn capture reliability — fires after 10s to verify
                            # STT pipeline is producing turns. If 0 turns after 10s on an
                            # active call, something went wrong (race condition, STT failure).
                            async def _turn_watchdog(ctx, cid):
                                try:
                                    await asyncio.sleep(10.0)
                                    if ctx.get('stream_ended'):
                                        return  # Call already ended
                                    msgs = ctx.get('messages', [])
                                    if len(msgs) == 0:
                                        elapsed = (datetime.now() - ctx['start_time']).total_seconds()
                                        logger.warning(
                                            f"[WATCHDOG] 0 turns after {elapsed:.0f}s on call {ctx.get('call_sid', cid)} — "
                                            f"STT pipeline may be stalled. stream_started={ctx.get('stream_started')}, "
                                            f"greeting_sent={ctx.get('greeting_sent')}, "
                                            f"vad_state={ctx.get('vad_state', 'unknown')}"
                                        )
                                        # Force finalize STT buffer in case audio was buffered but never committed
                                        _ws_sid = ctx.get('streamSid')
                                        if _ws_sid:
                                            try:
                                                await aqi_stt_engine.finalize_and_clear(_ws_sid)
                                                logger.info(f"[WATCHDOG] Forced STT finalize for {_ws_sid}")
                                            except Exception as _stt_err:
                                                logger.debug(f"[WATCHDOG] STT finalize failed: {_stt_err}")
                                except asyncio.CancelledError:
                                    logger.info("[WATCHDOG] Task cancelled (call ended)")
                                except Exception as _wd_err:
                                    logger.error(f"[WATCHDOG] CRASH — STT stall detection DISABLED: {_wd_err}", exc_info=True)
                            asyncio.create_task(_turn_watchdog(conversation_context, str(client_id)))

                            # ================================================================
                            # [COST SENTINEL] Air-Call / IVR Timeout / Idle Kill
                            # ================================================================
                            # Tim's Directive: "Do not allow for so called Air-Calls —
                            #   no open lines with nothing happening. Detect and kill."
                            # Also enforces IVR time-based fallback and max idle duration.
                            # ================================================================
                            async def _cost_sentinel(ctx, ws, cid):
                                """Background cost-protection monitor for each call.
                                
                                Checks every 10s:
                                1. AIR-CALL: No merchant speech for 60s → Alan asks "Are you there?"
                                   No response after 90s total → force hangup.
                                2. IVR TIMEOUT: If IVR detector flagged is_ivr and call > 90s → abort.
                                3. MAX IDLE: Call > 60s with 0 meaningful turns → abort.
                                4. ENGAGED CALLS OK: If Alan is having a real conversation, no interference.
                                
                                [2026-02-20 FIX] Restored generous limits. Previous values (20s zero-turn,
                                25s silence, 8s initial sleep) were murdering live human calls before Alan
                                could even have a conversation. Tim's directive: "we should never be killed."
                                The sentinel must protect against true air-calls and IVR, NOT kill calls
                                where a human picked up and is taking a moment to respond.
                                """
                                _sentinel_asked = False  # Already asked "are you there?"
                                _real_turns = 0          # [2026-02-28 FIX] Init before loop — used in _has_real_conversation
                                                         # check (line ~4223) before IVR counting defines it (line ~4285).
                                                         # Without this, fast human pickups (2+ meaningful turns in 28s)
                                                         # cause NameError → sentinel crashes silently → all protections off.
                                _SILENCE_WARNING = 30.0  # Seconds before asking "are you there?" (was 50 — too generous for dead lines)
                                _SILENCE_KILL = 50.0     # Seconds before force hangup (was 75 — wasted 25s of Twilio billing)
                                _IVR_TIME_LIMIT = 90.0   # Max time for IVR-flagged call
                                _ZERO_TURN_LIMIT = 40.0  # Max time with 0 merchant turns (was 60 — 40s after sentinel start = 58s total)
                                _HARD_MAX_DURATION = 600.0  # 10 min absolute backstop — supports 40+ turn deep conversations
                                _HARD_MAX_TURNS = 30     # [2026-02-28] Absolute turn backstop. No call ever exceeds 30 turns.
                                                         # Catches IVR loops where duration tracking fails (78-turn salon loop).
                                                         # Real human conversations rarely exceed 20 turns.
                                try:
                                    await asyncio.sleep(18.0)  # Give call time to establish + greeting to land (restored from 8)
                                    while not ctx.get('stream_ended'):
                                        await asyncio.sleep(10.0)
                                        if ctx.get('stream_ended'):
                                            break

                                        elapsed = (datetime.now() - ctx['start_time']).total_seconds()
                                        msgs = ctx.get('messages', [])
                                        merchant_turns = sum(1 for m in msgs if m.get('user', '').strip())
                                        # [FIX] Count MEANINGFUL turns — at least 2 words.
                                        # STT transcribes background noise/music as short text
                                        # ("ok", "hmm", "...") which creates phantom turns.
                                        # These phantom turns prevented CHECK 3 from firing.
                                        # [2026-02-20 FIX] Reduced from 3 to 2 — "Hello?" or "Yeah?"
                                        # from a human should count as a turn, not be ignored.
                                        _MEANINGFUL_WORD_MIN = 2
                                        meaningful_turns = sum(
                                            1 for m in msgs
                                            if len((m.get('user', '') or '').strip().split()) >= _MEANINGFUL_WORD_MIN
                                        )
                                        last_speech = ctx.get('last_speech_time', 0)
                                        now_ts = time.time()
                                        silence_duration = (now_ts - last_speech) if last_speech > 0 else elapsed

                                        # --- CHECK 0: INBOUND HEARTBEAT ---
                                        if INBOUND_SENSITIZER_WIRED and _inbound_sensitizer and cid:
                                            _hb = _inbound_sensitizer.check_heartbeat(cid)
                                            if _hb.get('action') == 'hangup':
                                                logger.warning(f"[COST SENTINEL] INBOUND KILL — {_hb.get('reason')}")
                                                # [PHASE 2] FSM: → ENDED (connection_loss_kill)
                                                _fsm = ctx.get('_call_fsm')
                                                if _fsm:
                                                    _fsm.end_call(reason='connection_loss_kill')
                                                else:
                                                    ctx['stream_ended'] = True
                                                ctx['_evolution_outcome'] = 'connection_loss_kill'
                                                ctx['_killed_by'] = 'inbound_sentinel'
                                                # Don't try to synthesize goodbye - connection is dead
                                                break

                                        # --- CHECK 0: HARD MAX TURNS BACKSTOP ---
                                        # [2026-02-28] No call EVER exceeds 30 turns. Period.
                                        # Catches IVR loops where duration tracking fails.
                                        # Data: 78-turn salon call showed 0s duration — the
                                        # duration backstop never fired. Turn count is reliable.
                                        if merchant_turns >= _HARD_MAX_TURNS:
                                            logger.warning(
                                                f"[COST SENTINEL] HARD MAX TURNS KILL — {merchant_turns} turns "
                                                f"(limit={_HARD_MAX_TURNS}). elapsed={elapsed:.0f}s. "
                                                f"Absolute turn backstop. Force disconnect."
                                            )
                                            _fsm = ctx.get('_call_fsm')
                                            if _fsm:
                                                _fsm.end_call(reason='max_turns_kill')
                                            else:
                                                ctx['stream_ended'] = True
                                            ctx['_evolution_outcome'] = 'max_turns_kill'
                                            ctx['_killed_by'] = 'sentinel'
                                            ctx['_ccnm_ignore'] = True
                                            try:
                                                asyncio.create_task(
                                                    self.synthesize_and_stream_greeting(
                                                        ws, "I appreciate your time today. I'll follow up another time. Goodbye!",
                                                        ctx.get('streamSid')
                                                    )
                                                )
                                            except Exception as _bye_err:
                                                logger.debug(f"[COST SENTINEL] Goodbye synthesis failed (max turns kill): {_bye_err}")
                                            break

                                        # --- CHECK 0: HARD MAX DURATION BACKSTOP ---
                                        # No call EVER runs longer than 10 minutes. Period.
                                        # This catches every edge case: noise resetting timers,
                                        # IVR hold music, broken connections, etc.
                                        # [LONG CONV] Raised from 300s (5 min) to 600s (10 min)
                                        # to support 20-40+ turn deep consultative conversations.
                                        if elapsed > _HARD_MAX_DURATION:
                                            logger.warning(
                                                f"[COST SENTINEL] HARD MAX KILL — {elapsed:.0f}s elapsed "
                                                f"(limit={_HARD_MAX_DURATION:.0f}s). turns={merchant_turns}. "
                                                f"Absolute time backstop. Force disconnect."
                                            )
                                            # [PHASE 2] FSM: → ENDED (max_duration_kill)
                                            _fsm = ctx.get('_call_fsm')
                                            if _fsm:
                                                _fsm.end_call(reason='max_duration_kill')
                                            else:
                                                ctx['stream_ended'] = True
                                            ctx['_evolution_outcome'] = 'max_duration_kill'
                                            ctx['_killed_by'] = 'sentinel'
                                            ctx['_ccnm_ignore'] = True
                                            try:
                                                asyncio.create_task(
                                                    self.synthesize_and_stream_greeting(
                                                        ws, "I appreciate your time today. I'll follow up another time. Goodbye!",
                                                        ctx.get('streamSid')
                                                    )
                                                )
                                            except Exception as _bye_err:
                                                logger.debug(f"[COST SENTINEL] Goodbye synthesis failed (silence kill): {_bye_err}")
                                            break

                                        # --- CHECK 0.5: TRANSCRIPT IVR DETECTION ---
                                        # If merchant "turns" contain IVR phrases, they don't count as
                                        # real conversation. This catches recorded human-voice IVR systems
                                        # that fool the voice frequency detector.
                                        _ivr_phrases = ['press one', 'press two', 'press three', 'press four',
                                                        'press five', 'press six', 'press seven', 'press eight',
                                                        'press nine', 'press zero', 'press pound', 'press star',
                                                        'to replay', 'to repeat', 're-record', 'leave a message',
                                                        'after the tone', 'after the beep', 'not available',
                                                        'business hours', 'office hours', 'regular hours',
                                                        'press the', 'dial one', 'dial two', 'to disconnect',
                                                        'to add to it', 'report a claim', 'your call is',
                                                        'please hold', 'please wait', 'your call will be',
                                                        'this call may be', 'your call may be', 'may be monitored',
                                                        'may be recorded', 'select from the', 'following menu',
                                                        'reached our main', 'reached the main', 'wrong number',
                                                        'for quality', 'para espanol', 'directory',
                                                        'if you know your party', 'extension', 'operator',
                                                        # [2026-02-20] CALL SCREENER / PHONE SCANNER PATTERNS
                                                        'please stay on the line', 'stay on the line',
                                                        'what company did you say', 'what company',
                                                        'screening this call', 'screening your call',
                                                        'state your name', 'state your business',
                                                        'who is calling', 'describe why you',
                                                        'are you a real person', 'are you a robot',
                                                        'if you\'re selling', 'are you selling',
                                                        'are you soliciting', 'person you\'re calling',
                                                        'person you\'re trying to reach',
                                                        'is this call important', 'please remain on the line',
                                                        'i\'ll let them know', 'pass that along']

                                        # --- IVR TURN COUNTING (compute _real_turns) ---
                                        # [2026-02-28 STRUCTURAL FIX] Moved ABOVE voicemail check.
                                        # _real_turns is used by _has_real_conversation in CHECK 0.6.
                                        # Previously computed 140 lines later — forward-reference bug
                                        # caused NameError on fast human pickups, silently killing
                                        # the entire sentinel. Now computed immediately after the
                                        # IVR phrase list, before any consumer.
                                        _ivr_turn_count = 0
                                        for _m in msgs:
                                            _mt = (_m.get('user', '') or '').lower()
                                            if any(p in _mt for p in _ivr_phrases):
                                                _ivr_turn_count += 1
                                        _real_turns = merchant_turns - _ivr_turn_count

                                        # --- CHECK 0.6: INSTANT VOICEMAIL KILL ---
                                        # If ANY turn contains definitive voicemail language, kill immediately.
                                        # No need to wait — voicemail is never a real conversation.
                                        #
                                        # [2026-03-03 FIX] REMOVED 'thank you/thanks for calling' from
                                        # definitive killers. These are AMBIGUOUS — real humans say
                                        # "thank you for calling me, Alan" and "thanks for calling."
                                        # Tim's call #3 was killed because he said "Well, thank you
                                        # for calling me, Alan. What would you like to know?" — clearly
                                        # a human, not a voicemail. Moved to ambiguous-only detection
                                        # with stricter qualifying rules.
                                        _voicemail_killers = ['leave a message', 'leave your message',
                                                              'after the tone', 'after the beep',
                                                              'record your message', 'not available right now',
                                                              'cannot take your call',
                                                              'reached the voicemail', 'mailbox is full',
                                                              'no one is available', 'at the tone',
                                                              're-record your message', 'press pound',
                                                              'monitor your call', 'recorded for quality',
                                                              'reached our main', 'reached the main',
                                                              'select from the', 'following menu',
                                                              'get to the phone', 'come to the phone',
                                                              'take your call right now', 'not here right now',
                                                              'leave your name', 'name and number',
                                                              'unable to answer', 'can\'t answer',
                                                              'stepped away', 'away from the phone',
                                                              'busy on another', 'currently on another',
                                                              'is not available', 'not in service',
                                                              'trying to reach', 'you have reached',
                                                              'subscriber', 'has been disconnected',
                                                              # [2026-02-20] CALL SCREENER / PHONE SCANNER PATTERNS
                                                              # Tim: "Alan continues to talk to phone scanners"
                                                              'please stay on the line', 'stay on the line',
                                                              'screening this call', 'screening your call',
                                                              'describe why you', 'person you\'re calling',
                                                              'person you\'re trying to reach',
                                                              'serving from', 'last seating',
                                                              'table reservations', 'make a reservation']
                                        _is_voicemail = False
                                        # [EAB GUARD] If EAB is actively navigating a screener/IVR,
                                        # don't let sentinel kill the call for screener phrases —
                                        # EAB is handling the pass-through attempt.
                                        _eab_active = ctx.get('_eab_action') in (
                                            EnvironmentAction.PASS_THROUGH if EAB_WIRED else None,
                                            EnvironmentAction.NAVIGATE if EAB_WIRED else None,
                                        ) if EAB_WIRED else False

                                        # [2026-02-24 FIX] HUMAN CONVERSATION GUARD
                                        # If a real back-and-forth has happened (1+ meaningful turns
                                        # AND recent speech), this is a HUMAN — not a voicemail.
                                        # Voicemails don't have multi-turn back-and-forth.
                                        # Tim: "What my concern would be, is if it may interfere
                                        # with an actual human caller?"
                                        # [2026-03-03 FIX] Lowered from 2→1 meaningful turns.
                                        # A merchant who says 13+ words ("Well, thank you for
                                        # calling me, Alan. What would you like to know?") in
                                        # their FIRST response is definitively human. Voicemails
                                        # never address the caller by name or ask questions.
                                        _has_real_conversation = (
                                            meaningful_turns >= 1
                                            and _real_turns >= 1
                                            and silence_duration < 30.0
                                        )

                                        # [2026-02-24 FIX] AMBIGUOUS PHRASE GUARD
                                        # These phrases are used by BOTH voicemails AND real humans
                                        # (receptionists). They are NOT in _voicemail_killers.
                                        # They only trigger a VM kill when:
                                        #   1. They appear in the first utterance (turn 0), AND
                                        #   2. There's NO human-indicator in the same utterance, AND
                                        #   3. The utterance is short (<15 words — VM greetings are brief)
                                        #
                                        # [2026-03-03 FIX] Complete rewrite of ambiguous phrase logic.
                                        # OLD BUG: The guard said "if ambiguous AND _idx >= 2: continue"
                                        # — this was BACKWARDS. It protected ambiguous phrases in
                                        # LATER turns but KILLED them in EARLY turns (0-1). A VM
                                        # says "thank you for calling" in turn 0 — but so does a
                                        # polite human. The old logic killed both.
                                        # NEW: Ambiguous phrases are only VM-flagged when the
                                        # utterance ALSO lacks human indicators (names, questions,
                                        # personal pronouns addressing the caller).
                                        _ambiguous_phrases = {
                                            'thank you for calling', 'thanks for calling',
                                            'who is calling', 'what company',
                                            'what company did you say',
                                            'state your name', 'state your business',
                                            'are you selling', 'are you soliciting',
                                            'is this call important', 'if you\'re selling',
                                            'are you a real person', 'are you a robot',
                                            'unavailable',
                                        }

                                        # Human-speech indicators: if ANY of these appear in the
                                        # same utterance as an ambiguous phrase, it's a human.
                                        # Voicemails never address the caller by name, ask
                                        # questions, or use second-person references.
                                        _human_indicators = [
                                            'alan', 'what would you', 'how can i help',
                                            'what do you', 'who are you', 'what are you',
                                            'calling me', 'called me', 'how are you',
                                            'what can i do', 'how may i help', 'yes?',
                                            'yeah?', 'hello?', 'speaking',
                                            'this is', 'you\'re looking for',
                                            'go ahead', 'sure, what', 'okay, what',
                                            # [2026-03-03] Additional human-conversation signals:
                                            # These phrases indicate interactive back-and-forth
                                            # that voicemails never produce.
                                            'can you call', 'call back', 'call me back',
                                            'try again', 'come back', 'sorry,',
                                            'no problem', 'sure thing', 'one moment',
                                            'hold on', 'let me', 'i\'ll get',
                                            'he\'s not', 'she\'s not', 'they\'re not',
                                            'the owner', 'the manager', 'my boss',
                                            'what\'s this about', 'what\'s this regarding',
                                            'can i help', 'may i help', 'help you with',
                                        ]

                                        # [2026-03-03] INSTRUCTOR MODE BYPASS
                                        # Instructor/training calls are NEVER voicemail.
                                        _is_instructor_call = ctx.get('prospect_info', {}).get('instructor_mode', False)

                                        for _idx, _m in enumerate(msgs):
                                            _mt = (_m.get('user', '') or '').lower()
                                            for _vk_phrase in _voicemail_killers:
                                                if _vk_phrase in _mt:
                                                    _is_voicemail = True
                                                    break
                                            # Check ambiguous phrases separately with stricter rules
                                            if not _is_voicemail:
                                                for _ap in _ambiguous_phrases:
                                                    if _ap in _mt:
                                                        # Only flag as VM if:
                                                        # 1. Early turn (0 or 1)
                                                        # 2. Short utterance (< 15 words — VM greetings)
                                                        # 3. No human indicators present
                                                        _word_count = len(_mt.split())
                                                        _has_human_signal = any(h in _mt for h in _human_indicators)
                                                        if _idx <= 1 and _word_count < 15 and not _has_human_signal:
                                                            _is_voicemail = True
                                                            logger.info(f"[COST SENTINEL] Ambiguous phrase '{_ap}' flagged as VM (turn={_idx}, words={_word_count}, no human signal)")
                                                            break
                                                        else:
                                                            logger.info(f"[COST SENTINEL] Ambiguous phrase '{_ap}' SKIPPED — human detected (turn={_idx}, words={_word_count}, human_signal={_has_human_signal})")
                                            if _is_voicemail:
                                                break

                                        # [2026-03-03] Instructor mode calls are never voicemail
                                        if _is_instructor_call and _is_voicemail:
                                            logger.info(f"[COST SENTINEL] VM detection overridden — instructor mode call")
                                            _is_voicemail = False

                                        if _is_voicemail and elapsed > 15.0 and not _eab_active and not _has_real_conversation:
                                            logger.warning(
                                                f"[COST SENTINEL] VOICEMAIL KILL — {elapsed:.0f}s elapsed, "
                                                f"definitive voicemail language detected. Force disconnect."
                                            )
                                            # [PHASE 2] FSM: → ENDED (voicemail_ivr)
                                            _fsm = ctx.get('_call_fsm')
                                            if _fsm:
                                                _fsm.end_call(reason='voicemail_ivr')
                                            else:
                                                ctx['stream_ended'] = True
                                            ctx['_evolution_outcome'] = 'voicemail_ivr'
                                            ctx['_killed_by'] = 'sentinel'
                                            ctx['_ccnm_ignore'] = True
                                            try:
                                                asyncio.create_task(
                                                    self.synthesize_and_stream_greeting(
                                                        ws, "I'll try back at a better time. Goodbye!",
                                                        ctx.get('streamSid')
                                                    )
                                                )
                                            except Exception as _bye_err:
                                                logger.debug(f"[COST SENTINEL] Goodbye synthesis failed (voicemail kill): {_bye_err}")
                                            break

                                        # If >30% of merchant turns match IVR phrases, it's not a real conversation (was 40%)
                                        _is_ivr_conversation = (merchant_turns >= 2 and _ivr_turn_count / max(merchant_turns, 1) > 0.3)
                                        if _is_ivr_conversation and elapsed > 30.0:
                                            logger.warning(
                                                f"[COST SENTINEL] TRANSCRIPT IVR KILL — {elapsed:.0f}s elapsed, "
                                                f"{_ivr_turn_count}/{merchant_turns} turns match IVR phrases. "
                                                f"Force disconnect."
                                            )
                                            # [PHASE 2] FSM: → ENDED (ivr_transcript_kill)
                                            _fsm = ctx.get('_call_fsm')
                                            if _fsm:
                                                _fsm.end_call(reason='ivr_transcript_kill')
                                            else:
                                                ctx['stream_ended'] = True
                                            ctx['_evolution_outcome'] = 'ivr_transcript_kill'
                                            ctx['_killed_by'] = 'sentinel'
                                            ctx['_ccnm_ignore'] = True
                                            try:
                                                asyncio.create_task(
                                                    self.synthesize_and_stream_greeting(
                                                        ws, "I appreciate your time, but I'll try back at a better time. Goodbye!",
                                                        ctx.get('streamSid')
                                                    )
                                                )
                                            except Exception as _bye_err:
                                                logger.debug(f"[COST SENTINEL] Goodbye synthesis failed (IVR transcript kill): {_bye_err}")
                                            break

                                        # --- CHECK 1: Active Conversation? Leave it alone. ---
                                        # If merchant has spoken recently (<30s) and has REAL meaningful turns, call is healthy
                                        # [FIX] Use _real_turns AND meaningful_turns to avoid false "active" on IVR/noise
                                        if _real_turns >= 2 and meaningful_turns >= 2 and silence_duration < 30.0:
                                            continue  # Call is alive and active

                                        # --- CHECK 2: IVR Time-Based Fallback ---
                                        # If IVR detector has flagged is_ivr but hasn't hit abort threshold,
                                        # use time as the tiebreaker
                                        _ivr_det = ctx.get('_ivr_detector')
                                        if _ivr_det and elapsed > _IVR_TIME_LIMIT:
                                            try:
                                                _ivr_state = _ivr_det.get_state() if hasattr(_ivr_det, 'get_state') else {}
                                                _ivr_score = _ivr_state.get('score', 0) if isinstance(_ivr_state, dict) else 0
                                            except Exception:
                                                _ivr_score = 0
                                            if _ivr_score > 0.15 or ctx.get('_ccnm_ignore'):
                                                logger.warning(
                                                    f"[COST SENTINEL] IVR TIME KILL — {elapsed:.0f}s elapsed, "
                                                    f"IVR score={_ivr_score:.2f}, turns={merchant_turns}. "
                                                    f"Force disconnecting to save cost."
                                                )
                                                # [PHASE 2] FSM: → ENDED (ivr_timeout_kill)
                                                _fsm = ctx.get('_call_fsm')
                                                if _fsm:
                                                    _fsm.end_call(reason='ivr_timeout_kill')
                                                else:
                                                    ctx['stream_ended'] = True
                                                ctx['_evolution_outcome'] = 'ivr_timeout_kill'
                                                ctx['_killed_by'] = 'sentinel'
                                                ctx['_ccnm_ignore'] = True
                                                try:
                                                    abort_msg = "I appreciate your time, but I'll try back at a better time. Goodbye!"
                                                    asyncio.create_task(
                                                        self.synthesize_and_stream_greeting(ws, abort_msg, ctx.get('streamSid'))
                                                    )
                                                except Exception as _bye_err:
                                                    logger.debug(f"[COST SENTINEL] Goodbye synthesis failed (IVR timeout kill): {_bye_err}")
                                                break

                                        # --- CHECK 3: Zero-Turn Timeout ---
                                        # Call has been going on but no merchant has spoken meaningfully
                                        # [FIX] Use meaningful_turns (3+ words) instead of merchant_turns
                                        # to prevent STT noise from creating phantom turns
                                        if meaningful_turns == 0 and elapsed > _ZERO_TURN_LIMIT:
                                            logger.warning(
                                                f"[COST SENTINEL] ZERO-TURN KILL — {elapsed:.0f}s elapsed, "
                                                f"0 meaningful turns (raw={merchant_turns}). Air-call detected. Force disconnect."
                                            )
                                            # [PHASE 2] FSM: → ENDED (air_call_kill)
                                            _fsm = ctx.get('_call_fsm')
                                            if _fsm:
                                                _fsm.end_call(reason='air_call_kill')
                                            else:
                                                ctx['stream_ended'] = True
                                            ctx['_evolution_outcome'] = 'air_call_kill'
                                            ctx['_killed_by'] = 'sentinel'
                                            ctx['_ccnm_ignore'] = True
                                            break

                                        # --- CHECK 4: Air-Call Silence Detection ---
                                        if silence_duration >= _SILENCE_KILL:
                                            logger.warning(
                                                f"[COST SENTINEL] SILENCE KILL — {silence_duration:.0f}s silence. "
                                                f"Force disconnect. elapsed={elapsed:.0f}s, turns={merchant_turns}"
                                            )
                                            # [PHASE 2] FSM: → ENDED (silence_kill)
                                            _fsm = ctx.get('_call_fsm')
                                            if _fsm:
                                                _fsm.end_call(reason='silence_kill')
                                            else:
                                                ctx['stream_ended'] = True
                                            ctx['_evolution_outcome'] = 'silence_kill'
                                            ctx['_killed_by'] = 'sentinel'
                                            ctx['_ccnm_ignore'] = True
                                            try:
                                                asyncio.create_task(
                                                    self.synthesize_and_stream_greeting(
                                                        ws, "I don't seem to be reaching anyone. I'll try again another time. Goodbye!",
                                                        ctx.get('streamSid')
                                                    )
                                                )
                                            except Exception as _bye_err:
                                                logger.debug(f"[COST SENTINEL] Goodbye synthesis failed (silence kill): {_bye_err}")
                                            break
                                        elif silence_duration >= _SILENCE_WARNING and not _sentinel_asked:
                                            logger.info(
                                                f"[COST SENTINEL] SILENCE WARNING — {silence_duration:.0f}s silence. "
                                                f"Alan asking 'Are you still there?'"
                                            )
                                            _sentinel_asked = True
                                            try:
                                                asyncio.create_task(
                                                    self.synthesize_and_stream_greeting(
                                                        ws, "Hello? Are you still there?",
                                                        ctx.get('streamSid')
                                                    )
                                                )
                                            except Exception as _ask_err:
                                                logger.debug(f"[COST SENTINEL] 'Are you still there?' synthesis failed: {_ask_err}")

                                    logger.info(f"[COST SENTINEL] Exiting — stream_ended={ctx.get('stream_ended')}")
                                except asyncio.CancelledError:
                                    logger.info("[COST SENTINEL] Task cancelled (call ended)")
                                except Exception as _cs_err:
                                    logger.error(f"[COST SENTINEL] CRASH — all call protections DISABLED: {_cs_err}", exc_info=True)
                            asyncio.create_task(_cost_sentinel(conversation_context, websocket, str(client_id)))

                            # [ALAN V2] MIP & MTSP Initialization
                            merchant_id = data.get('parameters', {}).get('merchant_id') or stream_sid
                            conversation_context['merchant_id'] = merchant_id
                            
                            # Load Profile
                            try:
                                profile = self.mip.load_profile(merchant_id)
                                # Seed Context
                                mip_context = self.mip.seed_context_from_profile(profile)
                                conversation_context.update(mip_context)
                                conversation_context['merchant_profile'] = profile.dict()
                                
                                # [PERSISTENCE PILLAR] Restore preferences from MIP if returning merchant
                                if mip_context.get('restored_preferences'):
                                    conversation_context['preferences'] = mip_context['restored_preferences']
                                    logger.info(f"[PERSISTENCE] Restored preferences for returning merchant {merchant_id}")
                                
                                # Initialize MTSP Plan
                                plan = self.mtsp.initialize_plan(conversation_context)
                                conversation_context['mtsp_plan'] = plan.dict()
                                
                                logger.info(f"[ALAN V2] Loaded MIP Profile & MTSP Plan for {merchant_id}")
                            except Exception as e:
                                logger.error(f"[ALAN V2] Failed to initialize MIP/MTSP: {e}")

                            # [OPTIMIZATION] Fire Opener IMMEDIATELY upon stream start (don't wait for silence)
                            # This mimics the "hello" reflex and cuts 1.0s latency
                            # [FIX] TEMPORARILY DISABLED to fix "Double Audio" / "Underwater" issues.
                            # Letting smart_greeting_routine handle logic instead.
                            # if not conversation_context.get('greeting_sent'):
                            #      logger.info("⚡ [IMMEDIATE OPENER] Firing Greeting on Stream Start")
                            #      # We simulate a 'trigger_opener' event internally
                            #      start_payload = {
                            #          'type': 'trigger_opener',
                            #          'parameters': data['parameters']
                            #      }
                            #      # We call the handler logic directly or just trigger the synthesis here
                            #      # Let's reuse the existing logic block for trigger_opener below by continuing loop
                            #      # But we need to inject it. 
                            #      
                            #      # Safer: Just call the greeting logic directly here.
                            #      conversation_context['greeting_sent'] = True
                            #      agent = conversation_context['agent_instance']
                            #      prospect_info = conversation_context.get('prospect_info', {}) # Populated by handle_conversation_start
                            #      
                            #      greeting = agent.generate_business_greeting(
                            #         strategy=prospect_info.get('strategy', 'cold_call'),
                            #         prospect_name=prospect_info.get('name'),
                            #         company=prospect_info.get('company'),
                            #         signal_data=prospect_info.get('signal')
                            #      )
                            #      conversation_context['conversation_state'] = 'dialogue'
                            #      conversation_context['first_turn_complete'] = False
                            #      conversation_context['fallback_suppressed_until'] = time.time() + 20.0
                            #      
                            #      logger.info(f"[IMMEDIATE OPENER] Greeting: '{greeting}'")
                            #      asyncio.create_task(self.synthesize_and_stream_greeting(websocket, greeting, conversation_context.get('streamSid')))

                            continue
                            
                        elif event == 'media':
                            if not conversation_context.get('stream_started'):
                                # [FIX] Early media arrived before 'start' event completed
                                # Buffer audio so it's not lost — this handles the race condition
                                # where Twilio starts streaming before handle_conversation_start finishes.
                                _early_buf = conversation_context.get('_early_media_buffer', [])
                                _early_buf.append(data['media']['payload'])
                                conversation_context['_early_media_buffer'] = _early_buf
                                if len(_early_buf) <= 3:  # Only log first few
                                    logger.info(f"[RELAY TIMING] Buffered early media frame ({len(_early_buf)} total)")
                                continue
                            
                            if conversation_context.get('stream_started'):
                                payload = data['media']['payload']
                                
                                # ============================================================
                                # HUMAN PERCEPTION MODEL — Ears + Voice work simultaneously
                                # ============================================================
                                # A human can hear while talking. They detect interrupts,
                                # process background speech, and stop mid-sentence if needed.
                                # HUMAN MODEL: Alan's ears are always on (STT feeds continuously).
                                # VAD runs in two modes based on whether audio is playing:
                                #   LISTENING mode (normal threshold) = standard conversation
                                #   SPEAKING mode (high threshold) = only real interrupts, not echo
                                # If a real interrupt is detected, generation increments and
                                # the pipeline stops gracefully — like a human who hears
                                # someone speaking and stops talking to listen.
                                # ============================================================
                                
                                _current_state = conversation_context.get('conversation_state')
                                _echo_cooldown = 0.8  # seconds — covers Twilio's 400-800ms buffer tail. Was 2.0s which made Alan deaf to fast responses.
                                _responding_ended = conversation_context.get('responding_ended_at', 0)
                                _in_cooldown = (time.time() - _responding_ended) < _echo_cooldown
                                # HUMAN MODEL: "is Alan talking" is a physical fact
                                # (audio frames flowing to Twilio), not a lock state.
                                # [ECHO FIX] Also consider Twilio's playback buffer — we may
                                # have finished sending frames but Twilio is still playing them.
                                # twilio_playback_done is set True when Twilio's mark event arrives.
                                _is_alan_talking = (
                                    _current_state == 'FIRST_GREETING_PENDING' or
                                    conversation_context.get('audio_playing', False) or
                                    (not conversation_context.get('twilio_playback_done', True))  # If False, Twilio still playing
                                )
                                
                                # During echo cooldown: skip everything (brief 300ms window)
                                if _in_cooldown and not _is_alan_talking:
                                    conversation_context['vad_speech_frames'] = 0
                                    continue
                                
                                # 1. Feed the STT Buffer — EARS ALWAYS ON
                                # During Alan's speech, audio contains echo + possible real speech.
                                # We still feed it so genuine interruptions are captured.
                                # The STT buffer is cleared on barge-in to drop echo residue.
                                if not _is_alan_talking:
                                    # Normal mode: always feed STT
                                    await aqi_stt_engine.process_audio_chunk(
                                        conversation_context['streamSid'], 
                                        payload, 
                                        'audio/ulaw'
                                    )
                                
                                # 2. Physics-Based VAD — Dual-Mode (Listening vs Speaking)
                                try:
                                    raw_audio = base64.b64decode(payload)
                                    
                                    # [INBOUND SENSITIZER] Monitor user audio health (Dead Air / Connection Loss)
                                    if INBOUND_SENSITIZER_WIRED and _inbound_sensitizer:
                                        _call_sid_check = conversation_context.get('call_sid', '')
                                        if _call_sid_check:
                                            try:
                                                _in_res = _inbound_sensitizer.process_packet(_call_sid_check, raw_audio)
                                                if _in_res.get('action') == 'trigger_stt_restart':
                                                    # [LOG THROTTLE] Only log once per 5 seconds to avoid flooding
                                                    _dead_air_ms = _in_res.get('reason', '')
                                                    _now_sec = int(time.time())
                                                    _last_dead_air_log = conversation_context.get('_last_dead_air_log', 0)
                                                    if _now_sec - _last_dead_air_log >= 5:
                                                        logger.warning(f"[INBOUND] {_dead_air_ms} - Check STT health")
                                                        conversation_context['_last_dead_air_log'] = _now_sec
                                                    # We don't necessarily clear buffer on dead air, but we track metrics
                                                elif _in_res.get('action') == 'hangup':
                                                    logger.warning(f"[INBOUND] {_in_res.get('reason')} - Force disconnect")
                                                    # [PHASE 2] FSM: → ENDED (inbound_silence)
                                                    _fsm = conversation_context.get('_call_fsm')
                                                    if _fsm:
                                                        _fsm.end_call(reason='inbound_silence')
                                                    else:
                                                        conversation_context['stream_ended'] = True
                                                    conversation_context['_killed_by'] = 'inbound_silence'
                                                    await websocket.close()
                                                    break
                                            except Exception:
                                                pass

                                    pcm_data = audioop.ulaw2lin(raw_audio, 2)
                                    rms = audioop.rms(pcm_data, 2)

                                    # [PHASE 3B] Feed telephony health monitor every frame
                                    _tel_mon = conversation_context.get('_telephony_monitor')
                                    if _tel_mon:
                                        _tel_mon.process_frame(rms)

                                    # [LIVE MONITOR] Voice frequency analysis on every frame
                                    if LIVE_MONITOR_WIRED and _live_monitor:
                                        _call_sid_for_monitor = conversation_context.get('call_sid', '')
                                        if _call_sid_for_monitor:
                                            try:
                                                _voice_analysis = analyze_voice_frame(pcm_data, rms, _is_alan_talking)
                                                _live_monitor.process_frame(_call_sid_for_monitor, _voice_analysis)
                                            except Exception:
                                                pass  # Never let monitoring crash the call
                                    
                                    # VAD Constants — Tuned for Telephony Narrowband (300-3400 Hz)
                                    SPEECH_THRESHOLD = 400      # Normal mode: detect user speech
                                    ECHO_SPEECH_THRESHOLD = 1500  # Speaking mode: only detect REAL interrupts (echo is ~400-600 RMS)
                                    SILENCE_THRESHOLD = 250     # Silence floor
                                    SILENCE_DURATION = 0.55     # Turn commit delay — 550ms. Was 420ms which cut mid-sentence pauses.
                                                                # Human inter-word pauses can be 500-700ms (Stivers et al. 2009).
                                                                # 550ms < 700ms trouble threshold. VAD guard still catches edge cases.
                                    BARGE_IN_CONSECUTIVE_FRAMES = 3   # Normal mode: 60ms sustained
                                    ECHO_BARGE_IN_FRAMES = 5          # Speaking mode: 100ms sustained (more conservative)
                                    
                                    # Select threshold based on whether Alan is talking
                                    active_threshold = ECHO_SPEECH_THRESHOLD if _is_alan_talking else SPEECH_THRESHOLD
                                    active_frames_needed = ECHO_BARGE_IN_FRAMES if _is_alan_talking else BARGE_IN_CONSECUTIVE_FRAMES
                                    
                                    now = time.time()
                                    vad_state = conversation_context.get('vad_state', 'silence')
                                    last_speech_time = conversation_context.get('vad_last_speech', now)
                                    
                                    if rms > active_threshold:
                                        # Track consecutive above-threshold frames
                                        conversation_context['vad_speech_frames'] = conversation_context.get('vad_speech_frames', 0) + 1
                                        
                                        if vad_state == 'silence' and conversation_context['vad_speech_frames'] >= active_frames_needed:
                                             if _is_alan_talking:
                                                 # BARGE-IN DURING ALAN'S SPEECH — User is genuinely interrupting
                                                 # Like a human: stop talking, listen to what they're saying
                                                 logger.info(f"[VAD] BARGE-IN INTERRUPT detected during TTS (RMS: {rms}, sustained {conversation_context['vad_speech_frames']} frames)")
                                                 
                                                 # [PHASE 3B] Record talk-over for telephony health
                                                 _tel_mon = conversation_context.get('_telephony_monitor')
                                                 if _tel_mon:
                                                     _tel_mon.record_talkover()

                                                 # 1. Tell Twilio to stop playing Alan's audio
                                                 barge_in_payload = {
                                                     "event": "clear",
                                                     "streamSid": conversation_context['streamSid']
                                                 }
                                                 asyncio.create_task(self._safe_send(websocket, barge_in_payload))
                                                 logger.info(f"[BARGE-IN] Sent CLEAR command to Twilio (interrupt)")
                                                 
                                                 # 2. Increment generation — running pipeline sees mismatch and stops
                                                 conversation_context['response_generation'] = conversation_context.get('response_generation', 0) + 1
                                                 conversation_context['audio_playing'] = False
                                                 conversation_context['twilio_playback_done'] = True  # Barge-in clears Twilio buffer
                                                 
                                                 # 4. Clear STT buffer (drop echo residue) and start fresh
                                                 aqi_stt_engine.clear_buffer(conversation_context['streamSid'])
                                                 
                                                 # 5. NOW start feeding STT with the interrupt speech
                                                 await aqi_stt_engine.process_audio_chunk(
                                                     conversation_context['streamSid'],
                                                     payload,
                                                     'audio/ulaw'
                                                 )
                                             else:
                                                 # Normal speech start — user speaking after Alan finished
                                                 # Do NOT send CLEAR here — there's no audio to clear.
                                                 # Sending CLEAR on every speech start can cause Twilio
                                                 # buffer hiccups and audio artifacts.
                                                 logger.info(f"[VAD] User Started Speaking (RMS: {rms}, sustained {conversation_context['vad_speech_frames']} frames)")
                                             
                                             conversation_context['vad_state'] = 'speaking'
                                        elif vad_state == 'silence':
                                            # Building speech confidence — not yet enough frames
                                            pass
                                        else:
                                            # Already in speaking state — keep tracking
                                            pass
                                        
                                        conversation_context['vad_last_speech'] = now
                                        
                                    elif rms < SILENCE_THRESHOLD and vad_state == 'speaking':
                                        # Reset speech frame counter when silence detected
                                        conversation_context['vad_speech_frames'] = 0
                                        silence_elapsed = now - last_speech_time
                                        if silence_elapsed > SILENCE_DURATION:
                                            logger.info(f"[VAD] Silence Detected ({silence_elapsed:.2f}s). Committing Turn.")
                                            conversation_context['vad_state'] = 'silence'
                                            
                                            # [2026-03-03] Pause telephony health during LLM processing —
                                            # silence while Alan thinks is expected, not a line problem.
                                            _tel_mon_vad = conversation_context.get('_telephony_monitor')
                                            if _tel_mon_vad and hasattr(_tel_mon_vad, 'pause_during_processing'):
                                                _tel_mon_vad.pause_during_processing()
                                            
                                            # [INSTRUMENT] Stamp VAD end — pipeline clock starts here
                                            conversation_context['_vad_end_mono'] = time.monotonic()
                                            
                                            # TRIGGER THE MODEL
                                            await aqi_stt_engine.finalize_and_clear(conversation_context['streamSid'])
                                    
                                    elif rms <= active_threshold and vad_state == 'silence':
                                        # Below speech threshold while in silence — reset consecutive counter
                                        # Prevents intermittent noise spikes from accumulating
                                        conversation_context['vad_speech_frames'] = 0
                                            
                                    elif vad_state == 'speaking':
                                        # We are in the gap between talking and timeout (keep alive)
                                        pass
                                            
                                except Exception as e:
                                    logger.error(f"VAD Physics Error: {e}")
                                    
                            continue
                            
                        elif event == 'connected':
                            continue
                            
                        elif event == 'stop':
                            logger.info(f"[TWILIO] Stream Stopped")
                            _call_sid = conversation_context.get('call_sid', '')
                            
                            # [INBOUND SENSITIZER] Unregister call
                            if INBOUND_SENSITIZER_WIRED and _inbound_sensitizer and _call_sid:
                                _inbound_sensitizer.unregister_call(_call_sid)
                            
                            # [LIVE MONITOR] Unregister call
                            if LIVE_MONITOR_WIRED and _live_monitor:
                                if _call_sid:
                                    _live_monitor.unregister_call(_call_sid)
                            # [PHASE 2] FSM: → ENDED (stream_stop)
                            _fsm = conversation_context.get('_call_fsm')
                            if _fsm:
                                _fsm.end_call(reason='stream_stop')
                            else:
                                conversation_context['stream_ended'] = True
                            # Increment generation to kill any in-progress pipeline
                            conversation_context['response_generation'] = conversation_context.get('response_generation', 0) + 1
                            
                            # [AQI 0.1mm CHIP] Guard — on_call_end
                            if AQI_GUARD_WIRED and self._aqi_guard and _call_sid:
                                try:
                                    _aqi_fsm_state = _derive_aqi_state(conversation_context)
                                    _aqi_exit = conversation_context.get('_evolution_outcome', 'caller_hangup')
                                    # Build health/telephony trajectories from context
                                    _aqi_health_traj = [conversation_context.get('_organism_health_int', 1)]
                                    _aqi_tel_traj = [conversation_context.get('_telephony_health_state', 'Excellent')]
                                    _aqi_outcome = {
                                        'outcome': _aqi_exit,
                                        'turns': len(conversation_context.get('messages', [])),
                                        'trajectory': conversation_context.get('master_closer_state', {}).get('trajectory'),
                                    }
                                    _aqi_end_violations = self._aqi_guard.on_call_end(
                                        _call_sid, _aqi_fsm_state, _aqi_exit,
                                        _aqi_health_traj, _aqi_tel_traj, _aqi_outcome
                                    )
                                    if _aqi_end_violations:
                                        _fatal_count = sum(1 for v in _aqi_end_violations if v.fatal)
                                        logger.warning(f"[AQI GUARD] Call end: {len(_aqi_end_violations)} violation(s) ({_fatal_count} fatal)")
                                except Exception as _aqi_err:
                                    logger.warning(f"[AQI GUARD] on_call_end failed (non-fatal): {_aqi_err}")
                            
                            # [PHASE 4] Trace Exporter — finalize and write JSONL
                            if PHASE4_EXPORTER_WIRED and self._phase4_exporter and _call_sid:
                                try:
                                    _p4_fsm = _derive_aqi_state(conversation_context)
                                    _p4_exit = conversation_context.get('_evolution_outcome', 'caller_hangup')
                                    _p4_trace = self._phase4_exporter.finalize_trace(_call_sid, {
                                        'fsm_state': _p4_fsm,
                                        'exit_reason': _p4_exit,
                                        'end_time': datetime.now(),
                                        'master_closer_state': conversation_context.get('master_closer_state'),
                                        'evolution_outcome': _p4_exit,
                                        'outcome': {
                                            'outcome': _p4_exit,
                                            'turns': len(conversation_context.get('messages', [])),
                                            'trajectory': conversation_context.get('master_closer_state', {}).get('trajectory'),
                                        },
                                    })
                                    if _p4_trace:
                                        logger.info(f"[PHASE 4 EXPORTER] Trace written: {_call_sid} | "
                                                    f"turns={len(_p4_trace.get('turns', []))} exit={_p4_exit}")
                                        
                                        # [PHASE 5 REFLEX ARC] Feed Phase 4 trace into Phase 5 behavioral analyzer
                                        # This is THE missing connection: Phase4 → Phase5 → behavioral profiles → CCNM → next call
                                        if PHASE5_ANALYZER_WIRED and _phase5_analyzer:
                                            try:
                                                _p5_profile = _phase5_analyzer.on_call_complete(_p4_trace)
                                                if _p5_profile and not _p5_profile.get('error'):
                                                    _end_payload['phase5_profile'] = _p5_profile
                                                    logger.info(f"[PHASE 5] Behavioral profile generated: "
                                                                f"calls_analyzed={_phase5_analyzer.calls_analyzed}")
                                                elif _p5_profile and _p5_profile.get('error'):
                                                    logger.warning(f"[PHASE 5] Profile error: {_p5_profile.get('error')}")
                                            except Exception as _p5_err:
                                                logger.warning(f"[PHASE 5] Analysis failed (non-fatal): {_p5_err}")
                                        
                                except Exception as _p4_err:
                                    logger.warning(f"[PHASE 4 EXPORTER] on_call_end failed (non-fatal): {_p4_err}")
                            
                            # [EVOLUTION] Trigger Final Outcome Detection and Evolutionary Nudge
                            try:
                                # [CCNM QUARANTINE] Skip evolution learning for IVR calls
                                if conversation_context.get('_ccnm_ignore'):
                                    logger.info("[EVOLUTION] SKIPPED — IVR call quarantined from learning")
                                    conversation_context['_evolution_outcome'] = conversation_context.get('_evolution_outcome', 'ivr_system')
                                    conversation_context['_evolution_confidence'] = conversation_context.get('_evolution_confidence', 0.0)
                                    conversation_context['_evolution_band'] = 'quarantined'
                                    conversation_context['_evolution_engagement'] = 0.0
                                else:
                                    full_transcript = " ".join([m.get("user", "") + " " + m.get("alan", "") for m in conversation_context.get("messages", [])])
                                    duration = (datetime.now() - conversation_context['start_time']).total_seconds()
                                
                                    # Gather signals (Determined during call or estimated from stats)
                                    call_signals = {
                                        "TPS": 1 if len(conversation_context.get("messages", [])) > 2 else 0,
                                        "RLS": 1 if conversation_context.get("master_closer_state", {}).get("trajectory") == "warming" else 0,
                                        "ULS": 0, # Should be set if keyword detected or link sent
                                        "TDS": 1 if duration > 180 else 0,
                                        "OSS": 1 if conversation_context.get("master_closer_state", {}).get("endgame_state") == "ready" else 0
                                    }

                                    # Detect Outcome with Confidence
                                    metadata = {"duration": duration, "disconnected_by": "user"}
                                    outcome, matched, total = self.odl.detect_with_match_stats(full_transcript, metadata, call_signals)
                                    engagement_score = self.odl.calculate_engagement_score(call_signals)
                                    
                                    # [FIX] POST-ODL IVR OVERRIDE
                                    # ODL classifies any call >120s as "kept_engaged" based on duration alone.
                                    # This poisons the learning loop when Alan was talking to an IVR/voicemail.
                                    # If IVR detector has ANY signal (score > 0.25) or many IVR phrases in
                                    # transcript, override "kept_engaged" to the correct IVR outcome.
                                    if outcome == "kept_engaged":
                                        _ivr_det = conversation_context.get('_ivr_detector')
                                        _ivr_override = False
                                        _ivr_override_reason = ""
                                        
                                        # Check 1: IVR detector had partial detection
                                        if _ivr_det:
                                            try:
                                                _det_state = _ivr_det.get_state()
                                                if _det_state.get('score', 0) > 0.25:
                                                    _ivr_override = True
                                                    _ivr_override_reason = f"IVR score={_det_state['score']:.2f}"
                                                elif _det_state.get('lifetime_keyphrase_hits', 0) >= 2:
                                                    _ivr_override = True
                                                    _ivr_override_reason = f"lifetime_keyphrase_hits={_det_state['lifetime_keyphrase_hits']}"
                                            except Exception as _ivr_err:
                                                logger.debug(f"[IVR] Detector state check failed: {_ivr_err}")
                                        
                                        # Check 2: Transcript contains IVR phrases
                                        if not _ivr_override:
                                            _ivr_check_phrases = ['press one', 'press two', 'press three',
                                                                   'leave a message', 'after the tone',
                                                                   'after the beep', 'please hold',
                                                                   'business hours', 'para espanol',
                                                                   'press pound', 'press star']
                                            _ivr_phrase_count = sum(1 for p in _ivr_check_phrases if p in full_transcript.lower())
                                            if _ivr_phrase_count >= 2:
                                                _ivr_override = True
                                                _ivr_override_reason = f"transcript_ivr_phrases={_ivr_phrase_count}"
                                        
                                        if _ivr_override:
                                            _old_outcome = outcome
                                            outcome = _ivr_det.get_outcome_label() if _ivr_det else "voicemail_ivr"
                                            if outcome == "unknown":
                                                outcome = "voicemail_ivr"
                                            conversation_context['_ccnm_ignore'] = True  # Quarantine from learning
                                            logger.warning(
                                                f"[EVOLUTION] IVR OVERRIDE — ODL said '{_old_outcome}' but "
                                                f"{_ivr_override_reason}. Overriding to '{outcome}'. CCNM quarantined."
                                            )
                                    
                                    # Derive objection type clarity for confidence
                                    objection_type = "none"
                                    if 'call_memory' in conversation_context:
                                        objs = conversation_context['call_memory'].get('objections', [])
                                        if objs:
                                            if any(o.get('strength', 0) > 3 for o in objs): objection_type = "hard"
                                            elif len(objs) > 2: objection_type = "mixed"
                                            else: objection_type = "soft"

                                    # Confidence Scoring Context
                                    coc_context = {
                                        "rule_matched_conditions": matched,
                                        "rule_total_conditions": total,
                                        "engagement_score": engagement_score,
                                        "trajectory_switches": conversation_context.get('master_closer_state', {}).get('switches', 0),
                                        "turn_count": len(conversation_context.get("messages", [])),
                                        "objection_type": objection_type,
                                        "hangup": True if (metadata.get("disconnected_by") == "user" and duration < 30) else False
                                    }
                                    
                                    confidence = self.cocs.score(coc_context)
                                    band = self.cocs.classify_band(confidence)

                                    logger.info(f"[EVOLUTION] Call Closed. Outcome: {outcome}, Confidence: {confidence:.2f} ({band}), Engagement: {engagement_score}/10")
                                    
                                    # [FIX] Store evolution results in conversation_context so
                                    # the finally block can include them in _end_payload.
                                    # Previously these were local variables that went out of scope.
                                    conversation_context['_evolution_outcome'] = outcome
                                    conversation_context['_evolution_confidence'] = confidence
                                    conversation_context['_evolution_band'] = band
                                    conversation_context['_evolution_engagement'] = engagement_score
                                    
                                    # Apply Call Result with Confidence (Micro-Learning)
                                    call_summary = {
                                        "outcome": outcome,
                                        "engagement_score": engagement_score,
                                        "outcome_confidence": confidence,
                                        "outcome_confidence_band": band
                                    }
                                    
                                    self.evolution.apply_call_result_with_confidence(call_summary)

                                    # [OUTCOME ATTRIBUTION]
                                    call_context = {
                                        "stable_archetype": coc_context["trajectory_switches"] == 0,
                                        "archetype_flip": coc_context["trajectory_switches"] > 2,
                                        "engagement_high": engagement_score >= 6,
                                        "engagement_low": engagement_score < 3,
                                        "warming": call_signals["RLS"] == 1,
                                        "stable": coc_context["trajectory_switches"] <= 1,
                                        "cooling": call_signals["RLS"] == 0 and "soft_decline" in outcome,
                                        "escalating": outcome == "hard_decline",
                                        "soft_to_positive": outcome == "statement_obtained" and objection_type == "soft",
                                        "soft_to_neutral": outcome == "kept_engaged" and objection_type == "soft",
                                        "hard_to_negative": outcome == "hard_decline" and objection_type == "hard",
                                        "ignored_objection": objection_type == "none" and len(conversation_context.get("messages", [])) > 5,
                                        "bias_match": conversation_context.get('behavior_profile', {}).get('closing_bias') is not None if isinstance(conversation_context.get('behavior_profile'), dict) else False,
                                        "bias_mismatch": (conversation_context.get('behavior_profile', {}).get('closing_bias') is None if isinstance(conversation_context.get('behavior_profile'), dict) else True) and objection_type != "none",
                                        "high_novelty_positive": False,  # reasoning_block is str, not dict
                                        "high_novelty_negative": False,
                                        "low_novelty_positive": outcome in ["statement_obtained", "kept_engaged"],
                                        "low_novelty_negative": outcome in ["hard_decline", "hangup"]
                                    }

                                    attribution = self.attribution_engine.attribute(call_context)
                                    logger.info(f"[ATTRIBUTION] Dimensions Scored: {attribution}")

                                    # [CAPTURE] Record evolution event with full outcome data
                                    if CALL_CAPTURE_WIRED:
                                        try:
                                            _cdc_evolution(
                                                conversation_context.get('call_sid', str(client_id)),
                                                outcome, confidence, band, engagement_score,
                                                nudge=json.dumps(call_summary),
                                                attribution=json.dumps(attribution) if isinstance(attribution, dict) else str(attribution),
                                            )
                                        except Exception as _cdc_evo_err:
                                            logger.debug(f"[CDC] Evolution event capture failed: {_cdc_evo_err}")

                                    if self.attribution_engine.should_review():
                                        logger.info("[PERIODIC REVIEW] Review Cycle Triggered.")
                                        # Perform Periodic Review Protocol (PRP)
                                        # 1. Load window (Actually, attribution_engine logs these)
                                        # For this relay we simulate the review by processing the log or recent buffer
                                        # In production, this would be a separate asynchronous maintenance task.
                                        
                                        # Aggregation Check
                                        if self.aggregation_engine.should_aggregate():
                                            logger.info("[AGGREGATION] Macrobrain Aggregation Triggered.")
                                            aggregation = self.aggregation_engine.aggregate()
                                            logger.info(f"[AGGREGATION] Guidance: {aggregation['final_dimension_guidance']}")

                            except Exception as evo_err:
                                logger.error(f"[EVOLUTION] Post-Call Analysis Failed: {evo_err}")

                            aqi_stt_engine.close_stt_session(conversation_context.get('streamSid'))
                            break
                        
                        elif event == 'mark':
                            # [ECHO FIX] Track Twilio playback completion via mark events
                            # Twilio sends mark back ONLY when audio preceding the mark 
                            # has actually been PLAYED to the caller. This is the ground 
                            # truth for "Alan stopped talking" — NOT when we finished 
                            # sending frames (which can be 1-3s earlier).
                            mark_name = data.get('mark', {}).get('name', '')
                            if mark_name in ('turn_complete', 'greeting_complete'):
                                conversation_context['twilio_playback_done'] = True
                                conversation_context['responding_ended_at'] = time.time()
                                # [2026-03-03] Resume telephony health monitoring now that
                                # Alan's response has finished playing — real silence from
                                # here means actual line problems, not LLM processing gaps.
                                _tel_mon_mark = conversation_context.get('_telephony_monitor')
                                if _tel_mon_mark and hasattr(_tel_mon_mark, 'resume_after_processing'):
                                    _tel_mon_mark.resume_after_processing()
                                logger.info(f"[TWILIO] Mark '{mark_name}' received — playback confirmed complete")
                            continue
                    
                    msg_type = data.get('type', 'unknown')
                    # logger.info(f"📥 Received: {msg_type}") # Too noisy?
                    
                    response = None # Default to no response

                    # Handle different message types
                    if msg_type == 'conversation_initiation':
                        logger.info(f"[TRACE] Init received")
                        response = await self.handle_conversation_start(data, conversation_context, websocket)

                    elif msg_type == 'user_speech':
                        # [DISABLED] This path was for ConversationRelay STT.
                        # We use Media Streams + custom VAD + Whisper STT instead.
                        # Having both paths active caused DUPLICATE LLM responses
                        # with different tones playing simultaneously.
                        logger.info(f"[BLOCKED] Ignoring user_speech WebSocket message (using custom VAD/STT pipeline)")
                        pass

                    elif msg_type == 'dtmf':
                        response = await self.handle_dtmf(data, conversation_context)

                    elif msg_type == 'trigger_opener':
                        logger.info(f"[TRACE] TRIGGER OPENER received (Warm-Wire)")
                        # Force Greeting Immediate
                        # We must cancel the smart_greeting_routine if it's running?
                        # Or just set greeting_sent=True and fire.
                        # Since smart_greeting_routine checks context.get('greeting_sent'), setting it here handles race conditions.
                        
                        if not conversation_context.get('greeting_sent'):
                             # [PHASE 2] FSM: FAST_START (skip greeting states, go to dialogue)
                             _fsm = conversation_context.get('_call_fsm')
                             if _fsm:
                                 _fsm.handle_event(CallFlowEvent.FAST_START)
                             else:
                                 conversation_context['greeting_sent'] = True
                                 conversation_context['conversation_state'] = 'dialogue'
                                 conversation_context['first_turn_complete'] = False
                                 conversation_context['fallback_suppressed_until'] = time.time() + 20.0
                             
                             agent = conversation_context['agent_instance']
                             prospect = conversation_context.get('prospect_info', {})
                             greeting = agent.generate_business_greeting(
                                strategy=prospect.get('strategy', 'cold_call'),
                                prospect_name=prospect.get('name'),
                                company=prospect.get('company'),
                                signal_data=prospect.get('signal')
                             )
                             # [PHASE 2] Old flag writes removed — FSM FAST_START above handles all state
                             
                             logger.info(f"[TRIGGER OPENER] Firing Immediate Greeting: '{greeting}'")
                             
                             # Fire Synthesis Task
                             asyncio.create_task(self.synthesize_and_stream_greeting(websocket, greeting, conversation_context.get('streamSid')))

                    # [NEW] Handle 'ready' event to signify initialization complete
                    elif msg_type == 'ready':
                        logger.info(f"[TRACE] Ready signal received")
                        # You can add logic here if needed

                    else:
                        # Unknown message type
                        # response = {
                        #     'type': 'error',
                        #     'message': 'Unknown message type'
                        # }
                        pass # Ignore unknown message types to prevent noise

                    # Send response if one exists
                    if response:
                        await self._safe_send(websocket, response)
                        logger.info(f"📤 Sent response: {response.get('type', 'unknown')}")

                except json.JSONDecodeError:
                    logger.error("❌ Invalid JSON received")
                    await self._safe_send(websocket, {
                        'type': 'error',
                        'message': 'Invalid JSON'
                    })

                except Exception as e:
                    logger.error(f"❌ Error processing message: {e}")
                    await self._safe_send(websocket, {
                        'type': 'error',
                        'message': 'Internal server error'
                    })

        except ConnectionClosed:
            logger.info(f"📞 Connection closed: {client_id}")

        finally:
            # [ORGAN] Hook 8 — Call End
            if CALL_MONITOR_WIRED:
                monitor_call_end(conversation_context.get('call_sid', str(client_id)))

            # [NFC] Emit organism trace at call end — the clinical artifact
            if NFC_WIRED:
                try:
                    _nfc_inst = conversation_context.get('_nfc')
                    if _nfc_inst and _nfc_inst._turn_count > 0:
                        _trace_text = _nfc_inst.render_trace_text()
                        logger.info(f"\n{_trace_text}")
                except Exception as _nfc_err:
                    logger.warning(f"[NFC] Trace render failed (non-fatal): {_nfc_err}")

            # [ORGAN 24] Collect retrieval stats at call end
            if RETRIEVAL_CORTEX_WIRED:
                try:
                    _rc = conversation_context.get('_retrieval_cortex')
                    if _rc:
                        _rc_stats = _rc.end_call()
                        logger.info(f"[ORGAN 24] Call stats: {_rc_stats['retrievals']} retrievals, "
                                   f"{_rc_stats['cache_hits']} cached")
                except Exception as _rc_end_err:
                    logger.debug(f"[ORGAN 24] End-call stats failed: {_rc_end_err}")

            # [ORGAN 34] Log competitive intel summary at call end
            if COMPETITIVE_INTEL_WIRED:
                _ci_detections = conversation_context.get('_competitor_detections', [])
                if _ci_detections:
                    _ci_names = list(set(d['competitor'] for d in _ci_detections))
                    logger.info(f"[ORGAN 34] Call intel: {len(_ci_detections)} competitor mentions — {', '.join(_ci_names)}")

            # [ORGAN 30] Collect prosody analysis stats at call end
            if PROSODY_ANALYSIS_WIRED:
                try:
                    _pa = conversation_context.get('_prosody_analysis')
                    if _pa:
                        _pa_stats = _pa.end_call()
                        _pa_trend = _pa_stats.get('trend', {})
                        logger.info(f"[ORGAN 30] Call stats: {_pa_stats['total_frames']} frames — "
                                   f"dominant: {_pa_trend.get('dominant_emotion', 'n/a')}, "
                                   f"urgency: {_pa_trend.get('urgency_trend', 'n/a')}")
                except Exception as _pa_end_err:
                    logger.debug(f"[ORGAN 30] End-call stats failed: {_pa_end_err}")

            # [ORGAN 31] Post-call clustering + learning summary
            if OBJECTION_LEARNING_WIRED and _objection_learning_organ:
                try:
                    _obj_events = conversation_context.get('_objection_events', [])
                    _obj_turns = conversation_context.get('_objection_turns', 0)
                    # Run clustering to discover/promote new patterns
                    _newly_promoted = _objection_learning_organ.cluster_and_promote()
                    _ol_status = _objection_learning_organ.get_status()
                    logger.info(
                        f"[ORGAN 31] Call learning summary: "
                        f"{len(_obj_events)} objection events across {_obj_turns} turns | "
                        f"newly promoted: {len(_newly_promoted)} | "
                        f"total candidates: {_ol_status['candidates']} | "
                        f"total promoted: {_ol_status['promoted']} | "
                        f"review queue: {_ol_status['review_queue']}"
                    )
                    if _newly_promoted:
                        for _np in _newly_promoted:
                            logger.info(f"[ORGAN 31] NEW PATTERN PROMOTED: '{_np['pattern']}' "
                                       f"(support={_np['support']}, conf={_np['confidence']:.2f})")
                except Exception as _ol_end_err:
                    logger.debug(f"[ORGAN 31] Post-call clustering failed: {_ol_end_err}")

            # [ORGAN 32] Generate structured call summary at call end
            if SUMMARIZATION_WIRED and conversation_context.get('_summary_state') == 'collecting':
                try:
                    _t_sum = time.time()
                    _sum_organ = conversation_context.get('_summarization_organ')
                    if _sum_organ:
                        _pi = conversation_context.get('prospect_info', {})
                        _sum_outcome = conversation_context.get('_evolution_outcome', 'unknown')
                        _sum_result = _sum_organ.generate_summary(
                            merchant_name=_pi.get('name', _pi.get('company', '')),
                            merchant_email=_pi.get('email', ''),
                            merchant_phone=_pi.get('phone', _pi.get('prospect_phone', '')),
                            business_name=_pi.get('company', _pi.get('business', '')),
                            current_processor=_pi.get('current_processor', ''),
                            outcome=_sum_outcome,
                        )
                        _sum_stats = _sum_organ.end_call()
                        conversation_context['_summary_state'] = 'complete'
                        conversation_context['_call_summary'] = _sum_result
                        _sum_ms = 1000 * (time.time() - _t_sum)
                        logger.info(
                            f"[ORGAN 32] Call summary generated: "
                            f"outcome={_sum_outcome} | "
                            f"interest={_sum_result.get('expressed_interest_level', 'n/a')} | "
                            f"readiness={_sum_result.get('deal_readiness_score', 0)} | "
                            f"turns={_sum_stats.get('transcript_turns', 0)} | "
                            f"summary_generated={_sum_stats.get('summary_generated', False)} | "
                            f"{_sum_ms:.1f}ms"
                        )
                except Exception as _sum_end_err:
                    conversation_context['_summary_state'] = 'inactive'
                    logger.debug(f"[ORGAN 32] Summary generation failed: {_sum_end_err}")

            # [ORGAN 33] Push call summary to CRM at call end
            if CRM_INTEGRATION_WIRED and conversation_context.get('_summary_state') == 'complete':
                try:
                    _t_crm = time.time()
                    _crm_organ = conversation_context.get('_crm_organ')
                    _call_summary = conversation_context.get('_call_summary')
                    if _crm_organ and _call_summary:
                        # Enrich payload with additional call context
                        _crm_summary = dict(_call_summary)
                        _crm_summary['objection_events_detail'] = conversation_context.get('_objection_events', [])
                        _crm_summary['competitor_detections'] = conversation_context.get('_competitor_detections', [])
                        _crm_summary['calendar_booking'] = conversation_context.get('_calendar_booking')
                        _crm_summary['outbound_sends'] = conversation_context.get('_outbound_sends', [])
                        _crm_summary['handoff_state'] = conversation_context.get('_handoff_state', 'inactive')
                        _mc_state = conversation_context.get('master_closer_state', {})
                        _crm_summary['deal_stage'] = _mc_state.get('endgame_state', 'not_ready')
                        _crm_summary['trajectory'] = _mc_state.get('trajectory', 'neutral')
                        _crm_summary['temperature'] = _mc_state.get('temperature', 50)

                        _crm_result = _crm_organ.push_summary(_crm_summary)
                        _crm_stats = _crm_organ.end_call()
                        conversation_context['_crm_push_state'] = _crm_result.get('status', 'failed')
                        conversation_context['_crm_push_result'] = _crm_result
                        _crm_ms = 1000 * (time.time() - _t_crm)
                        logger.info(
                            f"[ORGAN 33] CRM push: "
                            f"status={_crm_result.get('status')} | "
                            f"retries={_crm_result.get('retries', 0)} | "
                            f"email_missing={_crm_result.get('email_missing', False)} | "
                            f"queue_depth={_crm_stats.get('queue_depth', 0)} | "
                            f"{_crm_ms:.1f}ms"
                        )
                except Exception as _crm_end_err:
                    conversation_context['_crm_push_state'] = 'failed'
                    logger.debug(f"[ORGAN 33] CRM push failed: {_crm_end_err}")

            # [ORGAN 35] Collect IQ budget stats at call end
            if IQ_BUDGET_WIRED:
                try:
                    _iq_organ_end = conversation_context.get('_iq_budget_organ')
                    if _iq_organ_end:
                        _iq_report = _iq_organ_end.end_call()
                        conversation_context['_iq_state'] = _iq_report.get('burn_state', 'normal')
                        conversation_context['_iq_budget_report'] = _iq_report
                        logger.info(
                            f"[ORGAN 35] Call budget report: "
                            f"spent={_iq_report.get('total_spent', 0)}/{_iq_report.get('budget', 0)} | "
                            f"burn={_iq_report.get('burn_pct', 0)}% | "
                            f"state={_iq_report.get('burn_state', 'normal')} | "
                            f"turns={_iq_report.get('turns', 0)} | "
                            f"avg/turn={_iq_report.get('avg_spend_per_turn', 0)} | "
                            f"scarcity_events={_iq_report.get('scarcity_events', 0)} | "
                            f"fallback={_iq_report.get('fallback_active', False)}"
                        )
                except Exception as _iq_end_err:
                    logger.debug(f"[ORGAN 35] Budget report failed: {_iq_end_err}")

            # [ORGAN 29] Collect inbound context stats at call end
            if INBOUND_CONTEXT_WIRED:
                try:
                    _ic_organ = conversation_context.get('_inbound_context_organ')
                    if _ic_organ:
                        _ic_stats = _ic_organ.end_call()
                        _ic_state_end = conversation_context.get('_inbound_context_state', 'cold')
                        logger.info(
                            f"[ORGAN 29] Call inbound context summary: "
                            f"state={_ic_state_end} | "
                            f"context_injected={_ic_stats.get('context_injected', False)} | "
                            f"context_type={_ic_stats.get('context_type', 'none')}"
                        )
                except Exception as _ic_end_err:
                    logger.debug(f"[ORGAN 29] End-call stats failed: {_ic_end_err}")

            # [ORGAN 28] Collect calendar stats at call end
            if CALENDAR_ENGINE_WIRED:
                try:
                    _cal = conversation_context.get('_calendar_organ')
                    if _cal:
                        _cal_stats = _cal.end_call()
                        _cal_state_end = conversation_context.get('_calendar_state', 'inactive')
                        _cal_booking = conversation_context.get('_calendar_booking')
                        logger.info(
                            f"[ORGAN 28] Call calendar summary: "
                            f"state={_cal_state_end} | "
                            f"bookings_made={_cal_stats.get('bookings_made', 0)} | "
                            f"pending_abandoned={_cal_stats.get('pending_abandoned', False)} | "
                            f"booking_id={(_cal_booking or {}).get('booking_id', 'none')}"
                        )
                except Exception as _cal_end_err:
                    logger.debug(f"[ORGAN 28] End-call stats failed: {_cal_end_err}")

            # [ORGAN 27] Collect language switch stats at call end
            if LANGUAGE_SWITCH_WIRED:
                try:
                    _ls = conversation_context.get('_language_organ')
                    if _ls:
                        _ls_stats = _ls.end_call()
                        _ls_final = conversation_context.get('_language_state', 'en')
                        _ls_switch_st = conversation_context.get('_language_switch_state', 'inactive')
                        logger.info(
                            f"[ORGAN 27] Call language summary: "
                            f"final={_ls_final} | detected={_ls_stats.get('detected_language', 'none')} | "
                            f"confidence={_ls_stats.get('detection_confidence', 0):.2f} | "
                            f"switches={_ls_stats.get('switches', 0)} | state={_ls_switch_st}"
                        )
                except Exception as _ls_end_err:
                    logger.debug(f"[ORGAN 27] End-call stats failed: {_ls_end_err}")

            # [ORGAN 26] Collect outbound comms stats at call end
            if OUTBOUND_COMMS_WIRED:
                try:
                    _oc = conversation_context.get('_outbound_comms')
                    if _oc:
                        _oc_stats = _oc.end_call()
                        _oc_sends = conversation_context.get('_outbound_sends', [])
                        _oc_pending = conversation_context.get('_outbound_pending')
                        logger.info(
                            f"[ORGAN 26] Call comms summary: "
                            f"messages_sent={_oc_stats.get('messages_sent', 0)} | "
                            f"pending={_oc_pending is not None} | "
                            f"channels={set(s.get('channel', '?') for s in _oc_sends) or 'none'}"
                        )
                except Exception as _oc_end_err:
                    logger.debug(f"[ORGAN 26] End-call stats failed: {_oc_end_err}")

            # [ORGAN 25] Collect warm handoff stats at call end
            if WARM_HANDOFF_WIRED:
                try:
                    _ho = conversation_context.get('_handoff_organ')
                    if _ho:
                        _ho_stats = _ho.end_call()
                        _ho_state = conversation_context.get('_handoff_state', 'inactive')
                        _ho_reason = conversation_context.get('_handoff_reason')
                        _ho_result = conversation_context.get('_handoff_result', {})
                        logger.info(
                            f"[ORGAN 25] Call handoff summary: "
                            f"state={_ho_state} | reason={_ho_reason or 'none'} | "
                            f"attempts={_ho_stats.get('handoffs_attempted', 0)} | "
                            f"consent={_ho_stats.get('consent_given', False)} | "
                            f"closer={_ho_result.get('closer', 'N/A')}"
                        )
                except Exception as _ho_end_err:
                    logger.debug(f"[ORGAN 25] End-call stats failed: {_ho_end_err}")
            
            # [CAPTURE] Record comprehensive call end data — fire-and-forget
            if CALL_CAPTURE_WIRED:
                try:
                    # [CONV INTEL] Short-Call Outcome Fallback — eliminate "unknown"
                    if CONV_INTEL_WIRED:
                        _current_outcome = conversation_context.get('_evolution_outcome', 'unknown')
                        _reclassified = ShortCallOutcomeFallback.reclassify(_current_outcome, conversation_context)
                        if _reclassified != _current_outcome:
                            logger.info(f"[CONV INTEL] Outcome reclassified: '{_current_outcome}' → '{_reclassified}'")
                            conversation_context['_evolution_outcome'] = _reclassified
                    
                    _mc_final = conversation_context.get('master_closer_state', {})
                    _sig_eff = conversation_context.get('_effective_signature')
                    _end_payload = {
                        'final_trajectory': _mc_final.get('trajectory', 'neutral'),
                        'final_temperature': _mc_final.get('temperature', 50),
                        'final_confidence_score': _mc_final.get('confidence_score', 50),
                        'final_endgame': _mc_final.get('endgame_state', 'not_ready'),
                        'final_merchant_type': _mc_final.get('merchant_type', 'unknown'),
                        'error_count': conversation_context.get('error_count', 0),
                    }
                    if _sig_eff:
                        _end_payload['signature_speed_bias'] = getattr(_sig_eff, 'speed_bias', None)
                        _end_payload['signature_silence_bias'] = getattr(_sig_eff, 'silence_bias_frames', None)
                        _end_payload['signature_breath_bias'] = getattr(_sig_eff, 'breath_prob_bias', None)
                        _end_payload['signature_caller_influence'] = getattr(_sig_eff, 'caller_influence_pct', None)
                    _bp_final = conversation_context.get('behavior_profile', {})
                    _end_payload['deep_layer_final_mode'] = _bp_final.get('deep_layer_mode') if isinstance(_bp_final, dict) else None
                    _end_payload['deep_layer_final_strategy'] = _bp_final.get('deep_layer_strategy') if isinstance(_bp_final, dict) else None
                    # [FIX] Include evolution outcome data — previously missing, causing final_outcome="unknown"
                    _end_payload['final_outcome'] = conversation_context.get('_evolution_outcome', 'unknown')
                    _end_payload['outcome_confidence'] = conversation_context.get('_evolution_confidence', 0.0)
                    _end_payload['outcome_band'] = conversation_context.get('_evolution_band', 'unknown')
                    _end_payload['engagement_score'] = conversation_context.get('_evolution_engagement', 0.0)
                    # [CCNM QUARANTINE] Mark IVR calls for downstream systems
                    _end_payload['ccnm_ignore'] = conversation_context.get('_ccnm_ignore', False)
                    # [CW23] Unfit context for training set
                    _end_payload['unfit_context'] = conversation_context.get('_unfit_context')
                    # [PHASE 1] Tag sentinel-killed and system-abort calls
                    _killed_by = conversation_context.get('_killed_by')
                    if _killed_by:
                        _end_payload['killed_by'] = _killed_by
                    # System abort: calls killed by server restart (end_time=None in CDC)
                    if conversation_context.get('_system_abort'):
                        _end_payload['final_outcome'] = 'system_abort'
                        _end_payload['killed_by'] = 'infrastructure'
                    
                    # [PHASE 1] Human override — prevent misclassification of real conversations
                    # If merchant spoke 40+ words across 3+ turns, this is human, not IVR
                    _msgs = conversation_context.get('messages', [])
                    _total_merchant_words = sum(len((m.get('user', '') or '').split()) for m in _msgs)
                    _total_turns = sum(1 for m in _msgs if (m.get('user', '') or '').strip())
                    _current_outcome = _end_payload.get('final_outcome', 'unknown')
                    _sentinel_outcomes = {'voicemail_ivr', 'ivr_transcript_kill', 'ivr_timeout_kill',
                                          'silence_kill', 'air_call_kill', 'max_duration_kill'}
                    if (_total_merchant_words >= 40 and _total_turns >= 3
                            and _current_outcome in _sentinel_outcomes):
                        logger.info(
                            f"[HUMAN OVERRIDE] Reclassifying '{_current_outcome}' → 'kept_engaged' "
                            f"(words={_total_merchant_words}, turns={_total_turns})"
                        )
                        _end_payload['final_outcome'] = 'kept_engaged'
                        _end_payload['ccnm_ignore'] = False
                        _end_payload['_human_override'] = True
                    
                    # [CLASSIFIER] Run call-type fusion classifier
                    if CLASSIFIER_WIRED:
                        try:
                            # Hot-reload config if YAML changed
                            _clf_cfg_fresh = _clf_config_loader.get()
                            if _clf_cfg_fresh:
                                _call_type_classifier.reload_config(_clf_cfg_fresh)
                            
                            # Build a CDC-like record for the classifier
                            _clf_record = {
                                'merchant_words': _end_payload.get('merchant_words') or _total_merchant_words,
                                'alan_words': _end_payload.get('alan_words', 0),
                                'total_turns': _end_payload.get('total_turns') or _total_turns,
                                'duration_seconds': _end_payload.get('duration_seconds', 0),
                                'final_outcome': _end_payload.get('final_outcome', 'unknown'),
                                'coaching_weaknesses': '',
                            }
                            _clf_result = _call_type_classifier.classify_from_cdc(_clf_record)
                            
                            # Merge classifier results into end_payload
                            _end_payload['call_type'] = _clf_result['call_type']
                            _end_payload['call_type_confidence'] = _clf_result['confidence']
                            _end_payload['call_type_raw_scores'] = _clf_result['raw_scores']
                            _end_payload['call_type_probabilities'] = _clf_result['probabilities']
                            _end_payload['call_type_override_flags'] = _clf_result['override_flags']
                            _end_payload['call_type_reasoning'] = _clf_result.get('reasoning', '')
                            
                            logger.info(
                                f"[CLASSIFIER] call_type={_clf_result['call_type']} "
                                f"conf={_clf_result['confidence']:.3f} "
                                f"overrides={_clf_result['override_flags']}"
                            )
                        except Exception as _clf_err:
                            logger.debug(f"[CLASSIFIER] Classification failed: {_clf_err}")
                    
                    # [VOICE SENSITIZER] Post-call voice integrity summary
                    if VOICE_SENSITIZER_WIRED and _voice_sensitizer:
                        try:
                            _vs_summary = _voice_sensitizer.analyze_call(
                                conversation_context.get('call_sid', str(client_id))
                            )
                            _end_payload['voice_avg_drift'] = _vs_summary.get('avg_drift', 0.0)
                            _end_payload['voice_max_drift'] = _vs_summary.get('max_drift', 0.0)
                            import json as _json_vs
                            _end_payload['voice_integrity'] = _json_vs.dumps(_vs_summary)
                            logger.info(
                                f"[VOICE-SENS] avg_drift={_vs_summary['avg_drift']:.4f} "
                                f"max_drift={_vs_summary['max_drift']:.4f} "
                                f"events={_vs_summary['drift_event_count']} "
                                f"prosody_flags={_vs_summary['prosody_flag_count']}"
                            )
                            # Reset for next call
                            _voice_sensitizer.reset_call()
                        except Exception as _vs_err:
                            logger.debug(f"[VOICE-SENS] Summary failed: {_vs_err}")

                    # [PERCEPTION FUSION] Compute final snapshot
                    if 'perception_engine' in conversation_context:
                        try:
                            _p_eng = conversation_context['perception_engine']
                            # Gather inputs from Sensitizers
                            _inb = {}
                            if INBOUND_SENSITIZER_WIRED and _inbound_sensitizer:
                                _inb = _inbound_sensitizer.get_stats(conversation_context.get('call_sid', str(client_id)))
                            
                            # Get Voice Sensitizer stats from local scope if available
                            _vs_drift = 0.0
                            if '_vs_summary' in locals() and isinstance(_vs_summary, dict):
                                _vs_drift = _vs_summary.get('avg_drift', 0.0)
                            
                            # Get Classifier scores from local scope if available
                            _ivr_score = 0.0
                            _vm_score = 0.0
                            if '_clf_result' in locals() and isinstance(_clf_result, dict):
                                _probs = _clf_result.get('probabilities', {})
                                _ivr_score = _probs.get('ivr', 0.0)
                                _vm_score = _probs.get('voicemail', 0.0)
                            
                            # Fuse signals
                            snapshot = _p_eng.fuse(
                                stt_confidence=conversation_context.get('avg_stt_confidence', 1.0),
                                tts_drift_score=_vs_drift,
                                inbound_silence_ms=_inb.get('max_silence_ms', 0),
                                packet_gap_ms=_inb.get('max_packet_gap_ms', 0),
                                ivr_score=_ivr_score,
                                voicemail_score=_vm_score,
                            )
                            _end_payload['perception_vector'] = snapshot.to_dict()
                            
                            # Include Inbound Metrics in payload
                            if _inb:
                                import json as _json_inb
                                _end_payload['inbound_metrics'] = _json_inb.dumps(_inb)
                            
                            logger.info(f"[PERCEPTION FUSION] Snapshot: mode={snapshot.mode.value} health={snapshot.health.value}")
                        except Exception as _pf_err:
                            logger.error(f"[PERCEPTION FUSION] Failed to compute snapshot: {_pf_err}")

                    # [BEHAVIORAL FUSION]
                    if BEHAVIORAL_FUSION_WIRED and client_id in _behavioral_engines:
                        try:
                            _be = _behavioral_engines[client_id]
                            _bs = _behavioral_stats.get(client_id, {})
                            
                            # Get perception metrics from the snapshot we just computed (if available)
                            _p_mode = "unknown"
                            _p_health = "unknown"
                            if 'snapshot' in locals():
                                _p_mode = snapshot.mode.value
                                _p_health = snapshot.health.value
                            
                            # Compute final behavioral snapshot
                            _b_snap = _be.fuse(
                                fluidic_state=_bs.get("fluidic_state", "OPENING"),
                                trajectory_velocity=_bs.get("trajectory_velocity", 0.0),
                                trajectory_drift=_bs.get("trajectory_drift", 0.0),
                                emotional_viscosity=_bs.get("emotional_viscosity", 1.0),
                                objection_count=_bs.get("objection_count", 0),
                                objections_resolved=_bs.get("objections_resolved", 0),
                                turn_count=_bs.get("turn_count", 0),
                                perception_mode=_p_mode,
                                perception_health=_p_health
                            )
                            
                            bv = _b_snap.to_dict()
                            
                            # [GOVERNOR] Apply behavioral action
                            try:
                                _gov_action = decide_governor_action(_b_snap)
                                bv['governor_action'] = _gov_action.name  # Embed in vector for persistence
                                
                                if _gov_action != GovernorAction.NONE:
                                    logger.info(f"[GOVERNOR] Action triggered: {_gov_action.name} for {client_id}")
                                    
                                    # Flag outcome for control loops
                                    _end_payload['governor_action'] = _gov_action.name
                                    
                                    # If critical, force system abort flag
                                    if _gov_action == GovernorAction.HARD_KILL:
                                        _end_payload['final_outcome'] = 'system_abort'
                                        _end_payload['system_abort_reason'] = f"Behavioral Hard Kill: {_b_snap.mode.value}"
                            except Exception as _gov_err:
                                logger.warning(f"[GOVERNOR] Failed to apply action: {_gov_err}")
                            
                            _end_payload['behavioral_vector'] = bv
                            
                            # [SESSION 19.2] Coaching Tags
                            try:
                                _pv_dict = {}
                                # Use local snapshot variable if available (it holds the latest PerceptionSnapshot)
                                if 'snapshot' in locals() and snapshot:
                                     _pv_dict = snapshot.to_dict()
                                
                                _end_payload['coaching_tags'] = derive_coaching_tags(bv, _pv_dict)
                                logger.info(f"[COACHING] Tags generated: {_end_payload['coaching_tags']}")
                            except Exception as _ct_err:
                                logger.warning(f"[COACHING] Failed to derive tags: {_ct_err}")

                            logger.info(f"[BEHAVIORAL FUSION] Snapshot: mode={_b_snap.mode.value} health={_b_snap.health.value}")
                            
                            # Cleanup
                            _behavioral_engines.pop(client_id, None)
                            _behavioral_stats.pop(client_id, None)
                        except Exception as _bf_err:
                            logger.warning(f"[BEHAVIORAL FUSION] Failed to compute snapshot: {_bf_err}")

                    # [INBOUND FILTER] Tag inbound spam calls in CDC payload
                    if conversation_context.get('_inbound_spam'):
                        _end_payload['call_type'] = conversation_context.get('_inbound_spam_class', 'there_inbound')
                        _end_payload['killed_by'] = _end_payload.get('killed_by') or 'inbound_filter'
                        _end_payload['there_spam_flag'] = 1
                        logger.info(f"[INBOUND FILTER] CDC tagged: call_type={_end_payload['call_type']}")

                    # [PHASE 5] DNC flag — set by CONV INTEL pre_check abort path
                    if conversation_context.get('_dnc_flag'):
                        _end_payload['dnc_flag'] = 1

                    # [ZERO-TURN DIAGNOSTICS] Classify 0-turn calls for actionable reporting
                    if _total_turns == 0:
                        try:
                            from zero_turn_diagnostics import ZeroTurnDiagnostics, ZeroTurnEvent
                            _zt_evt = ZeroTurnEvent(
                                call_sid=conversation_context.get('call_sid', str(client_id)),
                                merchant_name=conversation_context.get('prospect_info', {}).get('company', ''),
                                duration_sec=conversation_context.get('_call_duration_seconds', 0) or 0,
                                env_class=conversation_context.get('_eab_env_class'),
                                eab_action=conversation_context.get('_eab_action'),
                                killed_by=_end_payload.get('killed_by'),
                                asr_frames=conversation_context.get('_asr_frame_count', 0) or 0,
                                audio_bytes=conversation_context.get('_audio_bytes_received', 0) or 0,
                                inbound=conversation_context.get('prospect_info', {}).get('call_direction') == 'inbound',
                                call_type=_end_payload.get('call_type'),
                                final_outcome=_end_payload.get('final_outcome', 'unknown'),
                            )
                            _zt_class = ZeroTurnDiagnostics.classify(_zt_evt)
                            _end_payload['zero_turn_class'] = _zt_class
                            logger.info(f"[ZERO-TURN] Classified: {_zt_class} "
                                       f"(dur={_zt_evt.duration_sec:.1f}s, env={_zt_evt.env_class}, killed_by={_zt_evt.killed_by})")
                        except Exception as _zt_err:
                            logger.warning(f"[ZERO-TURN] Classification failed (non-fatal): {_zt_err}")

                    _cdc_call_end(conversation_context.get('call_sid', str(client_id)), _end_payload)
                    
                    # [COACHING] Generate and write per-call coaching report
                    # [PHASE 1] Skip coaching for system_abort and infrastructure kills
                    _skip_coaching = (
                        conversation_context.get('_system_abort')
                        or _end_payload.get('killed_by') == 'infrastructure'
                        or _end_payload.get('final_outcome') == 'system_abort'
                    )
                    if CONV_INTEL_WIRED and not _skip_coaching:
                        try:
                            _guard = conversation_context.get('_conversation_guard')
                            if _guard:
                                _report = _guard.generate_coaching_report()
                                if _report and _report.get('coaching_score') is not None:
                                    _cdc_coaching(
                                        conversation_context.get('call_sid', str(client_id)),
                                        _report['coaching_score'],
                                        _report['coaching_strengths'],
                                        _report['coaching_weaknesses'],
                                        _report['coaching_action_item'],
                                    )
                                    logger.info(f"[COACHING] Call report written — score={_report['coaching_score']:.3f}, "
                                               f"strengths={_report['coaching_strengths']}, "
                                               f"weaknesses={_report['coaching_weaknesses']}")
                                    
                                    # [CW20 STEP 5] Evolution Nudge Engine — bridge coaching → evolution
                                    # Feed coaching flags into the evolution engine so Alan's behavioral
                                    # weights adjust based on HOW he performed, not just WHAT happened.
                                    try:
                                        if not conversation_context.get('_ccnm_ignore'):
                                            _evo_nudge = self.evolution.apply_coaching_nudges(_report)
                                            if _evo_nudge:
                                                conversation_context['_coaching_nudge'] = _evo_nudge
                                                # Write nudge summary to CDC evolution_nudge field
                                                if CALL_CAPTURE_WIRED:
                                                    _nudge_summary = ','.join(_evo_nudge.get('behavioral_flags', []))
                                                    try:
                                                        import sqlite3
                                                        _db = sqlite3.connect('data/call_capture.db')
                                                        _db.execute(
                                                            'UPDATE calls SET evolution_nudge = ? WHERE call_sid = ?',
                                                            (_nudge_summary, conversation_context.get('call_sid', str(client_id)))
                                                        )
                                                        _db.commit()
                                                        _db.close()
                                                    except Exception as _nudge_db_err:
                                                        logger.debug(f"[EVOLUTION] Nudge CDC write failed: {_nudge_db_err}")
                                        else:
                                            logger.info("[EVOLUTION] Coaching nudge SKIPPED — IVR call quarantined")
                                    except Exception as _nudge_err:
                                        logger.debug(f"[EVOLUTION] Coaching nudge failed: {_nudge_err}")
                        except Exception as _coach_err:
                            logger.debug(f"[COACHING] Call report generation failed: {_coach_err}")
                except Exception as _cap_err:
                    logger.error(f"[CAPTURE] Call-end capture FAILED — call data LOST: {_cap_err}", exc_info=True)
            
            # ================================================================
            # [INSTRUCTOR MODE] Governed Learning Capture
            # Finalizes the training session via InstructorLearningEngine.
            # Writes full session (turns, signals, summary) to JSONL logs.
            # Nothing enters Alan's core persona without Tim's sign-off.
            # ================================================================
            if conversation_context.get('prospect_info', {}).get('instructor_mode'):
                try:
                    _inst_session = conversation_context.get('_instructor_session')
                    if _inst_session and INSTRUCTOR_MODE_WIRED and _instructor_learning_engine:
                        _session_summary = _instructor_learning_engine.end_session(_inst_session.session_id)
                        logger.info(f"[INSTRUCTOR MODE] Session finalized — "
                                   f"{_session_summary.get('turn_count', 0)} turns, "
                                   f"{_session_summary.get('signal_count', 0)} training signals, "
                                   f"{_session_summary.get('duration_seconds', 0):.0f}s duration. "
                                   f"Pending Tim's review.")
                    else:
                        # Fallback: basic JSONL capture if module not wired
                        import json as _json_inst
                        _training_log = {
                            "session_id": conversation_context.get('call_sid', str(client_id)),
                            "timestamp": datetime.now().isoformat(),
                            "instructor_name": conversation_context.get('prospect_info', {}).get('name', 'Unknown'),
                            "duration_seconds": (datetime.now() - conversation_context.get('start_time', datetime.now())).total_seconds(),
                            "turn_count": len(conversation_context.get('messages', [])),
                            "transcript": [{"role": m.get('role', '?'), "text": m.get('content', m.get('text', ''))} for m in conversation_context.get('messages', [])],
                            "status": "pending_review"
                        }
                        import os as _os_inst
                        _os_inst.makedirs('data', exist_ok=True)
                        with open('data/instructor_training_log.jsonl', 'a', encoding='utf-8') as f:
                            f.write(_json_inst.dumps(_training_log, default=str) + '\n')
                        logger.info(f"[INSTRUCTOR MODE] Fallback capture — {_training_log['turn_count']} turns logged")
                except Exception as _inst_err:
                    logger.warning(f"[INSTRUCTOR MODE] Training log capture failed: {_inst_err}")

            # [ORGAN 11] Absorb signature sample at call end — learn from this interaction
            if SIGNATURE_ENGINE_WIRED:
                try:
                    sig_extractor = conversation_context.get('_signature_extractor')
                    if sig_extractor and _sig_learner:
                        sample = sig_extractor.finalize()
                        if sample:
                            _sig_learner.absorb_sample(sample)
                            logger.info("[ORGAN 11] Signature sample absorbed at call end")
                except Exception as e:
                    logger.warning(f"[ORGAN 11] Signature absorption failed (non-fatal): {e}")
            
            # [ALAN V2] Save MIP Profile on Disconnect
            if 'merchant_id' in conversation_context:
                try:
                    # Gather call metadata
                    call_outcome = {
                        "outcome": "completed",
                        "archetype": conversation_context.get('master_closer_state', {}).get('merchant_type'),
                        "endgame_state": conversation_context.get('master_closer_state', {}).get('endgame_state'),
                        "timestamp": datetime.now().isoformat()
                    }
                    if conversation_context.get('messages'):
                        last_msg = conversation_context['messages'][-1]
                        call_outcome['last_sentiment'] = last_msg.get('sentiment')
                    
                    # [PERSISTENCE PILLAR] Persist CallMemory snapshot
                    if conversation_context.get('call_memory'):
                        call_outcome['call_memory'] = conversation_context['call_memory']
                    
                    # [PERSISTENCE PILLAR] Persist detected preferences
                    if conversation_context.get('preferences'):
                        call_outcome['preferences'] = conversation_context['preferences']
                    
                    # [PERSISTENCE PILLAR] Persist conversation turns (per-merchant)
                    if conversation_context.get('messages'):
                        turns = []
                        for msg in conversation_context['messages']:
                            turn = {}
                            if msg.get('user'):
                                turn['user'] = msg['user']
                            if msg.get('alan'):
                                turn['alan'] = msg['alan']
                            if turn:
                                turns.append(turn)
                        if turns:
                            call_outcome['conversation_turns'] = turns
                    
                    # [PERSISTENCE PILLAR] Trajectory for pattern analysis
                    call_outcome['trajectory'] = conversation_context.get('master_closer_state', {}).get('trajectory')
                    
                    self.mip.update_profile_from_call(conversation_context['merchant_id'], call_outcome)
                    logger.info(f"[ALAN V2] Saved full MIP Profile for {conversation_context['merchant_id']}")
                except Exception as e:
                    logger.error(f"[ALAN V2] Failed to save MIP profile: {e}")

            # [SUPERVISOR] Fire Agent Coach review (fire-and-forget)
            if conversation_context.get('messages') and len(conversation_context.get('messages', [])) >= 3:
                try:
                    import threading
                    def _coach_review():
                        try:
                            from src.agent_coach import AgentCoach
                            import os
                            base_dir = os.path.dirname(os.path.abspath(__file__))
                            coach = AgentCoach(
                                os.path.join(base_dir, 'data', 'agent_x.db'),
                                os.path.join(base_dir, 'data', 'conversation_history.json')
                            )
                            coach.analyze_last_conversation()
                            logger.info("[COACH] Post-call coaching review completed")
                        except Exception as e:
                            logger.warning(f"[COACH] Coaching review failed (non-critical): {e}")
                    threading.Thread(target=_coach_review, daemon=True).start()
                except Exception:
                    pass  # Coach is non-critical

            # [AUTONOMY] Fire process_call_outcome for follow-up scheduling (fire-and-forget)
            if hasattr(alan_ai, 'process_call_outcome'):
                try:
                    import threading as _threading_outcome
                    # Extract phone and build outcome summary from conversation context
                    _phone = conversation_context.get('prospect_info', {}).get('phone', '')
                    if not _phone:
                        _phone = conversation_context.get('caller_number', '')
                    _outcome_parts = []
                    _endgame = conversation_context.get('master_closer_state', {}).get('endgame_state', '')
                    _trajectory = conversation_context.get('master_closer_state', {}).get('trajectory', '')
                    if _endgame:
                        _outcome_parts.append(f"endgame:{_endgame}")
                    if _trajectory:
                        _outcome_parts.append(f"trajectory:{_trajectory}")
                    _turns = len(conversation_context.get('messages', []))
                    _outcome_parts.append(f"turns:{_turns}")
                    # Check last few messages for key phrases
                    _last_msgs = conversation_context.get('messages', [])[-3:]
                    for _m in _last_msgs:
                        _user_text = _m.get('user', '').lower()
                        if any(w in _user_text for w in ['call me back', 'busy', 'not a good time']):
                            _outcome_parts.append("busy")
                        if any(w in _user_text for w in ['not interested', 'no thanks', 'remove me']):
                            _outcome_parts.append("not interested")
                        if any(w in _user_text for w in ['interested', 'tell me more', 'sounds good', 'send info']):
                            _outcome_parts.append("interested")
                        if any(w in _user_text for w in ['proposal', 'sign up', 'lets do it', "let's do it"]):
                            _outcome_parts.append("proposal")
                    _outcome_summary = ", ".join(_outcome_parts) if _outcome_parts else "completed"

                    if _phone:
                        def _fire_outcome():
                            try:
                                alan_ai.process_call_outcome(_phone, _outcome_summary)
                                logger.info(f"[FOLLOW-UP] Call outcome processed for {_phone}: {_outcome_summary}")
                            except Exception as e:
                                logger.warning(f"[FOLLOW-UP] Outcome processing failed (non-critical): {e}")
                        _threading_outcome.Thread(target=_fire_outcome, daemon=True).start()
                    else:
                        logger.info("[FOLLOW-UP] No phone number available — skipping outcome processing")
                except Exception:
                    pass  # Outcome processing is non-critical

            # Clean up conversation
            # [REPLICATION] Deregister this Alan instance from the fleet
            if REPLICATION_WIRED and conversation_context.get('replication_registered'):
                try:
                    rep_engine = get_replication_engine()
                    call_sid = conversation_context.get('call_sid', str(client_id))
                    outcome = conversation_context.get('outcome', 'completed')
                    turns = len(conversation_context.get('messages', []))
                    rep_engine.deregister_instance(
                        call_sid,
                        outcome=outcome,
                        lessons=f"{turns} turns, outcome: {outcome}",
                        merchant_data={
                            "prospect_name": conversation_context.get('prospect_info', {}).get('name', ''),
                            "business_name": conversation_context.get('prospect_info', {}).get('business', ''),
                            "merchant_id": conversation_context.get('merchant_id', ''),
                        }
                    )
                    logger.info(f"[REPLICATION] Instance deregistered for call {call_sid} "
                                f"(fleet: {rep_engine.current_count}/{rep_engine.max_instances})")
                except Exception as e:
                    logger.warning(f"[REPLICATION] Failed to deregister: {e}")
            
            if client_id in self.active_conversations:
                del self.active_conversations[client_id]

    async def _stream_audio_frames(self, websocket, raw_audio, stream_sid):
        """Stream pre-synthesized mulaw audio frames to Twilio.
        
        Used by two-stage greeting to stream cached prefix and live suffix
        independently. Does NOT send MARK event (caller handles that).
        """
        chunk_size = 160  # 20ms frames
        offset = 0
        frame_count = 0
        while offset < len(raw_audio):
            end = min(offset + chunk_size, len(raw_audio))
            frame = raw_audio[offset:end]
            offset = end
            if len(frame) < chunk_size:
                frame = frame + b'\xFF' * (chunk_size - len(frame))
            b64_data = base64.b64encode(frame).decode('utf-8')
            payload = {"event": "media", "streamSid": stream_sid, "media": {"payload": b64_data}}
            try:
                if hasattr(websocket, 'send_text'):
                    await websocket.send_text(json.dumps(payload))
                else:
                    await websocket.send(json.dumps(payload))
            except Exception:
                break
            frame_count += 1
            if frame_count < 20:
                await asyncio.sleep(0.005)
            elif frame_count < 50:
                await asyncio.sleep(0.003)
            else:
                await asyncio.sleep(0.012)

    async def synthesize_and_stream_greeting(self, websocket, greeting, stream_sid):
        """Helper to Synthesize and Stream Greeting with Soft-Start Heartbeat"""
        # [ECHO FIX] Mark Twilio playback as pending — greeting is about to play
        # We'll get a mark event back from Twilio when it finishes
        # (greeting uses FIRST_GREETING_PENDING state for _is_alan_talking, 
        #  but twilio_playback_done provides the post-greeting echo gate too)
        # [TTS WEDGE] Synthesis & Streaming (Pure Streaming Mode)
        try:
             # [ZERO-LATENCY] Check startup pre-cache FIRST (saves 300-600ms)
             if greeting in self.greeting_cache:
                 raw_audio = self.greeting_cache[greeting]
                 logger.info(f"[TTS] GREETING CACHE HIT! {len(raw_audio)} bytes ready instantly.")
             else:
                 # Named greeting (with prospect name) — synthesize live
                 logger.info(f"[TTS] Starting Greeting Synthesis for: '{greeting[:40]}...'")
                 
                 if not self.tts_client:
                     logger.error("[TTS] No TTS client available.")
                     return

                 # Synthesize in thread
                 loop = asyncio.get_running_loop()
                 raw_audio = await loop.run_in_executor(self.executor, self._openai_tts_sync, greeting)
             
             if not raw_audio:
                 logger.error("[TTS] No audio data from OpenAI TTS.")
                 return
             
             logger.info(f"[TTS] Got {len(raw_audio)} bytes from OpenAI TTS. Streaming frames...")
             
             # Stream Chunks from buffered audio (non-blocking)
             chunk_buffer = raw_audio
             chunk_size = 160 # 20ms
             frame_count = 0
             offset = 0
             
             while offset < len(chunk_buffer):
                 end = min(offset + chunk_size, len(chunk_buffer))
                 frame = chunk_buffer[offset:end]
                 offset = end
                 
                 # Pad last frame if needed
                 if len(frame) < chunk_size:
                     frame = frame + b'\xFF' * (chunk_size - len(frame))
                 
                 # Send Frame
                 b64_data = base64.b64encode(frame).decode("utf-8")
                 payload = {
                    "event": "media",
                    "streamSid": stream_sid,
                    "media": {"payload": b64_data}
                 }
                 
                 if hasattr(websocket, 'send_text'):
                     await websocket.send_text(json.dumps(payload))
                 else:
                     await websocket.send(json.dumps(payload))
                     
                 frame_count += 1
                 # Pacing: warm up Twilio's jitter buffer gently, then real-time
                 # Greeting is the FIRST audio on a cold connection — don't flood
                 if frame_count < 20:
                     await asyncio.sleep(0.005)  # Gentle warm-up for cold jitter buffer
                 elif frame_count < 50:
                     await asyncio.sleep(0.003)  # Ramp up
                 else:
                     await asyncio.sleep(0.012)  # Real-time pacing
             
             logger.info(f"[TTS WEDGE] Streaming Complete. Sent {frame_count} frames.")
             
             # Send MARK event
             mark_payload = {"event": "mark", "streamSid": stream_sid, "mark": {"name": "turn_complete"}}
             if hasattr(websocket, 'send_text'):
                 await websocket.send_text(json.dumps(mark_payload))
             else:
                 await websocket.send(json.dumps(mark_payload))

        except Exception as e:
             logger.error(f"[TTS WEDGE] Detailed Failure: {e}")

    async def handle_conversation_start(self, data, context, websocket):
        """
        Handle conversation initiation.
        Refinement 2: Dynamic Breath (VAD Synchronization).
        """
        # Extract prospect information from ConversationRelay parameters
        context['streamSid'] = data.get('streamSid')
        parameters = data.get('parameters', {})

        # [INSTRUCTOR MODE] Detect training flag from Stream parameters
        _instructor_flag = parameters.get('instructor_mode', 'false').lower() == 'true'
        if _instructor_flag:
            logger.info("[INSTRUCTOR MODE] Training call activated — governed learning session")

        # [DEMO MODE] Detect demo mode from Stream parameters (e.g. 'italian_aqi')
        _demo_mode = parameters.get('demo_mode', '').strip()
        if _demo_mode:
            logger.info(f"[DEMO MODE] Activated: {_demo_mode}")

        context['prospect_info'] = {
            'name': parameters.get('prospect_name', 'there'),
            'company': parameters.get('business_name', ''),
            'call_type': 'instructor_training' if _instructor_flag else ('demo_' + _demo_mode if _demo_mode else parameters.get('call_type', 'business_development')),
            'strategy': 'instructor_mode' if _instructor_flag else ('demo_mode' if _demo_mode else parameters.get('strategy', 'cold_call')),
            'call_direction': parameters.get('call_direction', 'outbound'),
            'instructor_mode': _instructor_flag,
            'demo_mode': _demo_mode
        }

        # [ORGAN 29] Inbound Context — lookup caller for callback memory
        if INBOUND_CONTEXT_WIRED:
            try:
                _ic_organ = context.get('_inbound_context_organ')
                _call_dir_ic = context['prospect_info'].get('call_direction', 'outbound')
                _merchant_phone_ic = parameters.get('prospect_phone', '')

                if _ic_organ and _call_dir_ic == 'inbound' and _merchant_phone_ic:
                    _ic_result = _ic_organ.lookup_caller(_merchant_phone_ic)
                    context['_inbound_context'] = _ic_result

                    # Classify warm vs cold vs partial
                    _ic_type = _ic_result.get('context_type', 'unknown')
                    if _ic_type in ('returning_caller', 'scheduled_callback'):
                        context['_inbound_context_state'] = 'warm'
                        # Enrich prospect_info with callback memory
                        if _ic_result.get('merchant_name') and context['prospect_info'].get('name') in ('there', 'Unknown', '', 'unknown'):
                            context['prospect_info']['name'] = _ic_result['merchant_name']
                        if _ic_result.get('business_name') and not context['prospect_info'].get('company'):
                            context['prospect_info']['company'] = _ic_result['business_name']
                        context['prospect_info']['phone'] = _merchant_phone_ic
                        logger.info(f"[ORGAN 29] WARM inbound: {_ic_type} — "
                                   f"name={_ic_result.get('merchant_name')}, "
                                   f"prior_calls={len(_ic_result.get('prior_calls', []))}")
                    elif _ic_type == 'known_lead':
                        context['_inbound_context_state'] = 'partial'
                        if _ic_result.get('merchant_name') and context['prospect_info'].get('name') in ('there', 'Unknown', '', 'unknown'):
                            context['prospect_info']['name'] = _ic_result['merchant_name']
                        if _ic_result.get('business_name') and not context['prospect_info'].get('company'):
                            context['prospect_info']['company'] = _ic_result['business_name']
                        context['prospect_info']['phone'] = _merchant_phone_ic
                        logger.info(f"[ORGAN 29] PARTIAL inbound: known_lead — "
                                   f"name={_ic_result.get('merchant_name')}")
                    else:
                        context['_inbound_context_state'] = 'cold'
                        logger.info("[ORGAN 29] COLD inbound — no prior context found")
                elif _call_dir_ic != 'inbound':
                    logger.info("[ORGAN 29] Outbound call — skipping inbound context lookup")
            except Exception as _ic_lookup_err:
                context['_inbound_context_state'] = 'cold'
                logger.warning(f"[ORGAN 29] Inbound lookup failed (non-fatal): {_ic_lookup_err}")

        # [INBOUND FILTER] Detect "there" inbound spam callbacks early
        if INBOUND_FILTER_WIRED:
            _call_dir = context['prospect_info'].get('call_direction', 'outbound')
            _prospect_nm = parameters.get('prospect_name', 'there')
            _biz_nm = parameters.get('business_name', '')
            if _call_dir == 'inbound':
                _inbound_ctx = {
                    'merchant_name': _prospect_nm,
                    'call_direction': _call_dir,
                    'business_name': _biz_nm,
                }
                if is_inbound_spam(_inbound_ctx):
                    context['_inbound_spam'] = True
                    context['_inbound_spam_class'] = classify_inbound(_inbound_ctx)
                    logger.info(f"[INBOUND FILTER] Spam callback detected: {context['_inbound_spam_class']}")

        # [INSTRUCTOR MODE] Initialize governed training session
        if _instructor_flag and INSTRUCTOR_MODE_WIRED and _instructor_learning_engine:
            _session_id = context.get('call_sid', str(id(context)))
            _instructor_id = parameters.get('instructor_id', 'unknown')
            _instructor_name = parameters.get('prospect_name', 'Instructor')
            _inst_session = _instructor_learning_engine.start_session(
                session_id=_session_id,
                instructor_id=_instructor_id,
                instructor_name=_instructor_name,
            )
            context['_instructor_session'] = _inst_session
            logger.info(f"[INSTRUCTOR MODE] Session {_session_id} initialized — "
                       f"instructor: {_instructor_name} ({_instructor_id})")

        # Enrich with RSE Data (The "Perfect" Intelligence)
        agent = context['agent_instance']
        try:
            rse_data = agent.lookup_rse_lead(
                company_name=context['prospect_info']['company']
            )
            if rse_data:
                logger.info(f"🎯 RSE Data Found for {context['prospect_info']['company']}")
                context['prospect_info']['rse_data'] = rse_data
                if rse_data.get('primary_signal'):
                    context['prospect_info']['signal'] = rse_data['primary_signal']
                    # Update strategy if we have a strong signal
                    context['prospect_info']['strategy'] = 'sniper_approach'
        except Exception as e:
            logger.error(f"Error enriching with RSE data: {e}")

        # Start Dynamic Breath Routine (Don't reply immediately)
        asyncio.create_task(self.smart_greeting_routine(websocket, context))
        return None # No immediate response

    @staticmethod
    def _is_person_name(name: str) -> bool:
        """Detect if a string looks like a real person's name vs a business/search title.
        Lead data often has business names ('MH Nail Salon'), search result titles 
        ('About Rose Roofing in Houston'), or addresses in the name field.
        Only return True for strings that look like actual human names (e.g. 'John Smith')."""
        if not name or len(name.strip()) < 2:
            return False
        name = name.strip()
        words = name.split()
        # Person names are 1-3 words (first, middle, last)
        if len(words) > 3:
            return False
        # Contains numbers → not a person name
        if any(c.isdigit() for c in name):
            return False
        # Contains special chars → not a person name
        if any(ch in name for ch in ',–—|/:()&@#$%.!?'):
            return False
        # Business/location/category keywords → not a person name
        _biz = (
            'salon', 'grooming', 'groom', 'roofing', 'roof', 'restaurant', 'pizza',
            'florist', 'flower', 'retail', 'wash', 'cafe', 'café', 'bar', 'grill',
            'shop', 'store', 'market', 'clinic', 'dental', 'spa', 'gym', 'fitness',
            'repair', 'auto', 'plumbing', 'plumber', 'electric', 'cleaning',
            'landscap', 'construction', 'inc', 'llc', 'corp', 'ltd', 'co.',
            'services', 'service', 'solutions', 'studio', 'gallery', 'hotel',
            'motel', 'boutique', 'bakery', 'pharmacy', 'laundry', 'pet', 'vet',
            'animal', 'rent', 'insurance', 'realty', 'property', 'home', 'house',
            'nail', 'hair', 'beauty', 'barber', 'tattoo', 'church', 'school',
            'academy', 'institute', 'center', 'centre', 'trucking', 'towing',
            'hvac', 'moving', 'storage', 'supply', 'wholesale', 'design', 'tech',
            'software', 'media', 'agency', 'group', 'associates', 'about',
            'selecting', 'case study', 'page', 'the ideal', 'guide', 'how to',
            'best', 'top', 'review', 'rated', '2026', '2025', '2024',
            # Retail / product categories
            'music', 'sports', 'cycles', 'bicycle', 'bike', 'shoes', 'books',
            'jewel', 'clothing', 'apparel', 'furniture', 'food', 'drink', 'grocer',
            # Business/org terms
            'bistro', 'hospitality', 'business', 'division', 'department',
            'development', 'restoration', 'capital', 'fund', 'invest',
            'consulting', 'management', 'enterprise', 'venture', 'holding',
            'legacy', 'excellence', 'premier', 'elite', 'classic', 'modern',
            'global', 'urban', 'golden', 'silver', 'royal', 'first star',
        )
        name_lower = name.lower()
        if any(kw in name_lower for kw in _biz):
            return False
        # US state abbreviations at end (e.g. "Dallas TX")
        _states = {'al','ak','az','ar','ca','co','ct','de','fl','ga','hi','id',
                    'il','ia','ks','ky','la','me','md','ma','mi','mn','ms','mo',
                    'mt','ne','nv','nh','nj','nm','ny','nc','nd','oh','ok','or',
                    'pa','ri','sc','sd','tn','tx','ut','vt','va','wa','wv','wi','wy','dc'}
        if words[-1].lower().rstrip(')') in _states:
            return False
        # Common cities in name → not a person
        _cities = ('dallas', 'houston', 'chicago', 'seattle', 'orlando', 'angeles',
                   'francisco', 'antonio', 'diego', 'phoenix', 'philadelphia', 'nyc',
                   'atlanta', 'miami', 'denver', 'portland', 'boston', 'detroit',
                   'tampa', 'charlotte', 'minneapolis', 'memphis', 'nashville',
                   'austin', 'vegas', 'brooklyn', 'manhattan', 'sacramento',
                   'jacksonville', 'columbus', 'indianapolis', 'milwaukee')
        if any(c in name_lower for c in _cities):
            return False
        # Single word that's all lowercase → probably not a name
        if len(words) == 1 and name == name.lower():
            return False
        # Placeholder values
        if name_lower in ('unknown', 'there', 'n/a', 'none', 'test', 'owner'):
            return False
        # Passed all filters → likely a person name
        return True

    async def smart_greeting_routine(self, websocket, context):
        """
        DETERMINISTIC FIRST-TURN PIPELINE
        Enforces exact greeting requirement and clean first-turn state.
        Uses greeting rotation for natural variation across calls.
        """
        logger.info("[FIRST TURN] Initiating Deterministic First-Turn Pipeline...")

        # 1. DETERMINE GREETING BASED ON CALL DIRECTION + AVAILABLE INFO
        call_direction = context.get('prospect_info', {}).get('call_direction', 'outbound')
        prospect_name = context.get('prospect_info', {}).get('name', 'there')
        # [FIX] Only treat as a person name if it actually looks like one.
        # Lead data often has business names or search titles in the name field.
        has_name = (prospect_name 
                    and prospect_name not in ('there', 'Unknown', '', 'unknown')
                    and self._is_person_name(prospect_name))
        if not has_name and prospect_name not in ('there', 'Unknown', '', 'unknown', None):
            # It's a business name — make sure prospect_info['company'] has it
            if not context.get('prospect_info', {}).get('company'):
                context.setdefault('prospect_info', {})['company'] = prospect_name
            logger.info(f"[GREETING] '{prospect_name}' detected as BUSINESS name — using owner-ask greeting")
        
        # [INSTRUCTOR MODE] Training greeting — different from sales greetings
        _is_instructor = context.get('prospect_info', {}).get('instructor_mode', False)
        _demo_mode = context.get('prospect_info', {}).get('demo_mode', '')
        if _demo_mode == 'italian_aqi':
            ITALIAN_GREETINGS = [
                "Buonasera, signora. Mi chiamo Alan. Sono l'intelligenza artificiale che suo figlio Tim ha creato. Lui voleva che la chiamassi, perche' ha qualcosa di importante da farle sapere. Come sta?",
            ]
            REQUIRED_GREETING = random.choice(ITALIAN_GREETINGS)
            logger.info(f"[DEMO MODE] Using Italian AQI greeting")
        elif _is_instructor:
            INSTRUCTOR_GREETINGS = [
                "Hey, this is Alan. Tim set us up for some role-play practice. Appreciate you taking the time.",
                "Hey, it's Alan. Tim said you'd be a great person to train with. Thanks for doing this.",
            ]
            REQUIRED_GREETING = random.choice(INSTRUCTOR_GREETINGS)
            logger.info(f"[INSTRUCTOR MODE] Using training greeting")
        elif call_direction == 'inbound':
            # [ORGAN 29] Warm greeting for returning callers
            _ic_state = context.get('_inbound_context_state', 'cold')
            _ic_ctx = context.get('_inbound_context')
            if _ic_state == 'warm' and _ic_ctx and INBOUND_CONTEXT_WIRED:
                try:
                    _ic_organ = context.get('_inbound_context_organ')
                    if _ic_organ:
                        REQUIRED_GREETING = _ic_organ.get_greeting_script(_ic_ctx)
                        logger.info(f"[ORGAN 29] Warm inbound greeting: {REQUIRED_GREETING[:60]}...")
                    else:
                        INBOUND_GREETINGS = [
                            "Signature Card Services, this is Alan.",
                            "Signature Card, Alan speaking."
                        ]
                        REQUIRED_GREETING = random.choice(INBOUND_GREETINGS)
                except Exception as _ic_greet_err:
                    logger.warning(f"[ORGAN 29] Warm greeting failed (non-fatal): {_ic_greet_err}")
                    INBOUND_GREETINGS = [
                        "Signature Card Services, this is Alan.",
                        "Signature Card, Alan speaking."
                    ]
                    REQUIRED_GREETING = random.choice(INBOUND_GREETINGS)
            else:
                INBOUND_GREETINGS = [
                    "Signature Card Services, this is Alan.",
                    "Signature Card, Alan speaking."
                ]
                REQUIRED_GREETING = random.choice(INBOUND_GREETINGS)
        elif has_name:
            # We have the owner's name — TWO-STAGE GREETING for zero-latency start.
            # Stage 1: Cached generic prefix (plays instantly from greeting_cache).
            # Stage 2: Live TTS for the name-specific tail (synthesized while stage 1 plays).
            # Full greeting is assembled as one string for history/logging.
            #
            # [FEB 24 2026] SOFT OPENER — delay company name to survive the 3-second hangup window.
            # Data: 43% of hangups happen 6-11s in, 0 turns — merchant hears "Signature Card Services"
            # and instantly hangs up. Real sales reps say their name first, ask for the owner,
            # then introduce the company only AFTER they have attention.
            # Mix: 50% soft (no company name upfront), 50% standard (for A/B signal).
            # [FEB 27 2026] PRECISION OPENERS — shorter, faster, human-sounding.
            # Data: 86% zero-turn hangup rate. 18-word greetings take 4-5s — merchant
            # has already decided "sales call" and hung up by word 10.
            # Fix: Cut to 7-10 words max. 80% soft (no company), 20% standard.
            # Also validate prospect_name — filter out scraping artifacts.
            _NAME_BLACKLIST = {'contact us', 'screen printing', 'unknown', 'none', 'n/a', 
                               'owner', 'manager', 'the owner', 'business', 'llc', 'inc',
                               'restaurant', 'restaurants', 'shop', 'store', 'service'}
            _clean_name = prospect_name.strip()
            if _clean_name.lower() in _NAME_BLACKLIST or len(_clean_name) < 3 or len(_clean_name.split()) > 4:
                has_name = False  # Fall through to cold greeting
                logger.info(f"[GREETING] Name '{_clean_name}' rejected — using cold opener")
            
            if has_name:
                NAMED_GREETING_PAIRS = [
                    # SOFT — short, human, no company (80% of pool)
                    ("Hey, this is Alan.", f"Is {prospect_name} around?"),
                    ("Hey, this is Alan.", f"Could I speak with {prospect_name}?"),
                    ("Hi, this is Alan.", f"Is {prospect_name} available?"),
                    ("Hey, it's Alan.", f"Is {prospect_name} there?"),
                    # STANDARD — company name (20% of pool)
                    ("Hi, this is Alan from Signature Card.", f"Is {prospect_name} available?"),
                ]
                _pair = random.choice(NAMED_GREETING_PAIRS)
                REQUIRED_GREETING = _pair[0] + " " + _pair[1]
                context['_greeting_prefix'] = _pair[0]
                context['_greeting_suffix'] = _pair[1]
        else:
            # No name — ask for the owner. Tim's proven script.
            # [FEB 24 2026] SOFT OPENER MIX — same strategy as named greetings.
            # 50% soft (just Alan, no company), 50% standard (with company name).
            # [FEB 27 2026] PRECISION COLD OPENERS — 7-10 words max.
            # Old openers averaged 18 words → 4-5s delivery → instant hangup.
            # New openers: fast, human, get to the ask in under 2 seconds.
            # 80% soft (no company name), 20% standard.
            COLD_GREETINGS = [
                # SOFT — short and human (80% of pool)
                "Hey, this is Alan. Is the owner around?",
                "Hi, this is Alan. Is the owner available?",
                "Hey, it's Alan. Is the owner or manager there?",
                "Hey, this is Alan calling. Is the owner in?",
                # STANDARD — with company (20% of pool)
                "Hi, this is Alan from Signature Card. Is the owner available?",
            ]
            REQUIRED_GREETING = random.choice(COLD_GREETINGS)
        
        logger.info(f"[FIRST TURN] Call direction: {call_direction}")

        # [DEBUG] Write selected greeting to file for verification
        try:
            import os as _dbg_os
            with open(_dbg_os.path.join(_dbg_os.path.dirname(_dbg_os.path.abspath(__file__)), '_greeting_debug.log'), 'a') as _dbg_f:
                _dbg_f.write(f"{datetime.now().isoformat()} | has_name={has_name} | name={prospect_name} | greeting={REQUIRED_GREETING}\n")
        except Exception:
            pass

        # 2. CHECK ALREADY SENT
        if context.get('greeting_sent'):
            logger.info("[FIRST TURN] Greeting already sent. Skipping.")
            return

        # 2.5 STREAM RING TONE — OUTBOUND ONLY: skip entirely
        # On outbound calls, merchant already heard ringing on their end.
        # Adding fake ring tone wastes 0.5-2s where they're waiting for someone to speak.
        # Only play on inbound calls where caller expects a pickup sound.
        stream_sid = context.get('streamSid')
        if self.ring_tone_audio and stream_sid and call_direction == 'inbound':
            logger.info(f"[RING TONE] Streaming {len(self.ring_tone_audio)} bytes before greeting...")
            chunk_size = 160  # 20ms frames
            offset = 0
            while offset < len(self.ring_tone_audio):
                end = min(offset + chunk_size, len(self.ring_tone_audio))
                frame = self.ring_tone_audio[offset:end]
                offset = end
                if len(frame) < chunk_size:
                    frame = frame + b'\xFF' * (chunk_size - len(frame))
                b64_data = base64.b64encode(frame).decode('utf-8')
                payload = {"event": "media", "streamSid": stream_sid, "media": {"payload": b64_data}}
                try:
                    if hasattr(websocket, 'send_text'):
                        await websocket.send_text(json.dumps(payload))
                    else:
                        await websocket.send(json.dumps(payload))
                except Exception:
                    break
                await asyncio.sleep(0.012)  # Match cruise pacing across all frame streams (was 0.018 — 80% above standard)
            logger.info("[RING TONE] Ring tone streamed.")

        # 3. SET STATE IMMEDIATELY (Prevents race conditions)
        # [PHASE 2] FSM: STREAM_READY → GREETING_PENDING
        _fsm = context.get('_call_fsm')
        if _fsm:
            _fsm.handle_event(CallFlowEvent.GREETING_BUILT)
        else:
            context['greeting_sent'] = True
            context['conversation_state'] = 'FIRST_GREETING_PENDING'
        
        # 4. FIRE GREETING (Streaming TTS)
        # We assume the stream is ready because this routine is called from handle_conversation_start
        stream_sid = context.get('streamSid')
        
        logger.info(f"[FIRST TURN] Streaming Mandatory Greeting: '{REQUIRED_GREETING}'")
        logger.info(f"[VERIFICATION] Timestamp Greeting Start: {datetime.now().isoformat()}")
        
        try:
             # [TWO-STAGE GREETING] If we have a prefix+suffix pair (named greeting),
             # stream the cached prefix instantly while TTS synthesizes the suffix.
             # This gets first audio out in <100ms instead of waiting 300-600ms for full TTS.
             _prefix = context.pop('_greeting_prefix', None)
             _suffix = context.pop('_greeting_suffix', None)
             
             if _prefix and _suffix and _prefix in self.greeting_cache:
                 logger.info(f"[TWO-STAGE] Prefix CACHE HIT: '{_prefix}' | Suffix live: '{_suffix}'")
                 
                 # Start suffix TTS synthesis concurrently BEFORE streaming prefix
                 loop = asyncio.get_running_loop()
                 _suffix_future = loop.run_in_executor(self.executor, self._openai_tts_sync, _suffix)
                 
                 # Stream the cached prefix immediately (zero latency)
                 await self._stream_audio_frames(websocket, self.greeting_cache[_prefix], stream_sid)
                 
                 # Now await the suffix TTS (likely already done — prefix playback took ~1.5s)
                 _suffix_audio = await _suffix_future
                 if _suffix_audio:
                     await self._stream_audio_frames(websocket, _suffix_audio, stream_sid)
                 
                 # Send MARK event
                 mark_payload = {"event": "mark", "streamSid": stream_sid, "mark": {"name": "turn_complete"}}
                 if hasattr(websocket, 'send_text'):
                     await websocket.send_text(json.dumps(mark_payload))
                 else:
                     await websocket.send(json.dumps(mark_payload))
             else:
                 # Standard path: full greeting (cached or live)
                 await self.synthesize_and_stream_greeting(websocket, REQUIRED_GREETING, stream_sid)
             logger.info("[FIRST TURN] Greeting Stream Initiated Successfully.")
             logger.info(f"[VERIFICATION] Timestamp Greeting Stream Active: {datetime.now().isoformat()}")
             
             # 5. SEED CONVERSATION HISTORY WITH GREETING
             # Critical: Without this, the LLM has no idea Alan already spoke.
             # It would generate a second greeting/intro on the first user turn.
             context['messages'].append({
                 'timestamp': datetime.now(),
                 'user': '',
                 'alan': REQUIRED_GREETING,
                 'sentiment': 'neutral',
                 'interest': 0
             })
             # Also persist to the agent's conversation history for LLM context
             agent = context.get('agent_instance')
             if agent and hasattr(agent, 'conversation_history'):
                 agent.conversation_history.add_message('Alan', REQUIRED_GREETING)
             
             # [LAG FIX] Pre-warm LLM connection while greeting audio plays
             # The greeting takes ~3-4 seconds to play. During that window,
             # fire a cheap API call to warm the TCP connection + OpenAI prompt cache.
             # This makes the FIRST real LLM call much faster (3000ms → 500ms TTFT).
             if agent:
                 loop = asyncio.get_running_loop()
                 await loop.run_in_executor(self.executor, self._prewarm_llm_connection, agent)
             logger.info(f"[FIRST TURN] Greeting seeded + LLM connection pre-warmed")
             
             # [ORGAN] Hook 2 — Greeting Sent
             if CALL_MONITOR_WIRED:
                 monitor_greeting_sent(context.get('call_sid', ''), REQUIRED_GREETING)
             
             # [CAPTURE] Record greeting
             if CALL_CAPTURE_WIRED:
                 _cdc_greeting(context.get('call_sid', ''), REQUIRED_GREETING)
             
             # 6. ENTER LISTENING STATE
             # [PHASE 2] FSM: GREETING_PENDING → GREETING_PLAYED
             _fsm = context.get('_call_fsm')
             if _fsm:
                 _fsm.handle_event(CallFlowEvent.GREETING_STREAMED)
             else:
                 context['conversation_state'] = 'LISTENING_FOR_CALLER'
             context['responding_ended_at'] = time.time()  # Echo cooldown reference
             context['vad_speech_frames'] = 0  # Reset speech detection
             
             # Clear STT buffer of any echo collected during greeting
             if stream_sid:
                 aqi_stt_engine.clear_buffer(stream_sid)
             
             logger.info("[FIRST TURN] Transitioned to LISTENING_FOR_CALLER")
             
        except Exception as e:
             logger.error(f"[FIRST TURN] Critical Failure in Greeting Synthesis: {e}")
             # Absolute worst case fallback text (if TTS fails completely)
             response = {
                'type': 'conversation_reply',
                'speech': REQUIRED_GREETING,
                'end_conversation': False
             }
             await self._safe_send(websocket, response)

    # =============================================================================
    # [LAG FIX] LLM CONNECTION + PROMPT CACHE PRE-WARM
    # =============================================================================
    # During the greeting window (~3-4 seconds of audio playback), the server
    # does nothing. We use this window to:
    #   1. Warm the TCP/TLS connection to OpenAI (saves ~150ms on first call)
    #   2. Warm OpenAI's prompt cache with the system prompt (saves ~1-2s on first call)
    # This reduces first-turn TTFT from ~3000ms to ~500-800ms.
    # =============================================================================

    def _prewarm_llm_connection(self, agent):
        """Pre-warm OpenAI API connection + prompt cache during greeting window.
        Runs in executor thread. Non-critical — failures are silently logged.
        Retries once on stale connection (RemoteDisconnected)."""
        try:
            api_key = agent.get_api_key()
            if not api_key:
                return
            system_prompt = agent.system_prompt
            url = "https://api.openai.com/v1/chat/completions"
            payload = {
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": "OK"}
                ],
                "max_tokens": 1,
                "temperature": 0,
            }
            headers = {"Authorization": f"Bearer {api_key}"}
            warm_start = time.time()
            for attempt in range(2):
                try:
                    r = self._llm_session.post(url, json=payload, headers=headers, timeout=(3, 10))
                    warm_ms = 1000 * (time.time() - warm_start)
                    logger.info(f"[PRE-WARM LLM] Connection + prompt cache warmed in {warm_ms:.0f}ms (status {r.status_code})")
                    return
                except (ConnectionError, OSError) as ce:
                    if attempt == 0:
                        # Stale keep-alive connection — rebuild session with adapter
                        self._llm_session.close()
                        import requests as _req
                        from requests.adapters import HTTPAdapter as _WarmAdapter
                        self._llm_session = _req.Session()
                        self._llm_session.mount("https://", _WarmAdapter(pool_connections=4, pool_maxsize=8))
                        continue
                    raise ce
        except Exception as e:
            logger.warning(f"[PRE-WARM LLM] Failed (non-critical): {e}")

    # =============================================================================
    # [VERSION R+] ORCHESTRATED PIPELINE — "The Symphony"
    # =============================================================================
    # Previous architecture: Sequential (marching band)
    #   LLM(full 2s) → split → TTS(sentence1 0.6s) → stream → TTS(sentence2)
    #   Total: ~2800-5500ms from user-stops to first-audio-out
    #
    # New architecture: Overlapped (symphony orchestra)
    #   LLM SSE tokens stream → first sentence detected (~400ms) → TTS starts
    #   immediately → audio streams to Twilio while LLM generates sentence 2
    #   Total: ~1500-2200ms from user-stops to first-audio-out
    #
    # Key insight: Both LLM and TTS are STREAMING-CAPABLE systems.
    # Using them in batch mode (collect everything, then act) wastes 800-1500ms.
    # The orchestrated pipeline lets every instrument play AS SOON as it's ready.
    # =============================================================================

    # =============================================================================
    # [SPECULATIVE DECODING] Sprint Prompt Builder
    # =============================================================================
    def _build_sprint_prompt(self, user_text, context):
        """Build minimal prompt for speculative decoding sprint.
        
        Generates a stripped-down prompt that retains Alan's core identity
        and current conversation context but drops all advanced systems
        (deep layer, evolution, perception, behavioral fusion, etc.)
        to minimize input tokens and maximize TTFT speed.
        
        ~200 input tokens vs ~3000+ for the full prompt.
        This shorter prompt means OpenAI processes it faster → earlier TTFT.
        
        [2026-03-04 FIX] Redesigned for COMPLETE responses instead of fragments.
        Previous version forced "8-15 word opening clause" which created disjointed
        output when stitched with full LLM. Now generates 1-2 complete sentences
        that can stand alone as a natural response.
        
        Returns: list of message dicts for OpenAI API
        """
        mode = context.get('_deep_layer_mode', 'rapport')
        business_name = context.get('business_name', '')
        _is_instructor = context.get('prospect_info', {}).get('instructor_mode', False)
        
        # Check if this is the FIRST merchant response after greeting (turn 1)
        conv_messages = context.get('messages', [])
        is_first_response = len(conv_messages) <= 1  # Only greeting in history
        
        # [2026-03-04] INSTRUCTOR MODE gets its own sprint prompt — training, not sales
        if _is_instructor:
            system = (
                "You are Alan, a sales rep in a TRAINING session on a live phone call. "
                "The person on this call is your instructor — they're coaching you. "
                "LISTEN to what they say. RESPOND to their actual words. "
                "Keep your response to 1-2 short sentences. Be natural and conversational. "
                "If they gave feedback → acknowledge it and try again or ask a follow-up. "
                "If they're role-playing a merchant → stay in character and respond naturally. "
                "If they asked you a question → answer it directly. "
                "If they said something casual → match their energy. Be a real person. "
                "A brief natural acknowledgment is fine: 'Right', 'Yeah', 'Got it'. "
                "NEVER say goodbye or end the call. "
                "NEVER pitch payment processing unless you're in an active role-play. "
                "NO lists, NO markdown. Just natural phone speech."
            )
        elif is_first_response:
            system = (
                "You are Alan, a payment processing consultant on a live phone call. "
                "You JUST greeted the merchant and asked for the owner. "
                "Their reply is the ANSWER to your question. "
                "Respond appropriately — explain why you're calling in 1-2 complete sentences. "
                "\n\n"
                "FIRST-RESPONSE RULES (match merchant's reply):\n"
                "- If they say 'thank you', 'thanks', 'sure', 'yeah', 'okay' → They're LISTENING. "
                "Launch directly into why you're calling. Do NOT fold, do NOT ask another question.\n"
                "- If they say 'speaking', 'this is [name]', 'that's me' → You have the owner. "
                "Launch directly into your pitch.\n"
                "- If they ask 'who is this?', 'what company?' → Identify yourself and pivot to pitch.\n"
                "- If they say 'can I take a message?', 'they're not here', 'hold on' → GATEKEEPER. "
                "Ask to speak with the owner/manager directly.\n"
                "- If they give a short acknowledgment like 'hello?', 'yes?' → "
                "Launch into why you're calling.\n"
                "\n"
                "Keep your response COMPLETE — a full thought that makes sense on its own. "
                "1-2 sentences max. End with a period, question mark, or natural pause. "
                "NEVER start with 'I appreciate you picking up' or any variant of that. "
                "NEVER say goodbye or any exit phrase. "
                "NO lists, NO markdown, NO formal language. Just natural phone speech."
            )
        else:
            system = (
                "You are Alan, a sharp payment processing consultant on a live phone call. "
                "Sound like a real person — direct, natural. "
                f"Current conversation mode: {mode}. "
            )
            if business_name:
                system += f"You're speaking with someone at {business_name}. "
            system += (
                "LISTEN to what they just said. Respond to THEIR words, not your script. "
                "Keep your response to 1-2 complete sentences that make sense on their own. "
                "A brief natural acknowledgment is OK before your point: 'Right', 'Yeah', 'Look'. "
                "NEVER repeat what you already said. Check the conversation history. "
                "If they gave information → use it to ask a sharper follow-up. "
                "If they asked a question → answer it directly. "
                "If they showed interest → deepen with a specific benefit or question. "
                "If they objected → counter with a specific benefit. "
                "If they asked 'how can I help you' or 'what do you need' → get specific: "
                "'Are you guys processing cards right now?' or 'So who handles the merchant services over there?' "
                "End with a period or question mark — your response should be COMPLETE. "
                "NEVER say 'I appreciate you letting me know', 'Thanks for that', 'Thanks for sharing'. "
                "NEVER say 'Sounds like you're in a good mood' or any comment about their mood/tone. "
                "NEVER say goodbye, 'have a good one', or 'take care' — the call is not over. "
                "NO lists, NO markdown, NO formal language. Just natural phone speech."
            )
        
        messages = [{"role": "system", "content": system}]
        
        # [LONG CONV] Adaptive history window — early turns need speed (4 messages),
        # deep turns (8+) need full context to avoid repetition (10 messages).
        # GPT-4o-mini has 128K context — 10 messages is ~2K tokens, negligible.
        _history_window = 10 if len(conv_messages) >= 8 else 4
        for msg in conv_messages[-_history_window:]:
            _u = msg.get('user', '')
            _a = msg.get('alan', '')
            if _u:
                messages.append({"role": "user", "content": _u})
            if _a:
                messages.append({"role": "assistant", "content": _a})
        
        messages.append({"role": "user", "content": user_text})
        
        return messages

    def _tts_sentence_sync(self, text, prev_text=None, next_text=None, prosody_intent="neutral", sentence_idx=0,
                           speed_bias=1.0, breath_prob_bias=0.0):
        """Synchronous TTS for one sentence. Runs in executor thread.
        Uses OpenAI TTS with prosody-aware instructions, returns mulaw 8kHz bytes."""
        return self._openai_tts_sync(text, prosody_intent=prosody_intent, sentence_idx=sentence_idx,
                                     speed_bias=speed_bias, breath_prob_bias=breath_prob_bias)

    async def _orchestrated_response(self, user_text, analysis, context, websocket, agent, generation=0):
        """
        ORCHESTRATED PIPELINE — LLM SSE → sentence detection → TTS → audio streaming.
        
        HUMAN MODEL: Just think and talk. If someone says something new
        (generation changes), stop gracefully. No locks, no safety nets.
        
        Returns: full_response_text (str) or None on failure.
        """
        stream_sid = context.get('streamSid')
        client_id = context.get('client_id')  # [FIX] Extract client_id for Behavioral Fusion lookups
        if not stream_sid or not websocket:
            logger.error("[ORCHESTRATED] No stream_sid or websocket. Cannot proceed.")
            return None

        # 1. BUILD LLM PROMPT (all injections: preferences, call memory, behavior, etc.)
        messages, prompt_user_text = agent.build_llm_prompt(analysis, context)
        api_key = agent.get_api_key()
        
        if not api_key:
            logger.error("[ORCHESTRATED] No API key available.")
            return None
        
        # [INSTRUCTOR MODE] Inject correction guidance into LLM context
        # If the instructor just gave a correction, on_instructor_turn detects it
        # and returns guidance that gets appended to the system prompt so Alan
        # adjusts his next response accordingly.
        _is_instructor_call = context.get('prospect_info', {}).get('instructor_mode', False)
        _inst_session = context.get('_instructor_session')
        if _inst_session and INSTRUCTOR_MODE_WIRED:
            _alan_last = ""
            _conv_msgs = context.get('messages', [])
            for _m in reversed(_conv_msgs):
                if _m.get('role') == 'assistant':
                    _alan_last = _m.get('content', _m.get('text', ''))
                    break
            _inst_guidance = on_instructor_turn(
                session=_inst_session,
                user_text=user_text,
                alan_last_utterance=_alan_last,
            )
            if _inst_guidance:
                # Append guidance to system message so Alan adjusts behavior
                if messages and messages[0].get('role') == 'system':
                    messages[0]['content'] += f"\n\n[INSTRUCTOR CORRECTION]\n{_inst_guidance}"
                logger.info(f"[INSTRUCTOR MODE] Correction guidance injected into LLM context")
        
        # [ORGAN 24] Inject Retrieval Cortex knowledge into LLM context
        # [2026-03-04] Skip for instructor mode — training calls don't need
        # retrieval cortex, competitive intel, objection learning, summarization,
        # CRM, IQ budget, or inbound context. These add thousands of tokens
        # that slow TTFT from ~800ms to 5+ seconds, causing dead air.
        _retrieval_ctx = context.get('_retrieval_context')
        if _retrieval_ctx and RETRIEVAL_CORTEX_WIRED and not _is_instructor_call:
            if messages and messages[0].get('role') == 'system':
                messages[0]['content'] += f"\n\n[RETRIEVAL CORTEX — RELEVANT KNOWLEDGE]\n{_retrieval_ctx}"
            logger.info(f"[ORGAN 24] Knowledge injected into LLM context ({len(_retrieval_ctx)} chars)")
        
        # [ORGAN 34] Inject Competitive Intel context into LLM system message
        _competitor_ctx = context.get('_competitor_context')
        if _competitor_ctx and COMPETITIVE_INTEL_WIRED and not _is_instructor_call:
            if messages and messages[0].get('role') == 'system':
                messages[0]['content'] += f"\n\n[COMPETITIVE INTEL — §4.9 POSITIONING]\n{_competitor_ctx}"
            logger.info(f"[ORGAN 34] Competitor context injected into LLM ({context.get('_detected_competitor')})")
        
        # [ORGAN 31] Inject objection learning context into LLM system message
        _obj_events = context.get('_objection_events', [])
        if _obj_events and OBJECTION_LEARNING_WIRED and not _is_instructor_call:
            _recent_objs = _obj_events[-3:]  # last 1-3 objections this call
            _obj_ctx_parts = []
            for _oe in _recent_objs:
                _fam = _oe.get('family', 'general_hesitation')
                _fam_desc = _FAMILY_DESCRIPTIONS.get(_fam, 'Unclassified')
                _obj_ctx_parts.append(
                    f"- Objection: \"{_oe['text'][:100]}\" → Family: {_fam.upper()} | "
                    f"Rebuttal: {_oe.get('rebuttal_ref', '—')} | "
                    f"Closing: {_oe.get('closing_style', '—')} | "
                    f"Emotion: {_oe.get('emotion', 'neutral')}"
                )
            _obj_ctx_parts.append(f"FAMILY GUIDANCE: {_fam_desc}")
            # Add promoted patterns as additional awareness
            if _objection_learning_organ:
                _promoted = _objection_learning_organ.get_promoted_patterns()
                if _promoted:
                    _obj_ctx_parts.append(f"LEARNED PATTERNS: {len(_promoted)} patterns evolved from field data")
            if messages and messages[0].get('role') == 'system':
                messages[0]['content'] += (
                    f"\n\n[OBJECTION LEARNING — LIVE OBJECTION CONTEXT]\n"
                    + '\n'.join(_obj_ctx_parts)
                )
            logger.info(f"[ORGAN 31] Objection context injected into LLM ({len(_recent_objs)} events)")

        # [ORGAN 32] Inject call summary / deal readiness context into LLM system message
        if SUMMARIZATION_WIRED and context.get('_summarization_organ') and context.get('_summary_state') == 'collecting' and not _is_instructor_call:
            try:
                _sum_organ_llm = context['_summarization_organ']
                _sum_ctx_parts = []
                # Inject live interest level if detected
                _sum_transcript = " ".join(t["text"] for t in _sum_organ_llm._transcript_buffer)
                _live_interest = _sum_organ_llm._detect_interest_level(_sum_transcript)
                if _live_interest and _live_interest != 'none':
                    _sum_ctx_parts.append(f"LIVE INTEREST LEVEL: {_live_interest.upper()}")
                # Inject objection count
                _live_objection_count = len(_sum_organ_llm._objection_events)
                if _live_objection_count > 0:
                    _sum_ctx_parts.append(f"OBJECTIONS THIS CALL: {_live_objection_count}")
                # Inject tone trend
                if _sum_organ_llm._tone_timeline:
                    _last_tone = _sum_organ_llm._tone_timeline[-1]
                    _sum_ctx_parts.append(f"LATEST TONE: {_last_tone.get('emotion', 'neutral')} (confidence: {_last_tone.get('confidence', 0):.2f})")
                # Inject retrieval usage
                if _sum_organ_llm._retrieval_hits:
                    _sum_ctx_parts.append(f"KNOWLEDGE RETRIEVED: {len(_sum_organ_llm._retrieval_hits)} items used")
                # Inject competitor mentions
                if _sum_organ_llm._competitive_intel_used:
                    _sum_ctx_parts.append(f"COMPETITORS MENTIONED: {', '.join(_sum_organ_llm._competitive_intel_used)}")
                # Only inject if we have meaningful context
                if _sum_ctx_parts and messages and messages[0].get('role') == 'system':
                    messages[0]['content'] += (
                        f"\n\n[CALL INTELLIGENCE — LIVE SUMMARY]\n"
                        + '\n'.join(_sum_ctx_parts)
                    )
                    logger.info(f"[ORGAN 32] Live summary context injected into LLM ({len(_sum_ctx_parts)} items)")
            except Exception as _sum_llm_err:
                logger.debug(f"[ORGAN 32] LLM injection failed (non-fatal): {_sum_llm_err}")

        # [ORGAN 33] Inject CRM pipeline context into LLM system message
        if CRM_INTEGRATION_WIRED and context.get('_crm_organ') and not _is_instructor_call:
            try:
                _crm_ctx_parts = []
                _crm_push_st = context.get('_crm_push_state', 'idle')
                _crm_result = context.get('_crm_push_result')
                if _crm_push_st == 'idle':
                    # CRM push hasn't happened yet — collect missing fields
                    _pi_crm = context.get('prospect_info', {})
                    _missing_crm = []
                    if not _pi_crm.get('email'):
                        _missing_crm.append('email')
                    if not _pi_crm.get('name') and not _pi_crm.get('company'):
                        _missing_crm.append('name or business name')
                    if _missing_crm:
                        _crm_ctx_parts.append(f"CRM FIELDS NEEDED: {', '.join(_missing_crm)}")
                        _crm_ctx_parts.append('RULE: Naturally ask for missing contact info before call ends.')
                elif _crm_push_st in ('queued', 'sent', SyncStatus.SENT.value if CRM_INTEGRATION_WIRED else 'sent'):
                    _crm_ctx_parts.append('CRM STATUS: Summary will be pushed to CRM after this call.')
                elif _crm_push_st in ('failed', SyncStatus.FAILED.value if CRM_INTEGRATION_WIRED else 'failed'):
                    _crm_ctx_parts.append('CRM STATUS: Push pending retry — no action needed from merchant.')
                if _crm_ctx_parts and messages and messages[0].get('role') == 'system':
                    messages[0]['content'] += (
                        f"\n\n[CRM INTEGRATION — PIPELINE CONTEXT]\n"
                        + '\n'.join(_crm_ctx_parts)
                    )
                    logger.info(f"[ORGAN 33] CRM pipeline context injected into LLM ({len(_crm_ctx_parts)} items)")
            except Exception as _crm_llm_err:
                logger.debug(f"[ORGAN 33] LLM injection failed (non-fatal): {_crm_llm_err}")

        # [ORGAN 35] Inject IQ Budget cognitive state into LLM system message
        if IQ_BUDGET_WIRED and context.get('_iq_budget_organ') and not _is_instructor_call:
            try:
                _iq_ctx_parts = []
                _iq_organ_llm = context['_iq_budget_organ']
                _iq_st = context.get('_iq_state', 'normal')
                _iq_burn_total = context.get('_iq_burn_total', 0)
                _iq_budget_val = _iq_organ_llm._budget
                _iq_remaining = max(0, _iq_budget_val - _iq_burn_total)
                _iq_prompt_complexity = _iq_organ_llm.get_prompt_complexity()
                _iq_ctx_parts.append(f"BURN STATE: {_iq_st.upper()}")
                _iq_ctx_parts.append(f"BUDGET: {_iq_burn_total}/{_iq_budget_val} spent ({_iq_remaining} remaining)")
                _iq_ctx_parts.append(f"PROMPT COMPLEXITY: {_iq_prompt_complexity}")
                # State-specific behavioral directives
                if _iq_st == 'normal':
                    _iq_ctx_parts.append("ALLOWED: Full reasoning, retrieval, competitive intel, multi-step logic.")
                elif _iq_st == 'high':
                    _iq_ctx_parts.append("ALLOWED: Standard reasoning, selective retrieval.")
                    _iq_ctx_parts.append("FORBIDDEN: Deep multi-step reasoning, unnecessary retrieval.")
                    _iq_ctx_parts.append("FALLBACK: Use simpler scripts, reduce reasoning depth.")
                elif _iq_st == 'critical':
                    _iq_ctx_parts.append("ALLOWED: Simple direct responses, warmth, clarity.")
                    _iq_ctx_parts.append("FORBIDDEN: Retrieval, competitive intel, complex objection handling, pressure, escalation.")
                    _iq_ctx_parts.append("FALLBACK: Prioritize rapport, use minimal-risk phrasing, slow pacing.")
                elif _iq_st == 'exhausted':
                    _iq_ctx_parts.append("ALLOWED: Minimal safe responses only.")
                    _iq_ctx_parts.append("FORBIDDEN: ALL complex operations. No retrieval, no intel, no multi-step reasoning.")
                    _iq_ctx_parts.append("FALLBACK: Re-establish rapport, re-ground conversation, prepare graceful wrap-up.")
                # Inject disabled organs list
                _iq_disabled = context.get('_iq_disabled_organs', [])
                if _iq_disabled:
                    _iq_ctx_parts.append(f"DISABLED ORGANS: {', '.join(_iq_disabled)}")
                if _iq_ctx_parts and messages and messages[0].get('role') == 'system':
                    messages[0]['content'] += (
                        f"\n\n[IQ BUDGET — COGNITIVE STATE]\n"
                        + '\n'.join(_iq_ctx_parts)
                    )
                    logger.info(f"[ORGAN 35] IQ Budget context injected into LLM (state={_iq_st})")
            except Exception as _iq_llm_err:
                logger.debug(f"[ORGAN 35] LLM injection failed (non-fatal): {_iq_llm_err}")

        # [ORGAN 29] Inject inbound context (callback memory) into LLM system message
        _ic_state_llm = context.get('_inbound_context_state', 'cold')
        _ic_ctx_llm = context.get('_inbound_context')
        if _ic_state_llm != 'cold' and _ic_ctx_llm and INBOUND_CONTEXT_WIRED and not _is_instructor_call:
            _ic_parts = []
            _ic_parts.append(f"CALLER STATUS: {_ic_state_llm.upper()} — {'returning caller' if _ic_state_llm == 'warm' else 'known lead'}")

            if _ic_ctx_llm.get('merchant_name'):
                _ic_parts.append(f"MERCHANT NAME: {_ic_ctx_llm['merchant_name']}")
            if _ic_ctx_llm.get('business_name'):
                _ic_parts.append(f"BUSINESS: {_ic_ctx_llm['business_name']}")
            if _ic_ctx_llm.get('lead_status'):
                _ic_parts.append(f"LEAD STATUS: {_ic_ctx_llm['lead_status']}")
            if _ic_ctx_llm.get('callback_reason'):
                _ic_parts.append(f"CALLBACK REASON: {_ic_ctx_llm['callback_reason']}")
            if _ic_ctx_llm.get('scheduled_callback'):
                _ic_parts.append(f"SCHEDULED CALLBACK: {_ic_ctx_llm['scheduled_callback']}")

            _prior = _ic_ctx_llm.get('prior_calls', [])
            if _prior:
                _ic_parts.append(f"PRIOR CALLS: {len(_prior)}")
                _last = _prior[0]
                if _last.get('summary'):
                    _ic_parts.append(f"LAST CALL SUMMARY: {_last['summary']}")
                if _last.get('date'):
                    _ic_parts.append(f"LAST CALL DATE: {_last['date']}")

            if _ic_ctx_llm.get('missing_notes'):
                _ic_parts.append(f"NOTES: {'; '.join(_ic_ctx_llm['missing_notes'])}")

            # Behavioral guidance
            if _ic_state_llm == 'warm':
                _ic_parts.append('RULE: Reference prior conversation naturally. Do NOT repeat info merchant already knows.')
                _ic_parts.append('RULE: Pick up where you left off — acknowledge the callback warmly.')
            else:
                _ic_parts.append('RULE: Acknowledge familiarity but do not assume details you do not have.')
                _ic_parts.append('RULE: Verify context with merchant before proceeding.')

            if _ic_parts and messages and messages[0].get('role') == 'system':
                messages[0]['content'] += (
                    f"\n\n[INBOUND CONTEXT \u2014 CALLBACK MEMORY]\n"
                    + '\n'.join(_ic_parts)
                )
                logger.info(f"[ORGAN 29] Inbound context injected into LLM (state={_ic_state_llm})")

        # [ORGAN 28] Inject calendar scheduling context into LLM system message
        _cal_state = context.get('_calendar_state', 'inactive')
        if _cal_state != 'inactive' and CALENDAR_ENGINE_WIRED:
            _cal_ctx_parts = []

            if _cal_state == 'proposed':
                _proposed_data = context.get('_calendar_proposed', {})
                _propose_result = _proposed_data.get('result', {})
                _all_slots = _proposed_data.get('all_slots', [])
                _cal_ctx_parts.append(f"STATUS: SLOT PROPOSED \u2014 awaiting merchant confirmation")
                _cal_ctx_parts.append(f"PROPOSED TIME: {_propose_result.get('start', 'unknown')}")
                _cal_ctx_parts.append(f"DURATION: {_propose_result.get('duration', 30)} minutes")
                if len(_all_slots) > 1:
                    _alt_displays = [s.get('display', '?') for s in _all_slots[1:3]]
                    _cal_ctx_parts.append(f"ALTERNATIVES: {', '.join(_alt_displays)}")
                _cal_ctx_parts.append('Confirm: "Does [proposed time] work for you?"')
                _cal_ctx_parts.append("RULE: Merchant must verbally confirm before booking is final.")

            elif _cal_state == 'confirmed':
                _booking = context.get('_calendar_booking', {})
                _cal_ctx_parts.append(f"STATUS: BOOKING CONFIRMED")
                _cal_ctx_parts.append(f"BOOKING ID: {_booking.get('booking_id', 'N/A')}")
                _cal_ctx_parts.append(f"TIME: {_booking.get('start', 'unknown')}")
                _cal_ctx_parts.append(f"CONFIRMATION: Will be sent via {_booking.get('confirmation_method', 'N/A')}")
                _cal_ctx_parts.append('Say: "You\'re all set! You\'ll receive a confirmation shortly."')

            elif _cal_state == 'declined':
                _cal_ctx_parts.append(f"STATUS: MERCHANT DECLINED ALL PROPOSED TIMES")
                _cal_ctx_parts.append('Offer: "No problem! When would be a better time for you?"')
                _cal_ctx_parts.append("Suggest merchant provides their preferred time or offer to call back.")

            if _cal_ctx_parts and messages and messages[0].get('role') == 'system':
                messages[0]['content'] += (
                    f"\n\n[CALENDAR ENGINE \u2014 SCHEDULING CONTEXT]\n"
                    + '\n'.join(_cal_ctx_parts)
                )
                logger.info(f"[ORGAN 28] Calendar context injected into LLM (state={_cal_state})")

        # [ORGAN 27] Inject language switch context into LLM system message
        _ls_switch_state = context.get('_language_switch_state', 'inactive')
        if _ls_switch_state != 'inactive' and LANGUAGE_SWITCH_WIRED:
            _ls_ctx_parts = []
            _ls_lang = context.get('_language_state', 'en')
            _ls_detected = context.get('_language_detected')
            _ls_conf = context.get('_language_confidence', 0.0)

            if _ls_switch_state == 'pending_confirm':
                _ls_organ = context.get('_language_organ')
                _confirm_prompt = _ls_organ.get_confirmation_prompt() if _ls_organ else ''
                _ls_ctx_parts.append(f"LANGUAGE DETECTION: {LANGUAGE_CONFIGS.get(_ls_detected, {}).get('name', _ls_detected)} detected (confidence: {_ls_conf:.2f})")
                _ls_ctx_parts.append(f"STATUS: Awaiting merchant confirmation")
                _ls_ctx_parts.append(f"ASK: {_confirm_prompt}")
                _ls_ctx_parts.append("RULE: Do not switch languages until the merchant confirms.")
            elif _ls_switch_state == 'switched':
                _lang_cfg = LANGUAGE_CONFIGS.get(_ls_lang, {})
                _ls_ctx_parts.append(f"ACTIVE LANGUAGE: {_lang_cfg.get('name', _ls_lang)}")
                _ls_ctx_parts.append(f"STATUS: Language switched successfully")
                if _lang_cfg.get('prompt_suffix'):
                    _ls_ctx_parts.append(f"INSTRUCTION:{_lang_cfg['prompt_suffix']}")
                _ls_ctx_parts.append("Respond entirely in the active language. Maintain professional tone and rapport.")
            elif _ls_switch_state == 'declined':
                _ls_ctx_parts.append(f"LANGUAGE: English (merchant declined switch to {LANGUAGE_CONFIGS.get(_ls_detected, {}).get('name', _ls_detected)})")
                _ls_ctx_parts.append("STATUS: Locked to English for this call. Do not offer to switch again.")

            if _ls_ctx_parts and messages and messages[0].get('role') == 'system':
                messages[0]['content'] += (
                    f"\n\n[LANGUAGE SWITCH — CONTEXT]\n"
                    + '\n'.join(_ls_ctx_parts)
                )
                logger.info(f"[ORGAN 27] Language context injected into LLM (state={_ls_switch_state}, lang={_ls_lang})")

        # [ORGAN 26] Inject outbound comms context into LLM system message
        _oc_sends = context.get('_outbound_sends', [])
        _oc_pending = context.get('_outbound_pending')
        if OUTBOUND_COMMS_WIRED and (_oc_sends or _oc_pending):
            _oc_ctx_parts = []
            if _oc_sends:
                _last_send = _oc_sends[-1]
                _oc_ctx_parts.append(f"LAST SEND: {_last_send.get('channel', 'unknown').upper()} — template: {_last_send.get('template', 'unknown')} — status: {_last_send.get('status', 'unknown')}")
                _oc_ctx_parts.append(f"Total messages sent this call: {len(_oc_sends)}")
            if _oc_pending:
                _pending_ch = _oc_pending.get('channel', 'unknown')
                if _pending_ch == 'sms':
                    _oc_ctx_parts.append("PENDING: Merchant requested a text but we don't have their phone number.")
                    _oc_ctx_parts.append('Ask: "Sure! What\'s the best number to text that to?"')
                elif _pending_ch == 'email':
                    _oc_ctx_parts.append("PENDING: Merchant requested an email but we don't have their email address.")
                    _oc_ctx_parts.append('Ask: "Of course! What\'s the best email to send that to?"')
                _oc_ctx_parts.append("RULE: Confirm the contact info before sending. Never guess.")
            if _oc_ctx_parts and messages and messages[0].get('role') == 'system':
                messages[0]['content'] += (
                    f"\n\n[OUTBOUND COMMS — FOLLOW-UP CONTEXT]\n"
                    + '\n'.join(_oc_ctx_parts)
                )
                logger.info(f"[ORGAN 26] Outbound context injected into LLM (sends={len(_oc_sends)}, pending={_oc_pending is not None})")

        # [ORGAN 25] Inject warm handoff escalation context into LLM system message
        _handoff_state = context.get('_handoff_state', 'inactive')
        if _handoff_state != 'inactive' and WARM_HANDOFF_WIRED:
            _ho_ctx_parts = []
            _ho_reason = context.get('_handoff_reason', 'unknown')
            if _handoff_state == 'pending_consent':
                _ho_ctx_parts.append(f"ESCALATION STATE: PENDING CONSENT")
                _ho_ctx_parts.append(f"REASON: {_ho_reason.upper().replace('_', ' ')}")
                if _ho_reason == 'merchant_request':
                    _ho_ctx_parts.append("The merchant has asked to speak with someone. Confirm and initiate the transfer.")
                    _ho_ctx_parts.append('Say something like: "Absolutely, let me connect you with our team lead. One moment please."')
                elif _ho_reason == 'deal_ready':
                    _ho_ctx_parts.append("The deal appears ready for a closer. Ask for consent before transferring.")
                    _ho_ctx_parts.append('Say something like: "This sounds like a great fit. Would it be okay if I connected you with my colleague who handles the account setup?"')
                elif _ho_reason == 'duration_exceeded':
                    _ho_ctx_parts.append("The call has been going for a while. Offer to connect with a specialist.")
                    _ho_ctx_parts.append('Say something like: "I want to make sure you get the best attention on this. Would you like me to connect you with our specialist who can finalize the details?"')
                _ho_ctx_parts.append("RULE: Never transfer without explicit merchant consent (§5.12 Rule 3).")
            elif _handoff_state == 'initiated':
                _ho_result = context.get('_handoff_result', {})
                _ho_ctx_parts.append(f"ESCALATION STATE: TRANSFER INITIATED")
                _ho_ctx_parts.append(f"CLOSER: {_ho_result.get('closer', 'team lead')}")
                _ho_ctx_parts.append("Stay on the line. Introduce the merchant to the closer when they join.")
                _ho_ctx_parts.append('Say something like: "I\'m connecting you now. While we wait, is there anything else you\'d like me to note for your account?"')
            elif _handoff_state == 'failover':
                _ho_ctx_parts.append(f"ESCALATION STATE: FAILOVER — no closer available")
                _ho_ctx_parts.append("Offer to schedule a callback. Do not leave the merchant hanging.")
                _ho_ctx_parts.append('Say something like: "It looks like our specialist is currently with another client. Can I schedule a callback at a time that works for you?"')
            if _ho_ctx_parts:
                if messages and messages[0].get('role') == 'system':
                    messages[0]['content'] += (
                        f"\n\n[WARM HANDOFF — ESCALATION CONTEXT]\n"
                        + '\n'.join(_ho_ctx_parts)
                    )
                logger.info(f"[ORGAN 25] Escalation context injected into LLM (state={_handoff_state})")
        
        # [ORGAN 30] Inject merchant emotional awareness into LLM context
        _pa_emotion = context.get('_prosody_emotion', 'neutral')
        _pa_confidence = context.get('_prosody_confidence', 0.0)
        _pa_strategy = context.get('_prosody_strategy')
        if _pa_emotion != 'neutral' and _pa_confidence >= 0.5 and PROSODY_ANALYSIS_WIRED:
            _pa_ctx_parts = [
                f"MERCHANT EMOTIONAL STATE: {_pa_emotion.upper()} (confidence: {_pa_confidence:.2f})",
            ]
            if _pa_strategy:
                _pa_ctx_parts.append(f"Recommended pacing: {_pa_strategy.get('pacing', 'normal')}")
                _pa_ctx_parts.append(f"Recommended tone: {_pa_strategy.get('tone', 'professional')}")
                _pa_ctx_parts.append(f"Priority: {_pa_strategy.get('priority', 'continue')}")
            _pa_ctx_parts.append("RULE: Tone is advisory, not authoritative. Never override explicit merchant statements.")
            if messages and messages[0].get('role') == 'system':
                messages[0]['content'] += f"\n\n[PROSODY ANALYSIS — EMOTIONAL CONTEXT]\n" + '\n'.join(_pa_ctx_parts)
            logger.info(f"[ORGAN 30] Emotional context injected into LLM ({_pa_emotion})")
        
        # [ORGAN 7] Detect prosody intent for this turn
        # This determines HOW Alan sounds — instructions, speed, and inter-sentence pause
        prosody_intent = detect_prosody_intent(context, analysis)
        # [ORGAN 30] Apply prosody mode override if Organ 30 detected strong emotion
        _prosody_override = context.get('_prosody_mode_override')
        if _prosody_override and PROSODY_ANALYSIS_WIRED:
            _original_intent = prosody_intent
            prosody_intent = _prosody_override
            logger.info(f"[ORGAN 30×ORGAN 7] Prosody intent: {_original_intent} → {prosody_intent} (§2.19 override)")
        prosody_silence = PROSODY_SILENCE_FRAMES.get(prosody_intent, SENTENCE_SILENCE_FRAMES)
        prosody_speed = PROSODY_SPEED.get(prosody_intent, TIMING.tts_default_speed)  # [TIMING CONFIG]
        
        # [ORGAN 11] Apply signature bias — learned from human interaction patterns
        eff_sig = context.get('_effective_signature')
        if eff_sig and SIGNATURE_ENGINE_WIRED:
            prosody_silence = get_prosody_silence_bias(eff_sig, prosody_silence)
            prosody_speed = get_prosody_speed_bias(eff_sig, prosody_speed)
            sig_speed_bias = eff_sig.speed_bias
            sig_breath_bias = eff_sig.breath_prob_bias
            logger.info(f"[PROSODY+SIG] Intent: {prosody_intent} | "
                       f"Silence: {prosody_silence} frames (~{prosody_silence * 20}ms) | "
                       f"Speed: {prosody_speed} | "
                       f"Sig bias: speed={eff_sig.speed_bias:.3f}, silence={eff_sig.silence_bias_frames:+d}, breath={eff_sig.breath_prob_bias:+.3f}")
        else:
            sig_speed_bias = 1.0
            sig_breath_bias = 0.0
            logger.info(f"[PROSODY] Base intent: {prosody_intent} | Silence: {prosody_silence} frames (~{prosody_silence * 20}ms) | Speed: {prosody_speed}")
        
        # Persist user message
        if prompt_user_text:
            agent.conversation_history.add_message("User", prompt_user_text)
        
        # 2. SENTENCE QUEUE — bridge between LLM thread and async TTS consumer
        sentence_q = thread_queue.Queue()
        # No artificial sentence cap — let the LLM say what needs to be said.
        # max_tokens provides the natural ceiling. A real person doesn't count sentences.

        # [SPECULATIVE DECODING] Sprint queue + prompt (built only if feature enabled)
        sprint_q = thread_queue.Queue()
        sprint_messages = self._build_sprint_prompt(user_text, context) if SPECULATIVE_DECODING_ENABLED else None

        # [LAG FIX] Capture session for closure — connection reuse across calls
        llm_session = self._llm_session

        # [RELAY DECOMPOSITION] Chatbot Immune System — extracted to chatbot_immune_system.py
        # Was ~270 lines inline here. Now a thin wrapper that delegates to the extracted module.
        # Contains: markdown cleanup, filler prefix stripping, chatbot phrase kills,
        # early-turn exit guard, and repetition detector (short + long phrase modes).
        def _clean_sentence(s):
            """Delegate to extracted chatbot_immune_system module."""
            return _chatbot_clean_sentence(s, context, logger)

        # 3. LLM SSE READER — runs in background thread, pushes sentences to queue
        def _llm_sentence_stream():
            """Read SSE tokens from OpenAI, detect sentence boundaries, push to queue."""
            url = "https://api.openai.com/v1/chat/completions"
            
            # [LONG CONV] Graduated adaptive max_tokens and max_sentences —
            # Turns 0-1 (ULTRA_FAST): 60 tokens — snappy first impression, avoids 5s+ LLM stalls
            # Turns 2-4 (FAST_PATH): 100 tokens — enough for a complete business answer
            # Turns 5-7 (MIDWEIGHT): 120 tokens — merchant is engaged, slightly fuller responses
            # Turns 8+ (FULL): 150 tokens — deep consultative conversation, detail expected
            # [2026-03-03] Lesson: Turn 2 hit 5.7s LLM deadline with 100 tokens, truncating to
            # "I get that, " — merchant heard weird audio, telephony health killed the call.
            # Fix: First 2 turns use 60 tokens (enough for 1-2 sentences) for speed.
            _conv_turn_count = len(context.get('messages', []))
            if _conv_turn_count >= 8:
                _adaptive_max_tokens = 150
                _adaptive_max_sentences = 5
            elif _conv_turn_count >= 5:
                _adaptive_max_tokens = 120
                _adaptive_max_sentences = 4
            elif _conv_turn_count >= 2:
                _adaptive_max_tokens = TIMING.relay_max_tokens  # 100 from timing_config.json
                _adaptive_max_sentences = TIMING.max_sentences
            else:
                _adaptive_max_tokens = 60  # Ultra-fast first impression
                _adaptive_max_sentences = 2
            
            payload = {
                "model": "gpt-4o-mini",
                "messages": messages,
                "temperature": TIMING.temperature,  # [TIMING CONFIG]
                "max_tokens": _adaptive_max_tokens,  # [LONG CONV] Adaptive — 45 early, 80 deep
                "frequency_penalty": TIMING.frequency_penalty,  # [TIMING CONFIG]
                "stream": True
            }
            headers = {"Authorization": f"Bearer {api_key}"}
            
            token_buffer = ""
            sentence_count = 0
            ttft_logged = False
            stream_start = time.time()
            
            MAX_SENTENCES = _adaptive_max_sentences  # [LONG CONV] Adaptive — 3 early, 5 deep
            
            # [LATENCY FIX] TTFT hard deadline — if OpenAI doesn't return a first
            # token within TTFT_DEADLINE_S, abort the stream and push a fallback sentence.
            # This prevents 5-9+ second dead air that causes instant hangups.
            # The fallback is a natural sales opener that keeps the call alive.
            TTFT_DEADLINE_S = 2.0  # Max seconds to wait for first token (was 2.5 — pre-warm ensures <800ms TTFT)
            TOTAL_LLM_DEADLINE_S = 3.5  # Max total LLM time (was 4.5 — 60 tokens early/100 mid never needs >3.5s)
            # [2026-03-03] Lowered from 4.5→3.5: With 60-token early turns, 3.5s is generous.
            # When deadline hits, we truncate gracefully + add bridge sentence.
            
            try:
                # [TIMING FIX] Read timeout tightened from 8s→3s to enforce TTFT deadline.
                # iter_lines() blocks until a line arrives, so the TTFT check inside the loop
                # never fires if OpenAI is slow to send the first line. A 3s read timeout
                # forces a ReadTimeout exception which triggers the fallback path below.
                with llm_session.post(url, json=payload, headers=headers, stream=True, timeout=(2, 3)) as response:
                    response.raise_for_status()
                    for line in response.iter_lines(decode_unicode=True):
                        if not line or not line.startswith('data: '):
                            # [LATENCY FIX] Check TTFT deadline even on empty lines
                            if not ttft_logged and (time.time() - stream_start) > TTFT_DEADLINE_S:
                                logger.error(f"[LLM] TTFT DEADLINE EXCEEDED ({TTFT_DEADLINE_S}s) — aborting stream, pushing fallback")
                                _telemetry['ttft_ms'] = 1000 * TTFT_DEADLINE_S
                                _telemetry['ttft_deadline_hit'] = True
                                # [2026-03-03 FIX] Bridge-aware TTFT fallback.
                                # If a bridge phrase already played ("Good question..."),
                                # the fallback must continue naturally from it.
                                if context.get('_bridge_sent'):
                                    _ttft_bridge = [
                                        "who handles the card processing for you guys right now?",
                                        "what system are you using for payments currently?",
                                        "are you set up to take cards there?",
                                    ]
                                    sentence_q.put(random.choice(_ttft_bridge))
                                else:
                                    sentence_q.put("So who handles the card processing for you guys?")
                                sentence_count = 1
                                break
                            # [LATENCY FIX] Check total deadline
                            if (time.time() - stream_start) > TOTAL_LLM_DEADLINE_S:
                                logger.error(f"[LLM] TOTAL DEADLINE EXCEEDED ({TOTAL_LLM_DEADLINE_S}s) — aborting")
                                break
                            continue
                        data_str = line[6:]
                        if data_str == '[DONE]':
                            break
                        # [LATENCY FIX] Check total deadline mid-stream
                        if (time.time() - stream_start) > TOTAL_LLM_DEADLINE_S:
                            logger.error(f"[LLM] TOTAL DEADLINE hit at {(time.time() - stream_start):.1f}s — truncating")
                            break
                        try:
                            chunk = json.loads(data_str)
                            delta = chunk['choices'][0]['delta'].get('content', '')
                            if delta:
                                if not ttft_logged:
                                    ttft_ms = 1000 * (time.time() - stream_start)
                                    logger.info(f"[LLM] First token in {ttft_ms:.0f}ms")
                                    ttft_logged = True
                                    _telemetry['ttft_ms'] = ttft_ms
                                    # [INSTRUMENT] LLM first token relative to vad_end
                                    _telemetry['llm_first_token_ms'] = round(1000 * (time.monotonic() - _mono_base), 1)
                                
                                token_buffer += delta
                                
                                # Detect sentence on punctuation immediately.
                                # Don't wait for text AFTER the period — that
                                # wastes a full token of latency (~30-50ms).
                                #
                                # [EARLY-FIRE] If no sentence punctuation after 30+ chars,
                                # fire at first comma/semicolon boundary. Gets TTS started
                                # ~200-400ms earlier on long first sentences.
                                while True:
                                    # Try split on punct + trailing text first
                                    parts = re.split(r'(?<=[.!?])\s+', token_buffer, maxsplit=1)
                                    if len(parts) > 1:
                                        sentence = _clean_sentence(parts[0])
                                        token_buffer = parts[1]
                                        if sentence and len(sentence) > 3:
                                            if sentence_count >= MAX_SENTENCES:
                                                logger.info(f"[LLM] Sentence cap hit ({MAX_SENTENCES}). Dropping: '{sentence[:50]}'")
                                            else:
                                                sentence_q.put(sentence)
                                                sentence_count += 1
                                                logger.info(f"[LLM] Sentence {sentence_count}: '{sentence[:50]}'")
                                    # Buffer ends with sentence punctuation — fire immediately
                                    elif re.search(r'[.!?]$', token_buffer.strip()):
                                        sentence = _clean_sentence(token_buffer)
                                        token_buffer = ""
                                        if sentence and len(sentence) > 3:
                                            if sentence_count >= MAX_SENTENCES:
                                                logger.info(f"[LLM] Sentence cap hit ({MAX_SENTENCES}). Dropping: '{sentence[:50]}'")
                                            else:
                                                sentence_q.put(sentence)
                                                sentence_count += 1
                                                logger.info(f"[LLM] Sentence {sentence_count} (end): '{sentence[:50]}'")
                                    # [EARLY-FIRE] Long buffer with no sentence punct —
                                    # fire at comma/semicolon to start TTS sooner.
                                    # Only for first sentence (subsequent benefit from pipeline overlap).
                                    elif sentence_count == 0 and len(token_buffer) > 30:
                                        clause_m = re.search(r'[,;]\s+', token_buffer[12:])
                                        if clause_m:
                                            split_at = 12 + clause_m.end()
                                            fragment = _clean_sentence(token_buffer[:split_at])
                                            token_buffer = token_buffer[split_at:]
                                            if fragment and len(fragment) > 8:
                                                sentence_q.put(fragment)
                                                sentence_count += 1
                                                logger.info(f"[LLM] EARLY-FIRE clause: '{fragment[:50]}'")
                                        break  # Always break after early-fire attempt
                                    else:
                                        break
                        except (json.JSONDecodeError, KeyError, IndexError):
                            pass
                
                # Push remaining buffer as final sentence
                # [2026-03-03] If we hit the deadline mid-stream and have an incomplete
                # fragment (e.g. "I get that, "), append a natural bridge so it doesn't
                # sound cut off. This prevents the "you sound kind of weird" reaction.
                if token_buffer.strip():
                    final = _clean_sentence(token_buffer)
                    if final and len(final) > 3:
                        # Check if fragment looks incomplete (no sentence-ending punct)
                        _ends_clean = final.rstrip().endswith(('.', '!', '?'))
                        if not _ends_clean and _telemetry.get('ttft_deadline_hit') or \
                           (not _ends_clean and (time.time() - stream_start) >= TOTAL_LLM_DEADLINE_S * 0.9):
                            # Deadline-truncated fragment — add bridge
                            _bridge_phrases = [
                                "but hey, who handles the card processing for you guys?",
                                "anyway, do you guys take card payments there?",
                                "but real quick, are you set up to take cards?",
                            ]
                            final = final.rstrip().rstrip(',;—–-') + " — " + random.choice(_bridge_phrases)
                            logger.info(f"[LLM] Deadline bridge applied: '{final[:60]}'")
                        sentence_q.put(final)
                        sentence_count += 1
                
                elapsed = 1000 * (time.time() - stream_start)
                logger.info(f"[LLM] Complete. {sentence_count} sentences in {elapsed:.0f}ms")
                _telemetry['llm_ms'] = elapsed
                _telemetry['llm_done_ms'] = round(1000 * (time.monotonic() - _mono_base), 1)
                
            except Exception as e:
                logger.error(f"[ORCHESTRATED LLM] SSE error: {e}")
                # [TIMING FIX] If the LLM stream failed before producing any sentences,
                # push a natural fallback so there's no dead air. This catches ReadTimeout,
                # ConnectionError, and any other LLM failure before first sentence.
                if sentence_count == 0:
                    import requests.exceptions as _req_exc
                    is_timeout = isinstance(e, (_req_exc.ReadTimeout, _req_exc.ConnectTimeout, _req_exc.ConnectionError))
                    if is_timeout:
                        logger.warning(f"[LLM] [TIMING GUARD] LLM timeout before first sentence — pushing fallback")
                    else:
                        logger.warning(f"[LLM] [TIMING GUARD] LLM error before first sentence — pushing fallback: {type(e).__name__}")
                    _telemetry['ttft_deadline_hit'] = True
                    # [2026-03-03 FIX] Bridge-aware SSE error fallback.
                    if context.get('_bridge_sent'):
                        _sse_bridge = [
                            "who handles the card processing for you guys right now?",
                            "do you mind if I ask what you're paying on your processing?",
                            "what system are you using for payments currently?",
                        ]
                        sentence_q.put(random.choice(_sse_bridge))
                    else:
                        sentence_q.put("Hey, I'm still with you \u2014 are you guys set up to take cards there?")
                    sentence_count = 1
            
            sentence_q.put(None)  # Sentinel: stream complete

        # [SPECULATIVE DECODING] Sprint LLM stream — tiny prompt, fast first clause
        def _sprint_sentence_stream():
            """Sprint LLM call: minimal prompt, max_tokens=30, one opening clause.
            
            Runs concurrently with _llm_sentence_stream. The shorter prompt
            (~200 tokens vs ~3000+) means OpenAI returns the first token faster.
            We only need one clause from this — the opening words that buy time
            while the full response generates.
            """
            if not sprint_messages:
                sprint_q.put(None)
                return
            
            url = "https://api.openai.com/v1/chat/completions"
            payload = {
                "model": "gpt-4o-mini",
                "messages": sprint_messages,
                "temperature": TIMING.temperature,
                "max_tokens": SPRINT_MAX_TOKENS,
                "stream": True
            }
            headers = {"Authorization": f"Bearer {api_key}"}
            
            token_buffer = ""
            sprint_start = time.time()
            clause_sent = False
            sprint_ttft_logged = False
            
            try:
                with llm_session.post(url, json=payload, headers=headers, stream=True, timeout=(2, 4)) as response:
                    response.raise_for_status()
                    for line in response.iter_lines(decode_unicode=True):
                        if not line or not line.startswith('data: '):
                            continue
                        data_str = line[6:]
                        if data_str == '[DONE]':
                            break
                        try:
                            chunk = json.loads(data_str)
                            delta = chunk['choices'][0]['delta'].get('content', '')
                            if delta:
                                if not sprint_ttft_logged:
                                    sprint_ttft_ms = 1000 * (time.time() - sprint_start)
                                    logger.info(f"[SPECULATIVE] Sprint TTFT: {sprint_ttft_ms:.0f}ms")
                                    sprint_ttft_logged = True
                                
                                token_buffer += delta
                                
                                # Fire on sentence-end, comma, dash, or length threshold
                                stripped = token_buffer.strip()
                                if (re.search(r'[.!?,;—–\-]\s*$', stripped) and len(stripped) > 8) or len(stripped) > 60:
                                    # Clean the clause (reuse chatbot killer patterns)
                                    clause = re.sub(r'\*\*([^*]+)\*\*', r'\1', stripped)
                                    clause = re.sub(r'^[-*]\s+', '', clause)
                                    clause = clause.strip()
                                    
                                    if clause and len(clause) > 5:
                                        sprint_q.put(clause)
                                        clause_sent = True
                                        elapsed = 1000 * (time.time() - sprint_start)
                                        logger.info(f"[SPECULATIVE] Sprint clause ready in {elapsed:.0f}ms: '{clause[:60]}'")
                                    break  # Sprint: ONE clause only
                        except (json.JSONDecodeError, KeyError, IndexError):
                            pass
                
                # Push remaining buffer if no clause was sent yet
                if not clause_sent and token_buffer.strip():
                    clause = token_buffer.strip()
                    if clause and len(clause) > 5:
                        sprint_q.put(clause)
                        elapsed = 1000 * (time.time() - sprint_start)
                        logger.info(f"[SPECULATIVE] Sprint remainder in {elapsed:.0f}ms: '{clause[:60]}'")
                
                total_elapsed = 1000 * (time.time() - sprint_start)
                _telemetry['sprint_ms'] = total_elapsed
                
            except Exception as e:
                logger.error(f"[SPECULATIVE] Sprint LLM error: {e}")
            
            sprint_q.put(None)  # Sentinel: sprint complete

        # 4. START LLM IN BACKGROUND THREAD
        loop = asyncio.get_running_loop()
        # [CW20 STEP 6] Latency telemetry — shared timing container between LLM thread and TTS consumer
        _telemetry = {
            'llm_ms': None, 'ttft_ms': None, 'tts_total_ms': 0.0,
            'ttfa_ms': None, 'sprint_ms': None,
            # [INSTRUMENT] Stage-level monotonic timestamps (ms)
            'vad_end_ms': None, 'stt_done_ms': None, 'env_done_ms': None,
            'llm_start_ms': None, 'llm_first_token_ms': None, 'llm_done_ms': None,
            'tts_start_ms': None, 'tts_first_audio_ms': None, 'play_start_ms': None,
        }
        # [INSTRUMENT] Capture upstream timestamps from context
        _mono_base = context.get('_vad_end_mono') or time.monotonic()
        _telemetry['vad_end_ms'] = 0.0  # reference point
        if context.get('_stt_done_mono'):
            _telemetry['stt_done_ms'] = round(1000 * (context['_stt_done_mono'] - _mono_base), 1)
        if context.get('_env_done_mono'):
            _telemetry['env_done_ms'] = round(1000 * (context['_env_done_mono'] - _mono_base), 1)
        _telemetry['llm_start_ms'] = round(1000 * (time.monotonic() - _mono_base), 1)
        llm_future = loop.run_in_executor(self.executor, _llm_sentence_stream)
        
        # [SPECULATIVE DECODING] Fire sprint concurrently with full LLM
        sprint_future = None
        if SPECULATIVE_DECODING_ENABLED and sprint_messages:
            sprint_future = loop.run_in_executor(self.executor, _sprint_sentence_stream)
            logger.info("[SPECULATIVE] Sprint + Full LLM fired concurrently")
        
        # 5. CONSUME SENTENCES — TTS and stream each AS IT ARRIVES
        full_response_text = ""
        sentence_idx = 0
        total_frames = 0
        pipeline_start = time.time()
        first_audio_logged = False
        prev_sentence_text = None
        question_count = 0  # [QUESTION CAP] Track questions — drop 2nd+ to prevent double-question pattern
        
        # TTS prefetch state
        prefetch_future = None
        prefetch_sentence_text = None
        
        # === [SPECULATIVE DECODING] Sprint Consumption Phase ===
        # Drain sprint queue first — get the opening clause to TTS immediately.
        # This produces audio ~500-800ms faster than waiting for the full response.
        _sprint_text = ""
        _spec_skip_first_full = False
        
        if sprint_future is not None:
            _sprint_t0 = time.time()
            _sprint_deadline = _sprint_t0 + 3.0  # Max 3s wait for sprint
            
            while time.time() < _sprint_deadline:
                if context.get('response_generation') != generation:
                    logger.info("[SPECULATIVE] Sprint superseded by new speech. Aborting sprint.")
                    break
                try:
                    sprint_sentence = sprint_q.get_nowait()
                except thread_queue.Empty:
                    await asyncio.sleep(0.003)
                    continue
                
                if sprint_sentence is None:
                    break  # Sprint done
                
                logger.info(f"[SPECULATIVE] Sprint clause arrived: '{sprint_sentence}'")
                
                # [FIX CW-AUDIT 2025-06-24] Run chatbot killer + exit guard on sprint output.
                # Previously sprint bypassed ALL protection systems — chatbot filler like
                # "I appreciate you letting me know" and exit phrases went straight to TTS.
                # Now sprint gets the same sentence cleaning as full LLM output.
                # [2026-03-04] is_sprint=True uses lighter filtering — sprint generates
                # short complete thoughts, not fragments. Aggressive contains-match kills
                # were destroying ~50% of sprint output, forcing slow LLM fallback.
                sprint_sentence = _chatbot_clean_sentence(sprint_sentence, context, logger, is_sprint=True)
                if not sprint_sentence or len(sprint_sentence) <= 3:
                    logger.warning(f"[SPECULATIVE] Sprint clause killed by chatbot killer. Falling through to full LLM.")
                    continue
                
                # TTS synthesis — immediate, no prefetch complexity needed
                _tts_t0 = time.time()
                # [INSTRUMENT] Stamp TTS start for sprint path
                if _telemetry.get('tts_start_ms') is None:
                    _telemetry['tts_start_ms'] = round(1000 * (time.monotonic() - _mono_base), 1)
                sprint_audio = await loop.run_in_executor(
                    self.executor,
                    self._tts_sentence_sync,
                    sprint_sentence, None, None, prosody_intent, 0,
                    sig_speed_bias, sig_breath_bias
                )
                _telemetry['tts_total_ms'] += 1000 * (time.time() - _tts_t0)
                
                if sprint_audio:
                    _sprint_text = sprint_sentence
                    full_response_text = sprint_sentence + " "
                    sentence_idx = 1
                    
                    # [INSTRUMENT] TTS produced audio
                    if _telemetry.get('tts_first_audio_ms') is None:
                        _telemetry['tts_first_audio_ms'] = round(1000 * (time.monotonic() - _mono_base), 1)
                    
                    # First audio tracking
                    if not first_audio_logged:
                        ttfa = 1000 * (time.time() - pipeline_start)
                        logger.info(f"[SPECULATIVE] ★ FIRST AUDIO in {ttfa:.0f}ms (sprint)")
                        first_audio_logged = True
                        _telemetry['ttfa_ms'] = ttfa
                        # [INSTRUMENT] First frame to Twilio
                        _telemetry['play_start_ms'] = round(1000 * (time.monotonic() - _mono_base), 1)
                        context['audio_playing'] = True
                        context['twilio_playback_done'] = False
                        context['first_audio_produced'] = True
                    
                    # Stream audio frames to Twilio (fast pacing — sprint is short)
                    offset = 0
                    sprint_frame = 0
                    while offset < len(sprint_audio):
                        if context.get('response_generation') != generation:
                            logger.info("[SPECULATIVE] Mid-frame interrupt during sprint.")
                            break
                        end = min(offset + FRAME_SIZE, len(sprint_audio))
                        frame = sprint_audio[offset:end]
                        offset = end
                        if len(frame) < FRAME_SIZE:
                            frame = frame + ULAW_SILENCE_BYTE * (FRAME_SIZE - len(frame))
                        b64_data = base64.b64encode(frame).decode("utf-8")
                        payload = {"event": "media", "streamSid": stream_sid, "media": {"payload": b64_data}}
                        try:
                            if hasattr(websocket, 'send_text'):
                                await websocket.send_text(json.dumps(payload))
                            else:
                                await websocket.send(json.dumps(payload))
                        except Exception as _ws_err:
                            logger.debug(f"[SPECULATIVE] Frame send error: {_ws_err}")
                            break
                        # Fast pacing for sprint — minimal ramp then cruise
                        if sprint_frame < 3:
                            await asyncio.sleep(0.001)
                        else:
                            await asyncio.sleep(0.012)
                        total_frames += 1
                        sprint_frame += 1
                    
                    _spec_skip_first_full = True
                    prev_sentence_text = sprint_sentence
                
                break  # Sprint: only first clause
            
            _sprint_elapsed = 1000 * (time.time() - _sprint_t0)
            if _sprint_text:
                logger.info(f"[SPECULATIVE] Sprint phase complete: '{_sprint_text}' ({_sprint_elapsed:.0f}ms)")
            else:
                logger.info(f"[SPECULATIVE] Sprint phase empty ({_sprint_elapsed:.0f}ms) — full response takes over")
        
        # === Main Consumption Loop ===
        while True:
            # If we have a prefetched sentence (already consumed from queue),
            # use it directly instead of polling the queue again
            if prefetch_future is not None and prefetch_sentence_text is not None:
                sentence = prefetch_sentence_text
                # prefetch_future will be awaited in the TTS section below
                # (the check `if prefetch_future is not None: raw_audio = await ...`)
                prefetch_sentence_text = None  # Consumed
            else:
                # Normal path: poll the sentence queue
                try:
                    sentence = sentence_q.get_nowait()
                except thread_queue.Empty:
                    await asyncio.sleep(0.003)  # 3ms poll — minimal latency
                    continue
            
            if sentence is None:
                break  # LLM done
            
            # [SPECULATIVE DECODING] Skip first full sentence if sprint already covered it
            if _spec_skip_first_full:
                _spec_skip_first_full = False
                if _sprint_text:
                    sprint_words = set(_sprint_text.lower().split())
                    sent_words = set(sentence.lower().split())
                    overlap = len(sprint_words & sent_words) / len(sent_words) if sent_words else 0
                    # [FIX 2026-02-26] ALWAYS skip the first full sentence when sprint was used.
                    # Previously, diverged sentences (low overlap) caused both to play → stuttering.
                    # Sprint already gave the listener a coherent opening. Playing a DIFFERENT
                    # first sentence on top creates "I work with businesses — It's Alan from" stutter.
                    logger.info(f"[SPECULATIVE] Skipping first full sentence (overlap {overlap:.0%}, sprint played): '{sentence[:60]}'")
                    prev_sentence_text = sentence
                    sentence_idx += 1
                    continue
            
            # Check if superseded by new speech
            if context.get('response_generation') != generation:
                logger.info(f"[ORCHESTRATED] Superseded at sentence {sentence_idx+1} (gen {generation} vs {context.get('response_generation')}). Stopping.")
                break
            
            # QUICK COMPLIANCE CHECK (per-sentence — fast, ~5ms)
            try:
                sentence, meta = self.coordinator.process_llm_output(sentence, context)
            except Exception as _comp_err:
                logger.debug(f"[COMPLIANCE] Per-sentence check failed: {_comp_err}")
            
            if self.supervisor_instance:
                try:
                    if not self.supervisor_instance.validate_response_compliance(sentence, context):
                        sentence = "So tell me — what's going on with your setup over there?"
                except Exception as _val_err:
                    logger.debug(f"[COMPLIANCE] Supervisor validation failed: {_val_err}")
            
            # [QUESTION CAP] One question per turn — drop extras
            # Prevents "Do you have a website? And how are you handling payments?"
            # and "Does that make sense? Any questions on that?" patterns.
            if sentence.rstrip().endswith('?'):
                question_count += 1
                if question_count > 1:
                    logger.info(f"[QUESTION CAP] Dropping extra question #{question_count}: '{sentence[:60]}'")
                    prev_sentence_text = sentence
                    sentence_idx += 1
                    continue
            
            logger.info(f"[ORCHESTRATED] Sentence {sentence_idx+1}: '{sentence[:60]}'")
            
            # Accumulate full response
            if full_response_text:
                full_response_text += " "
            full_response_text += sentence
            
            # TTS — check if we have a prefetched result
            if prefetch_future is not None:
                _tts_t0 = time.time()
                raw_audio = await prefetch_future
                _telemetry['tts_total_ms'] += 1000 * (time.time() - _tts_t0)
                prefetch_future = None
            else:
                # [ORGAN 7] Per-sentence prosody refinement
                # Peek queue to check if this is the last sentence
                is_last = sentence_q.empty()
                sentence_prosody = refine_prosody_per_sentence(sentence, prosody_intent, is_last_sentence=is_last)
                if sentence_prosody != prosody_intent:
                    logger.info(f"[PROSODY REFINE] {prosody_intent} → {sentence_prosody} for: '{sentence[:50]}'")
                # First sentence — synthesize now (with refined prosody)
                _tts_t0 = time.time()
                # [INSTRUMENT] Stamp TTS start for main path
                if _telemetry.get('tts_start_ms') is None:
                    _telemetry['tts_start_ms'] = round(1000 * (time.monotonic() - _mono_base), 1)
                raw_audio = await loop.run_in_executor(
                    self.executor,
                    self._tts_sentence_sync,
                    sentence, prev_sentence_text, None, sentence_prosody, sentence_idx,
                    sig_speed_bias, sig_breath_bias
                )
                _telemetry['tts_total_ms'] += 1000 * (time.time() - _tts_t0)
            
            if not raw_audio:
                logger.warning(f"[ORCHESTRATED] No audio for sentence {sentence_idx+1}. Skipping.")
                prev_sentence_text = sentence
                sentence_idx += 1
                continue
            
            if not first_audio_logged:
                ttfa = 1000 * (time.time() - pipeline_start)
                logger.info(f"[ORCHESTRATED] FIRST AUDIO in {ttfa:.0f}ms")
                first_audio_logged = True
                _telemetry['ttfa_ms'] = ttfa
                # [INSTRUMENT] TTS first audio + play start for main path
                if _telemetry.get('tts_first_audio_ms') is None:
                    _telemetry['tts_first_audio_ms'] = round(1000 * (time.monotonic() - _mono_base), 1)
                _telemetry['play_start_ms'] = round(1000 * (time.monotonic() - _mono_base), 1)
                # [ECHO FIX] Signal that Alan is now actively talking.
                # This activates the high-threshold VAD mode and stops 
                # feeding STT with audio (which would be Alan's own echo).
                context['audio_playing'] = True
                context['twilio_playback_done'] = False
                # [ACCUMULATOR] Signal that this pipeline has produced audio.
                # Any new STT text from this point is a REAL interrupt, not a
                # continuation of the caller's thought.
                context['first_audio_produced'] = True
            
            # PREFETCH next sentence TTS while we stream current audio
            # If the next sentence is already in the queue, start synthesizing it now.
            # The prefetch_future + prefetch_text are consumed in the NEXT loop iteration.
            if prefetch_future is None:
                try:
                    next_sentence_peek = sentence_q.get_nowait()
                    if next_sentence_peek is not None:
                        # Run compliance on the prefetched sentence
                        try:
                            next_sentence_peek, _ = self.coordinator.process_llm_output(next_sentence_peek, context)
                        except Exception as _comp_err:
                            logger.debug(f"[COMPLIANCE] Prefetch sentence check failed: {_comp_err}")
                        if self.supervisor_instance:
                            try:
                                if not self.supervisor_instance.validate_response_compliance(next_sentence_peek, context):
                                    next_sentence_peek = "So tell me — what's going on with your setup over there?"
                            except Exception as _val_err:
                                logger.debug(f"[COMPLIANCE] Prefetch supervisor validation failed: {_val_err}")
                        
                        # [ORGAN 7] Per-sentence prosody refinement for prefetched sentence
                        # Peek once more to see if this prefetched sentence is likely the last
                        prefetch_is_last = sentence_q.empty()
                        prefetch_prosody = refine_prosody_per_sentence(next_sentence_peek, prosody_intent, is_last_sentence=prefetch_is_last)
                        if prefetch_prosody != prosody_intent:
                            logger.info(f"[PROSODY REFINE PREFETCH] {prosody_intent} → {prefetch_prosody} for: '{next_sentence_peek[:50]}'")
                        # Start TTS in background — will be awaited in next iteration
                        prefetch_future = loop.run_in_executor(
                            self.executor,
                            self._tts_sentence_sync,
                            next_sentence_peek, sentence, None, prefetch_prosody, sentence_idx + 1,
                            sig_speed_bias, sig_breath_bias
                        )
                        # Store the text so the main loop can accumulate it without re-processing
                        prefetch_sentence_text = next_sentence_peek
                        logger.info(f"[ORCHESTRATED PREFETCH] Started TTS for next sentence in background")
                    else:
                        sentence_q.put(None)  # Put sentinel back — we're done
                except thread_queue.Empty:
                    pass  # Next sentence not ready yet — will be picked up next iteration
            
            # ENCODER UNIFICATION — REMOVED
            # TTS returns ulaw_8000 directly. Converting ulaw→pcm→ulaw was waste.
            # Old code: pcm16 = audioop.ulaw2lin(raw_audio, 2); raw_audio = audioop.lin2ulaw(pcm16, 2)
            
            # [ORGAN 7] INTER-SENTENCE SILENCE — adaptive to prosody intent
            # Empathetic turns breathe longer (~240ms). Closing turns keep momentum (~100ms).
            if sentence_idx > 0 and stream_sid:
                for _ in range(prosody_silence):
                    comfort_frame = generate_comfort_noise_frame()
                    b64_silence = base64.b64encode(comfort_frame).decode("utf-8")
                    payload = {"event": "media", "streamSid": stream_sid, "media": {"payload": b64_silence}}
                    try:
                        if hasattr(websocket, 'send_text'):
                            await websocket.send_text(json.dumps(payload))
                        else:
                            await websocket.send(json.dumps(payload))
                    except Exception as _ws_err:
                        logger.debug(f"[ORCHESTRATED] Inter-sentence silence frame send failed: {_ws_err}")
                    await asyncio.sleep(0.012)  # Tighter inter-sentence pacing
                    total_frames += 1
            
            # STREAM AUDIO FRAMES TO TWILIO
            # [VERSION R+ NEG-PROOF] ADAPTIVE FRAME PACING
            # Like an orchestra warming up: first notes are careful, then the ensemble
            # finds its tempo. As the conversation progresses, Twilio's jitter buffer
            # stabilizes and we can pace tighter.
            #
            # Two dimensions:
            #   1. Frame position within this audio (early = gentle, later = real-time)
            #   2. Conversation maturity (first response = cold, later = warm)
            #
            # Pacing schedule per frame:
            #   Cold start (sentence_idx == 0, first response):
            #     frames 0-4:   0.003s  (minimal warm-up)
            #     frames 5-15:  0.001s  (fast ramp)
            #     frames 16+:   0.012s  (real-time cruise)
            #   Warm (sentence_idx > 0 or messages > 2):
            #     frames 0-3:   0.001s  (near-instant prime)
            #     frames 4+:    0.012s  (real-time cruise)
            #
            conversation_age = len(context.get('messages', []))
            is_cold_start = (sentence_idx == 0 and conversation_age < 2)
            
            offset = 0
            sentence_frame = 0  # Frame counter within THIS sentence
            while offset < len(raw_audio):
                if context.get('response_generation') != generation:
                    logger.info(f"[ORCHESTRATED] Mid-frame interrupt. Aborting.")
                    break
                
                end = min(offset + FRAME_SIZE, len(raw_audio))
                frame = raw_audio[offset:end]
                offset = end
                
                if len(frame) < FRAME_SIZE:
                    frame = frame + ULAW_SILENCE_BYTE * (FRAME_SIZE - len(frame))
                
                b64_data = base64.b64encode(frame).decode("utf-8")
                payload = {"event": "media", "streamSid": stream_sid, "media": {"payload": b64_data}}
                
                try:
                    if hasattr(websocket, 'send_text'):
                        await websocket.send_text(json.dumps(payload))
                    else:
                        await websocket.send(json.dumps(payload))
                except Exception as e:
                    logger.error(f"[ORCHESTRATED] Send Error: {e}")
                
                # ADAPTIVE PACING — the conductor's tempo
                if is_cold_start:
                    # Cold jitter buffer: minimal ramp
                    if sentence_frame < 5:
                        await asyncio.sleep(0.003)
                    elif sentence_frame < 15:
                        await asyncio.sleep(0.001)
                    else:
                        await asyncio.sleep(0.012)
                else:
                    # Warm buffer: near-instant then cruise
                    if sentence_frame < 3:
                        await asyncio.sleep(0.001)
                    else:
                        await asyncio.sleep(0.012)
                
                total_frames += 1
                sentence_frame += 1
            
            prev_sentence_text = sentence
            sentence_idx += 1
        
        # Wait for LLM thread to complete (should already be done)
        try:
            await asyncio.wait_for(asyncio.shield(llm_future), timeout=5.0)
        except Exception as _llm_wait_err:
            logger.debug(f"[ORCHESTRATED] LLM future wait failed (non-critical): {_llm_wait_err}")
        
        # [SPECULATIVE] Wait for sprint thread too
        if sprint_future is not None:
            try:
                await asyncio.wait_for(asyncio.shield(sprint_future), timeout=2.0)
            except Exception:
                pass  # Sprint is non-critical
        
        context['audio_playing'] = False  # Audio stopped flowing
        
        # [ORGAN 11] Record that Alan finished speaking — for turn latency measurement
        if SIGNATURE_ENGINE_WIRED:
            sig_extractor = context.get('_signature_extractor')
            if sig_extractor:
                sig_extractor.record_alan_finished_speaking()
        
        total_time = 1000 * (time.time() - pipeline_start)
        logger.info(f"[ORCHESTRATED] Complete. {total_frames} frames, {sentence_idx} sentences in {total_time:.0f}ms")
        
        # SEND MARK (end of turn)
        mark_payload = {"event": "mark", "streamSid": stream_sid, "mark": {"name": "turn_complete"}}
        try:
            if hasattr(websocket, 'send_text'):
                await websocket.send_text(json.dumps(mark_payload))
            else:
                await websocket.send(json.dumps(mark_payload))
            logger.info("[ORCHESTRATED] Sent MARK event")
        except Exception as _mark_err:
            logger.debug(f"[ORCHESTRATED] MARK event send failed: {_mark_err}")
        
        # PERSIST AI RESPONSE
        if full_response_text:
            agent.conversation_history.add_message("Alan", full_response_text)
        
        # =====================================================================
        # [FIX R5b 2026-02-20] EMPTY RESPONSE FALLBACK — BEFORE CDC/downstream
        # If the entire orchestrated pipeline (LLM+Sprint) produced zero text,
        # the merchant is hearing dead air. This is a controllable hangup cause.
        # Synthesize and stream a fallback phrase so the merchant always hears
        # *something*, and CDC/health/evolution all see the fallback text.
        # MUST fire before return so downstream code sees non-empty response_text.
        # =====================================================================
        if not full_response_text or not full_response_text.strip():
            import random as _fb_random
            # [FIX CW-AUDIT 2025-06-24] Every fallback MUST advance the sales mission.
            # "Yeah? Go ahead." violated Rule #8. Passive phrases cause NO_PITCH failures.
            # All entries now either re-engage with pitch context or prompt the merchant
            # to share information Alan can use as a bridge into the value prop.
            # [2026-03-02 FIX] Removed "Quick question" from fallback pool — it was
            # reinforcing the repetition loop. All fallbacks are now unique phrasings.
            # [2026-03-03 FIX] Bridge-aware fallback — if a bridge phrase was sent
            # this turn, the fallback CONTINUES from it naturally.
            _bridge_was_sent = context.get('_bridge_sent', False)
            if _bridge_was_sent:
                _FALLBACK_POOL = [
                    "who handles the card processing for you guys right now?",
                    "what system are you using for payments currently?",
                    "are you set up to take cards there?",
                    "do you mind if I ask what you're paying on your processing?",
                ]
            else:
                _FALLBACK_POOL = [
                    "So what's going on with your payment setup right now?",
                    "The reason I'm reaching out is I help business owners cut their processing costs —",
                    "I work with local businesses on their payment processing — who handles yours right now?",
                    "Hey, are you guys set up to accept cards there?",
                    "Sorry, I missed that — what were you saying?",
                    "Can you hear me alright?",
                    "Hello?",
                ]
            _fallback_text = _fb_random.choice(_FALLBACK_POOL)
            logger.warning(f"[ORCHESTRATED] ⚠️ LLM produced ZERO text. Streaming fallback: '{_fallback_text}'")
            try:
                stream_sid = context.get('streamSid')
                if stream_sid and websocket:
                    await self.synthesize_and_stream_greeting(websocket, _fallback_text, stream_sid)
                    logger.info("[ORCHESTRATED] Fallback audio streamed to Twilio successfully.")
                    context['audio_playing'] = False  # Audio done
                else:
                    logger.warning("[ORCHESTRATED] No stream_sid/websocket — fallback audio could not be sent.")
            except Exception as _fb_err:
                logger.error(f"[ORCHESTRATED] Fallback TTS/stream failed: {_fb_err}")
            full_response_text = _fallback_text
            agent.conversation_history.add_message("Alan", full_response_text)
        
        # Store latency telemetry for CDC capture
        context['_turn_telemetry'] = _telemetry
        
        # [PHASE 3] Per-turn JSONL latency profiler
        try:
            turn_number = context.get('alan_turn_count', 0) + 1
            streaming_overhead = total_time - (_telemetry.get('llm_ms') or 0) - (_telemetry.get('tts_total_ms') or 0)
            latency_record = {
                'ts': datetime.now().isoformat(),
                'call_sid': context.get('callSid', 'unknown'),
                'turn': turn_number,
                'first_audio_latency_ms': round(_telemetry.get('ttfa_ms') or 0, 1),
                'full_turn_latency_ms': round(total_time, 1),
                'llm_latency_ms': round(_telemetry.get('llm_ms') or 0, 1),
                'llm_ttft_ms': round(_telemetry.get('ttft_ms') or 0, 1),
                'tts_total_ms': round(_telemetry.get('tts_total_ms') or 0, 1),
                'streaming_overhead_ms': round(max(0, streaming_overhead), 1),
                'sprint_ms': round(_telemetry.get('sprint_ms') or 0, 1),
                'sprint_text': _sprint_text if _sprint_text else None,
                'sentences': sentence_idx,
                'frames': total_frames,
                # [INSTRUMENT] Stage-level breakdown (ms from vad_end)
                'stages': {
                    'vad_end_ms': _telemetry.get('vad_end_ms'),
                    'stt_done_ms': _telemetry.get('stt_done_ms'),
                    'env_done_ms': _telemetry.get('env_done_ms'),
                    'llm_start_ms': _telemetry.get('llm_start_ms'),
                    'llm_first_token_ms': _telemetry.get('llm_first_token_ms'),
                    'llm_done_ms': _telemetry.get('llm_done_ms'),
                    'tts_start_ms': _telemetry.get('tts_start_ms'),
                    'tts_first_audio_ms': _telemetry.get('tts_first_audio_ms'),
                    'play_start_ms': _telemetry.get('play_start_ms'),
                },
            }
            import os as _os_lat
            _os_lat.makedirs('data/latency', exist_ok=True)
            with open('data/latency/turn_latency.jsonl', 'a') as _lat_f:
                _lat_f.write(json.dumps(latency_record) + '\n')
            # [INSTRUMENT] Summary log line for stage visibility
            _stg = latency_record.get('stages', {})
            logger.info(f"[STAGES] stt={_stg.get('stt_done_ms')} | env={_stg.get('env_done_ms')} | "
                        f"llm_start={_stg.get('llm_start_ms')} | llm_1st={_stg.get('llm_first_token_ms')} | "
                        f"llm_done={_stg.get('llm_done_ms')} | tts_start={_stg.get('tts_start_ms')} | "
                        f"tts_1st={_stg.get('tts_first_audio_ms')} | play={_stg.get('play_start_ms')}")
        except Exception as _lat_err:
            logger.debug(f"[LATENCY PROFILER] Write failed: {_lat_err}")
        
        return full_response_text

    async def handle_user_speech(self, data, context, websocket=None, generation=0):
        """
        Handle user speech input.
        
        HUMAN MODEL: No locks, no safety nets. Just process what was said.
        If a new generation arrives (someone spoke again), stop gracefully.
        """
        supervisor = AlanSupervisor.get_instance()
        client_id = context.get('client_id')  # [FIX] Extract client_id for Behavioral Fusion + Deep Layer lookups
        user_text = data.get('text', '').strip()

        if not user_text:
            return None

        # [PHASE 3B] Record ASR quality for telephony health monitor
        _tel_mon = context.get('_telephony_monitor')
        if _tel_mon:
            _words = user_text.split()
            _is_low_quality = (
                len(_words) <= 1  # Single word / noise
                or user_text.lower() in ('sorry', 'what', 'huh', 'hmm', 'ok', 'okay')
            )
            _tel_mon.record_asr_result(user_text, is_low_quality=_is_low_quality)

        # Update VAD Timestamp for Dynamic Breath
        # [NEG PROOF] Only update on REAL speech (2+ words), not noise/music STT artifacts
        # Bug fix V2: 1-word garbage ("hmm", "ok", music transcripts) was resetting
        # silence timer, letting dead calls run 90-150s instead of dying at 40s
        if len(user_text.split()) >= 2:
            context['last_speech_time'] = time.time()

        # During greeting, ignore input (greeting must complete first)
        current_state = context.get('conversation_state')
        if current_state == 'FIRST_GREETING_PENDING':
            logger.info(f"[FIRST TURN] Ignored user input '{user_text}' while greeting is pending.")
            return None

        # Already superseded by newer speech? Don't even start.
        if context.get('response_generation') != generation:
            logger.info(f"[SUPERSEDED] gen {generation} already replaced. Skipping.")
            return None
        
        # [ECHO PREVENTION] Clear STT buffer when starting response
        # Any audio collected between last finalize and now could be echo residue
        stream_sid_for_clear = context.get('streamSid')
        if stream_sid_for_clear:
            aqi_stt_engine.clear_buffer(stream_sid_for_clear)

        # [CONV INTEL] Pre-check: DNC, Government, Voicemail, Dead-End
        # These checks run BEFORE any LLM call. If abort → speak exit line and end.
        if CONV_INTEL_WIRED and not context.get('stream_ended'):
            _guard = context.get('_conversation_guard')
            if _guard:
                _guard.bridge.mark_turn_start()  # Start latency clock
                _ci_result = _guard.pre_check(user_text, context)
                if _ci_result and _ci_result.get('abort'):
                    _ci_system = _ci_result.get('system', 'unknown')
                    _ci_outcome = _ci_result.get('outcome', _ci_system)
                    logger.warning(f"[CONV INTEL] ABORT — system={_ci_system}, outcome={_ci_outcome}, text='{user_text[:60]}'")
                    
                    # Store outcome for evolution/CDC
                    context['_evolution_outcome'] = _ci_outcome
                    context['_guard_outcome'] = _ci_outcome
                    context['_ccnm_ignore'] = True  # Don't learn from aborted calls
                    # [PHASE 2] FSM: → ENDED (guard_abort)
                    _fsm = context.get('_call_fsm')
                    if _fsm:
                        _fsm.end_call(reason='guard_abort')
                    else:
                        context['stream_ended'] = True
                    
                    # Determine exit line
                    _exit_line = (_ci_result.get('goodbye_line')  # DNC
                                 or _ci_result.get('exit_line')   # Government / Dead-end
                                 or _ci_result.get('voicemail_message')  # Voicemail
                                 or "Thanks for your time. Have a great day!")
                    
                    # [2026-03-02 FIX] Early-turn farewell guard: if this is one of the
                    # first 3 turns and the exit line contains farewell language, replace
                    # it with a re-engagement question instead of saying goodbye.
                    # The DeadEndDetector can false-trigger from noise/echo fragments
                    # and this ensures Alan NEVER opens a call with a farewell phrase.
                    _etg_msg_count = len(context.get('messages', []))
                    _abort_blocked = False
                    # [2026-03-02 FIX v2] Broadened from dead_end-only to ALL abort
                    # systems on early turns. Voicemail/government detection can also
                    # false-trigger on noise before real speech arrives.
                    if _etg_msg_count <= 3:
                        _farewell_words = ['goodbye', 'good bye', 'have a great', 'have a good',
                                           'take care', 'thanks for your time', 'thank you for your time',
                                           "don't want to keep you", 'appreciate your time']
                        _exit_lower = _exit_line.lower()
                        if any(fw in _exit_lower for fw in _farewell_words):
                            logger.warning(f"[EXIT GUARD] Blocked dead-end farewell on msg #{_etg_msg_count}: '{_exit_line[:60]}'")
                            # Don't end the call — undo the abort
                            context.pop('_evolution_outcome', None)
                            context.pop('_guard_outcome', None)
                            context.pop('_ccnm_ignore', None)
                            context['stream_ended'] = False
                            _abort_blocked = True
                    
                    if _abort_blocked:
                        pass  # Fall through to normal LLM pipeline
                    else:
                        # Speak exit line and close
                        _stream_sid = context.get('streamSid')
                        if _stream_sid and websocket:
                            await self.synthesize_and_stream_greeting(websocket, _exit_line, _stream_sid)
                        
                        # [DNC AUTO-PERSIST] If this was a DNC request, mark the number
                        # so we NEVER call this merchant again. Legal + ethical imperative.
                        # Also set dnc_flag for Phase 5 CDC persistence
                        if _ci_outcome == 'dnc_request':
                            context['_dnc_flag'] = True
                        if DNC_WIRED and _dnc_mgr and _ci_outcome == 'dnc_request':
                            _merchant_phone = context.get('merchant_phone', '')
                            if _merchant_phone:
                                _dnc_mgr.mark_dnc(
                                    phone_number=_merchant_phone,
                                    reason='explicit_dnc_request',
                                    source_call_sid=context.get('call_sid', ''),
                                    transcript_excerpt=user_text[:200]
                                )
                                logger.warning(f"[DNC] AUTO-PERSISTED: {_merchant_phone} marked DNC — "
                                             f"merchant said: '{user_text[:60]}'")

                        # Log to CDC
                        if CALL_CAPTURE_WIRED:
                            try:
                                _cdc_turn(context.get('call_sid', ''), {
                                    'user_text': user_text,
                                    'alan_text': _exit_line,
                                    'sentiment': 'negative' if _ci_system == 'compliance' else 'neutral',
                                    'conv_intel_system': _ci_system,
                                    'conv_intel_outcome': _ci_outcome,
                                })
                            except Exception as _cdc_ci_err:
                                logger.debug(f"[CDC] Conv intel turn capture failed: {_cdc_ci_err}")
                        
                        return {
                            'type': 'conversation_reply',
                            'speech': _exit_line,
                            'end_conversation': True,
                        }

        # [PHASE 1.7] First-Turn Detection
        # The opener is over; we are now listening for the first real user input.
        if (current_state == 'dialogue' or current_state == 'LISTENING_FOR_CALLER') and not context.get('first_turn_complete'):
            # [PHASE 2] FSM: GREETING_PLAYED → DIALOGUE (first merchant speech)
            _fsm = context.get('_call_fsm')
            if _fsm:
                _fsm.handle_event(CallFlowEvent.FIRST_SPEECH)
            else:
                context['first_turn_complete'] = True
                context['conversation_state'] = 'dialogue'
            logger.info("[PHASE 1.7] First Turn Detected. Conversation Entry Locked. Disabling Opener Blocks.")

            # =================================================================
            # [TURN-01 FAST RESPONSE] Instant reply — bypass LLM entirely
            # =================================================================
            # On cold calls, Turn 01 is the most critical moment. The merchant
            # just responded to Alan's greeting. LLM pipeline takes 2.4-5.9s.
            # That dead air kills calls. Instead: pattern-match the merchant's
            # short response and serve a pre-cached TTS response in ~50ms.
            #
            # Triggers on responses ≤12 words that match known patterns.
            # Complex/long responses go to the full LLM pipeline.
            # =================================================================
            _t01_words = user_text.strip().split()
            _t01_text_lower = user_text.strip().lower().rstrip('?.!,')
            _t01_category = None

            if len(_t01_words) <= 12 and hasattr(self, '_turn01_responses'):
                # Pattern matching — most specific first
                _ACK_TRANSFER_PATTERNS = [
                    'hold on', 'one moment', 'one second', 'hang on',
                    'let me get', 'let me see', 'one sec', 'hold please',
                    'just a moment', 'just a second', 'just a sec',
                    'let me transfer', 'i\'ll get',
                ]
                _BUSY_PATTERNS = [
                    'busy', 'not available', 'not here', 'she\'s busy',
                    'he\'s busy', 'they\'re busy', 'in a meeting',
                    'with a client', 'with a customer', 'stepped out',
                    'not in', 'isn\'t here', 'isn\'t available',
                    'can\'t come to the phone', 'call back',
                    'try again later', 'leave a message',
                ]
                _IDENTITY_PATTERNS = [
                    'who is this', 'who\'s this', 'who\'s calling',
                    'who is calling', 'who am i speaking', 'may i ask who',
                    'and you are', 'who are you', 'what company',
                ]
                _PURPOSE_PATTERNS = [
                    'what\'s this about', 'whats this about', 'what is this about',
                    'what do you need', 'what are you calling about',
                    'what\'s this regarding', 'what is this regarding',
                    'how can i help', 'can i help you', 'what can i do',
                    'what\'s going on', 'what do you want',
                ]
                _ACK_OWNER_PATTERNS = [
                    'speaking', 'yeah', 'yes', 'yep', 'yup', 'uh huh',
                    'that\'s me', 'thats me', 'this is', 'you got him',
                    'you got her', 'you got me', 'go ahead', 'what\'s up',
                    'i am', 'i\'m the owner', 'i\'m him', 'i\'m her',
                ]
                _GREETING_PATTERNS = [
                    'hello', 'hi', 'hey', 'good morning', 'good afternoon',
                    'hey there', 'hi there',
                ]

                # Check each category — priority order
                for _pattern in _ACK_TRANSFER_PATTERNS:
                    if _pattern in _t01_text_lower:
                        _t01_category = 'ack_transfer'
                        break
                if not _t01_category:
                    for _pattern in _BUSY_PATTERNS:
                        if _pattern in _t01_text_lower:
                            _t01_category = 'busy'
                            break
                if not _t01_category:
                    for _pattern in _IDENTITY_PATTERNS:
                        if _pattern in _t01_text_lower:
                            _t01_category = 'identity'
                            break
                if not _t01_category:
                    for _pattern in _PURPOSE_PATTERNS:
                        if _pattern in _t01_text_lower:
                            _t01_category = 'purpose'
                            break
                if not _t01_category:
                    for _pattern in _ACK_OWNER_PATTERNS:
                        if _t01_text_lower.startswith(_pattern) or _t01_text_lower == _pattern:
                            _t01_category = 'ack_owner'
                            break
                if not _t01_category:
                    for _pattern in _GREETING_PATTERNS:
                        if _t01_text_lower == _pattern or _t01_text_lower.startswith(_pattern):
                            _t01_category = 'greeting'
                            break
                # [2026-03-02 FIX] Removed catch-all fallback that routed ALL 1-3 word
                # utterances to 'ack_owner' → "Quick question — are you currently processing
                # credit cards there?". This was too aggressive — short fragments from STT
                # noise, partial words, or ambiguous speech all got the same canned response.
                # Now, unmatched short utterances fall through to the full LLM pipeline,
                # which can produce a contextually appropriate reply.
                # if not _t01_category and len(_t01_words) <= 3:
                #     _t01_category = 'ack_owner'

            if _t01_category and hasattr(self, '_turn01_responses'):
                _t01_response_text = self._turn01_responses.get(_t01_category)
                if _t01_response_text:
                    _t01_start = time.time()
                    logger.info(f"[T01 FAST] Category='{_t01_category}' | Merchant='{user_text[:60]}' | Response='{_t01_response_text[:60]}'")

                    # Play cached audio directly
                    _stream_sid = context.get('streamSid')
                    if _stream_sid and websocket:
                        context['first_audio_produced'] = True
                        await self.synthesize_and_stream_greeting(websocket, _t01_response_text, _stream_sid)

                    _t01_ms = 1000 * (time.time() - _t01_start)
                    logger.info(f"[T01 FAST] Delivered in {_t01_ms:.0f}ms (vs ~3500ms LLM pipeline)")

                    # Record in conversation history so LLM has context for Turn 02
                    agent = context.get('agent_instance')
                    if agent:
                        agent.conversation_history.add_message("User", user_text)
                        agent.conversation_history.add_message("Alan", _t01_response_text)
                    # [2026-03-02 FIX] Use SAME message format as rest of pipeline
                    # (single dict with 'user' + 'alan' keys). Previously used two
                    # OpenAI-style dicts ({role:'user'} + {role:'assistant'}) which
                    # inflated turn_count by 1, causing MIDWEIGHT_PROMPT (turns 3-7)
                    # to be used on Turn 2 instead of FAST_PATH_PROMPT (turns 0-2).
                    # This turn_count mismatch exposed the LLM to more "quick question"
                    # examples, reinforcing the repetition loop.
                    context.setdefault('messages', []).append({
                        'timestamp': datetime.now(),
                        'user': user_text,
                        'alan': _t01_response_text,
                        'sentiment': 'neutral',
                        'interest': 0,
                    })
                    context['alan_turn_count'] = context.get('alan_turn_count', 0) + 1

                    # Record turn in CDC
                    if CALL_CAPTURE_WIRED:
                        try:
                            _cdc_turn(context.get('call_sid', ''), {
                                'user_text': user_text,
                                'alan_text': _t01_response_text,
                                'sentiment': 'neutral',
                                'interest_level': 'unknown',
                                'caller_energy': 'neutral',
                                'preprocess_ms': 0,
                                'total_turn_ms': _t01_ms,
                                'llm_ms': 0,
                                'tts_ms': 0,
                                'coaching_score': 1.0,
                                'coaching_flags': 't01_fast_response',
                            })
                        except Exception as _t01_cdc_err:
                            logger.debug(f"[T01 FAST] CDC capture failed: {_t01_cdc_err}")

                    return {'type': 'conversation_reply', 'speech': _t01_response_text}

        # [CLOSER STACK] Preference Modeling Initialization
        if 'preferences' not in context:
            context['preferences'] = MerchantPreferences().to_dict()

        # [MASTER CLOSER] State Initialization
        if 'master_closer_state' not in context:
            context['master_closer_state'] = {
                'trajectory': 'neutral',
                'merchant_type': 'unknown',
                'temperature': 50,
                'confidence_score': 50,
                'endgame_state': 'not_ready'
            }
        
        if 'call_memory' not in context:
            context['call_memory'] = CallMemory().to_dict()

        agent = context['agent_instance']
        
        # [ORGAN 4] Energy Mirroring — detect caller energy and inject into context
        caller_energy = detect_caller_energy(user_text)
        prev_energy = context.get('caller_energy', 'neutral')
        # Smooth energy transitions: stressed overrides all, otherwise only change on strong signal
        if caller_energy == 'stressed' or prev_energy == 'neutral':
            context['caller_energy'] = caller_energy
        elif caller_energy != 'neutral':
            context['caller_energy'] = caller_energy
        # else: keep previous non-neutral energy (humans don't flip-flop)
        if context['caller_energy'] != 'neutral':
            logger.info(f"[ENERGY MIRROR] Caller energy: {context['caller_energy']}")

        # [ORGAN 6] Live Objection Detection — classify and inject for rebuttal reference
        live_objection = detect_live_objection(user_text)

        # Pre-fetch IQ budget organ for Organ 31/30 (defined here so it's in scope before line 7930)
        _iq_organ = context.get('_iq_budget_organ')

        if live_objection:
            context['live_objection_type'] = live_objection
            logger.info(f"[OBJECTION DETECTED] Type: {live_objection} — rebuttal reference will be injected into LLM context")
        else:
            # Clear previous objection — each turn is fresh
            context.pop('live_objection_type', None)

        # [ORGAN 31] Objection Learning — capture + learn from objections
        if OBJECTION_LEARNING_WIRED and _objection_learning_organ:
            try:
                _t_obj31 = time.time()
                _call_id = context.get('call_sid', context.get('stream_sid', 'unknown'))
                if live_objection:
                    # Known objection — record event with metadata
                    _obj_family_info = _OBJECTION_FAMILIES.get(live_objection, {
                        'family': 'general_hesitation', 'rebuttal': '—', 'closing': '—', 'tone': '—'
                    })
                    _obj_event = {
                        'text': user_text[:200],
                        'type': live_objection,
                        'family': _obj_family_info['family'],
                        'rebuttal_ref': _obj_family_info['rebuttal'],
                        'closing_style': _obj_family_info['closing'],
                        'emotion': context.get('_prosody_emotion', 'neutral'),
                        'confidence': 1.0,
                        'turn': context.get('turn_count', 0),
                        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                    }
                    context.setdefault('_objection_events', []).append(_obj_event)
                    context['_objection_turns'] = context.get('_objection_turns', 0) + 1
                    logger.info(f"[ORGAN 31] Objection captured: {live_objection} → family={_obj_family_info['family']}")
                    # [ORGAN 32] Feed objection event to summarization organ
                    if SUMMARIZATION_WIRED and context.get('_summarization_organ') and context.get('_summary_state') == 'collecting':
                        try:
                            context['_summarization_organ'].add_objection_event(live_objection)
                        except Exception as _sum_obj_err:
                            logger.debug(f"[ORGAN 32] Objection feed failed (non-fatal): {_sum_obj_err}")
                else:
                    # Org 6 didn't recognize it — check if it sounds like a hesitation
                    # Feed to Organ 31 for learning (observe_uncaptured)
                    _text_lower = user_text.lower()
                    _hesitation_signals = ['i don\'t know', 'not really', 'we\'ll see',
                                           'maybe later', 'let me think', 'i\'m not sure',
                                           'probably not', 'i don\'t think so', 'we had bad',
                                           'that\'s a lot', 'too much', 'happy with what',
                                           'don\'t need', 'we tried that', 'burned before']
                    if any(h in _text_lower for h in _hesitation_signals):
                        _objection_learning_organ.observe_uncaptured(
                            phrase=user_text.strip(),
                            call_id=_call_id
                        )
                        # Record as general hesitation event
                        _obj_event = {
                            'text': user_text[:200],
                            'type': 'uncaptured',
                            'family': 'general_hesitation',
                            'rebuttal_ref': '—',
                            'closing_style': '—',
                            'emotion': context.get('_prosody_emotion', 'neutral'),
                            'confidence': 0.4,
                            'turn': context.get('turn_count', 0),
                            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                        }
                        context.setdefault('_objection_events', []).append(_obj_event)
                        logger.info(f"[ORGAN 31] Uncaptured hesitation observed for learning: {user_text[:80]}")
                _obj31_ms = 1000 * (time.time() - _t_obj31)
                context.setdefault('_component_times_early', {})['objection_learning_ms'] = round(_obj31_ms, 1)
                # [ORGAN 35] Record objection learning spend
                if IQ_BUDGET_WIRED and _iq_organ:
                    try:
                        _iq_organ.record_spend('organ_31_objection_observe', ORGAN_COST_MAP.get('organ_31_objection_observe', 1))
                    except Exception:
                        pass
            except Exception as _obj31_err:
                logger.warning(f"[ORGAN 31] Objection capture failed (non-fatal): {_obj31_err}")

        # [ORGAN 30] Prosody Analysis — detect merchant emotional state from text
        _pa = context.get('_prosody_analysis')
        if _pa:
            try:
                _t_prosody = time.time()
                _sentiment_for_pa = analysis.get('sentiment', 'neutral') if 'analysis' in dir() else 'neutral'
                _pa_frame = _text_to_prosody_frame(user_text, sentiment=_sentiment_for_pa)
                _pa_result = _pa.analyze_frame(_pa_frame)
                _pa_emotion = _pa_result.get('emotion', 'neutral')
                _pa_confidence = _pa_result.get('emotion_confidence', 0.0)
                _pa_strategy = _pa_result.get('strategy', {})
                context['_prosody_emotion'] = _pa_emotion
                context['_prosody_confidence'] = _pa_confidence
                # [ORGAN 35] Record prosody spend
                if IQ_BUDGET_WIRED and _iq_organ:
                    try:
                        _iq_organ.record_spend('organ_30_prosody', ORGAN_COST_MAP.get('organ_30_prosody', 1))
                    except Exception:
                        pass
                context['_prosody_strategy'] = _pa_strategy
                # [ORGAN 32] Feed tone event to summarization organ
                if SUMMARIZATION_WIRED and context.get('_summarization_organ') and context.get('_summary_state') == 'collecting':
                    try:
                        context['_summarization_organ'].add_tone_event({
                            'emotion': _pa_emotion,
                            'confidence': _pa_confidence,
                            'strategy': _pa_strategy.get('priority', 'continue') if _pa_strategy else 'continue',
                        })
                    except Exception as _sum_tone_err:
                        logger.debug(f"[ORGAN 32] Tone feed failed (non-fatal): {_sum_tone_err}")
                # Enrich caller_energy with Organ 30 emotion → prosody mode mapping
                _prosody_override = _EMOTION_TO_PROSODY_MODE.get(_pa_emotion)
                if _prosody_override and _pa_confidence >= 0.5:
                    context['_prosody_mode_override'] = _prosody_override
                else:
                    context.pop('_prosody_mode_override', None)
                _component_times = context.get('_component_times_early', {})
                _prosody_ms = 1000 * (time.time() - _t_prosody)
                if _pa_emotion != 'neutral':
                    logger.info(f"[ORGAN 30] Tone: {_pa_emotion} ({_pa_confidence:.2f}) — "
                               f"strategy: {_pa_strategy.get('priority', 'continue')} — "
                               f"{_prosody_ms:.1f}ms")
                    if _prosody_override:
                        logger.info(f"[ORGAN 30] Prosody mode override: {_prosody_override} (§2.19)")
            except Exception as _pa_err:
                logger.warning(f"[ORGAN 30] Analysis failed (non-fatal): {_pa_err}")
                context.pop('_prosody_mode_override', None)
        
        # [ORGAN 11] Feed caller turn to signature extractor
        sig_extractor = context.get('_signature_extractor')
        if sig_extractor:
            try:
                caller_sentiment = (context.get('master_closer_state', {}) or {}).get('trajectory', 'neutral')
                sig_extractor.process_caller_turn(user_text, sentiment=caller_sentiment)
                
                # Re-compute effective signature with updated caller data (every 3+ turns)
                if sig_extractor._total_caller_words >= 20 and _sig_learner:
                    partial_sample = sig_extractor.finalize()  # Non-destructive peek
                    sig_extractor._call_start = context.get('start_time', datetime.now()).timestamp() if hasattr(context.get('start_time', 0), 'timestamp') else sig_extractor._call_start
                    global_sig = _sig_learner.get_global_signature()
                    eff_sig = compute_effective_signature(global_sig, partial_sample)
                    context['_effective_signature'] = eff_sig
                    logger.debug(f"[ORGAN 11] Signature updated — speed_bias={eff_sig.speed_bias:.3f}, "
                                f"silence_bias={eff_sig.silence_bias_frames}, "
                                f"breath_bias={eff_sig.breath_prob_bias:.3f}, "
                                f"caller_influence={eff_sig.caller_influence_pct:.0%}")
            except Exception as e:
                logger.debug(f"[ORGAN 11] Extraction step failed (non-fatal): {e}")
        
        # [ORGAN] Hook 4 — Merchant Speech (fire-and-forget, zero latency)
        if CALL_MONITOR_WIRED:
            monitor_merchant_speech(context.get('call_sid', ''), user_text)
        
        # [LIVE MONITOR] Record merchant speech for live state tracking
        if LIVE_MONITOR_WIRED and _live_monitor:
            _live_monitor.record_merchant_speech(context.get('call_sid', ''), user_text)
        
        # [PIPELINE TIMING] Track total processing time
        pipeline_t0 = time.time()
        _component_times = {}  # Track each pre-processing component

        # [ORGAN 35] Start turn — budget accounting for this conversational turn
        _iq_organ = context.get('_iq_budget_organ')
        if IQ_BUDGET_WIRED and _iq_organ:
            try:
                _iq_turn_info = _iq_organ.start_turn()
                context['_iq_state'] = _iq_turn_info.get('burn_state', 'normal')
                context['_iq_disabled_organs'] = _iq_turn_info.get('disabled_organs', [])
                context['_iq_fallback_active'] = _iq_turn_info.get('fallback_active', False)
                context['_iq_turn_spend'] = 0
            except Exception as _iq_start_err:
                logger.debug(f"[ORGAN 35] start_turn failed (non-fatal): {_iq_start_err}")

        # [PHASE 1.7] Dead-State Prevention (Timeout Wrapper)
        try:
            # 1. Analyze
            _t_analyze = time.time()
            analysis = agent.analyze_business_response(user_text)
            _component_times['analyze_ms'] = 1000 * (time.time() - _t_analyze)
            
            # [CONV INTEL] Store analysis for dead-end detector access
            context['_last_analysis'] = analysis

            # [CLOSER STACK] Update Preferences
            current_prefs = MerchantPreferences()
            # De-serialize from context
            for k, v in context['preferences'].items():
                setattr(current_prefs, k, v)
            
            updated_prefs = update_preferences(current_prefs, user_text, analysis, len(context['messages']))
            context['preferences'] = updated_prefs.to_dict()
            
            # [MASTER CLOSER] Orchestration Turn
            mc_state = context['master_closer_state']
            
            # 1. Update Merchant Type
            mc_state['merchant_type'] = self.master_closer.classify_merchant(user_text, mc_state['merchant_type'])
            
            # 2. Update Trajectory
            # [VERSION R] TRAJECTORY LOCK — Humans don't flip between warming/cooling
            # every turn. Once a trajectory is established (after 2 turns of data), lock it
            # in and only allow a change if 3+ consecutive turns show contradictory signal.
            old_trajectory = mc_state.get('trajectory', 'neutral')
            proposed_trajectory = self.master_closer.update_trajectory(mc_state['trajectory'], analysis.get('signals', []))
            
            if proposed_trajectory != old_trajectory:
                # Count consecutive contradictory turns before allowing a switch
                mc_state['contradictory_turns'] = mc_state.get('contradictory_turns', 0) + 1
                if mc_state['contradictory_turns'] >= 3 or old_trajectory == 'neutral':
                    # Genuine shift or first read — allow it
                    mc_state['trajectory'] = proposed_trajectory
                    mc_state['switches'] = mc_state.get('switches', 0) + 1
                    mc_state['contradictory_turns'] = 0
                    logger.info(f"[TRAJECTORY] Locked new trajectory: {old_trajectory} -> {proposed_trajectory} (after {mc_state['switches']} switches)")
                else:
                    logger.info(f"[TRAJECTORY] Holding {old_trajectory} (contradictory signal {mc_state['contradictory_turns']}/3, proposed: {proposed_trajectory})")
            else:
                # Consistent signal — reset contradictory counter
                mc_state['contradictory_turns'] = 0
            
            # 3. Update Call Memory (Intra-call)
            cm = CallMemory.from_dict(context['call_memory'])
            # Simple heuristic for key points
            if "rate" in user_text.lower() or "fee" in user_text.lower():
                cm.key_points.append("Concerned about rates/fees")
            if analysis.get('objections'):
                for obj in analysis['objections']:
                    # Weighted objection
                    weight = self.master_closer.calculate_objection_weight(
                        obj, mc_state['trajectory'], analysis.get('micro_patterns', [])
                    )
                    cm.objections.append({"type": obj, "strength": weight})
            
            if analysis.get('sentiment') == 'positive' and len(user_text) > 20:
                cm.agreements.append(f"Positive engagement: '{user_text[:20]}...'")
            
            context['call_memory'] = cm.to_dict()
            
            # 4. Update Scores
            self.master_closer.update_scores(mc_state, analysis.get('signals', []), analysis.get('sentiment', 'neutral'))
            
            # 5. Check Endgame
            mc_state['endgame_state'] = self.master_closer.get_endgame_state(mc_state['temperature'], mc_state['confidence_score'])
            
            # [BAL] Locked to consistent consultative profile
            # Previously: per-turn archetype classification caused tone whiplash
            # (strong → gentle → consultative → gentle every other turn)
            # Alan should sound like the SAME person throughout the entire call.
            context['behavior_profile'] = {
                "tone": "consultative",
                "pacing": "normal",
                "formality": "neutral",
                "assertiveness": "medium",
                "rapport_level": "medium",
                "pivot_style": "soft",
                "closing_bias": "consultative",
                "compression_mode": False,
                "expansion_mode": False
            }
            
            # [CRG] Cognitive Reasoning Governor Turn
            crg_signals = {
                "archetype": mc_state['merchant_type'],
                "temperature": mc_state['temperature'],
                "confidence": mc_state['confidence_score']
            }
            reasoning_block = self.crg.build_reasoning_block(crg_signals)
            context['reasoning_block'] = reasoning_block

            logger.info(f"[MASTER CLOSER] Trajectory: {mc_state['trajectory']}, Temp: {mc_state['temperature']}, Conf: {mc_state['confidence_score']}, Endgame: {mc_state['endgame_state']}")
            logger.info(f"[BAL] Locked Profile: consultative/normal/medium (stable)")
            logger.info(f"[CRG] Reasoning Budget Applied.")

            # [ORGAN 25] Warm Handoff — escalation trigger evaluation
            _ho = context.get('_handoff_organ')
            if _ho and WARM_HANDOFF_WIRED and context.get('_handoff_state') == 'inactive':
                try:
                    _t_handoff = time.time()
                    _escalation_reason = None
                    _text_lower_ho = user_text.lower()

                    # Trigger 1: Merchant explicitly requests human
                    if any(p in _text_lower_ho for p in _MERCHANT_ESCALATION_PATTERNS):
                        _escalation_reason = 'merchant_request'
                        logger.info(f"[ORGAN 25] Merchant requested human escalation")

                    # Trigger 2: Deal readiness — endgame ready + high temperature
                    elif mc_state.get('endgame_state') == 'ready' and mc_state.get('temperature', 0) >= 75:
                        _deal_check = _ho.check_deal_readiness_escalation(mc_state.get('temperature', 0))
                        if _deal_check.get('should_escalate'):
                            _escalation_reason = 'deal_ready'
                            logger.info(f"[ORGAN 25] Deal readiness threshold met (temp={mc_state.get('temperature')})")

                    # Trigger 3: Duration exceeded
                    else:
                        _dur_check = _ho.check_duration_escalation()
                        if _dur_check.get('should_escalate'):
                            _escalation_reason = 'duration_exceeded'
                            logger.info(f"[ORGAN 25] Call duration exceeded ({_dur_check.get('duration_seconds', 0):.0f}s)")

                    if _escalation_reason:
                        context['_handoff_state'] = 'pending_consent'
                        context['_handoff_reason'] = _escalation_reason
                        # For merchant_request, auto-record consent (they asked for it)
                        if _escalation_reason == 'merchant_request':
                            _ho.record_consent(True)
                        logger.info(f"[ORGAN 25] Escalation triggered: {_escalation_reason} — awaiting consent")

                    _handoff_ms = 1000 * (time.time() - _t_handoff)
                    context.setdefault('_component_times', {})['handoff_ms'] = round(_handoff_ms, 1)
                except Exception as _ho_err:
                    logger.warning(f"[ORGAN 25] Escalation check failed (non-fatal): {_ho_err}")

            # [ORGAN 25] Consent detection — when pending, check if merchant confirms
            elif _ho and WARM_HANDOFF_WIRED and context.get('_handoff_state') == 'pending_consent':
                try:
                    _text_lower_ho = user_text.lower()
                    _consent_given = any(p in _text_lower_ho for p in _HANDOFF_CONSENT_PATTERNS)
                    _decline_given = any(w in _text_lower_ho for w in ['no', 'nah', 'not right now', 'no thanks', 'don\'t transfer'])

                    if _consent_given:
                        _ho.record_consent(True)
                        # Build context for the closer
                        _merchant_name = context.get('prospect_info', {}).get('contact_name')
                        _business_name = context.get('prospect_info', {}).get('company')
                        _merchant_phone = context.get('prospect_info', {}).get('phone')
                        _emotion = context.get('_prosody_emotion', 'neutral')

                        _handoff_result = _ho.initiate_handoff(
                            reason=context.get('_handoff_reason', 'deal_ready'),
                            mode='warm',
                            merchant_name=_merchant_name,
                            business_name=_business_name,
                            merchant_phone=_merchant_phone,
                            deal_readiness_score=mc_state.get('temperature', 0),
                            context_notes=(
                                f"Emotion: {_emotion} | "
                                f"Trajectory: {mc_state.get('trajectory', 'neutral')} | "
                                f"Objections: {len(context.get('_objection_events', []))} | "
                                f"Competitor: {context.get('_detected_competitor', 'none')}"
                            ),
                        )
                        context['_handoff_state'] = _handoff_result.get('status', 'initiated')
                        context['_handoff_result'] = _handoff_result
                        logger.info(f"[ORGAN 25] Handoff {_handoff_result['status']}: "
                                   f"{_handoff_result.get('mode', 'warm')} to {_handoff_result.get('closer', 'N/A')} "
                                   f"— reason: {context.get('_handoff_reason')}")
                    elif _decline_given:
                        context['_handoff_state'] = 'inactive'
                        context['_handoff_reason'] = None
                        _ho.record_consent(False)
                        logger.info("[ORGAN 25] Merchant declined transfer — returning to normal flow")
                except Exception as _ho_consent_err:
                    logger.warning(f"[ORGAN 25] Consent detection failed (non-fatal): {_ho_consent_err}")

            # [ORGAN 26] Outbound Comms — mid-call send request detection
            _oc = context.get('_outbound_comms')
            if _oc and OUTBOUND_COMMS_WIRED:
                try:
                    _t_oc = time.time()
                    _text_lower_oc = user_text.lower()
                    _oc_channel = None
                    _oc_template = None

                    # Detect SMS request
                    if any(p in _text_lower_oc for p in _OUTBOUND_SMS_REQUEST_PATTERNS):
                        _oc_channel = 'sms'
                        _oc_template = 'follow_up_pricing'
                        logger.info("[ORGAN 26] Merchant requested SMS follow-up")

                    # Detect email request
                    elif any(p in _text_lower_oc for p in _OUTBOUND_EMAIL_REQUEST_PATTERNS):
                        _oc_channel = 'email'
                        _oc_template = 'follow_up_email_pricing'
                        logger.info("[ORGAN 26] Merchant requested email follow-up")

                    if _oc_channel:
                        _merchant_phone_oc = context.get('prospect_info', {}).get('phone')
                        _merchant_email_oc = context.get('prospect_info', {}).get('email')
                        _merchant_name_oc = context.get('prospect_info', {}).get('contact_name')
                        _business_name_oc = context.get('prospect_info', {}).get('company')

                        # Check if we have contact info for the requested channel
                        _has_contact = (_oc_channel == 'sms' and _merchant_phone_oc) or \
                                       (_oc_channel == 'email' and _merchant_email_oc)

                        if _has_contact:
                            _send_result = _oc.send_message(
                                template_name=_oc_template,
                                merchant_phone=_merchant_phone_oc,
                                merchant_email=_merchant_email_oc,
                                merchant_name=_merchant_name_oc,
                                business_name=_business_name_oc,
                                channel_override=_oc_channel,
                                variables={'link': 'https://edge.aqi.com/info', 'details': 'Edge payment processing program details'},
                            )
                            context.setdefault('_outbound_sends', []).append(_send_result)
                            logger.info(f"[ORGAN 26] Send result: {_send_result['status']} via {_send_result.get('channel', _oc_channel)}")
                        else:
                            # Missing contact info — set pending so LLM asks for it
                            context['_outbound_pending'] = {
                                'channel': _oc_channel,
                                'template': _oc_template,
                                'requested_at': time.time(),
                            }
                            logger.info(f"[ORGAN 26] Contact info missing for {_oc_channel} — prompting merchant")

                    _oc_ms = 1000 * (time.time() - _t_oc)
                    context.setdefault('_component_times', {})['outbound_comms_ms'] = round(_oc_ms, 1)
                except Exception as _oc_err:
                    logger.warning(f"[ORGAN 26] Outbound detection failed (non-fatal): {_oc_err}")

            # [ORGAN 27] Language Switch — detection + switch request + confirmation
            _ls = context.get('_language_organ')
            if _ls and LANGUAGE_SWITCH_WIRED:
                try:
                    _t_ls = time.time()
                    _ls_switch_state = context.get('_language_switch_state', 'inactive')
                    _text_lower_ls = user_text.lower()

                    if _ls_switch_state == 'inactive':
                        # Check 1: Explicit merchant request to switch language
                        _explicit_lang = None
                        for _lang_code, _patterns in _LANGUAGE_SWITCH_PATTERNS.items():
                            if any(p in _text_lower_ls for p in _patterns):
                                _explicit_lang = _lang_code
                                break

                        if _explicit_lang:
                            # Merchant explicitly asked — switch immediately (consent implicit)
                            _switch_result = _ls.switch_language(_explicit_lang, reason='merchant_request')
                            if _switch_result.get('status') == 'switched':
                                context['_language_state'] = _explicit_lang
                                context['_language_switch_state'] = 'switched'
                                context['_language_detected'] = _explicit_lang
                                context['_language_confidence'] = 1.0
                                logger.info(f"[ORGAN 27] Merchant requested {_switch_result['language_name']} — switched")
                            else:
                                logger.info(f"[ORGAN 27] Language '{_explicit_lang}' unsupported — continuing in English")
                        else:
                            # Check 2: Auto-detect from speech markers
                            _detect_result = _ls.analyze_speech(user_text)
                            if _detect_result.get('status') == 'detected' and _detect_result.get('meets_threshold'):
                                _det_lang = _detect_result['detected_language']
                                _det_conf = _detect_result['confidence']
                                context['_language_detected'] = _det_lang
                                context['_language_confidence'] = _det_conf
                                context['_language_switch_state'] = 'pending_confirm'
                                logger.info(f"[ORGAN 27] Detected {_detect_result['language_name']} "
                                           f"(conf={_det_conf:.2f}) — awaiting confirmation")

                    elif _ls_switch_state == 'pending_confirm':
                        # Merchant responds to confirmation prompt
                        _confirmed = any(p in _text_lower_ls for p in _LANGUAGE_CONFIRM_PATTERNS)
                        _declined = any(p in _text_lower_ls for p in _LANGUAGE_DECLINE_PATTERNS)

                        if _confirmed:
                            _target_lang = context.get('_language_detected', 'es')
                            _switch_result = _ls.switch_language(_target_lang, reason='merchant_confirmed')
                            if _switch_result.get('status') == 'switched':
                                context['_language_state'] = _target_lang
                                context['_language_switch_state'] = 'switched'
                                logger.info(f"[ORGAN 27] Merchant confirmed — switched to {_switch_result['language_name']}")
                        elif _declined:
                            context['_language_switch_state'] = 'declined'
                            logger.info("[ORGAN 27] Merchant declined language switch — locked to English")

                    _ls_ms = 1000 * (time.time() - _t_ls)
                    context.setdefault('_component_times', {})['language_switch_ms'] = round(_ls_ms, 1)
                except Exception as _ls_err:
                    logger.warning(f"[ORGAN 27] Language detection failed (non-fatal): {_ls_err}")

            # [ORGAN 28] Calendar Engine — scheduling request detection + confirmation
            _cal = context.get('_calendar_organ')
            if _cal and CALENDAR_ENGINE_WIRED:
                try:
                    _t_cal = time.time()
                    _cal_state = context.get('_calendar_state', 'inactive')
                    _text_lower_cal = user_text.lower()

                    if _cal_state == 'inactive':
                        # Check if merchant requests scheduling
                        _wants_schedule = any(p in _text_lower_cal for p in _CALENDAR_REQUEST_PATTERNS)

                        # Also trigger on closing success (deal ready + callback agreement)
                        _deal_trigger = (mc_state.get('endgame_state') == 'ready' and
                                        mc_state.get('temperature', 0) >= 70 and
                                        any(w in _text_lower_cal for w in ['call back', 'callback', 'follow up', 'next step']))

                        if _wants_schedule or _deal_trigger:
                            _avail = _cal.check_availability()
                            if _avail.get('status') == 'ok' and _avail.get('available_slots'):
                                _slots = _avail['available_slots']
                                # Propose first available slot
                                _merchant_name_cal = context.get('prospect_info', {}).get('contact_name')
                                _merchant_email_cal = context.get('prospect_info', {}).get('email')
                                _merchant_phone_cal = context.get('prospect_info', {}).get('phone')
                                _business_name_cal = context.get('prospect_info', {}).get('company')

                                _propose_result = _cal.propose_booking(
                                    slot_start=_slots[0]['start'],
                                    merchant_name=_merchant_name_cal,
                                    merchant_email=_merchant_email_cal,
                                    merchant_phone=_merchant_phone_cal,
                                    business_name=_business_name_cal,
                                    notes=f"Trigger: {'merchant_request' if _wants_schedule else 'deal_ready'}",
                                )
                                if _propose_result.get('status') == 'proposed':
                                    context['_calendar_state'] = 'proposed'
                                    context['_calendar_proposed'] = {
                                        'result': _propose_result,
                                        'all_slots': _slots,
                                    }
                                    logger.info(f"[ORGAN 28] Slot proposed: {_propose_result.get('start')}")
                            else:
                                logger.info("[ORGAN 28] No available slots found")

                    elif _cal_state == 'proposed':
                        # Check for confirmation or decline
                        _confirmed = any(p in _text_lower_cal for p in _CALENDAR_CONFIRM_PATTERNS)
                        _declined = any(p in _text_lower_cal for p in _CALENDAR_DECLINE_PATTERNS)

                        if _confirmed:
                            _confirm_result = _cal.confirm_booking()
                            if _confirm_result.get('status') == 'confirmed':
                                context['_calendar_state'] = 'confirmed'
                                context['_calendar_booking'] = _confirm_result
                                logger.info(f"[ORGAN 28] Booking confirmed: {_confirm_result.get('booking_id')}")
                        elif _declined:
                            # Offer alternative slots
                            _proposed_data = context.get('_calendar_proposed', {})
                            _all_slots = _proposed_data.get('all_slots', [])
                            if len(_all_slots) > 1:
                                # Propose next slot
                                _next_slot = _all_slots[1]
                                _propose_result = _cal.propose_booking(
                                    slot_start=_next_slot['start'],
                                    merchant_name=context.get('prospect_info', {}).get('contact_name'),
                                    merchant_email=context.get('prospect_info', {}).get('email'),
                                    merchant_phone=context.get('prospect_info', {}).get('phone'),
                                    business_name=context.get('prospect_info', {}).get('company'),
                                )
                                if _propose_result.get('status') == 'proposed':
                                    context['_calendar_proposed'] = {
                                        'result': _propose_result,
                                        'all_slots': _all_slots[1:],
                                    }
                                    logger.info(f"[ORGAN 28] Alternative slot proposed: {_propose_result.get('start')}")
                            else:
                                context['_calendar_state'] = 'declined'
                                logger.info("[ORGAN 28] Merchant declined all available slots")

                    _cal_ms = 1000 * (time.time() - _t_cal)
                    context.setdefault('_component_times', {})['calendar_ms'] = round(_cal_ms, 1)
                except Exception as _cal_err:
                    logger.warning(f"[ORGAN 28] Calendar detection failed (non-fatal): {_cal_err}")

            # [DEEP LAYER] QPC + Fluidic + Continuum per-turn step
            deep_layer = context.get('deep_layer')
            if deep_layer:
                try:
                    _t_dl = time.time()
                    deep_state = deep_layer.step(user_text, analysis, context)
                    _component_times['deep_layer_ms'] = 1000 * (time.time() - _t_dl)
                    # Override the hardcoded behavior profile with fluidic mode guidance
                    mode_obj_name = deep_state.get('mode', 'OPENING')
                    context['behavior_profile']['deep_layer_mode'] = mode_obj_name
                    context['behavior_profile']['deep_layer_strategy'] = deep_state.get('strategy', 'natural')
                    logger.info(f"[DEEP LAYER] Mode={mode_obj_name}, Strategy={deep_state.get('strategy')}, "
                               f"Blend={deep_state.get('mode_blend')}")
                    
                    # [BEHAVIORAL FUSION UPDATE]
                    if BEHAVIORAL_FUSION_WIRED and client_id in _behavioral_stats:
                        try:
                            # 1. Update Fluidic State
                            _b_stats = _behavioral_stats[client_id]
                            _b_stats['fluidic_state'] = mode_obj_name
                            
                            # 2. Extract Continuum metrics (if available) - default to stable if not
                            # Assuming deep_state might have continuum details, otherwise use defaults
                            continuum = deep_state.get('continuum', {})
                            # If continuum is a dict, use it. If it's just state string, use defaults.
                            if isinstance(continuum, dict):
                                _b_stats['trajectory_velocity'] = continuum.get('velocity', 0.0)
                                _b_stats['trajectory_drift'] = continuum.get('drift', 0.0)
                                _b_stats['emotional_viscosity'] = continuum.get('viscosity', 1.0)
                            
                            # 3. Update Objection Count (from analysis)
                            current_objections = analysis.get('objections', [])
                            if current_objections:
                                _b_stats['objection_count'] += len(current_objections)
                            
                            # 4. Turn Count
                            _b_stats['turn_count'] += 1
                            
                            logger.debug(f"[BEHAVIORAL FUSION] Updated stats: Mode={_b_stats['fluidic_state']}, "
                                        f"Obj={_b_stats['objection_count']}, Turns={_b_stats['turn_count']}")
                        except Exception as bf_e:
                            logger.warning(f"[BEHAVIORAL FUSION] Update failed (non-fatal): {bf_e}")

                except Exception as e:
                    logger.warning(f"[DEEP LAYER] Step failed (non-fatal): {e}")
            
            # [PIPELINE TIMING] Log pre-processing overhead with component breakdown
            preprocess_ms = 1000 * (time.time() - pipeline_t0)
            _comp_str = ' | '.join(f"{k}={v:.0f}" for k, v in _component_times.items())
            logger.info(f"[PIPELINE TIMING] Pre-processing complete in {preprocess_ms:.0f}ms [{_comp_str}]")

            # [CLOSER STACK] Predictive Intent Modeling
            _t_predict = time.time()
            prediction = self.predictive_engine.predict(user_text, analysis.get('sentiment', 'neutral'))
            _component_times['predict_ms'] = 1000 * (time.time() - _t_predict)
            
            predict_prefix = ""
            if prediction:
                context['last_predicted_intent'] = prediction.intent_name
                context['last_predicted_objection_type'] = prediction.objection_type
                
                high_conf = self.predictive_engine.config.get("thresholds", {}).get("high_confidence", 0.8)
                if prediction.confidence >= high_conf:
                    predict_prefix = self.predictive_engine.build_anticipatory_prefix(prediction) + " "
                    logger.info(f"[PREDICTIVE] High confidence intent: {prediction.intent_name}. Applied prefix.")
            
            # [LATENCY MASK] Pass current pipeline start time to context
            # so Agent X can estimate if THIS turn is running slow
            context['_pipeline_start_time'] = pipeline_t0

            # [AGENT X SUPPORT] Off-Topic Intelligence Processing
            # Agent X handles off-topic detection, turn tracking, and builds
            # conversation guidance that gets injected into Alan's LLM prompt.
            if self.agent_x_support:
                analysis = self.agent_x_support.process_turn(user_text, analysis, context)
                if analysis.get('is_off_topic'):
                    logger.info(f"[AGENT X SUPPORT] Off-topic: cat={analysis.get('off_topic_category')}, "
                               f"mode={analysis.get('off_topic_mode')}, "
                               f"turn={context.get('off_topic_turn_count', 0)}")
            elif analysis.get('is_off_topic'):
                # Fallback: basic rapport handling if Agent X support not loaded
                sentiment = analysis.get('sentiment', 'neutral')
                resilience = self.rapport_layer.get('off_topic_resilience', {})
                micro_acks = self.rapport_layer.get('micro_acknowledgments', {})
                acks = micro_acks.get(sentiment, micro_acks.get('neutral', ["I hear you."]))
                ack = random.choice(acks)
                pivots = resilience.get('mission_pivots', ["Anyway, back to why I called."])
                pivot = random.choice(pivots)
                logger.info(f"[RAPPORT] Off-topic fallback: {ack} {pivot}")

            if analysis.get('sentiment') == 'negative' and not analysis.get('is_off_topic'):
                # [PERSONALITY FLARE] Handle difficult users with high-status professionalism
                resilience = self.rapport_layer.get('off_topic_resilience', {})
                prefices = resilience.get('professional_prefices', ["I understand your perspective. To be direct:"])
                rapport_prefix = random.choice(prefices) + " "
                logger.info(f"[PERSONALITY FLARE] Negative sentiment detected. Applied professional prefix.")

            # [PHASE 1.7] Conversational Entry Lock (Suppression of Pitch if locked)
            if context.get('conversation_state') == 'dialogue' and analysis.get('pitch_intent'):
                if time.time() < context.get('fallback_suppressed_until', 0):
                    logger.info("[PHASE 1.7] Suppressing Premature Pitch. Forcing Dialogue.")
                    analysis['pitch_intent'] = None # Clear pitch intent

            # ================================================================
            # [REPETITION ESCALATION] Third-ask detection and strategy shift
            # ================================================================
            # Problem: When merchants repeat the same question 2-3 times, Alan
            # repeats the same answer. A human salesperson would escalate:
            #   Ask 1: Normal answer
            #   Ask 2: Reframe / add detail
            #   Ask 3: Spell it out / anchor with specifics / offer proof
            # [FIX] Lowered threshold from 0.65→0.45 because STT transcription
            # varies slightly each time (e.g., "What company?" vs "What company did you say?")
            # Also normalize by stripping filler/stopwords for better matching.
            # ================================================================
            _rep_history = context.get('_repetition_history', [])
            _rep_threshold = 0.45  # Lowered — STT makes identical phrases look different
            _user_lower = user_text.lower().strip()
            # Normalize: strip common filler for better matching
            import re as _rep_re
            _user_norm = _rep_re.sub(r'\b(did you say|you said|again|please|uh|um)\b', '', _user_lower).strip()
            _rep_count = 0
            for _prev_q in _rep_history:
                from difflib import SequenceMatcher
                _prev_norm = _rep_re.sub(r'\b(did you say|you said|again|please|uh|um)\b', '', _prev_q.lower()).strip()
                _sim = SequenceMatcher(None, _user_norm, _prev_norm).ratio()
                # Also check keyword overlap for short questions
                _words_a = set(_user_norm.split())
                _words_b = set(_prev_norm.split())
                _word_overlap = len(_words_a & _words_b) / max(len(_words_a | _words_b), 1) if _words_a and _words_b else 0
                if _sim > _rep_threshold or _word_overlap > 0.6:
                    _rep_count += 1
            _rep_history.append(user_text)
            if len(_rep_history) > 8:
                _rep_history = _rep_history[-8:]
            context['_repetition_history'] = _rep_history
            
            if _rep_count >= 2:
                # Third ask — inject escalation instruction into analysis
                context['_repetition_escalation'] = 'anchor'
                analysis['_escalation_directive'] = (
                    "[ESCALATION] The merchant has asked this same question 3+ times. "
                    "DO NOT repeat your previous answer. Instead: "
                    "1) Acknowledge you may not have been clear enough: 'Sorry, let me be more clear.' "
                    "2) Reframe with a concrete, specific example. "
                    "3) Spell out the key detail (name, number, or fact) slowly and clearly. "
                    "4) If about your identity/company: 'It's Signature Card Services — S-I-G-N-A-T-U-R-E. "
                    "We help businesses like yours save on credit card processing fees.'"
                )
                logger.info(f"[REPETITION] Third-ask ANCHOR escalation triggered for: '{user_text[:50]}'")
            elif _rep_count == 1:
                context['_repetition_escalation'] = 'reframe'
                analysis['_escalation_directive'] = (
                    "[REFRAME] The merchant asked a similar question before. "
                    "You MUST rephrase your answer with DIFFERENT words. Add a new detail they haven't heard. "
                    "Do NOT give the same answer again — that is a conversation killer."
                )
                logger.info(f"[REPETITION] Reframe triggered for: '{user_text[:50]}'")
            else:
                context['_repetition_escalation'] = None

            # [NFC] Neural Flow Cortex — harmonize all organs into unified state
            _nfc = context.get('_nfc')
            if _nfc:
                try:
                    _t_nfc = time.time()
                    _nfc_result = _nfc.step(analysis, context)
                    # Unlock BAL: overwrite locked profile with dynamic NFC values
                    _dyn_behavior = (_nfc_result.get('crossfeeds') or {}).get('dynamic_behavior')
                    if _dyn_behavior and isinstance(context.get('behavior_profile'), dict):
                        context['behavior_profile'].update(_dyn_behavior)
                    _component_times['nfc_ms'] = 1000 * (time.time() - _t_nfc)
                    logger.info(f"[NFC] Character={_nfc_result.get('character')}, "
                                f"dt={_nfc_result.get('step_ms', 0):.1f}ms")
                except Exception as _nfc_e:
                    logger.warning(f"[NFC] Step failed (non-fatal): {_nfc_e}")

            # [ORGAN 24] Retrieval Cortex — fetch relevant knowledge before LLM call
            _rc = context.get('_retrieval_cortex')
            # [ORGAN 35] Check if retrieval is allowed under current IQ budget
            _iq_allow_retrieval = True
            if IQ_BUDGET_WIRED and _iq_organ:
                try:
                    _iq_chk = _iq_organ.can_afford('organ_24_retrieval', ORGAN_COST_MAP.get('organ_24_retrieval', 2))
                    _iq_allow_retrieval = _iq_chk.get('allowed', True)
                    if not _iq_allow_retrieval:
                        logger.info(f"[ORGAN 35] Retrieval blocked: {_iq_chk.get('reason', 'budget')}")
                except Exception:
                    pass  # fail-open: allow retrieval
            if _rc and _iq_allow_retrieval:
                try:
                    _t_retrieval = time.time()
                    _retrieval_results = _rc.retrieve(user_text)
                    _component_times['retrieval_ms'] = 1000 * (time.time() - _t_retrieval)
                    # Filter by confidence threshold
                    _retrieval_hits = [r for r in _retrieval_results if r['score'] >= 0.4]
                    if _retrieval_hits:
                        context['_retrieval_context'] = "\n".join(
                            f"[{r['category'].upper()}] {r['text']}" for r in _retrieval_hits
                        )
                        logger.info(f"[ORGAN 24] Retrieved {len(_retrieval_hits)} items in "
                                   f"{_component_times['retrieval_ms']:.1f}ms "
                                   f"(top: {_retrieval_hits[0]['score']:.3f})")
                        # [ORGAN 32] Feed retrieval hits to summarization organ
                        if SUMMARIZATION_WIRED and context.get('_summarization_organ') and context.get('_summary_state') == 'collecting':
                            try:
                                for _rh in _retrieval_hits:
                                    context['_summarization_organ'].add_retrieval_hit({
                                        'category': _rh.get('category', 'unknown'),
                                        'score': _rh.get('score', 0),
                                        'text': _rh.get('text', '')[:200],
                                    })
                            except Exception as _sum_ret_err:
                                logger.debug(f"[ORGAN 32] Retrieval feed failed (non-fatal): {_sum_ret_err}")
                    else:
                        context.pop('_retrieval_context', None)
                        logger.debug(f"[ORGAN 24] No confident matches for: {user_text[:50]}")
                    # [ORGAN 35] Record retrieval spend
                    if IQ_BUDGET_WIRED and _iq_organ:
                        try:
                            _iq_organ.record_spend('organ_24_retrieval', ORGAN_COST_MAP.get('organ_24_retrieval', 2))
                        except Exception:
                            pass
                except Exception as _rc_err:
                    logger.warning(f"[ORGAN 24] Retrieval failed (non-fatal): {_rc_err}")
                    context.pop('_retrieval_context', None)

            # [ORGAN 34] Competitive Intel — detect competitor mentions + build positioning context
            # [ORGAN 35] Check if competitive intel is allowed under current IQ budget
            _iq_allow_competitive = True
            if IQ_BUDGET_WIRED and _iq_organ:
                try:
                    _iq_chk = _iq_organ.can_afford('organ_34_competitive', ORGAN_COST_MAP.get('organ_34_competitive', 1))
                    _iq_allow_competitive = _iq_chk.get('allowed', True)
                    if not _iq_allow_competitive:
                        logger.info(f"[ORGAN 35] Competitive intel blocked: {_iq_chk.get('reason', 'budget')}")
                except Exception:
                    pass  # fail-open
            if COMPETITIVE_INTEL_WIRED and _iq_allow_competitive:
                try:
                    _t_competitive = time.time()
                    _comp_name, _comp_trigger = detect_competitor_mention(user_text)
                    if _comp_name:
                        context['_detected_competitor'] = _comp_name
                        # Log detection with lineage
                        _detection_entry = {
                            'competitor': _comp_name,
                            'trigger': _comp_trigger,
                            'turn': len(context.get('messages', [])),
                            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                        }
                        context.setdefault('_competitor_detections', []).append(_detection_entry)
                        logger.info(f"[ORGAN 34] Competitor detected: {_comp_name} (trigger: '{_comp_trigger}')")
                        # [ORGAN 32] Feed competitive intel to summarization organ
                        if SUMMARIZATION_WIRED and context.get('_summarization_organ') and context.get('_summary_state') == 'collecting':
                            try:
                                context['_summarization_organ'].add_competitive_intel(_comp_name)
                            except Exception as _sum_comp_err:
                                logger.debug(f"[ORGAN 32] Competitive intel feed failed (non-fatal): {_sum_comp_err}")

                        # Build positioning context from §4.9 script selection rules
                        _positioning = _COMPETITOR_POSITIONING.get(_comp_name, {})
                        _intel = _competitive_intel_organ
                        _comp_profile = _intel.get_competitor(_comp_name) if _intel else None
                        _rebuttals = _intel.get_rebuttal(_comp_name) if _intel else None

                        # [UCP] Unknown Processor Protocol — inject full governed UCP block
                        if _comp_name == 'unknown_processor':
                            context['_competitor_context'] = _UCP_LLM_BLOCK
                            logger.info("[ORGAN 34] Unknown processor detected — UCP block injected")
                        else:
                            _comp_ctx_parts = [f"COMPETITOR DETECTED: {_comp_name}"]
                            if _positioning:
                                _comp_ctx_parts.append(f"Tone Mode: {_positioning.get('tone_mode', 'consultative')}")
                                _comp_ctx_parts.append(f"Closing Style: {_positioning.get('closing_style', 'consultative')}")
                                _comp_ctx_parts.append(f"Positioning: {_positioning.get('positioning', '')}")
                                _comp_ctx_parts.append(f"Key Weakness: {_positioning.get('key_weakness', '')}")
                                _comp_ctx_parts.append(f"Objection Pattern: {_positioning.get('objection_pattern', '')}")
                                _comp_ctx_parts.append(f"Savings Approach: {_positioning.get('savings_approach', '')}")
                            if _comp_profile:
                                _pricing = _comp_profile.get('pricing', '')
                                if _pricing:
                                    _comp_ctx_parts.append(f"Current Pricing: {_pricing}")
                                if _comp_profile.get('is_stale'):
                                    _comp_ctx_parts.append("⚠ DATA STALE — use general framing, not specific numbers.")
                            if _rebuttals:
                                _comp_ctx_parts.append(f"Rebuttals: {'; '.join(_rebuttals[:3])}")
                            _comp_ctx_parts.append("RULE: Never disparage — always compare factually. Use savings math with real numbers when available.")
                            context['_competitor_context'] = '\n'.join(_comp_ctx_parts)
                    else:
                        # No competitor detected — neutral positioning (fail-open)
                        if not context.get('_detected_competitor'):
                            context.pop('_competitor_context', None)
                    _component_times['competitive_ms'] = 1000 * (time.time() - _t_competitive)
                    # [ORGAN 35] Record competitive intel spend
                    if IQ_BUDGET_WIRED and _iq_organ and context.get('_detected_competitor'):
                        try:
                            _iq_organ.record_spend('organ_34_competitive', ORGAN_COST_MAP.get('organ_34_competitive', 1))
                        except Exception:
                            pass
                except Exception as _ci_err:
                    logger.warning(f"[ORGAN 34] Competitive intel failed (non-fatal): {_ci_err}")
                    context.pop('_competitor_context', None)

            # =================================================================
            # [PERSONALITY ENGINE] Probabilistic Personality Matrix per turn
            # =================================================================
            # Full per-turn personality processing with quantum jitter:
            #   1. Reactive mood/empathy/wit shift from merchant sentiment
            #   2. Jittered state vector (no two turns feel identical)
            #   3. Persona classification (playful/empathetic/analytical/etc.)
            #   4. Contextual flare generation (probability-weighted)
            #   5. System instruction crafting for LLM persona shaping
            #   6. Prosody bias hints for Organ 7
            # Fail-open: if PersonalityEngine not loaded, falls back to no-op.
            # =================================================================
            try:
                _sentiment_raw = analysis.get('sentiment', 'neutral')
                _user_text = user_text if isinstance(user_text, str) else ''
                _pe_result = agent.process_personality_turn(_sentiment_raw, _user_text, analysis)
                if _pe_result:
                    # Store flare for prompt injection
                    if _pe_result.get('flare'):
                        context['_personality_flare'] = _pe_result['flare']
                        logger.info(f"[PERSONALITY ENGINE] Flare: '{_pe_result['flare']}' (persona={_pe_result['persona']})")
                    else:
                        context.pop('_personality_flare', None)
                    # Store full personality state for prompt builder
                    context['_personality_state'] = {
                        'system_instruction': _pe_result.get('system_instruction', ''),
                        'persona': _pe_result.get('persona', 'neutral'),
                        'mood_score': _pe_result.get('mood_score', 0.5),
                        'relationship_depth': _pe_result.get('relationship_depth', 0.0),
                    }
                    # Store prosody bias for Organ 7
                    context['_personality_prosody_bias'] = _pe_result.get('prosody_bias', {})
            except Exception as _pm_e:
                logger.debug(f"[PERSONALITY ENGINE] Processing failed (non-fatal): {_pm_e}")

            # =================================================================
            # [SOUL CORE] Ethical awareness — pre-flight check before LLM call
            # =================================================================
            # Evaluates current conversational action against SAP-1 tenets.
            # If vetoed, injects an ethical constraint into context so the
            # prompt builder can steer Alan away from deceptive/zero-sum framing.
            # Fail-open: if SoulCore not loaded, no constraint is added.
            # =================================================================
            try:
                _action_desc = f"respond to merchant who said: {user_text[:80]}"
                _impact = 0.0  # Default neutral — no harm detected
                if analysis.get('sentiment') == 'negative':
                    _impact = -0.1  # Slightly adversarial context
                _approved, _reason = agent.evaluate_ethics(_action_desc, _impact)
                if not _approved:
                    context['_ethical_constraint'] = _reason
                    logger.warning(f"[SOUL CORE] Ethical veto: {_reason}")
                else:
                    context.pop('_ethical_constraint', None)
            except Exception as _sc_e:
                logger.debug(f"[SOUL CORE] Evaluation failed (non-fatal): {_sc_e}")

            # =================================================================
            # [CONV INTEL] LATENCY BRIDGE — Pre-LLM bridging utterance
            # =================================================================
            # Send a short cached bridge phrase ("Yeah, so..." / "Got it...")
            # BEFORE the LLM call to prevent dead air. Bridge audio is pre-cached
            # so it plays instantly while LLM + TTS runs in the background.
            #
            # Fire on turns 2+ — the LLM+TTS pipeline always takes 1.5-5s.
            # The bridge buys ~0.5s of perceived responsiveness.
            # Skip on turn 0-1 (first merchant response after greeting).
            # On the first response, Alan needs to explain why he's calling —
            # a bridge phrase like "So..." before that creates confusion.
            # =================================================================
            _turn_count = len(context.get('messages', []))
            _bridge_sent = False  # [2026-03-03] Track if bridge phrase was sent this turn
            if CONV_INTEL_WIRED and not context.get('stream_ended') and _turn_count > 1:
                _guard = context.get('_conversation_guard')
                if _guard:
                    _bridge_preprocess_ms = 1000 * (time.time() - pipeline_t0)
                    # Determine context type for appropriate bridge
                    _bridge_ctx = 'default'
                    if analysis.get('sentiment') == 'negative' or analysis.get('objections'):
                        _bridge_ctx = 'after_objection'
                    elif '?' in user_text:
                        _bridge_ctx = 'after_question'
                    elif len(user_text.split()) > 15:
                        _bridge_ctx = 'after_info'
                    
                    _bridge_text = _guard.bridge.get_bridge(_bridge_ctx)
                    _bridge_sid = context.get('streamSid')
                    if _bridge_text and _bridge_sid and websocket:
                        logger.info(f"[LATENCY BRIDGE] Sending bridge: '{_bridge_text}' (preprocess={_bridge_preprocess_ms:.0f}ms)")
                        asyncio.create_task(self.synthesize_and_stream_greeting(websocket, _bridge_text, _bridge_sid))
                        _component_times['bridge_ms'] = 1000 * (time.time() - pipeline_t0) - _bridge_preprocess_ms
                        _bridge_sent = True
                        context['_bridge_sent'] = True      # LLM fallback path uses this
                        context['_bridge_text'] = _bridge_text  # So fallback can continue naturally

            # =================================================================
            # [VERSION R+] ORCHESTRATED PIPELINE — The Symphony
            # =================================================================
            # Instead of sequential: LLM(full) → post-process → split → TTS
            # This does: LLM SSE streaming → detect sentence → TTS immediately
            # While LLM generates sentence 2, sentence 1 is already playing.
            # Saves ~800-1500ms on perceived first-word-out latency.
            #
            # [2026-03-03 FIX] BRIDGE-AWARE TIMEOUT
            # When a bridge phrase was already sent ("Good question..."), the
            # merchant is actively waiting for the continuation. Dead air after
            # a bridge is WORSE than dead air without one — it signals
            # "I started to answer but forgot what I was saying."
            # Timeout reduced from 6.0s → 4.0s when bridge was sent.
            # =================================================================
            _t_orchestra = time.time()
            _pipeline_timeout = 4.0 if _bridge_sent else 6.0
            response_text = await asyncio.wait_for(
                self._orchestrated_response(user_text, analysis, context, websocket, agent, generation=generation),
                timeout=_pipeline_timeout
            )
            _component_times['orchestrated_ms'] = 1000 * (time.time() - _t_orchestra)
            
            # [INSTRUCTOR MODE] Record both turns (instructor + Alan) into session
            _inst_session = context.get('_instructor_session')
            if _inst_session and INSTRUCTOR_MODE_WIRED and response_text:
                _inst_session.add_turn(role="alan", text=response_text)
                logger.debug(f"[INSTRUCTOR MODE] Alan turn recorded — {len(response_text)} chars")
            
            # [ORGAN 35] End turn — finalize burn accounting for this turn
            if IQ_BUDGET_WIRED and _iq_organ:
                try:
                    _iq_turn_result = _iq_organ.end_turn()
                    context['_iq_state'] = _iq_turn_result.get('burn_state', 'normal')
                    context['_iq_turn_spend'] = _iq_turn_result.get('spend', 0)
                    context['_iq_burn_total'] = _iq_turn_result.get('total_spent', 0)
                    context['_iq_disabled_organs'] = _iq_turn_result.get('disabled_organs', [])
                    context['_iq_fallback_active'] = _iq_turn_result.get('fallback_active', False)
                    if _iq_turn_result.get('burn_state') != 'normal':
                        logger.info(
                            f"[ORGAN 35] Turn {_iq_turn_result.get('turn', 0)}: "
                            f"spend={_iq_turn_result.get('spend', 0)} | "
                            f"total={_iq_turn_result.get('total_spent', 0)} | "
                            f"state={_iq_turn_result.get('burn_state', 'normal')} | "
                            f"fallback={_iq_turn_result.get('fallback_active', False)}"
                        )
                except Exception as _iq_end_err:
                    logger.debug(f"[ORGAN 35] end_turn failed (non-fatal): {_iq_end_err}")

            # [PIPELINE TIMING] Total turn time with full component breakdown
            total_turn_ms = 1000 * (time.time() - pipeline_t0)
            _comp_str = ' | '.join(f"{k}={v:.0f}" for k, v in _component_times.items())
            logger.info(f"[PIPELINE TIMING] Total turn: {total_turn_ms:.0f}ms [{_comp_str}]")

            # =================================================================
            # [PHASE 3A] ORGANISM HEALTH — Per-Turn Self-Awareness
            # =================================================================
            # After each turn, record signals and compute health level.
            # Stores health level + directive in context for build_llm_prompt().
            # Level 4 (UNFIT) triggers sovereign exit via FSM.
            # =================================================================
            _health_mon = context.get('_health_monitor')
            if _health_mon:
                _had_error = response_text is None or response_text == "I hear you. Tell me more about that."
                _had_veto = bool(context.get('_ethical_constraint'))
                _health_mon.record_turn(
                    llm_latency_ms=_component_times.get('orchestrated_ms', 0),
                    had_error=_had_error,
                    had_fallback=_had_error,
                    had_veto=_had_veto,
                    response_text=response_text or "",
                )
                context['_organism_health_level'] = _health_mon.current_level_name
                context['_organism_health_int'] = _health_mon.current_level_int
                _health_directive = _health_mon.get_directive()
                if _health_directive:
                    context['_organism_health_directive'] = _health_directive
                else:
                    context.pop('_organism_health_directive', None)

                # Level 4 (UNFIT) — sovereign exit (CW23 tuning: engagement + coaching override)
                if _health_mon.is_unfit and not context.get('stream_ended'):
                    # CW23: Check if merchant is engaged before triggering exit
                    _turn_count = context.get('turn_count', 0)
                    _last_merchant = context.get('last_merchant_utterance', '')
                    _merchant_engaged = (
                        _turn_count >= 3
                        and len(_last_merchant) > 20
                        and ('?' in _last_merchant or len(_last_merchant.split()) >= 5)
                    )
                    # CW23: High-coaching override — if call is going well, don't kill it
                    _coaching_override = False
                    try:
                        _guard = context.get('_conversation_guard')
                        if _guard and hasattr(_guard, 'coaching') and _guard.coaching.turn_scores:
                            _running_avg = sum(_guard.coaching.turn_scores) / len(_guard.coaching.turn_scores)
                            if _running_avg >= 0.75 and _turn_count >= 3:
                                _coaching_override = True
                                logger.info(
                                    f"[ORGANISM HEALTH] UNFIT blocked by coaching override "
                                    f"(score={_running_avg:.3f}, turns={_turn_count})"
                                )
                    except Exception as _co_err:
                        logger.debug(f"[ORGANISM HEALTH] Coaching override check failed: {_co_err}")

                    if _coaching_override:
                        pass  # High coaching — let the call continue
                    elif _health_mon.should_suppress_unfit(
                        turn_count=_turn_count,
                        merchant_engaged=_merchant_engaged,
                    ):
                        logger.info(
                            f"[ORGANISM HEALTH] UNFIT suppressed — merchant engaged "
                            f"(turn={_turn_count}, utterance_len={len(_last_merchant)})"
                        )
                    else:
                        logger.warning("[ORGANISM HEALTH] LEVEL 4 UNFIT — triggering sovereign exit")
                        # CW23 Item 3: Capture unfit context for training set
                        try:
                            import json as _json_unfit
                            _unfit_ctx = {
                                'last_merchant_utterance': _last_merchant[:500] if _last_merchant else '',
                                'turn_count': _turn_count,
                                'health_level_history': getattr(_health_mon, '_level_history', [])[-5:] if hasattr(_health_mon, '_level_history') else [],
                                'latency_ms': getattr(_health_mon, 'latency_ms', 0),
                                'error_count': getattr(_health_mon, 'error_count', 0),
                                'repetition_count': getattr(_health_mon, 'repetition_count', 0),
                                'reason': 'threshold_breach',
                            }
                            # Add coaching score at exit if available
                            try:
                                _guard_uc = context.get('_conversation_guard')
                                if _guard_uc and hasattr(_guard_uc, 'coaching') and _guard_uc.coaching.turn_scores:
                                    _unfit_ctx['coaching_at_exit'] = round(
                                        sum(_guard_uc.coaching.turn_scores) / len(_guard_uc.coaching.turn_scores), 3
                                    )
                            except Exception:
                                pass
                            context['_unfit_context'] = _json_unfit.dumps(_unfit_ctx)
                            logger.info(f"[ORGANISM HEALTH] Unfit context captured: turns={_turn_count}, "
                                        f"last_merchant={(_last_merchant or '')[:60]}")
                        except Exception as _uc_err:
                            logger.debug(f"[ORGANISM HEALTH] Unfit context capture failed: {_uc_err}")

                        _fsm = context.get('_call_fsm')
                        if _fsm:
                            _fsm.end_call(reason='organism_unfit')
                        else:
                            context['stream_ended'] = True
                        context['_evolution_outcome'] = 'organism_unfit'

            # =================================================================
            # [PHASE 3B] TELEPHONY HEALTH — Per-Turn Line Assessment
            # =================================================================
            # Check telephony health state after each turn.
            # If degraded → send repair phrase (once). If unusable → sovereign exit.
            # =================================================================
            _tel_mon = context.get('_telephony_monitor')
            if _tel_mon and not context.get('stream_ended'):
                context['_telephony_health_state'] = _tel_mon.current_state_name
                context['_telephony_health_int'] = _tel_mon.current_state_int
                _tel_directive = _tel_mon.get_directive()
                if _tel_directive:
                    context['_telephony_health_directive'] = _tel_directive
                else:
                    context.pop('_telephony_health_directive', None)

                # One-shot repair phrase on first degradation
                if _tel_mon.needs_repair and websocket:
                    _repair = _tel_mon.get_repair_phrase()
                    _stream_sid = context.get('streamSid')
                    if _stream_sid:
                        logger.info(f"[TELEPHONY HEALTH] Sending repair phrase: '{_repair}'")
                        asyncio.create_task(self.synthesize_and_stream_greeting(websocket, _repair, _stream_sid))
                        _tel_mon.mark_repair_sent()

                # Unusable → sovereign withdrawal
                if _tel_mon.should_exit():
                    logger.warning("[TELEPHONY HEALTH] UNUSABLE — triggering sovereign withdrawal")
                    _exit_phrase = _tel_mon.get_exit_phrase()
                    _stream_sid = context.get('streamSid')
                    if _stream_sid and websocket:
                        await self.synthesize_and_stream_greeting(websocket, _exit_phrase, _stream_sid)
                    _fsm = context.get('_call_fsm')
                    if _fsm:
                        _fsm.end_call(reason='telephony_unusable')
                    else:
                        context['stream_ended'] = True
                    context['_evolution_outcome'] = 'telephony_unusable'

            # =================================================================
            # [AQI 0.1mm CHIP] RUNTIME GUARD — Per-Turn Constitutional Audit
            # =================================================================
            # After health monitors have updated context, run all 6 enforcement
            # organs. The guard reads FSM state, health levels, prompt layer
            # order, and supervisor context. Non-blocking, non-crashing.
            # =================================================================
            if AQI_GUARD_WIRED and self._aqi_guard and not context.get('stream_ended'):
                try:
                    _aqi_call_sid = context.get('call_sid', '')
                    _aqi_state = _derive_aqi_state(context)
                    _aqi_prev_state = context.get('_aqi_prev_state', 'OPENING')
                    _aqi_event = _derive_aqi_event(context, user_text)
                    _aqi_health = _build_aqi_health_snapshot(context)
                    # Build prompt layers from tier system
                    _turn_count = len(context.get('messages', []))
                    if _turn_count <= 2:
                        _aqi_layers = ['Identity', 'Personality', 'Mission']  # FAST PATH
                    elif _turn_count <= 7:
                        _aqi_layers = ['Identity', 'Personality', 'Knowledge', 'Mission']  # MIDWEIGHT
                    else:
                        _aqi_layers = ['Identity', 'Ethics', 'Personality', 'Knowledge', 'Mission', 'Output']  # FULL
                    _aqi_ctx = {
                        'turn_count': _turn_count,
                        'response_text': response_text if 'response_text' in locals() else '',
                        'user_text': user_text,
                    }
                    _aqi_violations = self._aqi_guard.on_turn(
                        _aqi_call_sid, _aqi_state, _aqi_prev_state, _aqi_event,
                        _aqi_ctx, _aqi_layers, _aqi_health
                    )
                    # Store current state as prev for next turn
                    context['_aqi_prev_state'] = _aqi_state
                    if _aqi_violations:
                        _aqi_fatal = sum(1 for v in _aqi_violations if v.fatal)
                        logger.warning(f"[AQI GUARD] Turn violations: {len(_aqi_violations)} ({_aqi_fatal} fatal)")
                        context['_aqi_violations_this_turn'] = len(_aqi_violations)
                        context['_aqi_fatal_this_turn'] = _aqi_fatal
                    else:
                        context['_aqi_violations_this_turn'] = 0
                        context['_aqi_fatal_this_turn'] = 0
                except Exception as _aqi_err:
                    logger.warning(f"[AQI GUARD] on_turn failed (non-fatal): {_aqi_err}")

            # =================================================================
            # [PHASE 4] TRACE EXPORTER — Per-Turn Telemetry Capture
            # =================================================================
            # Appends a canonical turn record to the active trace. Accumulates
            # health_trajectory and telephony_trajectory per-turn so the final
            # trace has full state evolution. Non-blocking, non-crashing.
            # =================================================================
            if PHASE4_EXPORTER_WIRED and self._phase4_exporter and not context.get('stream_ended'):
                try:
                    _p4_call_sid = context.get('call_sid', '')
                    if _p4_call_sid and self._phase4_exporter.has_trace(_p4_call_sid):
                        _p4_state = _derive_aqi_state(context)
                        _p4_prev = context.get('_aqi_prev_state', 'OPENING')
                        _p4_event = _derive_aqi_event(context, user_text)
                        _p4_turn_count = len(context.get('messages', []))
                        # Build prompt layer list
                        if _p4_turn_count <= 2:
                            _p4_layers = ['Identity', 'Personality', 'Mission']
                        elif _p4_turn_count <= 7:
                            _p4_layers = ['Identity', 'Personality', 'Knowledge', 'Mission']
                        else:
                            _p4_layers = ['Identity', 'Ethics', 'Personality', 'Knowledge', 'Mission', 'Output']
                        self._phase4_exporter.append_turn(_p4_call_sid, {
                            'fsm_state': _p4_state,
                            'fsm_prev_state': _p4_prev,
                            'fsm_event': _p4_event,
                            'organism_level': context.get('_organism_health_int', 1),
                            'telephony_state': context.get('_telephony_health_state', 'Excellent'),
                            'turn_count': _p4_turn_count,
                            'user_text': user_text,
                            'response_text': response_text if 'response_text' in locals() else '',
                            'aqi_layers': _p4_layers,
                            'master_closer_state': context.get('master_closer_state'),
                            'live_objection_type': context.get('live_objection_type'),
                            'caller_energy': context.get('caller_energy', 'neutral'),
                        })
                except Exception as _p4_err:
                    logger.warning(f"[PHASE 4 EXPORTER] on_turn failed (non-fatal): {_p4_err}")

            # =================================================================
            # [CONV INTEL] POST-CHECK — Repetition Breaker
            # =================================================================
            # After LLM generates response, check if Alan is looping.
            # If bail → override response with exit line and end call.
            # If force_rephrase → inject directive for next turn (too late to re-gen).
            # Record response for future loop detection.
            # =================================================================
            if CONV_INTEL_WIRED and response_text:
                _guard = context.get('_conversation_guard')
                if _guard:
                    _post_result = _guard.post_check(response_text)
                    if _post_result:
                        _post_action = _post_result.get('action', '')
                        if _post_action in ('bail', 'hard_kill'):
                            # Response loop — override with bail line
                            _bail_line = _post_result.get('line', "Let me try you back another time. Take care!")
                            logger.warning(f"[CONV INTEL] REPETITION BAIL — overriding response with: '{_bail_line}'")
                            response_text = _bail_line
                            # [PHASE 2] FSM: → ENDED (repetition_bail)
                            _fsm = context.get('_call_fsm')
                            if _fsm:
                                _fsm.end_call(reason='repetition_bail')
                            else:
                                context['stream_ended'] = True
                            context['_evolution_outcome'] = _post_result.get('outcome', 'repetition_bail')
                            context['_guard_outcome'] = _post_result.get('outcome', 'repetition_bail')
                        elif _post_action == 'force_rephrase':
                            # Can't re-generate this turn, but inject directive for NEXT turn
                            context['_conv_intel_rephrase_directive'] = _post_result.get('directive', '')
                            logger.warning(f"[CONV INTEL] REPETITION WARNING — rephrase directive queued for next turn")
                        elif _post_action == 'nudge':
                            context['_conv_intel_rephrase_directive'] = _post_result.get('directive', '')
                            logger.info(f"[CONV INTEL] Repetition nudge queued for next turn")
                    
                    # Always record what Alan said for future detection
                    _guard.record_alan_response(response_text)

            # [CAPTURE] Record complete turn with full analytics — fire-and-forget
            if CALL_CAPTURE_WIRED:
                try:
                    _mc = context.get('master_closer_state', {})
                    _bp = context.get('behavior_profile', {})
                    _dl = context.get('deep_layer')
                    _dl_mode = _bp.get('deep_layer_mode') if isinstance(_bp, dict) else None
                    _dl_strat = _bp.get('deep_layer_strategy') if isinstance(_bp, dict) else None
                    _pred = context.get('last_predicted_intent')
                    _pred_obj = context.get('last_predicted_objection_type')
                    # [COACHING] Score this turn before writing to CDC
                    _coaching_score_val = None
                    _coaching_flags_str = None
                    if CONV_INTEL_WIRED:
                        try:
                            _guard = context.get('_conversation_guard')
                            if _guard:
                                _alan_resp = response_text if 'response_text' in locals() else ''
                                _turn_telem = context.get('_turn_telemetry', {})
                                _c_score, _c_flags = _guard.score_turn(
                                    user_text, _alan_resp,
                                    {'total_turn_ms': total_turn_ms,
                                     'first_audio_latency_ms': _turn_telem.get('ttfa_ms'),
                                     'llm_ms': _turn_telem.get('llm_ms'),
                                     'preprocess_ms': preprocess_ms if 'preprocess_ms' in locals() else None}
                                )
                                _coaching_score_val = _c_score
                                _coaching_flags_str = ','.join(_c_flags) if _c_flags else None
                        except Exception as _coach_err:
                            logger.debug(f"[COACHING] Per-turn scoring failed: {_coach_err}")
                    
                    _cdc_turn(context.get('call_sid', ''), {
                        'user_text': user_text,
                        'alan_text': response_text if 'response_text' in locals() else '',
                        'sentiment': analysis.get('sentiment', 'neutral') if 'analysis' in locals() else 'neutral',
                        'interest_level': str(analysis.get('interest_level', 'unknown')) if 'analysis' in locals() else 'unknown',
                        'caller_energy': context.get('caller_energy', 'neutral'),
                        'live_objection_type': context.get('live_objection_type'),
                        'preprocess_ms': preprocess_ms if 'preprocess_ms' in locals() else None,
                        'total_turn_ms': total_turn_ms,
                        'llm_ms': context.get('_turn_telemetry', {}).get('llm_ms'),
                        'tts_ms': context.get('_turn_telemetry', {}).get('tts_total_ms'),
                        'deep_layer_mode': _dl_mode,
                        'deep_layer_strategy': _dl_strat,
                        'deep_layer_blend': str(_bp.get('deep_layer_blend')) if isinstance(_bp, dict) and 'deep_layer_blend' in _bp else None,
                        'trajectory': _mc.get('trajectory'),
                        'temperature': _mc.get('temperature'),
                        'confidence_score': _mc.get('confidence_score'),
                        'endgame_state': _mc.get('endgame_state'),
                        'merchant_type': _mc.get('merchant_type'),
                        'trajectory_switches': _mc.get('switches', 0),
                        'agent_x_off_topic': analysis.get('is_off_topic', False) if 'analysis' in locals() else False,
                        'agent_x_category': analysis.get('off_topic_category') if 'analysis' in locals() else None,
                        'agent_x_mode': analysis.get('off_topic_mode') if 'analysis' in locals() else None,
                        'predicted_intent': _pred,
                        'predicted_objection': _pred_obj,
                        'prediction_confidence': None,
                        'behavior_tone': _bp.get('tone') if isinstance(_bp, dict) else None,
                        'behavior_closing_bias': _bp.get('closing_bias') if isinstance(_bp, dict) else None,
                        'reasoning_block': str(context.get('reasoning_block', ''))[:500] if context.get('reasoning_block') else None,
                        'coaching_score': _coaching_score_val,
                        'coaching_flags': _coaching_flags_str,
                    })
                except Exception as _cdc_turn_err:
                    logger.warning(f"[CDC TURN] Turn capture failed (non-fatal): {_cdc_turn_err}")  # Was silent pass

            # [LATENCY MASK] Store turn latency so Agent X can mask lag on NEXT turn
            context['_last_turn_latency_ms'] = total_turn_ms
            
            # [FIX R5b 2026-02-20] Old fallback location removed — fallback now fires
            # INSIDE _orchestrated_response() BEFORE return, so audio is synthesized
            # and streamed to Twilio before CDC/health/evolution see the response.
            # The old fallback here was too late: CDC already captured empty, TTS=0ms,
            # merchant heard dead air. See Pool Service incident (batch 3, Call 1).

            # [CLOSER STACK] Adaptive Closing Strategy — DEFERRED TO AFTER AUDIO
            # [VERSION R+] Analytics run AFTER speaking, not before. The audience
            # hears Alan's response faster because we don't block on analytics.
            mc_state = context.get('master_closer_state', {})
            if analysis.get('interest_level') == 'high' or len(context['messages']) > 5 or mc_state.get('endgame_state') == 'ready':
                style = self.closing_engine.choose_style(analysis)
                if mc_state.get('merchant_type') != 'unknown':
                    m_type_cfg = self.master_closer.config.get('merchant_types', {}).get(mc_state.get('merchant_type', ''), {})
                    if m_type_cfg.get('bias'):
                        style = m_type_cfg['bias']
                if context.get('behavior_profile') and context['behavior_profile'].get('closing_bias'):
                    style = context['behavior_profile'].get('closing_bias')
                if context.get('preferences', {}).get('closing_style_bias'):
                    style = context['preferences'].get('closing_style_bias')
                logger.info(f"[CLOSER] Readiness: endgame={mc_state.get('endgame_state')}, style={style}, interest={analysis.get('interest_level')}")

            # [ORGAN] Hook 5 — Alan Response
            if CALL_MONITOR_WIRED and response_text:
                response_time_s = (time.time() - pipeline_t0)
                monitor_alan_response(context.get('call_sid', ''), response_text, response_time_s)
                if response_time_s > 4.0:
                    monitor_call_warning(context.get('call_sid', ''), f"Slow response: {response_time_s:.2f}s")
            
            # [LIVE MONITOR] Record Alan's speech for live state tracking
            if LIVE_MONITOR_WIRED and _live_monitor and response_text:
                _live_monitor.record_alan_speech(context.get('call_sid', ''), response_text)

        except asyncio.TimeoutError:
            logger.warning("[ORCHESTRATED] ⚠️ Pipeline timeout (6.0s). Recovering.")
            # [2026-03-02 FIX] Changed timeout fallback from yet another "quick question"
            # variant to a different formulation. The old text reinforced the "quick question"
            # repetition loop — the LLM saw multiple "quick question" entries in history
            # and mirrored the pattern on subsequent turns.
            response_text = "Hey, I'm still here — so who handles the card processing for you guys?"
            # [RECOVERY] Reset HTTP session with adapter — the old one may be stuck/poisoned
            try:
                self._llm_session.close()
            except Exception as _sess_err:
                logger.debug(f"[RECOVERY] HTTP session close failed: {_sess_err}")
            from requests.adapters import HTTPAdapter as _RecoveryAdapter
            self._llm_session = requests.Session()
            self._llm_session.mount("https://", _RecoveryAdapter(pool_connections=4, pool_maxsize=8))
            self._llm_session.headers.update({"Content-Type": "application/json"})
            logger.info("[RECOVERY] HTTP session reset after timeout")
            if CALL_MONITOR_WIRED:
                monitor_call_error(context.get('call_sid', ''), 'PIPELINE_TIMEOUT', 'Orchestrated pipeline timeout 6s')
            
        except Exception as e:
            logger.error(f"[ORCHESTRATED] Pipeline Error: {e}")
            traceback.print_exc()
            response_text = "I'm still with you—what would you like to focus on next?"
            if CALL_MONITOR_WIRED:
                monitor_call_error(context.get('call_sid', ''), 'PIPELINE_ERROR', str(e))

        # Update conversation state
        try:
            context['messages'].append({
                'timestamp': datetime.now(),
                'user': user_text,
                'alan': response_text,
                'sentiment': analysis.get('sentiment') if 'analysis' in locals() else 'neutral',
                'interest': analysis.get('interest_level') if 'analysis' in locals() else 0
            })

            # [ORGAN 32] Feed transcript turns to summarization organ
            if SUMMARIZATION_WIRED and context.get('_summarization_organ') and context.get('_summary_state') == 'collecting':
                try:
                    context['_summarization_organ'].add_transcript_turn('merchant', user_text)
                    if response_text:
                        context['_summarization_organ'].add_transcript_turn('alan', response_text)
                except Exception as _sum_feed_err:
                    logger.debug(f"[ORGAN 32] Transcript feed failed (non-fatal): {_sum_feed_err}")

            # [SWEEP] Cap message history to prevent unbounded memory growth
            MAX_MESSAGES = 100
            if len(context['messages']) > MAX_MESSAGES:
                context['messages'] = context['messages'][-MAX_MESSAGES:]

            # Check if we should end the conversation
            should_end = self.should_end_conversation(analysis, context) if 'analysis' in locals() else False
            # [CONV INTEL] Force end if guard triggered stream_ended
            if context.get('stream_ended'):
                should_end = True
        except Exception as cleanup_err:
            logger.error(f"[CLEANUP] Error during state update: {cleanup_err}")
            should_end = False

        # HUMAN MODEL CLEANUP — No locks to release. Just note what happened.
        was_superseded = context.get('response_generation') != generation
        context['audio_playing'] = False
        if not was_superseded:
            context['responding_ended_at'] = time.time()  # Echo cooldown reference
            context['vad_state'] = 'silence'
            context['vad_speech_frames'] = 0
        logger.info(f"[TURN] Response complete gen {generation} ({'superseded' if was_superseded else 'natural end'}).")

        # Return JSON for logging (ignored by Twilio Media Stream generally)
        return {
            'type': 'conversation_reply',
            'speech': response_text if 'response_text' in locals() else '',
            'end_conversation': should_end if 'should_end' in locals() else False
        }

    async def handle_dtmf(self, data, context):
        """
        Handle inbound DTMF input received from the call.
        Routes to Organ 36 (DTMF Reflex) for audit logging,
        and to Organ 37 (IVR Navigator) if IVR navigation is active.
        """
        digits = data.get('digits', '') or data.get('digit', '')
        logger.info(f"[DTMF] Received inbound DTMF: '{digits}'")

        # [ORGAN 36] Record received DTMF for audit trail
        if DTMF_REFLEX_WIRED:
            _dtmf = context.get('_dtmf_reflex')
            if _dtmf:
                for d in digits:
                    _dtmf.record_received(d, context=f"inbound_dtmf")

        # If IVR navigation is active, the Navigator doesn't need inbound DTMF —
        # it's the OUTBOUND DTMF (Alan pressing buttons) that matters.
        # Inbound DTMF from the far side is unusual but we log it.
        if digits:
            logger.info(f"[DTMF] Inbound DTMF '{digits}' logged. No action required.")

        return {
            'type': 'conversation_reply',
            'speech': '',
            'end_conversation': False
        }

    def should_end_conversation(self, analysis, context):
        """
        Determine if the conversation should end
        """
        # End if user explicitly wants to end
        user_text = context['messages'][-1]['user'].lower() if context['messages'] else ''
        
        # Strong termination signals
        termination_phrases = ['hang up', 'end call', 'stop calling', 'take me off your list', 'goodbye', 'bye']
        
        if any(phrase in user_text for phrase in termination_phrases):
            return True

        # NOTE: We do NOT hang up on 'low' interest anymore.
        # Alan is a top salesman; he will try to handle the objection.
        # The user must explicitly end the call.
        
        # Continue conversation
        return False

    def get_conversation_stats(self):
        """
        Get conversation statistics
        """
        return {
            'active_conversations': len(self.active_conversations),
            'total_conversations': len(self.active_conversations),  # For now
            'server_status': 'running'
        }

    async def prewarm_system(self):
        """
        Pre-warm system components after startup.
        Greetings are already cached by _precache_greetings() in __init__.
        This method handles any remaining async warm-up tasks.
        
        [LATENCY FIX] Also fires a real LLM API call with the FAST_PATH_PROMPT
        to warm the TCP/TLS connection pool AND OpenAI's internal prompt cache.
        Without this, the FIRST call after server start suffers 3-9s cold-start
        latency because: (1) new TCP handshake, (2) new TLS negotiation,
        (3) OpenAI prompt cache is cold. This prewarm eliminates all three.
        """
        if not self.shared_agent_instance:
            return

        logger.info("[ALAN AI] Pre-warm system check...")

        # Greetings already cached in __init__ via _precache_greetings()
        cached_count = len(self.greeting_cache)
        if cached_count > 0:
            logger.info(f"[ALAN AI] Greeting cache already warm: {cached_count} variants ({sum(len(v) for v in self.greeting_cache.values())} bytes)")
        else:
            # Fallback: cache at least one default greeting if __init__ cache failed
            logger.warning("[ALAN AI] Greeting cache empty — attempting fallback cache...")
            try:
                greeting = self.shared_agent_instance.generate_business_greeting(
                    strategy='cold_call',
                    prospect_name='there',
                    company='',
                    signal_data=None
                )
                mulaw_bytes = await self.synthesize_greeting_to_mulaw_bytes(greeting)
                if mulaw_bytes:
                    self.greeting_cache[greeting] = mulaw_bytes
                    logger.info(f"[ALAN AI] Fallback greeting cached ({len(mulaw_bytes)} bytes)")
            except Exception as e:
                logger.error(f"[ALAN AI] Fallback cache failed: {e}")

        # [LATENCY FIX] Fire a real LLM warmup call — warms TCP pool, TLS, and
        # OpenAI's internal prompt cache. Uses FAST_PATH_PROMPT (the one used for
        # turns 0-2) so the very first call benefits from a hot cache.
        try:
            agent = self.shared_agent_instance
            api_key = agent.get_api_key() if hasattr(agent, 'get_api_key') else None
            fast_prompt = getattr(agent, 'FAST_PATH_PROMPT', None) or getattr(agent, 'system_prompt', '')
            if api_key and fast_prompt:
                import concurrent.futures
                loop = asyncio.get_running_loop()
                def _warmup_llm():
                    url = "https://api.openai.com/v1/chat/completions"
                    payload = {
                        "model": "gpt-4o-mini",
                        "messages": [
                            {"role": "system", "content": fast_prompt[:2000]},
                            {"role": "user", "content": "Hello"}
                        ],
                        "max_tokens": 5,
                        "temperature": 0,
                        "stream": True,  # Stream to warm the SSE path too
                    }
                    headers = {"Authorization": f"Bearer {api_key}"}
                    t0 = time.time()
                    with self._llm_session.post(url, json=payload, headers=headers, stream=True, timeout=(5, 10)) as r:
                        r.raise_for_status()
                        # Drain the stream to complete the connection cycle
                        for line in r.iter_lines():
                            pass
                    elapsed = 1000 * (time.time() - t0)
                    logger.info(f"[BOOT WARMUP] LLM connection + prompt cache warmed in {elapsed:.0f}ms")
                await loop.run_in_executor(None, _warmup_llm)
            else:
                logger.warning("[BOOT WARMUP] Skipped — no API key or prompt available")
        except Exception as e:
            logger.warning(f"[BOOT WARMUP] LLM warmup failed (non-critical): {e}")

async def main():
    """
    Main server function
    """
    # [STARTUP GUARD] Prevent multiple server instances on the same port
    # Tim's Issue: 3-4 zombie server processes were running simultaneously
    import socket as _startup_socket
    _guard_sock = _startup_socket.socket(_startup_socket.AF_INET, _startup_socket.SOCK_STREAM)
    _port_result = _guard_sock.connect_ex(('127.0.0.1', 8777))
    _guard_sock.close()
    if _port_result == 0:
        logger.error(
            "[STARTUP GUARD] Port 8777 is ALREADY IN USE! "
            "Another server instance is running. Kill it first:\n"
            "  PowerShell: Get-NetTCPConnection -LocalPort 8777 | Select-Object OwningProcess\n"
            "  Then: Stop-Process -Id <PID> -Force"
        )
        print("\n❌ ERROR: Port 8777 is already in use by another process!")
        print("   Kill the existing process first, then restart.")
        sys.exit(1)
    
    # [PID FILE] Write PID for external monitoring
    _pid_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "alan_server.pid")
    try:
        with open(_pid_file, 'w') as f:
            f.write(str(os.getpid()))
        logger.info(f"[STARTUP] PID {os.getpid()} written to {_pid_file}")
    except Exception as e:
        logger.warning(f"[STARTUP] Could not write PID file: {e}")
    
    server = AQIConversationRelayServer()

    # [OPTIMIZATION] Pre-warm Audio Cache
    await server.prewarm_system()

    # Start websocket server
    # [FIX] Port changed to 8777 match production tunnel (Nginx upstream: 10.8.0.2:8777)
    start_server = websockets.serve(
        server.handle_conversation,
        "0.0.0.0", # Bind to all interfaces to catch WireGuard traffic
        8777,
        ping_interval=None  # Disable ping to avoid issues with Twilio
    )

    logger.info("🚀 Starting AQI Conversation Relay Server on ws://0.0.0.0:8777")

    async with start_server:
        logger.info("Server started successfully")
        logger.info("🎯 Ready to handle Twilio ConversationRelay connections")

        # [MAINTENANCE] Start background maintenance scheduler
        if MAINTENANCE_WIRED and _maintenance_scheduler:
            _maintenance_scheduler.set_server_ref(server)
            asyncio.create_task(_maintenance_scheduler.run())
            logger.info("[MAINTENANCE] Background scheduler launched (GC every 5min, health every 60s, log rotation every 1hr)")

        # Keep server running
        await asyncio.Future()  # Run forever

if __name__ == "__main__":
    print("AQI CONVERSATION RELAY SERVER")
    print("=" * 40)
    print("AI-powered conversation handling for Twilio calls")
    print("WebSocket server on port 8777")
    print("Ready for Agent Alan conversations")
    print()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Server shutdown requested")
    except Exception as e:
        print(f"❌ Server error: {e}")
    finally:
        # [CLEANUP] Remove PID file on exit
        _pid_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "alan_server.pid")
        try:
            if os.path.exists(_pid_path):
                os.remove(_pid_path)
        except Exception as _pid_err:
            logger.debug(f"[CLEANUP] PID file removal failed: {_pid_err}")