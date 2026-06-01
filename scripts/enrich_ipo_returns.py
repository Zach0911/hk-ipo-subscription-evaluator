#!/usr/bin/env python3
"""Enrich hk_ipo_history.csv with first-day, day-5, and day-20 returns."""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import timedelta
from pathlib import Path

from match_peer_ipos import parse_date, parse_float
from update_hk_ipo_history import DEFAULT_DATA, FIELDS

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from finance_all_in_one_adapter import get_hk_kline, normalize_hk_code  # noqa: E402


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def pct_return(close: float | None, issue_price: float | None) -> str:
    if close is None or issue_price is None or issue_price <= 0:
        return ""
    return f"{((close - issue_price) / issue_price * 100):.2f}"


def close_at(records: list[dict[str, object]], index: int) -> float | None:
    if len(records) <= index:
        return None
    return parse_float(str(records[index].get("close", "")))


def needs_enrich(row: dict[str, str], force: bool) -> bool:
    if force:
        return True
    return not (row.get("first_day_return_pct") and row.get("day5_return_pct") and row.get("day20_return_pct"))


def enrich_row(row: dict[str, str], force: bool = False, limit: int = 35) -> tuple[dict[str, str], str]:
    if not needs_enrich(row, force):
        return row, "skipped"

    code = normalize_hk_code(row.get("code", ""))
    listing_date = parse_date(row.get("listing_date", ""))
    issue_price = parse_float(row.get("issue_price_hkd", ""))
    if not code or not listing_date or not issue_price:
        return row, "missing code/listing_date/issue_price_hkd"

    start_date = listing_date.isoformat()
    end_date = (listing_date + timedelta(days=60)).isoformat()
    payload = get_hk_kline(code, start_date=start_date, end_date=end_date, limit=limit)
    records = payload.get("data", [])
    if not records:
        return row, "no kline data"

    first = close_at(records, 0)
    day5 = close_at(records, 4)
    day20 = close_at(records, 19)
    row["code"] = code + ".HK"
    row["first_day_return_pct"] = pct_return(first, issue_price)
    row["day5_return_pct"] = pct_return(day5, issue_price)
    row["day20_return_pct"] = pct_return(day20, issue_price)
    if row["first_day_return_pct"]:
        row["is_broken"] = "yes" if parse_float(row["first_day_return_pct"]) < 0 else "no"
    if not row.get("source_date"):
        row["source_date"] = start_date
    return row, f"enriched from {payload.get('source', 'finance-all-in-one')}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Enrich HK IPO history rows with post-listing returns")
    parser.add_argument("--data", default=str(DEFAULT_DATA), help="Path to hk_ipo_history.csv")
    parser.add_argument("--output", help="Optional output CSV; defaults to overwrite --data")
    parser.add_argument("--force", action="store_true", help="Recompute existing return fields")
    parser.add_argument("--limit", type=int, default=35, help="K-line rows to request")
    args = parser.parse_args()

    data_path = Path(args.data).expanduser()
    output_path = Path(args.output).expanduser() if args.output else data_path
    rows = read_rows(data_path)

    statuses: dict[str, int] = {}
    updated: list[dict[str, str]] = []
    for row in rows:
        normalized = {field: (row.get(field, "") or "").strip() for field in FIELDS}
        enriched, status = enrich_row(normalized, force=args.force, limit=args.limit)
        statuses[status] = statuses.get(status, 0) + 1
        updated.append(enriched)

    write_rows(output_path, updated)
    print(f"rows={len(rows)} output={output_path}")
    for status, count in sorted(statuses.items()):
        print(f"{status}={count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
