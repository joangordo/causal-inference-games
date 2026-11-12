"""
03 - Build the analysis panel from two snapshots.

Merges snapshot t1 and t2, computes the outcomes (log growth in reviews and
whether any new review arrived) and, optionally, merges pre-treatment game
characteristics from your original dataset for balance tests.

Run from the part2_steam_rdd folder:
    python scripts/03_build_panel.py --t1 t1 --t2 t2 --covariates-from ../../steam_indie.csv
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from src import config
from src.ids import extract_appids, read_table
from src.panel import build_panel, prepare_covariates
from src.snapshot import load_snapshot


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--t1", default="t1")
    ap.add_argument("--t2", default="t2")
    ap.add_argument("--covariates-from", default=None, help="Original dataset with game characteristics")
    ap.add_argument("--id-col", default=None)
    ap.add_argument("--allow-short-gap", action="store_true", help="Only for testing")
    args = ap.parse_args()

    t1, t2 = load_snapshot(args.t1), load_snapshot(args.t2)

    cov = None
    if args.covariates_from and config.COVARIATE_COLUMNS:
        raw = prepare_covariates(read_table(args.covariates_from))
        ids, _ = extract_appids(raw, args.id_col)
        missing = [c for c in config.COVARIATE_COLUMNS if c not in raw.columns]
        if missing:
            sys.exit(f"STOP: covariates not found in dataset: {missing}")
        cov = raw[config.COVARIATE_COLUMNS].assign(appid=ids).dropna(subset=["appid"])
        cov["appid"] = cov["appid"].astype(int)
    elif args.covariates_from:
        print("Note: COVARIATE_COLUMNS is empty in src/config.py, no covariates merged.")

    panel, gap = build_panel(t1, t2, cov)
    if gap < config.MIN_GAP_DAYS and not args.allow_short_gap:
        sys.exit(f"STOP: median gap between snapshots is {gap:.1f} days "
                 f"(< {config.MIN_GAP_DAYS} required by the plan).")

    config.PANEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    panel.to_csv(config.PANEL_PATH, index=False)
    print(f"Games in t1: {len(t1):,} | t2: {len(t2):,} | panel: {len(panel):,}")
    print(f"Median gap: {gap:.1f} days")
    print(f"Games with fewer reviews at t2 than t1 (deleted reviews): {(panel['new_reviews'] < 0).sum():,}")
    print(f"Share with at least one new review: {panel['any_new_review'].mean():.3f}")
    print(f"Saved: {config.PANEL_PATH}")


if __name__ == "__main__":
    main()
