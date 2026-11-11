# Validity checks (blind to outcomes by arm)

## Sample ratio mismatch

| Arm | Observed | Expected | Share |
|---|---:|---:|---:|
| gate_30 | 44,700 | 45,094.5 | 0.4956 |
| gate_40 | 45,489 | 45,094.5 | 0.5044 |

Chi-square = 6.902, p-value = 0.008608 (threshold alpha_SRM = 0.001).

No SRM detected at the pre-specified threshold.

## Pooled data quality

```json
{
  "n_players": 90189,
  "n_unique_userid": 90189,
  "share_zero_rounds": 0.0442847797403231,
  "n_zero_rounds_but_retained_d1": 87,
  "n_zero_rounds_but_retained_d7": 29,
  "n_retained_d7_not_d1": 3599,
  "rounds_quantiles": {
    "p50": 16.0,
    "p75": 51.0,
    "p90": 134.0,
    "p99": 493.0,
    "p99.9": 1073.6240000000107
  },
  "rounds_max": 49854
}
```

## Most extreme players by game rounds (pooled)

|   userid |   sum_gamerounds |   robust_z_log | above_hard_cap   |
|---------:|-----------------:|---------------:|:-----------------|
|  6390605 |            49854 |           4.99 | True             |
|   871500 |             2961 |           3.23 | False            |
|  3271615 |             2640 |           3.15 | False            |
|  4832608 |             2438 |           3.10 | False            |
|  5346171 |             2294 |           3.07 | False            |
|  5133952 |             2251 |           3.06 | False            |
|  9640085 |             2156 |           3.03 | False            |
|  4090246 |             2124 |           3.02 | False            |
|  9791599 |             2063 |           3.00 | False            |
|   725080 |             2015 |           2.99 | False            |
