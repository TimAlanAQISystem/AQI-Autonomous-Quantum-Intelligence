
import sqlite3
import logging
from pathlib import Path
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB_PATH = Path('data/leads.db')

def reset_recent_leads():
    if not DB_PATH.exists():
        logger.error(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    today_str = datetime.now().strftime("%Y-%m-%d")
    
    # Reset leads executed today that are not successful
    # We target leads with attempts > 0 and last_attempt effectively today.
    # The timestamps in the DB are ISO format "YYYY-MM-DDTHH:MM:SS.mmmmmm"
    
    logger.info(f"Resetting leads attempted on {today_str}...")

    # Select count first
    cursor.execute(f"""
        SELECT count(*) FROM leads 
        WHERE last_attempt LIKE '{today_str}%'
        AND outcome NOT IN ('success', 'appointment_set', 'interested', 'do_not_call')
    """)
    count = cursor.fetchone()[0]
    
    if count == 0:
        logger.info("No leads found to reset.")
        conn.close()
        return

    logger.info(f"Found {count} leads to reset.")

    # Execute update
    cursor.execute(f"""
        UPDATE leads
        SET attempts = 0, 
            outcome = 'pending',
            last_attempt = NULL,
            outcome_details = NULL
        WHERE last_attempt LIKE '{today_str}%'
        AND outcome NOT IN ('success', 'appointment_set', 'interested', 'do_not_call')
    """)
    
    conn.commit()
    logger.info(f"Successfully reset {cursor.rowcount} leads.")
    conn.close()

if __name__ == "__main__":
    reset_recent_leads()
