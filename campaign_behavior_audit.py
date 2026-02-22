# campaign_behavior_audit.py

import sqlite3
import json
import argparse
import os
from datetime import datetime, timedelta

DB_PATH = "data/call_capture.db"


def load_calls(days: int):
    if not os.path.exists(DB_PATH):
        print(f"Warning: Database not found at {DB_PATH}")
        return []

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    since = (datetime.utcnow() - timedelta(days=days)).isoformat()

    try:
        # Check if behavioral_vector column exists first to avoid crash on old schemas
        cur.execute("PRAGMA table_info(calls)")
        cols = [c[1] for c in cur.fetchall()]
        
        has_behavioral = 'behavioral_vector' in cols
        has_perception = 'perception_vector' in cols
        
        if not has_behavioral:
            print("Warning: behavioral_vector column missing. Run schema migration.")
            return []

        query = """
            SELECT call_sid, start_time, end_time, final_outcome, behavioral_vector, perception_vector
            FROM calls
            WHERE start_time >= ?
            ORDER BY start_time DESC
        """
        # Note: older code might use 'id', 'started_at', 'ended_at', 'outcome'
        # Let's align with call_data_capture schema:
        # call_sid, start_time, end_time, final_outcome...
        
        cur.execute(query, (since,))
        rows = cur.fetchall()
    except Exception as e:
        print(f"Error querying database: {e}")
        rows = []
    finally:
        conn.close()
    
    return rows


def parse_vector(raw):
    if not raw:
        return {}
    if isinstance(raw, dict): 
        return raw
    try:
        return json.loads(raw)
    except:
        return {}


def summarize(rows):
    total = len(rows)
    stalled = 0
    collapsed = 0
    high_friction = 0
    recovering = 0
    governor_actions = {
        "none": 0,
        "nudge": 0,
        "flag": 0,
        "soft_kill": 0,
        "hard_kill": 0,
        "cooldown": 0,
    }

    worst_calls = []

    for row in rows:
        # Adjust unpacking based on query columns
        call_id, started, ended, outcome, bvec_raw, pvec_raw = row
        bvec = parse_vector(bvec_raw)
        pvec = parse_vector(pvec_raw)

        mode = bvec.get("mode", "unknown")
        health = bvec.get("health", "unknown")
        drift = bvec.get("trajectory_drift", 0)
        velocity = bvec.get("trajectory_velocity", 0)
        # Governor action might be stored as string in behavioral vector if we put it there
        action = bvec.get("governor_action", "none").lower()

        # Count modes
        if mode == "stalled":
            stalled += 1
        if mode == "collapsed":
            collapsed += 1
        if mode == "high_friction":
            high_friction += 1
        if mode == "recovering":
            recovering += 1

        # Count governor actions
        if action in governor_actions:
            governor_actions[action] += 1
        else:
            # handle unknown actions gracefully
            if action not in governor_actions:
                 governor_actions[action] = 0
            governor_actions[action] += 1

        # Track worst calls
        # Criteria: collapsed, stalled, high friction, or any governor kill
        if health == "failed" or mode in ["collapsed", "stalled", "high_friction"] or "kill" in action:
            worst_calls.append({
                "call_id": call_id,
                "mode": mode,
                "health": health,
                "drift": drift,
                "velocity": velocity,
                "action": action,
                "outcome": outcome,
                "started": started,
            })

    # Sort worst calls by severity
    # Priority: Hard Kill > Collapsed > Failed Health > High Friction > Stalled
    def severity_score(c):
        score = 0
        if "hard_kill" in c["action"]: score += 100
        if c["mode"] == "collapsed": score += 50
        if c["health"] == "failed": score += 25
        if c["mode"] == "stalled": score += 10
        if c["mode"] == "high_friction": score += 5
        return score + abs(c["drift"])

    worst_calls.sort(key=severity_score, reverse=True)

    return {
        "total": total,
        "stalled": stalled,
        "collapsed": collapsed,
        "high_friction": high_friction,
        "recovering": recovering,
        "governor_actions": governor_actions,
        "worst_calls": worst_calls[:10],
    }


def print_report(summary):
    print("\n=== CAMPAIGN BEHAVIORAL AUDIT ===")
    print(f"Total Calls: {summary['total']}")
    print(f"Stalled: {summary['stalled']}")
    print(f"Collapsed: {summary['collapsed']}")
    print(f"High Friction: {summary['high_friction']}")
    print(f"Recovering: {summary['recovering']}")

    print("\n--- Governor Actions ---")
    for k, v in summary["governor_actions"].items():
        if v > 0:
            print(f"{k.upper():12}: {v}")

    print("\n--- Top 10 Worst Calls ---")
    if not summary["worst_calls"]:
        print("None found.")
    for c in summary["worst_calls"]:
        print(f"{c['call_id'][:8]}... | {c['mode']} | {c['health']} | drift={c['drift']:.2f} | vel={c['velocity']:.2f} | action={c['action']} | outcome={c['outcome']}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=7, help="How many days back to audit")
    args = parser.parse_args()

    rows = load_calls(args.days)
    summary = summarize(rows)
    print_report(summary)


if __name__ == "__main__":
    main()
