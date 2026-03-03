"""
Latency Profiler Aggregation — Phase 3
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Post-campaign aggregation of per-turn latency JSONL data.
Reports median, p90, p95 for all latency dimensions.

Usage:
    python latency_profiler.py                     # All data
    python latency_profiler.py --last 100          # Last 100 turns
    python latency_profiler.py --call CA...        # Specific call
"""
import json
import sys
import statistics
from pathlib import Path

JSONL_PATH = Path('data/latency/turn_latency.jsonl')

METRICS = [
    'first_audio_latency_ms',
    'full_turn_latency_ms',
    'llm_latency_ms',
    'llm_ttft_ms',
    'tts_total_ms',
    'streaming_overhead_ms',
]

THRESHOLDS = {
    'first_audio_latency_ms': {'good': 1500, 'ok': 2500, 'unit': 'ms'},
    'full_turn_latency_ms': {'good': 3000, 'ok': 5000, 'unit': 'ms'},
    'llm_latency_ms': {'good': 2000, 'ok': 3500, 'unit': 'ms'},
    'llm_ttft_ms': {'good': 400, 'ok': 800, 'unit': 'ms'},
    'tts_total_ms': {'good': 800, 'ok': 1500, 'unit': 'ms'},
}


def percentile(data, p):
    """Calculate the p-th percentile of a sorted list."""
    if not data:
        return 0
    k = (len(data) - 1) * (p / 100)
    f = int(k)
    c = f + 1
    if c >= len(data):
        return data[f]
    return data[f] + (k - f) * (data[c] - data[f])


def load_records(last_n=None, call_sid=None):
    """Load and optionally filter JSONL records."""
    if not JSONL_PATH.exists():
        print(f"No latency data found at {JSONL_PATH}")
        return []
    
    records = []
    with open(JSONL_PATH) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                if call_sid and rec.get('call_sid', '') != call_sid:
                    continue
                records.append(rec)
            except json.JSONDecodeError:
                continue
    
    if last_n and last_n > 0:
        records = records[-last_n:]
    
    return records


def aggregate(records):
    """Compute aggregate statistics for all metrics."""
    if not records:
        print("No records to aggregate.")
        return
    
    print("=" * 70)
    print(f"LATENCY PROFILER — {len(records)} turns analyzed")
    print("=" * 70)
    
    # Unique calls
    call_sids = set(r.get('call_sid', 'unknown') for r in records)
    print(f"Unique calls: {len(call_sids)}")
    
    # Time range
    timestamps = [r.get('ts', '') for r in records if r.get('ts')]
    if timestamps:
        print(f"Time range: {min(timestamps)} → {max(timestamps)}")
    
    print()
    print(f"{'Metric':<28s} {'Median':>8s} {'P90':>8s} {'P95':>8s} {'Min':>8s} {'Max':>8s} {'Grade':>6s}")
    print("-" * 70)
    
    for metric in METRICS:
        values = sorted([r.get(metric, 0) for r in records if r.get(metric, 0) > 0])
        if not values:
            print(f"{metric:<28s}  {'(no data)':>8s}")
            continue
        
        med = statistics.median(values)
        p90 = percentile(values, 90)
        p95 = percentile(values, 95)
        mn = min(values)
        mx = max(values)
        
        # Grade based on thresholds
        grade = ''
        thresh = THRESHOLDS.get(metric)
        if thresh:
            if med <= thresh['good']:
                grade = 'GOOD'
            elif med <= thresh['ok']:
                grade = 'OK'
            else:
                grade = 'SLOW'
        
        print(f"{metric:<28s} {med:>7.0f}  {p90:>7.0f}  {p95:>7.0f}  {mn:>7.0f}  {mx:>7.0f}  {grade:>6s}")
    
    # Turn count distribution
    print()
    turns_per_call = {}
    for r in records:
        sid = r.get('call_sid', 'unknown')
        turns_per_call[sid] = turns_per_call.get(sid, 0) + 1
    
    turn_counts = sorted(turns_per_call.values())
    if turn_counts:
        print(f"Turns per call: median={statistics.median(turn_counts):.0f}, "
              f"max={max(turn_counts)}, min={min(turn_counts)}")
    
    # Sentence distribution
    sentence_counts = [r.get('sentences', 0) for r in records]
    if sentence_counts:
        print(f"Sentences per turn: median={statistics.median(sentence_counts):.1f}, "
              f"max={max(sentence_counts)}")
    
    print()
    print("=" * 70)


if __name__ == '__main__':
    last_n = None
    call_sid = None
    
    for i, arg in enumerate(sys.argv):
        if arg == '--last' and i + 1 < len(sys.argv):
            last_n = int(sys.argv[i + 1])
        elif arg == '--call' and i + 1 < len(sys.argv):
            call_sid = sys.argv[i + 1]
    
    records = load_records(last_n=last_n, call_sid=call_sid)
    aggregate(records)
