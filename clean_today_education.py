import sqlite3
import os
import datetime

db_path = os.path.join(os.getcwd(), 'data', 'agent_x.db')
conn = sqlite3.connect(db_path)
c = conn.cursor()

# Delete entries learned today to force re-fetch with new logic
today = datetime.datetime.now().strftime('%Y-%m-%d')
print(f"Cleaning entries for {today}...")
c.execute("DELETE FROM knowledge_base WHERE learned_at LIKE ?", (f"{today}%",))
deleted = c.rowcount
print(f"Deleted {deleted} entries.")

conn.commit()
conn.close()
