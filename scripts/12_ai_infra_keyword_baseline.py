# -*- coding: utf-8 -*-
"""
12_ai_infra_keyword_baseline.py — AI/算力基础设施热词供给基线（可复现）

回答的问题：Trending-Now 热词流里，能被归入 "ai-infra" 垂直线（并触发铭信赞助位）
的热词到底有多少？——先测后建，为导流预期提供客观依据。

数据源（与流水线同源，任何第三方可重跑核验）：
  1. data/raw/trending_rss_{GEO}_{日期}.xml   历史归档快照
  2. --live 时追加一次实时抓取（默认开启；网络失败自动降级为仅历史数据并如实标注）

方法：
  - 词表 = pipeline.opportunity_filter.AI_INFRA_TERMS（单一事实来源，与线上过滤器完全一致）
  - 匹配口径 = pipeline.opportunity_filter._ai_infra_hits（规范化短语子串匹配）
  - 跨 geo 去重后，按"快照日"统计命中数；用 Wilson–Hilferty 近似给出
    Poisson 计数的 95% 置信区间，换算为"每周可产出 ai-infra 简报篇数"区间。
    （区间表达而非点估计——按规律办事，不作绝对断言。）

产出：
  data/ai_infra_baseline.json   完整统计 + 方法学说明 + 命中样本

运行：python scripts/12_ai_infra_keyword_baseline.py [--no-live]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline.fetch_trends import Trend, fetch_from_files, fetch_live  # noqa: E402
from pipeline.opportunity_filter import (  # noqa: E402
    AI_INFRA_TERMS,
    _ai_infra_hits,
    _norm_text,
)

RAW_DIR = ROOT / "data" / "raw"
OUT_JSON = ROOT / "data" / "ai_infra_baseline.json"

SNAPSHOT_DATE_RE = re.compile(r"trending_rss_[A-Z]{2}_(\d{8})\.xml")


def poisson_ci_95(k: int) -> tuple[float, float]:
    """Poisson 计数 k 的 95% 置信区间（Wilson–Hilferty 近似，纯标准库实现）。

    参考：Johnson, Kotz & Kemp, "Univariate Discrete Distributions"；
    k=0 时下界取 0、上界取 3.69（-ln(0.025)，精确值）。
    """
    z = 1.959964  # 双侧 95% 分位
    if k == 0:
        return 0.0, 3.69
    lower = k * (1.0 - 1.0 / (9.0 * k) - z / (3.0 * (k**0.5))) ** 3
    upper = (k + 1) * (1.0 - 1.0 / (9.0 * (k + 1)) + z / (3.0 * ((k + 1) ** 0.5))) ** 3
    return max(lower, 0.0), upper


def dedup_across_geos(trends: list[Trend]) -> list[Trend]:
    """与流水线一致：同一关键词跨国重复时保留流量最高的一条。"""
    best: dict[str, Trend] = {}
    for t in trends:
        k = _norm_text(t.keyword)
        if k not in best or (t.traffic_lower_bound or 0) > (best[k].traffic_lower_bound or 0):
            best[k] = t
    return list(best.values())


def analyze_snapshot_day(label: str, trends: list[Trend]) -> dict:
    deduped = dedup_across_geos(trends)
    hits = []
    for t in deduped:
        terms = _ai_infra_hits(t)
        if terms:
            hits.append(
                {
                    "keyword": t.keyword,
                    "geo": t.geo,
                    "traffic_lower_bound": t.traffic_lower_bound,
                    "matched_terms": terms,
                    "news_titles": [n.title for n in t.news][:3],
                }
            )
    return {
        "snapshot_day": label,
        "trends_raw": len(trends),
        "trends_unique_keywords": len(deduped),
        "ai_infra_hits": len(hits),
        "hit_rate": round(len(hits) / len(deduped), 4) if deduped else None,
        "hits": hits,
    }


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="AI-infra 热词供给基线分析")
    ap.add_argument("--no-live", action="store_true", help="只用历史归档，不做实时抓取")
    args = ap.parse_args()

    # 1. 历史归档：按快照日期分组
    by_day: dict[str, list[Path]] = {}
    for p in sorted(RAW_DIR.glob("trending_rss_*.xml")):
        m = SNAPSHOT_DATE_RE.match(p.name)
        if m:
            by_day.setdefault(m.group(1), []).append(p)

    days: list[dict] = []
    for day, paths in sorted(by_day.items()):
        trends = fetch_from_files(paths)
        days.append(analyze_snapshot_day(f"archive-{day}", trends))
        print(f"[archive] {day}: {days[-1]['ai_infra_hits']} ai-infra 命中 / "
              f"{days[-1]['trends_unique_keywords']} 去重热词（{len(paths)} 国）")

    # 2. 实时抓取（可选；失败不阻断，如实标注）
    live_status = "skipped (--no-live)"
    if not args.no_live:
        today = datetime.now(timezone.utc).strftime("%Y%m%d")
        if f"archive-{today}" in {d["snapshot_day"].replace("live-", "archive-") for d in days}:
            live_status = f"skipped (archive already covers {today})"
        else:
            try:
                trends = fetch_live(raw_dir=RAW_DIR)
                if trends:
                    days.append(analyze_snapshot_day(f"live-{today}", trends))
                    live_status = f"ok ({len(trends)} trends)"
                    print(f"[live] {today}: {days[-1]['ai_infra_hits']} ai-infra 命中 / "
                          f"{days[-1]['trends_unique_keywords']} 去重热词")
                else:
                    live_status = "failed (0 trends fetched)"
            except Exception as exc:
                live_status = f"failed ({exc})"
                print(f"[live] 抓取失败，仅用历史归档：{exc}")

    if not days:
        print("FATAL: 无任何快照数据（data/raw 为空且实时抓取失败）")
        return 1

    # 3. 汇总 + 每周供给区间（Poisson 95% CI）
    n_days = len(days)
    total_hits = sum(d["ai_infra_hits"] for d in days)
    total_unique = sum(d["trends_unique_keywords"] for d in days)
    lo, hi = poisson_ci_95(total_hits)
    weekly_lo = lo / n_days * 7
    weekly_hi = hi / n_days * 7
    weekly_point = total_hits / n_days * 7

    term_counter: Counter[str] = Counter()
    for d in days:
        for h in d["hits"]:
            term_counter.update(h["matched_terms"])

    result = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "methodology": {
            "term_list_source": "pipeline.opportunity_filter.AI_INFRA_TERMS "
                                f"({len(AI_INFRA_TERMS)} terms, single source of truth with the live filter)",
            "matching": "normalized phrase substring match over keyword + news titles "
                        "(identical to pipeline._ai_infra_hits)",
            "dedup": "cross-geo dedup keeps highest-traffic copy (identical to pipeline)",
            "interval": "Poisson 95% CI via Wilson–Hilferty approximation, scaled to per-week",
            "caveat": "each snapshot-day is one point-in-time RSS sample (~25 trends/geo), "
                      "NOT the full day's trend flow; true daily supply is likely higher, "
                      "so this baseline is a conservative lower-bound estimate",
        },
        "data": {
            "snapshot_days": n_days,
            "live_fetch": live_status,
            "total_unique_keywords": total_unique,
            "total_ai_infra_hits": total_hits,
            "overall_hit_rate": round(total_hits / total_unique, 4) if total_unique else None,
            "top_matched_terms": term_counter.most_common(15),
        },
        "weekly_supply_estimate": {
            "point": round(weekly_point, 1),
            "ci95_low": round(weekly_lo, 1),
            "ci95_high": round(weekly_hi, 1),
            "unit": "ai-infra briefings per week (lower-bound sampling, see caveat)",
        },
        "per_day": days,
    }

    OUT_JSON.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n写出 {OUT_JSON}")
    print(json.dumps({k: result[k] for k in ("data", "weekly_supply_estimate")},
                     ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
