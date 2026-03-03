#!/usr/bin/env python3
"""
CALL DATA CAPTURE SYSTEM
=========================
Non-intrusive, comprehensive call data capture for every Alan production call.

Captures:
  - Full transcript (every turn: user + Alan, timestamped)
  - Per-turn pipeline timing (STT, pre-process, LLM, TTS, total)
  - Deep Layer state per turn (QPC decision, Fluidic mode, Continuum field)
  - Agent X dispatch logs (P0-P5 decisions, time budget usage)
  - Master Closer state per turn (trajectory, temperature, confidence, endgame)
  - Evolution Engine post-call adjustments (outcome, confidence, nudge)
  - Outcome Detection with confidence band
  - Coaching scores (post-call)
  - Signature Learning deltas per call
  - Call metadata (SID, duration, merchant info, error count)

Design Principles:
  - ZERO latency impact: All writes happen in a background thread
  - ZERO failure propagation: Every operation is wrapped in try/except
  - FIRE-AND-FORGET: The relay server calls capture functions and moves on
  - APPEND-ONLY: Data is never modified after capture, only appended
  - SELF-HEALING: If the DB is locked or unavailable, data is queued in memory

Author: Claude Opus 4.6 — AQI System Expert
Date: February 17, 2026
Neg-Proofed: Yes — all operations fail silently, no exceptions propagate
"""

import os
import json
import time
import sqlite3
import logging
import threading
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path
from collections import deque

logger = logging.getLogger(__name__)

# =============================================================================
# DATABASE SCHEMA
# =============================================================================

_SCHEMA = """
-- Master call record: one row per call
CREATE TABLE IF NOT EXISTS calls (
    call_sid TEXT PRIMARY KEY,
    session_id TEXT,
    merchant_phone TEXT DEFAULT '',
    merchant_name TEXT DEFAULT '',
    business_name TEXT DEFAULT '',
    start_time TEXT NOT NULL,
    end_time TEXT,
    duration_seconds REAL,
    total_turns INTEGER DEFAULT 0,
    merchant_words INTEGER DEFAULT 0,
    alan_words INTEGER DEFAULT 0,
    final_outcome TEXT DEFAULT 'unknown',
    outcome_confidence REAL DEFAULT 0.0,
    outcome_band TEXT DEFAULT 'unknown',
    engagement_score REAL DEFAULT 0.0,
    final_trajectory TEXT DEFAULT 'neutral',
    final_temperature INTEGER DEFAULT 50,
    final_confidence_score INTEGER DEFAULT 50,
    final_endgame TEXT DEFAULT 'not_ready',
    final_merchant_type TEXT DEFAULT 'unknown',
    error_count INTEGER DEFAULT 0,
    coaching_score REAL,
    coaching_strengths TEXT,
    coaching_weaknesses TEXT,
    coaching_action_item TEXT,
    signature_speed_bias REAL,
    signature_silence_bias INTEGER,
    signature_breath_bias REAL,
    signature_caller_influence REAL,
    evolution_nudge TEXT,
    attribution_dimensions TEXT,
    deep_layer_final_mode TEXT,
    deep_layer_final_strategy TEXT,
    greeting_text TEXT,
    call_type TEXT,
    call_type_confidence REAL,
    call_type_raw_scores TEXT,
    call_type_probabilities TEXT,
    call_type_override_flags TEXT,
    call_type_reasoning TEXT,
    killed_by TEXT,
    voice_avg_drift REAL,
    voice_max_drift REAL,
    voice_integrity TEXT,
    inbound_metrics TEXT,
    perception_vector TEXT,
    behavioral_vector TEXT,
    coaching_tags TEXT,
    unfit_context TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

-- Per-turn detail: one row per conversational exchange
CREATE TABLE IF NOT EXISTS turns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    call_sid TEXT NOT NULL,
    turn_number INTEGER NOT NULL,
    timestamp TEXT NOT NULL,
    user_text TEXT DEFAULT '',
    alan_text TEXT DEFAULT '',
    user_word_count INTEGER DEFAULT 0,
    alan_word_count INTEGER DEFAULT 0,
    sentiment TEXT DEFAULT 'neutral',
    interest_level TEXT DEFAULT 'unknown',
    caller_energy TEXT DEFAULT 'neutral',
    live_objection_type TEXT,
    -- Pipeline timing (milliseconds)
    preprocess_ms REAL,
    llm_ms REAL,
    tts_ms REAL,
    total_turn_ms REAL,
    -- Deep Layer state
    deep_layer_mode TEXT,
    deep_layer_strategy TEXT,
    deep_layer_blend TEXT,
    -- Master Closer state
    trajectory TEXT,
    temperature INTEGER,
    confidence_score INTEGER,
    endgame_state TEXT,
    merchant_type TEXT,
    trajectory_switches INTEGER DEFAULT 0,
    -- Agent X dispatch
    agent_x_off_topic INTEGER DEFAULT 0,
    agent_x_category TEXT,
    agent_x_mode TEXT,
    -- Predictive intent
    predicted_intent TEXT,
    predicted_objection TEXT,
    prediction_confidence REAL,
    -- Behavior profile
    behavior_tone TEXT,
    behavior_closing_bias TEXT,
    -- CRG reasoning
    reasoning_block TEXT,
    -- Coaching engine (per-turn)
    coaching_score REAL,
    coaching_flags TEXT,
    FOREIGN KEY (call_sid) REFERENCES calls(call_sid)
);

-- Errors captured during calls
CREATE TABLE IF NOT EXISTS call_errors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    call_sid TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    error_type TEXT NOT NULL,
    error_message TEXT,
    FOREIGN KEY (call_sid) REFERENCES calls(call_sid)
);

-- Evolution engine post-call logs
CREATE TABLE IF NOT EXISTS evolution_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    call_sid TEXT,
    timestamp TEXT NOT NULL,
    outcome TEXT,
    confidence REAL,
    band TEXT,
    engagement_score REAL,
    nudge_applied TEXT,
    attribution TEXT
);

-- [EAB] Environment classification events
CREATE TABLE IF NOT EXISTS environment_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    call_sid TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    env_class TEXT,
    env_confidence REAL,
    behavior TEXT,
    outcome TEXT,
    utterance TEXT,
    cycles INTEGER DEFAULT 0,
    FOREIGN KEY (call_sid) REFERENCES calls(call_sid)
);

-- [EAB-PLUS] Enhanced environment signals per turn
CREATE TABLE IF NOT EXISTS env_plus_signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    call_sid TEXT NOT NULL,
    turn_index INTEGER NOT NULL,
    env_class TEXT,
    env_action TEXT,
    env_behavior TEXT,
    hangup_risk REAL,
    prosody_is_human REAL,
    prosody_emotion_busy REAL,
    prosody_emotion_annoyed REAL,
    prosody_emotion_curious REAL,
    silence_is_machine REAL,
    silence_is_voicemail REAL,
    silence_has_beep REAL,
    timing_prior_env_class TEXT,
    timing_confidence REAL,
    vertical TEXT,
    state TEXT,
    lead_last_env_class TEXT,
    resolution_reason TEXT,
    resolve_ms REAL,
    zero_turn_class TEXT DEFAULT NULL,
    dnc_flag INTEGER DEFAULT 0,
    there_spam_flag INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(call_sid) REFERENCES calls(call_sid)
);

-- Indexes for fast queries
CREATE INDEX IF NOT EXISTS idx_turns_call_sid ON turns(call_sid);
CREATE INDEX IF NOT EXISTS idx_turns_timestamp ON turns(timestamp);
CREATE INDEX IF NOT EXISTS idx_calls_start ON calls(start_time);
CREATE INDEX IF NOT EXISTS idx_errors_call_sid ON call_errors(call_sid);
CREATE INDEX IF NOT EXISTS idx_env_class ON environment_events(env_class);
CREATE INDEX IF NOT EXISTS idx_env_call_sid ON environment_events(call_sid);
CREATE INDEX IF NOT EXISTS idx_env_plus_call ON env_plus_signals(call_sid);
CREATE INDEX IF NOT EXISTS idx_env_plus_env_class ON env_plus_signals(env_class);
CREATE INDEX IF NOT EXISTS idx_env_plus_hangup_risk ON env_plus_signals(hangup_risk);
"""


