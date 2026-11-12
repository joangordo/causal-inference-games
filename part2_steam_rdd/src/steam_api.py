"""Minimal client for Steam's public review-summary endpoint, with retries."""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone

import requests

from . import config

FIELDS = ["appid", "fetched_at_utc", "status", "http_status", "total_positive",
          "total_negative", "total_reviews", "review_score", "review_score_desc", "error"]
PERMANENT_STATUSES = {"ok", "no_summary"}   # not retried on resume
RETRYABLE_HTTP = {429, 500, 502, 503, 504}


def parse_summary(appid: int, payload: dict) -> dict:
    """Turn a GetAppReviews JSON reply ({"response": {"query_summary": ...}}) into one row."""
    row = {k: None for k in FIELDS}
    row["appid"] = appid
    qs = (payload.get("response") or {}).get("query_summary")
    if not qs or "total_reviews" not in qs:
        row["status"] = "no_summary"
        return row
    row.update(status="ok",
               total_positive=int(qs.get("total_positive", 0)),
               total_negative=int(qs.get("total_negative", 0)),
               total_reviews=int(qs.get("total_reviews", 0)),
               review_score=int(qs.get("review_score", 0)),
               review_score_desc=qs.get("review_score_desc"))
    return row


def request_params(appid: int, purchase_type: int | None = None) -> dict:
    body = {"appid": int(appid), **config.API_INPUT,
            "purchase_type": config.PURCHASE_TYPE if purchase_type is None else purchase_type}
    return {"input_json": json.dumps(body, separators=(",", ":"))}


class EndpointGone(RuntimeError):
    """Steam answered with a redirect or a web page instead of JSON."""


class SteamReviewsClient:
    def __init__(self, session: requests.Session | None = None,
                 max_retries: int = config.MAX_RETRIES, timeout: float = config.TIMEOUT_S,
                 backoff_base: float = 2.0, sleep=time.sleep):
        self.session = session or requests.Session()
        self.session.headers.update({"User-Agent": config.USER_AGENT})
        self.max_retries, self.timeout = max_retries, timeout
        self.backoff_base, self.sleep = backoff_base, sleep

    def fetch(self, appid: int) -> dict:
        last_err, last_status = None, None
        for attempt in range(self.max_retries + 1):
            try:
                resp = self.session.get(config.API_URL, params=request_params(appid),
                                        timeout=self.timeout, allow_redirects=False)
                last_status = resp.status_code
                if 300 <= resp.status_code < 400:
                    raise EndpointGone(f"Steam redirected the request to {resp.headers.get('Location')}")
                if resp.status_code == 200:
                    try:
                        payload = resp.json()
                    except ValueError:
                        raise EndpointGone("Steam answered with a web page instead of JSON")
                    row = parse_summary(appid, payload)
                    row["http_status"] = 200
                    return self._stamp(row)
                if resp.status_code not in RETRYABLE_HTTP:
                    break
                last_err = f"HTTP {resp.status_code}"
            except (requests.RequestException, ValueError) as e:
                last_err = f"{type(e).__name__}: {e}"
            if attempt < self.max_retries:
                self.sleep(min(self.backoff_base ** (attempt + 1), 120))
        row = {k: None for k in FIELDS}
        row.update(appid=appid, status="http_error" if last_status else "exception",
                   http_status=last_status, error=last_err or f"HTTP {last_status}")
        return self._stamp(row)

    @staticmethod
    def _stamp(row: dict) -> dict:
        row["fetched_at_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        return row
