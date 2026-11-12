"""Read Steam app ids from the user's existing dataset (CSV, Parquet or Excel)."""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

ID_CANDIDATES = ["appid", "app_id", "steam_appid", "steam_app_id", "AppID", "appID", "id"]
URL_CANDIDATES = ["url", "store_url", "link", "steam_url", "game_url"]
_APP_RE = re.compile(r"/app/(\d+)")


def read_table(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".csv":
        df = pd.read_csv(path, low_memory=False)
        if df.shape[1] == 1 and ";" in str(df.columns[0]):  # Excel-style CSV
            df = pd.read_csv(path, sep=";", low_memory=False)
        return df
    if suffix in (".parquet", ".pq"):
        return pd.read_parquet(path)
    if suffix in (".xlsx", ".xls"):
        return pd.read_excel(path)
    raise ValueError(f"Unsupported file type: {suffix}")


def _to_appid(value) -> int | None:
    if pd.isna(value):
        return None
    s = str(value).strip()
    m = _APP_RE.search(s)
    if m:
        return int(m.group(1))
    s = s.split(".")[0]  # "620.0" -> "620"
    return int(s) if s.isdigit() else None


def detect_id_column(df: pd.DataFrame) -> str:
    for c in ID_CANDIDATES + URL_CANDIDATES:
        if c in df.columns:
            return c
    lowered = {c.lower(): c for c in df.columns}
    for c in ID_CANDIDATES + URL_CANDIDATES:
        if c.lower() in lowered:
            return lowered[c.lower()]
    raise ValueError(f"Could not find an app id column. Columns: {list(df.columns)[:30]}... "
                     "Pass it explicitly with --id-col.")


def extract_appids(df: pd.DataFrame, id_col: str | None = None) -> tuple[pd.Series, str]:
    """Return a Series of app ids aligned with df (NaN where not parseable)."""
    col = id_col or detect_id_column(df)
    if col not in df.columns:
        raise ValueError(f"Column '{col}' not in dataset.")
    ids = df[col].map(_to_appid)
    return ids.astype("Int64"), col


def load_appids(path: str | Path, id_col: str | None = None) -> tuple[list[int], str]:
    df = read_table(path)
    ids, col = extract_appids(df, id_col)
    unique = sorted(set(int(i) for i in ids.dropna()))
    if not unique:
        raise ValueError(f"No valid app ids found in column '{col}'.")
    return unique, col
