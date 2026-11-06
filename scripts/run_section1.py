"""Section 1 end-to-end: raw House 1 CSV part files -> cleaned 1-minute parquet + JSON log.

Usage (from the project root):
    python scripts/run_section1.py
    python scripts/run_section1.py --raw data/raw/a.csv data/raw/b.csv
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.cleaning import outage_table, run_cleaning_pipeline  # noqa: E402
from src.io import load_config, load_house_parts, raw_house1_paths, resolve  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", nargs="+", default=None,
                        help="raw House 1 CSV file(s), in order (default: paths.raw_house1_files)")
    args = parser.parse_args()

    cfg = load_config()
    raw_paths = args.raw or raw_house1_paths(cfg)
    out_dir = resolve(cfg["paths"]["processed_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading {raw_paths} ...")
    df_raw = load_house_parts(raw_paths)
    print(f"  {len(df_raw):,} rows, columns: {list(df_raw.columns)}")
    print(df_raw.groupby("part").size().to_string())

    clean, log = run_cleaning_pipeline(df_raw, cfg)

    out_file = out_dir / "house1_raw_cleaned_1min.parquet"
    clean.to_parquet(out_file)
    outage_table(clean).to_csv(out_dir / "house1_outages.csv", index=False)
    with open(out_dir / "house1_cleaning_log.json", "w") as f:
        json.dump(log, f, indent=2, default=str)

    print(json.dumps(log, indent=2, default=str))
    print(f"\nSaved {out_file}")


if __name__ == "__main__":
    main()