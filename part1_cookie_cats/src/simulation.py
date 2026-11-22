"""
Synthetic data-generating process to show post-treatment bias.

Latent engagement U drives both game rounds R and retention Y. The treatment
T (gate at level 40) lets players play more rounds before the first gate, so
T -> R. If we condition on R (segmenting "engaged" players or adding R as a
covariate), treated and control players in the same segment differ in U, and
the comparison is no longer randomised.

    U --> R <-- T
    U --> Y <-- T
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm

from . import config


def _sigmoid(x):
    return 1 / (1 + np.exp(-x))


def simulate_players(n: int, beta_t_on_y: float, rounds_multiplier: float = 1.10,
                     rng: np.random.Generator | None = None) -> tuple[pd.DataFrame, float]:
    """Simulate one experiment. Returns the data and the true average effect
    of T on Y (computed from both potential outcomes of every player)."""
    rng = rng or np.random.default_rng(config.SEED)
    u = rng.normal(size=n)
    t = rng.integers(0, 2, n)
    lam = np.exp(2.8 + 0.9 * u + np.log(rounds_multiplier) * t)
    rounds = rng.poisson(lam)
    lin = -1.45 + 1.2 * u
    p0, p1 = _sigmoid(lin), _sigmoid(lin + beta_t_on_y)
    y = rng.random(n) < np.where(t == 1, p1, p0)
    df = pd.DataFrame({"t": t, "rounds": rounds, "y": y.astype(int)})
    return df, float((p1 - p0).mean())


def estimate_three_ways(df: pd.DataFrame, threshold: int = 30) -> dict:
    """Correct (randomised) estimate vs two tempting but biased ones."""
    naive = df.loc[df.t == 1, "y"].mean() - df.loc[df.t == 0, "y"].mean()
    seg = df[df["rounds"] >= threshold]
    segmented = seg.loc[seg.t == 1, "y"].mean() - seg.loc[seg.t == 0, "y"].mean()
    X = sm.add_constant(np.column_stack([df["t"], np.log1p(df["rounds"])]))
    adjusted = sm.OLS(df["y"].to_numpy(dtype=float), X).fit().params[1]
    return {"randomised_diff": float(naive),
            f"segment_rounds_ge_{threshold}": float(segmented),
            "adjusted_for_rounds": float(adjusted)}
