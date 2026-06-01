#!/usr/bin/env python3
"""Match recent Hong Kong IPO peers and summarize post-listing performance."""

from __future__ import annotations

import argparse
import csv
import json
import statistics
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable


SKILL_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA = SKILL_ROOT / "data" / "hk_ipo_history.csv"
SPECIAL_LISTING_TYPES = {"spac", "introduction", "secondary", "de-spac", "dual-primary"}


@dataclass
class PeerRow:
    raw: dict[str, str]
    score: float
    reasons: list[str]


def parse_date(value: str) -> date | None:
    value = (value or "").strip()
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass
    return None


def parse_float(value: str) -> float | None:
    value = (value or "").strip().replace(",", "").replace("%", "")
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def norm(value: str) -> str:
    return (value or "").strip().lower()


def load_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"History data not found: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def score_row(row: dict[str, str], args: argparse.Namespace) -> PeerRow:
    score = 0.0
    reasons: list[str] = []

    industry = norm(row.get("industry", ""))
    sector = norm(row.get("sector", ""))
    business_model = norm(row.get("business_model", ""))
    profit_status = norm(row.get("profit_status", ""))
    growth_stage = norm(row.get("growth_stage", ""))
    valuation_type = norm(row.get("valuation_type", ""))
    sponsor = norm(row.get("sponsor", ""))

    if args.industry and norm(args.industry) == industry:
        score += 30
        reasons.append("same industry")
    elif args.sector and norm(args.sector) == sector:
        score += 20
        reasons.append("same sector")

    if args.business_model and norm(args.business_model) == business_model:
        score += 10
        reasons.append("same business model")

    market_cap = parse_float(row.get("market_cap_hkd_m", ""))
    if args.market_cap_hkd_m and market_cap and market_cap > 0:
        ratio = market_cap / args.market_cap_hkd_m
        if 0.5 <= ratio <= 2.0:
            score += 15
            reasons.append("similar market cap")
        elif 0.25 <= ratio < 0.5 or 2.0 < ratio <= 4.0:
            score += 7
            reasons.append("broadly comparable market cap")

    fundraising = parse_float(row.get("fundraising_hkd_m", ""))
    if args.fundraising_hkd_m and fundraising and fundraising > 0:
        ratio = fundraising / args.fundraising_hkd_m
        if 0.5 <= ratio <= 2.0:
            score += 6
            reasons.append("similar fundraising size")

    if args.profit_status and norm(args.profit_status) == profit_status:
        score += 15
        reasons.append("same profit status")

    if args.growth_stage and norm(args.growth_stage) == growth_stage:
        score += 6
        reasons.append("same growth stage")

    if args.valuation_type and norm(args.valuation_type) == valuation_type:
        score += 8
        reasons.append("same valuation type")

    if args.sponsor and norm(args.sponsor) and norm(args.sponsor) in sponsor:
        score += 5
        reasons.append("same or related sponsor")

    return PeerRow(raw=row, score=score, reasons=reasons)


def filter_recent_rows(
    rows: Iterable[dict[str, str]],
    as_of: date,
    days: int,
    include_special: bool,
) -> list[dict[str, str]]:
    start = as_of - timedelta(days=days)
    filtered: list[dict[str, str]] = []
    for row in rows:
        listing_date = parse_date(row.get("listing_date", ""))
        if not listing_date or not (start <= listing_date <= as_of):
            continue
        listing_type = norm(row.get("listing_type", ""))
        if not include_special and listing_type in SPECIAL_LISTING_TYPES:
            continue
        filtered.append(row)
    return filtered


def median(values: list[float]) -> float | None:
    return statistics.median(values) if values else None


def pct(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.1f}%"


def num(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.1f}"


def collect_metric(rows: list[PeerRow], field: str) -> list[float]:
    values: list[float] = []
    for item in rows:
        parsed = parse_float(item.raw.get(field, ""))
        if parsed is not None:
            values.append(parsed)
    return values


def summarize(rows: list[PeerRow]) -> dict[str, object]:
    first_day = collect_metric(rows, "first_day_return_pct")
    day5 = collect_metric(rows, "day5_return_pct")
    day20 = collect_metric(rows, "day20_return_pct")
    one_lot = collect_metric(rows, "one_lot_success_rate")
    subscriptions = collect_metric(rows, "public_subscription_multiple")

    broken = 0
    broken_known = 0
    for item in rows:
        value = norm(item.raw.get("is_broken", ""))
        if value in {"yes", "true", "1", "y", "破发"}:
            broken += 1
            broken_known += 1
        elif value in {"no", "false", "0", "n", "未破发"}:
            broken_known += 1
        else:
            ret = parse_float(item.raw.get("first_day_return_pct", ""))
            if ret is not None:
                broken_known += 1
                if ret < 0:
                    broken += 1

    positive_count = len([value for value in first_day if value > 0])

    return {
        "sample_count": len(rows),
        "first_day_positive_rate": positive_count / len(first_day) * 100 if first_day else None,
        "first_day_median_return": median(first_day),
        "break_rate": broken / broken_known * 100 if broken_known else None,
        "day5_median_return": median(day5),
        "day20_median_return": median(day20),
        "one_lot_success_rate_median": median(one_lot),
        "public_subscription_multiple_median": median(subscriptions),
    }


