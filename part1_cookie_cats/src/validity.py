"""
Validity checks that must pass BEFORE estimating any treatment effect.

Design principle: these checks are blind to outcomes by arm. The only
arm-level quantity used is the number of players per arm (needed for the SRM
test). Everything about game rounds and retention is computed on the pooled
sample, so running this script cannot bias later analytical decisions.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict

import numpy as np
import pandas as pd
from scipy import stats

from . import config


# --- Sample ratio mismatch -----------------------------------------------------
@dataclass
class SRMResult:
    observed: dict
    expected: dict
    observed_share: dict
    chi2: float
    p_value: float
    alpha: float
    srm_detected: bool

    def to_dict(self) -> dict:
        return asdict(self)


def srm_test(counts: dict[str, int],
             expected_split: dict[str, float] = config.EXPECTED_SPLIT,
             alpha: float = config.ALPHA_SRM) -> SRMResult:
    """Chi-square goodness-of-fit test of observed arm sizes vs the design split.

    A significant result means the randomisation or the logging is broken
    (e.g. one arm loses players because of a bug), and any effect estimate is
    suspect until the cause is understood.
    """
    arms = list(expected_split)
    if set(arms) != set(counts):
        raise ValueError(f"Arms in counts {sorted(counts)} do not match design {sorted(arms)}")
    if not np.isclose(sum(expected_split.values()), 1.0):
        raise ValueError("Expected split must sum to 1.")

    observed = np.array([counts[a] for a in arms], dtype=float)
    total = observed.sum()
    expected = np.array([expected_split[a] * total for a in arms])
    chi2, p = stats.chisquare(observed, expected)

    return SRMResult(
        observed={a: int(counts[a]) for a in arms},
        expected={a: float(e) for a, e in zip(arms, expected)},
        observed_share={a: float(counts[a] / total) for a in arms},
        chi2=float(chi2),
        p_value=float(p),
        alpha=alpha,
        srm_detected=bool(p < alpha),
    )


# --- Pooled data quality -------------------------------------------------------
def pooled_quality_report(df: pd.DataFrame) -> dict:
    """Integrity facts about the pooled sample (no arm breakdown)."""
    r = df["sum_gamerounds"]
    zero_rounds = r == 0
    return {
        "n_players": int(len(df)),
        "n_unique_userid": int(df["userid"].nunique()),
        "share_zero_rounds": float(zero_rounds.mean()),
        # Logically odd: never played a round but counted as retained.
        "n_zero_rounds_but_retained_d1": int((zero_rounds & (df["retention_1"] == 1)).sum()),
        "n_zero_rounds_but_retained_d7": int((zero_rounds & (df["retention_7"] == 1)).sum()),
        # Returned on day 7 without returning on day 1: possible, not an error.
        "n_retained_d7_not_d1": int(((df["retention_7"] == 1) & (df["retention_1"] == 0)).sum()),
        "rounds_quantiles": {f"p{int(q * 1000) / 10:g}": float(r.quantile(q))
                             for q in (0.5, 0.75, 0.9, 0.99, 0.999)},
        "rounds_max": int(r.max()),
    }


def flag_outliers(df: pd.DataFrame,
                  hard_cap: int = config.OUTLIER_ROUNDS_HARD_CAP,
                  top_n: int = 10) -> pd.DataFrame:
    """Return the most extreme players by game rounds (pooled, without arm).

    Rows above the hard cap are marked. Nothing is removed here: the treatment
    of outliers is defined in the analysis plan and applied later.
    """
    cols = ["userid", "sum_gamerounds"]
    top = df.nlargest(top_n, "sum_gamerounds")[cols].copy()
    log_r = np.log1p(df["sum_gamerounds"])
    med = log_r.median()
    mad = stats.median_abs_deviation(log_r, scale="normal")
    top["robust_z_log"] = (np.log1p(top["sum_gamerounds"]) - med) / mad
    top["above_hard_cap"] = top["sum_gamerounds"] > hard_cap
    return top.reset_index(drop=True)


def winsorise_pooled(series: pd.Series, quantile: float = config.WINSOR_QUANTILE) -> tuple[pd.Series, float]:
    """Cap values at a pooled quantile. Returns the capped series and the cap."""
    cap = float(series.quantile(quantile))
    return series.clip(upper=cap), cap
