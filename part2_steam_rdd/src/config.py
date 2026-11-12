"""
Central configuration for Part 2 (Steam review-label RDD).

Decisions here mirror analysis_plan.md and are fixed before the second
snapshot is taken.
"""
from pathlib import Path

# --- Paths -------------------------------------------------------------------
PART2_DIR = Path(__file__).resolve().parents[1]
SNAPSHOT_DIR = PART2_DIR / "data" / "snapshots"
PANEL_PATH = PART2_DIR / "data" / "panel.csv"
RESULTS_DIR = PART2_DIR / "results"
FIGURES_DIR = RESULTS_DIR / "figures"
PLAN_PATH = PART2_DIR / "analysis_plan.md"

# --- Steam API -----------------------------------------------------------------
# Valve retired store.steampowered.com/appreviews on 22 October 2026 (it now
# redirects to the store front page). Its replacement is the keyless Web API
# method IUserReviewsService/GetAppReviews, called with a single input_json.
# The score fields are only returned on the first page and with review_type = 0 (all).
API_URL = "https://api.steampowered.com/IUserReviewsService/GetAppReviews/v1/"
# purchase_type is an enum. The store score is computed from reviews by Steam
# purchasers; scripts/00_test_api.py checks which code reproduces it.
PURCHASE_TYPE = 0
API_INPUT = {"num_per_page": 1, "languages": ["all"], "review_type": 0, "filter": 0}
REQUEST_DELAY_S = 1.0        # pause between requests (be polite)
MAX_RETRIES = 5
TIMEOUT_S = 20
USER_AGENT = "causal-inference-games research script (github.com/joangordo)"

# Numeric review_score codes returned by the API
SCORE_LABELS = {
    9: "Overwhelmingly Positive", 8: "Very Positive", 7: "Positive",
    6: "Mostly Positive", 5: "Mixed", 4: "Mostly Negative", 3: "Negative",
    2: "Very Negative", 1: "Overwhelmingly Negative", 0: "No user reviews",
}

# --- Design ------------------------------------------------------------------
# Each cutoff: share of positive reviews at which the label changes, the
# minimum number of reviews for that label pair, and the minimum review_score
# code that counts as "above the cutoff" (treated).
CUTOFFS = {
    "primary_80": {"c": 0.80, "min_reviews": 50, "treated_min_score": 8,
                   "below": "Mostly Positive", "above": "Very Positive"},
    "secondary_70": {"c": 0.70, "min_reviews": 10, "treated_min_score": 6,
                     "below": "Mixed", "above": "Mostly Positive"},
    "secondary_95": {"c": 0.95, "min_reviews": 500, "treated_min_score": 9,
                     "below": "Very Positive", "above": "Overwhelmingly Positive"},
}
PRIMARY_CUTOFF = "primary_80"
PLACEBO_CUTOFFS = [0.75, 0.85]       # applied to the primary sample
SHARP_COMPLIANCE = 0.99              # >= this share labelled as expected -> sharp RDD
DONUT_PP = 0.25                      # donut radius in percentage points
BANDWIDTH_MULTIPLIERS = [0.5, 0.75, 1.0, 1.5, 2.0]

# --- Outcomes ----------------------------------------------------------------
PRIMARY_OUTCOME = "log_review_growth"    # log(1+reviews_t2) - log(1+reviews_t1)
SECONDARY_OUTCOMES = ["any_new_review"]  # 1 if reviews_t2 > reviews_t1
MIN_GAP_DAYS = 28                        # minimum days between snapshots
ALPHA = 0.05

# --- Covariates for balance tests --------------------------------------------
# Pre-treatment game characteristics from the scraper dataset (October 2026).
# release_year and price_eur are derived in src/panel.py from release_date and
# price_original. Reception-driven fields (curators, awards, press) are excluded.
COVARIATE_COLUMNS: list[str] = ["release_year", "price_eur", "early_access", "n_languages",
                                "n_tags", "about_n_words", "n_screenshots", "n_dlc"]
