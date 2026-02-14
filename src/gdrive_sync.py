"""
gdrive_sync.py — Auto-download the Oracle's Elixir CSV from a shared
Google Drive folder so the model always has fresh data.

Uses `gdown` (pip install gdown) which works with public Google Drive links.
"""

import os
import time
import shutil
import logging

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
GDRIVE_FOLDER_ID = "1gLSw0RLjBbtaNy0dgnGQDAZOHIgCe-HH"
SYNC_INTERVAL_HOURS = 24

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_DIR = os.path.join(ROOT, "Data", "csv")
CSV_FILENAME = "2026_LoL_esports_match_data_from_OraclesElixir.csv"
CSV_PATH = os.path.join(CSV_DIR, CSV_FILENAME)


def _file_age_hours() -> float:
    """Return how many hours since the CSV was last modified (or inf)."""
    try:
        mtime = os.path.getmtime(CSV_PATH)
        return (time.time() - mtime) / 3600
    except OSError:
        return float("inf")


def _backup_existing() -> None:
    """Create a .bak copy of the current CSV before overwriting."""
    if os.path.exists(CSV_PATH):
        bak = CSV_PATH + ".bak"
        shutil.copy2(CSV_PATH, bak)
        log.info("Backed up existing CSV to %s", bak)


def download_from_gdrive(force: bool = False) -> bool:
    """
    Download the CSV from the shared Google Drive folder.

    Parameters
    ----------
    force : bool
        If True, download regardless of file age.

    Returns
    -------
    bool
        True if a new file was downloaded, False if skipped or failed.
    """
    try:
        import gdown
    except ImportError:
        log.warning(
            "gdown is not installed — run `pip install gdown` to enable "
            "automatic CSV syncing from Google Drive."
        )
        return False

    age = _file_age_hours()
    if not force and age < SYNC_INTERVAL_HOURS:
        log.debug(
            "CSV is %.1f hours old (threshold %d h) — skipping sync.",
            age,
            SYNC_INTERVAL_HOURS,
        )
        return False

    log.info(
        "CSV is %.1f hours old — downloading fresh copy from Google Drive…",
        age,
    )

    _backup_existing()
    os.makedirs(CSV_DIR, exist_ok=True)

    # gdown.download_folder downloads every file in the folder.
    # We use a temp directory, then move only the CSV we care about.
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        try:
            gdown.download_folder(
                id=GDRIVE_FOLDER_ID,
                output=tmp,
                quiet=False,
                remaining_ok=True,
            )
        except Exception as exc:
            log.error("gdown folder download failed: %s", exc)
            return False

        # Find the CSV in the downloaded files
        downloaded = None
        for root_dir, _dirs, files in os.walk(tmp):
            for f in files:
                if f.endswith(".csv"):
                    downloaded = os.path.join(root_dir, f)
                    break
            if downloaded:
                break

        if downloaded is None:
            log.error("No CSV found in downloaded folder contents.")
            return False

        shutil.copy2(downloaded, CSV_PATH)
        log.info("✅ CSV synced successfully → %s", CSV_PATH)
        return True


def sync_if_stale(force: bool = False) -> bool:
    """
    Check if the CSV is stale and download a fresh copy if needed.

    This is the main entry point — call it before loading data.
    It's fast when the file is fresh (just an mtime check).
    """
    return download_from_gdrive(force=force)


# ---------------------------------------------------------------------------
# CLI entry point (for manual / scheduled runs)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    import argparse

    parser = argparse.ArgumentParser(description="Sync Oracle's Elixir CSV from Google Drive")
    parser.add_argument("--force", action="store_true", help="Force download even if file is fresh")
    args = parser.parse_args()

    success = sync_if_stale(force=args.force)
    if success:
        print("Download complete!")
    else:
        age = _file_age_hours()
        if age < SYNC_INTERVAL_HOURS:
            print(f"CSV is only {age:.1f}h old — no download needed. Use --force to override.")
        else:
            print("Download failed — check the logs above.")
