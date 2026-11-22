"""
06 - Why we do not segment by game rounds (exploratory, simulation only).

`sum_gamerounds` is measured after assignment and is affected by the
treatment. This script simulates experiments with a KNOWN true effect and
compares three estimators:

  * randomised difference in retention (what the plan uses),
  * difference among "engaged" players who reached the first gate
    (rounds >= 30), a very tempting segmentation,
  * regression of retention on treatment adjusting for log(rounds).

Two scenarios: no true effect, and a true drop in retention.
The real dataset is NOT used, as promised in §8 of the analysis plan.

Run from the part1_cookie_cats folder:
    python scripts/06_post_treatment_bias.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyArrowPatch

from src import config
from src.simulation import estimate_three_ways, simulate_players

N_PLAYERS = 40_000
N_REPS = 300
THRESHOLD = 30
SCENARIOS = {"no true effect": 0.0, "true drop in retention": -0.06}


def draw_dag(path: Path) -> None:
    pos = {"T\n(gate at 40)": (0.1, 0.75), "U\n(engagement,\nunobserved)": (0.1, 0.15),
           "R\n(game rounds)": (0.55, 0.45), "Y\n(retention)": (0.95, 0.45)}
    fig, ax = plt.subplots(figsize=(6.5, 3.4))
    for label, (x, y) in pos.items():
        dashed = "U" in label
        ax.text(x, y, label, ha="center", va="center", fontsize=9,
                bbox=dict(boxstyle="round,pad=0.4", fc="white",
                          ec="grey" if dashed else "black", ls="--" if dashed else "-"))
    keys = list(pos)
    # (from, to, curvature): T->R, U->R straight; T->Y above R; U->Y below R
    edges = [(0, 2, 0.0), (1, 2, 0.0), (0, 3, -0.25), (1, 3, 0.3)]
    for a, b, rad in edges:
        (x1, y1), (x2, y2) = pos[keys[a]], pos[keys[b]]
        ax.add_patch(FancyArrowPatch((x1 + 0.08, y1), (x2 - 0.09, y2), arrowstyle="-|>",
                                     mutation_scale=14, color="black", lw=1,
                                     connectionstyle=f"arc3,rad={rad}"))
    ax.text(0.55, 0.92, "Conditioning on R opens the path T → R ← U → Y",
            ha="center", fontsize=9, color="#C44E52")
    ax.set_xlim(-0.05, 1.08)
    ax.set_ylim(0, 1)
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(path, dpi=150)


def main() -> None:
    config.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    config.FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(config.SEED)

    records = []
    for scen, beta in SCENARIOS.items():
        for rep in range(N_REPS):
            df, truth = simulate_players(N_PLAYERS, beta, rng=rng)
            for method, est in estimate_three_ways(df, THRESHOLD).items():
                records.append({"scenario": scen, "rep": rep, "method": method,
                                "estimate": est, "truth": truth})
    sims = pd.DataFrame(records)
    sims["error"] = sims["estimate"] - sims["truth"]
    summary = (sims.groupby(["scenario", "method"], sort=False)
               .agg(true_effect=("truth", "mean"), mean_estimate=("estimate", "mean"),
                    bias=("error", "mean"), sd=("estimate", "std"))
               .reset_index())
    summary.to_csv(config.RESULTS_DIR / "post_treatment_bias.csv", index=False)

    # Figure: distributions of estimates per method and scenario
    fig, axes = plt.subplots(1, len(SCENARIOS), figsize=(9, 3.6), sharey=True)
    for ax, scen in zip(axes, SCENARIOS):
        s = sims[sims.scenario == scen]
        methods = list(s["method"].unique())
        ax.boxplot([100 * s.loc[s.method == m, "estimate"] for m in methods],
                   vert=False, showfliers=False)
        ax.set_yticks(range(1, len(methods) + 1), [m.replace("_", " ") for m in methods], fontsize=8)
        ax.axvline(100 * s["truth"].mean(), color="#C44E52", ls="--", lw=1.2, label="true effect")
        ax.set_title(scen, fontsize=10)
        ax.set_xlabel("Estimated effect on retention (pp)")
    axes[0].legend(frameon=False, fontsize=8)
    fig.suptitle(f"Post-treatment bias: {N_REPS} simulated experiments per scenario", fontsize=11)
    fig.tight_layout()
    fig.savefig(config.FIGURES_DIR / "06_post_treatment_bias.png", dpi=150)
    draw_dag(config.FIGURES_DIR / "06_dag.png")

    lines = ["# Why we do not segment by game rounds (exploratory, simulation)", "",
             "Synthetic players with latent engagement U. The treatment increases game rounds "
             "(more levels before the first gate). Estimates are compared with the known true effect.", "",
             "![DAG](figures/06_dag.png)", "",
             "| Scenario | Method | True effect (pp) | Mean estimate (pp) | Bias (pp) |",
             "|---|---|---:|---:|---:|",
             *[f"| {r.scenario} | {r.method} | {100 * r.true_effect:+.2f} | {100 * r.mean_estimate:+.2f} "
               f"| {100 * r.bias:+.2f} |" for _, r in summary.iterrows()],
             "", "![Bias](figures/06_post_treatment_bias.png)", ""]
    (config.RESULTS_DIR / "post_treatment_report.md").write_text("\n".join(lines), encoding="utf-8")

    pd.set_option("display.float_format", "{:.4f}".format)
    print(summary[["scenario", "method", "true_effect", "mean_estimate", "bias"]].to_string(index=False))
    print(f"\nSaved report: {config.RESULTS_DIR / 'post_treatment_report.md'}")


if __name__ == "__main__":
    main()
