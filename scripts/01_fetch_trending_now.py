# -*- coding: utf-8 -*-
"""
01_fetch_trending_now.py — 采集 Google Trends "Trending Now" 实时热词（一手数据 [D1]）

数据源：Google Trends 官方 RSS（无需鉴权，公开可复现）
    https://trends.google.com/trending/rss?geo={GEO}

产出：
    data/raw/trending_rss_{GEO}_{日期}.xml   原始快照（供第三方核验）
    data/trending_now.csv                    解析后的结构化数据
    data/trending_now_summary.json           汇总统计（供报告正文引用）

用途：证明"热词机会供给"的存在性与量级——每天每个国家有多少个热词窗口、
     每个窗口的搜索量级分布如何。
"""
import csv
import json
import re
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

# 覆盖主要英文市场 + 对照市场
GEOS = ["US", "GB", "CA", "AU", "IN", "DE", "BR", "JP"]
NS = {"ht": "https://trends.google.com/trending/rss"}
UA = {"User-Agent": "Mozilla/5.0 (research; reproducible-data-collection)"}

TRAFFIC_RE = re.compile(r"([\d,.]+)\s*([KMB]?)\+?", re.I)
MULT = {"": 1, "K": 1_000, "M": 1_000_000, "B": 1_000_000_000}


def parse_traffic(text: str) -> int | None:
    """把 '200K+' / '1M+' 这类近似搜索量解析成数字下界。"""
    if not text:
        return None
    m = TRAFFIC_RE.search(text.replace(",", ""))
    if not m:
        return None
    return int(float(m.group(1)) * MULT[m.group(2).upper()])


def fetch_geo(geo: str, today: str) -> list[dict]:
    url = f"https://trends.google.com/trending/rss?geo={geo}"
    resp = requests.get(url, headers=UA, timeout=30)
    resp.raise_for_status()
    raw_path = RAW_DIR / f"trending_rss_{geo}_{today}.xml"
    raw_path.write_bytes(resp.content)

    rows = []
    root = ET.fromstring(resp.content)
    for item in root.iter("item"):
        title = item.findtext("title", "")
        traffic_text = item.findtext("ht:approx_traffic", "", NS)
        pub = item.findtext("pubDate", "")
        news_titles = [
            (n.findtext("ht:news_item_title", "", NS) or "").strip()
            for n in item.findall("ht:news_item", NS)
        ]
        rows.append(
            {
                "geo": geo,
                "keyword": title.strip(),
                "approx_traffic_text": traffic_text,
                "approx_traffic_lower_bound": parse_traffic(traffic_text),
                "pub_date": pub,
                "news_item_count": len(news_titles),
                "first_news_title": news_titles[0] if news_titles else "",
                "snapshot_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            }
        )
    return rows


def main() -> None:
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    all_rows: list[dict] = []
    for geo in GEOS:
        try:
            rows = fetch_geo(geo, today)
            print(f"[OK] {geo}: {len(rows)} 条热词")
            all_rows.extend(rows)
        except Exception as exc:  # 单个 geo 失败不阻断整体采集
            print(f"[FAIL] {geo}: {exc}")
        time.sleep(1.5)

    if not all_rows:
        raise SystemExit("未采集到任何数据，请检查网络后重试")

    out_csv = ROOT / "data" / "trending_now.csv"
    with out_csv.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(all_rows[0].keys()))
        writer.writeheader()
        writer.writerows(all_rows)

    # 汇总统计：供报告正文直接引用
    def stats_for(rows: list[dict]) -> dict:
        vals = [r["approx_traffic_lower_bound"] for r in rows if r["approx_traffic_lower_bound"]]
        vals.sort()
        return {
            "trend_count": len(rows),
            "with_traffic_estimate": len(vals),
            "traffic_lower_bound_min": vals[0] if vals else None,
            "traffic_lower_bound_median": vals[len(vals) // 2] if vals else None,
            "traffic_lower_bound_max": vals[-1] if vals else None,
            "sum_traffic_lower_bound": sum(vals) if vals else None,
        }

    summary = {
        "snapshot_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "Google Trends Trending-Now RSS (https://trends.google.com/trending/rss)",
        "geos": {g: stats_for([r for r in all_rows if r["geo"] == g]) for g in GEOS},
        "total": stats_for(all_rows),
    }
    out_json = ROOT / "data" / "trending_now_summary.json"
    out_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n写出文件：\n  {out_csv}\n  {out_json}\n  原始快照 {len(GEOS)} 份 -> {RAW_DIR}")
    print(json.dumps(summary["total"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
