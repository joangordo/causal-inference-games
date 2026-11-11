# Analysis plan — Cookie Cats A/B test

> This plan is committed to the repository **before** any comparison of outcomes
> between arms. The git history is the proof. Analyses not listed here are
> reported as *exploratory*.

## 1. Context and question

Cookie Cats is a mobile puzzle game. Players hit "gates" that force them to wait
or pay before continuing. The experiment moved the first gate from level 30
(control, `gate_30`) to level 40 (treatment, `gate_40`).

**Question:** does moving the first gate to level 40 change player retention?

## 2. Design

- **Unit of randomisation and analysis:** player, assigned at install.
- **Expected split:** 50 / 50.
- **Data:** one row per player; game rounds played in the first 14 days after
  install; retention 1 and 7 days after install.

## 3. Metrics

| Role | Metric | Definition |
|---|---|---|
| Primary | `retention_7` | Player returned 7 days after install (0/1) |
| Secondary | `retention_1` | Player returned 1 day after install (0/1) |
| Guardrail | `sum_gamerounds` | Game rounds in the first 14 days |

## 4. Hypotheses and inference

- H0: retention is equal in both arms. H1: it differs (two-sided).
- **Effect:** difference in proportions, treatment − control, in percentage
  points, plus relative lift.
- **Test:** two-proportion z-test. **Intervals:** 95% Wald CI and 95% percentile
  bootstrap CI (10,000 resamples, seed 42).
- **Multiplicity:** Holm correction over the family {retention_7, retention_1}
  at alpha = 0.05.
- **Guardrail:** difference in mean game rounds with bootstrap CI on the
  winsorised metric (see §6), Mann-Whitney U as robustness. Not part of the
  Holm family; a significant drop is reported as a warning.

## 5. Design-stage power

Assumed baselines (from typical mobile-game benchmarks, not from this data):
D1 = 45%, D7 = 19%. Business MDE: a 1 pp absolute change in each retention
metric. With alpha = 0.05 and power = 80%, see `results/power_analysis.csv`.

## 6. Validity rules (decided in advance)

- **SRM:** chi-square test of arm sizes vs 50/50. If p < 0.001, stop and do not
  estimate effects. If 0.001 ≤ p < 0.05, proceed but report it prominently as a
  limitation and discuss possible causes.
- **Integrity:** no duplicated players, no nulls, no unknown arms (enforced by
  `src/data.py`).
- **Outliers:** detected on the pooled sample, blind to arm. Players with more
  than 10,000 rounds are flagged. For the guardrail metric only, values are
  winsorised at the pooled 99.9th percentile; results are shown with and
  without winsorisation. Retention metrics are not affected and nobody is removed.

## 7. Decision rule

Based on the Holm-adjusted result for `retention_7`:

| Result | Decision |
|---|---|
| Significant decrease with gate_40 | Keep the gate at level 30 |
| Significant increase with gate_40 | Move the gate to level 40 |
| Not significant, 95% CI inside ±1 pp | Practically equivalent; keep level 30 (no change without evidence) |
| Not significant, CI wider than ±1 pp | Inconclusive; recommend a larger or longer test |

`retention_1` and the guardrail inform the recommendation but cannot override
the primary metric on their own.

## 8. What will NOT be done

- **No conditioning on `sum_gamerounds`.** It is measured after assignment and is
  affected by the treatment, so segmenting by "engaged players" or using it as a
  covariate would introduce post-treatment bias.
- No change of primary metric, alpha or decision rule after seeing results.
- No removal of players using criteria that differ between arms.

## 9. Planned exploratory analyses

- Bayesian Beta-Binomial model: probability that each arm is better and
  expected loss of each decision.
- A/A simulations showing how repeated "peeking" inflates false positives, and
  comparison with a sequential testing procedure.

## 10. Known limitations

- No timestamps: novelty effects and test duration cannot be studied.
- No pre-treatment covariates: variance reduction (CUPED) is not possible.
- A single game and a single change: external validity is limited.
