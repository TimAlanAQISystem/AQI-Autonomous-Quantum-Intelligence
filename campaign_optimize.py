# campaign_optimize.py

import argparse
from campaign_behavior_audit import load_calls, summarize
from campaign_optimization_engine import CampaignOptimizationEngine


def print_optimization_report(opt):
    print("\n=== CAMPAIGN OPTIMIZATION REPORT ===")
    print(f"Readiness Score: {opt['readiness_score']}/100")
    print(f"Stall Rate:       {opt['stall_rate']:.3f}")
    print(f"Collapse Rate:    {opt['collapse_rate']:.3f}")
    print(f"Friction Rate:    {opt['friction_rate']:.3f}")
    print(f"HARD_KILL Rate:   {opt['hard_kill_rate']:.3f}")
    print(f"SOFT_KILL Rate:   {opt['soft_kill_rate']:.3f}")

    recs = opt["recommendations"]

    def section(title, items):
        print(f"\n--- {title} ---")
        if not items:
            print("No changes recommended.")
        else:
            for r in items:
                print(f"- {r}")

    section("Thresholds", recs["thresholds"])
    section("Fluidic Kernel", recs["fluidic_kernel"])
    section("Classifier / Routing", recs["classifier"])
    section("STT / TTS", recs["stt_tts"])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=7, help="How many days back to optimize over")
    args = parser.parse_args()

    # Reuse logic from audit script
    rows = load_calls(args.days)
    if not rows:
        print("No calls found to optimize.")
        return

    summary = summarize(rows)

    engine = CampaignOptimizationEngine()
    opt = engine.analyze(summary)
    print_optimization_report(opt)


if __name__ == "__main__":
    main()
