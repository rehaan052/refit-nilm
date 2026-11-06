"""Turn each official CLEAN house CSV into a small 1-minute parquet (aggregate + washing machine).

Run locally (light on memory: one house at a time, only 3 columns read), then upload the small
parquet files to Google Drive for the Colab training run.

    python scripts/prepare_minute_data.py
    python scripts/prepare_minute_data.py --houses 2 5
"""
import argparse
import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.data import clean_csv_path, load_clean_house, minute_parquet_path  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--houses", type=int, nargs="*")
    a = ap.parse_args()
    cfg = yaml.safe_load(open(a.config))
    houses = a.houses or cfg["model"]["houses"]
    c = cfg["cleaning"]
    all_logs = {}
    for h in houses:
        ch = cfg["washing_machine_channel"][h]
        if isinstance(ch, list) or ch is None:
            raise SystemExit(f"House {h}: washing_machine_channel must be ONE channel name, got {ch}")
        csv = clean_csv_path(cfg, h)
        print(f"House {h}: reading {csv} (washing machine = {ch}) ...")
        df, log = load_clean_house(
            csv, ch,
            time_zone=cfg["model"].get("clean_time_zone"),
            stuck_min_minutes=c.get("stuck_min_minutes"),
            stuck_min_readings=c.get("stuck_min_readings", 20),
            max_fill_minutes=c["max_fill_minutes"],
        )
        out = minute_parquet_path(cfg, h)
        out.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(out)
        log["wm_channel"] = ch
        log["first"], log["last"] = str(df.index.min()), str(df.index.max())
        all_logs[h] = log
        print(f"  saved {out}  ({len(df):,} minutes)")
    log_path = Path(cfg["paths"]["minute_dir"]) / "prepare_log.json"
    log_path.write_text(json.dumps(all_logs, indent=2, default=str))
    print("log:", log_path)


if __name__ == "__main__":
    main()