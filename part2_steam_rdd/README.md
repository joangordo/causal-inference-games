# Part 2 — Steam review labels: a natural experiment (RDD)

Does showing *Very Positive* instead of *Mostly Positive* cause a game to get
more new reviews? Steam assigns labels with fixed thresholds on the share of
positive reviews, so games just above and just below 80% are nearly identical
except for the label. A regression discontinuity design compares them.

The data are two snapshots of Steam's public review summaries for the games
in my own dataset of indie games translated into Spanish, taken several weeks apart.

## Workflow

The steps are spread over time because the outcome needs two snapshots.

```bash
# 0. quick API test with 20 games
python scripts/01_take_snapshot.py --input PATH/TO/your_dataset.csv --label test --limit 20

# 1. first snapshot (several hours, resumable: rerun the same command if it stops)
python scripts/01_take_snapshot.py --input PATH/TO/your_dataset.csv --label t1

# 2. inspect labels and cutoffs on t1 only (no outcome data)
python scripts/02_inspect_snapshot.py --label t1

# 3. review analysis_plan.md and src/config.py, then commit the plan

# 4. at least 28 days later: second snapshot
python scripts/01_take_snapshot.py --input PATH/TO/your_dataset.csv --label t2

# 5. analysis: panel, estimation, robustness, report
python run_analysis.py --covariates-from PATH/TO/your_dataset.csv
```

Scripts 04 and 05 refuse to run until `analysis_plan.md` is committed to git.

## Pipeline

| Script | What it does |
|---|---|
| `01_take_snapshot.py` | Review totals and label for every game, one request each, resumable |
| `02_inspect_snapshot.py` | Label codes, empirical switch points, density test (t1 only) |
| `03_build_panel.py` | Merges t1 and t2, computes outcomes, adds covariates |
| `04_rdd_estimation.py` | Local-linear RDD at 70%, 80% and 95% (`rdrobust`) |
| `05_robustness.py` | Density, covariate balance, bandwidths, donut, placebo cutoffs |
| `06_build_report.py` | Assembles `results/REPORT.md` |

Unit tests (`python -m pytest -q`) mock the Steam API and use synthetic data with a
known discontinuity.
