"""Regression discontinuity helpers built on rdrobust / rddensity."""
from __future__ import annotations

import io
from contextlib import redirect_stdout

import numpy as np
import pandas as pd

from . import config


def add_running_variable(df: pd.DataFrame, suffix: str = "_t1") -> pd.DataFrame:
    """Share of positive reviews at the given snapshot."""
    out = df.copy()
    tot = out[f"total_reviews{suffix}"]
    out[f"pct_positive{suffix}"] = np.where(tot > 0, out[f"total_positive{suffix}"] / tot.where(tot > 0), np.nan)
    return out


def cutoff_sample(df: pd.DataFrame, name: str, c: float | None = None) -> pd.DataFrame:
    """Games eligible for a cutoff, with centred running variable x (in pp)
    and treatment indicator from the label observed at t1."""
    spec = config.CUTOFFS[name]
    c = spec["c"] if c is None else c
    s = df[df["total_reviews_t1"] >= spec["min_reviews"]].copy()
    s = s.dropna(subset=["pct_positive_t1"])
    s["x"] = 100 * (s["pct_positive_t1"] - c)
    s["above"] = (s["x"] >= 0).astype(int)
    s["treated"] = (s["review_score_t1"] >= spec["treated_min_score"]).astype(int)
    return s


def compliance(s: pd.DataFrame) -> float:
    """Share of games whose label matches the side of the cutoff they are on."""
    return float((s["treated"] == s["above"]).mean()) if len(s) else np.nan


def estimate(s: pd.DataFrame, outcome: str, h: float | None = None,
             donut: float = 0.0, force_sharp: bool | None = None) -> dict:
    """Local-linear RDD with MSE-optimal bandwidth and robust bias-corrected
    inference (Calonico, Cattaneo & Titiunik). Fuzzy design if compliance is
    below the pre-specified threshold."""
    from rdrobust import rdrobust

    d = s.dropna(subset=[outcome, "x"])
    if donut > 0:
        d = d[d["x"].abs() >= donut]
    comp = compliance(d)
    sharp = comp >= config.SHARP_COMPLIANCE if force_sharp is None else force_sharp
    base = {"n_total": len(d), "compliance": comp, "design": "sharp" if sharp else "fuzzy",
            "donut_pp": donut}
    if d["x"].lt(0).sum() < 20 or d["x"].ge(0).sum() < 20:
        return {**base, "error": "too few observations on one side"}
    kwargs = {"y": d[outcome].to_numpy(float), "x": d["x"].to_numpy(float), "c": 0.0}
    if not sharp:
        kwargs["fuzzy"] = d["treated"].to_numpy(float)
    if h is not None:
        kwargs["h"] = h
    try:
        with redirect_stdout(io.StringIO()):
            r = rdrobust(**kwargs)
    except Exception as e:  # rdrobust raises on degenerate samples
        return {**base, "error": f"{type(e).__name__}: {e}"}
    return {**base,
            "coef": float(r.coef.iloc[0, 0]),
            "se_robust": float(r.se.iloc[2, 0]),
            "ci_low_robust": float(r.ci.iloc[2, 0]),
            "ci_high_robust": float(r.ci.iloc[2, 1]),
            "p_robust": float(r.pv.iloc[2, 0]),
            "h": float(r.bws.iloc[0, 0]),
            "n_left_h": int(r.N_h[0]), "n_right_h": int(r.N_h[1]),
            "error": None}


def density_test(x: np.ndarray) -> dict:
    """Cattaneo-Jansson-Ma manipulation test at x = 0."""
    from rddensity import rddensity
    x = np.asarray(x, float)
    x = x[~np.isnan(x)]
    try:
        with redirect_stdout(io.StringIO()):
            d = rddensity(X=x, c=0.0)
        return {"n": len(x), "t": float(d.test["t_jk"]), "p_value": float(d.test["p_jk"]), "error": None}
    except Exception as e:
        return {"n": len(x), "t": np.nan, "p_value": np.nan, "error": f"{type(e).__name__}: {e}"}


def binned_means(s: pd.DataFrame, outcome: str, width_pp: float = 1.0,
                 max_abs_pp: float = 10.0) -> pd.DataFrame:
    """Mean outcome in bins of the running variable (for RD plots)."""
    d = s[s["x"].abs() <= max_abs_pp].dropna(subset=[outcome])
    edges = np.arange(-max_abs_pp, max_abs_pp + width_pp, width_pp)
    d = d.assign(bin=pd.cut(d["x"], edges, right=False))
    g = d.groupby("bin", observed=True).agg(x=("x", "mean"), y=(outcome, "mean"), n=(outcome, "size"))
    return g.reset_index(drop=True)


def local_linear_fit(s: pd.DataFrame, outcome: str, h: float, side: str) -> tuple[np.ndarray, np.ndarray]:
    """Triangular-kernel local linear fit on one side, for drawing the RD plot."""
    d = s.dropna(subset=[outcome])
    d = d[(d["x"] < 0) & (d["x"] >= -h)] if side == "left" else d[(d["x"] >= 0) & (d["x"] <= h)]
    if len(d) < 3:
        return np.array([]), np.array([])
    w = np.clip(1 - d["x"].abs() / h, 0, None)
    X = np.column_stack([np.ones(len(d)), d["x"]])
    W = np.diag(w)
    beta = np.linalg.lstsq(X.T @ W @ X, X.T @ W @ d[outcome].to_numpy(float), rcond=None)[0]
    grid = np.linspace(-h, 0, 50) if side == "left" else np.linspace(0, h, 50)
    return grid, beta[0] + beta[1] * grid
