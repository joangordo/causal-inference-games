"""Power analysis for a two-proportion test (design stage, no outcome data)."""
from __future__ import annotations

import numpy as np
from statsmodels.stats.power import NormalIndPower
from statsmodels.stats.proportion import proportion_effectsize

from . import config

_SOLVER = NormalIndPower()


def required_n_per_arm(p_baseline: float, mde_abs: float,
                       alpha: float = config.ALPHA, power: float = config.POWER) -> int:
    """Players needed per arm to detect a drop of `mde_abs` from `p_baseline`.

    Uses Cohen's h with a two-sided z-test. A drop is used because it is the
    conservative direction for retention metrics below 0.5.
    """
    if not 0 < p_baseline < 1:
        raise ValueError("p_baseline must be in (0, 1).")
    if not 0 < mde_abs < p_baseline:
        raise ValueError("mde_abs must be positive and smaller than p_baseline.")
    h = abs(proportion_effectsize(p_baseline, p_baseline - mde_abs))
    n = _SOLVER.solve_power(effect_size=h, alpha=alpha, power=power,
                            ratio=1.0, alternative="two-sided")
    return int(np.ceil(n))


def mde_for_n(p_baseline: float, n_per_arm: int,
              alpha: float = config.ALPHA, power: float = config.POWER) -> float:
    """Smallest absolute drop detectable with `n_per_arm` players per arm."""
    if n_per_arm <= 1:
        raise ValueError("n_per_arm must be > 1.")
    h = _SOLVER.solve_power(nobs1=n_per_arm, alpha=alpha, power=power,
                            ratio=1.0, alternative="two-sided")
    # Invert Cohen's h: h = 2*asin(sqrt(p1)) - 2*asin(sqrt(p2))
    p2 = np.sin(np.arcsin(np.sqrt(p_baseline)) - h / 2) ** 2
    return float(p_baseline - p2)


def achieved_power(p_baseline: float, mde_abs: float, n_per_arm: int,
                   alpha: float = config.ALPHA) -> float:
    """Power to detect a drop of `mde_abs` with `n_per_arm` players per arm."""
    h = abs(proportion_effectsize(p_baseline, p_baseline - mde_abs))
    return float(_SOLVER.power(effect_size=h, nobs1=n_per_arm, alpha=alpha,
                               ratio=1.0, alternative="two-sided"))
