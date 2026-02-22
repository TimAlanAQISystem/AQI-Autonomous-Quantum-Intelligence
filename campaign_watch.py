#!/usr/bin/env python3
"""
CAMPAIGN WATCH — Real-Time Conversation Quality Monitor
========================================================
Tim's Directive: Watch each lead, confirm appropriate action, monitor 50 human
conversations for quality, timing, dialogue accuracy, sales progression.

Runs continuously during a campaign. Polls call_capture.db for new calls.
Analyzes each completed human conversation. Logs everything.

Usage: .\.venv\Scripts\python.exe campaign_watch.py

Author: Claude Opus 4.6 — CW20 Session 16
Date: February 18, 2026
"""

import os
import sys
import json
import time
import sqlite3
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

# Setup
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
CDC_DB = DATA_DIR / "call_capture.db"
LEAD_DB = DATA_DIR / "leads.db"
WATCH_LOG = DATA_DIR / "campaign_watch.json"
WATCH_REPORT = BASE_DIR / "CAMPAIGN_WATCH_REPORT.md"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [WATCH] %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger("CAMPAIGN_WATCH")

# ─── Quality Constants ───
AI_WORDS = [
    'leverage', 'optimize', 'streamline', 'facilitate', 'ensure', 'utilize',
    'comprehensive', 'robust', 'innovative', 'solutions', 'absolutely',
    'certainly', 'i appreciate', 'that sounds great', 'i can help with that',
    "i'd love to help", 'thank you for your valuable time', 'i understand your concern'
]

BANNED_OPENERS = [
    'absolutely!', 'great!', 'sure thing!', 'perfect!', 'got it.',
    'got it, what can i help you with', "that's a great question",
    "that's a wonderful", "i completely understand"
]

ROBOTIC_PHRASES = [
    "i'm right here", "go ahead", "i'm here to help",
    "looking forward to it", "in the meantime",
    "that sounds like a valuable service", "is there anything else",
    "thank you for your time today", "it was a pleasure speaking"
]

NATURAL_STARTERS = ['yeah', 'so', 'right', 'okay', 'look', 'well', 'hey', 'oh', 'no', 'hmm', 'sure']

SALES_PROGRESSION_SIGNALS = [
    'send me', 'email me', 'sounds interesting', 'tell me more',
    'how much', 'what would', 'pricing', 'cost', 'rate', 'fee',
    'compare', 'switch', 'save', 'sign up', 'application',
    'statement', 'current processor', 'currently using', 'interested',
    'let me think', 'talk to', 'call back', 'follow up', 'appointment',
    'when can you', 'send over', 'information', 'brochure'
]

NEGATIVE_SIGNALS = [
    'not interested', 'no thanks', 'don\'t call', 'remove me',
    'stop calling', 'we\'re good', 'happy with', 'not looking',
    'do not call', 'take me off', 'already have', 'go away',
    'busy right now', 'not a good time', 'hung up', 'click'
]


