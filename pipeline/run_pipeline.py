# -*- coding: utf-8 -*-
"""
run_pipeline.py — 流水线编排器：抓取 → 过滤 → 生成 → 审核 → 发布。

用法：
    python -m pipeline.run_pipeline                      # 网络模式，最多发布 5 篇
    python -m pipeline.run_pipeline --max-publish 3
    python -m pipeline.run_pipeline --fixture-dir tests/fixtures   # 离线模式（测试）
    python -m pipeline.run_pipeline --dry-run            # 只打印决策，不写文件

退出码：0 = 正常（含"本轮无新内容"），1 = 异常（抓取全失败等）。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.fetch_trends import fetch_from_files, fetch_live
from pipeline.generate import generate, llm_config
from pipeline.opportunity_filter import filter_trends
from pipeline.publish import append_audit, audit_entry, write_article
from pipeline.review import review

ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIR = ROOT / "site" / "content" / "briefings"
AUDIT_DIR = ROOT / "site" / "content" / "audit"


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="TrendFlow content pipeline")
    ap.add_argument("--max-publish", type=int, default=5, help="本轮最多发布篇数")
    # 实测 Trending-Now RSS 的量级下界中位数约 500（data/trending_now_summary.json），阈值取中位数
    ap.add_argument("--min-traffic", type=int, default=500, help="最低搜索量下界")
    ap.add_argument("--fixture-dir", type=Path, default=None, help="离线模式：本地 RSS XML 目录")
    ap.add_argument("--dry-run", action="store_true", help="只打印决策，不写任何文件")
    ap.add_argument("--content-dir", type=Path, default=CONTENT_DIR, help="内容输出目录（测试隔离用）")
    ap.add_argument("--audit-dir", type=Path, default=AUDIT_DIR, help="审计日志目录（测试隔离用）")
    args = ap.parse_args()
    content_dir: Path = args.content_dir
    audit_dir: Path = args.audit_dir

    mode = "llm" if llm_config() else "briefing"
    print(f"[pipeline] content mode: {mode}")

    # 1. 抓取
    if args.fixture_dir:
        xmls = sorted(args.fixture_dir.glob("trending_rss_*.xml"))
        if not xmls:
            print(f"[pipeline] no fixture XML found in {args.fixture_dir}")
            return 1
        trends = fetch_from_files(xmls)
        print(f"[pipeline] offline mode: {len(trends)} trends from {len(xmls)} fixtures")
    else:
        trends = fetch_live()
        print(f"[pipeline] live mode: {len(trends)} trends fetched")
    if not trends:
        print("[pipeline] FATAL: no trends fetched")
        return 1

    # 2. 机会过滤（合规黑名单 + 去重 + 意图评分）
    results = filter_trends(
        trends, content_dir, min_traffic=args.min_traffic, max_accept=args.max_publish
    )
    accepted = [r for r in results if r.accepted]
    print(f"[pipeline] filter: {len(accepted)} accepted / {len(results)} decisions")

    audit: list[dict] = []
    for r in results:
        if not r.accepted:
            audit.append(audit_entry(r.trend.keyword, r.trend.geo, "rejected", r.reason))

    # 3-5. 生成 → 审核 → 发布
    published = 0
    for r in accepted:
        article = generate(r.trend, r.category)
        article["review"] = review(article)
        if article["review"]["approved"]:
            if not args.dry_run:
                path = write_article(article, content_dir)
                print(f"[pipeline] PUBLISHED {path.name} (review {article['review']['score']})")
            else:
                print(f"[pipeline] DRY-RUN would publish {article['slug']}")
            audit.append(
                audit_entry(
                    r.trend.keyword, r.trend.geo, "published",
                    f"score {article['review']['score']} ({article['review']['mode']})",
                    slug=article["slug"],
                )
            )
            published += 1
        else:
            print(f"[pipeline] REJECTED by review gate: {article['slug']} — {article['review']['notes']}")
            audit.append(
                audit_entry(
                    r.trend.keyword, r.trend.geo, "rejected",
                    f"review gate: {article['review']['notes']}",
                )
            )

    if not args.dry_run:
        append_audit(audit, audit_dir)

    print(
        json.dumps(
            {"mode": mode, "fetched": len(trends), "accepted": len(accepted), "published": published},
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
