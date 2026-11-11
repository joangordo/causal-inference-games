"""Loading and schema validation of the Cookie Cats dataset."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from . import config

EXPECTED_COLUMNS = ["userid", "version", "sum_gamerounds", "retention_1", "retention_7"]
_BOOL_MAP = {"True": 1, "False": 0, "true": 1, "false": 0, True: 1, False: 0, 1: 1, 0: 0}


class DataValidationError(ValueError):
    """Raised when the raw file does not match the expected schema."""


def load_data(path: str | Path = config.DATA_PATH) -> pd.DataFrame:
    """Read the raw CSV, validate it and return a clean DataFrame.

    Retention columns are returned as 0/1 integers and `version` as an
    ordered categorical (control first). Any problem raises a
    DataValidationError instead of being silently fixed.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Data file not found: {path}. See data/README.md.")

    df = pd.read_csv(path)
    return validate(df)


def validate(df: pd.DataFrame) -> pd.DataFrame:
    """Validate schema and basic integrity. Returns a cleaned copy."""
    missing = [c for c in EXPECTED_COLUMNS if c not in df.columns]
    if missing:
        raise DataValidationError(f"Missing columns: {missing}")

    df = df[EXPECTED_COLUMNS].copy()

    if df.isna().any().any():
        bad = df.columns[df.isna().any()].tolist()
        raise DataValidationError(f"Null values found in columns: {bad}")

    if df["userid"].duplicated().any():
        n_dup = int(df["userid"].duplicated().sum())
        raise DataValidationError(f"{n_dup} duplicated userid values: a player in both arms "
                                  "or a logging error must be investigated before analysis.")

    arms = {config.CONTROL, config.TREATMENT}
    unknown = set(df["version"].unique()) - arms
    if unknown:
        raise DataValidationError(f"Unknown experiment arms: {sorted(unknown)}")

    for col in ["retention_1", "retention_7"]:
        mapped = df[col].map(_BOOL_MAP)
        if mapped.isna().any():
            raise DataValidationError(f"Column {col} has values that are not boolean.")
        df[col] = mapped.astype("int8")

    if not pd.api.types.is_integer_dtype(df["sum_gamerounds"]):
        raise DataValidationError("sum_gamerounds must be an integer column.")
    if (df["sum_gamerounds"] < 0).any():
        raise DataValidationError("sum_gamerounds has negative values.")

    df["version"] = pd.Categorical(df["version"],
                                   categories=[config.CONTROL, config.TREATMENT],
                                   ordered=True)
    return df.reset_index(drop=True)
