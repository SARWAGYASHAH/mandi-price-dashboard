"""Run the complete mandi analytics pipeline in dependency order."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run(*command: str) -> None:
    """Run one pipeline command from the repository root."""
    print(f"\n> {' '.join(command)}", flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> None:
    """Regenerate cleaned data, SQL outputs, reports, forecasts, and previews."""
    sqlite = shutil.which("sqlite3")
    if sqlite is None:
        raise RuntimeError(
            "sqlite3 was not found on PATH. Install the SQLite command-line "
            "shell before running the complete pipeline."
        )

    python = sys.executable

    # Optional: fetch fresh data from data.gov.in if an API key is available.
    if os.environ.get("DATA_GOV_API_KEY"):
        print("\n> DATA_GOV_API_KEY detected — fetching latest prices…", flush=True)
        run(python, "scripts/fetch_live_data.py")
    else:
        print("\n> No DATA_GOV_API_KEY set — skipping live fetch (offline mode).",
              flush=True)

    run(python, "scripts/data_cleaning.py")
    run(sqlite, "-batch", "data/mandi_prices.db", ".read sql/queries.sql")
    run(python, "scripts/anomaly_detection.py")
    run(python, "scripts/forecast_model.py")
    run(python, "scripts/automated_insights.py")
    run(python, "scripts/generate_dashboard_previews.py")
    print("\nPipeline completed successfully.", flush=True)


if __name__ == "__main__":
    main()
