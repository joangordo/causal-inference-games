"""Resumable snapshot writer: one CSV per snapshot, appended row by row."""
from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd

from . import config
from .steam_api import FIELDS, PERMANENT_STATUSES


def snapshot_path(label: str) -> Path:
    return config.SNAPSHOT_DIR / f"snapshot_{label}.csv"


def already_done(path: Path) -> set[int]:
    """App ids with a permanent result. Transient errors are retried."""
    if not path.exists():
        return set()
    df = pd.read_csv(path, usecols=["appid", "status"])
    return set(df.loc[df["status"].isin(PERMANENT_STATUSES), "appid"].astype(int))


class SnapshotWriter:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        new = not path.exists()
        self._fh = open(path, "a", newline="", encoding="utf-8")
        self._w = csv.DictWriter(self._fh, fieldnames=FIELDS)
        if new:
            self._w.writeheader()

    def write(self, row: dict) -> None:
        self._w.writerow(row)
        self._fh.flush()

    def close(self) -> None:
        self._fh.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def load_snapshot(label: str) -> pd.DataFrame:
    """Latest row per app id, keeping only successful fetches."""
    path = snapshot_path(label)
    if not path.exists():
        raise FileNotFoundError(f"Snapshot not found: {path}")
    df = pd.read_csv(path)
    df["fetched_at_utc"] = pd.to_datetime(df["fetched_at_utc"], utc=True)
    df = df.sort_values("fetched_at_utc").drop_duplicates("appid", keep="last")
    return df[df["status"] == "ok"].reset_index(drop=True)
