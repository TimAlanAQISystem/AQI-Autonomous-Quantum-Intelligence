# Agent Communication and Experience Sharing System
# Enables inter-agent learning and coordination

import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Any

class AgentCommunicationHub:
    def __init__(self, db_path: str = "agent_experiences.db"):
        self.db_path = db_path
        self.setup_database()

    def setup_database(self):
        """Initialize shared experience database"""
        conn = sqlite3.connect(self.db_path)
        # Enable WAL mode for concurrency
        conn.execute('PRAGMA journal_mode=WAL;')
        cursor = conn.cursor()

        # Shared experiences table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS shared_experiences (
                id INTEGER PRIMARY KEY,
                agent_id TEXT,
                experience_type TEXT,
                merchant_data TEXT,
                outcome TEXT,
                lessons_learned TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Agent coordination table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS agent_coordination (
                id INTEGER PRIMARY KEY,
                from_agent TEXT,
                to_agent TEXT,
                message_type TEXT,
                message_data TEXT,
                priority INTEGER DEFAULT 1,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        conn.commit()
        conn.close()

    def share_experience(self, agent_id: str, experience_type: str,
                        merchant_data: Dict, outcome: str, lessons: str):
        """Share an experience with other agents"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO shared_experiences
            (agent_id, experience_type, merchant_data, outcome, lessons_learned)
            VALUES (?, ?, ?, ?, ?)
        ''', (agent_id, experience_type, json.dumps(merchant_data),
              outcome, lessons))

        conn.commit()
        conn.close()

    def get_shared_experiences(self, experience_type: str = None,
                              limit: int = 10) -> List[Dict]:
        """Retrieve shared experiences for learning"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if experience_type:
            cursor.execute('''
                SELECT * FROM shared_experiences
                WHERE experience_type = ?
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (experience_type, limit))
        else:
            cursor.execute('''
                SELECT * FROM shared_experiences
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (limit,))

        experiences = []
        for row in cursor.fetchall():
            experiences.append({
                'id': row[0],
                'agent_id': row[1],
                'experience_type': row[2],
                'merchant_data': json.loads(row[3]),
                'outcome': row[4],
                'lessons_learned': row[5],
                'timestamp': row[6]
            })

        conn.close()
        return experiences

    def send_message(self, from_agent: str, to_agent: str,
                    message_type: str, message_data: Dict, priority: int = 1):
        """Send coordination message between agents"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO agent_coordination
            (from_agent, to_agent, message_type, message_data, priority)
            VALUES (?, ?, ?, ?, ?)
        ''', (from_agent, to_agent, message_type, json.dumps(message_data), priority))

        conn.commit()
        conn.close()

    def get_messages(self, to_agent: str) -> List[Dict]:
        """Retrieve messages for an agent"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM agent_coordination
            WHERE to_agent = ? OR to_agent = 'all'
            ORDER BY priority DESC, timestamp DESC
        ''', (to_agent,))

        messages = []
        for row in cursor.fetchall():
            messages.append({
                'id': row[0],
                'from_agent': row[1],
                'to_agent': row[2],
                'message_type': row[3],
                'message_data': json.loads(row[4]),
                'priority': row[5],
                'timestamp': row[6]
            })

        conn.close()
        return messages

# Global communication hub instance
comm_hub = AgentCommunicationHub()