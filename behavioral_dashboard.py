import sqlite3
import json
import os
from datetime import datetime

# Configuration
DB_PATH = "data/call_capture.db"

def get_db_connection():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return None
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        print(f"Failed to connect to DB: {e}")
        return None

def run_dashboard():
    conn = get_db_connection()
    if not conn:
        return

    print(f"\n===== AGENT X BEHAVIORAL DASHBOARD =====")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("========================================\n")

    try:
        cursor = conn.cursor()
        
        # Check if behavioral_vector column exists
        cursor.execute("PRAGMA table_info(calls)")
        existing_cols = [row['name'] for row in cursor.fetchall()]

        if 'behavioral_vector' not in existing_cols:
            print("❌ 'behavioral_vector' column NOT FOUND. Run schema update.")
            return

        # 1. Overall Stats
        cursor.execute("SELECT count(*) as fused FROM calls WHERE behavioral_vector IS NOT NULL")
        row = cursor.fetchone()
        fused_calls = row['fused'] if row else 0
        
        print(f"BEHAVIORAL FUSED CALLS: {fused_calls}\n")

        if fused_calls == 0:
            print("⚠️ No behavioral data recorded yet. Make some test calls!")
            return

        # 2. Behavioral Modes
        print("--- BEHAVIORAL MODES ---")
        print(f"{'Mode':<20} | {'Count':<10} | {'Avg Velocity':<15}")
        print("-" * 55)
        
        cursor.execute("""
            SELECT 
                json_extract(behavioral_vector, '$.mode') as mode,
                count(*) as count,
                avg(json_extract(behavioral_vector, '$.trajectory_velocity')) as avg_vel
            FROM calls 
            WHERE behavioral_vector IS NOT NULL
            GROUP BY 1
            ORDER BY 2 DESC
        """)
        
        rows = cursor.fetchall()
        for row in rows:
            mode = row['mode'] or 'unknown'
            count = row['count']
            avg_vel = row['avg_vel'] or 0.0
            print(f"{mode:<20} | {count:<10} | {avg_vel:<15.2f}")
        print("\n")

        # 3. Behavioral Health
        print("--- BEHAVIORAL HEALTH ---")
        print(f"{'Health':<15} | {'Count':<10}")
        print("-" * 30)
            
        cursor.execute("""
            SELECT 
                json_extract(behavioral_vector, '$.health') as health,
                count(*) as count
            FROM calls 
            WHERE behavioral_vector IS NOT NULL
            GROUP BY 1
            ORDER BY 2 DESC
        """)
        
        rows = cursor.fetchall()
        for row in rows:
            health = row['health'] or 'unknown'
            count = row['count']
            print(f"{health:<15} | {count:<10}")
        print("\n")

        # 4. Objection Impact
        print("--- OBJECTION IMPACT ---")
        print(f"{'Objection Count':<20} | {'Call Count':<10} | {'Avg Velocity':<12}")
        print("-" * 50)
        cursor.execute("""
            SELECT 
                json_extract(behavioral_vector, '$.objection_count') as objc,
                count(*) as count,
                avg(json_extract(behavioral_vector, '$.trajectory_velocity')) as avg_vel
            FROM calls 
            WHERE behavioral_vector IS NOT NULL
            GROUP BY 1
            ORDER BY 1
        """)
        rows = cursor.fetchall()
        for row in rows:
            objc = row['objc']
            count = row['count']
            avg_vel = row['avg_vel'] or 0.0
            print(f"{objc:<20} | {count:<10} | {avg_vel:<12.2f}")
        print("\n")

        # 5. Governor Actions
        print("--- GOVERNOR ACTIONS ---")
        print(f"{'Action':<20} | {'Count':<10}")
        print("-" * 35)
        cursor.execute("""
            SELECT 
                json_extract(behavioral_vector, '$.governor_action') as action,
                count(*) as count
            FROM calls 
            WHERE behavioral_vector IS NOT NULL
            GROUP BY 1
            ORDER BY 2 DESC
        """)
        rows = cursor.fetchall()
        for row in rows:
            action = row['action'] or 'none'
            count = row['count']
            print(f"{action:<20} | {count:<10}")
        print("\n")


    except Exception as e:
        print(f"❌ Error querying database: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    run_dashboard()
