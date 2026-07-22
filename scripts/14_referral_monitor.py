# -*- coding: utf-8 -*-
"""
14_referral_monitor.py — 铭信导流监控（供给侧，逐日时间序列，可复现）

监控口径（诚实边界）：
  - 本脚本测量 **TrendFlow 侧可测的导流供给与合规状态**：线上 ai-infra 简报数、
    赞助触点数（上下文赞助卡 / 垂直枢纽页 / 全站页脚）、合规三要素
    （可见 Sponsored 标注 + rel="sponsored" + UTM 归因参数）、铭信落地页可达性。
  - **最终点击/转化数据在铭信站点侧**（UTM 归因，utm_source=trendflow），
    本脚本不编造任何点击数字。

输出：
  - data/referral_monitor.jsonl        —— 逐次快照追加（时间序列，审计可查）
  - data/referral_monitor_latest.json  —— 最新一次快照（便于人和脚本读取）

用法：
  python scripts/14_referral_monitor.py [--base-url https://trendflow-site.vercel.app]

退出码 0 = 全部合规检查通过；1 = 存在合规缺失（CI 中可见告警）。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests

ROOT = Path(__file__).resolve().parent.parent
OUT_JSONL = ROOT / "data" / "referral_monitor.jsonl"
OUT_LATEST = ROOT / "data" / "referral_monitor_latest.json"

UA = {"User-Agent": "TrendFlowReferralMonitor/1.0"}
SPONSOR_HOST = "mingxinstorage.xyz"
UTM_MARK = "utm_source=trendflow"


def get(url: str, timeout: int = 30) -> requests.Response:
    return requests.get(url, timeout=timeout, headers=UA, allow_redirects=True)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="MingXin referral supply monitor")
    ap.add_argument("--base-url", default="https://trendflow-site.vercel.app")
    args = ap.parse_args()
    base = args.base_url.rstrip("/")

    problems: list[str] = []

    # ---------- 1. 线上简报清单（以 sitemap 为准 = 真实已部署内容） ----------
    r = get(f"{base}/sitemap.xml")
    briefing_urls: list[str] = []
    if r.status_code == 200:
        try:
            ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
            tree = ET.fromstring(r.content)
            briefing_urls = [
                (e.text or "") for e in tree.findall(".//sm:loc", ns)
                if "/briefings/" in (e.text or "")
            ]
        except Exception as exc:
            problems.append(f"sitemap parse failed: {exc}")
    else:
        problems.append(f"sitemap HTTP {r.status_code}")

    # ---------- 2. 逐篇分类 + ai-infra 页赞助卡合规 ----------
    ai_infra_pages = 0
    sponsor_cards_ok = 0
    card_defects: list[str] = []
    for url in briefing_urls:
        path = urlparse(url).path
        try:
            page = get(f"{base}{path}")
        except Exception as exc:
            problems.append(f"{path}: fetch failed {exc}")
            continue
        if page.status_code != 200:
            problems.append(f"{path}: HTTP {page.status_code}")
            continue
        if ">ai-infra<" not in page.text:
            continue
        ai_infra_pages += 1
        ok = (
            'data-testid="sponsor-card"' in page.text
            and "Sponsored · Affiliated" in page.text
            and 'rel="sponsored noopener"' in page.text
            and UTM_MARK in page.text
            and SPONSOR_HOST in page.text
        )
        if ok:
            sponsor_cards_ok += 1
        else:
            card_defects.append(path)
    if card_defects:
        problems.append(f"sponsor card non-compliant on: {card_defects}")

    # ---------- 3. 垂直枢纽页 /ai-infrastructure ----------
    hub_live = False
    hub_listed = 0
    r = get(f"{base}/ai-infrastructure")
    if r.status_code == 200:
        hub_live = (
            'data-testid="sponsor-card"' in r.text
            and 'rel="sponsored noopener"' in r.text
            and UTM_MARK in r.text
        )
        hub_listed = len(set(re.findall(r'href="(/briefings/[^"#]+)"', r.text)))
        if not hub_live:
            problems.append("hub page live but sponsor module non-compliant")
    else:
        # 枢纽页随下一次部署上线；未上线期间如实记录，不算合规缺陷
        print(f"[info] hub not live yet (HTTP {r.status_code}); will appear after next deploy")

    # ---------- 4. 全站页脚披露位（以首页为样本） ----------
    r = get(f"{base}/")
    footer_ok = (
        r.status_code == 200
        and 'data-testid="footer-sponsor"' in r.text
        and 'rel="sponsored noopener"' in r.text
        and UTM_MARK in r.text
    )
    if not footer_ok:
        problems.append("footer sponsor slot missing or non-compliant")

    # ---------- 5. 铭信落地页可达性（含 UTM，模拟真实点击路径） ----------
    landing_url = (
        f"https://{SPONSOR_HOST}/?utm_source=trendflow&utm_medium=sponsored"
        "&utm_campaign=ai-infra&utm_content=monitor-probe"
    )
    try:
        lr = get(landing_url)
        landing_status = lr.status_code
    except Exception as exc:
        landing_status = 0
        problems.append(f"MingXin landing unreachable: {exc}")
    if landing_status != 200:
        problems.append(f"MingXin landing HTTP {landing_status}")

    # ---------- 汇总快照 ----------
    snapshot = {
        "at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "base_url": base,
        "briefings_live": len(briefing_urls),
        "ai_infra_pages_live": ai_infra_pages,
        "sponsor_cards_compliant": sponsor_cards_ok,
        "hub_live_and_compliant": hub_live,
        "hub_listed_briefings": hub_listed,
        "footer_sponsor_compliant": footer_ok,
        "sponsor_touchpoints_total": sponsor_cards_ok + (1 if hub_live else 0) + (1 if footer_ok else 0),
        "mingxin_landing_http": landing_status,
        "problems": problems,
        "note": "click/conversion data is measured on the MingXin side via UTM "
                "(utm_source=trendflow); this monitor covers supply-side exposure "
                "and compliance only",
    }

    OUT_JSONL.parent.mkdir(parents=True, exist_ok=True)
    with OUT_JSONL.open("a", encoding="utf-8") as f:
        f.write(json.dumps(snapshot, ensure_ascii=False) + "\n")
    OUT_LATEST.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2),
                          encoding="utf-8")

    print(json.dumps(snapshot, ensure_ascii=False, indent=2))
    print(f"\n写出 {OUT_JSONL}（追加）与 {OUT_LATEST}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