def quality_label(count: int, average_score: float) -> str:
    if count >= 8 and average_score >= 65:
        return "高"
    if count >= 4 and average_score >= 45:
        return "中"
    return "低"


def select_peers(rows: list[dict[str, str]], args: argparse.Namespace) -> list[PeerRow]:
    scored = [score_row(row, args) for row in rows]
    scored.sort(key=lambda item: (item.score, row_date_key(item.raw)), reverse=True)
    return [item for item in scored if item.score >= args.min_score][: args.limit]


def row_date_key(row: dict[str, str]) -> str:
    parsed = parse_date(row.get("listing_date", ""))
    return parsed.isoformat() if parsed else ""


def to_json(peers: list[PeerRow], stats: dict[str, object], quality: str) -> str:
    return json.dumps(
        {
            "match_quality": quality,
            "stats": stats,
            "peers": [
                {"score": peer.score, "reasons": peer.reasons, **peer.raw}
                for peer in peers
            ],
        },
        ensure_ascii=False,
        indent=2,
    )


def to_markdown(peers: list[PeerRow], stats: dict[str, object], quality: str, args: argparse.Namespace) -> str:
    lines = [
        "# 近 1 年同类港股 IPO 样本匹配",
        "",
        f"- 样本库：`{args.data}`",
        f"- 截止日期：{args.as_of}",
        f"- 时间窗口：过去 {args.days} 天",
        f"- 匹配质量：{quality}",
        f"- 样本数量：{stats['sample_count']}",
        "",
        "## 统计摘要",
        "",
        "| 指标 | 数值 |",
        "|---|---:|",
        f"| 首日正收益率 | {pct(stats['first_day_positive_rate'])} |",
        f"| 首日收益中位数 | {pct(stats['first_day_median_return'])} |",
        f"| 首日破发率 | {pct(stats['break_rate'])} |",
        f"| 首 5 日收益中位数 | {pct(stats['day5_median_return'])} |",
        f"| 首 20 日收益中位数 | {pct(stats['day20_median_return'])} |",
        f"| 一手中签率中位数 | {pct(stats['one_lot_success_rate_median'])} |",
        f"| 公开认购倍数中位数 | {num(stats['public_subscription_multiple_median'])} |",
        "",
        "## 匹配样本",
        "",
        "| 分数 | 公司 | 代码 | 上市日期 | 行业 | 板块 | 市值(HKD m) | 首日 | 5日 | 20日 | 匹配原因 |",
        "|---:|---|---|---|---|---|---:|---:|---:|---:|---|",
    ]
    if not peers:
        lines.append("| N/A | 无匹配样本 |  |  |  |  |  |  |  |  | 请补充历史样本库或放宽筛选条件 |")
    for peer in peers:
        row = peer.raw
        lines.append(
            "| {score:.0f} | {company} | {code} | {date} | {industry} | {sector} | {cap} | {fd} | {d5} | {d20} | {reasons} |".format(
                score=peer.score,
                company=row.get("company_name", ""),
                code=row.get("code", ""),
                date=row.get("listing_date", ""),
                industry=row.get("industry", ""),
                sector=row.get("sector", ""),
                cap=row.get("market_cap_hkd_m", ""),
                fd=row.get("first_day_return_pct", ""),
                d5=row.get("day5_return_pct", ""),
                d20=row.get("day20_return_pct", ""),
                reasons=", ".join(peer.reasons),
            )
        )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Match recent Hong Kong IPO peer samples.")
    parser.add_argument("--data", default=str(DEFAULT_DATA), help="Path to hk_ipo_history.csv")
    parser.add_argument("--as-of", default=date.today().isoformat(), help="As-of date, YYYY-MM-DD")
    parser.add_argument("--days", type=int, default=365, help="Lookback window in days")
    parser.add_argument("--include-special", action="store_true", help="Include SPAC/introduction/secondary listings")
    parser.add_argument("--industry", help="Current IPO industry")
    parser.add_argument("--sector", help="Current IPO sector")
    parser.add_argument("--business-model", help="Current IPO business model")
    parser.add_argument("--market-cap-hkd-m", type=float, help="Current IPO market cap in HKD million")
    parser.add_argument("--fundraising-hkd-m", type=float, help="Current IPO fundraising amount in HKD million")
    parser.add_argument("--profit-status", help="盈利/亏损/未商业化 or equivalent")
    parser.add_argument("--growth-stage", help="Current IPO growth stage")
    parser.add_argument("--valuation-type", help="PE/PS/EV/Sales/etc.")
    parser.add_argument("--sponsor", help="Sponsor name")
    parser.add_argument("--min-score", type=float, default=35, help="Minimum peer match score")
    parser.add_argument("--limit", type=int, default=12, help="Maximum peers to output")
    parser.add_argument("--json", action="store_true", help="Output JSON instead of Markdown")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    args.data = str(Path(args.data).expanduser())
    as_of = parse_date(args.as_of)
    if not as_of:
        parser.error("--as-of must be a valid date")

    rows = load_rows(Path(args.data))
    recent_rows = filter_recent_rows(rows, as_of, args.days, args.include_special)
    peers = select_peers(recent_rows, args)
    stats = summarize(peers)
    average_score = sum(peer.score for peer in peers) / len(peers) if peers else 0
    quality = quality_label(len(peers), average_score)

    if args.json:
        print(to_json(peers, stats, quality))
    else:
        print(to_markdown(peers, stats, quality, args))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
