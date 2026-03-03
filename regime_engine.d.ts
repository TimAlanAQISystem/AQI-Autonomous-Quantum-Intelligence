/**
 * Regime Engine 1.0 — TypeScript Type Definitions
 * Fully aligned with REGIME_ENGINE_CONFIG_SCHEMA.json
 *
 * These types define the shape of all data flowing through the
 * Regime Engine meta-organ. They are strictly readonly where
 * the contract demands immutability.
 */

// ─── Enums & Literals ──────────────────────────────────────────────

export type SegmentPriority = "HIGH" | "MEDIUM" | "LOW" | "OFF";
export type PredictionTrust = "HIGH" | "MEDIUM" | "LOW";
export type SegmentStatus = "STABLE" | "SHIFTING" | "DEGRADED" | "EXPERIMENTAL";
export type PacingMode = "AGGRESSIVE" | "NORMAL" | "CONSERVATIVE";

export type RegimeShiftType =
  | "timing_regime"
  | "state_cultural_shift"
  | "script_performance"
  | "objection_mutation"
  | "cost_explosion";

export type ModelAction =
  | "spawn_new_model"
  | "retire_model"
  | "split_segment"
  | "merge_segment"
  | "retrain_model";

// ─── Segment Config ────────────────────────────────────────────────

export interface SegmentConfig {
  readonly priority: SegmentPriority;
  readonly prediction_trust: PredictionTrust;
  readonly status: SegmentStatus;
  readonly preferred_script?: string;
  readonly notes?: string;
}

// ─── Call Routing Override ─────────────────────────────────────────

export interface CallRoutingOverride {
  readonly queue_priority: SegmentPriority;
  readonly pacing: PacingMode;
}

// ─── Model Action Request ──────────────────────────────────────────

export interface ModelActionRequest {
  readonly action: ModelAction;
  readonly target: string;
  readonly parameters?: Record<string, unknown>;
}

// ─── Regime Event ──────────────────────────────────────────────────

export interface RegimeEvent {
  readonly event_id: string;
  readonly type: RegimeShiftType;
  readonly segment?: string;
  readonly state?: string;
  readonly script?: string;
  readonly confidence: number;
  readonly evidence?: Record<string, unknown>;
  readonly timestamp: string; // ISO 8601
}

// ─── Governance ────────────────────────────────────────────────────

export interface RejectedProposal {
  readonly proposal_id: string;
  readonly reason: string;
}

export interface GovernanceBlock {
  readonly approved_proposals: readonly string[];
  readonly rejected_proposals: readonly RejectedProposal[];
}

// ─── Top-Level Config ──────────────────────────────────────────────

export interface RegimeConfigLive {
  readonly version: string;
  readonly generated_at: string; // ISO 8601
  readonly segments: Record<string, SegmentConfig>;
  readonly call_routing_overrides?: Record<string, CallRoutingOverride>;
  readonly script_overrides?: Record<string, string>;
  readonly model_actions?: readonly ModelActionRequest[];
  readonly regime_events?: readonly RegimeEvent[];
  readonly governance?: GovernanceBlock;
}

// ─── Internal Engine Types (not in schema, engine-internal) ────────

/**
 * A candidate regime shift detected by one of the four faculties.
 * Before it becomes a REGIME_EVENT, it must be composed into a
 * REGIME_PROPOSAL and approved by governance.
 */
export interface RegimeShiftCandidate {
  readonly candidate_id: string;
  readonly type: RegimeShiftType;
  readonly segment: string;
  readonly confidence: number;
  readonly evidence: Record<string, unknown>;
  readonly faculty: "uncertainty" | "anomaly" | "value" | "model_of_models";
  readonly detected_at: string; // ISO 8601
}

/**
 * A proposal composed from one or more candidates.
 * Submitted to Agent X governance for approval.
 */
export interface RegimeProposal {
  readonly proposal_id: string;
  readonly candidates: readonly RegimeShiftCandidate[];
  readonly recommended_actions: readonly ModelActionRequest[];
  readonly config_diff: Partial<RegimeConfigLive>;
  readonly composed_at: string; // ISO 8601
  readonly status: "pending" | "approved" | "rejected" | "expired";
}

/**
 * Telemetry event emitted by the engine for audit trail.
 */
export interface RegimeEngineTelemetryEvent {
  readonly event_type:
    | "REGIME_SHIFT_CANDIDATE_DETECTED"
    | "REGIME_PROPOSAL_COMPOSED"
    | "REGIME_PROPOSAL_APPROVED"
    | "REGIME_PROPOSAL_REJECTED"
    | "CONFIG_LIVE_UPDATED"
    | "FACULTY_RUN_COMPLETE";
  readonly payload: Record<string, unknown>;
  readonly timestamp: string; // ISO 8601
}
