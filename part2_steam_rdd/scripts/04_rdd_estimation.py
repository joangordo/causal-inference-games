"""
04 - RDD estimation (confirmatory, as pre-registered).

For each cutoff and outcome: local-linear RDD with MSE-optimal bandwidth and
robust bias-corrected inference. Sharp design if at least 99% of games carry
the label expected for their side of the cutoff, fuzzy otherwise.

Refuses to run until analysis_plan.md is committed (use --force only for testing).

Run from the part2_steam_rdd folder:
    python scripts/04_rdd_estimation.py
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib.pyplot as plt
import pandas as pd

from src import config
from src.guard import plan_is_committed
from src.rdd import binned_means, cutoff_sample, estimate, local_linear_fit


def rd_plot(s: pd.DataFrame, outcome: str, h: float, spec: dict, path: Path) -> None:
    bins = binned_means(s, outcome, width_pp=0.5, max_abs_pp=max(10.0, h))
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.scatter(bins["x"], bins["y"], s=12 + 60 * bins["n"] / bins["n"].max(), color="#4C72B0", alpha=0.8)
    for side in ("left", "right"):
        gx, gy = local_linear_fit(s, outcome, h, side)
        ax.plot(gx, gy, color="#C44E52", lw=2)
    ax.axvline(0, color="black", lw=0.8)
    ax.axvspan(-h, h, color="grey", alpha=0.08, label=f"bandwidth ±{h:.1f} pp")
    ax.set_xlabel(f"Share of positive reviews − {spec['c']:.0%} (pp)")
    ax.set_ylabel(outcome.replace("_", " "))
    ax.set_title(f"{spec['below']} → {spec['above']}")
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=150)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    ok, msg = plan_is_committed(config.PLAN_PATH)
    if not ok and not args.force:
        sys.exit(f"STOP: {msg}\nCommit the analysis plan before estimating effects.")
    msg = msg if ok else f"WARNING: run with --force. {msg}"
    print(msg)

    config.FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    panel = pd.read_csv(config.PANEL_PATH)
    outcomes = [config.PRIMARY_OUTCOME, *config.SECONDARY_OUTCOMES]

    rows = []
    for name, spec in config.CUTOFFS.items():
        s = cutoff_sample(panel, name)
        for outcome in outcomes:
            r = estimate(s, outcome)
            role = "primary" if (name == config.PRIMARY_CUTOFF and outcome == config.PRIMARY_OUTCOME) else "secondary"
            rows.append({"cutoff": name, "outcome": outcome, "role": role, **r})
            if r.get("error") is None and outcome == config.PRIMARY_OUTCOME:
                rd_plot(s, outcome, r["h"], spec, config.FIGURES_DIR / f"04_rdplot_{name}.png")
    res = pd.DataFrame(rows)
    res.to_csv(config.RESULTS_DIR / "rdd_estimates.csv", index=False)

    def fmt(r):
        if r.get("error"):
            return f"| {r['cutoff']} | {r['outcome']} | {r['role']} | — | — | — | — | {r['error']} |"
        return (f"| {r['cutoff']} | {r['outcome']} | {r['role']} | {r['coef']:+.4f} "
                f"| [{r['ci_low_robust']:+.4f}, {r['ci_high_robust']:+.4f}] | {r['p_robust']:.4f} "
                f"| {r['h']:.2f} pp | {r['design']}, n = {r['n_left_h']:,} + {r['n_right_h']:,} |")

    lines = ["# RDD estimates (confirmatory)", "", f"_{msg}_", "",
             "Effect of being just above the cutoff (better label) on the outcome. "
             "Robust bias-corrected 95% CI. For `log_review_growth`, a coefficient of 0.05 "
             "means roughly 5% more growth in reviews between snapshots.", "",
             "| Cutoff | Outcome | Role | Estimate | 95% robust CI | p | Bandwidth | Design, n in bandwidth |",
             "|---|---|---|---:|---|---:|---:|---|",
             *[fmt(r) for r in rows], ""]
    lines += [f"![RD plot {n}](figures/04_rdplot_{n}.png)" for n in config.CUTOFFS
              if (config.FIGURES_DIR / f"04_rdplot_{n}.png").exists()]
    (config.RESULTS_DIR / "rdd_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    pd.set_option("display.float_format", "{:.4f}".format)
    pd.set_option("display.width", 160)
    cols = ["cutoff", "outcome", "design", "coef", "ci_low_robust", "ci_high_robust", "p_robust", "h", "error"]
    print(res[[c for c in cols if c in res.columns]].to_string(index=False))
    print(f"\nSaved report: {config.RESULTS_DIR / 'rdd_report.md'}")


if __name__ == "__main__":
    main()
