"""
05 - Peeking and sequential testing (exploratory, simulation only).

The dataset has no timestamps, so this uses simulation calibrated to the
experiment design (baseline D7 retention, business MDE).

  A. A/A tests: how the false positive rate grows if we check the p-value
     at every interim look and stop at the first p < 0.05.
     The Brownian approximation is validated against real binomial data.
  B. Fourteen daily looks: naive peeking vs Pocock and O'Brien-Fleming
     boundaries. Type I error, power at the MDE and expected sample used.

Run from the part1_cookie_cats folder:
    python scripts/05_peeking_simulation.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src import config
from src.power import required_n_per_arm
from src.sequential import (calibrate_boundary, final_z_for_mde, naive_boundary,
                            operating_characteristics, simulate_binomial_z_paths,
                            simulate_z_paths)

LOOKS_GRID = [1, 2, 3, 5, 7, 10, 14, 20, 30, 50, 100]
DAILY_LOOKS = 14
N_SIMS = 100_000


def main() -> None:
    config.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    config.FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(config.SEED)

    p0 = config.BASELINE[config.PRIMARY_METRIC]
    mde = config.MDE_ABS[config.PRIMARY_METRIC]
    n_design = required_n_per_arm(p0, mde)            # fixed test with 80% power
    delta = final_z_for_mde(p0, mde, n_design)

    # --- A. False positive rate vs number of looks ------------------------------
    rows = []
    for k in LOOKS_GRID:
        z = simulate_z_paths(k, N_SIMS, 0.0, rng)
        rows.append({"n_looks": k,
                     "false_positive_rate": operating_characteristics(z, naive_boundary(k))["reject_rate"]})
    fpr = pd.DataFrame(rows)

    # Validation with real binomial data at 10 looks
    zb = simulate_binomial_z_paths(p0, p0, n_design, 10, 20_000, rng)
    fpr_binom_10 = operating_characteristics(zb, naive_boundary(10))["reject_rate"]
    fpr_brown_10 = float(fpr.loc[fpr.n_looks == 10, "false_positive_rate"].iloc[0])

    # --- B. Fourteen daily looks: three strategies --------------------------------------
    boundaries = {
        "naive peeking (p < 0.05 every day)": naive_boundary(DAILY_LOOKS),
        "Pocock": calibrate_boundary("pocock", DAILY_LOOKS, rng=rng),
        "O'Brien-Fleming": calibrate_boundary("obrien_fleming", DAILY_LOOKS, rng=rng),
    }
    z_h0 = simulate_z_paths(DAILY_LOOKS, N_SIMS, 0.0, rng)
    z_h1 = simulate_z_paths(DAILY_LOOKS, N_SIMS, delta, rng)
    seq_rows = []
    for name, b in boundaries.items():
        h0 = operating_characteristics(z_h0, b)
        h1 = operating_characteristics(z_h1, b)
        seq_rows.append({"strategy": name, "type_I_error": h0["reject_rate"],
                         "power_at_mde": h1["reject_rate"],
                         "expected_sample_H0": h0["expected_sample_fraction"],
                         "expected_sample_H1": h1["expected_sample_fraction"],
                         "first_look_critical_z": b[0], "last_look_critical_z": b[-1]})
    seq_rows.append({"strategy": "fixed sample (one look at the end)", "type_I_error": config.ALPHA,
                     "power_at_mde": config.POWER, "expected_sample_H0": 1.0, "expected_sample_H1": 1.0,
                     "first_look_critical_z": np.nan, "last_look_critical_z": naive_boundary(1)[0]})
    seq = pd.DataFrame(seq_rows)

    fpr.to_csv(config.RESULTS_DIR / "peeking_fpr.csv", index=False)
    seq.to_csv(config.RESULTS_DIR / "sequential_designs.csv", index=False)

    # --- Figures ------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(7, 3.8))
    ax.plot(fpr.n_looks, 100 * fpr.false_positive_rate, "o-", color="#C44E52")
    ax.axhline(100 * config.ALPHA, ls="--", color="black", lw=1, label="nominal 5%")
    ax.set_xscale("log")
    ax.set_xlabel("Number of interim looks (log scale)")
    ax.set_ylabel("False positive rate (%)")
    ax.set_title("A/A tests: stopping at the first p < 0.05")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(config.FIGURES_DIR / "05_peeking_fpr.png", dpi=150)

    fig, ax = plt.subplots(figsize=(7, 3.8))
    days = np.arange(1, DAILY_LOOKS + 1)
    for name, b in boundaries.items():
        ax.plot(days, b, "o-", ms=3, label=name)
    ax.set_xlabel("Day of the experiment (interim look)")
    ax.set_ylabel("Critical |z| to stop")
    ax.set_title("Stopping boundaries with 14 daily looks")
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(config.FIGURES_DIR / "05_sequential_boundaries.png", dpi=150)

    # --- Report ------------------------------------------------------------------
    lines = ["# Peeking and sequential testing (exploratory, simulation)", "",
             f"Design: baseline D7 = {p0:.0%}, MDE = {100 * mde:g} pp, fixed-sample size "
             f"{n_design:,} players/arm (80% power). {N_SIMS:,} simulated experiments per scenario.", "",
             "## A. False positive rate when peeking", "",
             "| Looks | False positive rate |", "|---:|---:|",
             *[f"| {int(k)} | {100 * v:.1f}% |" for k, v in zip(fpr.n_looks, fpr.false_positive_rate)],
             "", f"Validation at 10 looks: Brownian approximation {100 * fpr_brown_10:.1f}% vs "
             f"binomial simulation {100 * fpr_binom_10:.1f}%.", "",
             "![Peeking](figures/05_peeking_fpr.png)", "",
             "## B. Fourteen daily looks", "",
             "| Strategy | Type I error | Power at MDE | E[sample] under H0 | E[sample] under H1 |",
             "|---|---:|---:|---:|---:|",
             *[f"| {r.strategy} | {100 * r.type_I_error:.1f}% | {100 * r.power_at_mde:.1f}% "
               f"| {100 * r.expected_sample_H0:.0f}% | {100 * r.expected_sample_H1:.0f}% |"
               for _, r in seq.iterrows()],
             "", "![Boundaries](figures/05_sequential_boundaries.png)", ""]
    (config.RESULTS_DIR / "peeking_report.md").write_text("\n".join(lines), encoding="utf-8")

    pd.set_option("display.float_format", "{:.4f}".format)
    print("=== A. False positive rate vs looks ===")
    print(fpr.to_string(index=False))
    print(f"Validation (10 looks): Brownian {fpr_brown_10:.4f} vs binomial {fpr_binom_10:.4f}")
    print("\n=== B. 14 daily looks ===")
    print(seq[["strategy", "type_I_error", "power_at_mde", "expected_sample_H0",
               "expected_sample_H1"]].to_string(index=False))
    print(f"\nSaved report: {config.RESULTS_DIR / 'peeking_report.md'}")


if __name__ == "__main__":
    main()
