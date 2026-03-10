"""
Quantum Trajectory Visualizer
===============================
Reads a Phase 5 cycle JSONL log and generates:
  1. Mode trajectory plot (dominant mode vs turn number)
  2. State component stacked area chart (5D state vector over turns)

Usage:
    .venv\\Scripts\\python.exe tools/quantum_trajectory.py <jsonl_path> [output_dir]
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

# ─── CANONICAL COLOR MAP ──────────────────────────────────────────────────
MODE_COLORS = {
    "wit":       "#E86A5F",
    "empathy":   "#F5A623",
    "precision": "#4A90E2",
    "patience":  "#7B4F9D",
    "entropy":   "#50C878",
}

DIMENSION_NAMES = ["wit", "empathy", "precision", "patience", "entropy"]
DIMENSION_COLORS = [MODE_COLORS[d] for d in DIMENSION_NAMES]


def load_records(jsonl_path):
    """Load turn records from JSONL file."""
    records = []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def plot_mode_trajectory(records, output_path):
    """Plot dominant mode vs turn number."""
    if not HAS_MATPLOTLIB:
        print("ERROR: matplotlib required.")
        return False

    turns = list(range(len(records)))
    dominants = [r.get("quantum_dominant", "precision") for r in records]

    # Encode modes as integers for y-axis
    mode_to_y = {name: i for i, name in enumerate(DIMENSION_NAMES)}
    y_vals = [mode_to_y.get(d, 2) for d in dominants]
    colors = [MODE_COLORS.get(d, "#888888") for d in dominants]

    fig, ax = plt.subplots(figsize=(12, 5))

    # Plot line + colored dots
    ax.plot(turns, y_vals, color="#cccccc", linewidth=1, zorder=1)
    ax.scatter(turns, y_vals, c=colors, s=100, zorder=2,
               edgecolors="black", linewidth=0.5)

    ax.set_yticks(range(len(DIMENSION_NAMES)))
    ax.set_yticklabels(DIMENSION_NAMES, fontsize=11)
    ax.set_xlabel("Turn Number", fontsize=12)
    ax.set_title("Quantum Dominant Mode Trajectory", fontsize=14)
    ax.grid(True, alpha=0.2, axis="x")

    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    print(f"  Mode trajectory saved to: {output_path}")
    return True


def plot_state_components(records, output_path):
    """Plot 5D state vector components as stacked area chart."""
    if not HAS_MATPLOTLIB:
        print("ERROR: matplotlib required.")
        return False

    turns = list(range(len(records)))

    # Extract state_vector_after from each record
    components = {d: [] for d in DIMENSION_NAMES}
    for r in records:
        sv = r.get("state_vector_after", [0.2, 0.2, 0.2, 0.2, 0.2])
        # Ensure we have 5 values
        while len(sv) < 5:
            sv.append(0.2)
        # Normalize to probabilities (Born rule)
        sq = [abs(v) ** 2 for v in sv]
        total = sum(sq)
        if total > 1e-10:
            sq = [s / total for s in sq]
        for i, name in enumerate(DIMENSION_NAMES):
            components[name].append(sq[i])

    fig, ax = plt.subplots(figsize=(12, 6))

    # Stacked area
    y_stack = np.array([components[d] for d in DIMENSION_NAMES])
    ax.stackplot(turns, y_stack, labels=DIMENSION_NAMES,
                 colors=DIMENSION_COLORS, alpha=0.8)

    ax.set_xlabel("Turn Number", fontsize=12)
    ax.set_ylabel("Trait Probability (Born rule)", fontsize=12)
    ax.set_title("Quantum State Components Over Time", fontsize=14)
    ax.legend(loc="upper right", fontsize=9)
    ax.set_ylim(0, 1)
    ax.grid(True, alpha=0.2)

    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    print(f"  State components saved to: {output_path}")
    return True


def main():
    if len(sys.argv) < 2:
        print("Usage: python tools/quantum_trajectory.py <jsonl_path> [output_dir]")
        return 1

    jsonl_path = sys.argv[1]
    if not os.path.exists(jsonl_path):
        print(f"ERROR: File not found: {jsonl_path}")
        return 1

    if len(sys.argv) >= 3:
        output_dir = sys.argv[2]
    else:
        output_dir = os.path.dirname(jsonl_path) or "."

    os.makedirs(output_dir, exist_ok=True)

    records = load_records(jsonl_path)
    if not records:
        print("ERROR: No records found.")
        return 1

    print(f"  Loaded {len(records)} records from {jsonl_path}")

    base = os.path.splitext(os.path.basename(jsonl_path))[0]

    ok1 = plot_mode_trajectory(
        records,
        os.path.join(output_dir, f"{base}_mode_trajectory.png")
    )
    ok2 = plot_state_components(
        records,
        os.path.join(output_dir, f"{base}_state_components.png")
    )

    return 0 if (ok1 and ok2) else 1


if __name__ == "__main__":
    sys.exit(main())
