"""
02 - Validity checks (blind to outcomes by arm).

  * Sample ratio mismatch (SRM) test on the number of players per arm.
  * Pooled data-quality report: duplicates, zero-round players, logical
    inconsistencies, distribution of game rounds.
  * Outlier listing on the pooled sample (nothing is removed here).

Writes results/validity_report.md, results/outliers_top.csv and a figure.

Run from the part1_cookie_cats folder:
    python scripts/02_validity_checks.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib.pyplot as plt
import numpy as np

from src import config
from src.data import load_data
from src.validity import flag_outliers, pooled_quality_report, srm_test


def write_report(srm, quality, outliers, path: Path) -> None:
    verdict = ("**SRM DETECTED** - investigate before estimating effects."
               if srm.srm_detected else "No SRM detected at the pre-specified threshold.")
    lines = [
        "# Validity checks (blind to outcomes by arm)",
        "",
        "## Sample ratio mismatch",
        "",
        "| Arm | Observed | Expected | Share |",
        "|---|---:|---:|---:|",
        *[f"| {a} | {srm.observed[a]:,} | {srm.expected[a]:,.1f} | {srm.observed_share[a]:.4f} |"
          for a in srm.observed],
        "",
        f"Chi-square = {srm.chi2:.3f}, p-value = {srm.p_value:.4g} "
        f"(threshold alpha_SRM = {srm.alpha}).",
        "",
        verdict,
        "",
        "## Pooled data quality",
        "",
        "```json",
        json.dumps(quality, indent=2),
        "```",
        "",
        "## Most extreme players by game rounds (pooled)",
        "",
        outliers.to_markdown(index=False, floatfmt=".2f"),
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    config.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    config.FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    df = load_data()

    counts = df["version"].value_counts().to_dict()
    srm = srm_test(counts)
    quality = pooled_quality_report(df)
    outliers = flag_outliers(df)

    write_report(srm, quality, outliers, config.RESULTS_DIR / "validity_report.md")
    outliers.to_csv(config.RESULTS_DIR / "outliers_top.csv", index=False)

    # Pooled distribution of game rounds (no arm split on purpose)
    fig, ax = plt.subplots(figsize=(7, 4.2))
    ax.hist(np.log1p(df["sum_gamerounds"]), bins=60, color="#4C72B0")
    cap = config.OUTLIER_ROUNDS_HARD_CAP
    ax.axvline(np.log1p(cap), ls="--", color="crimson", lw=1)
    ax.text(np.log1p(cap) * 0.98, ax.get_ylim()[1] * 0.9, f"hard cap = {cap:,}",
            color="crimson", ha="right", fontsize=9)
    ax.set_xlabel("log(1 + game rounds in first 14 days)")
    ax.set_ylabel("Players")
    ax.set_title("Pooled distribution of game rounds")
    fig.tight_layout()
    fig.savefig(config.FIGURES_DIR / "02_rounds_pooled_distribution.png", dpi=150)

    print("\n=== SRM test ===")
    for arm in srm.observed:
        print(f"  {arm}: {srm.observed[arm]:,} players ({srm.observed_share[arm]:.4f})")
    print(f"  chi2 = {srm.chi2:.3f}, p = {srm.p_value:.4g} -> "
          f"{'SRM DETECTED' if srm.srm_detected else 'no SRM'} (alpha_SRM = {srm.alpha})")
    print("\n=== Pooled quality ===")
    print(json.dumps(quality, indent=2))
    print("\n=== Top outliers (pooled) ===")
    print(outliers.to_string(index=False))
    print(f"\nSaved report: {config.RESULTS_DIR / 'validity_report.md'}")


if __name__ == "__main__":
    main()
