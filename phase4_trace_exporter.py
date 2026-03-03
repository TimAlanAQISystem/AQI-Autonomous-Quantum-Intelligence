"""
Phase 4 Trace Exporter
========================
Wired into aqi_conversation_relay_server.py at three hooks:
  1. on_call_start  → init_trace()
  2. on_turn        → append_turn()
  3. on_call_end    → finalize_trace()

Emits canonical Phase4CallTrace JSON to data/phase4/traces.jsonl.
Each call produces exactly one JSON line upon finalization.

The exporter accumulates per-turn health and telephony snapshots
to build the health_trajectory and telephony_trajectory arrays
that the Phase 5 Behavioral Intelligence stack requires.

Zero external dependencies. Triple-safe — every public method
wraps in try/except so relay server stability is never risked.
"""

import json
import os
import logging
import threading
from datetime import datetime, timezone

logger = logging.getLogger("phase4_trace_exporter")

# ─── Output paths ───────────────────────────────────────────────
PHASE4_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "phase4")
PHASE4_TRACES_FILE = os.path.join(PHASE4_DATA_DIR, "traces.jsonl")

# ─── AQI FSM states (canonical) ────────────────────────────────
VALID_FSM_STATES = {"OPENING", "DISCOVERY", "VALUE", "OBJECTION", "CLOSE", "EXIT"}

# ─── Exit reasons (canonical) ──────────────────────────────────
VALID_EXIT_REASONS = {
    "caller_hangup", "stream_stop", "organism_unfit", "telephony_unusable",
    "repetition_bail", "government_entity", "ivr_system", "voicemail_ivr",
    "connection_loss_kill", "max_duration_kill", "ivr_transcript_kill",
    "hard_decline", "appointment_set", "soft_decline",
}

# ─── Governance order (prompt layers) ──────────────────────────
GOVERNANCE_ORDER = ["Identity", "Ethics", "Personality", "Knowledge", "Mission", "Output"]

# ─── Prompt tier map (turn count → active layers) ──────────────
# FAST_PATH: turns 0-2, MIDWEIGHT: 3-7, FULL: 8+
def _get_prompt_layers_dict(turn_count, aqi_layers=None):
    """Build canonical PromptLayers dict from turn count or explicit layer list."""
    if aqi_layers and isinstance(aqi_layers, list):
        # Map list to governance-ordered dict
        result = {}
        for layer_name in GOVERNANCE_ORDER:
            result[layer_name] = "active" if layer_name in aqi_layers else "inactive"
        return result

    # Derive from turn count (fast path / midweight / full)
    if turn_count <= 2:
        # FAST_PATH: Identity + Personality + Mission
        return {
            "Identity": "active", "Ethics": "inactive", "Personality": "active",
            "Knowledge": "inactive", "Mission": "active", "Output": "inactive",
        }
    elif turn_count <= 7:
        # MIDWEIGHT: Identity + Ethics + Personality + Mission + Output
        return {
            "Identity": "active", "Ethics": "active", "Personality": "active",
            "Knowledge": "inactive", "Mission": "active", "Output": "active",
        }
    else:
        # FULL: All 6
        return {
            "Identity": "active", "Ethics": "active", "Personality": "active",
            "Knowledge": "active", "Mission": "active", "Output": "active",
        }


class _ActiveTrace:
    """Internal per-call accumulator. Not exported."""

    __slots__ = (
        "call_id", "start_time", "merchant_profile",
        "turns", "health_trajectory", "telephony_trajectory",
        "prev_fsm_state", "close_attempt_count", "escalation_count",
        "custom_params",
    )

    def __init__(self, call_id, start_time, custom_params=None):
        self.call_id = call_id
        self.start_time = start_time
        self.custom_params = custom_params or {}
        self.merchant_profile = {
            "business_type": self.custom_params.get("business_name") or self.custom_params.get("business_type"),
            "size": None,
            "prior_processing": None,
        }
        self.turns = []
        self.health_trajectory = []
        self.telephony_trajectory = []
        self.prev_fsm_state = "OPENING"
        self.close_attempt_count = 0
        self.escalation_count = 0


