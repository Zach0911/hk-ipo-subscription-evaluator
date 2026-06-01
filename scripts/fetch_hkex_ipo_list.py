#!/usr/bin/env python3
"""Fetch current HKEX new listing information for Main Board and GEM."""

from __future__ import annotations

import argparse
import csv
import html
import json
import re
import sys
import urllib.request
from dataclasses import dataclass, field
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


SKILL_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = SKILL_ROOT / "data" / "hkex_current_new_listings.csv"

URLS = {
    "main": "https://www2.hkexnews.hk/new-listings/new-listing-information/main-board?sc_lang=en",
    "gem": "https://www2.hkexnews.hk/new-listings/new-listing-information/gem?sc_lang=en",
}

FIELDS = [
    "board",
    "code",
    "company_name",
    "new_listing_announcements",
    "prospectuses",
    "allotment_results",
    "source_url",
    "source_date",
]


@dataclass
class Cell:
    text: list[str] = field(default_factory=list)
    links: list[str] = field(default_factory=list)

    def clean_text(self) -> str:
        return " ".join(" ".join(self.text).split())


class ListingTableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_table = False
        self.in_row = False
        self.in_cell = False
        self.current_cell: Cell | None = None
        self.current_row: list[Cell] = []
        self.rows: list[list[Cell]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        if tag == "table" and "table-mobile-list" in (attrs_dict.get("class") or ""):
            self.in_table = True
        if not self.in_table:
            return
        if tag == "tr":
            self.in_row = True
            self.current_row = []
        elif tag in {"td", "th"} and self.in_row:
            self.in_cell = True
            self.current_cell = Cell()
        elif tag == "a" and self.in_cell and self.current_cell is not None:
            href = attrs_dict.get("href")
            if href:
                self.current_cell.links.append(html.unescape(href))

    def handle_endtag(self, tag: str) -> None:
        if not self.in_table:
            return
        if tag in {"td", "th"} and self.in_cell:
            if self.current_cell is not None:
                self.current_row.append(self.current_cell)
            self.current_cell = None
            self.in_cell = False
        elif tag == "tr" and self.in_row:
            if self.current_row:
                self.rows.append(self.current_row)
            self.current_row = []
            self.in_row = False
        elif tag == "table":
            self.in_table = False

    def handle_data(self, data: str) -> None:
        if self.in_cell and self.current_cell is not None:
            text = html.unescape(data).strip()
            if text:
                self.current_cell.text.append(text)


def fetch_url(url: str, timeout: int = 30) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 hk-ipo-subscription-evaluator/1.0",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def normalize_code(code: str) -> str:
    value = re.sub(r"\D", "", code or "")
    return value.zfill(5) + ".HK" if value else ""


def links_text(cell: Cell) -> str:
    return ";".join(cell.links)


def parse_board(board: str, url: str, source_date: str | None = None) -> list[dict[str, str]]:
    page = fetch_url(url)
    if not source_date:
        match = re.search(r"Updated:\s*([0-9]{2}\s+[A-Za-z]{3}\s+[0-9]{4})", page)
        source_date = match.group(1) if match else date.today().isoformat()

    parser = ListingTableParser()
    parser.feed(page)

    rows: list[dict[str, str]] = []
    for cells in parser.rows:
        if len(cells) < 5:
            continue
        raw_code = cells[0].clean_text()
        if not re.fullmatch(r"\d{1,5}", raw_code):
            continue
        rows.append(
            {
                "board": board,
                "code": normalize_code(raw_code),
                "company_name": cells[1].clean_text(),
                "new_listing_announcements": links_text(cells[2]),
                "prospectuses": links_text(cells[3]),
                "allotment_results": links_text(cells[4]),
                "source_url": url,
                "source_date": source_date,
            }
        )
    return rows


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch HKEX current new listing information")
    parser.add_argument("--board", choices=["main", "gem", "all"], default="all")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Output CSV path")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of writing CSV")
    args = parser.parse_args()

    boards = ["main", "gem"] if args.board == "all" else [args.board]
    rows: list[dict[str, str]] = []
    for board in boards:
        rows.extend(parse_board(board, URLS[board]))

    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    else:
        write_csv(Path(args.output).expanduser(), rows)
        print(f"rows={len(rows)} output={args.output}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
