"""Fetch daily commodity prices from the data.gov.in Open Government Data API.

This script pulls mandi price records for the five target commodities via the
public OGD REST endpoint.  It supports incremental ingestion through a
watermark file that records the last successfully fetched date, so repeated
runs only download new data.

Environment
-----------
DATA_GOV_API_KEY : str
    Your personal API key from https://data.gov.in (free registration).
    Can also be passed via ``--api-key``.

Usage
-----
# Fetch everything since the last watermark (or last 7 days on first run):
python scripts/fetch_live_data.py

# Fetch a specific date:
python scripts/fetch_live_data.py --date 2026-06-20

# Fetch the last N days regardless of watermark:
python scripts/fetch_live_data.py --days-back 30

# Full refresh — re-download all available data:
python scripts/fetch_live_data.py --full-refresh
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
import requests

from common import RAW_DIR, TARGET_COMMODITIES, ensure_directories


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

API_BASE = "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070"
PAGE_LIMIT = 1000           # max records per API call
MAX_RETRIES = 4             # total attempts per request
RETRY_BACKOFF = 2.0         # exponential backoff base (seconds)
REQUEST_TIMEOUT = 30        # seconds
RATE_LIMIT_DELAY = 0.5      # polite delay between paginated requests

WATERMARK_PATH = Path(__file__).resolve().parents[1] / "data" / "ingestion_metadata.json"

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
LOGGER = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Watermark helpers
# ---------------------------------------------------------------------------

def read_watermark() -> date | None:
    """Return the last-ingested date from the watermark file, or None."""
    if not WATERMARK_PATH.exists():
        return None
    try:
        meta = json.loads(WATERMARK_PATH.read_text(encoding="utf-8"))
        return date.fromisoformat(meta["last_ingested_date"])
    except (json.JSONDecodeError, KeyError, ValueError):
        return None


def write_watermark(ingested_date: date) -> None:
    """Persist the most recent successfully ingested date."""
    meta: dict[str, object] = {}
    if WATERMARK_PATH.exists():
        try:
            meta = json.loads(WATERMARK_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass

    meta["last_ingested_date"] = ingested_date.isoformat()
    meta["last_run_utc"] = datetime.utcnow().isoformat(timespec="seconds")
    WATERMARK_PATH.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    LOGGER.info("Watermark updated → %s", ingested_date.isoformat())


# ---------------------------------------------------------------------------
# API client
# ---------------------------------------------------------------------------

def _get_api_key(cli_key: str | None) -> str:
    """Resolve the API key from CLI arg → environment variable."""
    key = cli_key or os.environ.get("DATA_GOV_API_KEY")
    if not key:
        LOGGER.error(
            "No API key supplied.  Set DATA_GOV_API_KEY in your environment "
            "or pass --api-key.  Register free at https://data.gov.in"
        )
        sys.exit(1)
    return key


def _fetch_page(
    api_key: str,
    commodity: str,
    target_date: str,
    offset: int,
) -> dict:
    """Fetch one page of results with retry + exponential backoff."""
    params = {
        "api-key": api_key,
        "format": "json",
        "limit": PAGE_LIMIT,
        "offset": offset,
        "filters[commodity]": commodity,
        "filters[arrival_date]": target_date,
    }

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(API_BASE, params=params, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as exc:
            wait = RETRY_BACKOFF ** attempt
            LOGGER.warning(
                "Attempt %d/%d failed for %s on %s (offset %d): %s  "
                "— retrying in %.1fs",
                attempt, MAX_RETRIES, commodity, target_date, offset, exc, wait,
            )
            if attempt < MAX_RETRIES:
                time.sleep(wait)

    LOGGER.error(
        "All %d attempts exhausted for %s on %s (offset %d)",
        MAX_RETRIES, commodity, target_date, offset,
    )
    return {"records": []}


def fetch_commodity_date(api_key: str, commodity: str, target_date: str) -> list[dict]:
    """Paginate through all records for one commodity on one date."""
    all_records: list[dict] = []
    offset = 0

    while True:
        data = _fetch_page(api_key, commodity, target_date, offset)
        records = data.get("records", [])
        if not records:
            break
        all_records.extend(records)
        LOGGER.debug(
            "  %s / %s — fetched %d (total %d)",
            commodity, target_date, len(records), len(all_records),
        )
        if len(records) < PAGE_LIMIT:
            break  # last page
        offset += PAGE_LIMIT
        time.sleep(RATE_LIMIT_DELAY)

    return all_records


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def fetch_date_range(
    api_key: str,
    start: date,
    end: date,
) -> pd.DataFrame:
    """Fetch all target commodities for every date in [start, end]."""
    all_records: list[dict] = []
    current = start

    while current <= end:
        date_str = current.strftime("%d/%m/%Y")  # API expects DD/MM/YYYY
        for commodity in TARGET_COMMODITIES:
            LOGGER.info("Fetching %s for %s …", commodity, current.isoformat())
            records = fetch_commodity_date(api_key, commodity, date_str)
            all_records.extend(records)
            time.sleep(RATE_LIMIT_DELAY)
        current += timedelta(days=1)

    if not all_records:
        LOGGER.warning("No records returned from the API for the requested range.")
        return pd.DataFrame()

    frame = pd.DataFrame(all_records)
    return frame


def normalize_api_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Rename API response columns to match the project's raw CSV schema."""
    if frame.empty:
        return frame

    # The data.gov.in API returns these column names (may vary slightly)
    rename_map = {
        "state": "State",
        "district": "District",
        "market": "Market",
        "commodity": "Commodity",
        "variety": "Variety",
        "grade": "Grade",
        "arrival_date": "Arrival_Date",
        "min_price": "Min_Price",
        "max_price": "Max_Price",
        "modal_price": "Modal_Price",
    }
    # Only rename columns that actually exist
    rename_map = {k: v for k, v in rename_map.items() if k in frame.columns}
    frame = frame.rename(columns=rename_map)

    # Keep only the columns we need (drop any extras the API sends)
    keep = [
        "State", "District", "Market", "Commodity", "Variety",
        "Grade", "Arrival_Date", "Min_Price", "Max_Price", "Modal_Price",
    ]
    keep = [c for c in keep if c in frame.columns]
    return frame[keep].copy()


