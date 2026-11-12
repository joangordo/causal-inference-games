"""
Run the Part 2 analysis once BOTH snapshots exist:
build panel (03) -> estimation (04) -> robustness (05) -> report (06).

    python run_analysis.py --covariates-from ../../steam_indie.csv
"""
import argparse
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ap = argparse.ArgumentParser()
ap.add_argument("--t1", default="t1")
ap.add_argument("--t2", default="t2")
ap.add_argument("--covariates-from", default=None)
ap.add_argument("--id-col", default=None)
args = ap.parse_args()

panel_args = ["--t1", args.t1, "--t2", args.t2]
if args.covariates_from:
    panel_args += ["--covariates-from", args.covariates_from]
if args.id_col:
    panel_args += ["--id-col", args.id_col]

steps = [("03_build_panel.py", panel_args), ("04_rdd_estimation.py", []),
         ("05_robustness.py", []), ("06_build_report.py", ["--t1", args.t1])]
for script, extra in steps:
    print(f"\n{'=' * 70}\n>>> {script}\n{'=' * 70}")
    if subprocess.run([sys.executable, str(HERE / "scripts" / script), *extra], cwd=HERE).returncode:
        sys.exit(f"\nPipeline stopped at {script}.")
print("\nDone. Full report: results/REPORT.md")