# =============================================================================
# CAPTURE ENGINE
# =============================================================================

class CallDataCaptureEngine:
    """
    Non-intrusive call data capture engine.
    
    All public methods are fire-and-forget: they queue work to a background
    thread and return immediately. The relay server's hot path is never blocked.
    """

    def __init__(self, db_path: str = None):
        if db_path is None:
            base = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(base, "data", "call_capture.db")
        
        self._db_path = db_path
        self._queue: deque = deque(maxlen=10000)  # Bounded queue prevents memory leak
        self._lock = threading.Lock()
        self._active_calls: Dict[str, Dict[str, Any]] = {}
        self._initialized = False
        
        # Initialize DB in background
        self._bg_exec(self._init_db)
        logger.info(f"[CAPTURE] Call Data Capture Engine initialized — DB: {db_path}")

    def _init_db(self):
        """Create database and tables if they don't exist."""
        try:
            os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
            conn = sqlite3.connect(self._db_path, timeout=10)
            conn.executescript(_SCHEMA)
            # Migration: add classifier/behavioral columns to existing databases
            with sqlite3.connect(self._db_path) as conn:
                _migration_cols = [
                    ('call_type', 'TEXT'),
                    ('call_type_confidence', 'REAL'),
                    ('call_type_raw_scores', 'TEXT'),
                    ('call_type_probabilities', 'TEXT'),
                    ('call_type_override_flags', 'TEXT'),
                    ('call_type_reasoning', 'TEXT'),
                    ('killed_by', 'TEXT'),
                    ('voice_avg_drift', 'REAL'),
                    ('voice_max_drift', 'REAL'),
                    ('voice_integrity', 'TEXT'),
                    ('inbound_metrics', 'TEXT'),
                    ('perception_vector', 'TEXT'),
                    ('behavioral_vector', 'TEXT'),
                    ('coaching_tags', 'TEXT'),
                    ('unfit_context', 'TEXT')
                ]
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(calls)")
                existing_cols = {row[1] for row in cursor.fetchall()}

                for col_name, col_type in _migration_cols:
                    if col_name not in existing_cols:
                        try:
                            cursor.execute(f'ALTER TABLE calls ADD COLUMN {col_name} {col_type}')
                        except Exception as e:
                            logger.warning(f"[CAPTURE] Migration warning for {col_name}: {e}")

                conn.commit()

            self._initialized = True
            logger.info("[CAPTURE] Database schema initialized")
        except Exception as e:
            logger.error(f"[CAPTURE] DB init failed (will retry on first write): {e}")

    def _get_conn(self) -> Optional[sqlite3.Connection]:
        """Get a fresh SQLite connection (connections are NOT thread-safe, create per-use)."""
        try:
            if not self._initialized:
                self._init_db()
            conn = sqlite3.connect(self._db_path, timeout=10)
            conn.execute("PRAGMA journal_mode=WAL")  # WAL for concurrent reads
            conn.execute("PRAGMA synchronous=NORMAL")  # Faster writes, still durable
            return conn
        except Exception as e:
            logger.error(f"[CAPTURE] Failed to connect to DB: {e}")
            return None

    def _bg_exec(self, fn, *args, **kwargs):
        """Execute a function in a background thread. Fire-and-forget."""
        def _wrapper():
            try:
                fn(*args, **kwargs)
            except Exception as e:
                logger.error(f"[CAPTURE] Background task failed: {e}")
        
        t = threading.Thread(target=_wrapper, daemon=True)
        t.start()

    # -------------------------------------------------------------------------
    # PUBLIC API — Called from the relay server
    # -------------------------------------------------------------------------

    def capture_call_start(self, call_sid: str, session_id: str,
                           merchant_phone: str = "", merchant_name: str = "",
                           business_name: str = ""):
        """
        Capture call start. Called when Twilio stream 'start' event arrives.
        Zero-latency: queues to background thread.
        """
        call_data = {
            "call_sid": call_sid,
            "session_id": session_id,
            "merchant_phone": merchant_phone,
            "merchant_name": merchant_name,
            "business_name": business_name,
            "start_time": datetime.now().isoformat(),
            "turn_count": 0,
        }
        self._active_calls[call_sid] = call_data
        self._bg_exec(self._write_call_start, call_data)

    def capture_greeting(self, call_sid: str, greeting_text: str):
        """Capture the greeting Alan sends."""
        if call_sid in self._active_calls:
            self._active_calls[call_sid]["greeting_text"] = greeting_text
        self._bg_exec(self._write_greeting, call_sid, greeting_text)

    def capture_turn(self, call_sid: str, turn_data: Dict[str, Any]):
        """
        Capture a complete conversational turn (user spoke → Alan responded).
        
        turn_data should contain:
            user_text, alan_text, sentiment, interest_level, caller_energy,
            live_objection_type, preprocess_ms, total_turn_ms,
            deep_layer_mode, deep_layer_strategy, deep_layer_blend,
            trajectory, temperature, confidence_score, endgame_state,
            merchant_type, trajectory_switches,
            agent_x_off_topic, agent_x_category, agent_x_mode,
            predicted_intent, predicted_objection, prediction_confidence,
            behavior_tone, behavior_closing_bias, reasoning_block
        """
        if call_sid in self._active_calls:
            self._active_calls[call_sid]["turn_count"] = \
                self._active_calls[call_sid].get("turn_count", 0) + 1
        
        turn_data["call_sid"] = call_sid
        turn_data["turn_number"] = self._active_calls.get(call_sid, {}).get("turn_count", 0)
        turn_data["timestamp"] = datetime.now().isoformat()
        
        self._bg_exec(self._write_turn, turn_data)

    def capture_error(self, call_sid: str, error_type: str, error_message: str):
        """Capture an error during a call."""
        self._bg_exec(self._write_error, call_sid, error_type, error_message)

    def capture_call_end(self, call_sid: str, end_data: Dict[str, Any] = None):
        """
        Capture call end with final state.
        
        end_data may contain:
            duration_seconds, final_outcome, outcome_confidence, outcome_band,
            engagement_score, final_trajectory, final_temperature,
            final_confidence_score, final_endgame, final_merchant_type,
            error_count, evolution_nudge, attribution_dimensions,
            deep_layer_final_mode, deep_layer_final_strategy,
            signature_speed_bias, signature_silence_bias,
            signature_breath_bias, signature_caller_influence
        """
        if end_data is None:
            end_data = {}
        
        end_data["call_sid"] = call_sid
        end_data["end_time"] = datetime.now().isoformat()
        
        # Merge active call data
        if call_sid in self._active_calls:
            active = self._active_calls[call_sid]
            end_data.setdefault("total_turns", active.get("turn_count", 0))
            if "start_time" in active:
                start = datetime.fromisoformat(active["start_time"])
                end_data.setdefault("duration_seconds",
                                    (datetime.now() - start).total_seconds())
        
        self._bg_exec(self._write_call_end, end_data)
        
        # Also write full JSON transcript (compatible with existing format)
        self._bg_exec(self._write_json_transcript, call_sid)
        
        # Cleanup active call tracking
        self._active_calls.pop(call_sid, None)

    def capture_evolution_event(self, call_sid: str, outcome: str,
                                confidence: float, band: str,
                                engagement_score: float,
                                nudge: str = "", attribution: str = ""):
        """Capture evolution engine post-call analysis."""
        self._bg_exec(self._write_evolution_event,
                       call_sid, outcome, confidence, band,
                       engagement_score, nudge, attribution)

    def capture_coaching(self, call_sid: str, score: float,
                         strengths: str, weaknesses: str, action_item: str):
        """Capture post-call coaching analysis results."""
        self._bg_exec(self._write_coaching, call_sid, score,
                       strengths, weaknesses, action_item)

    def capture_environment(self, call_sid: str, env_class: str,
                            env_confidence: float, behavior: str,
                            outcome: str = '', utterance: str = '',
                            cycles: int = 0):
        """Capture EAB environment classification event."""
        self._bg_exec(self._write_environment, call_sid, env_class,
                       env_confidence, behavior, outcome, utterance, cycles)

    def _write_environment(self, call_sid, env_class, env_confidence,
                           behavior, outcome, utterance, cycles):
        try:
            conn = self._get_conn()
            if not conn:
                return
            conn.execute(
                "INSERT INTO environment_events "
                "(call_sid, timestamp, env_class, env_confidence, behavior, outcome, utterance, cycles) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (call_sid, datetime.utcnow().isoformat() + 'Z',
                 env_class, env_confidence, behavior, outcome, utterance, cycles)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"[CAPTURE] Environment write failed: {e}")

    def capture_env_plus_signals(self, call_sid: str, turn_index: int,
                                  ctx: Dict, eab_result: Dict):
        """Capture EAB-Plus enhanced environment signals per turn."""
        self._bg_exec(self._write_env_plus_signals,
                       call_sid, turn_index, ctx, eab_result)

    def _write_env_plus_signals(self, call_sid, turn_index, ctx, eab_result):
        try:
            conn = self._get_conn()
            if not conn:
                return
            prosody = eab_result.get("prosody", {})
            silence = eab_result.get("silence", {})
            timing = eab_result.get("timing", {})
            lead_prior = eab_result.get("lead_prior", {})
            conn.execute(
                """INSERT INTO env_plus_signals (
                    call_sid, turn_index,
                    env_class, env_action, env_behavior,
                    hangup_risk,
                    prosody_is_human,
                    prosody_emotion_busy,
                    prosody_emotion_annoyed,
                    prosody_emotion_curious,
                    silence_is_machine,
                    silence_is_voicemail,
                    silence_has_beep,
                    timing_prior_env_class,
                    timing_confidence,
                    vertical, state,
                    lead_last_env_class,
                    resolution_reason,
                    resolve_ms,
                    zero_turn_class,
                    dnc_flag,
                    there_spam_flag
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    call_sid,
                    turn_index,
                    eab_result.get("env_class"),
                    ctx.get("env_action"),
                    ctx.get("env_behavior"),
                    eab_result.get("hangup_risk"),
                    prosody.get("is_human"),
                    prosody.get("emotion_busy"),
                    prosody.get("emotion_annoyed"),
                    prosody.get("emotion_curious"),
                    silence.get("is_machine"),
                    silence.get("is_voicemail"),
                    silence.get("has_beep"),
                    timing.get("prior_env_class"),
                    timing.get("confidence"),
                    ctx.get("vertical"),
                    ctx.get("state"),
                    lead_prior.get("last_env_class"),
                    eab_result.get("resolution_reason"),
                    eab_result.get("resolve_ms"),
                    ctx.get("zero_turn_class"),
                    int(ctx.get("dnc_flag", 0) or 0),
                    int(ctx.get("there_spam_flag", 0) or 0),
                ),
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"[CAPTURE] Env-Plus write failed: {e}")

    # -------------------------------------------------------------------------
    # QUERY API — For monitoring and analysis
    # -------------------------------------------------------------------------

    def get_call_summary(self, call_sid: str) -> Optional[Dict]:
        """Get summary of a specific call."""
        try:
            conn = self._get_conn()
            if not conn:
                return None
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM calls WHERE call_sid = ?",
                               (call_sid,)).fetchone()
            conn.close()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"[CAPTURE] Query failed: {e}")
            return None

    def get_call_turns(self, call_sid: str) -> List[Dict]:
        """Get all turns for a specific call."""
        try:
            conn = self._get_conn()
            if not conn:
                return []
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM turns WHERE call_sid = ? ORDER BY turn_number",
                (call_sid,)).fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"[CAPTURE] Query failed: {e}")
            return []

    def get_recent_calls(self, limit: int = 20) -> List[Dict]:
        """Get most recent calls."""
        try:
            conn = self._get_conn()
            if not conn:
                return []
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM calls ORDER BY start_time DESC LIMIT ?",
                (limit,)).fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"[CAPTURE] Query failed: {e}")
            return []

    def get_stats(self) -> Dict:
        """Get aggregate capture statistics."""
        try:
            conn = self._get_conn()
            if not conn:
                return {}
            cur = conn.cursor()
            total_calls = cur.execute("SELECT COUNT(*) FROM calls").fetchone()[0]
            total_turns = cur.execute("SELECT COUNT(*) FROM turns").fetchone()[0]
            total_errors = cur.execute("SELECT COUNT(*) FROM call_errors").fetchone()[0]
            avg_duration = cur.execute(
                "SELECT AVG(duration_seconds) FROM calls WHERE duration_seconds IS NOT NULL"
            ).fetchone()[0]
            conn.close()
            return {
                "total_calls_captured": total_calls,
                "total_turns_captured": total_turns,
                "total_errors_captured": total_errors,
                "avg_call_duration_seconds": round(avg_duration or 0, 1),
                "active_calls_tracking": len(self._active_calls),
                "db_path": self._db_path,
            }
        except Exception as e:
            logger.error(f"[CAPTURE] Stats query failed: {e}")
            return {"error": str(e)}

    # -------------------------------------------------------------------------
    # PRIVATE — Database write operations (always run in background thread)
    # -------------------------------------------------------------------------

    def _write_call_start(self, call_data: Dict):
        """Insert new call record."""
        conn = self._get_conn()
        if not conn:
            return
        try:
            conn.execute("""
                INSERT OR IGNORE INTO calls
                    (call_sid, session_id, merchant_phone, merchant_name,
                     business_name, start_time)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                call_data["call_sid"],
                call_data.get("session_id", ""),
                call_data.get("merchant_phone", ""),
                call_data.get("merchant_name", ""),
                call_data.get("business_name", ""),
                call_data["start_time"],
            ))
            conn.commit()
            logger.info(f"[CAPTURE] Call start recorded: {call_data['call_sid'][:16]}...")
        except Exception as e:
            logger.error(f"[CAPTURE] Failed to write call start: {e}")
        finally:
            conn.close()

    def _write_greeting(self, call_sid: str, greeting_text: str):
        """Update call record with greeting text."""
        conn = self._get_conn()
        if not conn:
            return
        try:
            conn.execute("UPDATE calls SET greeting_text = ? WHERE call_sid = ?",
                         (greeting_text, call_sid))
            conn.commit()
        except Exception as e:
            logger.error(f"[CAPTURE] Failed to write greeting: {e}")
        finally:
            conn.close()

    def _write_turn(self, turn_data: Dict):
        """Insert a turn record."""
        conn = self._get_conn()
        if not conn:
            return
        try:
            user_text = turn_data.get("user_text", "")
            alan_text = turn_data.get("alan_text", "")
            conn.execute("""
                INSERT INTO turns (
                    call_sid, turn_number, timestamp,
                    user_text, alan_text,
                    user_word_count, alan_word_count,
                    sentiment, interest_level, caller_energy,
                    live_objection_type,
                    preprocess_ms, llm_ms, tts_ms, total_turn_ms,
                    deep_layer_mode, deep_layer_strategy, deep_layer_blend,
                    trajectory, temperature, confidence_score,
                    endgame_state, merchant_type, trajectory_switches,
                    agent_x_off_topic, agent_x_category, agent_x_mode,
                    predicted_intent, predicted_objection, prediction_confidence,
                    behavior_tone, behavior_closing_bias,
                    reasoning_block,
                    coaching_score, coaching_flags
                ) VALUES (
                    ?, ?, ?,
                    ?, ?,
                    ?, ?,
                    ?, ?, ?,
                    ?,
                    ?, ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?,
                    ?, ?,
                    ?,
                    ?, ?
                )
            """, (
                turn_data.get("call_sid", ""),
                turn_data.get("turn_number", 0),
                turn_data.get("timestamp", datetime.now().isoformat()),
                user_text,
                alan_text,
                len(user_text.split()) if user_text else 0,
                len(alan_text.split()) if alan_text else 0,
                turn_data.get("sentiment", "neutral"),
                turn_data.get("interest_level", "unknown"),
                turn_data.get("caller_energy", "neutral"),
                turn_data.get("live_objection_type"),
                turn_data.get("preprocess_ms"),
                turn_data.get("llm_ms"),
                turn_data.get("tts_ms"),
                turn_data.get("total_turn_ms"),
                turn_data.get("deep_layer_mode"),
                turn_data.get("deep_layer_strategy"),
                turn_data.get("deep_layer_blend"),
                turn_data.get("trajectory"),
                turn_data.get("temperature"),
                turn_data.get("confidence_score"),
                turn_data.get("endgame_state"),
                turn_data.get("merchant_type"),
                turn_data.get("trajectory_switches", 0),
                1 if turn_data.get("agent_x_off_topic") else 0,
                turn_data.get("agent_x_category"),
                turn_data.get("agent_x_mode"),
                turn_data.get("predicted_intent"),
                turn_data.get("predicted_objection"),
                turn_data.get("prediction_confidence"),
                turn_data.get("behavior_tone"),
                turn_data.get("behavior_closing_bias"),
                turn_data.get("reasoning_block"),
                turn_data.get("coaching_score"),
                turn_data.get("coaching_flags"),
            ))
            conn.commit()
            
            # Also update running totals on the calls table
            conn.execute("""
                UPDATE calls SET
                    total_turns = total_turns + 1,
                    merchant_words = merchant_words + ?,
                    alan_words = alan_words + ?
                WHERE call_sid = ?
            """, (
                len(user_text.split()) if user_text else 0,
                len(alan_text.split()) if alan_text else 0,
                turn_data.get("call_sid", ""),
            ))
            conn.commit()
        except Exception as e:
            logger.error(f"[CAPTURE] Failed to write turn: {e}")
        finally:
            conn.close()

    def _write_error(self, call_sid: str, error_type: str, error_message: str):
        """Insert error record and increment error count."""
        conn = self._get_conn()
        if not conn:
            return
        try:
            conn.execute("""
                INSERT INTO call_errors (call_sid, timestamp, error_type, error_message)
                VALUES (?, ?, ?, ?)
            """, (call_sid, datetime.now().isoformat(), error_type, error_message))
            conn.execute("""
                UPDATE calls SET error_count = error_count + 1 WHERE call_sid = ?
            """, (call_sid,))
            conn.commit()
        except Exception as e:
            logger.error(f"[CAPTURE] Failed to write error: {e}")
        finally:
            conn.close()

    def _write_call_end(self, end_data: Dict):
        """Update call record with final state."""
        conn = self._get_conn()
        if not conn:
            return
        try:
            call_sid = end_data.get("call_sid", "")
            # Serialize classifier JSON fields
            _ct_raw = end_data.get('call_type_raw_scores')
            _ct_prob = end_data.get('call_type_probabilities')
            _ct_flags = end_data.get('call_type_override_flags')
            if isinstance(_ct_raw, dict):
                _ct_raw = json.dumps(_ct_raw)
            if isinstance(_ct_prob, dict):
                _ct_prob = json.dumps(_ct_prob)
            if isinstance(_ct_flags, (list, tuple)):
                _ct_flags = json.dumps(_ct_flags)
            conn.execute("""
                UPDATE calls SET
                    end_time = ?,
                    duration_seconds = ?,
                    total_turns = ?,
                    final_outcome = ?,
                    outcome_confidence = ?,
                    outcome_band = ?,
                    engagement_score = ?,
                    final_trajectory = ?,
                    final_temperature = ?,
                    final_confidence_score = ?,
                    final_endgame = ?,
                    final_merchant_type = ?,
                    signature_speed_bias = ?,
                    signature_silence_bias = ?,
                    signature_breath_bias = ?,
                    signature_caller_influence = ?,
                    evolution_nudge = ?,
                    attribution_dimensions = ?,
                    deep_layer_final_mode = ?,
                    deep_layer_final_strategy = ?,
                    call_type = ?,
                    call_type_confidence = ?,
                    call_type_raw_scores = ?,
                    call_type_probabilities = ?,
                    call_type_override_flags = ?,
                    call_type_reasoning = ?,
                    killed_by = ?,
                    voice_avg_drift = ?,
                    voice_max_drift = ?,
                    voice_integrity = ?,
                    inbound_metrics = ?,
                    perception_vector = ?,
                    behavioral_vector = ?,
                    coaching_tags = ?,
                    zero_turn_class = ?,
                    dnc_flag = ?,
                    there_spam_flag = ?,
                    unfit_context = ?
                WHERE call_sid = ?
            """, (
                end_data.get("end_time"),
                end_data.get("duration_seconds"),
                end_data.get("total_turns"),
                end_data.get("final_outcome", "unknown"),
                end_data.get("outcome_confidence", 0.0),
                end_data.get("outcome_band", "unknown"),
                end_data.get("engagement_score", 0.0),
                end_data.get("final_trajectory", "neutral"),
                end_data.get("final_temperature", 50),
                end_data.get("final_confidence_score", 50),
                end_data.get("final_endgame", "not_ready"),
                end_data.get("final_merchant_type", "unknown"),
                end_data.get("signature_speed_bias"),
                end_data.get("signature_silence_bias"),
                end_data.get("signature_breath_bias"),
                end_data.get("signature_caller_influence"),
                end_data.get("evolution_nudge"),
                end_data.get("attribution_dimensions"),
                end_data.get("deep_layer_final_mode"),
                end_data.get("deep_layer_final_strategy"),
                end_data.get("call_type"),
                end_data.get("call_type_confidence"),
                _ct_raw,
                _ct_prob,
                _ct_flags,
                end_data.get("call_type_reasoning"),
                end_data.get("killed_by"),
                end_data.get("voice_avg_drift"),
                end_data.get("voice_max_drift"),
                end_data.get("voice_integrity"),
                json.dumps(end_data.get("inbound_metrics")) if isinstance(end_data.get("inbound_metrics"), dict) else end_data.get("inbound_metrics"),
                json.dumps(end_data.get("perception_vector")) if isinstance(end_data.get("perception_vector"), dict) else end_data.get("perception_vector"),
                json.dumps(end_data.get("behavioral_vector")) if isinstance(end_data.get("behavioral_vector"), dict) else end_data.get("behavioral_vector"),
                json.dumps(end_data.get("coaching_tags", [])),
                end_data.get("zero_turn_class"),
                int(end_data.get("dnc_flag", 0) or 0),
                int(end_data.get("there_spam_flag", 0) or 0),
                end_data.get("unfit_context"),
                call_sid,
            ))
            conn.commit()
            logger.info(f"[CAPTURE] Call end recorded: {call_sid[:16]}... "
                        f"({end_data.get('duration_seconds', 0):.1f}s, "
                        f"{end_data.get('total_turns', 0)} turns, "
                        f"outcome={end_data.get('final_outcome', '?')})")
        except Exception as e:
            logger.error(f"[CAPTURE] Failed to write call end: {e}")
        finally:
            conn.close()

    def _write_evolution_event(self, call_sid: str, outcome: str,
                                confidence: float, band: str,
                                engagement_score: float,
                                nudge: str, attribution: str):
        """Insert evolution event record."""
        conn = self._get_conn()
        if not conn:
            return
        try:
            conn.execute("""
                INSERT INTO evolution_events
                    (call_sid, timestamp, outcome, confidence, band,
                     engagement_score, nudge_applied, attribution)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (call_sid, datetime.now().isoformat(), outcome, confidence,
                  band, engagement_score, nudge, attribution))
            conn.commit()
        except Exception as e:
            logger.error(f"[CAPTURE] Failed to write evolution event: {e}")
        finally:
            conn.close()

    def _write_coaching(self, call_sid: str, score: float,
                         strengths: str, weaknesses: str, action_item: str):
        """Update call record with coaching results."""
        conn = self._get_conn()
        if not conn:
            return
        try:
            conn.execute("""
                UPDATE calls SET
                    coaching_score = ?,
                    coaching_strengths = ?,
                    coaching_weaknesses = ?,
                    coaching_action_item = ?
                WHERE call_sid = ?
            """, (score, strengths, weaknesses, action_item, call_sid))
            conn.commit()
        except Exception as e:
            logger.error(f"[CAPTURE] Failed to write coaching: {e}")
        finally:
            conn.close()

    def _write_json_transcript(self, call_sid: str):
        """
        Write a comprehensive JSON transcript file.
        Compatible with existing logs/call_transcripts/ format but enriched.
        """
        conn = self._get_conn()
        if not conn:
            return
        try:
            conn.row_factory = sqlite3.Row
            
            # Get call summary
            call_row = conn.execute(
                "SELECT * FROM calls WHERE call_sid = ?", (call_sid,)
            ).fetchone()
            if not call_row:
                conn.close()
                return
            
            # Get all turns
            turn_rows = conn.execute(
                "SELECT * FROM turns WHERE call_sid = ? ORDER BY turn_number",
                (call_sid,)
            ).fetchall()
            
            # Get errors
            error_rows = conn.execute(
                "SELECT * FROM call_errors WHERE call_sid = ?", (call_sid,)
            ).fetchall()
            
            conn.close()
            
            # Build transcript JSON
            call = dict(call_row)
            transcript_data = {
                "call_sid": call_sid,
                "captured_by": "CallDataCaptureEngine v1.0",
                "capture_date": datetime.now().isoformat(),
                "summary": {
                    "duration_seconds": call.get("duration_seconds", 0),
                    "total_turns": call.get("total_turns", 0),
                    "merchant_words": call.get("merchant_words", 0),
                    "alan_words": call.get("alan_words", 0),
                    "outcome": call.get("final_outcome", "unknown"),
                    "outcome_confidence": call.get("outcome_confidence", 0),
                    "outcome_band": call.get("outcome_band", "unknown"),
                    "engagement_score": call.get("engagement_score", 0),
                    "trajectory": call.get("final_trajectory", "neutral"),
                    "merchant_type": call.get("final_merchant_type", "unknown"),
                    "error_count": call.get("error_count", 0),
                },
                "merchant": {
                    "phone": call.get("merchant_phone", ""),
                    "name": call.get("merchant_name", ""),
                    "business": call.get("business_name", ""),
                },
                "greeting": call.get("greeting_text", ""),
                "transcript": [],
                "turn_analytics": [],
                "errors": [dict(r) for r in error_rows],
                "evolution": {
                    "nudge": call.get("evolution_nudge"),
                    "attribution": call.get("attribution_dimensions"),
                },
                "coaching": {
                    "score": call.get("coaching_score"),
                    "strengths": call.get("coaching_strengths"),
                    "weaknesses": call.get("coaching_weaknesses"),
                    "action_item": call.get("coaching_action_item"),
                },
                "signature": {
                    "speed_bias": call.get("signature_speed_bias"),
                    "silence_bias": call.get("signature_silence_bias"),
                    "breath_bias": call.get("signature_breath_bias"),
                    "caller_influence": call.get("signature_caller_influence"),
                },
            }
            
            for turn in turn_rows:
                t = dict(turn)
                # Simple transcript entry (compatible with existing format)
                if t.get("user_text"):
                    transcript_data["transcript"].append({
                        "timestamp": t["timestamp"],
                        "speaker": "merchant",
                        "text": t["user_text"],
                        "sentiment": t.get("sentiment", "neutral"),
                        "word_count": t.get("user_word_count", 0),
                    })
                if t.get("alan_text"):
                    transcript_data["transcript"].append({
                        "timestamp": t["timestamp"],
                        "speaker": "alan",
                        "text": t["alan_text"],
                        "sentiment": "neutral",
                        "word_count": t.get("alan_word_count", 0),
                        "response_time_ms": t.get("total_turn_ms", 0),
                    })
                
                # Rich analytics per turn
                transcript_data["turn_analytics"].append({
                    "turn": t.get("turn_number", 0),
                    "timing": {
                        "preprocess_ms": t.get("preprocess_ms"),
                        "llm_ms": t.get("llm_ms"),
                        "tts_ms": t.get("tts_ms"),
                        "total_ms": t.get("total_turn_ms"),
                    },
                    "deep_layer": {
                        "mode": t.get("deep_layer_mode"),
                        "strategy": t.get("deep_layer_strategy"),
                        "blend": t.get("deep_layer_blend"),
                    },
                    "closer": {
                        "trajectory": t.get("trajectory"),
                        "temperature": t.get("temperature"),
                        "confidence": t.get("confidence_score"),
                        "endgame": t.get("endgame_state"),
                        "type": t.get("merchant_type"),
                    },
                    "agent_x": {
                        "off_topic": bool(t.get("agent_x_off_topic")),
                        "category": t.get("agent_x_category"),
                        "mode": t.get("agent_x_mode"),
                    },
                    "predictive": {
                        "intent": t.get("predicted_intent"),
                        "objection": t.get("predicted_objection"),
                        "confidence": t.get("prediction_confidence"),
                    },
                    "energy": t.get("caller_energy"),
                    "objection": t.get("live_objection_type"),
                })
            
            # Write JSON file
            transcript_dir = Path(os.path.dirname(os.path.abspath(__file__))) / "logs" / "call_transcripts"
            transcript_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = transcript_dir / f"transcript_{call_sid}_{timestamp_str}.json"
            
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(transcript_data, f, indent=2, default=str)
            
            logger.info(f"[CAPTURE] Enriched transcript saved: {filename.name}")
            
        except Exception as e:
            logger.error(f"[CAPTURE] Failed to write JSON transcript: {e}")


# =============================================================================
# SINGLETON — Global capture engine instance
# =============================================================================

_capture_engine: Optional[CallDataCaptureEngine] = None
_capture_lock = threading.Lock()


def get_capture_engine() -> CallDataCaptureEngine:
    """Get or create the global capture engine singleton."""
    global _capture_engine
    if _capture_engine is None:
        with _capture_lock:
            if _capture_engine is None:
                _capture_engine = CallDataCaptureEngine()
    return _capture_engine


# =============================================================================
# CONVENIENCE FUNCTIONS — Direct fire-and-forget API for the relay server
# =============================================================================

def capture_call_start(call_sid: str, session_id: str,
                       merchant_phone: str = "", merchant_name: str = "",
                       business_name: str = ""):
    """Fire-and-forget: Record call start."""
    try:
        get_capture_engine().capture_call_start(
            call_sid, session_id, merchant_phone, merchant_name, business_name)
    except Exception as _cdc_err:
        logger.debug(f"[CDC] capture_call_start failed for {call_sid}: {_cdc_err}")

def capture_greeting(call_sid: str, greeting_text: str):
    """Fire-and-forget: Record greeting."""
    try:
        get_capture_engine().capture_greeting(call_sid, greeting_text)
    except Exception as _cdc_err:
        logger.debug(f"[CDC] capture_greeting failed for {call_sid}: {_cdc_err}")

def capture_turn(call_sid: str, turn_data: Dict[str, Any]):
    """Fire-and-forget: Record a conversational turn with full analytics."""
    try:
        get_capture_engine().capture_turn(call_sid, turn_data)
    except Exception as _cdc_err:
        logger.debug(f"[CDC] capture_turn failed for {call_sid}: {_cdc_err}")

def capture_error(call_sid: str, error_type: str, error_message: str):
    """Fire-and-forget: Record an error."""
    try:
        get_capture_engine().capture_error(call_sid, error_type, error_message)
    except Exception as _cdc_err:
        logger.debug(f"[CDC] capture_error failed for {call_sid}: {_cdc_err}")

def capture_call_end(call_sid: str, end_data: Dict[str, Any] = None):
    """Fire-and-forget: Record call end with final state."""
    try:
        get_capture_engine().capture_call_end(call_sid, end_data)
    except Exception as _cdc_err:
        logger.debug(f"[CDC] capture_call_end failed for {call_sid}: {_cdc_err}")

def capture_evolution(call_sid: str, outcome: str, confidence: float,
                      band: str, engagement_score: float,
                      nudge: str = "", attribution: str = ""):
    """Fire-and-forget: Record evolution engine event."""
    try:
        get_capture_engine().capture_evolution_event(
            call_sid, outcome, confidence, band, engagement_score, nudge, attribution)
    except Exception as _cdc_err:
        logger.debug(f"[CDC] capture_evolution failed for {call_sid}: {_cdc_err}")

def capture_coaching(call_sid: str, score: float,
                     strengths: str, weaknesses: str, action_item: str):
    """Fire-and-forget: Record coaching results."""
    try:
        get_capture_engine().capture_coaching(
            call_sid, score, strengths, weaknesses, action_item)
    except Exception as _cdc_err:
        logger.debug(f"[CDC] capture_coaching failed for {call_sid}: {_cdc_err}")

def capture_environment(call_sid: str, env_class: str, env_confidence: float,
                        behavior: str, outcome: str = '', utterance: str = '',
                        cycles: int = 0):
    """Fire-and-forget: Record EAB environment classification event."""
    try:
        get_capture_engine().capture_environment(
            call_sid, env_class, env_confidence, behavior, outcome, utterance, cycles)
    except Exception as _cdc_err:
        logger.debug(f"[CDC] capture_environment failed for {call_sid}: {_cdc_err}")
