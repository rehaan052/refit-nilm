"""Loading config and REFIT CSV files."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml

from src.cleaning import power_columns, standardise_columns

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_config(path: str | Path | None = None) -> dict:
    """Read config.yaml (default: the one in the project root)."""
    path = Path(path) if path else PROJECT_ROOT / "config.yaml"
    with open(path) as f:
        return yaml.safe_load(f)


def resolve(rel_path: str | Path) -> Path:
    """Turn a path from config.yaml (relative to the project root) into an absolute path."""
    p = Path(rel_path)
    return p if p.is_absolute() else PROJECT_ROOT / p


def load_house_csv(path: str | Path, nrows: int | None = None) -> pd.DataFrame:
    """Read a REFIT house CSV (raw or cleaned).
    - Column names are normalised to lower case: time, unix, aggregate, appliance1..9, (issues).
    - Power columns are stored as float32.
    - Timestamps are NOT parsed here, so inspection can look at the raw strings."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Put the file there or fix the paths in config.yaml."
        )
    df = pd.read_csv(path, nrows=nrows)
    df = standardise_columns(df)
    for col in power_columns(df):
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("float32")
    return df


def raw_house1_paths(cfg: dict) -> list[str]:
    """List of raw House 1 files from config (supports one file or several parts)."""
    p = cfg["paths"]
    if "raw_house1_files" in p:
        return list(p["raw_house1_files"])
    return [p["raw_house1_file"]]


def load_house_parts(paths: list) -> pd.DataFrame:
    """Load part files of one house in the given order and stack them.
    A 'part' column (1, 2, ...) records which file each row came from.
    No sorting or dedup here; that happens in the cleaning pipeline."""
    frames = []
    for i, p in enumerate(paths, start=1):
        df = load_house_csv(resolve(p))
        df["part"] = i
        frames.append(df)
    cols = [list(f.columns) for f in frames]
    if any(c != cols[0] for c in cols):
        raise ValueError(f"Part files have different columns: {cols}")
    return pd.concat(frames, ignore_index=True)