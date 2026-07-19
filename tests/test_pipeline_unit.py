# -*- coding: utf-8 -*-
"""
test_pipeline_unit.py — 流水线单元测试（零第三方测试框架，纯 Python 断言）。

覆盖：RSS 解析、合规黑名单（C1-C5）、去重（跨国/批内/历史）、容量上限、
slug 生成、简报生成 schema、审核规则关口（好内容通过/坏内容拒绝）、
离线全链路（fixture → 发布文件 + 审计日志）。

运行：python tests/test_pipeline_unit.py   （退出码 0 = 全部通过）
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline.fetch_trends import NewsItem, Trend, fetch_from_files, parse_traffic
from pipeline.generate import generate_briefing
from pipeline.opportunity_filter import filter_trends, slugify
from pipeline.review import review, rules_review

FIXTURES = ROOT / "tests" / "fixtures"

PASSED: list[str] = []
FAILED: list[tuple[str, str]] = []


def run(name: str, fn) -> None:
    try:
        fn()
        PASSED.append(name)
        print(f"[PASS] {name}")
    except Exception:
        FAILED.append((name, traceback.format_exc()))
        print(f"[FAIL] {name}\n{traceback.format_exc()}")


def make_trend(keyword: str, traffic: int = 50_000, geo: str = "US", news: list | None = None) -> Trend:
    if news is None:
        news = [NewsItem(title=f"News about {keyword}", url="https://example.com/a", source="Example")]
    return Trend(
        geo=geo, keyword=keyword, approx_traffic_text=f"{traffic}+",
        traffic_lower_bound=traffic, pub_date="Fri, 17 Jul 2026 08:00:00 -0700",
        news=news, snapshot_utc="2026-07-17T16:00:00+00:00",
    )


# ---------------- 抓取/解析 ----------------

def test_parse_traffic():
    assert parse_traffic("200K+") == 200_000
    assert parse_traffic("1M+") == 1_000_000
    assert parse_traffic("2,000+") == 2_000
    assert parse_traffic("") is None


def test_fixture_parse():
    trends = fetch_from_files(sorted(FIXTURES.glob("trending_rss_*.xml")))
    assert len(trends) == 10, f"expected 10 fixture trends, got {len(trends)}"
    kws = {t.keyword for t in trends}
    assert "pixel 11 pro release date" in kws
    us_pixel = next(t for t in trends if t.keyword == "pixel 11 pro release date" and t.geo == "US")
    assert us_pixel.traffic_lower_bound == 50_000
    assert len(us_pixel.news) == 2
    assert us_pixel.news[0].url.startswith("https://")


# ---------------- 机会过滤器 ----------------

def _filter(trends, tmp: Path, **kw):
    return filter_trends(trends, tmp / "briefings", **kw)


def test_blacklist_gossip():
    with tempfile.TemporaryDirectory() as d:
        res = _filter([make_trend("celebrity divorce settlement")], Path(d))
        assert not res[0].accepted and "C4-gossip" in res[0].reason, res[0].reason


def test_blacklist_finance():
    with tempfile.TemporaryDirectory() as d:
        res = _filter([make_trend("best stocks to buy now")], Path(d))
        assert not res[0].accepted and "C1-YMYL-finance" in res[0].reason, res[0].reason


def test_blacklist_tragedy():
    with tempfile.TemporaryDirectory() as d:
        news = [NewsItem(title="Several killed in crash", url="https://e.com/a", source="E")]
        res = _filter([make_trend("highway incident", news=news)], Path(d))
        assert not res[0].accepted and "C3-tragedy" in res[0].reason, res[0].reason


def test_no_source_rejected():
    with tempfile.TemporaryDirectory() as d:
        res = _filter([make_trend("no source term", news=[])], Path(d))
        assert not res[0].accepted and "C5-sources" in res[0].reason, res[0].reason


def test_low_volume_rejected():
    with tempfile.TemporaryDirectory() as d:
        res = _filter([make_trend("tiny term", traffic=100)], Path(d), min_traffic=500)
        assert not res[0].accepted and "low-volume" in res[0].reason, res[0].reason


def test_dedup_across_geos():
    with tempfile.TemporaryDirectory() as d:
        res = _filter(
            [make_trend("pixel 11", traffic=50_000, geo="US"), make_trend("pixel 11", traffic=20_000, geo="GB")],
            Path(d),
        )
        accepted = [r for r in res if r.accepted]
        assert len(accepted) == 1 and accepted[0].trend.geo == "US"


def test_dedup_against_history():
    with tempfile.TemporaryDirectory() as d:
        content = Path(d) / "briefings"
        content.mkdir(parents=True)
        from datetime import datetime, timezone
        (content / "old.json").write_text(json.dumps({
            "keyword": "pixel 11", "publishedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }), encoding="utf-8")
        res = filter_trends([make_trend("pixel 11")], content)
        assert not res[0].accepted and "within 7 days" in res[0].reason, res[0].reason


def test_capacity_cap():
    with tempfile.TemporaryDirectory() as d:
        trends = [make_trend(f"unique keyword number {i}", traffic=10_000 + i) for i in range(8)]
        res = _filter(trends, Path(d), max_accept=3)
        assert sum(r.accepted for r in res) == 3
        assert any("skipped-capacity" in r.reason for r in res)


def test_tier_a_priority():
    with tempfile.TemporaryDirectory() as d:
        trends = [
            make_trend("some general event thing", traffic=900_000),
            make_trend("iphone 18 review", traffic=20_000),
        ]
        res = _filter(trends, Path(d), max_accept=1)
        accepted = [r for r in res if r.accepted]
        assert len(accepted) == 1 and accepted[0].trend.keyword == "iphone 18 review", (
            "Tier A (consumer-tech) must outrank higher-traffic general topics"
        )


def test_ai_infra_classification():
    """含 AI 基础设施词的热词必须归类为 ai-infra（Tier S）。"""
    with tempfile.TemporaryDirectory() as d:
        news = [NewsItem(title="Nvidia unveils next Blackwell GPU for data center AI",
                         url="https://e.com/a", source="E")]
        res = _filter([make_trend("nvidia blackwell", news=news)], Path(d))
        accepted = [r for r in res if r.accepted]
        assert len(accepted) == 1 and accepted[0].category == "ai-infra", (
            f"expected ai-infra, got {accepted[0].category if accepted else 'rejected'}"
        )


def test_ai_infra_phrase_match():
    """多词短语（如 data center）也要能命中，且只看新闻标题也算。"""
    with tempfile.TemporaryDirectory() as d:
        news = [NewsItem(title="New data center powers local AI boom",
                         url="https://e.com/a", source="E")]
        res = _filter([make_trend("some regional project", news=news)], Path(d))
        accepted = [r for r in res if r.accepted]
        assert len(accepted) == 1 and accepted[0].category == "ai-infra"


def test_ai_infra_exempt_from_min_traffic():
    """ai-infra 类豁免流量门槛；同量级的 general 词仍被拒。"""
    with tempfile.TemporaryDirectory() as d:
        news = [NewsItem(title="Nvidia data center revenue update", url="https://e.com/a", source="E")]
        res = _filter(
            [make_trend("nvidia h100 supply", traffic=200, news=news),
             make_trend("random village fair", traffic=200)],
            Path(d), min_traffic=500,
        )
        by_kw = {r.trend.keyword: r for r in res}
        assert by_kw["nvidia h100 supply"].accepted and by_kw["nvidia h100 supply"].category == "ai-infra"
        assert not by_kw["random village fair"].accepted and "low-volume" in by_kw["random village fair"].reason


def test_ai_infra_outranks_consumer_tech():
    """容量受限时 Tier S（ai-infra）优先于流量更高的 Tier A（consumer-tech）。"""
    with tempfile.TemporaryDirectory() as d:
        trends = [
            make_trend("iphone 18 review", traffic=900_000),
            make_trend("openai gpt 6 inference", traffic=5_000),
        ]
        res = _filter(trends, Path(d), max_accept=1)
        accepted = [r for r in res if r.accepted]
        assert len(accepted) == 1 and accepted[0].trend.keyword == "openai gpt 6 inference", (
            "Tier S (ai-infra) must outrank higher-traffic consumer-tech topics"
        )


def test_slugify():
    assert slugify("Pixel 11 Pro!") == "pixel-11-pro"
    assert slugify("日本語キーワード").startswith("trend-")
    assert len(slugify("x" * 300)) <= 60


# ---------------- 生成 + 审核 ----------------

def test_briefing_schema_and_review():
    t = make_trend("pixel 11 pro release date", traffic=50_000)
    art = generate_briefing(t, "consumer-tech")
    for key in ("slug", "title", "description", "sections", "faq", "sources", "facts", "mode"):
        assert key in art, f"missing key {key}"
    assert art["mode"] == "briefing"
    assert 3 <= len(art["sections"]) <= 8
    assert len(art["faq"]) >= 2
    r = review(art)
    assert r["approved"], f"good briefing must pass review: {r['notes']}"
    assert r["mode"] == "rules"


def test_review_rejects_missing_sources():
    t = make_trend("pixel 11 pro", traffic=50_000)
    art = generate_briefing(t, "consumer-tech")
    art["sources"] = []
    ok, _, failures = rules_review(art)
    assert not ok and any("no sources" in f for f in failures)


def test_review_rejects_ungrounded_number():
    t = make_trend("pixel 11 pro", traffic=50_000)
    art = generate_briefing(t, "consumer-tech")
    art["sections"][0]["paragraphs"].append("It sold exactly 1,234,567 units.")
    ok, _, failures = rules_review(art)
    assert not ok and any("ungrounded number" in f for f in failures), failures


def test_review_rejects_blacklist_leak():
    t = make_trend("pixel 11 pro", traffic=50_000)
    art = generate_briefing(t, "consumer-tech")
    art["sections"][0]["paragraphs"].append("Also here is investment advice for you.")
    ok, _, failures = rules_review(art)
    assert not ok, failures


def test_llm_mode_fails_closed_without_reviewer():
    t = make_trend("pixel 11 pro", traffic=50_000)
    art = generate_briefing(t, "consumer-tech")
    art["mode"] = "llm"  # 模拟 LLM 内容但没有配置独立审核模型
    import os
    saved = {k: os.environ.pop(k, None) for k in ("LLM_API_KEY", "REVIEW_API_KEY")}
    try:
        r = review(art)
        assert not r["approved"] and "no review key" in r["notes"], r["notes"]
    finally:
        for k, v in saved.items():
            if v is not None:
                os.environ[k] = v


# ---------------- 离线全链路 ----------------

def test_offline_pipeline_end_to_end():
    with tempfile.TemporaryDirectory() as d:
        content = Path(d) / "briefings"
        audit = Path(d) / "audit"
        proc = subprocess.run(
            [sys.executable, "-m", "pipeline.run_pipeline",
             "--fixture-dir", str(FIXTURES),
             "--content-dir", str(content), "--audit-dir", str(audit),
             "--max-publish", "5"],
            cwd=ROOT, capture_output=True, text=True, timeout=300,
        )
        assert proc.returncode == 0, proc.stdout + proc.stderr
        published = list(content.glob("*.json"))
        assert len(published) >= 3, f"expected >=3 published, got {[p.name for p in published]}"
        # 黑名单词条一定不能出现在发布内容里
        kws = {json.loads(p.read_text(encoding="utf-8"))["keyword"] for p in published}
        assert "celebrity divorce settlement" not in kws
        assert "best stocks to buy now" not in kws
        assert "highway crash victims" not in kws
        # 审计日志覆盖每一条决策
        log = json.loads((audit / "pipeline_log.json").read_text(encoding="utf-8"))
        assert any(e["decision"] == "rejected" and "C4-gossip" in e["reason"] for e in log)
        assert any(e["decision"] == "published" for e in log)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    tests = [(k, v) for k, v in globals().items() if k.startswith("test_") and callable(v)]
    for name, fn in tests:
        run(name, fn)
    print(f"\n{len(PASSED)} passed, {len(FAILED)} failed (of {len(tests)})")
    return 1 if FAILED else 0


if __name__ == "__main__":
    raise SystemExit(main())