class CampaignWatcher:
    def __init__(self):
        self.analyzed_sids: set = set()
        self.conversation_count = 0
        self.target_conversations = 50
        self.watch_entries: List[Dict] = []
        self.issues_found: List[Dict] = []
        self.start_time = datetime.now()
        
        # Load prior state if exists
        if WATCH_LOG.exists():
            try:
                data = json.loads(WATCH_LOG.read_text())
                self.analyzed_sids = set(data.get("analyzed_sids", []))
                self.conversation_count = data.get("conversation_count", 0)
                self.watch_entries = data.get("entries", [])
                self.issues_found = data.get("issues", [])
                log.info(f"Resumed: {self.conversation_count}/{self.target_conversations} conversations tracked")
            except Exception:
                pass
    
    def save_state(self):
        """Persist state to disk"""
        data = {
            "conversation_count": self.conversation_count,
            "target": self.target_conversations,
            "analyzed_sids": list(self.analyzed_sids),
            "entries": self.watch_entries,
            "issues": self.issues_found,
            "last_updated": datetime.now().isoformat()
        }
        WATCH_LOG.write_text(json.dumps(data, indent=2, default=str))
    
    def get_new_calls(self) -> List[Dict]:
        """Get completed calls not yet analyzed"""
        if not CDC_DB.exists():
            return []
        
        conn = sqlite3.connect(str(CDC_DB), timeout=5)
        conn.row_factory = sqlite3.Row
        
        try:
            # Get completed calls with turns (indicating human conversation)
            rows = conn.execute("""
                SELECT c.*, COUNT(t.id) as turn_count
                FROM calls c
                LEFT JOIN turns t ON t.call_sid = c.call_sid
                WHERE c.end_time IS NOT NULL
                GROUP BY c.call_sid
                HAVING turn_count > 0
                ORDER BY c.start_time DESC
                LIMIT 50
            """).fetchall()
            
            new_calls = []
            for row in rows:
                sid = row["call_sid"]
                if sid not in self.analyzed_sids:
                    call_data = dict(row)
                    # Get turns
                    turns = conn.execute("""
                        SELECT * FROM turns WHERE call_sid = ? ORDER BY turn_number
                    """, (sid,)).fetchall()
                    call_data["turns"] = [dict(t) for t in turns]
                    new_calls.append(call_data)
            
            return new_calls
        except Exception as e:
            log.error(f"DB read error: {e}")
            return []
        finally:
            conn.close()
    
    def is_human_conversation(self, call: Dict) -> bool:
        """Determine if this was a real human conversation (not dead-end).
        
        Tim's directive: dead-end calls don't count toward 50.
        Excludes: voicemail, IVR navigation, silence kills, very short hangups.
        """
        turns = call.get("turns", [])
        outcome = (call.get("final_outcome") or "").lower()
        
        # Exclude known non-human outcomes
        dead_end_outcomes = {
            "voicemail_ivr", "ivr_system", "ivr_transcript_kill",
            "voicemail", "silence_kill", "no_answer", "busy",
            "failed", "error", "machine_detected", "dead_end_exit",
            "timeout"
        }
        if outcome in dead_end_outcomes:
            return False
        
        if len(turns) < 2:
            return False
        
        # Count turns where the merchant actually spoke
        merchant_turns = sum(1 for t in turns if (t.get("user_text") or "").strip())
        if merchant_turns < 2:
            return False
        
        # Check if total words from merchant is meaningful (3+ words = greeting at least)
        total_merchant_words = sum(t.get("user_word_count", 0) or 0 for t in turns)
        if total_merchant_words < 5:
            return False
        
        # Duration check — very short calls likely hangups
        duration = call.get("duration_seconds", 0) or 0
        if duration < 10:
            return False
        
        return True
    
    def analyze_human_quality(self, call: Dict) -> Dict:
        """Deep analysis of how human-like Alan sounded"""
        turns = call.get("turns", [])
        score = 50
        issues = []
        strengths = []
        
        ai_word_count = 0
        banned_opener_count = 0
        robotic_count = 0
        monologue_count = 0
        good_openers = 0
        
        for turn in turns:
            alan = (turn.get("alan_text") or "").lower()
            alan_wc = turn.get("alan_word_count", 0) or 0
            
            for w in AI_WORDS:
                if w in alan:
                    ai_word_count += 1
            
            for b in BANNED_OPENERS:
                if alan.strip().startswith(b):
                    banned_opener_count += 1
            
            for r in ROBOTIC_PHRASES:
                if r in alan:
                    robotic_count += 1
            
            if alan_wc > 50:
                monologue_count += 1
            
            first_word = alan.split()[0] if alan.split() else ""
            if first_word in NATURAL_STARTERS:
                good_openers += 1
        
        total_turns = len(turns)
        if total_turns == 0:
            return {"score": 50, "grade": "C", "issues": ["No turns"], "strengths": []}
        
        # Scoring
        if ai_word_count == 0:
            score += 15; strengths.append("Clean of AI words")
        else:
            score -= min(ai_word_count * 5, 20)
            issues.append(f"{ai_word_count} AI word(s)")
        
        if banned_opener_count == 0:
            score += 10; strengths.append("No banned openers")
        else:
            score -= banned_opener_count * 10
            issues.append(f"{banned_opener_count} banned opener(s)")
        
        if robotic_count == 0:
            score += 10; strengths.append("No robotic phrases")
        else:
            score -= robotic_count * 8
            issues.append(f"{robotic_count} robotic phrase(s)")
        
        if monologue_count == 0:
            score += 10; strengths.append("Good response brevity")
        else:
            score -= monologue_count * 5
            issues.append(f"{monologue_count} monologue(s) (50+ words)")
        
        if good_openers > 0:
            pct = good_openers / total_turns * 100
            if pct > 40:
                score += 10; strengths.append(f"Natural openers {pct:.0f}%")
            elif pct > 20:
                score += 5; strengths.append(f"Some natural openers")
        
        score = max(0, min(100, score))
        grade = "A" if score >= 85 else "B" if score >= 70 else "C" if score >= 55 else "D" if score >= 40 else "F"
        
        return {"score": score, "grade": grade, "issues": issues, "strengths": strengths}
    
    def analyze_sales_progression(self, call: Dict) -> Dict:
        """Analyze if Alan is progressing toward a sale"""
        turns = call.get("turns", [])
        
        positive_signals = 0
        negative_signals = 0
        signal_details = []
        
        for turn in turns:
            user = (turn.get("user_text") or "").lower()
            
            for sig in SALES_PROGRESSION_SIGNALS:
                if sig in user:
                    positive_signals += 1
                    signal_details.append(f"+ Merchant: '{sig}' (turn {turn.get('turn_number', '?')})")
                    break
            
            for sig in NEGATIVE_SIGNALS:
                if sig in user:
                    negative_signals += 1
                    signal_details.append(f"- Merchant: '{sig}' (turn {turn.get('turn_number', '?')})")
                    break
        
        trajectory = call.get("final_trajectory", "neutral")
        temperature = call.get("final_temperature", 50) or 50
        
        if positive_signals > negative_signals and temperature > 60:
            verdict = "PROGRESSING"
        elif negative_signals > positive_signals:
            verdict = "DECLINING"
        elif temperature >= 50:
            verdict = "NEUTRAL"
        else:
            verdict = "COLD"
        
        return {
            "verdict": verdict,
            "positive_signals": positive_signals,
            "negative_signals": negative_signals,
            "trajectory": trajectory,
            "temperature": temperature,
            "details": signal_details
        }
    
    def analyze_timing(self, call: Dict) -> Dict:
        """Analyze conversation timing patterns"""
        turns = call.get("turns", [])
        duration = call.get("duration_seconds", 0) or 0
        total_turns = len(turns)
        
        issues = []
        
        # Words per second analysis
        alan_words = call.get("alan_words", 0) or 0
        merchant_words = call.get("merchant_words", 0) or 0
        
        if duration > 0:
            words_per_sec = (alan_words + merchant_words) / duration
            if words_per_sec < 0.5 and duration > 30:
                issues.append(f"Low dialogue density: {words_per_sec:.1f} words/sec (dead air?)")
            elif words_per_sec > 5:
                issues.append(f"Very high density: {words_per_sec:.1f} words/sec (overlap?)")
        
        # Turn length balance
        if total_turns > 2:
            alan_avg = alan_words / total_turns if total_turns else 0
            merchant_avg = merchant_words / total_turns if total_turns else 0
            
            if alan_avg > 0 and merchant_avg > 0:
                ratio = alan_avg / merchant_avg
                if ratio > 4:
                    issues.append(f"Alan talking {ratio:.1f}x more than merchant — lecturing")
                elif ratio < 0.3:
                    issues.append(f"Merchant talking {1/ratio:.1f}x more — Alan too passive")
        
        # Duration assessment
        if duration > 300:
            assessment = "LONG"
        elif duration > 120:
            assessment = "GOOD"
        elif duration > 30:
            assessment = "SHORT"
        else:
            assessment = "VERY_SHORT"
        
        return {
            "duration_seconds": duration,
            "assessment": assessment,
            "total_turns": total_turns,
            "alan_words": alan_words,
            "merchant_words": merchant_words,
            "issues": issues
        }
    
    def analyze_call(self, call: Dict) -> Dict:
        """Complete analysis of a single call"""
        sid = call.get("call_sid", "unknown")
        name = call.get("merchant_name", "Unknown")
        biz = call.get("business_name", "")
        
        human_quality = self.analyze_human_quality(call)
        sales_prog = self.analyze_sales_progression(call)
        timing = self.analyze_timing(call)
        
        # Build transcript excerpt
        turns = call.get("turns", [])
        transcript = []
        for t in turns[:15]:
            user = (t.get("user_text") or "").strip()
            alan = (t.get("alan_text") or "").strip()
            if user:
                transcript.append(f"MERCHANT: {user[:200]}")
            if alan:
                transcript.append(f"ALAN: {alan[:200]}")
        
        # Determine overall call verdict
        all_issues = human_quality["issues"] + timing["issues"]
        if human_quality["score"] >= 70 and sales_prog["verdict"] in ("PROGRESSING", "NEUTRAL") and not all_issues:
            overall = "GOOD"
        elif human_quality["score"] < 50 or len(all_issues) > 3:
            overall = "NEEDS_ATTENTION"
        else:
            overall = "ACCEPTABLE"
        
        entry = {
            "call_sid": sid,
            "merchant": name,
            "business": biz,
            "timestamp": call.get("start_time", ""),
            "duration": call.get("duration_seconds", 0),
            "outcome": call.get("final_outcome", "unknown"),
            "human_quality": human_quality,
            "sales_progression": sales_prog,
            "timing": timing,
            "transcript_excerpt": transcript[:20],
            "overall_verdict": overall,
            "greeting": call.get("greeting_text", ""),
            "analyzed_at": datetime.now().isoformat()
        }
        
        # Collect issues for real-time action
        if overall == "NEEDS_ATTENTION":
            self.issues_found.append({
                "call_sid": sid,
                "merchant": name,
                "issues": all_issues,
                "score": human_quality["score"],
                "timestamp": datetime.now().isoformat()
            })
        
        return entry
    
    def write_report(self):
        """Write human-readable Campaign Watch report"""
        lines = []
        lines.append("# CAMPAIGN WATCH REPORT")
        lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"**Campaign Started:** {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"**Human Conversations Monitored:** {self.conversation_count} / {self.target_conversations}")
        lines.append("")
        
        # Summary stats
        if self.watch_entries:
            scores = [e["human_quality"]["score"] for e in self.watch_entries]
            avg_score = sum(scores) / len(scores)
            avg_grade = "A" if avg_score >= 85 else "B" if avg_score >= 70 else "C" if avg_score >= 55 else "D" if avg_score >= 40 else "F"
            
            verdicts = [e["sales_progression"]["verdict"] for e in self.watch_entries]
            progressing = verdicts.count("PROGRESSING")
            declining = verdicts.count("DECLINING")
            neutral = verdicts.count("NEUTRAL")
            cold = verdicts.count("COLD")
            
            durations = [e["duration"] or 0 for e in self.watch_entries]
            avg_dur = sum(durations) / len(durations) if durations else 0
            max_dur = max(durations) if durations else 0
            
            lines.append("## Overall Metrics")
            lines.append(f"- **Average Human Quality Score:** {avg_score:.1f}/100 (Grade: {avg_grade})")
            lines.append(f"- **Average Duration:** {avg_dur:.1f}s | Longest: {max_dur:.1f}s")
            lines.append(f"- **Sales Progression:** {progressing} progressing, {neutral} neutral, {declining} declining, {cold} cold")
            lines.append(f"- **Issues Found:** {len(self.issues_found)}")
            lines.append("")
        
        # Per-call details
        lines.append("## Per-Call Analysis")
        lines.append("")
        
        for i, entry in enumerate(self.watch_entries, 1):
            hq = entry["human_quality"]
            sp = entry["sales_progression"]
            tm = entry["timing"]
            
            badge = "GOOD" if entry["overall_verdict"] == "GOOD" else "NEEDS ATTENTION" if entry["overall_verdict"] == "NEEDS_ATTENTION" else "OK"
            
            lines.append(f"### Call #{i}: {entry['merchant']} ({entry['business']})")
            lines.append(f"- **Verdict:** {badge}")
            lines.append(f"- **Time:** {entry['timestamp'][:19] if entry['timestamp'] else 'N/A'}")
            lines.append(f"- **Duration:** {entry['duration']:.1f}s | Turns: {tm['total_turns']}")
            lines.append(f"- **Outcome:** {entry['outcome']}")
            lines.append(f"- **Human Quality:** {hq['score']}/100 ({hq['grade']})")
            lines.append(f"- **Sales:** {sp['verdict']} (temp={sp['temperature']})")
            lines.append(f"- **Greeting:** \"{entry['greeting'][:100]}\"")
            
            if hq["strengths"]:
                lines.append(f"- **Strengths:** {', '.join(hq['strengths'])}")
            if hq["issues"]:
                lines.append(f"- **Issues:** {', '.join(hq['issues'])}")
            if sp["details"]:
                lines.append(f"- **Signals:** {'; '.join(sp['details'][:5])}")
            
            # Transcript
            if entry.get("transcript_excerpt"):
                lines.append(f"- **Transcript Preview:**")
                for line in entry["transcript_excerpt"][:10]:
                    lines.append(f"  > {line[:150]}")
            
            lines.append("")
        
        # Issues section
        if self.issues_found:
            lines.append("## Issues Requiring Attention")
            lines.append("")
            for issue in self.issues_found:
                lines.append(f"- **{issue['merchant']}** (score={issue['score']}): {', '.join(issue['issues'])}")
            lines.append("")
        
        WATCH_REPORT.write_text("\n".join(lines), encoding="utf-8")
        log.info(f"Report written: {WATCH_REPORT.name}")
    
    def poll_once(self) -> int:
        """Single poll cycle. Returns number of new conversations analyzed."""
        new_calls = self.get_new_calls()
        analyzed = 0
        
        for call in new_calls:
            sid = call.get("call_sid", "")
            if not sid or sid in self.analyzed_sids:
                continue
            
            self.analyzed_sids.add(sid)
            
            # Check if it's a real human conversation (not dead-end)
            if not self.is_human_conversation(call):
                log.info(f"  Skip {sid[:12]}... — dead-end (no meaningful merchant dialogue)")
                continue
            
            # Analyze the conversation
            entry = self.analyze_call(call)
            self.watch_entries.append(entry)
            self.conversation_count += 1
            analyzed += 1
            
            hq = entry["human_quality"]
            sp = entry["sales_progression"]
            
            log.info(
                f"  CONV #{self.conversation_count}: {entry['merchant']:<25s} "
                f"dur={entry['duration']:.0f}s  quality={hq['score']}/100({hq['grade']}) "
                f"sales={sp['verdict']}  outcome={entry['outcome']}"
            )
            
            if entry["overall_verdict"] == "NEEDS_ATTENTION":
                log.warning(f"  *** ATTENTION: {', '.join(hq['issues'])}")
        
        if analyzed > 0:
            self.save_state()
            self.write_report()
        
        return analyzed
    
    def run(self, poll_interval: int = 15):
        """Main watch loop"""
        log.info(f"Campaign Watch started. Target: {self.target_conversations} conversations.")
        log.info(f"Polling every {poll_interval}s. Prior progress: {self.conversation_count} conversations.")
        log.info(f"CDC database: {CDC_DB}")
        
        try:
            while self.conversation_count < self.target_conversations:
                new = self.poll_once()
                
                if new > 0:
                    remaining = self.target_conversations - self.conversation_count
                    log.info(f"Progress: {self.conversation_count}/{self.target_conversations} ({remaining} remaining)")
                
                time.sleep(poll_interval)
        
        except KeyboardInterrupt:
            log.info("Watch interrupted by user")
        finally:
            self.save_state()
            self.write_report()
            log.info(f"Final: {self.conversation_count}/{self.target_conversations} conversations monitored")
            log.info(f"Report: {WATCH_REPORT}")


# ─── Standalone one-shot analysis ───
def one_shot_analysis():
    """Run one-time analysis of all existing conversations"""
    watcher = CampaignWatcher()
    watcher.analyzed_sids.clear()  # Re-analyze everything
    watcher.watch_entries.clear()
    watcher.conversation_count = 0
    watcher.poll_once()
    return watcher


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Campaign Watch — Real-Time Monitor")
    parser.add_argument("--oneshot", action="store_true", help="Run one-time analysis then exit")
    parser.add_argument("--interval", type=int, default=15, help="Poll interval in seconds")
    args = parser.parse_args()
    
    if args.oneshot:
        watcher = one_shot_analysis()
        print(f"\nAnalyzed {watcher.conversation_count} conversations")
        print(f"Report: {WATCH_REPORT}")
    else:
        watcher = CampaignWatcher()
        watcher.run(poll_interval=args.interval)
