"""Tests for Part 2 (no network access: the Steam API is mocked)."""
import numpy as np
import pandas as pd
import pytest

from src import config
from src.ids import extract_appids
from src.panel import build_panel
from src.rdd import compliance, cutoff_sample, density_test, estimate
from src.snapshot import SnapshotWriter, already_done
from src.steam_api import SteamReviewsClient, parse_summary


# --- API parsing and client --------------------------------------------------------
OK_PAYLOAD = {"response": {"query_summary": {"num_reviews": 1, "review_score": 8,
              "review_score_desc": "Very Positive", "total_positive": 850,
              "total_negative": 150, "total_reviews": 1000}, "reviews": [], "cursor": "x"}}


def test_parse_ok():
    r = parse_summary(620, OK_PAYLOAD)
    assert r["status"] == "ok" and r["total_reviews"] == 1000 and r["review_score"] == 8


@pytest.mark.parametrize("payload, status", [({"response": {}}, "no_summary"),
                                             ({}, "no_summary"),
                                             ({"response": {"query_summary": {"num_reviews": 0}}}, "no_summary")])
def test_parse_failures(payload, status):
    assert parse_summary(1, payload)["status"] == status


class FakeResp:
    def __init__(self, code, payload=None, headers=None, text=None):
        self.status_code, self._p = code, payload
        self.headers = headers or {}
        self._text = text

    def json(self):
        if self._text is not None:
            raise ValueError("not JSON")
        return self._p


class FakeSession:
    def __init__(self, responses):
        self.responses, self.headers, self.calls = list(responses), {}, 0

    def get(self, *a, **k):
        self.calls += 1
        return self.responses.pop(0)


def test_client_retries_on_rate_limit():
    s = FakeSession([FakeResp(429), FakeResp(503), FakeResp(200, OK_PAYLOAD)])
    row = SteamReviewsClient(session=s, sleep=lambda _: None).fetch(620)
    assert row["status"] == "ok" and s.calls == 3


def test_client_gives_up_and_marks_retryable():
    s = FakeSession([FakeResp(429)] * 3)
    row = SteamReviewsClient(session=s, max_retries=2, sleep=lambda _: None).fetch(620)
    assert row["status"] == "http_error" and row["http_status"] == 429


def test_client_does_not_retry_404():
    s = FakeSession([FakeResp(404)])
    row = SteamReviewsClient(session=s, sleep=lambda _: None).fetch(1)
    assert row["status"] == "http_error" and s.calls == 1


def test_redirect_or_web_page_stops_immediately():
    from src.steam_api import EndpointGone
    s = FakeSession([FakeResp(302, headers={"Location": "https://store.steampowered.com/"})])
    with pytest.raises(EndpointGone):
        SteamReviewsClient(session=s, sleep=lambda _: None).fetch(620)
    s = FakeSession([FakeResp(200, text="<html>")])
    with pytest.raises(EndpointGone):
        SteamReviewsClient(session=s, sleep=lambda _: None).fetch(620)


def test_request_uses_input_json():
    import json
    from src.steam_api import request_params
    body = json.loads(request_params(620, purchase_type=1)["input_json"])
    assert body["appid"] == 620 and body["purchase_type"] == 1 and body["review_type"] == 0
    assert body["languages"] == ["all"] and body["num_per_page"] == 1


# --- Resume -------------------------------------------------------------------------
def test_resume_skips_permanent_but_retries_transient(tmp_path):
    p = tmp_path / "snap.csv"
    with SnapshotWriter(p) as w:
        w.write({**parse_summary(1, OK_PAYLOAD), "fetched_at_utc": "2026-11-12T00:00:00+00:00"})
        w.write({"appid": 2, "status": "http_error", "fetched_at_utc": "2026-11-12T00:00:01+00:00"})
        w.write({**parse_summary(3, {"response": {}}), "fetched_at_utc": "2026-11-12T00:00:02+00:00"})
    assert already_done(p) == {1, 3}


