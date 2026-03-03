"""
AQI Phase 5 — HTML Report Generator
======================================
Renders per-call and aggregate Phase 5 intelligence as HTML.
Uses string formatting (no external template engine required).

Part of the AQI 0.1mm Chip ecosystem.
"""

from datetime import datetime


def render_call_html_report(call_id: str, profile: dict) -> str:
    """Render a single call's Phase 5 profile as HTML."""
    tags = profile.get("tags", [])
    continuum = profile.get("continuum", {})
    signals = profile.get("signals", {})
    tags_split = profile.get("tags_split", {})

    positive_tags = tags_split.get("positive", [])
    warning_tags = tags_split.get("warning", [])

    # State dwell table
    state_dwell = continuum.get("state_axis", {}).get("state_dwell", {})
    state_rows = "\n".join(
        f"        <tr><td>{s}</td><td>{c}</td></tr>"
        for s, c in sorted(state_dwell.items())
    )

    # Health trajectory
    health = continuum.get("health_axis", {})
    health_trajectory = health.get("health_trajectory", [])

    # Mission
    mission = continuum.get("mission_axis", {})

    # Time
    time_axis = continuum.get("time_axis", {})

    # Signal rows
    signal_rows = "\n".join(
        f"        <tr><td>{k.replace('_', ' ').title()}</td><td>{v}</td></tr>"
        for k, v in sorted(signals.items())
    )

    # Tag lists
    pos_items = "\n".join(f"        <li class='tag-positive'>{t}</li>" for t in positive_tags)
    warn_items = "\n".join(f"        <li class='tag-warning'>{t}</li>" for t in warning_tags)

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Phase 5 Call Report — {call_id}</title>
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; max-width: 900px; margin: 40px auto; padding: 0 20px; color: #222; }}
        h1 {{ border-bottom: 3px solid #1a73e8; padding-bottom: 10px; }}
        h2 {{ color: #1a73e8; margin-top: 30px; }}
        table {{ border-collapse: collapse; width: 100%; margin: 10px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px 12px; text-align: left; }}
        th {{ background: #f5f5f5; font-weight: 600; }}
        .tag-positive {{ color: #0d7f3f; font-weight: 600; }}
        .tag-warning {{ color: #c62828; font-weight: 600; }}
        .meta {{ color: #666; font-size: 0.9em; }}
        .health-bar {{ display: flex; gap: 4px; }}
        .health-dot {{ width: 20px; height: 20px; border-radius: 50%; display: inline-block; }}
        .h1 {{ background: #4caf50; }}
        .h2 {{ background: #ffeb3b; }}
        .h3 {{ background: #ff9800; }}
        .h4 {{ background: #f44336; }}
    </style>
</head>
<body>
    <h1>Phase 5 Call Report</h1>
    <p class="meta">
        <strong>Call ID:</strong> {call_id}<br>
        <strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M')}<br>
        <strong>Total Turns:</strong> {time_axis.get('total_turns', 0)}<br>
        <strong>Exit Reason:</strong> {mission.get('exit_reason', 'N/A')}<br>
        <strong>Appointment Set:</strong> {'Yes' if mission.get('appointment_set') else 'No'}
    </p>

    <h2>Behavioral Tags</h2>
    <h3>Positive</h3>
    <ul>
{pos_items if pos_items else '        <li><em>None</em></li>'}
    </ul>
    <h3>Warnings</h3>
    <ul>
{warn_items if warn_items else '        <li><em>None</em></li>'}
    </ul>

    <h2>Behavioral Signals</h2>
    <table>
        <tr><th>Signal</th><th>Value</th></tr>
{signal_rows}
    </table>

    <h2>Continuum — State Axis</h2>
    <table>
        <tr><th>FSM State</th><th>Turns</th></tr>
{state_rows}
    </table>
    <p>Backtracks: {continuum.get('state_axis', {}).get('backtracks', 0)}</p>

    <h2>Continuum — Health Axis</h2>
    <p>Peak Degradation: Level {health.get('peak_degradation', 1)}</p>
    <p>Recovery Events: {health.get('recovery_events', 0)}</p>
    <div class="health-bar">
{''.join(f"<span class='health-dot h{l}'></span>" for l in health_trajectory[:20])}
    </div>

    <h2>Continuum — Mission Axis</h2>
    <p>Close Attempts: {mission.get('close_attempts', 0)}</p>
    <p>Escalations: {mission.get('escalations', 0)}</p>

    <h2>Continuum — Time Axis</h2>
    <p>First Objection Turn: {time_axis.get('first_objection_turn', 'N/A')}</p>
    <p>First Close Turn: {time_axis.get('first_close_turn', 'N/A')}</p>

    <hr>
    <p class="meta"><em>AQI Phase 5 Behavioral Intelligence Engine</em></p>
</body>
</html>"""

    return html


def render_aggregate_html_report(agg: dict) -> str:
    """Render aggregate Phase 5 intelligence as HTML."""
    n = agg.get("total_calls", 0)
    tendencies = agg.get("tendencies", {})
    tag_counts = agg.get("tag_counts", {})
    heatmaps = agg.get("heatmaps", {})
    outcome = agg.get("outcome_distribution", {})

    tag_rows = "\n".join(
        f"        <tr><td>{tag}</td><td>{count}</td></tr>"
        for tag, count in sorted(tag_counts.items(), key=lambda x: -x[1])
    )

    state_rows = "\n".join(
        f"        <tr><td>{s}</td><td>{c}</td></tr>"
        for s, c in sorted(heatmaps.get("state_axis", {}).items())
    )

    tendency_rows = "\n".join(
        f"        <tr><td>{k.replace('_', ' ').title()}</td><td>{v}</td></tr>"
        for k, v in sorted(tendencies.items())
    )

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Phase 5 Aggregate Report — {n} Calls</title>
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; max-width: 900px; margin: 40px auto; padding: 0 20px; color: #222; }}
        h1 {{ border-bottom: 3px solid #1a73e8; padding-bottom: 10px; }}
        h2 {{ color: #1a73e8; margin-top: 30px; }}
        table {{ border-collapse: collapse; width: 100%; margin: 10px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px 12px; text-align: left; }}
        th {{ background: #f5f5f5; font-weight: 600; }}
        .meta {{ color: #666; font-size: 0.9em; }}
    </style>
</head>
<body>
    <h1>Phase 5 Aggregate Intelligence</h1>
    <p class="meta">
        <strong>Calls Analyzed:</strong> {n}<br>
        <strong>Conversion Rate:</strong> {outcome.get('conversion_rate', 0):.1%}<br>
        <strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M')}
    </p>

    <h2>Behavioral Tendencies</h2>
    <table>
        <tr><th>Dimension</th><th>Tendency</th></tr>
{tendency_rows}
    </table>

    <h2>Tag Frequency</h2>
    <table>
        <tr><th>Tag</th><th>Count</th></tr>
{tag_rows}
    </table>

    <h2>State Heatmap</h2>
    <table>
        <tr><th>State</th><th>Total Turns</th></tr>
{state_rows}
    </table>

    <hr>
    <p class="meta"><em>AQI Phase 5 Behavioral Intelligence Engine</em></p>
</body>
</html>"""

    return html
