"""
DNC (Do Not Call) Manager
=========================
Auto-suppressor that marks phone numbers as DNC when merchants request removal.

Wires into:
  1. conversational_intelligence.py DNC detection → post-call DNC persist
  2. _fire_campaign.py lead selection → pre-dial DNC check
  3. lead_database.py mark_dnc() → persistence layer

Tim's directive: "a human hang up is the worst possible outcome... never by
timing or issues of any kind associated to the telephone, Twilio or coding
or anything that we have control over."

Calling a DNC number back is a controllable failure AND a legal liability.
"""

import time
import logging
import sqlite3
from typing import Optional

logger = logging.getLogger(__name__)

# DNC trigger phrases — if any match, mark the number as DNC
# These supplement the patterns in conversational_intelligence.py
DNC_TRIGGER_PHRASES = [
    "stop calling",
    "don't call",
    "do not call",
    "remove me",
    "take me off",
    "not interested",
    "never call",
    "quit calling",
    "stop ringing",
]


class DNCManager:
    """
    Manages the Do-Not-Call suppression list.
    
    Uses the leads database as the primary store (do_not_call column).
    For numbers not in the leads table, maintains a separate DNC log
    in data/dnc_log.db.
    """
    
    def __init__(self, leads_db_path: str = 'data/leads.db', dnc_log_path: str = 'data/dnc_log.db'):
        self.leads_db_path = leads_db_path
        self.dnc_log_path = dnc_log_path
        self._ensure_dnc_log_table()
    
    def _ensure_dnc_log_table(self):
        """Create standalone DNC log table if it doesn't exist."""
        try:
            conn = sqlite3.connect(self.dnc_log_path)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS dnc_entries (
                    phone_number TEXT PRIMARY KEY,
                    reason TEXT,
                    source_call_sid TEXT,
                    transcript_excerpt TEXT,
                    marked_at TEXT,
                    marked_by TEXT DEFAULT 'auto'
                )
            """)
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"[DNC] Failed to create DNC log table: {e}")
    
    def mark_dnc(self, phone_number: str, reason: str = 'explicit_request',
                 source_call_sid: str = '', transcript_excerpt: str = ''):
        """
        Mark a phone number as DNC in both the leads DB and the DNC log.
        
        Args:
            phone_number: E.164 format phone number
            reason: Why this was marked (e.g., 'explicit_stop_calling', 'dnc_request')
            source_call_sid: The call SID that triggered the DNC
            transcript_excerpt: What the merchant said
        """
        marked_at = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        
        # 1. Mark in leads database
        try:
            conn = sqlite3.connect(self.leads_db_path)
            conn.execute(
                "UPDATE leads SET do_not_call = 1, updated_at = ? WHERE phone_number = ?",
                (marked_at, phone_number)
            )
            rows_affected = conn.total_changes
            conn.commit()
            conn.close()
            if rows_affected > 0:
                logger.warning(f"[DNC] Marked {phone_number} as DNC in leads DB "
                             f"(reason={reason}, call={source_call_sid})")
        except Exception as e:
            logger.error(f"[DNC] Failed to mark {phone_number} in leads DB: {e}")
        
        # 2. Log in standalone DNC log (always, even if not in leads DB)
        try:
            conn = sqlite3.connect(self.dnc_log_path)
            conn.execute("""
                INSERT OR REPLACE INTO dnc_entries 
                (phone_number, reason, source_call_sid, transcript_excerpt, marked_at)
                VALUES (?, ?, ?, ?, ?)
            """, (phone_number, reason, source_call_sid, transcript_excerpt[:200], marked_at))
            conn.commit()
            conn.close()
            logger.info(f"[DNC] Logged DNC entry for {phone_number} in dnc_log.db")
        except Exception as e:
            logger.error(f"[DNC] Failed to log DNC entry: {e}")
    
    def is_dnc(self, phone_number: str) -> bool:
        """
        Check if a phone number is on the DNC list.
        Checks both leads DB and standalone DNC log.
        """
        # Check leads DB
        try:
            conn = sqlite3.connect(self.leads_db_path)
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT do_not_call FROM leads WHERE phone_number = ?",
                (phone_number,)
            ).fetchone()
            conn.close()
            if row and row['do_not_call']:
                return True
        except Exception as e:
            logger.debug(f"[DNC] Leads DB check failed: {e}")
        
        # Check standalone DNC log
        try:
            conn = sqlite3.connect(self.dnc_log_path)
            row = conn.execute(
                "SELECT 1 FROM dnc_entries WHERE phone_number = ?",
                (phone_number,)
            ).fetchone()
            conn.close()
            if row:
                return True
        except Exception as e:
            logger.debug(f"[DNC] DNC log check failed: {e}")
        
        return False
    
    def get_dnc_reason(self, phone_number: str) -> Optional[str]:
        """Get the reason a number was marked DNC."""
        try:
            conn = sqlite3.connect(self.dnc_log_path)
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT reason, source_call_sid, transcript_excerpt, marked_at "
                "FROM dnc_entries WHERE phone_number = ?",
                (phone_number,)
            ).fetchone()
            conn.close()
            if row:
                return (f"reason={row['reason']}, call={row['source_call_sid']}, "
                       f"marked={row['marked_at']}, said='{row['transcript_excerpt'][:60]}'")
        except Exception:
            pass
        return None
    
    def get_stats(self) -> dict:
        """Get DNC statistics."""
        stats = {'leads_db_dnc': 0, 'dnc_log_entries': 0}
        try:
            conn = sqlite3.connect(self.leads_db_path)
            row = conn.execute("SELECT COUNT(*) as c FROM leads WHERE do_not_call = 1").fetchone()
            stats['leads_db_dnc'] = row[0] if row else 0
            conn.close()
        except Exception:
            pass
        try:
            conn = sqlite3.connect(self.dnc_log_path)
            row = conn.execute("SELECT COUNT(*) as c FROM dnc_entries").fetchone()
            stats['dnc_log_entries'] = row[0] if row else 0
            conn.close()
        except Exception:
            pass
        return stats


# Singleton for use across modules
_dnc_manager: Optional[DNCManager] = None

def get_dnc_manager() -> DNCManager:
    """Get or create the singleton DNC manager."""
    global _dnc_manager
    if _dnc_manager is None:
        _dnc_manager = DNCManager()
    return _dnc_manager


def is_dnc_request(transcript: str) -> bool:
    """
    Quick check if a transcript line contains a DNC request.
    Uses simple substring matching for speed.
    For full regex-based detection, use conversational_intelligence.py.
    """
    lower = transcript.lower().strip()
    return any(phrase in lower for phrase in DNC_TRIGGER_PHRASES)