def save_to_raw(frame: pd.DataFrame, label: str) -> Path | None:
    """Write the fetched data as a dated CSV in data/raw/."""
    if frame.empty:
        LOGGER.info("Nothing to save for %s.", label)
        return None

    filename = f"mandi_live_{label}.csv"
    out_path = RAW_DIR / filename
    frame.to_csv(out_path, index=False)
    LOGGER.info("Saved %d records → %s", len(frame), out_path)
    return out_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch daily mandi prices from data.gov.in",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="data.gov.in API key (or set DATA_GOV_API_KEY env var)",
    )
    parser.add_argument(
        "--date",
        default=None,
        help="Fetch a single date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--days-back",
        type=int,
        default=None,
        help="Fetch the last N days regardless of watermark",
    )
    parser.add_argument(
        "--full-refresh",
        action="store_true",
        help="Ignore watermark and fetch maximum available history (last 365 days)",
    )
    return parser.parse_args()


def main() -> None:
    """Entry point — resolve date range and kick off the fetch."""
    args = parse_args()
    ensure_directories()
    api_key = _get_api_key(args.api_key)

    today = date.today()

    if args.date:
        # Single-date mode
        target = date.fromisoformat(args.date)
        frame = fetch_date_range(api_key, target, target)
        frame = normalize_api_frame(frame)
        save_to_raw(frame, target.isoformat())
        write_watermark(target)

    elif args.days_back:
        # Explicit look-back window
        start = today - timedelta(days=args.days_back)
        frame = fetch_date_range(api_key, start, today)
        frame = normalize_api_frame(frame)
        save_to_raw(frame, f"{start.isoformat()}_to_{today.isoformat()}")
        write_watermark(today)

    elif args.full_refresh:
        # Pull up to a year of history
        start = today - timedelta(days=365)
        LOGGER.info("Full refresh: fetching %s → %s", start, today)
        frame = fetch_date_range(api_key, start, today)
        frame = normalize_api_frame(frame)
        save_to_raw(frame, f"full_{start.isoformat()}_to_{today.isoformat()}")
        write_watermark(today)

    else:
        # Incremental mode — use watermark
        watermark = read_watermark()
        if watermark is None:
            start = today - timedelta(days=7)
            LOGGER.info("No watermark found — defaulting to last 7 days.")
        else:
            start = watermark + timedelta(days=1)
            LOGGER.info("Watermark: %s — fetching from %s", watermark, start)

        if start > today:
            LOGGER.info("Already up-to-date (watermark=%s, today=%s).", watermark, today)
            return

        frame = fetch_date_range(api_key, start, today)
        frame = normalize_api_frame(frame)
        save_to_raw(frame, f"{start.isoformat()}_to_{today.isoformat()}")
        write_watermark(today)

    LOGGER.info("Done.")


if __name__ == "__main__":
    main()
