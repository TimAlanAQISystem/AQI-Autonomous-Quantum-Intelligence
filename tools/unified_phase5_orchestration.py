"""
Unified Phase 5 Orchestration
================================
Full-cycle runner that executes the Phase 5 governance loop:
  1. Runs test harness (prosody + quantum stress test)
  2. Processes cycle JSONL data
  3. Generates visualizations (heatmap, trajectory, components)
  4. Runs anomaly detection
  5. Generates cycle summary

Usage:
    .venv\\Scripts\\python.exe tools/unified_phase5_orchestration.py <cycle_id> [jsonl_path]

Example:
    .venv\\Scripts\\python.exe tools/unified_phase5_orchestration.py 001 phase5_cycles/cycle_001/call_log.jsonl
"""

import sys
import os
import json
import subprocess
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
CYCLES_DIR = os.path.join(PROJECT_ROOT, "phase5_cycles")
PYTHON = os.path.join(PROJECT_ROOT, ".venv", "Scripts", "python.exe")


def ensure_cycle_dir(cycle_id):
    """Create cycle directory if needed."""
    cycle_dir = os.path.join(CYCLES_DIR, f"cycle_{cycle_id}")
    os.makedirs(cycle_dir, exist_ok=True)
    return cycle_dir


def run_tool(script_name, args, label):
    """Run a tool script and report status."""
    script_path = os.path.join(TOOLS_DIR, script_name)
    if not os.path.exists(script_path):
        print(f"  SKIP {label}: {script_name} not found")
        return False

    cmd = [PYTHON, script_path] + args
    print(f"\n  Running {label}...")
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=PROJECT_ROOT,
        )
        if result.stdout:
            for line in result.stdout.strip().split("\n"):
                print(f"    {line}")
        if result.returncode != 0:
            print(f"  WARNING: {label} returned exit code {result.returncode}")
            if result.stderr:
                for line in result.stderr.strip().split("\n")[-5:]:
                    print(f"    ERR: {line}")
            return False
        return True
    except subprocess.TimeoutExpired:
        print(f"  ERROR: {label} timed out after 120s")
        return False
    except Exception as e:
        print(f"  ERROR: {label} failed: {e}")
        return False


def generate_summary(cycle_id, cycle_dir, jsonl_path):
    """Generate a cycle summary markdown file."""
    summary_path = os.path.join(
        cycle_dir, f"phase5_cycle_{cycle_id}_summary.md"
    )

    # Load data if available
    anomaly_count = 0
    record_count = 0
    anomaly_path = os.path.join(
        cycle_dir,
        f"phase5_cycle_{cycle_id}_call_log_anomalies.json"
    )

    if os.path.exists(anomaly_path):
        try:
            with open(anomaly_path, "r", encoding="utf-8") as f:
                anomaly_data = json.load(f)
                anomaly_count = anomaly_data.get("total_anomalies", 0)
        except (json.JSONDecodeError, IOError):
            pass

    if jsonl_path and os.path.exists(jsonl_path):
        with open(jsonl_path, "r", encoding="utf-8") as f:
            record_count = sum(1 for line in f if line.strip())

    summary = f"""# Phase 5 Cycle {cycle_id} — Summary

**Generated:** {time.strftime('%Y-%m-%d %H:%M:%S')}

## Data
- Records processed: {record_count}
- Anomalies detected: {anomaly_count}

## Artifacts
- Call log: `phase5_cycle_{cycle_id}_call_log.jsonl`
- Prosody heatmap: `phase5_cycle_{cycle_id}_prosody_heatmap.png`
- Mode trajectory: `phase5_cycle_{cycle_id}_call_log_mode_trajectory.png`
- State components: `phase5_cycle_{cycle_id}_call_log_state_components.png`
- Anomaly report: `phase5_cycle_{cycle_id}_call_log_anomalies.json`

## Scoring
*Fill in manually after call evaluation*

| Dimension | Mean | Min | Max |
|-----------|------|-----|-----|
| Voice Realism | /5 | /5 | /5 |
| Emotional Congruence | /5 | /5 | /5 |
| Latency Feel | /5 | /5 | /5 |
| Objection Handling | /5 | /5 | /5 |
| Closure Behavior | /5 | /5 | /5 |

## Operator Notes
*Add observations here*
"""
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(summary)
    print(f"  Summary written to: {summary_path}")
    return True


def main():
    print("=" * 60)
    print("  UNIFIED PHASE 5 ORCHESTRATION")
    print("=" * 60)

    if len(sys.argv) < 2:
        print("\nUsage: python tools/unified_phase5_orchestration.py <cycle_id> [jsonl_path]")
        print("\nExample:")
        print("  python tools/unified_phase5_orchestration.py 001")
        print("  python tools/unified_phase5_orchestration.py 001 phase5_cycles/cycle_001/call_log.jsonl")
        return 1

    cycle_id = sys.argv[1].zfill(3)
    cycle_dir = ensure_cycle_dir(cycle_id)

    # Determine JSONL path
    if len(sys.argv) >= 3:
        jsonl_path = sys.argv[2]
    else:
        jsonl_path = os.path.join(
            cycle_dir, f"phase5_cycle_{cycle_id}_call_log.jsonl"
        )

    print(f"\n  Cycle: {cycle_id}")
    print(f"  Directory: {cycle_dir}")
    print(f"  JSONL: {jsonl_path}")

    results = {}

    # Step 1: Run test harness (always — it produces phase5_test_output.jsonl)
    results["test_harness"] = run_tool(
        "test_harness_phase5.py", [], "Test Harness"
    )

    # Steps 2-4 require JSONL data
    if os.path.exists(jsonl_path):
        # Step 2: Prosody heatmap
        heatmap_out = os.path.join(
            cycle_dir, f"phase5_cycle_{cycle_id}_prosody_heatmap.png"
        )
        results["prosody_heatmap"] = run_tool(
            "prosody_heatmap.py", [jsonl_path, heatmap_out], "Prosody Heatmap"
        )

        # Step 3: Quantum trajectory
        results["quantum_trajectory"] = run_tool(
            "quantum_trajectory.py", [jsonl_path, cycle_dir], "Quantum Trajectory"
        )

        # Step 4: Anomaly detection
        anomaly_out = os.path.join(
            cycle_dir,
            f"phase5_cycle_{cycle_id}_call_log_anomalies.json"
        )
        results["anomaly_detector"] = run_tool(
            "governance_anomaly_detector.py",
            [jsonl_path, anomaly_out],
            "Anomaly Detection"
        )
    else:
        print(f"\n  NOTE: JSONL file not found at {jsonl_path}")
        print("  Skipping visualization and anomaly steps.")
        print("  To generate visualizations, provide JSONL data from live calls.")

    # Step 5: Generate summary
    results["summary"] = generate_summary(cycle_id, cycle_dir, jsonl_path)

    # Final report
    print("\n" + "=" * 60)
    print("  ORCHESTRATION COMPLETE")
    print("=" * 60)
    for step, passed in results.items():
        symbol = "✓" if passed else "✗"
        print(f"  {symbol} {step}")

    passed_count = sum(1 for v in results.values() if v)
    total = len(results)
    print(f"\n  {passed_count}/{total} steps completed successfully.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
