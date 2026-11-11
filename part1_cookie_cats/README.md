# Part 1 — Cookie Cats A/B test

Run from this folder, in order:

```bash
pip install -r ../requirements.txt
python scripts/01_power_analysis.py   # design stage, no outcome comparison
python scripts/02_validity_checks.py  # SRM + pooled data quality, blind to arm
python -m pytest -q                   # unit tests on synthetic data
```

Outputs go to `results/`. The analysis plan is in `analysis_plan.md`.
