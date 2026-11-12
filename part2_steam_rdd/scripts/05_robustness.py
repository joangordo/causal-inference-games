"""
05 - Validity and robustness of the primary estimate.

  * Density (manipulation) test in the analysis sample.
  * Covariate balance: pre-treatment characteristics and the lagged number of
    reviews should not jump at the cutoff.
  * Bandwidth sensitivity: 0.5x to 2x the optimal bandwidth.
  * Donut RDD: drop games within ±0.25 pp of the cutoff (rounding / heaping).
  * Placebo cutoffs at 75% and 85%, each estimated on one side only.

Run from the part2_steam_rdd folder:
    python scripts/05_robustness.py
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib.pyplot as plt
import pandas as pd

from src import config
from src.guard import plan_is_committed
from src.rdd import cutoff_sample, density_test, estimate


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    ok, msg = plan_is_committed(config.PLAN_PATH)
    if not ok and not args.force:
        sys.exit(f"STOP: {msg}\nCommit the analysis plan before estimating effects.")

    panel = pd.read_csv(config.PANEL_PATH)
    name, y = config.PRIMARY_CUTOFF, config.PRIMARY_OUTCOME
    spec = config.CUTOFFS[name]
    s = cutoff_sample(panel, name)
    main_est = estimate(s, y)
    if main_est.get("error"):
        sys.exit(f"STOP: primary estimate failed: {main_est['error']}")
    h0 = main_est["h"]

    dens = density_test(s.loc[s["x"].abs() <= 2 * h0, "x"].to_numpy())

    balance = []
    for cov in ["log_reviews_t1", *config.COVARIATE_COLUMNS]:
        if cov in s.columns:
            balance.append({"covariate": cov, "sample": "all", **estimate(s, cov)})
            balance.append({"covariate": cov, "sample": f"donut ±{config.DONUT_PP} pp",
                            **estimate(s, cov, donut=config.DONUT_PP)})
    balance = pd.DataFrame(balance)

    bw = pd.DataFrame([{"multiplier": m, **estimate(s, y, h=m * h0)} for m in config.BANDWIDTH_MULTIPLIERS])
    donut = estimate(s, y, donut=config.DONUT_PP)

    placebo = []
    for pc in config.PLACEBO_CUTOFFS:
        side = s[s["pct_positive_t1"] < spec["c"]] if pc < spec["c"] else s[s["pct_positive_t1"] >= spec["c"]]
        ps = cutoff_sample(side, name, c=pc)
        placebo.append({"placebo_c": pc, **estimate(ps, y, force_sharp=True)})
    placebo = pd.DataFrame(placebo)

    for df_, f in [(balance, "balance"), (bw, "bandwidth"), (placebo, "placebo")]:
        df_.to_csv(config.RESULTS_DIR / f"robustness_{f}.csv", index=False)

    ok_bw = bw.dropna(subset=["coef"])
    fig, ax = plt.subplots(figsize=(6.5, 3.6))
    ax.errorbar(ok_bw["multiplier"], ok_bw["coef"],
                yerr=[ok_bw["coef"] - ok_bw["ci_low_robust"], ok_bw["ci_high_robust"] - ok_bw["coef"]],
                fmt="o", capsize=4, color="#4C72B0")
    ax.axhline(0, color="black", lw=0.8)
    ax.set_xlabel("Bandwidth as a multiple of the optimal one")
    ax.set_ylabel("RDD estimate (95% robust CI)")
    ax.set_title("Bandwidth sensitivity, primary cutoff")
    fig.tight_layout()
    fig.savefig(config.FIGURES_DIR / "05_bandwidth_sensitivity.png", dpi=150)

    def est_row(label, r):
        if r.get("error"):
            return f"| {label} | — | — | — | {r['error']} |"
        return (f"| {label} | {r['coef']:+.4f} | [{r['ci_low_robust']:+.4f}, {r['ci_high_robust']:+.4f}] "
                f"| {r['p_robust']:.4f} | h = {r['h']:.2f} pp, n = {r['n_left_h']:,} + {r['n_right_h']:,} |")

    head = "| Check | Estimate | 95% robust CI | p | Detail |\n|---|---:|---|---:|---|"
    lines = ["# Validity and robustness (primary cutoff, primary outcome)", "",
             "## Density test", "",
             f"Cattaneo-Jansson-Ma test: p = {dens['p_value']:.4f} (n = {dens['n']:,}). "
             "A small p-value would suggest sorting around the cutoff.", "",
             "## Covariate balance (should show no jump)", "", head,
             *[est_row(f"{r['covariate']} ({r['sample']})", r) for _, r in balance.iterrows()], "",
             "`log_reviews_t1` is a lagged outcome: the label existed before t1, so a jump here "
             "may reflect past effects of the label rather than imbalance. Shares of positive "
             "reviews are ratios of integers, so games with few reviews pile up at exact values "
             "such as 80%; the donut version removes that mass point.", "",
             "## Bandwidth sensitivity", "", head,
             *[est_row(f"{r['multiplier']}× optimal", r) for _, r in bw.iterrows()], "",
             "![Bandwidth](figures/05_bandwidth_sensitivity.png)", "",
             "## Donut RDD", "", head, est_row(f"exclude |x| < {config.DONUT_PP} pp", donut), "",
             "## Placebo cutoffs (should show no effect)", "", head,
             *[est_row(f"c = {r['placebo_c']:.0%}", r) for _, r in placebo.iterrows()], ""]
    (config.RESULTS_DIR / "robustness_report.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
