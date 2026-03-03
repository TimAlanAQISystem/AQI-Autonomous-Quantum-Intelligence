# evolution_analyze.py

import sqlite3
import argparse
from evolution_engine import EvolutionEngine
import json

DB_PATH = "call_capture.db"

def load_rows(days: int):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT id, outcome, behavioral_vector, perception_vector, coaching_tags
            FROM calls
            WHERE started_at >= datetime('now', ?)
        """, (f'-{days} days',))
        rows = cur.fetchall()
    except sqlite3.OperationalError:
        # Fallback if coaching_tags column doesn't exist yet
        print("Warning: 'coaching_tags' column might be missing. Returning partial data or empty.")
        rows = []
    conn.close()
    return rows

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=7)
    args = parser.parse_args()

    rows = load_rows(args.days)
    if not rows:
        print("No data found (or schema outdated). Run some calls first.")
        return

    engine = EvolutionEngine()
    result = engine.analyze_calls(rows)

    print("\n=== EVOLUTION ANALYSIS ===")
    print("Tag frequencies:")
    for tag, count in result["tags_counter"].most_common():
        print(f"- {tag}: {count}")

    print("\nRecommendations:")
    for k, items in result["recommendations"].items():
        print(f"\n[{k.upper()}]")
        if not items:
            print("  None.")
        else:
            for r in items:
                print(f"  - {r}")

if __name__ == "__main__":
    main()