# --- Ids -------------------------------------------------------------------------------
def test_ids_from_urls_and_numbers():
    df = pd.DataFrame({"url": ["https://store.steampowered.com/app/620/Portal_2/", "x", None],
                       "appid": [620, "440", 570.0]})
    ids, col = extract_appids(df)
    assert col == "appid" and ids.tolist() == [620, 440, 570]
    ids, _ = extract_appids(df, "url")
    assert ids.iloc[0] == 620 and pd.isna(ids.iloc[1])


# --- Panel and RDD ----------------------------------------------------------------------
def test_panel_outcomes(synthetic_snapshots):
    t1, t2 = synthetic_snapshots(n=500)
    p, gap = build_panel(t1, t2)
    assert gap == pytest.approx(35)
    assert (p["log_review_growth"] >= 0).all()
    assert p["any_new_review"].isin([0, 1]).all()


def test_labels_are_sharp_at_primary_cutoff(synthetic_snapshots):
    t1, t2 = synthetic_snapshots()
    p, _ = build_panel(t1, t2)
    s = cutoff_sample(p, config.PRIMARY_CUTOFF)
    assert compliance(s) == pytest.approx(1.0)
    assert (s["total_reviews_t1"] >= 50).all()


def test_rdd_recovers_known_jump(synthetic_snapshots):
    t1, t2 = synthetic_snapshots(n=60_000, jump=0.20, seed=1)
    p, _ = build_panel(t1, t2)
    r = estimate(cutoff_sample(p, config.PRIMARY_CUTOFF), "log_review_growth")
    assert r["error"] is None and r["design"] == "sharp"
    # A 20% higher review rate is roughly +0.01 in log growth over the gap
    assert r["ci_low_robust"] > 0 and 0.005 < r["coef"] < 0.02


def test_rdd_no_effect_when_no_jump(synthetic_snapshots):
    t1, t2 = synthetic_snapshots(n=40_000, jump=0.0, seed=2)
    p, _ = build_panel(t1, t2)
    r = estimate(cutoff_sample(p, config.PRIMARY_CUTOFF), "log_review_growth")
    assert r["ci_low_robust"] < 0 < r["ci_high_robust"]


def test_fuzzy_design_detected():
    rng = np.random.default_rng(3)
    x = rng.uniform(-10, 10, 4000)
    above = (x >= 0).astype(int)
    s = pd.DataFrame({"x": x, "above": above,
                      "treated": np.where(rng.random(4000) < 0.1, 1 - above, above),
                      "y": rng.normal(size=4000)})
    assert estimate(s, "y")["design"] == "fuzzy"


def test_donut_removes_central_observations():
    rng = np.random.default_rng(4)
    x = rng.uniform(-10, 10, 4000)
    s = pd.DataFrame({"x": x, "above": (x >= 0).astype(int), "treated": (x >= 0).astype(int),
                      "y": rng.normal(size=4000)})
    full, donut = estimate(s, "y"), estimate(s, "y", donut=1.0)
    assert donut["n_total"] < full["n_total"]


def test_density_test_no_manipulation():
    x = np.random.default_rng(5).uniform(-10, 10, 5000)
    assert density_test(x)["p_value"] > 0.01


def test_density_test_detects_bunching():
    rng = np.random.default_rng(6)
    x = np.concatenate([rng.uniform(-10, 10, 4000), rng.uniform(0, 1, 800)])
    assert density_test(x)["p_value"] < 0.01


def test_prepare_covariates_parses_spanish_store_fields():
    from src.panel import prepare_covariates
    raw = pd.DataFrame({"release_date": ["16 ABR 2025", "Próximamente", "1 FEB 2016"],
                        "price_original": ["18,99€", None, "1.299,00€"],
                        "is_free": [False, False, True], "early_access": [False, True, False]})
    out = prepare_covariates(raw)
    assert out["release_year"].tolist()[0] == 2025 and pd.isna(out["release_year"][1])
    assert out["price_eur"][0] == pytest.approx(18.99) and out["price_eur"][2] == 0
    assert out["early_access"].tolist() == [0, 1, 0]
