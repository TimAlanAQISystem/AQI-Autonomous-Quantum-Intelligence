"""
Governance Anomaly Heatmap
============================
Reads anomaly JSON reports from multiple Phase 5 cycles and generates
a cross-cycle anomaly heatmap showing anomaly density over time.

Usage:
    .venv\\Scripts\\python.exe tools/governance_anomaly_heatmap.py <cycle_dir> [output_path]

Example:
    .venv\\Scripts\\python.exe tools/governance_anomaly_heatmap.py phase5_cycles heatmap.png
"""

import sys
import os
import json
import glob

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

ANOMALY_TYPES = [
    "stuck_mode",
    "wild_swing",
    "entropy_explosion",
    "entropy_collapse",
    "prosody_inversion",
    "prosody_out_of_band",
]

ANOMALY_COLORS = {
    "stuck_mode":         "#E86A5F",
    "wild_swing":         "#F5A623",
    "entropy_explosion":  "#4A90E2",
    "entropy_collapse":   "#7B4F9D",
    "prosody_inversion":  "#50C878",
    "prosody_out_of_band": "#CC6677",
}


def load_anomaly_reports(cycle_dir):
    """Load all anomaly JSON files from cycle directories."""
    pattern = os.path.join(cycle_dir, "cycle_*", "*_anomalies.json")
    files = sorted(glob.glob(pattern))

    # Also check root-level anomaly files
    root_pattern = os.path.join(cycle_dir, "*_anomalies.json")
    files.extend(sorted(glob.glob(root_pattern)))

    reports = []
    for fpath in files:
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
                data["_source_file"] = fpath
                reports.append(data)
        except (json.JSONDecodeError, IOError) as e:
            print(f"  Warning: Could not load {fpath}: {e}")

    return reports


def build_heatmap_matrix(reports):
    """Build a matrix: rows = anomaly types, cols = cycles."""
    n_cycles = len(reports)
    n_types = len(ANOMALY_TYPES)

    matrix = np.zeros((n_types, n_cycles), dtype=float)

    for col, report in enumerate(reports):
        by_type = report.get("by_type", {})
        for row, atype in enumerate(ANOMALY_TYPES):
            matrix[row, col] = by_type.get(atype, 0)

    return matrix


def generate_heatmap(reports, output_path):
    """Generate cross-cycle anomaly heatmap."""
    if not HAS_MATPLOTLIB:
        print("ERROR: matplotlib not installed.")
        return False

    if not reports:
        print("ERROR: No anomaly reports found.")
        return False

    matrix = build_heatmap_matrix(reports)

    fig, ax = plt.subplots(figsize=(max(8, len(reports) * 1.2), 6))

    im = ax.imshow(matrix, cmap="YlOrRd", aspect="auto", interpolation="nearest")

    ax.set_yticks(range(len(ANOMALY_TYPES)))
    ax.set_yticklabels(ANOMALY_TYPES, fontsize=10)
    ax.set_xticks(range(len(reports)))
    ax.set_xticklabels([f"C{i+1}" for i in range(len(reports))], fontsize=10)

    ax.set_xlabel("Cycle", fontsize=12)
    ax.set_ylabel("Anomaly Type", fontsize=12)
    ax.set_title("Governance Anomaly Heatmap Across Cycles", fontsize=14)

    # Annotate cells with counts
    for row in range(matrix.shape[0]):
        for col in range(matrix.shape[1]):
            val = int(matrix[row, col])
            if val > 0:
                color = "white" if val > matrix.max() * 0.6 else "black"
                ax.text(col, row, str(val), ha="center", va="center",
                        fontsize=11, fontweight="bold", color=color)

    fig.colorbar(im, ax=ax, label="Count")
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    print(f"  Heatmap saved to: {output_path}")
    return True


def main():
    if len(sys.argv) < 2:
        print("Usage: python tools/governance_anomaly_heatmap.py <cycle_dir> [output_path]")
        return 1

    cycle_dir = sys.argv[1]
    if not os.path.isdir(cycle_dir):
        print(f"ERROR: Directory not found: {cycle_dir}")
        return 1

    output_path = sys.argv[2] if len(sys.argv) >= 3 else "governance_anomaly_heatmap.png"

    reports = load_anomaly_reports(cycle_dir)
    print(f"  Found {len(reports)} anomaly reports in {cycle_dir}")

    if not reports:
        print("  No anomaly data to visualize. Run governance_anomaly_detector.py first.")
        return 1

    success = generate_heatmap(reports, output_path)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
