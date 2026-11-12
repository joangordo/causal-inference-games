"""
06 - Assemble the Part 2 report into results/REPORT.md.

Run from the part2_steam_rdd folder:
    python scripts/06_build_report.py --t1 t1
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import config


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--t1", default="t1")
    args = ap.parse_args()
    sections = [("Snapshot inspection", f"snapshot_{args.t1}_inspection.md", "design check, no outcomes"),
                ("RDD estimates", "rdd_report.md", "confirmatory"),
                ("Validity and robustness", "robustness_report.md", "confirmatory checks")]
    missing = [f for _, f, _ in sections if not (config.RESULTS_DIR / f).exists()]
    if missing:
        sys.exit(f"STOP: missing outputs {missing}. Run scripts 02-05 first.")
    parts = ["# Part 2 — Steam review labels: regression discontinuity report", "",
             "Confirmatory analyses follow the pre-registered `analysis_plan.md`.", ""]
    for i, (title, fname, kind) in enumerate(sections, 1):
        body = (config.RESULTS_DIR / fname).read_text(encoding="utf-8")
        body = "\n".join(("##" + l) if l.startswith("#") else l for l in body.splitlines())
        parts += [f"## {i}. {title}", "", f"_{kind}_", "", body, ""]
    out = config.RESULTS_DIR / "REPORT.md"
    out.write_text("\n".join(parts), encoding="utf-8")
    print(f"Saved: {out}")


if __name__ == "__main__":
    main()
