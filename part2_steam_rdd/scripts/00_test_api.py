"""
00 - Check the Steam review API before taking a snapshot (about 30 seconds).

Calls IUserReviewsService/GetAppReviews for three games from the scraper
dataset whose store page showed a known share and number of reviews in
October 2026, with each purchase_type code. The code whose totals and label
match the store page is the one the store uses for its score.

Run from the part2_steam_rdd folder:
    python scripts/00_test_api.py
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import requests

from src import config
from src.steam_api import request_params

# appid: (name, store label, % positive, number of reviews) seen by the scraper in October 2026
REFERENCE = {
    2494780: ("#DRIVE Rally", "Mostly Positive", 79, 756),
    919640: ("Steel Division 2", "Mostly Positive", 79, 8087),
    1385380: ("Across the Obelisk", "Very Positive", 80, 10729),
}

print(f"Endpoint: {config.API_URL}")
for appid, (name, label, pct, n) in REFERENCE.items():
    print(f"\n=== {appid} {name}: store page showed {label}, {pct}% of {n:,} reviews ===")
    for ptype in (0, 1, 2):
        try:
            r = requests.get(config.API_URL, params=request_params(appid, purchase_type=ptype),
                             timeout=20, allow_redirects=False,
                             headers={"User-Agent": config.USER_AGENT})
            if r.status_code != 200:
                print(f"purchase_type={ptype}: HTTP {r.status_code} {r.headers.get('Location', '')} {r.text[:150]!r}")
                continue
            qs = r.json().get("response", {}).get("query_summary", {})
            tot, posv = qs.get("total_reviews"), qs.get("total_positive")
            share = f"{100 * posv / tot:.2f}%" if tot else "n/a"
            print(f"purchase_type={ptype}: {posv} positive of {tot} ({share}), "
                  f"score {qs.get('review_score')} = {qs.get('review_score_desc')}")
        except Exception as e:
            print(f"purchase_type={ptype}: {type(e).__name__}: {e}")
        time.sleep(1.5)
print("\nRaw reply for the first game with purchase_type=0 (first 400 characters):")
r = requests.get(config.API_URL, params=request_params(2494780, purchase_type=0), timeout=20)
print(json.dumps(r.json(), ensure_ascii=False)[:400] if r.ok else r.text[:400])
