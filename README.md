# Causal inference for games

Two ways of measuring the effect of a change in a game, with the analysis plan written
before looking at the results.

| Part | Question | Method | Status |
|---|---|---|---|
| [1. Cookie Cats](part1_cookie_cats/) | Does moving the first gate of a mobile game from level 30 to 40 change retention? | Randomised A/B test: pre-registered plan, blind validity checks, Holm correction, Bayesian expected loss, simulations of peeking and post-treatment bias | Done |
| [2. Steam review labels](part2_steam_rdd/) | Does showing *Very Positive* instead of *Mostly Positive* bring a game more reviews? | Natural experiment: regression discontinuity on Steam's label thresholds, with data I collect in two snapshots | In progress (second snapshot due December 2026) |

**Part 1 in one line:** the later gate lowered 7-day retention by 0.82 percentage points
(95% CI −1.33 to −0.31, Holm-adjusted p = 0.003), so the gate stays at level 30.

Each part is self-contained, with its own README, analysis plan, scripts and tests.
The analysis plans are committed to git before the effects are estimated, and the estimation
scripts refuse to run otherwise.

## Requirements

Python 3.11, then `pip install -r requirements.txt`. See each part for how to run it.
