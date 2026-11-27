"""Download the BTS Reporting Carrier On-Time Performance files for M8.

The US Bureau of Transportation Statistics publishes one zip per month (one
CSV inside, roughly 25-35 MB zipped) at a fixed address:

    https://transtats.bts.gov/PREZIP/On_Time_Reporting_Carrier_On_Time_Performance_1987_present_<YEAR>_<MONTH>.zip

with the month not zero-padded (``2025_1`` to ``2025_12``). Files are saved to
``data/raw/bts/``, which is git-ignored: GitHub rejects files over 100 MB, and
anyone can re-create the folder by running this script.

Usage::

    python scripts/download_bts.py                 # all of 2025
    python scripts/download_bts.py --months 1-3    # January to March only
    python scripts/download_bts.py --force         # re-download existing files

A file that is already present and is a valid zip is skipped, so the script
can be stopped and re-run safely. Each download is written to a ``.part``
file first and only renamed once it is complete and checked.
"""

from __future__ import annotations

import argparse
import shutil
import ssl
import sys
import time
import urllib.error
import urllib.request
import zipfile
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import BinaryIO

BASE_URL = "https://transtats.bts.gov/PREZIP"
FILE_STEM = "On_Time_Reporting_Carrier_On_Time_Performance_1987_present"
DEFAULT_YEAR = 2025
DEFAULT_DIR = Path("data/raw/bts")
USER_AGENT = "aom-course-project/0.1 (BTS on-time data download)"

Opener = Callable[[str, float], BinaryIO]


def file_name(year: int, month: int) -> str:
    """Name of the monthly zip, e.g. ``..._2025_1.zip``."""
    if not 1 <= month <= 12:
        raise ValueError(f"month must be 1-12, got {month}")
    return f"{FILE_STEM}_{year}_{month}.zip"


def month_url(year: int, month: int) -> str:
    """Download address of one month's zip."""
    return f"{BASE_URL}/{file_name(year, month)}"


def parse_months(text: str) -> list[int]:
    """Turn ``"1-3,7,10-12"`` into ``[1, 2, 3, 7, 10, 11, 12]``."""
    months: list[int] = []
    for part in text.split(","):
        part = part.strip()
        if "-" in part:
            lo, hi = (int(x) for x in part.split("-", 1))
            months.extend(range(lo, hi + 1))
        elif part:
            months.append(int(part))
    for m in months:
        if not 1 <= m <= 12:
            raise ValueError(f"month must be 1-12, got {m}")
    return sorted(set(months))


def _default_opener(url: str, timeout: float) -> BinaryIO:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    response: BinaryIO = urllib.request.urlopen(request, timeout=timeout)
    return response


def is_valid_zip(path: Path) -> bool:
    """True if ``path`` is a readable zip that contains at least one CSV."""
    if not path.is_file() or not zipfile.is_zipfile(path):
        return False
    try:
        with zipfile.ZipFile(path) as archive:
            return any(n.lower().endswith(".csv") for n in archive.namelist())
    except zipfile.BadZipFile:
        return False


def download_month(
    year: int,
    month: int,
    out_dir: Path = DEFAULT_DIR,
    *,
    force: bool = False,
    retries: int = 3,
    timeout: float = 120.0,
    opener: Opener = _default_opener,
    log: Callable[[str], None] = print,
) -> Path:
    """Download one month's zip into ``out_dir`` and return its path.

    Skips a valid existing file unless ``force``. Retries with a growing pause
    (2 s, 4 s, ...) on network errors. Raises RuntimeError if every attempt
    fails or the file is not a valid zip.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / file_name(year, month)
    if target.exists() and not force and is_valid_zip(target):
        log(f"skip   {target.name} (already downloaded)")
        return target

    url = month_url(year, month)
    partial = target.with_name(target.name + ".part")
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            log(f"fetch  {target.name} (attempt {attempt}/{retries})")
            with opener(url, timeout) as response, partial.open("wb") as handle:
                shutil.copyfileobj(response, handle, length=1 << 20)
            if not is_valid_zip(partial):
                raise RuntimeError(f"{url} did not return a valid zip with a CSV inside")
            partial.replace(target)
            size_mb = target.stat().st_size / 1_000_000
            log(f"saved  {target.name} ({size_mb:.1f} MB)")
            return target
        except ssl.SSLError as error:
            partial.unlink(missing_ok=True)
            raise RuntimeError(
                f"TLS error fetching {url}: {error}. Your Python may lack the CA "
                "certificates; on macOS run 'Install Certificates.command' from the "
                "Python folder, elsewhere 'pip install --upgrade certifi'."
            ) from error
        except (urllib.error.URLError, TimeoutError, OSError, RuntimeError) as error:
            last_error = error
            partial.unlink(missing_ok=True)
            if attempt < retries:
                pause = 2.0**attempt
                log(f"retry  {target.name} in {pause:.0f} s: {error}")
                time.sleep(pause)
    raise RuntimeError(f"giving up on {url}: {last_error}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Download BTS on-time performance zips.")
    parser.add_argument("--year", type=int, default=DEFAULT_YEAR)
    parser.add_argument("--months", default="1-12", help="e.g. 1-12 or 1-3,7")
    parser.add_argument("--out", type=Path, default=DEFAULT_DIR)
    parser.add_argument("--force", action="store_true", help="re-download existing files")
    parser.add_argument("--retries", type=int, default=3)
    args = parser.parse_args(argv)

    failed: list[int] = []
    for month in parse_months(args.months):
        try:
            download_month(args.year, month, args.out, force=args.force, retries=args.retries)
        except RuntimeError as error:
            print(f"FAILED month {month}: {error}", file=sys.stderr)
            failed.append(month)
    if failed:
        print(f"{len(failed)} month(s) failed: {failed}. Re-run to retry them.", file=sys.stderr)
        return 1
    print(f"All files are in {args.out}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
