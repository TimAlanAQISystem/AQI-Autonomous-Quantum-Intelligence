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

    print(f"\n===== AGENT X PERCEPTION FUSION DASHBOARD =====")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("===============================================\n")

    try:
        cursor = conn.cursor()
        
        # Check if perception_vector column exists
        cursor.execute("PRAGMA table_info(calls)")
        existing_cols = [row['name'] for row in cursor.fetchall()]

        if 'perception_vector' not in existing_cols:
            print("❌ 'perception_vector' column NOT FOUND in 'calls' table.\n")
            print("Running database schema update locally...")
            try:
                cursor.execute("ALTER TABLE calls ADD COLUMN perception_vector TEXT")
                cursor.execute("ALTER TABLE calls ADD COLUMN inbound_metrics TEXT")
                conn.commit()
                print("✅ Schema updated successfully: created new columns.")
            except Exception as e:
                print(f"⚠️ Failed to update schema: {e}")
                return

        # 1. Overall Stats
        cursor.execute("SELECT count(*) as total FROM calls")
        row = cursor.fetchone()
        total_calls = row['total'] if row else 0

        cursor.execute("SELECT count(*) as fused FROM calls WHERE perception_vector IS NOT NULL")
        row = cursor.fetchone()
        fused_calls = row['fused'] if row else 0
        
        percent = (fused_calls/total_calls*100) if total_calls > 0 else 0
        print(f"TOTAL CALLS: {total_calls}")
        print(f"FUSED CALLS: {fused_calls} ({percent:.1f}%)\n")

        if fused_calls == 0:
            print("⚠️ No perception data recorded yet. Make some test calls!")
            return

        # 2. Mode Distribution
        print("--- PERCEPTION MODES ---")
        print(f"{'Mode':<20} | {'Count':<10} | {'Avg Health':<10}")
        print("-" * 45)
        
        cursor.execute("""
            SELECT 
                json_extract(perception_vector, '$.mode') as mode,
                count(*) as count,
                avg(json_extract(perception_vector, '$.scores.combined_health_score')) as avg_health
            FROM calls 
            WHERE perception_vector IS NOT NULL
            GROUP BY 1
            ORDER BY 2 DESC
        """)
        
        rows = cursor.fetchall()
        for row in rows:
            mode = row['mode'] or 'unknown'
            count = row['count']
            avg_health = row['avg_health'] or 0.0
            print(f"{mode:<20} | {count:<10} | {avg_health:<10.2f}")
        print("\n")

        # 3. Health Status
        print("--- HEALTH STATUS ---")
        print(f"{'Health':<15} | {'Count':<10}")
        print("-" * 30)
            
        cursor.execute("""
            SELECT 
                json_extract(perception_vector, '$.health') as health,
                count(*) as count
            FROM calls 
            WHERE perception_vector IS NOT NULL
            GROUP BY 1
            ORDER BY 2 DESC
        """)
        
        rows = cursor.fetchall()
        for row in rows:
            health = row['health'] or 'unknown'
            count = row['count']
            print(f"{health:<15} | {count:<10}")
        print("\n")

    except Exception as e:
        print(f"❌ Error querying database: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    run_dashboard()
