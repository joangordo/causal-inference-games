# Effect estimation (confirmatory)

_Plan committed in c82a6af 2026-11-11 11:20:55 +0100_

## Decision (primary metric, rule from §7 of the plan)

**Significant decrease with gate_40: keep the gate at level 30**

## Retention

| Metric | Control | Treatment | Diff | 95% Wald CI | 95% bootstrap CI | Rel. lift | p | p (Holm) |
|---|---:|---:|---:|---|---|---:|---:|---:|
| retention_7 (primary) | 0.1902 | 0.1820 | -0.82 pp | [-1.33 pp, -0.31 pp] | [-1.34 pp, -0.31 pp] | -4.31% | 0.0016 | 0.0031 |
| retention_1 (secondary) | 0.4482 | 0.4423 | -0.59 pp | [-1.24 pp, +0.06 pp] | [-1.25 pp, +0.07 pp] | -1.32% | 0.0744 | 0.0744 |

## Guardrail: game rounds in the first 14 days

| Version | Mean C | Mean T | Median C | Median T | Diff in means | 95% bootstrap CI |
|---|---:|---:|---:|---:|---:|---|
| raw | 52.46 | 51.30 | 17 | 16 | -1.16 | [-4.10, +0.95] |
| winsorised (cap=1074) | 51.03 | 50.94 | 17 | 16 | -0.10 | [-1.36, +1.19] |

Mann-Whitney U p-value: 0.0502

Guardrail: no significant drop on the winsorised metric.
