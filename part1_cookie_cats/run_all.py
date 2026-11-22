"""
Run the whole Part 1 pipeline in order and stop at the first error.

    python run_all.py

Script 03 refuses to run until analysis_plan.md is committed to git.
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = sorted((HERE / "scripts").glob("0*.py"))

for script in SCRIPTS:
    print(f"\n{'=' * 70}\n>>> {script.name}\n{'=' * 70}")
    result = subprocess.run([sys.executable, str(script)], cwd=HERE)
    if result.returncode != 0:
        sys.exit(f"\nPipeline stopped at {script.name}.")
print("\nAll scripts finished. Full report: results/REPORT.md")
