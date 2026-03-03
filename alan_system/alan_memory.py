# alan_memory.py

import json
import os
import sqlite3
from datetime import datetime
from typing import Optional, List, Dict

from alan_config import JSON_MEMORY_PATH, SQLITE_DB_PATH, LOGS_DIR


# ---------- JSON MEMORY ----------

def _ensure_json_memory():
    if not os.path.exists(JSON_MEMORY_PATH):
        with open(JSON_MEMORY_PATH, "w", encoding="utf-8") as f:
            json.dump({"facts": {}}, f, indent=2)


def load_json_memory() -> Dict:
    _ensure_json_memory()
    with open(JSON_MEMORY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json_memory(data: Dict):
    with open(JSON_MEMORY_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def remember_fact(key: str, value: str):
    data = load_json_memory()
    data.setdefault("facts", {})
    data["facts"][key] = value
    save_json_memory(data)


def get_fact(key: str) -> Optional[str]:
    data = load_json_memory()
    return data.get("facts", {}).get(key)


def list_facts() -> Dict[str, str]:
    data = load_json_memory()
    return data.get("facts", {})


# ---------- SQLITE SESSION MEMORY ----------

def _get_conn():
    conn = sqlite3.connect(SQLITE_DB_PATH)
    return conn


def init_db():
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at TEXT,
            ended_at TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            role TEXT,
            content TEXT,
            created_at TEXT,
            FOREIGN KEY(session_id) REFERENCES sessions(id)
        )
    """)
    conn.commit()
    conn.close()


def start_session() -> int:
    conn = _get_conn()
    cur = conn.cursor()
    now = datetime.utcnow().isoformat()
    cur.execute("INSERT INTO sessions (started_at, ended_at) VALUES (?, ?)", (now, None))
    session_id = cur.lastrowid
    conn.commit()
    conn.close()
    return session_id


def end_session(session_id: int):
    conn = _get_conn()
    cur = conn.cursor()
    now = datetime.utcnow().isoformat()
    cur.execute("UPDATE sessions SET ended_at = ? WHERE id = ?", (now, session_id))
    conn.commit()
    conn.close()


def add_message(session_id: int, role: str, content: str):
    conn = _get_conn()
    cur = conn.cursor()
    now = datetime.utcnow().isoformat()
    cur.execute(
        "INSERT INTO messages (session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
        (session_id, role, content, now)
    )
    conn.commit()
    conn.close()


def get_session_messages(session_id: int) -> List[Dict]:
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("SELECT role, content, created_at FROM messages WHERE session_id = ? ORDER BY id", (session_id,))
    rows = cur.fetchall()
    conn.close()
    return [{"role": r[0], "content": r[1], "created_at": r[2]} for r in rows]


# ---------- LOG FILES ----------

def get_session_log_path(session_id: int) -> str:
    return os.path.join(LOGS_DIR, f"session_{session_id}.log")


def append_to_log(session_id: int, role: str, content: str):
    path = get_session_log_path(session_id)
    ts = datetime.utcnow().isoformat()
    line = f"[{ts}] {role.upper()}: {content}\n"
    with open(path, "a", encoding="utf-8") as f:
        f.write(line)