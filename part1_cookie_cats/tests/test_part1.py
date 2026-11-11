"""Unit tests for data loading, validity checks and power analysis.

All tests use synthetic data, so they run without the real dataset.
"""
import numpy as np
import pandas as pd
import pytest

from src import config
from src.data import DataValidationError, validate
from src.power import achieved_power, mde_for_n, required_n_per_arm
from src.validity import flag_outliers, pooled_quality_report, srm_test, winsorise_pooled


def make_df(n=1000, seed=0):
    rng = np.random.default_rng(seed)
    return pd.DataFrame({
        "userid": np.arange(n),
        "version": rng.choice([config.CONTROL, config.TREATMENT], n),
        "sum_gamerounds": rng.poisson(30, n),
        "retention_1": rng.random(n) < 0.45,
        "retention_7": rng.random(n) < 0.19,
    })


# --- data -----------------------------------------------------------------------
def test_validate_ok_and_types():
    out = validate(make_df())
    assert out["retention_1"].isin([0, 1]).all()
    assert list(out["version"].cat.categories) == [config.CONTROL, config.TREATMENT]


def test_validate_accepts_string_booleans():
    df = make_df()
    df["retention_7"] = df["retention_7"].astype(str)
    assert validate(df)["retention_7"].isin([0, 1]).all()


@pytest.mark.parametrize("mutation, msg", [
    (lambda d: d.drop(columns="retention_7"), "Missing columns"),
    (lambda d: d.assign(userid=0), "duplicated"),
    (lambda d: d.assign(version="gate_50"), "Unknown experiment arms"),
    (lambda d: d.assign(sum_gamerounds=-1), "negative"),
    (lambda d: d.assign(retention_1="maybe"), "not boolean"),
])
def test_validate_rejects_bad_data(mutation, msg):
    with pytest.raises(DataValidationError, match=msg):
        validate(mutation(make_df()))


def test_validate_rejects_nulls():
    df = make_df()
    df.loc[3, "sum_gamerounds"] = np.nan
    with pytest.raises(DataValidationError, match="Null"):
        validate(df)


# --- SRM ------------------------------------------------------------------------
def test_srm_balanced_not_flagged():
    r = srm_test({config.CONTROL: 50_000, config.TREATMENT: 50_100})
    assert not r.srm_detected


def test_srm_clear_imbalance_flagged():
    r = srm_test({config.CONTROL: 48_000, config.TREATMENT: 52_000})
    assert r.srm_detected and r.p_value < 1e-10


def test_srm_false_positive_rate_close_to_alpha():
    """Under correct randomisation the SRM test should fire about alpha of the time."""
    rng = np.random.default_rng(1)
    alpha, sims = 0.05, 4000
    n_ctrl = rng.binomial(10_000, 0.5, sims)
    fires = [srm_test({config.CONTROL: int(c), config.TREATMENT: int(10_000 - c)}, alpha=alpha).srm_detected
             for c in n_ctrl]
    assert abs(np.mean(fires) - alpha) < 0.015


def test_srm_rejects_mismatched_arms():
    with pytest.raises(ValueError):
        srm_test({"a": 10, "b": 10})


# --- quality / outliers ---------------------------------------------------------------
def test_quality_report_counts_inconsistencies():
    df = validate(make_df())
    df.loc[0, ["sum_gamerounds", "retention_1"]] = [0, 1]
    rep = pooled_quality_report(df)
    assert rep["n_players"] == len(df)
    assert rep["n_zero_rounds_but_retained_d1"] >= 1


def test_outliers_flag_extreme_player():
    df = validate(make_df())
    df.loc[5, "sum_gamerounds"] = 50_000
    top = flag_outliers(df, hard_cap=10_000, top_n=3)
    assert top.loc[0, "userid"] == 5 and top.loc[0, "above_hard_cap"]


def test_winsorise_caps_at_quantile():
    s = pd.Series(np.arange(1000))
    capped, cap = winsorise_pooled(s, 0.99)
    assert capped.max() == pytest.approx(cap) and capped.min() == 0


# --- power ----------------------------------------------------------------------
def test_required_n_decreases_with_larger_mde():
    assert required_n_per_arm(0.19, 0.02) < required_n_per_arm(0.19, 0.01)


def test_mde_and_required_n_are_consistent():
    n = required_n_per_arm(0.19, 0.01)
    assert mde_for_n(0.19, n) == pytest.approx(0.01, rel=0.02)
    assert achieved_power(0.19, 0.01, n) == pytest.approx(config.POWER, abs=0.01)


def test_power_matches_simulation():
    """Analytical power should match a Monte Carlo two-proportion z-test."""
    from statsmodels.stats.proportion import proportions_ztest
    rng = np.random.default_rng(7)
    p0, mde, n, sims = 0.19, 0.02, 4000, 2000
    hits = 0
    for _ in range(sims):
        a, b = rng.binomial(n, p0), rng.binomial(n, p0 - mde)
        hits += proportions_ztest([a, b], [n, n])[1] < config.ALPHA
    assert abs(hits / sims - achieved_power(p0, mde, n)) < 0.04


@pytest.mark.parametrize("args", [(0, 0.01), (0.19, 0.0), (0.19, 0.5)])
def test_required_n_rejects_bad_inputs(args):
    with pytest.raises(ValueError):
        required_n_per_arm(*args)
