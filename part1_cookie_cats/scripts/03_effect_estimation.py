"""
03 - Effect estimation (confirmatory analysis, as pre-registered).

  * Retention (primary D7, secondary D1): difference in proportions, z-test,
    Wald and bootstrap CIs, relative lift, Holm correction, decision rule.
  * Guardrail (game rounds): difference in means with bootstrap CI, raw and
    winsorised at the pooled quantile, plus Mann-Whitney U as robustness.

Safety checks before estimating anything:
  1. analysis_plan.md must be committed in git with no pending changes
     (skip with --force only if you understand what you are giving up).
  2. The SRM test must pass the pre-specified threshold.

Run from the part1_cookie_cats folder:
    python scripts/03_effect_estimation.py
"""
import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

from src import config
from src.data import load_data
from src.estimation import bootstrap_mean_diff, decide, holm_adjust, two_proportion_effect
from src.validity import srm_test, winsorise_pooled

PLAN = config.PART1_DIR / "analysis_plan.md"


def plan_is_committed() -> tuple[bool, str]:
    """True if analysis_plan.md is tracked by git and has no uncommitted changes."""
    try:
        cwd = str(config.PART1_DIR)
        tracked = subprocess.run(["git", "ls-files", "--error-unmatch", PLAN.name],
                                 cwd=cwd, capture_output=True, text=True)
        if tracked.returncode != 0:
            return False, "analysis_plan.md is not committed to git yet."
        dirty = subprocess.run(["git", "status", "--porcelain", PLAN.name],
                               cwd=cwd, capture_output=True, text=True)
        if dirty.stdout.strip():
            return False, "analysis_plan.md has uncommitted changes."
        last = subprocess.run(["git", "log", "-1", "--format=%h %ci", "--", PLAN.name],
                              cwd=cwd, capture_output=True, text=True)
        return True, f"Plan committed in {last.stdout.strip()}"
    except FileNotFoundError:
        return False, "git is not installed or not in PATH."


