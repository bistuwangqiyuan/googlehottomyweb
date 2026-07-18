# -*- coding: utf-8 -*-
"""
fetch_trends.py — 抓取 Google Trends "Trending Now" RSS（8 国），复用 scripts/01 已验证的解析逻辑，
并额外提取 news_item 的 url/source（内容引用需要具名来源）。

支持两种输入：
  - 网络模式：直接请求 https://trends.google.com/trending/rss?geo={GEO}
  - 离线模式：读取本地 XML 快照（测试用 fixture / data/raw 归档）
"""
from __future__ import annotations

import re
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import requests

GEOS = ["US", "GB", "CA", "AU", "IN", "DE", "BR", "JP"]
NS = {"ht": "https://trends.google.com/trending/rss"}
UA = {
    "User-Agent": (
        "TrendFlowPipeline/1.0 (automated trend briefing pipeline; "
        "contact: https://github.com/bistuwangqiyuan/googlehottomyweb)"
    )
}

TRAFFIC_RE = re.compile(r"([\d,.]+)\s*([KMB]?)\+?", re.I)
MULT = {"": 1, "K": 1_000, "M": 1_000_000, "B": 1_000_000_000}


@dataclass
class NewsItem:
    title: str
    url: str
    source: str


@dataclass
class Trend:
    geo: str
    keyword: str
    approx_traffic_text: str
    traffic_lower_bound: int | None
    pub_date: str
    news: list[NewsItem] = field(default_factory=list)
    snapshot_utc: str = ""


def parse_traffic(text: str) -> int | None:
    if not text:
        return None
    m = TRAFFIC_RE.search(text.replace(",", ""))
    if not m:
        return None
    return int(float(m.group(1)) * MULT[m.group(2).upper()])


def parse_rss(content: bytes, geo: str) -> list[Trend]:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    trends: list[Trend] = []
    root = ET.fromstring(content)
    for item in root.iter("item"):
        title = (item.findtext("title", "") or "").strip()
        if not title:
            continue
        traffic_text = item.findtext("ht:approx_traffic", "", NS) or ""
        news: list[NewsItem] = []
        for n in item.findall("ht:news_item", NS):
            n_title = (n.findtext("ht:news_item_title", "", NS) or "").strip()
            n_url = (n.findtext("ht:news_item_url", "", NS) or "").strip()
            n_source = (n.findtext("ht:news_item_source", "", NS) or "").strip()
            if n_title and n_url.startswith("http"):
                news.append(NewsItem(title=n_title, url=n_url, source=n_source or "unnamed outlet"))
        trends.append(
            Trend(
                geo=geo,
                keyword=title,
                approx_traffic_text=traffic_text,
                traffic_lower_bound=parse_traffic(traffic_text),
                pub_date=(item.findtext("pubDate", "") or "").strip(),
                news=news,
                snapshot_utc=now,
            )
        )
    return trends


def fetch_live(geos: list[str] | None = None, raw_dir: Path | None = None) -> list[Trend]:
    """网络模式抓取；单 geo 失败不阻断整体（与 scripts/01 一致）。"""
    geos = geos or GEOS
    all_trends: list[Trend] = []
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    for geo in geos:
        url = f"https://trends.google.com/trending/rss?geo={geo}"
        try:
            resp = requests.get(url, headers=UA, timeout=30)
            resp.raise_for_status()
            if raw_dir:
                raw_dir.mkdir(parents=True, exist_ok=True)
                (raw_dir / f"trending_rss_{geo}_{today}.xml").write_bytes(resp.content)
            trends = parse_rss(resp.content, geo)
            print(f"[fetch] {geo}: {len(trends)} trends")
            all_trends.extend(trends)
        except Exception as exc:
            print(f"[fetch] {geo} FAILED: {exc}")
        time.sleep(1.5)
    return all_trends


def fetch_from_files(xml_paths: list[Path]) -> list[Trend]:
    """离线模式：从本地 XML 快照解析。文件名需含 geo（trending_rss_{GEO}_*.xml）。"""
    all_trends: list[Trend] = []
    for p in xml_paths:
        m = re.search(r"trending_rss_([A-Z]{2})_", p.name)
        geo = m.group(1) if m else "XX"
        all_trends.extend(parse_rss(p.read_bytes(), geo))
    return all_trends
