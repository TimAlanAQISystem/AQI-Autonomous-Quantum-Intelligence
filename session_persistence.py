"""
Session Persistence Manager
============================

Provides session persistence across system restarts using SQLite.

Key Features:
- Auto-save sessions on state transitions
- Recovery of active sessions on startup
- Session history tracking
- Business continuity during crashes/maintenance
- Performance monitoring for operations

Usage:
    manager = SessionPersistenceManager()
    
    # Save session
    manager.save_session(session)
    
    # Load session
    session = manager.load_session(session_id)
    
    # Recover active sessions after restart
    active_sessions = manager.recover_active_sessions()
"""

import sqlite3
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

# Import performance monitoring
try:
    from performance_monitor import (
        monitor_session_save,
        monitor_session_load,
        monitor_session_recovery,
        monitor_conversation_save
    )
    PERFORMANCE_MONITORING_ENABLED = True
except ImportError:
    # Fallback: no-op decorators if performance_monitor not available
    def monitor_session_save(func):
        return func
    def monitor_session_load(func):
        return func
    def monitor_session_recovery(func):
        return func
    def monitor_conversation_save(func):
        return func
    PERFORMANCE_MONITORING_ENABLED = False
from pathlib import Path

# Import SessionStateMachine for type hints (not Session)
try:
    from alan_state_machine import SessionStateMachine, SessionState, SystemState
except ImportError:
    # Fallback if not available
    SessionStateMachine = Any
    SessionState = Any
    SystemState = Any

logger = logging.getLogger("SessionPersistence")


