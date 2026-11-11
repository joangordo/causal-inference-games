"""
01 - Power analysis (design stage).

Answers two questions before looking at any result:
  1. How many players per arm would we need to detect the business MDE?
  2. Given the players actually enrolled, what is the smallest effect we can
     detect, and what power do we have for the business MDE?

Only the number of players per arm is read from the data. No outcome is
compared between arms.

Run from the part1_cookie_cats folder:
    python scripts/01_power_analysis.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src import config
from src.data import load_data
from src.power import achieved_power, mde_for_n, required_n_per_arm


def main() -> None:
    config.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    config.FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    df = load_data()
    n_arm = df["version"].value_counts()
    n_min = int(n_arm.min())  # the smaller arm limits power

    rows = []
    for metric in [config.PRIMARY_METRIC, *config.SECONDARY_METRICS]:
        p0, mde = config.BASELINE[metric], config.MDE_ABS[metric]
        rows.append({
            "metric": metric,
            "assumed_baseline": p0,
            "business_mde_abs": mde,
            "business_mde_rel": mde / p0,
            "required_n_per_arm": required_n_per_arm(p0, mde),
            "enrolled_n_per_arm_min": n_min,
            "achieved_mde_abs": mde_for_n(p0, n_min),
            "power_for_business_mde": achieved_power(p0, mde, n_min),
        })
    summary = pd.DataFrame(rows)
    summary.to_csv(config.RESULTS_DIR / "power_analysis.csv", index=False)

    # Figure: detectable effect as a function of sample size
    ns = np.logspace(3, np.log10(200_000), 60).astype(int)
    fig, ax = plt.subplots(figsize=(7, 4.2))
    for metric in summary["metric"]:
        p0 = config.BASELINE[metric]
        ax.plot(ns, [100 * mde_for_n(p0, n) for n in ns], label=f"{metric} (baseline {p0:.0%})")
    ax.axvline(n_min, ls="--", color="grey", lw=1)
    ax.text(n_min * 1.05, ax.get_ylim()[1] * 0.9, f"enrolled ≈ {n_min:,}/arm", color="grey", fontsize=9)
    ax.axhline(100 * config.MDE_ABS[config.PRIMARY_METRIC], ls=":", color="black", lw=1)
    ax.set_xscale("log")
    ax.set_xlabel("Players per arm (log scale)")
    ax.set_ylabel("Minimum detectable drop (pp)")
    ax.set_title(f"Minimum detectable effect (alpha={config.ALPHA}, power={config.POWER:.0%})")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(config.FIGURES_DIR / "01_mde_vs_sample_size.png", dpi=150)

    pd.set_option("display.float_format", "{:.4f}".format)
    print("\n=== Power analysis ===")
    print(summary.to_string(index=False))
    print(f"\nSaved: {config.RESULTS_DIR / 'power_analysis.csv'}")
    print(f"Saved: {config.FIGURES_DIR / '01_mde_vs_sample_size.png'}")


if __name__ == "__main__":
    main()
