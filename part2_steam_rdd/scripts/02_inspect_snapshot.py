"""
02 - Inspect a snapshot (uses ONLY the first snapshot: no outcome data).

  * Cross-tab of numeric review_score vs label text (checks the code mapping).
  * Empirical switch points: for each cutoff, the highest share of positive
    reviews still labelled "below" and the lowest labelled "above". This tells
    us whether labels switch exactly at 80% or at a rounded value (e.g. 79.5%).
  * Compliance with the expected label, number of games near each cutoff.
  * Density (manipulation) test of the running variable at each cutoff.

Use the output to confirm or adjust the cutoffs in src/config.py and
analysis_plan.md BEFORE committing the plan and taking the second snapshot.

Run from the part2_steam_rdd folder:
    python scripts/02_inspect_snapshot.py --label t1
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src import config
from src.rdd import add_running_variable, compliance, cutoff_sample, density_test
from src.snapshot import load_snapshot


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", default="t1")
    args = ap.parse_args()
    config.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    config.FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    snap = load_snapshot(args.label)
    df = add_running_variable(snap.add_suffix("_t1").rename(columns={"appid_t1": "appid"}))

    xtab = pd.crosstab(df["review_score_t1"], df["review_score_desc_t1"])
    mismatched = {s: lab for s, lab in config.SCORE_LABELS.items()
                  if s != 0 and s in xtab.index and lab in xtab.columns and xtab.loc[s, lab] < xtab.loc[s].sum()}

    rows, near = [], []
    for name, spec in config.CUTOFFS.items():
        s = cutoff_sample(df, name)
        below = s.loc[s["treated"] == 0, "pct_positive_t1"]
        above = s.loc[s["treated"] == 1, "pct_positive_t1"]
        # Only look locally around the theoretical cutoff
        local_below = below[(below > spec["c"] - 0.05)]
        local_above = above[(above < spec["c"] + 0.05)]
        dens = density_test(s.loc[s["x"].abs() <= 10, "x"].to_numpy())
        rows.append({
            "cutoff": name, "theoretical_c": spec["c"], "min_reviews": spec["min_reviews"],
            "n_eligible": len(s),
            "max_pct_labelled_below": float(local_below.max()) if len(local_below) else np.nan,
            "min_pct_labelled_above": float(local_above.min()) if len(local_above) else np.nan,
            "compliance": compliance(s),
            "n_within_2pp": int((s["x"].abs() <= 2).sum()),
            "n_within_5pp": int((s["x"].abs() <= 5).sum()),
            "density_p_value": dens["p_value"],
        })
        near.append(s.assign(cutoff=name))
    summary = pd.DataFrame(rows)
    summary.to_csv(config.RESULTS_DIR / f"snapshot_{args.label}_inspection.csv", index=False)

    # Figure: share labelled "above" by bin of the running variable, per cutoff
    fig, axes = plt.subplots(1, len(config.CUTOFFS), figsize=(11, 3.4), sharey=True)
    for ax, s, (name, spec) in zip(axes, near, config.CUTOFFS.items()):
        d = s[s["x"].abs() <= 5]
        bins = np.arange(-5, 5.25, 0.25)
        g = d.groupby(pd.cut(d["x"], bins, right=False), observed=True)["treated"].mean()
        mids = [iv.mid for iv in g.index]
        ax.plot(mids, g.values, "o", ms=3)
        ax.axvline(0, color="black", lw=0.8)
        ax.set_title(f"{spec['below']} → {spec['above']}\n(c = {spec['c']:.0%}, ≥{spec['min_reviews']} reviews)",
                     fontsize=9)
        ax.set_xlabel("Share positive − cutoff (pp)")
    axes[0].set_ylabel("Share labelled 'above'")
    fig.tight_layout()
    fig.savefig(config.FIGURES_DIR / f"02_label_switch_{args.label}.png", dpi=150)

    fig, ax = plt.subplots(figsize=(7, 3.6))
    s = near[0]
    ax.hist(s.loc[s["x"].abs() <= 10, "x"], bins=np.arange(-10, 10.25, 0.25), color="#4C72B0")
    ax.axvline(0, color="crimson", lw=1)
    ax.set_xlabel("Share positive − 80% (pp)")
    ax.set_ylabel("Games")
    ax.set_title("Distribution of the running variable around the primary cutoff")
    fig.tight_layout()
    fig.savefig(config.FIGURES_DIR / f"02_running_variable_{args.label}.png", dpi=150)

    lines = [f"# Snapshot {args.label}: inspection (no outcome data)", "",
             f"Games with a valid summary: {len(df):,}.", "",
             "## review_score code vs label", "", xtab.to_markdown(), "",
             ("All codes map to the expected label." if not mismatched
              else f"**Codes with unexpected labels:** {mismatched}"), "",
             "## Cutoffs", "", summary.to_markdown(index=False, floatfmt=".4f"), "",
             f"![Switch](figures/02_label_switch_{args.label}.png)", "",
             f"![Running variable](figures/02_running_variable_{args.label}.png)", ""]
    (config.RESULTS_DIR / f"snapshot_{args.label}_inspection.md").write_text("\n".join(lines), encoding="utf-8")

    pd.set_option("display.float_format", "{:.4f}".format)
    pd.set_option("display.width", 160)
    print(f"Games with valid summary: {len(df):,}")
    print("\nreview_score vs label:\n", xtab.to_string())
    print("\n", summary.to_string(index=False))
    print(f"\nSaved: {config.RESULTS_DIR / f'snapshot_{args.label}_inspection.md'}")


if __name__ == "__main__":
    main()
