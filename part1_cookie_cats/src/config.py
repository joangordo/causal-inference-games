"""
Central configuration for Part 1.

Every analytical decision lives here and in analysis_plan.md, and both are
fixed BEFORE looking at any outcome comparison between the two arms.
Changing a value after seeing results defeats the purpose of the plan.
"""
from pathlib import Path

# --- Paths -------------------------------------------------------------------
PART1_DIR = Path(__file__).resolve().parents[1]
DATA_PATH = PART1_DIR / "data" / "cookie_cats.csv"
RESULTS_DIR = PART1_DIR / "results"
FIGURES_DIR = RESULTS_DIR / "figures"

# --- Experiment design -------------------------------------------------------
CONTROL = "gate_30"      # original game: first gate at level 30
TREATMENT = "gate_40"    # variant: first gate moved to level 40
EXPECTED_SPLIT = {CONTROL: 0.5, TREATMENT: 0.5}

PRIMARY_METRIC = "retention_7"
SECONDARY_METRICS = ["retention_1"]
GUARDRAIL_METRIC = "sum_gamerounds"

# --- Inference ---------------------------------------------------------------
ALPHA = 0.05             # two-sided significance level for retention metrics
POWER = 0.80             # target power used in the design
ALPHA_SRM = 0.001        # stricter threshold for the sample ratio mismatch
                         # test, as is common industry practice
SEED = 42

# --- Assumed baselines for the power analysis --------------------------------
# In a real company these would come from historical, pre-experiment data.
# Here they are fixed a priori from typical mobile-game benchmarks and are
# NOT updated after seeing this dataset.
BASELINE = {"retention_1": 0.45, "retention_7": 0.19}

# Smallest absolute change that would matter for the business
# (0.01 = 1 percentage point).
MDE_ABS = {"retention_1": 0.010, "retention_7": 0.010}

# --- Outlier rule (pre-specified, pooled sample, blind to arm) ---------------
# Players above this many game rounds are flagged and reported.
# For the guardrail metric only, values are winsorised at the pooled quantile.
OUTLIER_ROUNDS_HARD_CAP = 10_000
WINSOR_QUANTILE = 0.999