class Phase4TraceExporter:
    """
    Accumulates per-call telemetry and emits canonical Phase4CallTrace JSON.

    Usage (inside relay server):
        self._phase4_exporter = Phase4TraceExporter()

        # on_call_start:
        self._phase4_exporter.init_trace(call_sid, custom_params, start_time)

        # on_turn:
        self._phase4_exporter.append_turn(call_sid, turn_data)

        # on_call_end:
        self._phase4_exporter.finalize_trace(call_sid, final_data)
    """

    def __init__(self, output_dir=None, output_file=None):
        self._traces = {}  # call_sid → _ActiveTrace
        self._lock = threading.Lock()
        self._output_dir = output_dir or PHASE4_DATA_DIR
        self._output_file = output_file or os.path.join(self._output_dir, "traces.jsonl")
        self._ensure_output_dir()
        self._finalized_count = 0
        logger.info(f"[PHASE 4 EXPORTER] Initialized — output: {self._output_file}")

    def _ensure_output_dir(self):
        """Create output directory if it doesn't exist."""
        try:
            os.makedirs(self._output_dir, exist_ok=True)
        except Exception as e:
            logger.error(f"[PHASE 4 EXPORTER] Cannot create output dir: {e}")

    # ─── HOOK 1: on_call_start ──────────────────────────────────

    def init_trace(self, call_id, custom_params=None, start_time=None):
        """
        Initialize a new call trace skeleton.

        Called from relay server on_call_start (stream 'start' event).

        Args:
            call_id: Twilio call SID
            custom_params: dict from data['start']['customParameters']
                Keys: prospect_phone, prospect_name, business_name,
                      call_type, strategy, call_direction
            start_time: datetime — call start timestamp
        """
        try:
            if not call_id:
                logger.warning("[PHASE 4 EXPORTER] init_trace called with empty call_id — skipped")
                return

            _start = start_time or datetime.now(timezone.utc)
            if isinstance(_start, datetime) and _start.tzinfo is None:
                _start = _start.replace(tzinfo=timezone.utc)

            trace = _ActiveTrace(call_id, _start, custom_params or {})

            with self._lock:
                self._traces[call_id] = trace

            logger.info(f"[PHASE 4 EXPORTER] Trace initialized: {call_id}")

        except Exception as e:
            logger.error(f"[PHASE 4 EXPORTER] init_trace failed (non-fatal): {e}")

    # ─── HOOK 2: on_turn ────────────────────────────────────────

    def append_turn(self, call_id, turn_data):
        """
        Append a turn record to the active trace.

        Called from relay server on_turn, after AQI guard check.

        Args:
            turn_data: dict with keys:
                - fsm_state: str (OPENING/DISCOVERY/VALUE/OBJECTION/CLOSE/EXIT)
                - fsm_prev_state: str
                - fsm_event: str (merchant_speaks/objection_detected/degrade/veto/end)
                - organism_level: int (1-4)
                - telephony_state: str (Excellent/Good/Degraded/Unusable)
                - turn_count: int
                - user_text: str (merchant's speech)
                - response_text: str (Alan's response)
                - aqi_layers: list[str] (active prompt layers)
                - behavior_profile: dict (optional)
                - master_closer_state: dict (optional)
                - live_objection_type: str|None
                - caller_energy: str (optional)
        """
        try:
            with self._lock:
                trace = self._traces.get(call_id)

            if not trace:
                logger.debug(f"[PHASE 4 EXPORTER] append_turn: no active trace for {call_id}")
                return

            td = turn_data or {}
            turn_index = len(trace.turns)
            fsm_state = td.get("fsm_state", "OPENING")
            fsm_prev = td.get("fsm_prev_state", trace.prev_fsm_state)
            fsm_event = td.get("fsm_event", "merchant_speaks")
            turn_count = td.get("turn_count", turn_index)

            # ── Derive mission_escalation ──
            mcs = td.get("master_closer_state") or {}
            mission_escalation = (
                mcs.get("endgame_state") == "ready"
                or fsm_state == "CLOSE"
                or trace.escalation_count > 0
                and fsm_state in ("CLOSE", "EXIT")
            )
            if fsm_state == "CLOSE" and fsm_prev != "CLOSE":
                trace.escalation_count += 1

            # ── Derive close_attempt ──
            close_attempt = (
                fsm_state == "CLOSE"
                and mcs.get("endgame_state") == "ready"
            ) or (
                fsm_state == "CLOSE"
                and fsm_prev != "CLOSE"
            )
            if close_attempt:
                trace.close_attempt_count += 1

            # ── Derive objection_branch ──
            objection_branch = td.get("live_objection_type")

            # ── Derive output_complexity ──
            response_text = td.get("response_text", "")
            resp_len = len(response_text) if response_text else 0
            if resp_len < 80:
                output_complexity = "minimal"
            elif resp_len < 250:
                output_complexity = "normal"
            else:
                output_complexity = "complex"

            # ── Build prompt layers dict ──
            prompt_layers = _get_prompt_layers_dict(
                turn_count,
                td.get("aqi_layers")
            )

            # ── Build health snapshot ──
            organism_level = td.get("organism_level", 1)
            telephony_state = td.get("telephony_state", "Excellent")

            health_snapshot = {
                "organism_level": organism_level,
                "telephony_state": telephony_state,
            }

            # ── Accumulate trajectories ──
            trace.health_trajectory.append({
                "turn_index": turn_index,
                "organism_level": organism_level,
                "telephony_state": telephony_state,
            })

            trace.telephony_trajectory.append({
                "turn_index": turn_index,
                "telephony_state": telephony_state,
            })

            # ── Build canonical turn record ──
            turn_record = {
                "turn_index": turn_index,
                "fsm_prev_state": fsm_prev,
                "fsm_event": fsm_event,
                "fsm_state": fsm_state,
                "prompt_layers": prompt_layers,
                "context": {
                    "mission_escalation": bool(mission_escalation),
                    "objection_branch": objection_branch,
                    "close_attempt": bool(close_attempt),
                    "output_complexity": output_complexity,
                    "supervisor_flags": None,
                },
                "health_snapshot": health_snapshot,
            }

            with self._lock:
                trace.turns.append(turn_record)
                trace.prev_fsm_state = fsm_state

        except Exception as e:
            logger.error(f"[PHASE 4 EXPORTER] append_turn failed (non-fatal): {e}")

    # ─── HOOK 3: on_call_end ────────────────────────────────────

    def finalize_trace(self, call_id, final_data=None):
        """
        Finalize the trace and write to JSONL.

        Called from relay server on_call_end (stream 'stop' event).

        Args:
            final_data: dict with keys:
                - fsm_state: str (final FSM state)
                - exit_reason: str (canonical exit reason)
                - outcome: dict (optional — {outcome, turns, trajectory})
                - end_time: datetime (optional)
                - master_closer_state: dict (optional)
                - evolution_outcome: str (optional)

        Returns:
            dict: The complete Phase4CallTrace dict, or None on failure
        """
        try:
            with self._lock:
                trace = self._traces.pop(call_id, None)

            if not trace:
                logger.warning(f"[PHASE 4 EXPORTER] finalize_trace: no active trace for {call_id}")
                return None

            fd = final_data or {}
            end_time = fd.get("end_time") or datetime.now(timezone.utc)
            if isinstance(end_time, datetime) and end_time.tzinfo is None:
                end_time = end_time.replace(tzinfo=timezone.utc)

            # ── Resolve exit reason ──
            exit_reason = (
                fd.get("exit_reason")
                or fd.get("evolution_outcome")
                or "caller_hangup"
            )

            # ── Build outcome vector ──
            outcome_vector = self._build_outcome_vector(exit_reason, fd)

            # ── Build final block ──
            final_block = {
                "fsm_state": fd.get("fsm_state", trace.prev_fsm_state),
                "exit_reason": exit_reason,
                "health_trajectory": trace.health_trajectory,
                "telephony_trajectory": trace.telephony_trajectory,
                "outcome_vector": outcome_vector,
            }

            # ── Assemble canonical trace ──
            canonical_trace = {
                "call_id": call_id,
                "metadata": {
                    "timestamp_start": self._format_timestamp(trace.start_time),
                    "timestamp_end": self._format_timestamp(end_time),
                    "merchant_profile": trace.merchant_profile,
                },
                "turns": trace.turns,
                "final": final_block,
            }

            # ── Write to JSONL ──
            self._write_trace(canonical_trace)

            self._finalized_count += 1
            logger.info(
                f"[PHASE 4 EXPORTER] Trace finalized: {call_id} | "
                f"turns={len(trace.turns)} exit={exit_reason} | "
                f"total_finalized={self._finalized_count}"
            )

            return canonical_trace

        except Exception as e:
            logger.error(f"[PHASE 4 EXPORTER] finalize_trace failed (non-fatal): {e}")
            return None

    # ─── Outcome Vector Builder ─────────────────────────────────

    @staticmethod
    def _build_outcome_vector(exit_reason, final_data=None):
        """
        Derive the outcome vector from exit_reason.

        Maps the relay server's exit reason to the 5 canonical booleans.
        """
        fd = final_data or {}
        outcome = fd.get("outcome", {})
        outcome_label = outcome.get("outcome", exit_reason) if isinstance(outcome, dict) else exit_reason

        return {
            "appointment_set": outcome_label == "appointment_set" or exit_reason == "appointment_set",
            "soft_decline": outcome_label in ("soft_decline", "caller_hangup", "stream_stop"),
            "hard_decline": outcome_label == "hard_decline" or exit_reason == "hard_decline",
            "telephony_unusable": exit_reason == "telephony_unusable",
            "organism_unfit": exit_reason == "organism_unfit",
        }

    # ─── Health Trajectory Builder ──────────────────────────────

    @staticmethod
    def build_health_trajectory(turns):
        """
        Build the health_trajectory array from accumulated turns.

        This is the canonical builder that Tim asked about.
        Called internally during finalize_trace() — the trajectory is
        accumulated incrementally in append_turn(), so this method
        exists for external/test use.

        Args:
            turns: list of turn dicts (canonical Phase4 turn shape)

        Returns:
            list[dict]: [{turn_index, organism_level, telephony_state}, ...]
        """
        trajectory = []
        for turn in turns:
            hs = turn.get("health_snapshot", {})
            trajectory.append({
                "turn_index": turn.get("turn_index", len(trajectory)),
                "organism_level": hs.get("organism_level", 1),
                "telephony_state": hs.get("telephony_state", "Excellent"),
            })
        return trajectory

    # ─── Telephony Trajectory Builder ───────────────────────────

    @staticmethod
    def build_telephony_trajectory(turns):
        """
        Build the telephony_trajectory array from accumulated turns.

        This is the canonical builder that Tim asked about.
        Called internally during finalize_trace() — the trajectory is
        accumulated incrementally in append_turn(), so this method
        exists for external/test use.

        Args:
            turns: list of turn dicts (canonical Phase4 turn shape)

        Returns:
            list[dict]: [{turn_index, telephony_state}, ...]
        """
        trajectory = []
        for turn in turns:
            hs = turn.get("health_snapshot", {})
            trajectory.append({
                "turn_index": turn.get("turn_index", len(trajectory)),
                "telephony_state": hs.get("telephony_state", "Excellent"),
            })
        return trajectory

    # ─── Internal Helpers ───────────────────────────────────────

    def _write_trace(self, trace_dict):
        """Append a single trace to the JSONL file. Thread-safe."""
        try:
            self._ensure_output_dir()
            with self._lock:
                with open(self._output_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(trace_dict, default=str) + "\n")
        except Exception as e:
            logger.error(f"[PHASE 4 EXPORTER] Write failed: {e}")

    @staticmethod
    def _format_timestamp(dt):
        """Format datetime to ISO 8601 string."""
        if isinstance(dt, datetime):
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.isoformat()
        return str(dt)

    # ─── Diagnostics ────────────────────────────────────────────

    @property
    def active_traces(self):
        """Number of traces currently being accumulated."""
        return len(self._traces)

    @property
    def finalized_count(self):
        """Total traces finalized and written."""
        return self._finalized_count

    def get_active_call_ids(self):
        """List call_ids with active traces (for debugging)."""
        with self._lock:
            return list(self._traces.keys())

    def has_trace(self, call_id):
        """Check if a trace is active for the given call_id."""
        return call_id in self._traces


# ─── Module-level factory (for relay server) ───────────────────

def create_phase4_exporter(output_dir=None):
    """Create a Phase4TraceExporter instance. Triple-safe."""
    try:
        return Phase4TraceExporter(output_dir=output_dir)
    except Exception as e:
        logger.error(f"[PHASE 4 EXPORTER] Factory failed: {e}")
        return None
