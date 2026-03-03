"""
Evolution Data Sanitization Script
===================================
Fixes poisoned outcome data in call_capture.db:
1. Reclassifies "unknown" outcomes using turn-count heuristics
2. Overrides IVR-poisoned "kept_engaged" to "voicemail_ivr"
3. Validates coaching score presence

Run: .\.venv\Scripts\python.exe sanitize_evolution_data.py
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'call_capture.db')

def main():
    if not os.path.exists(DB_PATH):
        print(f"ERROR: Database not found at {DB_PATH}")
        return
    
    db = sqlite3.connect(DB_PATH)
    cur = db.cursor()
    
    print("=" * 60)
    print("EVOLUTION DATA SANITIZATION")
    print("=" * 60)
    
    # --- Before ---
    print("\n[BEFORE] Outcome Distribution:")
    rows = cur.execute("SELECT final_outcome, COUNT(*) as cnt FROM calls GROUP BY final_outcome ORDER BY cnt DESC").fetchall()
    for r in rows:
        print(f"  {str(r[0]):30s} : {r[1]}")
    
    # --- 1. Fix Unknown Outcomes ---
    print("\n[STEP 1] Reclassifying 'unknown' outcomes...")
    unknowns = cur.execute("""
        SELECT c.call_sid, 
               (SELECT COUNT(*) FROM turns t WHERE t.call_sid = c.call_sid) as tc
        FROM calls c 
        WHERE c.final_outcome = 'unknown' OR c.final_outcome IS NULL OR c.final_outcome = ''
    """).fetchall()
    
    fixed = 0
    for call_sid, turn_count in unknowns:
        if turn_count == 0:
            new_outcome = 'no_answer'
        elif turn_count <= 2:
            new_outcome = 'no_engagement'
        elif turn_count <= 5:
            new_outcome = 'short_interaction'
        else:
            new_outcome = 'soft_decline'
        
        cur.execute("UPDATE calls SET final_outcome = ? WHERE call_sid = ?", (new_outcome, call_sid))
        fixed += 1
        print(f"  {call_sid[:25]:25s} turns={turn_count:3d} → {new_outcome}")
    
    print(f"  Reclassified {fixed} unknown outcomes.")
    
    # --- 2. Fix IVR-Poisoned kept_engaged ---
    print("\n[STEP 2] Checking for IVR-poisoned 'kept_engaged'...")
    ivr_phrases = [
        'press one', 'press two', 'press three', 'press four',
        'leave a message', 'after the tone', 'after the beep',
        'please hold', 'business hours', 'para espanol',
        'press pound', 'press star', 'your call is important'
    ]
    
    kept = cur.execute("SELECT call_sid FROM calls WHERE final_outcome = 'kept_engaged'").fetchall()
    ivr_fixed = 0
    for (call_sid,) in kept:
        turns = cur.execute("SELECT user_text FROM turns WHERE call_sid = ?", (call_sid,)).fetchall()
        all_text = ' '.join((t[0] or '') for t in turns).lower()
        ivr_hits = sum(1 for p in ivr_phrases if p in all_text)
        if ivr_hits >= 2:
            cur.execute(
                "UPDATE calls SET final_outcome = 'voicemail_ivr' WHERE call_sid = ?",
                (call_sid,)
            )
            ivr_fixed += 1
            print(f"  IVR Override: {call_sid[:25]:25s} (ivr_hits={ivr_hits}) kept_engaged → voicemail_ivr")
    
    print(f"  Reclassified {ivr_fixed} IVR-poisoned entries.")
    
    # --- 3. Check Coaching Scores ---
    print("\n[STEP 3] Checking coaching scores...")
    try:
        # Check if coaching columns exist
        cols = [row[1] for row in cur.execute("PRAGMA table_info(turns)").fetchall()]
        if 'coaching_score' in cols:
            zero_coaching = cur.execute("SELECT COUNT(*) FROM turns WHERE coaching_score IS NULL OR coaching_score = 0").fetchone()[0]
            total_turns = cur.execute("SELECT COUNT(*) FROM turns").fetchone()[0]
            print(f"  Turns with coaching=0: {zero_coaching}/{total_turns}")
        else:
            print("  coaching_score column not in turns table (coaching not yet integrated)")
    except Exception as e:
        print(f"  Coaching check skipped: {e}")
    
    # --- Commit ---
    db.commit()
    
    # --- After ---
    print("\n[AFTER] Outcome Distribution:")
    rows = cur.execute("SELECT final_outcome, COUNT(*) as cnt FROM calls GROUP BY final_outcome ORDER BY cnt DESC").fetchall()
    for r in rows:
        print(f"  {str(r[0]):30s} : {r[1]}")
    
    unknown_count = sum(r[1] for r in rows if r[0] in ('unknown', None, ''))
    total = sum(r[1] for r in rows)
    pct = (unknown_count / total * 100) if total > 0 else 0
    print(f"\n  Unknown rate: {unknown_count}/{total} ({pct:.1f}%)")
    
    db.close()
    print("\n" + "=" * 60)
    print("SANITIZATION COMPLETE")
    print("=" * 60)

if __name__ == '__main__':
    main()
