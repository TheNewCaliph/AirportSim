"""Download the 2025 BTS on-time performance files into data/raw/bts/.

Run from the repository root:

    python scripts/download_bts.py
    python scripts/download_bts.py --months 1-3

The logic lives in aom/ml/bts_download.py so it can be tested.
"""

from aom.ml.bts_download import main

if __name__ == "__main__":
    raise SystemExit(main())
