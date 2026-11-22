"""Bayesian Beta-Binomial comparison of two proportions."""
from __future__ import annotations

import numpy as np

from . import config


def informative_prior(mean: float, strength: float) -> tuple[float, float]:
    """Beta prior with a given mean and 'strength' (equivalent number of players)."""
    if not 0 < mean < 1 or strength <= 0:
        raise ValueError("mean must be in (0, 1) and strength > 0.")
    return mean * strength, (1 - mean) * strength


def posterior_comparison(x_c: int, n_c: int, x_t: int, n_t: int,
                         prior: tuple[float, float] = (1.0, 1.0),
                         mde: float = config.MDE_ABS[config.PRIMARY_METRIC],
                         draws: int = 200_000, cred: float = 0.95,
                         rng: np.random.Generator | None = None) -> dict:
    """Posterior summaries of the treatment − control difference.

    Expected loss of a decision = average amount of retention we would lose
    if we choose that arm and the other one is actually better. It is the
    quantity a product team cares about: risk measured in the metric's units.
    """
    rng = rng or np.random.default_rng(config.SEED)
    a, b = prior
    p_c = rng.beta(a + x_c, b + n_c - x_c, draws)
    p_t = rng.beta(a + x_t, b + n_t - x_t, draws)
    diff = p_t - p_c
    tail = (1 - cred) / 2
    low, high = np.quantile(diff, [tail, 1 - tail])
    return {
        "post_mean_control": float(p_c.mean()),
        "post_mean_treatment": float(p_t.mean()),
        "diff_mean": float(diff.mean()),
        "cri_low": float(low), "cri_high": float(high),
        "prob_treatment_better": float((diff > 0).mean()),
        "prob_control_better": float((diff < 0).mean()),
        "prob_harm_beyond_mde": float((diff < -mde).mean()),
        "exp_loss_choose_treatment": float(np.maximum(p_c - p_t, 0).mean()),
        "exp_loss_choose_control": float(np.maximum(p_t - p_c, 0).mean()),
        "_diff_draws": diff,
    }
