"""Tests for the Bayesian, sequential and simulation modules (synthetic data)."""
import numpy as np
import pytest

from src import config
from src.bayes import informative_prior, posterior_comparison
from src.sequential import (calibrate_boundary, final_z_for_mde, naive_boundary,
                            operating_characteristics, simulate_binomial_z_paths,
                            simulate_z_paths)
from src.simulation import estimate_three_ways, simulate_players


# --- Bayesian -------------------------------------------------------------------
def test_informative_prior_mean_and_strength():
    a, b = informative_prior(0.2, 1000)
    assert a / (a + b) == pytest.approx(0.2) and a + b == pytest.approx(1000)


def test_posterior_probabilities_are_coherent():
    r = posterior_comparison(900, 5000, 1000, 5000, rng=np.random.default_rng(0))
    assert r["prob_treatment_better"] + r["prob_control_better"] == pytest.approx(1, abs=1e-6)
    assert r["prob_treatment_better"] > 0.99
    assert r["exp_loss_choose_treatment"] < r["exp_loss_choose_control"]


def test_flat_posterior_close_to_frequentist_for_large_n():
    x_c, x_t, n = 8500, 8200, 45_000
    r = posterior_comparison(x_c, n, x_t, n, rng=np.random.default_rng(1))
    se = np.sqrt((x_c / n) * (1 - x_c / n) / n + (x_t / n) * (1 - x_t / n) / n)
    assert r["diff_mean"] == pytest.approx((x_t - x_c) / n, abs=2e-4)
    assert r["cri_high"] - r["cri_low"] == pytest.approx(2 * 1.96 * se, rel=0.03)


# --- Sequential -----------------------------------------------------------------
def test_single_look_has_nominal_error():
    z = simulate_z_paths(1, 200_000, rng=np.random.default_rng(2))
    assert operating_characteristics(z, naive_boundary(1))["reject_rate"] == pytest.approx(0.05, abs=0.003)


def test_peeking_inflates_error():
    z = simulate_z_paths(10, 100_000, rng=np.random.default_rng(3))
    assert operating_characteristics(z, naive_boundary(10))["reject_rate"] > 0.15


@pytest.mark.parametrize("kind", ["pocock", "obrien_fleming"])
def test_calibrated_boundaries_control_error(kind):
    b = calibrate_boundary(kind, 14, n_sims=100_000, rng=np.random.default_rng(4))
    z = simulate_z_paths(14, 100_000, rng=np.random.default_rng(5))  # fresh paths
    assert operating_characteristics(z, b)["reject_rate"] == pytest.approx(0.05, abs=0.004)


def test_obrien_fleming_last_boundary_close_to_fixed():
    b = calibrate_boundary("obrien_fleming", 14, n_sims=100_000, rng=np.random.default_rng(6))
    assert b[0] > b[-1] and b[-1] < 2.15


def test_brownian_matches_binomial():
    rng = np.random.default_rng(7)
    zb = simulate_binomial_z_paths(0.19, 0.19, 20_000, 10, 20_000, rng)
    zw = simulate_z_paths(10, 20_000, rng=rng)
    fb = operating_characteristics(zb, naive_boundary(10))["reject_rate"]
    fw = operating_characteristics(zw, naive_boundary(10))["reject_rate"]
    assert fb == pytest.approx(fw, abs=0.015)


def test_final_z_gives_design_power():
    from src.power import required_n_per_arm
    n = required_n_per_arm(0.19, 0.01)
    z = simulate_z_paths(1, 200_000, final_z_for_mde(0.19, 0.01, n), np.random.default_rng(8))
    assert operating_characteristics(z, naive_boundary(1))["reject_rate"] == pytest.approx(0.80, abs=0.01)


# --- Post-treatment simulation ------------------------------------------------------
def test_randomised_estimate_is_unbiased_and_segmented_is_not():
    rng = np.random.default_rng(9)
    est = {"r": [], "s": [], "a": []}
    for _ in range(40):
        df, truth = simulate_players(30_000, 0.0, rng=rng)
        e = estimate_three_ways(df, 30)
        est["r"].append(e["randomised_diff"])
        est["s"].append(e["segment_rounds_ge_30"])
        est["a"].append(e["adjusted_for_rounds"])
    assert truth == pytest.approx(0.0)
    assert abs(np.mean(est["r"])) < 0.002
    assert np.mean(est["s"]) < -0.005 and np.mean(est["a"]) < -0.005
