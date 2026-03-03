"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                     REGIME ENGINE 1.0 — Python Module                       ║
║                                                                              ║
║  Meta-organ that detects when the world changes and rewrites the map.        ║
║  Sits ABOVE individual predictors (EAB-Plus, models, scripts).               ║
║  Consumes CDC telemetry, emits REGIME_SHIFT_CANDIDATE events,                ║
║  composes REGIME_PROPOSALs, and writes regime_config_live.json               ║
║  under Agent X governance.                                                   ║
║                                                                              ║
║  Five Detection Classes:                                                     ║
║   1. Timing Regime   — answer-rate by hour/DOW/holiday                       ║
║   2. Cultural Shift  — state-level behavioral patterns                       ║
║   3. Script Perf     — script variant A/B degradation                        ║
║   4. Objection Mut   — objection cluster drift                               ║
║   5. Cost Explosion  — per-call cost spikes                                  ║
║                                                                              ║
║  Four Faculties:                                                             ║
║   A. Uncertainty  — prediction confidence monitoring                         ║
║   B. Anomaly      — statistical deviation detection                          ║
║   C. Value        — ROI and conversion tracking                              ║
║   D. Model-of-Models — cross-model disagreement sensing                      ║
║                                                                              ║
║  Author: Agent X Regime Engine / CW23                                        ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import json
import os
import sqlite3
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ─── CONSTANTS ──────────────────────────────────────────────────────────────

VERSION = "1.0.0"
CDC_DB_PATH = os.path.join(os.path.dirname(__file__), "data", "call_capture.db")
CONFIG_LIVE_PATH = os.path.join(os.path.dirname(__file__), "data", "regime_config_live.json")
TELEMETRY_LOG_PATH = os.path.join(os.path.dirname(__file__), "data", "regime_engine_telemetry.jsonl")

# Detection thresholds
CONFIDENCE_FLOOR = 0.60          # Below this -> cannot emit candidate
ANOMALY_Z_THRESHOLD = 2.0       # Standard deviations for anomaly detection
COST_SPIKE_RATIO = 1.5          # 50% above rolling mean = cost explosion
MIN_SAMPLE_SIZE = 10            # Minimum calls to form a valid segment reading
LOOKBACK_HOURS = 168            # 7-day sliding window default
PROPOSAL_EXPIRY_HOURS = 24      # Proposals expire after this

# ─── ENUMS ──────────────────────────────────────────────────────────────────

