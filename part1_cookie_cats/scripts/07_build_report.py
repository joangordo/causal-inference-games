"""
07 - Build the full Part 1 report.

Concatenates the reports written by scripts 01-06 into results/REPORT.md,
in order, with a table of contents. Run it after the other scripts.

Run from the part1_cookie_cats folder:
    python scripts/07_build_report.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from src import config

SECTIONS = [
    ("Design-stage power", "power_analysis.csv", "confirmatory design"),
    ("Validity checks", "validity_report.md", "confirmatory"),
    ("Effect estimation", "effect_report.md", "confirmatory"),
    ("Bayesian analysis", "bayesian_report.md", "exploratory"),
    ("Peeking and sequential testing", "peeking_report.md", "exploratory"),
    ("Post-treatment bias", "post_treatment_report.md", "exploratory"),
]


def power_markdown(path: Path) -> str:
    df = pd.read_csv(path)
    lines = ["| Metric | Baseline | MDE | Required n/arm | Enrolled n/arm | Achieved MDE | Power at MDE |",
             "|---|---:|---:|---:|---:|---:|---:|"]
    for _, r in df.iterrows():
        lines.append(f"| {r.metric} | {r.assumed_baseline:.0%} | {100 * r.business_mde_abs:g} pp "
                     f"| {r.required_n_per_arm:,} | {r.enrolled_n_per_arm_min:,} "
                     f"| {100 * r.achieved_mde_abs:.2f} pp | {r.power_for_business_mde:.1%} |")
    lines += ["", "![MDE](figures/01_mde_vs_sample_size.png)"]
    return "\n".join(lines)


def demote_headings(text: str) -> str:
    """Turn '# X' into '### X' so sections nest under the report headings."""
    return "\n".join(("##" + line) if line.startswith("#") else line for line in text.splitlines())


def main() -> None:
    missing = [f for _, f, _ in SECTIONS if not (config.RESULTS_DIR / f).exists()]
    if missing:
        sys.exit(f"STOP: missing outputs {missing}. Run scripts 01-06 first.")

    parts = ["# Part 1 — Cookie Cats A/B test: full report", "",
             "Confirmatory sections follow the pre-registered `analysis_plan.md`. "
             "Exploratory sections are labelled as such.", "", "## Contents", ""]
    parts += [f"{i}. [{title}](#{i}-{title.lower().replace(' ', '-')}) — _{kind}_"
              for i, (title, _, kind) in enumerate(SECTIONS, 1)]
    for i, (title, fname, kind) in enumerate(SECTIONS, 1):
        path = config.RESULTS_DIR / fname
        body = power_markdown(path) if fname.endswith(".csv") else demote_headings(path.read_text(encoding="utf-8"))
        parts += ["", f"## {i}. {title}", "", f"_{kind}_", "", body]
    out = config.RESULTS_DIR / "REPORT.md"
    out.write_text("\n".join(parts) + "\n", encoding="utf-8")
    print(f"Saved: {out}")


if __name__ == "__main__":
    main()
