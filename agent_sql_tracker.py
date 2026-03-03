import sqlite3
import os
import logging
from datetime import datetime

# Database path
DB_PATH = os.path.join(os.path.dirname(__file__), 'database', 'alan_communication.db')

def init_db():
    """Initialize the SQL Command Center."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create the table as designed
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Alan_Communication_Logs (
        call_sid VARCHAR(50) PRIMARY KEY,
        merchant_name VARCHAR(255),
        phone_number VARCHAR(20),
        status VARCHAR(20), 
        duration_seconds INT,
        recording_url TEXT,
        stealth_logic_version VARCHAR(20), 
        vulture_reattempts INT DEFAULT 0,
        merchant_response_sentiment FLOAT, 
        first_account_secured BOOLEAN DEFAULT 0,
        twilio_error_code INT,
        hangup_source VARCHAR(20),
        sequence_number INT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    ''')
    
    # Simple migration for existing DB
    try:
        cursor.execute("ALTER TABLE Alan_Communication_Logs ADD COLUMN twilio_error_code INT")
    except sqlite3.OperationalError:
        pass # Column likely exists

    try:
        cursor.execute("ALTER TABLE Alan_Communication_Logs ADD COLUMN hangup_source VARCHAR(20)")
    except sqlite3.OperationalError:
        pass # Column likely exists

    try:
        cursor.execute("ALTER TABLE Alan_Communication_Logs ADD COLUMN sequence_number INT")
    except sqlite3.OperationalError:
        pass # Column likely exists

    conn.commit()
    conn.close()
    logging.info(f"[SQL] Initialized Alan_Communication_Logs at {DB_PATH}")

def log_communication_event(call_sid, data):
    """
    Upsert communication log.
    If call_sid exists, update provided fields.
    If not, insert new record.
    """
    if not call_sid:
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check existence
    cursor.execute("SELECT call_sid FROM Alan_Communication_Logs WHERE call_sid = ?", (call_sid,))
    exists = cursor.fetchone()
    
    fields = []
    values = []
    
    # Map input data to columns
    # Allowed columns keys in 'data' dict should match table columns
    allowed_cols = [
        'merchant_name', 'phone_number', 'status', 'duration_seconds', 
        'recording_url', 'stealth_logic_version', 'vulture_reattempts', 
        'merchant_response_sentiment', 'first_account_secured',
        'twilio_error_code', 'hangup_source', 'sequence_number'
    ]
    
    if exists:
        # Update
        update_parts = []
        update_values = []
        for k, v in data.items():
            if k in allowed_cols:
                update_parts.append(f"{k} = ?")
                update_values.append(v)
        
        if update_parts:
            update_values.append(call_sid)
            sql = f"UPDATE Alan_Communication_Logs SET {', '.join(update_parts)} WHERE call_sid = ?"
            cursor.execute(sql, update_values)
    else:
        # Insert
        insert_cols = ['call_sid']
        insert_vals = [call_sid]
        placeholders = ['?']
        
        for k, v in data.items():
            if k in allowed_cols:
                insert_cols.append(k)
                insert_vals.append(v)
                placeholders.append('?')
        
        sql = f"INSERT INTO Alan_Communication_Logs ({', '.join(insert_cols)}) VALUES ({', '.join(placeholders)})"
        cursor.execute(sql, insert_vals)
        
    conn.commit()
    conn.close()
    # logging.info(f"[SQL] Logged event for {call_sid}")

# Auto-initialize on import
init_db()