def retention_effects(df: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    metrics = [config.PRIMARY_METRIC, *config.SECONDARY_METRICS]
    rows = []
    for m in metrics:
        g = df.groupby("version", observed=True)[m].agg(["sum", "count"])
        res = two_proportion_effect(int(g.loc[config.CONTROL, "sum"]), int(g.loc[config.CONTROL, "count"]),
                                    int(g.loc[config.TREATMENT, "sum"]), int(g.loc[config.TREATMENT, "count"]),
                                    rng=rng)
        rows.append({"metric": m, "role": "primary" if m == config.PRIMARY_METRIC else "secondary", **res})
    out = pd.DataFrame(rows)
    out["p_holm"] = holm_adjust(out["p_value"].tolist())
    out["significant_holm"] = out["p_holm"] < config.ALPHA
    return out


def guardrail_effects(df: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    m = config.GUARDRAIL_METRIC
    wins, cap = winsorise_pooled(df[m])
    rows = []
    for label, series in [("raw", df[m]), (f"winsorised (cap={cap:.0f})", wins)]:
        c = series[df["version"] == config.CONTROL].to_numpy()
        t = series[df["version"] == config.TREATMENT].to_numpy()
        diff, low, high = bootstrap_mean_diff(c, t, rng=rng)
        rows.append({"version": label, "mean_control": c.mean(), "mean_treatment": t.mean(),
                     "median_control": np.median(c), "median_treatment": np.median(t),
                     "diff_mean": diff, "boot_ci_low": low, "boot_ci_high": high})
    out = pd.DataFrame(rows)
    c = df.loc[df["version"] == config.CONTROL, m]
    t = df.loc[df["version"] == config.TREATMENT, m]
    out["mannwhitney_p"] = stats.mannwhitneyu(t, c, alternative="two-sided").pvalue
    return out


def plot_effects(ret: pd.DataFrame, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(7, 3.6))
    y = np.arange(len(ret))[::-1]
    pp = 100
    ax.errorbar(ret["diff"] * pp, y,
                xerr=[(ret["diff"] - ret["wald_ci_low"]) * pp, (ret["wald_ci_high"] - ret["diff"]) * pp],
                fmt="o", color="#4C72B0", capsize=4, label="95% Wald CI")
    ax.scatter(ret["boot_ci_low"] * pp, y, marker="|", s=200, color="#DD8452", label="95% bootstrap CI")
    ax.scatter(ret["boot_ci_high"] * pp, y, marker="|", s=200, color="#DD8452")
    mde = config.MDE_ABS[config.PRIMARY_METRIC] * pp
    ax.axvspan(-mde, mde, color="grey", alpha=0.12, label=f"±{mde:g} pp (business MDE)")
    ax.axvline(0, color="black", lw=0.8)
    ax.set_yticks(y, ret["metric"])
    ax.set_xlabel(f"Difference {config.TREATMENT} − {config.CONTROL} (percentage points)")
    ax.set_title("Effect of moving the first gate to level 40")
    ax.set_ylim(-0.6, len(ret) - 0.4)
    ax.legend(frameon=False, fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.25), ncol=3)
    fig.tight_layout()
    fig.savefig(path, dpi=150)


def write_report(ret: pd.DataFrame, guard: pd.DataFrame, decision: str, plan_msg: str, path: Path) -> None:
    def pct(x):
        return f"{100 * x:+.2f} pp"

    lines = ["# Effect estimation (confirmatory)", "", f"_{plan_msg}_", "",
             "## Decision (primary metric, rule from §7 of the plan)", "", f"**{decision}**", "",
             "## Retention", "",
             "| Metric | Control | Treatment | Diff | 95% Wald CI | 95% bootstrap CI | Rel. lift | p | p (Holm) |",
             "|---|---:|---:|---:|---|---|---:|---:|---:|"]
    for _, r in ret.iterrows():
        lines.append(f"| {r.metric} ({r.role}) | {r.rate_control:.4f} | {r.rate_treatment:.4f} | {pct(r['diff'])} "
                     f"| [{pct(r.wald_ci_low)}, {pct(r.wald_ci_high)}] | [{pct(r.boot_ci_low)}, {pct(r.boot_ci_high)}] "
                     f"| {100 * r.rel_lift:+.2f}% | {r.p_value:.4f} | {r.p_holm:.4f} |")
    lines += ["", "## Guardrail: game rounds in the first 14 days", "",
              "| Version | Mean C | Mean T | Median C | Median T | Diff in means | 95% bootstrap CI |",
              "|---|---:|---:|---:|---:|---:|---|"]
    for _, g in guard.iterrows():
        lines.append(f"| {g.version} | {g.mean_control:.2f} | {g.mean_treatment:.2f} | {g.median_control:.0f} "
                     f"| {g.median_treatment:.0f} | {g.diff_mean:+.2f} | [{g.boot_ci_low:+.2f}, {g.boot_ci_high:+.2f}] |")
    warn = guard.iloc[-1]["boot_ci_high"] < 0
    lines += ["", f"Mann-Whitney U p-value: {guard['mannwhitney_p'].iloc[0]:.4f}", "",
              "Guardrail warning: **significant drop in game rounds**" if warn
              else "Guardrail: no significant drop on the winsorised metric.", ""]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--force", action="store_true",
                        help="Run even if the analysis plan is not committed (not recommended).")
    args = parser.parse_args()

    ok, plan_msg = plan_is_committed()
    if not ok and not args.force:
        sys.exit(f"STOP: {plan_msg}\nCommit the analysis plan before estimating effects "
                 "(or use --force if you know what you are giving up).")
    if not ok:
        plan_msg = f"WARNING: run with --force. {plan_msg}"
    print(plan_msg)

    config.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    config.FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    df = load_data()

    srm = srm_test(df["version"].value_counts().to_dict())
    if srm.srm_detected:
        sys.exit(f"STOP: SRM detected (p = {srm.p_value:.4g} < {srm.alpha}). "
                 "Per the plan, effects are not estimated.")
    print(f"SRM check passed (p = {srm.p_value:.4g}, threshold {srm.alpha}).")

    rng = np.random.default_rng(config.SEED)
    ret = retention_effects(df, rng)
    guard = guardrail_effects(df, rng)

    primary = ret.loc[ret["role"] == "primary"].iloc[0]
    decision = decide(primary["diff"], primary["wald_ci_low"], primary["wald_ci_high"],
                      primary["p_holm"], config.MDE_ABS[config.PRIMARY_METRIC])

    ret.to_csv(config.RESULTS_DIR / "effects_retention.csv", index=False)
    guard.to_csv(config.RESULTS_DIR / "effects_guardrail.csv", index=False)
    write_report(ret, guard, decision, plan_msg, config.RESULTS_DIR / "effect_report.md")
    plot_effects(ret, config.FIGURES_DIR / "03_retention_effects.png")

    pd.set_option("display.float_format", "{:.4f}".format)
    print("\n=== Retention ===")
    print(ret[["metric", "rate_control", "rate_treatment", "diff", "wald_ci_low",
               "wald_ci_high", "p_value", "p_holm"]].to_string(index=False))
    print("\n=== Guardrail ===")
    print(guard[["version", "mean_control", "mean_treatment", "diff_mean",
                 "boot_ci_low", "boot_ci_high"]].to_string(index=False))
    print(f"\nDECISION: {decision}")
    print(f"\nSaved report: {config.RESULTS_DIR / 'effect_report.md'}")


if __name__ == "__main__":
    main()
