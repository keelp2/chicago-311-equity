#!/usr/bin/env python3
"""
Pull Chicago 311 service request data from the Socrata Open Data API.

Downloads completed requests from the last 3 years with location data,
focusing on actionable service types (excludes info-only calls and noise complaints).

No API key required — uses the public endpoint with pagination.
"""

import os
import time
from pathlib import Path

import pandas as pd
import requests

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

ENDPOINT = "https://data.cityofchicago.org/resource/v6vf-nfxy.json"

# Exclude high-volume noise/info types that don't have meaningful response times
EXCLUDE_TYPES = [
    "311 INFORMATION ONLY CALL",
    "Aircraft Noise Complaint",
]

# Focus on completed requests from recent years for meaningful response time analysis
YEARS_BACK = 3


def pull_311_data():
    """Pull 311 data in paginated batches with retry logic."""
    exclude_clause = " AND ".join(f"sr_type != '{t}'" for t in EXCLUDE_TYPES)

    where = (
        f"status = 'Completed' "
        f"AND latitude IS NOT NULL "
        f"AND closed_date IS NOT NULL "
        f"AND created_date >= '2023-09-01T00:00:00' "
        f"AND {exclude_clause}"
    )

    select = (
        "sr_number,sr_type,sr_short_code,owner_department,status,origin,"
        "created_date,closed_date,last_modified_date,"
        "street_address,zip_code,community_area,ward,"
        "latitude,longitude,duplicate,created_hour,created_day_of_week,created_month"
    )

    all_rows = []
    offset = 0
    batch_size = 10000
    max_retries = 3

    print(f"Pulling 311 data (completed requests, {YEARS_BACK}yr, with location)...")
    print(f"Endpoint: {ENDPOINT}")
    print(f"Filter: {where[:100]}...")
    print()

    while True:
        params = {
            "$select": select,
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
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                if attempt < max_retries:
                    wait = attempt * 10
                    print(f"  Timeout on batch at offset {offset}, retrying in {wait}s (attempt {attempt}/{max_retries})...")
                    time.sleep(wait)
                else:
                    print(f"  Failed after {max_retries} attempts at offset {offset}. Saving what we have.")
                    batch = []
                    break

        if not batch:
            break

        all_rows.extend(batch)
        offset += batch_size
        if (offset // batch_size) % 10 == 0:
            print(f"  Fetched {len(all_rows):,} rows...")

        time.sleep(0.5)

    print(f"\nTotal rows: {len(all_rows):,}")

    # Convert to DataFrame
    df = pd.DataFrame(all_rows)

    # Type conversions
    for col in ["created_date", "closed_date", "last_modified_date"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    for col in ["latitude", "longitude"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    for col in ["community_area", "ward", "zip_code", "created_hour", "created_day_of_week", "created_month"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Calculate response time in hours
    df["response_hours"] = (df["closed_date"] - df["created_date"]).dt.total_seconds() / 3600

    # Drop negative/nonsensical response times
    df = df[df["response_hours"] >= 0]

    out_path = DATA_DIR / "chicago_311.parquet"
    df.to_parquet(out_path, index=False)
    print(f"\nSaved: {out_path} ({out_path.stat().st_size / 1e6:.1f} MB)")
    print(f"Date range: {df['created_date'].min()} to {df['created_date'].max()}")
    print(f"Service types: {df['sr_type'].nunique()}")
    print(f"Community areas: {df['community_area'].nunique()}")

    return df


def pull_community_area_income():
    """Pull Census ACS income data for Chicago community areas."""
    print("\n\nPulling Census ACS income by community area...")

    # Chicago community area income — from Census ACS via Chicago Data Portal
    url = "https://data.cityofchicago.org/resource/kn9c-c2s2.json"
    params = {"$limit": 5000}

    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    if data:
        df = pd.DataFrame(data)
        out_path = DATA_DIR / "community_area_socioeconomic.parquet"
        df.to_parquet(out_path, index=False)
        print(f"Saved: {out_path} ({len(df)} community areas)")
        return df
    else:
        print("WARNING: Could not pull community area data. Will use fallback.")
        return None


if __name__ == "__main__":
    pull_311_data()
    pull_community_area_income()
    print("\nDone! Run the analysis notebook next.")
