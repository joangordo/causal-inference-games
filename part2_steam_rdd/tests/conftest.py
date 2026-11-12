import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def steam_score(pct: np.ndarray, n: np.ndarray) -> np.ndarray:
    """Expected Steam review_score codes (used only to build synthetic data)."""
    s = np.zeros(len(pct), dtype=int)
    s = np.where(pct >= 0.80, np.where(n >= 50, 8, 7), s)
    s = np.where((pct >= 0.95) & (n >= 500), 9, s)
    s = np.where((pct >= 0.70) & (pct < 0.80), 6, s)
    s = np.where((pct >= 0.40) & (pct < 0.70), 5, s)
    s = np.where((pct >= 0.20) & (pct < 0.40), 4, s)
    s = np.where(pct < 0.20, np.where(n >= 500, 1, np.where(n >= 50, 2, 3)), s)
    return np.where(n < 10, 0, s)


@pytest.fixture
def synthetic_snapshots():
    """Two snapshots with a known +10% jump in review growth above 80%."""
    def make(n=20_000, jump=0.10, seed=0):
        rng = np.random.default_rng(seed)
        total = np.round(np.exp(rng.normal(4.5, 1.3, n))).astype(int) + 1
        pct = rng.beta(6, 2, n)
        pos = np.round(pct * total).astype(int)
        pct_obs = pos / total
        score = steam_score(pct_obs, total)
        rate = 0.05 * total * np.exp(0.5 * (pct_obs - 0.8)) * np.where((pct_obs >= 0.8) & (total >= 50), 1 + jump, 1)
        new = rng.poisson(rate)
        t1 = pd.DataFrame({"appid": np.arange(n) + 10, "fetched_at_utc": pd.Timestamp("2026-11-12", tz="UTC"),
                           "status": "ok", "total_positive": pos, "total_negative": total - pos,
                           "total_reviews": total, "review_score": score, "review_score_desc": "x"})
        t2 = t1.copy()
        t2["fetched_at_utc"] = pd.Timestamp("2026-12-17", tz="UTC")
        new_pos = rng.binomial(new, pct)
        t2["total_reviews"] = total + new
        t2["total_positive"] = pos + new_pos
        t2["total_negative"] = t2["total_reviews"] - t2["total_positive"]
        return t1, t2
    return make
