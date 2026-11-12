# Analysis plan — Steam review labels (regression discontinuity)

> Committed **after** inspecting the first snapshot (running variable and labels
> only) and **before** the second snapshot exists. No outcome data has been seen.
> Analyses not listed here are reported as *exploratory*.

## 1. Question

Steam shows each game a label based on its share of positive reviews
(e.g. *Mostly Positive* below 80%, *Very Positive* from 80%). Games at 79.5% and
80.5% are practically identical in quality but display different labels.

**Question:** does crossing into a better label cause a game to receive more
new reviews (a proxy for new players) in the following weeks?

## 2. Data and timing

- **Sample:** games in my dataset of Steam indie games translated into Spanish
  that return a valid review summary in both snapshots.
- **Source:** Steam Web API `IUserReviewsService/GetAppReviews` (keyless), reviews by Steam
  purchasers (`purchase_type = 0`) in all languages. This reproduces the counts and labels of the
  store pages (checked on three games against the October scrape). The older
  `store.steampowered.com/appreviews` endpoint was retired by Valve on 22 October 2026.
- **Snapshot t1:** taken first; defines the running variable and the label.
- **Snapshot t2:** at least 28 days after t1 (planned ~5 weeks).

## 3. Running variable, treatment and cutoffs

- **Running variable:** share of positive reviews at t1, centred at the cutoff,
  in percentage points.
- **Treatment:** the label displayed at t1 (numeric `review_score` code).

| Cutoff | Role | c | Eligible games | Below → above |
|---|---|---:|---|---|
| `primary_80` | primary | 80% | ≥ 50 reviews at t1 | Mostly Positive → Very Positive |
| `secondary_70` | secondary | 70% | ≥ 10 reviews at t1 | Mixed → Mostly Positive |
| `secondary_95` | secondary | 95% | ≥ 500 reviews at t1 | Very Positive → Overwhelmingly Positive |

Checked on snapshot t1 (26,294 games) with `scripts/02_inspect_snapshot.py`, before any
outcome exists (see `results/snapshot_t1_inspection.md`):

- Labels switch **exactly** at 70%, 80% and 95% of the unrounded share of positive reviews
  (highest share below 80% still labelled Mostly Positive: 79.99%; lowest labelled Very
  Positive: 80.00%). Compliance is 100% at all three cutoffs: the design is **sharp**.
- No sign of sorting: density test p-values 0.80 (80%), 0.65 (70%) and 0.83 (95%).
- Primary sample: 6,444 games with ≥ 50 reviews; 684 within ±2 pp and 1,662 within ±5 pp
  of the cutoff.
- The store page shows the share truncated (79.97% is displayed as 79%), so the API counts,
  not the displayed percentage, are used as running variable.

## 4. Outcomes

- **Primary:** `log_review_growth` = log(1 + reviews at t2) − log(1 + reviews at t1).
- **Secondary:** `any_new_review` = 1 if the game received at least one new review.

## 5. Estimation

- Local-linear regression on each side of the cutoff, triangular kernel,
  MSE-optimal bandwidth, robust bias-corrected 95% confidence intervals
  (`rdrobust`, Calonico, Cattaneo & Titiunik).
- **Sharp design** if at least 99% of eligible games carry the label expected
  for their side of the cutoff; otherwise **fuzzy design** using the observed label.
- Alpha = 0.05. The only confirmatory test is the primary cutoff with the
  primary outcome. Other combinations are reported as secondary, without
  multiplicity correction, and interpreted cautiously.

## 6. Validity and robustness (primary cutoff, primary outcome)

- **Density test** (Cattaneo-Jansson-Ma) for sorting around the cutoff.
- **Covariate balance:** pre-treatment game characteristics should not jump: release year,
  price (EUR), early access, number of languages, number of tags, length of the description,
  number of screenshots and number of DLCs (from the October 2026 scrape of the store pages).
  The number of reviews at t1 is also tested, but it is a lagged outcome:
  the label existed before t1, so a jump there may reflect past label effects.
  Balance is reported with and without the donut, because games with few
  reviews pile up at exact shares such as 40/50 = 80%.
- **Bandwidth sensitivity:** 0.5×, 0.75×, 1×, 1.5×, 2× the optimal bandwidth.
- **Donut RDD:** excluding games within ±0.25 pp of the cutoff.
- **Placebo cutoffs:** 75% (games below 80% only) and 85% (games above 80% only).

## 7. Interpretation

- The estimate is the effect of the **label**, not of game quality, and is local
  to games near the cutoff.
- It is an intention-to-treat effect of the label shown at t1; some games will
  cross a threshold between snapshots.
- A null result will be reported with its confidence interval: it tells us how
  large an effect can be ruled out.

## 8. What will NOT be done

- No change of cutoffs, outcomes, eligible sample or bandwidth rule after t2 exists.
- No choosing among bandwidths or specifications based on the results.
- No removal of games based on their outcome.

## 9. Known limitations

- The sample is Spanish-translated indie games, not all of Steam.
- Reviews are a proxy for new players, not sales.
- The window between snapshots may include Steam seasonal sales; they affect
  games on both sides of the cutoff, but can change the scale of the outcome.
- Steam's recommendation algorithms may use the review score continuously;
  RDD isolates only the discontinuous jump caused by the label.
