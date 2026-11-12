"""
01 - Take a snapshot of Steam review summaries.

For every app id in your existing Steam dataset, asks Steam's public review
endpoint for the total positive / negative reviews and the label shown on the
store. One request per game, results appended to
data/snapshots/snapshot_<label>.csv.

The run is resumable: if it stops (Ctrl+C, power cut, rate limit), run the
same command again and it continues where it left off.

Examples (from the part2_steam_rdd folder):
    # quick test with 20 games
    python scripts/01_take_snapshot.py --input ../../steam_indie.csv --label test --limit 20
    # full first snapshot
    python scripts/01_take_snapshot.py --input ../../steam_indie.csv --label t1
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from src import config
from src.ids import load_appids
from src.snapshot import SnapshotWriter, already_done, snapshot_path
from src.steam_api import EndpointGone, SteamReviewsClient


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", required=True, help="Your Steam dataset (CSV, Parquet or Excel)")
    ap.add_argument("--label", required=True, help="Snapshot name, e.g. t1 or t2")
    ap.add_argument("--id-col", default=None, help="Column with app ids or store URLs (auto-detected)")
    ap.add_argument("--delay", type=float, default=config.REQUEST_DELAY_S, help="Seconds between requests")
    ap.add_argument("--limit", type=int, default=None, help="Only the first N games (for testing)")
    args = ap.parse_args()

    appids, col = load_appids(args.input, args.id_col)
    if args.limit:
        appids = appids[:args.limit]
    path = snapshot_path(args.label)
    done = already_done(path)
    todo = [a for a in appids if a not in done]
    print(f"Id column: '{col}'. Games in input: {len(appids):,}. Already done: {len(done & set(appids)):,}. "
          f"To fetch: {len(todo):,}.")
    if not todo:
        print("Nothing to do.")
        return
    eta_h = len(todo) * (args.delay + 0.3) / 3600
    print(f"Estimated time: ~{eta_h:.1f} h at {args.delay}s between requests. Output: {path}")

    client = SteamReviewsClient()
    counts: dict[str, int] = {}
    start = time.time()
    try:
        with SnapshotWriter(path) as w:
            for i, appid in enumerate(todo, 1):
                row = client.fetch(appid)
                w.write(row)
                counts[row["status"]] = counts.get(row["status"], 0) + 1
                if i % 100 == 0 or i == len(todo):
                    rate = i / (time.time() - start)
                    left_min = (len(todo) - i) / rate / 60 if rate else float("nan")
                    print(f"  {i:,}/{len(todo):,}  {counts}  ~{left_min:.0f} min left", flush=True)
                time.sleep(args.delay)
    except KeyboardInterrupt:
        print("\nInterrupted. Run the same command again to resume.")
        sys.exit(1)
    except EndpointGone as e:
        sys.exit(f"\nSTOP: {e}. The Steam API has changed; nothing more was requested.")

    df = pd.read_csv(path)
    print("\nDone. Status counts in the whole snapshot file:")
    print(df.drop_duplicates("appid", keep="last")["status"].value_counts().to_string())
    if (df["status"].isin(["http_error", "exception"])).any():
        print("Some requests failed temporarily: run the same command again to retry them.")


if __name__ == "__main__":
    main()
