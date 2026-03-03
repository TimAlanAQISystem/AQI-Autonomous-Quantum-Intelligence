#!/usr/bin/env python3
"""
LEAD DATABASE — SQLite-Backed Merchant Lead Queue
===================================================
Replaces the 16K-line merchant_queue.json with a proper database.
- Thread-safe (SQLite WAL mode)
- Fast queries (indexed by phone, outcome, priority)
- Concurrent access safe
- Automatic JSON migration on first run

Usage:
    from lead_database import LeadDB
    db = LeadDB()
    lead = db.get_next_lead()
    db.record_attempt(lead["id"], "connected", "Campaign call SID: CA123")
"""

import sqlite3
import json
import os
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List
from contextlib import contextmanager

logger = logging.getLogger("LEAD_DB")

DB_PATH = Path(__file__).parent / "data" / "leads.db"
JSON_PATH = Path(__file__).parent / "merchant_queue.json"


class LeadDB:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(DB_PATH)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        
        # Auto-migrate from JSON if DB is empty and JSON exists
        if self._count() == 0 and JSON_PATH.exists():
            self._migrate_from_json()
    
    @contextmanager
    def _conn(self):
        """Thread-safe connection context manager"""
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def _init_db(self):
        """Create tables and indexes"""
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS leads (
                    id TEXT PRIMARY KEY,
                    phone_number TEXT NOT NULL,
                    name TEXT DEFAULT 'Unknown',
                    business_type TEXT DEFAULT 'Unknown',
                    priority TEXT DEFAULT 'medium',
                    attempts INTEGER DEFAULT 0,
                    max_attempts INTEGER DEFAULT 2,
                    last_attempt TEXT,
                    next_attempt TEXT,
                    outcome TEXT DEFAULT 'pending',
                    outcome_details TEXT,
                    interested_products TEXT DEFAULT '[]',
                    notes TEXT DEFAULT '[]',
                    do_not_call INTEGER DEFAULT 0,
                    created_at TEXT,
                    updated_at TEXT,
                    line_type TEXT DEFAULT 'unknown',
                    monthly_volume REAL,
                    lead_source TEXT,
                    tier TEXT,
                    expected_pitch TEXT,
                    fallback_pitch TEXT
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_phone ON leads(phone_number)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_outcome ON leads(outcome)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_priority ON leads(priority)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_dnc ON leads(do_not_call)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_next_attempt ON leads(next_attempt)")
            
            # Call history table for analytics
            conn.execute("""
                CREATE TABLE IF NOT EXISTS call_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    lead_id TEXT,
                    call_sid TEXT,
                    outcome TEXT,
                    duration_seconds INTEGER DEFAULT 0,
                    recording_url TEXT,
                    notes TEXT,
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (lead_id) REFERENCES leads(id)
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ch_lead ON call_history(lead_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ch_ts ON call_history(timestamp)")
    
    def _count(self) -> int:
        with self._conn() as conn:
            row = conn.execute("SELECT COUNT(*) as cnt FROM leads").fetchone()
            return row["cnt"]
    
    def _migrate_from_json(self):
        """One-time migration from merchant_queue.json"""
        logger.info(f"[LEAD_DB] Migrating from {JSON_PATH}...")
        try:
            with open(JSON_PATH, "r") as f:
                data = json.load(f)
            
            count = 0
            with self._conn() as conn:
                for key, m in data.items():
                    conn.execute("""
                        INSERT OR IGNORE INTO leads 
                        (id, phone_number, name, business_type, priority, attempts,
                         max_attempts, last_attempt, next_attempt, outcome, outcome_details,
                         interested_products, notes, do_not_call, created_at, updated_at,
                         line_type, monthly_volume, lead_source, tier, expected_pitch, fallback_pitch)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        m.get("id", key),
                        m.get("phone_number", ""),
                        m.get("name", "Unknown"),
                        m.get("business_type", "Unknown"),
                        m.get("priority", "medium"),
                        m.get("attempts", 0),
                        m.get("max_attempts", 2),
                        m.get("last_attempt"),
                        m.get("next_attempt"),
                        m.get("outcome", "pending"),
                        m.get("outcome_details"),
                        json.dumps(m.get("interested_products", [])),
                        json.dumps(m.get("notes", [])),
                        1 if m.get("do_not_call") else 0,
                        m.get("created_at", datetime.now().isoformat()),
                        m.get("updated_at", datetime.now().isoformat()),
                        m.get("line_type", "unknown"),
                        m.get("monthly_volume"),
                        m.get("lead_source"),
                        m.get("tier"),
                        m.get("expected_pitch"),
                        m.get("fallback_pitch")
                    ))
                    count += 1
            
            logger.info(f"[LEAD_DB] Migrated {count} leads from JSON to SQLite")
        except Exception as e:
            logger.error(f"[LEAD_DB] Migration failed: {e}")
    
    # ---- CORE OPERATIONS ----
    
    def get_next_lead(self, regime_aware: bool = True) -> Optional[Dict[str, Any]]:
        """Get the next callable lead (not DNC, under max attempts, due for retry).
        CW23 Regime Engine: When regime_aware=True, adjusts priority based on
        segment health from regime_config_live.json."""
        now = datetime.now().isoformat()
        with self._conn() as conn:
            # When regime-aware, pull a batch and let the regime engine re-rank
            if regime_aware:
                try:
                    from regime_queue_integrator import score_and_sort_leads, should_skip_lead
                    rows = conn.execute("""
                        SELECT * FROM leads 
                        WHERE do_not_call = 0 
                          AND attempts < max_attempts
                          AND outcome NOT IN ('sale', 'not_interested', 'invalid_number')
                          AND (next_attempt IS NULL OR next_attempt <= ?)
                          AND phone_number IS NOT NULL AND TRIM(phone_number) != ''
                        ORDER BY 
                            CASE priority WHEN 'critical' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END,
                            attempts ASC,
                            created_at ASC
                        LIMIT 20
                    """, (now,)).fetchall()

                    if rows:
                        candidates = [dict(r) for r in rows]
                        scored = score_and_sort_leads(candidates)
                        # Return first non-skipped lead
                        for lead in scored:
                            skip, reason = should_skip_lead(
                                lead.get("phone_number", ""),
                                lead.get("business_type", "")
                            )
                            if not skip:
                                return lead
                        # If all are skipped by regime, fall through to first candidate
                        return candidates[0]
                    return None
                except ImportError:
                    pass  # Regime module unavailable — fall through to standard query

            # Standard non-regime query
            row = conn.execute("""
                SELECT * FROM leads 
                WHERE do_not_call = 0 
                  AND attempts < max_attempts
                  AND outcome NOT IN ('sale', 'not_interested', 'invalid_number')
                  AND (next_attempt IS NULL OR next_attempt <= ?)
                  AND phone_number IS NOT NULL AND TRIM(phone_number) != ''
                ORDER BY 
                    CASE priority WHEN 'critical' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END,
                    attempts ASC,
                    created_at ASC
                LIMIT 1
            """, (now,)).fetchone()
            return dict(row) if row else None
    
    def record_attempt(self, lead_id: str, outcome: str, details: str = "", call_sid: str = "", duration: int = 0, recording_url: str = ""):
        """Record a call attempt and update lead status"""
        now = datetime.now().isoformat()
        retry_after = (datetime.now() + timedelta(hours=24)).isoformat()
        
        with self._conn() as conn:
            conn.execute("""
                UPDATE leads SET
                    attempts = attempts + 1,
                    last_attempt = ?,
                    next_attempt = ?,
                    outcome = ?,
                    outcome_details = ?,
                    updated_at = ?
                WHERE id = ?
            """, (now, retry_after, outcome, details, now, lead_id))
            
            # Log to call history
            conn.execute("""
                INSERT INTO call_history (lead_id, call_sid, outcome, duration_seconds, recording_url, notes, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (lead_id, call_sid, outcome, duration, recording_url, details, now))
    
    def add_lead(self, phone_number: str, name: str = "Unknown", business_type: str = "Unknown", priority: str = "medium", lead_source: str = None) -> str:
        """Add a new lead to the queue"""
        lead_id = f"merchant_{abs(hash(phone_number)) % 100000}"
        now = datetime.now().isoformat()
        
        with self._conn() as conn:
            conn.execute("""
                INSERT OR IGNORE INTO leads (id, phone_number, name, business_type, priority, lead_source, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (lead_id, phone_number, name, business_type, priority, lead_source, now, now))
        
        return lead_id
    
    def mark_dnc(self, phone_number: str):
        """Mark a number as Do Not Call"""
        with self._conn() as conn:
            conn.execute("UPDATE leads SET do_not_call = 1, updated_at = ? WHERE phone_number = ?",
                        (datetime.now().isoformat(), phone_number))
    
    def get_lead_by_phone(self, phone_number: str) -> Optional[Dict[str, Any]]:
        """Look up a lead by phone number"""
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM leads WHERE phone_number = ?", (phone_number,)).fetchone()
            return dict(row) if row else None
    
    def get_lead(self, lead_id: str) -> Optional[Dict[str, Any]]:
        """Get a lead by ID"""
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM leads WHERE id = ?", (lead_id,)).fetchone()
            return dict(row) if row else None
    
    def has_prior_conversation(self, phone_number: str) -> bool:
        """Check if a phone number has had a prior successful conversation.
        Used for voicemail exception: Tim's directive allows voicemail ONLY 
        for existing contacts/merchants we've already spoken with."""
        with self._conn() as conn:
            # Check if this phone has a lead with a successful outcome
            lead = conn.execute(
                "SELECT id, outcome FROM leads WHERE phone_number = ?", (phone_number,)
            ).fetchone()
            if not lead:
                return False
            if lead["outcome"] in ('connected', 'interested', 'sale', 'callback_scheduled'):
                return True
            # Check call history for any successful call
            history = conn.execute(
                "SELECT outcome FROM call_history WHERE lead_id = ? AND outcome IN ('connected', 'interested', 'sale')",
                (lead["id"],)
            ).fetchall()
            return len(history) > 0

    def apply_two_strike_check(self, phone_number: str) -> bool:
        """Check if a number has hit the 2-strike limit.
        Tim's directive: 'if it hits 2, that is it for that number.'
        Returns True if the number should be blocked (struck out)."""
        with self._conn() as conn:
            lead = conn.execute(
                "SELECT id, attempts, max_attempts FROM leads WHERE phone_number = ?", (phone_number,)
            ).fetchone()
            if lead and lead["attempts"] >= lead["max_attempts"]:
                return True
            return False

    def enforce_two_strike_all(self):
        """Update all existing leads to max_attempts=2 if currently set higher.
        One-time enforcement of Tim's 2-strike rule."""
        with self._conn() as conn:
            updated = conn.execute(
                "UPDATE leads SET max_attempts = 2 WHERE max_attempts > 2 AND outcome NOT IN ('sale', 'interested', 'connected')"
            )
            return updated.rowcount if hasattr(updated, 'rowcount') else 0

    # ---- ANALYTICS ----
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive queue statistics"""
        with self._conn() as conn:
            total = conn.execute("SELECT COUNT(*) as c FROM leads").fetchone()["c"]
            pending = conn.execute("SELECT COUNT(*) as c FROM leads WHERE outcome = 'pending'").fetchone()["c"]
            connected = conn.execute("SELECT COUNT(*) as c FROM leads WHERE outcome = 'connected'").fetchone()["c"]
            interested = conn.execute("SELECT COUNT(*) as c FROM leads WHERE outcome = 'interested'").fetchone()["c"]
            sale = conn.execute("SELECT COUNT(*) as c FROM leads WHERE outcome = 'sale'").fetchone()["c"]
            not_interested = conn.execute("SELECT COUNT(*) as c FROM leads WHERE outcome = 'not_interested'").fetchone()["c"]
            dnc = conn.execute("SELECT COUNT(*) as c FROM leads WHERE do_not_call = 1").fetchone()["c"]
            maxed_out = conn.execute("SELECT COUNT(*) as c FROM leads WHERE attempts >= max_attempts").fetchone()["c"]
            callable_now = conn.execute("""
                SELECT COUNT(*) as c FROM leads 
                WHERE do_not_call = 0 AND attempts < max_attempts
                  AND outcome NOT IN ('sale', 'not_interested', 'invalid_number')
                  AND (next_attempt IS NULL OR next_attempt <= ?)
            """, (datetime.now().isoformat(),)).fetchone()["c"]
            
            # Call history stats
            total_calls = conn.execute("SELECT COUNT(*) as c FROM call_history").fetchone()["c"]
            today_calls = conn.execute(
                "SELECT COUNT(*) as c FROM call_history WHERE timestamp >= ?",
                (datetime.now().replace(hour=0, minute=0, second=0).isoformat(),)
            ).fetchone()["c"]
            
            return {
                "total_leads": total,
                "pending": pending,
                "connected": connected,
                "interested": interested,
                "sales": sale,
                "not_interested": not_interested,
                "do_not_call": dnc,
                "maxed_out_attempts": maxed_out,
                "callable_now": callable_now,
                "total_calls_ever": total_calls,
                "calls_today": today_calls,
                "conversion_rate": round(sale / max(total_calls, 1) * 100, 2)
            }
    
    def get_call_history(self, lead_id: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Get call history, optionally filtered by lead"""
        with self._conn() as conn:
            if lead_id:
                rows = conn.execute(
                    "SELECT * FROM call_history WHERE lead_id = ? ORDER BY timestamp DESC LIMIT ?",
                    (lead_id, limit)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM call_history ORDER BY timestamp DESC LIMIT ?",
                    (limit,)
                ).fetchall()
            return [dict(r) for r in rows]
    
    def get_daily_stats(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get daily call stats for the last N days"""
        since = (datetime.now() - timedelta(days=days)).isoformat()
        with self._conn() as conn:
            rows = conn.execute("""
                SELECT 
                    DATE(timestamp) as date,
                    COUNT(*) as total_calls,
                    SUM(CASE WHEN outcome = 'connected' THEN 1 ELSE 0 END) as connected,
                    SUM(CASE WHEN outcome = 'interested' THEN 1 ELSE 0 END) as interested,
                    SUM(CASE WHEN outcome = 'sale' THEN 1 ELSE 0 END) as sales,
                    AVG(duration_seconds) as avg_duration
                FROM call_history
                WHERE timestamp >= ?
                GROUP BY DATE(timestamp)
                ORDER BY date DESC
            """, (since,)).fetchall()
            return [dict(r) for r in rows]


# Standalone migration utility
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    db = LeadDB()
    stats = db.get_stats()
    print(f"\n=== LEAD DATABASE STATS ===")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    print(f"\nDatabase: {DB_PATH}")
    print(f"Next callable lead: {db.get_next_lead()}")
