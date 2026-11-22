"""
Peeking and group-sequential testing via simulation.

Under equally spaced interim looks, the sequence of z-statistics of a
two-sample test behaves like a scaled Brownian motion:
    z_k = S_k / sqrt(k),  S_k = sum of k iid N(delta / sqrt(K), 1)
where delta is the expected z-statistic at the final look. This is the
standard canonical joint distribution used to design group-sequential tests.
"""
from __future__ import annotations

import numpy as np
from scipy import stats

from . import config


def simulate_z_paths(n_looks: int, n_sims: int, delta: float = 0.0,
                     rng: np.random.Generator | None = None) -> np.ndarray:
    """Return an (n_sims, n_looks) array of interim z-statistics."""
    rng = rng or np.random.default_rng(config.SEED)
    inc = rng.normal(delta / np.sqrt(n_looks), 1.0, size=(n_sims, n_looks))
    k = np.arange(1, n_looks + 1)
    return np.cumsum(inc, axis=1) / np.sqrt(k)


def simulate_binomial_z_paths(p_c: float, p_t: float, n_per_arm: int, n_looks: int,
                              n_sims: int, rng: np.random.Generator | None = None) -> np.ndarray:
    """Interim z-statistics from actual binomial data (used to validate the
    Brownian approximation). Pooled-SE two-proportion z at each look."""
    rng = rng or np.random.default_rng(config.SEED)
    batch = n_per_arm // n_looks
    xc = np.cumsum(rng.binomial(batch, p_c, (n_sims, n_looks)), axis=1)
    xt = np.cumsum(rng.binomial(batch, p_t, (n_sims, n_looks)), axis=1)
    n = batch * np.arange(1, n_looks + 1)
    pc, pt = xc / n, xt / n
    pool = (xc + xt) / (2 * n)
    se = np.sqrt(pool * (1 - pool) * 2 / n)
    return (pt - pc) / se


def naive_boundary(n_looks: int, alpha: float = config.ALPHA) -> np.ndarray:
    """Fixed-sample critical value reused at every look (the 'peeking' mistake)."""
    return np.full(n_looks, stats.norm.ppf(1 - alpha / 2))


def boundary_shape(kind: str, n_looks: int) -> np.ndarray:
    k = np.arange(1, n_looks + 1)
    if kind == "pocock":
        return np.ones(n_looks)
    if kind == "obrien_fleming":
        return np.sqrt(n_looks / k)
    raise ValueError(f"Unknown boundary kind: {kind}")


def calibrate_boundary(kind: str, n_looks: int, alpha: float = config.ALPHA,
                       n_sims: int = 200_000, rng: np.random.Generator | None = None) -> np.ndarray:
    """Two-sided boundary of the given shape with overall type I error alpha.

    The constant is the (1 - alpha) quantile, under H0, of
    max_k |z_k| / shape_k, so the probability of ever crossing is alpha.
    """
    shape = boundary_shape(kind, n_looks)
    z = simulate_z_paths(n_looks, n_sims, 0.0, rng)
    c = np.quantile((np.abs(z) / shape).max(axis=1), 1 - alpha)
    return c * shape


def operating_characteristics(z_paths: np.ndarray, boundary: np.ndarray) -> dict:
    """Rejection rate and expected fraction of the planned sample used."""
    crossed = np.abs(z_paths) >= boundary
    any_cross = crossed.any(axis=1)
    first = np.where(any_cross, crossed.argmax(axis=1) + 1, z_paths.shape[1])
    return {"reject_rate": float(any_cross.mean()),
            "expected_sample_fraction": float((first / z_paths.shape[1]).mean())}


def final_z_for_mde(p_baseline: float, mde: float, n_per_arm: int) -> float:
    """Expected final z-statistic when the true drop equals `mde`."""
    se = np.sqrt(2 * p_baseline * (1 - p_baseline) / n_per_arm)
    return mde / se
