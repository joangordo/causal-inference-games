"""Tests for the estimation module (synthetic data only)."""
import numpy as np
import pytest

from src import config
from src.estimation import bootstrap_mean_diff, decide, holm_adjust, two_proportion_effect


def test_wald_ci_coverage_is_nominal():
    """About 95% of Wald CIs should contain the true difference."""
    rng = np.random.default_rng(3)
    p_c, p_t, n, sims = 0.19, 0.18, 5000, 1500
    covered = 0
    for _ in range(sims):
        r = two_proportion_effect(rng.binomial(n, p_c), n, rng.binomial(n, p_t), n, n_boot=10, rng=rng)
        covered += r["wald_ci_low"] <= p_t - p_c <= r["wald_ci_high"]
    assert abs(covered / sims - 0.95) < 0.02


def test_bootstrap_ci_agrees_with_wald_for_large_n():
    r = two_proportion_effect(8500, 45000, 8200, 45000, n_boot=20_000,
                              rng=np.random.default_rng(0))
    assert r["boot_ci_low"] == pytest.approx(r["wald_ci_low"], abs=0.001)
    assert r["boot_ci_high"] == pytest.approx(r["wald_ci_high"], abs=0.001)


def test_false_positive_rate_under_null():
    rng = np.random.default_rng(5)
    n, sims = 4000, 2000
    hits = sum(two_proportion_effect(rng.binomial(n, 0.45), n, rng.binomial(n, 0.45), n,
                                     n_boot=10, rng=rng)["p_value"] < 0.05 for _ in range(sims))
    assert abs(hits / sims - 0.05) < 0.015


def test_holm_matches_manual():
    adj = holm_adjust([0.01, 0.04])
    assert adj[0] == pytest.approx(0.02) and adj[1] == pytest.approx(0.04)


@pytest.mark.parametrize("diff, low, high, p, expected", [
    (-0.008, -0.012, -0.004, 0.001, "keep the gate at level 30"),
    (0.008, 0.004, 0.012, 0.001, "move the gate to level 40"),
    (0.001, -0.004, 0.006, 0.60, "practically equivalent"),
    (-0.004, -0.015, 0.007, 0.40, "inconclusive"),
])
def test_decision_rule(diff, low, high, p, expected):
    assert expected in decide(diff, low, high, p, mde=0.01)


def test_bootstrap_mean_diff_contains_true_difference():
    rng = np.random.default_rng(11)
    c = rng.exponential(50, 20_000)
    t = rng.exponential(52, 20_000)
    diff, low, high = bootstrap_mean_diff(c, t, n_boot=500, rng=rng)
    assert low < diff < high and low < 2 < high
