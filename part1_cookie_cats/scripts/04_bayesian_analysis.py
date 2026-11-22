"""
04 - Bayesian analysis (exploratory).

Beta-Binomial model per arm and metric. Reports the probability that each
arm is better, a 95% credible interval for the difference, the probability
of a harm larger than the business MDE, and the expected loss of each
decision. Prior sensitivity: flat prior vs priors centred on the assumed
baseline with increasing strength.

Run from the part1_cookie_cats folder:
    python scripts/04_bayesian_analysis.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src import config
from src.bayes import informative_prior, posterior_comparison
from src.data import load_data


def main() -> None:
    config.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    config.FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    df = load_data()
    rng = np.random.default_rng(config.SEED)

    metrics = [config.PRIMARY_METRIC, *config.SECONDARY_METRICS]
    rows, draws_flat = [], {}
    for m in metrics:
        g = df.groupby("version", observed=True)[m].agg(["sum", "count"])
        x_c, n_c = int(g.loc[config.CONTROL, "sum"]), int(g.loc[config.CONTROL, "count"])
        x_t, n_t = int(g.loc[config.TREATMENT, "sum"]), int(g.loc[config.TREATMENT, "count"])
        priors = {
            "flat Beta(1,1)": (1.0, 1.0),
            "baseline-centred, 1k players": informative_prior(config.BASELINE[m], 1_000),
            "baseline-centred, 10k players": informative_prior(config.BASELINE[m], 10_000),
        }
        for name, prior in priors.items():
            res = posterior_comparison(x_c, n_c, x_t, n_t, prior=prior,
                                       mde=config.MDE_ABS[m], rng=rng)
            if name.startswith("flat"):
                draws_flat[m] = res["_diff_draws"]
            rows.append({"metric": m, "prior": name,
                         **{k: v for k, v in res.items() if not k.startswith("_")}})
    out = pd.DataFrame(rows)
    out.to_csv(config.RESULTS_DIR / "bayesian.csv", index=False)

    # Figure: posterior of the difference (flat prior)
    fig, ax = plt.subplots(figsize=(7, 3.8))
    for m, d in draws_flat.items():
        ax.hist(100 * d, bins=120, density=True, histtype="step", lw=1.8, label=m)
    mde = 100 * config.MDE_ABS[config.PRIMARY_METRIC]
    ax.axvspan(-mde, mde, color="grey", alpha=0.12, label=f"±{mde:g} pp (business MDE)")
    ax.axvline(0, color="black", lw=0.8)
    ax.set_xlabel(f"Posterior of {config.TREATMENT} − {config.CONTROL} (percentage points)")
    ax.set_ylabel("Density")
    ax.set_title("Posterior distribution of the effect (flat prior)")
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(config.FIGURES_DIR / "04_bayesian_posteriors.png", dpi=150)

    # Markdown report
    lines = ["# Bayesian analysis (exploratory)", "",
             "Beta-Binomial model; 200,000 posterior draws per arm. Expected loss = average "
             "retention lost (in pp) if we choose that arm and the other is actually better.", "",
             "| Metric | Prior | Diff (pp) | 95% CrI (pp) | P(T better) | P(harm > MDE) "
             "| Exp. loss choose T (pp) | Exp. loss choose C (pp) |",
             "|---|---|---:|---|---:|---:|---:|---:|"]
    for _, r in out.iterrows():
        lines.append(f"| {r.metric} | {r.prior} | {100 * r.diff_mean:+.3f} "
                     f"| [{100 * r.cri_low:+.3f}, {100 * r.cri_high:+.3f}] "
                     f"| {r.prob_treatment_better:.4f} | {r.prob_harm_beyond_mde:.4f} "
                     f"| {100 * r.exp_loss_choose_treatment:.4f} | {100 * r.exp_loss_choose_control:.4f} |")
    lines += ["", "![Posteriors](figures/04_bayesian_posteriors.png)", ""]
    (config.RESULTS_DIR / "bayesian_report.md").write_text("\n".join(lines), encoding="utf-8")

    pd.set_option("display.float_format", "{:.4f}".format)
    print(out[["metric", "prior", "diff_mean", "cri_low", "cri_high",
               "prob_treatment_better", "prob_harm_beyond_mde"]].to_string(index=False))
    print(f"\nSaved report: {config.RESULTS_DIR / 'bayesian_report.md'}")


if __name__ == "__main__":
    main()
