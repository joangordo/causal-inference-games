"""Merge two snapshots (and optional covariates) into an analysis panel."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .rdd import add_running_variable

KEEP = ["total_positive", "total_negative", "total_reviews", "review_score",
        "review_score_desc", "fetched_at_utc"]


def build_panel(t1: pd.DataFrame, t2: pd.DataFrame,
                covariates: pd.DataFrame | None = None) -> tuple[pd.DataFrame, float]:
    """Inner-join snapshots on appid and compute outcomes.

    Returns the panel and the median gap in days between the two snapshots.
    """
    a = t1[["appid", *KEEP]].add_suffix("_t1").rename(columns={"appid_t1": "appid"})
    b = t2[["appid", *KEEP]].add_suffix("_t2").rename(columns={"appid_t2": "appid"})
    p = a.merge(b, on="appid", how="inner")
    gap = (p["fetched_at_utc_t2"] - p["fetched_at_utc_t1"]).dt.total_seconds() / 86400
    p["gap_days"] = gap
    p["new_reviews"] = p["total_reviews_t2"] - p["total_reviews_t1"]
    p["log_review_growth"] = np.log1p(p["total_reviews_t2"]) - np.log1p(p["total_reviews_t1"])
    p["any_new_review"] = (p["new_reviews"] > 0).astype(int)
    p["log_reviews_t1"] = np.log1p(p["total_reviews_t1"])
    p = add_running_variable(p, "_t1")
    if covariates is not None and len(covariates.columns) > 1:
        p = p.merge(covariates.drop_duplicates("appid"), on="appid", how="left")
    return p, float(gap.median())


def prepare_covariates(raw: pd.DataFrame) -> pd.DataFrame:
    """Numeric covariates from the scraper dataset (Spanish store pages).

    release_year: the 4-digit year in release_date ("16 ABR 2025" -> 2025).
    price_eur: price_original ("18,99€" -> 18.99); free games -> 0.
    """
    out = raw.copy()
    out["release_year"] = pd.to_numeric(out["release_date"].astype(str).str.extract(r"(\d{4})")[0],
                                        errors="coerce")
    out.loc[out["release_year"] > 2026, "release_year"] = float("nan")  # placeholders such as 2999
    price = (out["price_original"].astype(str).str.replace("€", "", regex=False)
             .str.replace(".", "", regex=False).str.replace(",", ".", regex=False).str.strip())
    out["price_eur"] = pd.to_numeric(price, errors="coerce")
    if "is_free" in out:
        out.loc[out["is_free"].astype(str).str.lower() == "true", "price_eur"] = 0.0
    if "early_access" in out:
        out["early_access"] = (out["early_access"].astype(str).str.lower() == "true").astype(int)
    return out
