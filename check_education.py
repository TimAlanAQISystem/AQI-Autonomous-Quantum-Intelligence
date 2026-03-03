import sys
import os
import sqlite3

# Add src to path
sys.path.insert(0, os.path.join(os.getcwd(), 'src'))
from education import AgentEducation

db_path = os.path.join(os.getcwd(), 'data', 'agent_x.db')

# Check existing knowledge
print("--- Current Knowledge Base ---")
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    try:
        c.execute("SELECT title, learned_at FROM knowledge_base ORDER BY learned_at DESC")
        rows = c.fetchall()
        if rows:
            for row in rows:
                print(f"- {row[0]} (Learned: {row[1]})")
        else:
            print("Knowledge base is empty.")
    except sqlite3.OperationalError:
        print("Table 'knowledge_base' does not exist yet.")
    conn.close()
else:
    print("Database not found.")

print("\n--- Running Education Session ---")
# Run education
try:
    edu = AgentEducation(db_path)
    edu.explore_and_learn()
except Exception as e:
    print(f"Error running education: {e}")
