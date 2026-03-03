
import sqlite3
import os
from pathlib import Path

DB_PATH = Path('data/leads.db')

def check_failed_leads():
    if not DB_PATH.exists():
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print("Checking for recent failed leads...")
    
    # query for leads with attempts > 0 and outcome != 'consolidated' or 'success'
    # we want to see what the failed statuses are.
    query = """
        SELECT id, phone_number, name, attempts, max_attempts, outcome, last_attempt, outcome_details
        FROM leads
        WHERE attempts > 0
        AND outcome NOT IN ('success', 'appointment_set', 'interested')
        ORDER BY last_attempt DESC
        LIMIT 10
    """
    
    cursor.execute(query)
    rows = cursor.fetchall()
    
    if not rows:
        print("No failed leads found.")
    else:
        print(f"Found {len(rows)} recent failed leads:")
        for row in rows:
            print(f"ID: {row['id']}, Phone: {row['phone_number']}, Attempts: {row['attempts']}/{row['max_attempts']}, Outcome: {row['outcome']}, Last Attempt: {row['last_attempt']}")

    conn.close()

if __name__ == "__main__":
    check_failed_leads()
