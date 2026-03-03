"""
AQI Phase 5 — CLI Tool
========================
Command-line interface for running Phase 5 behavioral intelligence
on Phase 4 call trace exports.

Usage:
    .venv\\Scripts\\python.exe aqi_phase5_cli.py traces.jsonl
    .venv\\Scripts\\python.exe aqi_phase5_cli.py traces.jsonl --report phase5_report.md
    .venv\\Scripts\\python.exe aqi_phase5_cli.py data/call_traces/ --window 50
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from aqi_phase5_call_analyzer import Phase5CallAnalyzer
from aqi_phase5_dashboard import Phase5Dashboard
from aqi_phase5_tagging_engine import TaggingEngine
from phase4_validator import Phase4Validator


def main():
    parser = argparse.ArgumentParser(
        description="AQI Phase 5 Behavioral Intelligence CLI"
    )
    parser.add_argument(
        "input",
        help="Path to JSONL file or directory of call traces"
    )
    parser.add_argument(
        "--report", default=None,
        help="Output report path (markdown). If omitted, prints to stdout."
    )
    parser.add_argument(
        "--window", type=int, default=0,
        help="Rolling window size (0 = all calls)"
    )
    parser.add_argument(
        "--validate", action="store_true",
        help="Run strict validation before analysis"
    )
    parser.add_argument(
        "--json", action="store_true", dest="json_output",
        help="Output raw JSON aggregate instead of markdown report"
    )
    args = parser.parse_args()

    analyzer = Phase5CallAnalyzer()
    dashboard = Phase5Dashboard()
    validator = Phase4Validator()

    input_path = Path(args.input)
    traces_loaded = 0
    validation_errors = 0

    # ── Ingest ────────────────────────────────────────────
    if input_path.is_dir():
        for p in sorted(input_path.glob("*.jsonl")):
            traces_loaded += _ingest_file(p, analyzer, dashboard, validator, args.validate)
        for p in sorted(input_path.glob("*.json")):
            if p.name.endswith(".schema.json"):
                continue
            traces_loaded += _ingest_single_json(p, analyzer, dashboard, validator, args.validate)
    elif input_path.suffix == ".jsonl":
        traces_loaded = _ingest_file(input_path, analyzer, dashboard, validator, args.validate)
    elif input_path.suffix == ".json":
        traces_loaded = _ingest_single_json(input_path, analyzer, dashboard, validator, args.validate)
    else:
        print(f"ERROR: Unsupported input: {input_path}", file=sys.stderr)
        sys.exit(1)

    if traces_loaded == 0:
        print("No valid traces found.", file=sys.stderr)
        sys.exit(1)

    print(f"Loaded {traces_loaded} call traces.", file=sys.stderr)

    # ── Aggregate ─────────────────────────────────────────
    if args.window > 0:
        agg = dashboard.get_rolling_aggregate(args.window)
    else:
        agg = dashboard.aggregate()

    # ── Output ────────────────────────────────────────────
    if args.json_output:
        output = json.dumps(agg, indent=2, default=str)
    else:
        output = render_report(agg, args.window)

    if args.report:
        with open(args.report, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"Report written to {args.report}", file=sys.stderr)
    else:
        print(output)


def _ingest_file(path: Path, analyzer, dashboard, validator, validate: bool) -> int:
    count = 0
    with path.open("r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                trace = json.loads(line)
                if validate:
                    result = validator.validate(trace)
                    if not result["valid"]:
                        print(f"WARN: {path}:{line_num} validation failed: {result['structural_errors']}", file=sys.stderr)
                        continue
                profile = analyzer.analyze(trace)
                dashboard.add_call_profile(profile)
                count += 1
            except json.JSONDecodeError as e:
                print(f"WARN: {path}:{line_num} invalid JSON: {e}", file=sys.stderr)
            except Exception as e:
                print(f"WARN: {path}:{line_num} error: {e}", file=sys.stderr)
    return count


def _ingest_single_json(path: Path, analyzer, dashboard, validator, validate: bool) -> int:
    try:
        with path.open("r", encoding="utf-8") as f:
            trace = json.load(f)
        if validate:
            result = validator.validate(trace)
            if not result["valid"]:
                print(f"WARN: {path} validation failed: {result['structural_errors']}", file=sys.stderr)
                return 0
        profile = analyzer.analyze(trace)
        dashboard.add_call_profile(profile)
        return 1
    except Exception as e:
        print(f"WARN: {path} error: {e}", file=sys.stderr)
        return 0


def render_report(agg: dict, window: int) -> str:
    """Render a markdown report from aggregated Phase 5 intelligence."""
    n = agg.get("total_calls", 0)
    tendencies = agg.get("tendencies", {})
    tag_counts = agg.get("tag_counts", {})
    heatmaps = agg.get("heatmaps", {})
    signal_dist = agg.get("signal_distributions", {})
    outcome_dist = agg.get("outcome_distribution", {})

    tagger = TaggingEngine()

    lines = [
        "# AQI Phase 5 Behavioral Intelligence Report",
        f"**Organism**: Alan",
        f"**Substrate**: AQI 0.1mm Chip",
        f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"**Calls analyzed**: {n}",
        f"**Window**: {'all' if window == 0 else window}",
        "",
        "---",
        "",
        "## 1. Executive Summary",
        "",
        f"- **Persistence**: {tendencies.get('persistence_bias', 'N/A')}",
        f"- **Caution**: {tendencies.get('caution_bias', 'N/A')}",
        f"- **Close Timing**: {tendencies.get('close_timing_bias', 'N/A')}",
        f"- **Objection Handling**: {tendencies.get('objection_handling_bias', 'N/A')}",
        f"- **Personality**: {tendencies.get('personality_stability', 'N/A')}",
        f"- **Conversion Rate**: {outcome_dist.get('conversion_rate', 0):.1%}",
        "",
        "---",
        "",
        "## 2. Tag Distribution",
        "",
        "### Positive Tags",
        "| Tag | Count |",
        "|-----|-------|",
    ]

    for tag in sorted(tag_counts.keys()):
        if tagger.is_positive(tag):
            lines.append(f"| {tag} | {tag_counts[tag]} |")

    lines.extend([
        "",
        "### Warning Tags",
        "| Tag | Count |",
        "|-----|-------|",
    ])

    for tag in sorted(tag_counts.keys()):
        if tagger.is_warning(tag):
            lines.append(f"| {tag} | {tag_counts[tag]} |")

    lines.extend([
        "",
        "---",
        "",
        "## 3. Continuum Heatmaps",
        "",
        "### State Axis",
        "| State | Turns |",
        "|-------|-------|",
    ])

    for state in ["OPENING", "DISCOVERY", "VALUE", "OBJECTION", "CLOSE", "EXIT"]:
        count = heatmaps.get("state_axis", {}).get(state, 0)
        lines.append(f"| {state} | {count} |")

    lines.extend([
        "",
        "### Health Axis",
        "| Level | Turns |",
        "|-------|-------|",
    ])

    for level in [1, 2, 3, 4]:
        count = heatmaps.get("health_axis", {}).get(level, 0)
        lines.append(f"| Level {level} | {count} |")

    lines.extend([
        "",
        "### Mission Axis (Exit Reasons)",
        "| Exit Reason | Count |",
        "|-------------|-------|",
    ])

    for reason, count in sorted(heatmaps.get("mission_axis", {}).items()):
        lines.append(f"| {reason} | {count} |")

    lines.extend([
        "",
        "---",
        "",
        "## 4. Signal Distributions",
        "",
    ])

    for signal_name, dist in sorted(signal_dist.items()):
        lines.append(f"### {signal_name.replace('_', ' ').title()}")
        lines.append(f"| Value | Count |")
        lines.append(f"|-------|-------|")
        for val, count in sorted(dist.items()):
            lines.append(f"| {val} | {count} |")
        lines.append("")

    lines.extend([
        "---",
        "",
        f"*Generated by AQI Phase 5 Behavioral Intelligence Engine*",
    ])

    return "\n".join(lines)


if __name__ == "__main__":
    main()