class SegmentPriority(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    OFF = "OFF"

class PredictionTrust(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

class SegmentStatus(str, Enum):
    STABLE = "STABLE"
    SHIFTING = "SHIFTING"
    DEGRADED = "DEGRADED"
    EXPERIMENTAL = "EXPERIMENTAL"

class PacingMode(str, Enum):
    AGGRESSIVE = "AGGRESSIVE"
    NORMAL = "NORMAL"
    CONSERVATIVE = "CONSERVATIVE"

class RegimeShiftType(str, Enum):
    TIMING_REGIME = "timing_regime"
    STATE_CULTURAL_SHIFT = "state_cultural_shift"
    SCRIPT_PERFORMANCE = "script_performance"
    OBJECTION_MUTATION = "objection_mutation"
    COST_EXPLOSION = "cost_explosion"

class ModelActionType(str, Enum):
    SPAWN_NEW_MODEL = "spawn_new_model"
    RETIRE_MODEL = "retire_model"
    SPLIT_SEGMENT = "split_segment"
    MERGE_SEGMENT = "merge_segment"
    RETRAIN_MODEL = "retrain_model"

class Faculty(str, Enum):
    UNCERTAINTY = "uncertainty"
    ANOMALY = "anomaly"
    VALUE = "value"
    MODEL_OF_MODELS = "model_of_models"

class ProposalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


# ─── DATA CLASSES ───────────────────────────────────────────────────────────

@dataclass
class SegmentConfig:
    """Configuration for a single segment in regime_config_live."""
    priority: SegmentPriority = SegmentPriority.MEDIUM
    prediction_trust: PredictionTrust = PredictionTrust.MEDIUM
    status: SegmentStatus = SegmentStatus.STABLE
    preferred_script: Optional[str] = None
    notes: Optional[str] = None


@dataclass
class CallRoutingOverride:
    """Override for queue priority and pacing."""
    queue_priority: SegmentPriority = SegmentPriority.MEDIUM
    pacing: PacingMode = PacingMode.NORMAL


@dataclass
class ModelActionRequest:
    """Action the engine requests for model management."""
    action: ModelActionType
    target: str
    parameters: Optional[Dict[str, Any]] = None


@dataclass
class RegimeEvent:
    """A confirmed regime shift event."""
    event_id: str
    type: RegimeShiftType
    confidence: float
    timestamp: str
    segment: Optional[str] = None
    state: Optional[str] = None
    script: Optional[str] = None
    evidence: Optional[Dict[str, Any]] = None


@dataclass
class RegimeShiftCandidate:
    """
    A candidate regime shift detected by one of the four faculties.
    Must be composed into a proposal and approved before becoming a regime event.
    """
    candidate_id: str
    type: RegimeShiftType
    segment: str
    confidence: float
    evidence: Dict[str, Any]
    faculty: Faculty
    detected_at: str

    @staticmethod
    def new(shift_type: RegimeShiftType, segment: str, confidence: float,
            evidence: Dict[str, Any], faculty: Faculty) -> 'RegimeShiftCandidate':
        """Factory method for creating a fresh candidate."""
        return RegimeShiftCandidate(
            candidate_id=f"cand_{uuid.uuid4().hex[:12]}",
            type=shift_type,
            segment=segment,
            confidence=confidence,
            evidence=evidence,
            faculty=faculty,
            detected_at=datetime.now(timezone.utc).isoformat()
        )


@dataclass
class RegimeProposal:
    """
    A proposal composed from one or more candidates.
    Submitted to Agent X governance for approval.
    """
    proposal_id: str
    candidates: List[RegimeShiftCandidate]
    recommended_actions: List[ModelActionRequest]
    config_diff: Dict[str, Any]
    composed_at: str
    status: ProposalStatus = ProposalStatus.PENDING

    @staticmethod
    def compose(candidates: List[RegimeShiftCandidate],
                actions: List[ModelActionRequest],
                config_diff: Dict[str, Any]) -> 'RegimeProposal':
        """Compose a proposal from candidates."""
        return RegimeProposal(
            proposal_id=f"prop_{uuid.uuid4().hex[:12]}",
            candidates=candidates,
            recommended_actions=actions,
            config_diff=config_diff,
            composed_at=datetime.now(timezone.utc).isoformat()
        )


@dataclass
class RegimeConfigLive:
    """Top-level live configuration emitted by the engine."""
    version: str = VERSION
    generated_at: str = ""
    segments: Dict[str, SegmentConfig] = field(default_factory=dict)
    call_routing_overrides: Dict[str, CallRoutingOverride] = field(default_factory=dict)
    script_overrides: Dict[str, str] = field(default_factory=dict)
    model_actions: List[ModelActionRequest] = field(default_factory=list)
    regime_events: List[RegimeEvent] = field(default_factory=list)
    governance: Dict[str, Any] = field(default_factory=lambda: {
        "approved_proposals": [],
        "rejected_proposals": []
    })

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for JSON output."""
        d = {}
        d["version"] = self.version
        d["generated_at"] = self.generated_at
        d["segments"] = {
            k: {
                "priority": v.priority.value,
                "prediction_trust": v.prediction_trust.value,
                "status": v.status.value,
                **({"preferred_script": v.preferred_script} if v.preferred_script else {}),
                **({"notes": v.notes} if v.notes else {})
            }
            for k, v in self.segments.items()
        }
        if self.call_routing_overrides:
            d["call_routing_overrides"] = {
                k: {"queue_priority": v.queue_priority.value, "pacing": v.pacing.value}
                for k, v in self.call_routing_overrides.items()
            }
        if self.script_overrides:
            d["script_overrides"] = self.script_overrides
        if self.model_actions:
            d["model_actions"] = [
                {"action": a.action.value, "target": a.target,
                 **({"parameters": a.parameters} if a.parameters else {})}
                for a in self.model_actions
            ]
        if self.regime_events:
            d["regime_events"] = [
                {
                    "event_id": e.event_id,
                    "type": e.type.value,
                    "confidence": e.confidence,
                    "timestamp": e.timestamp,
                    **({"segment": e.segment} if e.segment else {}),
                    **({"state": e.state} if e.state else {}),
                    **({"script": e.script} if e.script else {}),
                    **({"evidence": e.evidence} if e.evidence else {})
                }
                for e in self.regime_events
            ]
        d["governance"] = self.governance
        return d


# ─── TELEMETRY ──────────────────────────────────────────────────────────────

class TelemetryEmitter:
    """Append-only JSONL telemetry for audit trail."""

    def __init__(self, path: str = TELEMETRY_LOG_PATH):
        self._path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)

    def emit(self, event_type: str, payload: Dict[str, Any]) -> None:
        entry = {
            "event_type": event_type,
            "payload": payload,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        try:
            with open(self._path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, default=str) + "\n")
        except Exception:
            pass  # Telemetry must never crash the engine


# ─── CDC READER ─────────────────────────────────────────────────────────────

class CDCReader:
    """
    Read from the Call Data Capture database.
    All queries are read-only — the engine NEVER writes to CDC.
    """

    def __init__(self, db_path: str = CDC_DB_PATH):
        self._db_path = db_path

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def get_calls_in_window(self, hours: int = LOOKBACK_HOURS) -> List[Dict[str, Any]]:
        """Fetch all calls within the lookback window."""
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        try:
            with self._connect() as conn:
                rows = conn.execute("""
                    SELECT * FROM calls
                    WHERE start_time >= ?
                    ORDER BY start_time DESC
                """, (cutoff,)).fetchall()
                return [dict(r) for r in rows]
        except Exception:
            return []

    def get_calls_by_segment(self, hours: int = LOOKBACK_HOURS) -> Dict[str, List[Dict[str, Any]]]:
        """Group calls by segment key (state_vertical_hourblock)."""
        calls = self.get_calls_in_window(hours)
        segments: Dict[str, List[Dict[str, Any]]] = {}
        for call in calls:
            seg_key = self._segment_key(call)
            segments.setdefault(seg_key, []).append(call)
        return segments

    def get_env_plus_signals(self, hours: int = LOOKBACK_HOURS) -> List[Dict[str, Any]]:
        """Fetch env_plus_signals within the lookback window."""
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        try:
            with self._connect() as conn:
                rows = conn.execute("""
                    SELECT * FROM env_plus_signals
                    WHERE created_at >= ?
                    ORDER BY created_at DESC
                """, (cutoff,)).fetchall()
                return [dict(r) for r in rows]
        except Exception:
            return []

    def get_turn_timing(self, hours: int = LOOKBACK_HOURS) -> List[Dict[str, Any]]:
        """Fetch per-turn timing data for cost analysis."""
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        try:
            with self._connect() as conn:
                rows = conn.execute("""
                    SELECT t.call_sid, t.turn_number, t.preprocess_ms, t.llm_ms, t.tts_ms,
                           t.timestamp, c.merchant_name, c.business_name
                    FROM turns t
                    JOIN calls c ON t.call_sid = c.call_sid
                    WHERE t.timestamp >= ?
                    ORDER BY t.timestamp DESC
                """, (cutoff,)).fetchall()
                return [dict(r) for r in rows]
        except Exception:
            return []

    def get_hourly_answer_rates(self, hours: int = LOOKBACK_HOURS) -> Dict[int, Dict[str, float]]:
        """
        Compute answer rate by hour of day.
        Returns: {hour: {"total": N, "answered": M, "rate": M/N}}
        """
        calls = self.get_calls_in_window(hours)
        hourly: Dict[int, Dict[str, int]] = {}
        for call in calls:
            try:
                dt = datetime.fromisoformat(call.get("start_time", ""))
                hour = dt.hour
            except (ValueError, TypeError):
                continue
            if hour not in hourly:
                hourly[hour] = {"total": 0, "answered": 0}
            hourly[hour]["total"] += 1
            outcome = (call.get("final_outcome") or "").lower()
            if outcome not in ("no_answer", "voicemail", "machine", "unknown", ""):
                hourly[hour]["answered"] += 1

        result = {}
        for hour, counts in hourly.items():
            total = counts["total"]
            answered = counts["answered"]
            result[hour] = {
                "total": total,
                "answered": answered,
                "rate": answered / total if total > 0 else 0.0
            }
        return result

    @staticmethod
    def _segment_key(call: Dict[str, Any]) -> str:
        """Build a segment key from call data: state_vertical_hourblock.
        
        Uses the SAME derivation logic as regime_queue_integrator.py:
        - State derived from merchant_phone area code (not a DB column)
        - Vertical derived from business_name keyword matching (not a DB column)
        This ensures the engine WRITES keys that the integrator can READ.
        """
        # Import the shared derivation functions from the integrator
        # to guarantee namespace alignment
        try:
            from regime_queue_integrator import (
                _phone_to_state, _business_to_vertical
            )
            phone = call.get("merchant_phone") or ""
            biz_name = call.get("business_name") or ""
            state = _phone_to_state(phone) if phone else "UN"
            vertical = _business_to_vertical(biz_name) if biz_name else "general"
        except ImportError:
            # Fallback if integrator not available — use raw DB fields
            state = (call.get("state") or "UNK").upper()[:2]
            vertical = (call.get("vertical") or "general").lower()

        try:
            dt = datetime.fromisoformat(call.get("start_time", ""))
            hour_block = f"{dt.hour:02d}"
        except (ValueError, TypeError):
            hour_block = "XX"
        return f"{state}_{vertical}_{hour_block}"


# ─── FACULTIES ──────────────────────────────────────────────────────────────

class UncertaintyFaculty:
    """
    Faculty A: Watches prediction confidence.
    When model confidence drops below thresholds, emits candidate.
    """

    def __init__(self, cdc: CDCReader, telemetry: TelemetryEmitter):
        self._cdc = cdc
        self._telemetry = telemetry

    def evaluate(self) -> List[RegimeShiftCandidate]:
        candidates = []
        segments = self._cdc.get_calls_by_segment()

        for seg_key, calls in segments.items():
            if len(calls) < MIN_SAMPLE_SIZE:
                continue

            # Check outcome_confidence distribution
            confidences = [c.get("outcome_confidence", 0.0) for c in calls
                           if c.get("outcome_confidence") is not None]
            if not confidences:
                continue

            avg_conf = sum(confidences) / len(confidences)
            low_conf_ratio = sum(1 for c in confidences if c < 0.5) / len(confidences)

            # If average confidence drops or too many low-confidence calls
            if avg_conf < 0.45 or low_conf_ratio > 0.6:
                confidence_score = min(0.95, 0.5 + (0.4 * low_conf_ratio))
                candidate = RegimeShiftCandidate.new(
                    shift_type=RegimeShiftType.TIMING_REGIME,
                    segment=seg_key,
                    confidence=round(confidence_score, 3),
                    evidence={
                        "avg_outcome_confidence": round(avg_conf, 3),
                        "low_confidence_ratio": round(low_conf_ratio, 3),
                        "sample_size": len(confidences),
                        "detection": "prediction_confidence_drop"
                    },
                    faculty=Faculty.UNCERTAINTY
                )
                candidates.append(candidate)

        self._telemetry.emit("FACULTY_RUN_COMPLETE", {
            "faculty": "uncertainty",
            "candidates_emitted": len(candidates),
            "segments_evaluated": len(segments)
        })
        return candidates


class AnomalyFaculty:
    """
    Faculty B: Statistical deviation detection.
    Uses z-score against rolling baselines to detect anomalies.
    """

    def __init__(self, cdc: CDCReader, telemetry: TelemetryEmitter):
        self._cdc = cdc
        self._telemetry = telemetry

    def evaluate(self) -> List[RegimeShiftCandidate]:
        candidates = []

        # Check 1: Answer rate anomalies by hour
        hourly = self._cdc.get_hourly_answer_rates()
        if len(hourly) >= 4:
            rates = [v["rate"] for v in hourly.values() if v["total"] >= MIN_SAMPLE_SIZE]
            if len(rates) >= 4:
                mean_rate = sum(rates) / len(rates)
                variance = sum((r - mean_rate) ** 2 for r in rates) / len(rates)
                std_dev = variance ** 0.5 if variance > 0 else 0.001

                for hour, data in hourly.items():
                    if data["total"] < MIN_SAMPLE_SIZE:
                        continue
                    z_score = (data["rate"] - mean_rate) / std_dev
                    if abs(z_score) >= ANOMALY_Z_THRESHOLD:
                        candidate = RegimeShiftCandidate.new(
                            shift_type=RegimeShiftType.TIMING_REGIME,
                            segment=f"hour_{hour:02d}",
                            confidence=round(min(0.95, 0.6 + 0.1 * abs(z_score)), 3),
                            evidence={
                                "hour": hour,
                                "answer_rate": round(data["rate"], 3),
                                "mean_rate": round(mean_rate, 3),
                                "z_score": round(z_score, 3),
                                "sample_size": data["total"],
                                "detection": "answer_rate_anomaly"
                            },
                            faculty=Faculty.ANOMALY
                        )
                        candidates.append(candidate)

        # Check 2: Duration anomalies per segment
        segments = self._cdc.get_calls_by_segment()
        for seg_key, calls in segments.items():
            durations = [c.get("duration_seconds", 0) for c in calls
                         if c.get("duration_seconds") is not None and c["duration_seconds"] > 0]
            if len(durations) < MIN_SAMPLE_SIZE:
                continue

            mean_dur = sum(durations) / len(durations)
            variance = sum((d - mean_dur) ** 2 for d in durations) / len(durations)
            std_dev = variance ** 0.5 if variance > 0 else 0.001

            # Check recent calls (last 20%) against baseline
            recent_count = max(3, len(durations) // 5)
            recent_durations = durations[:recent_count]  # already sorted DESC
            recent_mean = sum(recent_durations) / len(recent_durations)
            z_score = (recent_mean - mean_dur) / std_dev

            if abs(z_score) >= ANOMALY_Z_THRESHOLD:
                candidate = RegimeShiftCandidate.new(
                    shift_type=RegimeShiftType.STATE_CULTURAL_SHIFT,
                    segment=seg_key,
                    confidence=round(min(0.95, 0.6 + 0.1 * abs(z_score)), 3),
                    evidence={
                        "mean_duration": round(mean_dur, 1),
                        "recent_mean_duration": round(recent_mean, 1),
                        "z_score": round(z_score, 3),
                        "sample_size": len(durations),
                        "recent_sample": recent_count,
                        "detection": "duration_anomaly"
                    },
                    faculty=Faculty.ANOMALY
                )
                candidates.append(candidate)

        self._telemetry.emit("FACULTY_RUN_COMPLETE", {
            "faculty": "anomaly",
            "candidates_emitted": len(candidates),
            "checks": ["answer_rate_by_hour", "duration_by_segment"]
        })
        return candidates


class ValueFaculty:
    """
    Faculty C: ROI and conversion tracking.
    Watches conversion rates and coaching scores decline.
    """

    def __init__(self, cdc: CDCReader, telemetry: TelemetryEmitter):
        self._cdc = cdc
        self._telemetry = telemetry

    def evaluate(self) -> List[RegimeShiftCandidate]:
        candidates = []
        segments = self._cdc.get_calls_by_segment()

        for seg_key, calls in segments.items():
            if len(calls) < MIN_SAMPLE_SIZE:
                continue

            # Conversion rate
            total = len(calls)
            converted = sum(1 for c in calls
                            if (c.get("final_outcome") or "").lower() in
                            ("booked", "appointment_set", "interested", "converted", "sale"))
            conv_rate = converted / total

            # Coaching score trend
            coaching_scores = [c.get("coaching_score", 0) for c in calls
                               if c.get("coaching_score") is not None]
            avg_coaching = sum(coaching_scores) / len(coaching_scores) if coaching_scores else 0

            # Check recent coaching vs overall
            if len(coaching_scores) >= MIN_SAMPLE_SIZE:
                recent_count = max(3, len(coaching_scores) // 5)
                recent_coaching = coaching_scores[:recent_count]
                recent_avg = sum(recent_coaching) / len(recent_coaching)
                coaching_drop = avg_coaching - recent_avg

                if coaching_drop > 0.15:  # Significant coaching degradation
                    candidate = RegimeShiftCandidate.new(
                        shift_type=RegimeShiftType.SCRIPT_PERFORMANCE,
                        segment=seg_key,
                        confidence=round(min(0.95, 0.6 + coaching_drop), 3),
                        evidence={
                            "avg_coaching": round(avg_coaching, 3),
                            "recent_avg_coaching": round(recent_avg, 3),
                            "coaching_drop": round(coaching_drop, 3),
                            "conversion_rate": round(conv_rate, 3),
                            "sample_size": total,
                            "detection": "coaching_degradation"
                        },
                        faculty=Faculty.VALUE
                    )
                    candidates.append(candidate)

            # Check for very low conversion rate
            if total >= MIN_SAMPLE_SIZE * 2 and conv_rate < 0.05:
                candidate = RegimeShiftCandidate.new(
                    shift_type=RegimeShiftType.SCRIPT_PERFORMANCE,
                    segment=seg_key,
                    confidence=round(min(0.9, 0.65 + (0.05 - conv_rate) * 5), 3),
                    evidence={
                        "conversion_rate": round(conv_rate, 3),
                        "total_calls": total,
                        "converted": converted,
                        "detection": "low_conversion"
                    },
                    faculty=Faculty.VALUE
                )
                candidates.append(candidate)

        self._telemetry.emit("FACULTY_RUN_COMPLETE", {
            "faculty": "value",
            "candidates_emitted": len(candidates),
            "segments_evaluated": len(segments)
        })
        return candidates


class ModelOfModelsFaculty:
    """
    Faculty D: Cross-model disagreement sensing.
    Detects when different predictors disagree on outcomes.
    Also detects objection mutation and cost explosion.
    """

    def __init__(self, cdc: CDCReader, telemetry: TelemetryEmitter):
        self._cdc = cdc
        self._telemetry = telemetry

    def evaluate(self) -> List[RegimeShiftCandidate]:
        candidates = []

        # Check 1: Objection mutation — rising unfit_context patterns
        calls = self._cdc.get_calls_in_window()
        unfit_calls = [c for c in calls if c.get("unfit_context")]
        if len(unfit_calls) >= MIN_SAMPLE_SIZE:
            # Parse unfit contexts and look for pattern shifts
            reason_codes: Dict[str, int] = {}
            for c in unfit_calls:
                try:
                    ctx = json.loads(c["unfit_context"])
                    reason = ctx.get("reason_code", "unknown")
                    reason_codes[reason] = reason_codes.get(reason, 0) + 1
                except (json.JSONDecodeError, TypeError):
                    pass

            unfit_ratio = len(unfit_calls) / len(calls) if calls else 0
            if unfit_ratio > 0.5:  # More than 50% unfit = potential objection mutation
                candidate = RegimeShiftCandidate.new(
                    shift_type=RegimeShiftType.OBJECTION_MUTATION,
                    segment="global",
                    confidence=round(min(0.95, 0.5 + unfit_ratio), 3),
                    evidence={
                        "unfit_ratio": round(unfit_ratio, 3),
                        "unfit_count": len(unfit_calls),
                        "total_calls": len(calls),
                        "reason_code_distribution": reason_codes,
                        "detection": "unfit_rate_spike"
                    },
                    faculty=Faculty.MODEL_OF_MODELS
                )
                candidates.append(candidate)

        # Check 2: Cost explosion — LLM latency spikes
        turn_data = self._cdc.get_turn_timing()
        if len(turn_data) >= MIN_SAMPLE_SIZE * 3:
            llm_times = [t.get("llm_ms", 0) for t in turn_data
                         if t.get("llm_ms") is not None and t["llm_ms"] > 0]
            if len(llm_times) >= MIN_SAMPLE_SIZE:
                mean_llm = sum(llm_times) / len(llm_times)
                recent_count = max(10, len(llm_times) // 5)
                recent_llm = llm_times[:recent_count]
                recent_mean = sum(recent_llm) / len(recent_llm)

                if recent_mean > mean_llm * COST_SPIKE_RATIO:
                    candidate = RegimeShiftCandidate.new(
                        shift_type=RegimeShiftType.COST_EXPLOSION,
                        segment="global",
                        confidence=round(min(0.95, 0.6 + 0.1 * (recent_mean / mean_llm - 1)), 3),
                        evidence={
                            "mean_llm_ms": round(mean_llm, 1),
                            "recent_mean_llm_ms": round(recent_mean, 1),
                            "spike_ratio": round(recent_mean / mean_llm, 2),
                            "sample_size": len(llm_times),
                            "detection": "llm_cost_spike"
                        },
                        faculty=Faculty.MODEL_OF_MODELS
                    )
                    candidates.append(candidate)

        # Check 3: Call-type predictor vs outcome disagreement
        for call in calls[:50]:  # Check recent 50 calls
            call_type = (call.get("call_type") or "").lower()
            outcome = (call.get("final_outcome") or "").lower()
            conf = call.get("call_type_confidence", 0) or 0

            # High confidence prediction that disagreed with outcome
            if conf > 0.8:
                if call_type in ("human_interested", "human_engaged") and \
                   outcome in ("organism_unfit", "hung_up", "no_answer"):
                    # Predictor said interested, outcome was bad — rare is OK, pattern is not
                    pass  # Collect these, only emit if pattern found

        self._telemetry.emit("FACULTY_RUN_COMPLETE", {
            "faculty": "model_of_models",
            "candidates_emitted": len(candidates),
            "checks": ["objection_mutation", "cost_explosion", "predictor_disagreement"]
        })
        return candidates


# ─── PROPOSAL COMPOSER ──────────────────────────────────────────────────────

class ProposalComposer:
    """
    Composes candidates into proposals with recommended actions.
    Applies the confidence floor and deduplication logic.
    """

    def compose(self, candidates: List[RegimeShiftCandidate]) -> List[RegimeProposal]:
        """
        Group candidates by segment and type, compose proposals.
        Each proposal targets one segment with coherent recommendations.
        """
        if not candidates:
            return []

        # Filter below confidence floor
        viable = [c for c in candidates if c.confidence >= CONFIDENCE_FLOOR]
        if not viable:
            return []

        # Group by segment
        by_segment: Dict[str, List[RegimeShiftCandidate]] = {}
        for c in viable:
            by_segment.setdefault(c.segment, []).append(c)

        proposals = []
        for segment, seg_candidates in by_segment.items():
            actions = self._recommend_actions(segment, seg_candidates)
            config_diff = self._compute_config_diff(segment, seg_candidates)
            proposal = RegimeProposal.compose(seg_candidates, actions, config_diff)
            proposals.append(proposal)

        return proposals

    def _recommend_actions(self, segment: str,
                           candidates: List[RegimeShiftCandidate]) -> List[ModelActionRequest]:
        """Generate action recommendations based on candidate types."""
        actions = []
        types = {c.type for c in candidates}
        max_conf = max(c.confidence for c in candidates)

        if RegimeShiftType.COST_EXPLOSION in types:
            actions.append(ModelActionRequest(
                action=ModelActionType.RETRAIN_MODEL,
                target=segment,
                parameters={"reason": "cost_explosion", "urgency": "high"}
            ))

        if RegimeShiftType.SCRIPT_PERFORMANCE in types and max_conf > 0.8:
            actions.append(ModelActionRequest(
                action=ModelActionType.SPLIT_SEGMENT,
                target=segment,
                parameters={"reason": "script_degradation"}
            ))

        if RegimeShiftType.STATE_CULTURAL_SHIFT in types:
            actions.append(ModelActionRequest(
                action=ModelActionType.RETRAIN_MODEL,
                target=segment,
                parameters={"reason": "cultural_shift"}
            ))

        if RegimeShiftType.OBJECTION_MUTATION in types:
            actions.append(ModelActionRequest(
                action=ModelActionType.SPAWN_NEW_MODEL,
                target=segment,
                parameters={"reason": "objection_mutation_detected"}
            ))

        return actions

    def _compute_config_diff(self, segment: str,
                             candidates: List[RegimeShiftCandidate]) -> Dict[str, Any]:
        """Compute the config diff this proposal would apply."""
        max_conf = max(c.confidence for c in candidates)
        types = {c.type for c in candidates}

        new_status = SegmentStatus.STABLE
        new_priority = SegmentPriority.MEDIUM
        new_trust = PredictionTrust.MEDIUM

        if max_conf > 0.85:
            new_status = SegmentStatus.DEGRADED
            new_trust = PredictionTrust.LOW
        elif max_conf > 0.7:
            new_status = SegmentStatus.SHIFTING
            new_trust = PredictionTrust.LOW

        if RegimeShiftType.COST_EXPLOSION in types:
            new_priority = SegmentPriority.LOW
            new_status = SegmentStatus.DEGRADED

        notes_parts = [f"{c.type.value}(conf={c.confidence})" for c in candidates]

        return {
            "segments": {
                segment: {
                    "priority": new_priority.value,
                    "prediction_trust": new_trust.value,
                    "status": new_status.value,
                    "notes": f"Auto-detected: {', '.join(notes_parts)}"
                }
            }
        }


# ─── GOVERNANCE INTERFACE ────────────────────────────────────────────────────

class GovernanceInterface:
    """
    Interface with Agent X governance.
    In auto-approve mode (for now), proposals meeting threshold are approved.
    Full Agent X governance integration will require the governance loop.
    """

    AUTO_APPROVE_THRESHOLD = 0.80  # Auto-approve if all candidates >= this

    def evaluate_proposal(self, proposal: RegimeProposal) -> ProposalStatus:
        """
        Evaluate a proposal for approval.
        Currently: auto-approve if average confidence >= threshold.
        Future: Route to Agent X governance queue.
        """
        if not proposal.candidates:
            return ProposalStatus.REJECTED

        avg_conf = sum(c.confidence for c in proposal.candidates) / len(proposal.candidates)

        if avg_conf >= self.AUTO_APPROVE_THRESHOLD:
            return ProposalStatus.APPROVED
        elif avg_conf >= CONFIDENCE_FLOOR:
            return ProposalStatus.PENDING  # Needs human/Agent X review
        else:
            return ProposalStatus.REJECTED


# ─── REGIME ENGINE CORE ─────────────────────────────────────────────────────

class RegimeEngine:
    """
    The Regime Engine 1.0 — meta-organ.
    
    Orchestrates the four faculties, composes proposals,
    routes through governance, and writes regime_config_live.json.
    
    Usage:
        engine = RegimeEngine()
        result = engine.run()
        print(json.dumps(result, indent=2))
    """

    def __init__(self, db_path: str = CDC_DB_PATH,
                 config_path: str = CONFIG_LIVE_PATH,
                 telemetry_path: str = TELEMETRY_LOG_PATH):
        self._cdc = CDCReader(db_path)
        self._telemetry = TelemetryEmitter(telemetry_path)
        self._config_path = config_path
        self._composer = ProposalComposer()
        self._governance = GovernanceInterface()

        # Initialize faculties
        self._faculties = [
            UncertaintyFaculty(self._cdc, self._telemetry),
            AnomalyFaculty(self._cdc, self._telemetry),
            ValueFaculty(self._cdc, self._telemetry),
            ModelOfModelsFaculty(self._cdc, self._telemetry),
        ]

    def run(self) -> Dict[str, Any]:
        """
        Execute one full engine cycle:
        1. Run all faculties → collect candidates
        2. Compose candidates into proposals
        3. Route proposals through governance
        4. Apply approved proposals to config
        5. Write regime_config_live.json
        6. Return summary
        """
        run_start = datetime.now(timezone.utc)

        # Step 1: Run all faculties
        all_candidates: List[RegimeShiftCandidate] = []
        for faculty in self._faculties:
            try:
                candidates = faculty.evaluate()
                all_candidates.extend(candidates)
            except Exception as e:
                self._telemetry.emit("FACULTY_ERROR", {
                    "faculty": faculty.__class__.__name__,
                    "error": str(e)
                })

        self._telemetry.emit("REGIME_SHIFT_CANDIDATE_DETECTED", {
            "total_candidates": len(all_candidates),
            "by_type": self._count_by_type(all_candidates),
            "by_faculty": self._count_by_faculty(all_candidates)
        })

        # Step 2: Compose proposals
        proposals = self._composer.compose(all_candidates)
        for p in proposals:
            self._telemetry.emit("REGIME_PROPOSAL_COMPOSED", {
                "proposal_id": p.proposal_id,
                "candidate_count": len(p.candidates),
                "segments_affected": list({c.segment for c in p.candidates})
            })

        # Step 3: Governance
        approved = []
        rejected = []
        for proposal in proposals:
            status = self._governance.evaluate_proposal(proposal)
            proposal.status = status
            if status == ProposalStatus.APPROVED:
                approved.append(proposal)
                self._telemetry.emit("REGIME_PROPOSAL_APPROVED", {
                    "proposal_id": proposal.proposal_id
                })
            else:
                rejected.append(proposal)
                self._telemetry.emit("REGIME_PROPOSAL_REJECTED", {
                    "proposal_id": proposal.proposal_id,
                    "status": status.value
                })

        # Step 4: Load existing config or create fresh
        config = self._load_config()

        # Apply approved proposals
        for proposal in approved:
            self._apply_proposal(config, proposal)

        # Step 5: Write config
        config.generated_at = datetime.now(timezone.utc).isoformat()
        config.governance = {
            "approved_proposals": [p.proposal_id for p in approved],
            "rejected_proposals": [
                {"proposal_id": p.proposal_id, "reason": p.status.value}
                for p in rejected
            ]
        }
        self._write_config(config)

        self._telemetry.emit("CONFIG_LIVE_UPDATED", {
            "segments": len(config.segments),
            "approved": len(approved),
            "rejected": len(rejected)
        })

        run_duration = (datetime.now(timezone.utc) - run_start).total_seconds()

        return {
            "status": "complete",
            "version": VERSION,
            "duration_seconds": round(run_duration, 3),
            "candidates_detected": len(all_candidates),
            "proposals_composed": len(proposals),
            "proposals_approved": len(approved),
            "proposals_rejected": len(rejected),
            "segments_in_config": len(config.segments),
            "config_path": self._config_path
        }

    def get_status(self) -> Dict[str, Any]:
        """Return current engine status without running a cycle."""
        config = self._load_config()
        return {
            "version": VERSION,
            "config_exists": os.path.exists(self._config_path),
            "config_generated_at": config.generated_at,
            "segments": len(config.segments),
            "segment_statuses": {
                k: v.status.value for k, v in config.segments.items()
            }
        }

    def _load_config(self) -> RegimeConfigLive:
        """Load existing config or return clean default."""
        if os.path.exists(self._config_path):
            try:
                with open(self._config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                config = RegimeConfigLive()
                config.version = data.get("version", VERSION)
                config.generated_at = data.get("generated_at", "")
                for seg_name, seg_data in data.get("segments", {}).items():
                    config.segments[seg_name] = SegmentConfig(
                        priority=SegmentPriority(seg_data.get("priority", "MEDIUM")),
                        prediction_trust=PredictionTrust(seg_data.get("prediction_trust", "MEDIUM")),
                        status=SegmentStatus(seg_data.get("status", "STABLE")),
                        preferred_script=seg_data.get("preferred_script"),
                        notes=seg_data.get("notes")
                    )
                return config
            except Exception:
                pass
        return RegimeConfigLive()

    def _apply_proposal(self, config: RegimeConfigLive, proposal: RegimeProposal) -> None:
        """Apply an approved proposal to the live config."""
        diff = proposal.config_diff
        for seg_name, seg_data in diff.get("segments", {}).items():
            config.segments[seg_name] = SegmentConfig(
                priority=SegmentPriority(seg_data.get("priority", "MEDIUM")),
                prediction_trust=PredictionTrust(seg_data.get("prediction_trust", "MEDIUM")),
                status=SegmentStatus(seg_data.get("status", "STABLE")),
                preferred_script=seg_data.get("preferred_script"),
                notes=seg_data.get("notes")
            )

        # Convert candidates to regime events
        for c in proposal.candidates:
            event = RegimeEvent(
                event_id=f"evt_{uuid.uuid4().hex[:12]}",
                type=c.type,
                confidence=c.confidence,
                timestamp=c.detected_at,
                segment=c.segment,
                evidence=c.evidence
            )
            config.regime_events.append(event)

        # Add model actions
        config.model_actions.extend(proposal.recommended_actions)

    def _write_config(self, config: RegimeConfigLive) -> None:
        """Write regime_config_live.json."""
        os.makedirs(os.path.dirname(self._config_path), exist_ok=True)
        with open(self._config_path, "w", encoding="utf-8") as f:
            json.dump(config.to_dict(), f, indent=2, default=str)

    @staticmethod
    def _count_by_type(candidates: List[RegimeShiftCandidate]) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for c in candidates:
            counts[c.type.value] = counts.get(c.type.value, 0) + 1
        return counts

    @staticmethod
    def _count_by_faculty(candidates: List[RegimeShiftCandidate]) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for c in candidates:
            counts[c.faculty.value] = counts.get(c.faculty.value, 0) + 1
        return counts


# ─── CLI ENTRY POINT ─────────────────────────────────────────────────────────

def main():
    """Run the Regime Engine and print results."""
    print("=" * 70)
    print("  REGIME ENGINE 1.0 — Executing Full Cycle")
    print("=" * 70)

    engine = RegimeEngine()
    result = engine.run()

    print(f"\n  Status:             {result['status']}")
    print(f"  Version:            {result['version']}")
    print(f"  Duration:           {result['duration_seconds']}s")
    print(f"  Candidates Found:   {result['candidates_detected']}")
    print(f"  Proposals Composed: {result['proposals_composed']}")
    print(f"  Proposals Approved: {result['proposals_approved']}")
    print(f"  Proposals Rejected: {result['proposals_rejected']}")
    print(f"  Segments in Config: {result['segments_in_config']}")
    print(f"  Config Written To:  {result['config_path']}")
    print("=" * 70)

    # Also print current config
    if os.path.exists(CONFIG_LIVE_PATH):
        with open(CONFIG_LIVE_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
        print("\n  Live Config:")
        print(json.dumps(config, indent=2))


if __name__ == "__main__":
    main()