class SessionPersistenceManager:
    """
    Manages session persistence across system restarts.
    
    Architecture:
    - SQLite database for session storage
    - JSON serialization for session state
    - Automatic save on state transitions
    - Recovery mechanism for active sessions
    """
    
    def __init__(self, db_path: str = "alan_sessions.db"):
        """
        Initialize session persistence manager.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._init_database()
        logger.info(f"Session persistence initialized: {db_path}")
    
    def _init_database(self):
        """Create database schema if not exists"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Sessions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                user_id TEXT,
                state TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                terminated_at TEXT,
                metadata TEXT,
                is_active INTEGER DEFAULT 1
            )
        ''')
        
        # Session events table (audit trail)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS session_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                from_state TEXT,
                to_state TEXT,
                timestamp TEXT NOT NULL,
                details TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            )
        ''')
        
        # Conversation history table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversation_turns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                speaker TEXT NOT NULL,
                text TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                metadata TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            )
        ''')
        
        # Indexes for performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_session_active ON sessions(is_active)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_session_state ON sessions(state)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_events_session ON session_events(session_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_conversation_session ON conversation_turns(session_id)')
        
        conn.commit()
        conn.close()
        
        logger.info("Database schema initialized")
    
    @monitor_session_save
    def save_session(self, session) -> bool:
        """
        Save session to database.
        
        Args:
            session: SessionStateMachine object to save
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Serialize metadata to JSON
            metadata_json = json.dumps(session.metadata)
            
            # Check if session exists
            cursor.execute('SELECT session_id FROM sessions WHERE session_id = ?', (session.session_id,))
            exists = cursor.fetchone()
            
            now = datetime.now().isoformat()
            
            if exists:
                # Update existing session
                cursor.execute('''
                    UPDATE sessions 
                    SET state = ?, updated_at = ?, metadata = ?, is_active = ?
                    WHERE session_id = ?
                ''', (
                    session.state.value,
                    now,
                    metadata_json,
                    1 if session.state != SessionState.SESSION_TERMINATED else 0,
                    session.session_id
                ))
                logger.debug(f"Updated session {session.session_id}")
            else:
                # Insert new session
                cursor.execute('''
                    INSERT INTO sessions (session_id, user_id, state, created_at, updated_at, metadata, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    session.session_id,
                    session.user_id,
                    session.state.value,
                    now,
                    now,
                    metadata_json,
                    1
                ))
                logger.debug(f"Inserted session {session.session_id}")
            
            conn.commit()
            conn.close()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to save session {session.session_id}: {e}")
            return False
    
    @monitor_session_load
    def load_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Load session from database.
        
        Args:
            session_id: ID of session to load
            
        Returns:
            Session data dict or None if not found
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT session_id, user_id, state, created_at, updated_at, 
                       terminated_at, metadata, is_active
                FROM sessions 
                WHERE session_id = ?
            ''', (session_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                return None
            
            # Parse row into dict
            session_data = {
                'session_id': row[0],
                'user_id': row[1],
                'state': row[2],
                'created_at': row[3],
                'updated_at': row[4],
                'terminated_at': row[5],
                'metadata': json.loads(row[6]) if row[6] else {},
                'is_active': bool(row[7])
            }
            
            logger.debug(f"Loaded session {session_id}")
            return session_data
            
        except Exception as e:
            logger.error(f"Failed to load session {session_id}: {e}")
            return None
    
    @monitor_session_recovery
    def recover_active_sessions(self) -> List[Dict[str, Any]]:
        """
        Recover all active sessions (for system restart).
        
        Returns:
            List of active session data dicts
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT session_id, user_id, state, created_at, updated_at, 
                       terminated_at, metadata, is_active
                FROM sessions 
                WHERE is_active = 1 AND state != 'session_terminated'
                ORDER BY updated_at DESC
            ''')
            
            rows = cursor.fetchall()
            conn.close()
            
            sessions = []
            for row in rows:
                session_data = {
                    'session_id': row[0],
                    'user_id': row[1],
                    'state': row[2],
                    'created_at': row[3],
                    'updated_at': row[4],
                    'terminated_at': row[5],
                    'metadata': json.loads(row[6]) if row[6] else {},
                    'is_active': bool(row[7])
                }
                sessions.append(session_data)
            
            logger.info(f"Recovered {len(sessions)} active sessions")
            return sessions
            
        except Exception as e:
            logger.error(f"Failed to recover active sessions: {e}")
            return []
    
    def log_session_event(self, session_id: str, event_type: str, 
                         from_state: Optional[str] = None,
                         to_state: Optional[str] = None,
                         details: Optional[Dict[str, Any]] = None) -> bool:
        """
        Log session state transition or event.
        
        Args:
            session_id: ID of session
            event_type: Type of event (transition, error, etc.)
            from_state: Previous state (if transition)
            to_state: New state (if transition)
            details: Additional event details
            
        Returns:
            True if logged successfully
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO session_events (session_id, event_type, from_state, to_state, timestamp, details)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                session_id,
                event_type,
                from_state,
                to_state,
                datetime.now().isoformat(),
                json.dumps(details) if details else None
            ))
            
            conn.commit()
            conn.close()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to log session event: {e}")
            return False
    
    @monitor_conversation_save
    def save_conversation_turn(self, session_id: str, speaker: str, text: str,
                              metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Save conversation turn to database.
        
        Args:
            session_id: ID of session
            speaker: Who spoke (User/Alan)
            text: What was said
            metadata: Additional turn metadata
            
        Returns:
            True if saved successfully
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO conversation_turns (session_id, speaker, text, timestamp, metadata)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                session_id,
                speaker,
                text,
                datetime.now().isoformat(),
                json.dumps(metadata) if metadata else None
            ))
            
            conn.commit()
            conn.close()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to save conversation turn: {e}")
            return False
    
    def get_conversation_history(self, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get conversation history for session.
        
        Args:
            session_id: ID of session
            limit: Maximum number of turns to retrieve
            
        Returns:
            List of conversation turns
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT speaker, text, timestamp, metadata
                FROM conversation_turns
                WHERE session_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (session_id, limit))
            
            rows = cursor.fetchall()
            conn.close()
            
            turns = []
            for row in rows:
                turn = {
                    'speaker': row[0],
                    'text': row[1],
                    'timestamp': row[2],
                    'metadata': json.loads(row[3]) if row[3] else {}
                }
                turns.append(turn)
            
            # Reverse to chronological order
            turns.reverse()
            
            return turns
            
        except Exception as e:
            logger.error(f"Failed to get conversation history: {e}")
            return []
    
    def terminate_session(self, session_id: str) -> bool:
        """
        Mark session as terminated.
        
        Args:
            session_id: ID of session to terminate
            
        Returns:
            True if terminated successfully
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE sessions 
                SET is_active = 0, 
                    terminated_at = ?,
                    state = 'session_terminated'
                WHERE session_id = ?
            ''', (datetime.now().isoformat(), session_id))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Terminated session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to terminate session {session_id}: {e}")
            return False
    
    def cleanup_old_sessions(self, days: int = 30) -> int:
        """
        Clean up old terminated sessions.
        
        Args:
            days: Number of days to keep terminated sessions
            
        Returns:
            Number of sessions deleted
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            from datetime import timedelta
            cutoff_date = datetime.now() - timedelta(days=days)
            cutoff_str = cutoff_date.isoformat()
            
            # Delete old terminated sessions
            cursor.execute('''
                DELETE FROM sessions 
                WHERE is_active = 0 
                AND terminated_at < ?
            ''', (cutoff_str,))
            
            deleted = cursor.rowcount
            
            # Cleanup orphaned events and conversation turns
            cursor.execute('''
                DELETE FROM session_events 
                WHERE session_id NOT IN (SELECT session_id FROM sessions)
            ''')
            
            cursor.execute('''
                DELETE FROM conversation_turns 
                WHERE session_id NOT IN (SELECT session_id FROM sessions)
            ''')
            
            conn.commit()
            conn.close()
            
            logger.info(f"Cleaned up {deleted} old sessions")
            return deleted
            
        except Exception as e:
            logger.error(f"Failed to cleanup old sessions: {e}")
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get database statistics.
        
        Returns:
            Dict with session statistics
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            stats = {}
            
            # Total sessions
            cursor.execute('SELECT COUNT(*) FROM sessions')
            stats['total_sessions'] = cursor.fetchone()[0]
            
            # Active sessions
            cursor.execute('SELECT COUNT(*) FROM sessions WHERE is_active = 1')
            stats['active_sessions'] = cursor.fetchone()[0]
            
            # Total conversation turns
            cursor.execute('SELECT COUNT(*) FROM conversation_turns')
            stats['total_turns'] = cursor.fetchone()[0]
            
            # Total events
            cursor.execute('SELECT COUNT(*) FROM session_events')
            stats['total_events'] = cursor.fetchone()[0]
            
            # Database size
            db_path = Path(self.db_path)
            if db_path.exists():
                stats['db_size_mb'] = db_path.stat().st_size / (1024 * 1024)
            
            conn.close()
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {}


# Global persistence manager instance
_persistence_manager = None


def get_persistence_manager(db_path: str = "alan_sessions.db") -> SessionPersistenceManager:
    """
    Get or create global persistence manager instance.
    
    Args:
        db_path: Path to SQLite database file
        
    Returns:
        SessionPersistenceManager instance
    """
    global _persistence_manager
    
    if _persistence_manager is None:
        _persistence_manager = SessionPersistenceManager(db_path)
    
    return _persistence_manager
