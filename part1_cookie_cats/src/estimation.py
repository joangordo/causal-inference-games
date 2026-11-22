"""Effect estimation for retention (proportions) and the guardrail (means)."""
from __future__ import annotations

import numpy as np
from scipy import stats
from statsmodels.stats.multitest import multipletests
from statsmodels.stats.proportion import proportions_ztest

from . import config


# --- Retention: difference in proportions ------------------------------------------
def two_proportion_effect(x_c: int, n_c: int, x_t: int, n_t: int,
                          alpha: float = config.ALPHA, n_boot: int = 10_000,
                          rng: np.random.Generator | None = None) -> dict:
    """Treatment − control difference in proportions with Wald and bootstrap CIs.

    Bootstrap note: resampling n players with replacement from an arm with
    x successes gives a Binomial(n, x/n) number of successes, so the
    nonparametric bootstrap of a proportion can be drawn exactly and fast
    with rng.binomial instead of resampling rows.
    """
    rng = rng or np.random.default_rng(config.SEED)
    p_c, p_t = x_c / n_c, x_t / n_t
    diff = p_t - p_c
    z_crit = stats.norm.ppf(1 - alpha / 2)

    # Two-proportion z-test (pooled SE under H0)
    _, p_value = proportions_ztest([x_t, x_c], [n_t, n_c], alternative="two-sided")

    # Wald CI (unpooled SE, no H0 assumed)
    se = np.sqrt(p_c * (1 - p_c) / n_c + p_t * (1 - p_t) / n_t)
    wald = (diff - z_crit * se, diff + z_crit * se)

    # Percentile bootstrap for the difference and the relative lift
    bc = rng.binomial(n_c, p_c, n_boot) / n_c
    bt = rng.binomial(n_t, p_t, n_boot) / n_t
    q = [100 * alpha / 2, 100 * (1 - alpha / 2)]
    boot_diff = np.percentile(bt - bc, q)
    boot_lift = np.percentile((bt - bc) / bc, q)

    return {
        "n_control": n_c, "n_treatment": n_t,
        "rate_control": p_c, "rate_treatment": p_t,
        "diff": diff, "se": se, "p_value": float(p_value),
        "wald_ci_low": wald[0], "wald_ci_high": wald[1],
        "boot_ci_low": boot_diff[0], "boot_ci_high": boot_diff[1],
        "rel_lift": diff / p_c,
        "rel_lift_ci_low": boot_lift[0], "rel_lift_ci_high": boot_lift[1],
    }


def holm_adjust(p_values: list[float], alpha: float = config.ALPHA) -> np.ndarray:
    """Holm-adjusted p-values for a family of tests."""
    return multipletests(p_values, alpha=alpha, method="holm")[1]


def decide(diff: float, ci_low: float, ci_high: float, p_adj: float,
           mde: float, alpha: float = config.ALPHA) -> str:
    """Decision rule from §7 of the analysis plan (primary metric only)."""
    if p_adj < alpha and diff < 0:
        return f"Significant decrease with {config.TREATMENT}: keep the gate at level 30"
    if p_adj < alpha and diff > 0:
        return f"Significant increase with {config.TREATMENT}: move the gate to level 40"
    if -mde <= ci_low and ci_high <= mde:
        return f"Not significant and CI inside ±{mde * 100:g} pp: practically equivalent, keep level 30"
    return f"Not significant and CI wider than ±{mde * 100:g} pp: inconclusive, run a larger test"


# --- Guardrail: difference in means ------------------------------------------------
def bootstrap_mean_diff(control: np.ndarray, treatment: np.ndarray,
                        alpha: float = config.ALPHA, n_boot: int = 10_000,
                        rng: np.random.Generator | None = None,
                        chunk: int = 250) -> tuple[float, float, float]:
    """Treatment − control difference in means with a percentile bootstrap CI.

    Rows are resampled in chunks to keep memory bounded on ~45k players/arm.
    """
    rng = rng or np.random.default_rng(config.SEED)
    control = np.asarray(control, dtype=float)
    treatment = np.asarray(treatment, dtype=float)
    diffs = np.empty(n_boot)
    for start in range(0, n_boot, chunk):
        b = min(chunk, n_boot - start)
        mc = control[rng.integers(0, control.size, (b, control.size))].mean(axis=1)
        mt = treatment[rng.integers(0, treatment.size, (b, treatment.size))].mean(axis=1)
        diffs[start:start + b] = mt - mc
    low, high = np.percentile(diffs, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return float(treatment.mean() - control.mean()), float(low), float(high)
