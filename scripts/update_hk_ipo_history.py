#!/usr/bin/env python3
"""Validate and merge Hong Kong IPO history rows from an external CSV file."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA = SKILL_ROOT / "data" / "hk_ipo_history.csv"

FIELDS = [
    "company_name",
    "code",
    "listing_date",
    "industry",
    "sector",
    "business_model",
    "listing_type",
    "issue_price_hkd",
    "market_cap_hkd_m",
    "fundraising_hkd_m",
    "profit_status",
    "growth_stage",
    "valuation_type",
    "valuation_multiple",
    "sponsor",
    "cornerstone_investors",
    "public_subscription_multiple",
    "one_lot_success_rate",
    "first_day_return_pct",
    "day5_return_pct",
    "day20_return_pct",
    "is_broken",
    "notes",
    "source_url",
    "source_date",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def normalize_row(row: dict[str, str]) -> dict[str, str]:
    return {field: (row.get(field, "") or "").strip() for field in FIELDS}


def key(row: dict[str, str]) -> tuple[str, str]:
    return (row.get("code", "").strip().upper(), row.get("listing_date", "").strip())


def validate(row: dict[str, str], row_num: int) -> list[str]:
    errors: list[str] = []
    if not row.get("company_name"):
        errors.append(f"row {row_num}: missing company_name")
    if not row.get("code"):
        errors.append(f"row {row_num}: missing code")
    if not row.get("listing_date"):
        errors.append(f"row {row_num}: missing listing_date")
    return errors


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Merge external rows into hk_ipo_history.csv")
    parser.add_argument("--input", required=True, help="External CSV using the documented schema")
    parser.add_argument("--data", default=str(DEFAULT_DATA), help="Target hk_ipo_history.csv")
    parser.add_argument("--dry-run", action="store_true", help="Validate and report without writing")
    args = parser.parse_args()

    input_path = Path(args.input).expanduser()
    data_path = Path(args.data).expanduser()
    incoming = [normalize_row(row) for row in read_csv(input_path)]

    errors: list[str] = []
    for idx, row in enumerate(incoming, start=2):
        errors.extend(validate(row, idx))
    if errors:
        for error in errors:
            print(error)
        return 2

    existing = [normalize_row(row) for row in read_csv(data_path)]
    merged: dict[tuple[str, str], dict[str, str]] = {}
    for row in existing:
        if key(row) != ("", ""):
            merged[key(row)] = row
    before = len(merged)

    for row in incoming:
        merged[key(row)] = row

    rows = sorted(merged.values(), key=lambda item: (item.get("listing_date", ""), item.get("code", "")))
    if not args.dry_run:
        write_csv(data_path, rows)

    print(f"existing={len(existing)} incoming={len(incoming)} added_or_updated={len(merged)-before} total={len(rows)}")
    if args.dry_run:
        print("dry_run=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
