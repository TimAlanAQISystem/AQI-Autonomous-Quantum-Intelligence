-- ============================================================
-- AQI Phase 5 — Intelligence Database Schema
-- ============================================================
-- Relational schema for persisting Phase 5 behavioral intelligence.
-- SQLite-compatible. Hydrated from Phase 5 pipeline output.
--
-- Tables:
--   calls           — Phase 4 call metadata
--   call_profiles   — Phase 5 behavioral signals per call
--   call_tags       — Phase 5 behavioral tags per call
--   continuum_axes  — Continuum Map projections per call
--   aggregates      — Cross-call intelligence snapshots
-- ============================================================

CREATE TABLE IF NOT EXISTS calls (
    id              TEXT PRIMARY KEY,
    timestamp_start TEXT NOT NULL,
    timestamp_end   TEXT NOT NULL,
    business_type   TEXT,
    size            TEXT,
    prior_processing TEXT,
    total_turns     INTEGER,
    exit_reason     TEXT,
    appointment_set INTEGER DEFAULT 0,
    created_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS call_profiles (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    call_id                 TEXT NOT NULL REFERENCES calls(id),
    persistence             TEXT,
    caution                 TEXT,
    escalation_timing       TEXT,
    objection_depth         TEXT,
    withdrawal_behavior     TEXT,
    personality_modulation  TEXT,
    created_at              TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS call_tags (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    call_id  TEXT NOT NULL REFERENCES calls(id),
    tag      TEXT NOT NULL,
    is_positive INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS continuum_axes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    call_id     TEXT NOT NULL REFERENCES calls(id),
    axis_name   TEXT NOT NULL,
    axis_data   TEXT NOT NULL,  -- JSON-encoded axis value
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS aggregates (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    window_size     INTEGER NOT NULL,
    total_calls     INTEGER NOT NULL,
    persistence_bias TEXT,
    caution_bias     TEXT,
    close_timing_bias TEXT,
    objection_bias   TEXT,
    personality_stability TEXT,
    conversion_rate  REAL,
    tag_counts       TEXT,  -- JSON
    heatmaps         TEXT,  -- JSON
    created_at       TEXT DEFAULT (datetime('now'))
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_calls_exit ON calls(exit_reason);
CREATE INDEX IF NOT EXISTS idx_calls_appt ON calls(appointment_set);
CREATE INDEX IF NOT EXISTS idx_tags_tag ON call_tags(tag);
CREATE INDEX IF NOT EXISTS idx_tags_call ON call_tags(call_id);
CREATE INDEX IF NOT EXISTS idx_profiles_call ON call_profiles(call_id);
CREATE INDEX IF NOT EXISTS idx_continuum_call ON continuum_axes(call_id);
CREATE INDEX IF NOT EXISTS idx_continuum_axis ON continuum_axes(axis_name);
