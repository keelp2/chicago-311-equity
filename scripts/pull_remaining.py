#!/usr/bin/env python3
"""
Pull remaining 311 data (2023-09 to 2025-10) in quarterly chunks.
Appends to existing parquet file.
"""

import time
from pathlib import Path
import pandas as pd
import requests

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
ENDPOINT = "https://data.cityofchicago.org/resource/v6vf-nfxy.json"

EXCLUDE_TYPES = ["311 INFORMATION ONLY CALL", "Aircraft Noise Complaint"]

SELECT = (
    "sr_number,sr_type,sr_short_code,owner_department,status,origin,"
    "created_date,closed_date,last_modified_date,"
    "street_address,zip_code,community_area,ward,"
    "latitude,longitude,duplicate,created_hour,created_day_of_week,created_month"
)

# Quarterly chunks to pull (start, end)
CHUNKS = [
    ("2023-09-01", "2023-12-31"),
    ("2024-01-01", "2024-03-31"),
    ("2024-04-01", "2024-06-30"),
    ("2024-07-01", "2024-09-30"),
    ("2024-10-01", "2024-12-31"),
    ("2025-01-01", "2025-03-31"),
    ("2025-04-01", "2025-06-30"),
    ("2025-07-01", "2025-10-11"),
]


def pull_chunk(start, end, max_retries=3):
    """Pull one date range with pagination."""
    exclude_clause = " AND ".join(f"sr_type != '{t}'" for t in EXCLUDE_TYPES)
    where = (
        f"status = 'Completed' "
        f"AND latitude IS NOT NULL "
        f"AND closed_date IS NOT NULL "
        f"AND created_date >= '{start}T00:00:00' "
        f"AND created_date < '{end}T23:59:59' "
        f"AND {exclude_clause}"
    )

    rows = []
    offset = 0
    batch_size = 10000

    while True:
        params = {
            "$select": SELECT,
            "$where": where,
            "$order": "created_date DESC",
            "$limit": batch_size,
            "$offset": offset,
        }

        for attempt in range(1, max_retries + 1):
            try:
                resp = requests.get(ENDPOINT, params=params, timeout=60)
                resp.raise_for_status()
                batch = resp.json()
                break
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
                if attempt < max_retries:
                    wait = attempt * 10
                    print(f"    Retry {attempt}/{max_retries} (offset {offset}), waiting {wait}s...")
                    time.sleep(wait)
                else:
                    print(f"    FAILED at offset {offset} after {max_retries} tries")
                    return rows

        if not batch:
            break

        rows.extend(batch)
        offset += batch_size
        time.sleep(0.5)

    return rows


def main():
    existing = pd.read_parquet(DATA_DIR / "chicago_311.parquet")
    print(f"Existing data: {len(existing):,} rows ({existing['created_date'].min():%Y-%m-%d} to {existing['created_date'].max():%Y-%m-%d})")

    all_new = []
    for start, end in CHUNKS:
        print(f"\nPulling {start} to {end}...")
        rows = pull_chunk(start, end)
        print(f"  Got {len(rows):,} rows")
        all_new.extend(rows)

    print(f"\nTotal new rows: {len(all_new):,}")

    if not all_new:
        print("No new data pulled.")
        return

    new_df = pd.DataFrame(all_new)

    # Type conversions
    for col in ["created_date", "closed_date", "last_modified_date"]:
        if col in new_df.columns:
            new_df[col] = pd.to_datetime(new_df[col], errors="coerce")
    for col in ["latitude", "longitude"]:
        if col in new_df.columns:
            new_df[col] = pd.to_numeric(new_df[col], errors="coerce")
    for col in ["community_area", "ward", "zip_code", "created_hour", "created_day_of_week", "created_month"]:
        if col in new_df.columns:
            new_df[col] = pd.to_numeric(new_df[col], errors="coerce")

    new_df["response_hours"] = (new_df["closed_date"] - new_df["created_date"]).dt.total_seconds() / 3600
    new_df = new_df[new_df["response_hours"] >= 0]

    # Combine and deduplicate
    combined = pd.concat([existing, new_df], ignore_index=True)
    combined = combined.drop_duplicates(subset="sr_number", keep="first")
    combined = combined.sort_values("created_date").reset_index(drop=True)

    out_path = DATA_DIR / "chicago_311.parquet"
    combined.to_parquet(out_path, index=False)
    print(f"\nCombined: {len(combined):,} rows")
    print(f"Date range: {combined['created_date'].min():%Y-%m-%d} to {combined['created_date'].max():%Y-%m-%d}")
    print(f"Saved: {out_path} ({out_path.stat().st_size / 1e6:.1f} MB)")

    # Verify monthly coverage
    print("\nRows per month:")
    print(combined.groupby(combined['created_date'].dt.to_period('M')).size().to_string())


if __name__ == "__main__":
    main()
