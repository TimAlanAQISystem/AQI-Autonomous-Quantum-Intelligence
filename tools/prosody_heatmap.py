"""
Prosody Heatmap Generator
==========================
Reads a Phase 5 cycle JSONL log and generates a heatmap of
prosody bias (speed_mod × silence_mod) colored by quantum dominant mode.

Usage:
    .venv\\Scripts\\python.exe tools/prosody_heatmap.py <jsonl_path> [output_path]
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
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


def load_records(jsonl_path):
    """Load turn records from JSONL file."""
    records = []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def generate_heatmap(records, output_path):
    """Generate prosody bias scatter/heatmap."""
    if not HAS_MATPLOTLIB:
        print("ERROR: matplotlib not installed. Install with:")
        print("  .venv\\Scripts\\pip.exe install matplotlib")
        return False

    speed_mods = []
    silence_mods = []
    colors = []
    labels = []

    for r in records:
        pb = r.get("prosody_bias", {})
        dominant = r.get("quantum_dominant", "precision")

        speed = pb.get("speed_mod", 0)
        silence = pb.get("silence_mod", 0)

        speed_mods.append(speed)
        silence_mods.append(silence)
        colors.append(MODE_COLORS.get(dominant, "#888888"))
        labels.append(dominant)

    fig, ax = plt.subplots(figsize=(10, 7))

    ax.scatter(speed_mods, silence_mods, c=colors, s=80, alpha=0.7,
               edgecolors="black", linewidth=0.5)

    # Acceptance band overlay
    ax.axvline(x=-0.08, color="red", linestyle="--", alpha=0.3, label="speed_mod bounds")
    ax.axvline(x=0.08, color="red", linestyle="--", alpha=0.3)
    ax.axhline(y=-3, color="blue", linestyle="--", alpha=0.3, label="silence_mod bounds")
    ax.axhline(y=3, color="blue", linestyle="--", alpha=0.3)

    ax.set_xlabel("speed_mod", fontsize=12)
    ax.set_ylabel("silence_mod (frames)", fontsize=12)
    ax.set_title("Prosody Bias Heatmap — Colored by Quantum Dominant Mode", fontsize=14)

    # Legend
    patches = [
        mpatches.Patch(color=c, label=name)
        for name, c in MODE_COLORS.items()
    ]
    ax.legend(handles=patches, loc="upper right", fontsize=9)

    ax.grid(True, alpha=0.2)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    print(f"  Heatmap saved to: {output_path}")
    return True


def main():
    if len(sys.argv) < 2:
        print("Usage: python tools/prosody_heatmap.py <jsonl_path> [output_path]")
        print("  Generates a prosody bias scatter plot from Phase 5 JSONL data.")
        return 1

    jsonl_path = sys.argv[1]
    if not os.path.exists(jsonl_path):
        print(f"ERROR: File not found: {jsonl_path}")
        return 1

    if len(sys.argv) >= 3:
        output_path = sys.argv[2]
    else:
        base = os.path.splitext(jsonl_path)[0]
        output_path = base + "_prosody_heatmap.png"

    records = load_records(jsonl_path)
    if not records:
        print("ERROR: No records found in JSONL file.")
        return 1

    print(f"  Loaded {len(records)} records from {jsonl_path}")
    success = generate_heatmap(records, output_path)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
