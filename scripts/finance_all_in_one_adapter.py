#!/usr/bin/env python3
"""Adapter for calling the finance-all-in-one skill from this skill."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SEARCH_PATHS = [
    Path.home() / ".codex" / "skills" / "finance-all-in-one",
    Path.home() / ".agents" / "skills" / "finance-all-in-one",
    Path.cwd() / "work" / "finance-all-in-one",
]


def find_finance_skill() -> Path:
    for path in SEARCH_PATHS:
        if (path / "cli.py").exists():
            return path
    raise FileNotFoundError(
        "finance-all-in-one skill not found. Expected one of: "
        + ", ".join(str(path) for path in SEARCH_PATHS)
    )


def normalize_hk_code(code: str) -> str:
    value = (code or "").strip().upper()
    value = value.replace("HK.", "").replace(".HK", "")
    if value.isdigit():
        return value.zfill(5)
    return value


def run_cli(args: list[str], timeout: int = 60) -> dict[str, Any]:
    root = find_finance_skill()
    cmd = [sys.executable, str(root / "cli.py"), *args]
    completed = subprocess.run(
        cmd,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "finance-all-in-one CLI failed: "
            + (completed.stderr.strip() or completed.stdout.strip())
        )
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"finance-all-in-one returned non-JSON output: {completed.stdout[:500]}") from exc


def normalize_record_date(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (int, float)):
        timestamp = float(value)
        if timestamp > 10_000_000_000:
            timestamp /= 1000
        return datetime.fromtimestamp(timestamp, tz=timezone.utc).date().isoformat()
    text = str(value).strip()
    if not text:
        return ""
    if "T" in text:
        return text.split("T", 1)[0]
    if " " in text:
        return text.split(" ", 1)[0]
    return text[:10]


def get_hk_kline(
    code: str,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 30,
) -> dict[str, Any]:
    hk_code = normalize_hk_code(code)
    args = [
        "--data-type",
        "stock_kline",
        "--symbol",
        hk_code,
        "--market",
        "hk",
        "--period",
        "daily",
        "--limit",
        str(limit),
        "--output",
        "json",
    ]
    if start_date:
        args.extend(["--start-date", start_date])
    if end_date:
        args.extend(["--end-date", end_date])
    payload = run_cli(args)
    for row in payload.get("data", []):
        row["date"] = normalize_record_date(row.get("date"))
    return payload


def get_hk_quote(code: str) -> dict[str, Any]:
    hk_code = normalize_hk_code(code)
    return run_cli(
        [
            "--data-type",
            "stock_quote",
            "--symbol",
            hk_code,
            "--market",
            "hk",
            "--output",
            "json",
        ]
    )


def get_hk_valuation(code: str) -> dict[str, Any]:
    hk_code = normalize_hk_code(code)
    root = find_finance_skill()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from data_types.hk import get_hk_valuation as fetch_valuation  # type: ignore

    try:
        return fetch_valuation(hk_code).to_dict()
    except Exception as exc:
        payload = get_hk_quote(hk_code)
        warnings = payload.setdefault("warnings", [])
        warnings.append(f"hk_valuation failed; fell back to hk quote valuation fields: {exc}")
        payload["data_type"] = "hk_valuation_fallback_quote"
        return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Call finance-all-in-one for HK market data")
    parser.add_argument("kind", choices=["kline", "quote", "valuation"])
    parser.add_argument("--code", required=True, help="HK code, e.g. 00700 or 00700.HK")
    parser.add_argument("--start-date")
    parser.add_argument("--end-date")
    parser.add_argument("--limit", type=int, default=30)
    args = parser.parse_args()

    if args.kind == "kline":
        payload = get_hk_kline(args.code, args.start_date, args.end_date, args.limit)
    elif args.kind == "quote":
        payload = get_hk_quote(args.code)
    else:
        payload = get_hk_valuation(args.code)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
