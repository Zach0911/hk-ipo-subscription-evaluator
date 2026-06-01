#!/usr/bin/env python3
"""Create an empty Hong Kong IPO history CSV template."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from update_hk_ipo_history import DEFAULT_DATA, FIELDS


def main() -> int:
    parser = argparse.ArgumentParser(description="Create hk_ipo_history.csv template")
    parser.add_argument("--data", default=str(DEFAULT_DATA), help="Output CSV path")
    parser.add_argument("--force", action="store_true", help="Overwrite existing file")
    args = parser.parse_args()

    data_path = Path(args.data).expanduser()
    if data_path.exists() and not args.force:
        print(f"exists: {data_path}")
        return 0

    data_path.parent.mkdir(parents=True, exist_ok=True)
    with data_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
    print(f"created: {data_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
