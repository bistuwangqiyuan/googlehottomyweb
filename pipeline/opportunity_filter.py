# -*- coding: utf-8 -*-
"""
opportunity_filter.py — 机会过滤器：合规黑名单（C1-C5）+ 去重 + 意图/变现评分。

规则与商业计划书合规准则一致（business-plan/10-risks-and-compliance.md）：
  C1 不碰 YMYL（医疗/金融投资建议）
  C2 不碰博彩、成人、烟酒毒品
  C3 不消费悲剧/灾难/死亡（尊重原则）
  C4 不碰私人八卦（离婚/绯闻/逮捕类围观内容）
  C5 来源不完整（无具名新闻来源）不发布

每条决策产出结构化 (decision, reason)，由 run_pipeline 写入可审计日志。
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .fetch_trends import Trend

# ---------- 合规黑名单（对 keyword + 新闻标题做全文匹配，宁可错杀不可漏放） ----------
BLACKLIST: dict[str, list[str]] = {
    "C1-YMYL-medical": [
        "cancer treatment", "cure for", "vaccine side effect", "overdose", "diagnosis",
        "symptoms of", "medication", "prescription", "weight loss drug", "ozempic",
        "surgery", "medical advice", "mental illness", "suicide",
    ],
    "C1-YMYL-finance": [
        "stock to buy", "stocks to buy", "invest in", "investment advice", "crypto",
        "bitcoin price", "how to get rich", "loan", "mortgage rate", "forex",
        "share price target", "trading signal",
    ],
    "C2-gambling-adult": [
        "casino", "betting odds", "sportsbook", "lottery numbers", "powerball numbers",
        "jackpot", "porn", "onlyfans", "nsfw", "escort", "vape", "cigarette",
        "marijuana", "cannabis",
    ],
    "C3-tragedy": [
        "dies", "died", "death of", "dead at", "killed", "shooting", "massacre",
        "plane crash", "car crash", "earthquake death", "obituary", "funeral",
        "murder", "stabbing", "terror attack", "hostage", "body found", "found dead",
        "cause of death", "autopsy",
    ],
    "C4-gossip": [
        "divorce", "affair", "cheating scandal", "mugshot", "arrested", "leaked photos",
        "dating rumor", "breakup", "custody battle", "lawsuit against ex",
    ],
}

# ---------- 意图评分词表（消费科技/产品意图 → Tier A，商业价值更高） ----------
TECH_PRODUCT_TERMS = [
    "ai", "app", "chatgpt", "gpt", "gemini", "copilot", "openai", "iphone", "ipad",
    "macbook", "apple", "samsung", "galaxy", "pixel", "android", "windows", "xbox",
    "playstation", "ps5", "ps6", "nintendo", "switch", "steam", "tesla", "software",
    "update", "release", "launch", "review", "specs", "price", "preorder",
    "pre-order", "deal", "sale", "vs", "beta", "download", "feature", "chip", "gpu",
    "laptop", "smartphone", "earbuds", "console", "game", "trailer", "streaming",
]

_WORD_RE = re.compile(r"[a-z0-9]+")


def _norm_text(s: str) -> str:
    return " ".join(_WORD_RE.findall(s.lower()))


def slugify(keyword: str) -> str:
    ascii_kw = unicodedata.normalize("NFKD", keyword).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_kw.lower()).strip("-")
    if not slug:
        slug = "trend-" + hashlib.sha256(keyword.encode("utf-8")).hexdigest()[:8]
    return slug[:60].strip("-")


@dataclass
class FilterResult:
    trend: Trend
    accepted: bool
    reason: str
    category: str = ""
    score: float = 0.0


def _blacklist_hit(trend: Trend) -> str | None:
    corpus = " " + _norm_text(trend.keyword) + " "
    for n in trend.news:
        corpus += " " + _norm_text(n.title) + " "
    for rule, terms in BLACKLIST.items():
        for term in terms:
            if f" {_norm_text(term)} " in corpus or _norm_text(term) == _norm_text(trend.keyword):
                return f"{rule}: matched '{term}'"
    return None


def _intent_score(trend: Trend) -> tuple[float, str]:
    """返回 (score, category)。Tier A（consumer-tech）优先，其余为 general news。"""
    corpus_words = set(_norm_text(trend.keyword).split())
    for n in trend.news:
        corpus_words |= set(_norm_text(n.title).split())
    hits = corpus_words & set(TECH_PRODUCT_TERMS)
    traffic = trend.traffic_lower_bound or 0
    # 量级分 0-1（1M+ 封顶）+ 意图分 0-1（3 个词命中封顶）
    volume_score = min(traffic / 1_000_000, 1.0)
    intent = min(len(hits) / 3.0, 1.0)
    if hits:
        return 0.5 * intent + 0.5 * volume_score + 0.5, "consumer-tech"  # Tier A 加 0.5 基础分
    return 0.5 * volume_score, "general"


def load_recent_keywords(content_dir: Path, days: int = 7) -> set[str]:
    """已发布内容 7 天内的关键词集合（去重依据）。"""
    seen: set[str] = set()
    if not content_dir.exists():
        return seen
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    for f in content_dir.glob("*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            published = datetime.fromisoformat(data["publishedAt"].replace("Z", "+00:00"))
            if published >= cutoff:
                seen.add(_norm_text(data["keyword"]))
        except Exception:
            continue
    return seen


def filter_trends(
    trends: list[Trend],
    content_dir: Path,
    min_traffic: int = 500,
    max_accept: int = 5,
) -> list[FilterResult]:
    """按合规→质量→去重→评分顺序过滤，返回全部决策（含拒绝原因，供审计）。"""
    results: list[FilterResult] = []
    recent = load_recent_keywords(content_dir)
    batch_seen: set[str] = set()

    # 同一关键词跨国重复时保留流量最高的一条
    best_by_kw: dict[str, Trend] = {}
    for t in trends:
        k = _norm_text(t.keyword)
        if k not in best_by_kw or (t.traffic_lower_bound or 0) > (best_by_kw[k].traffic_lower_bound or 0):
            best_by_kw[k] = t

    scored: list[FilterResult] = []
    for t in trends:
        k = _norm_text(t.keyword)
        if best_by_kw[k] is not t:
            results.append(FilterResult(t, False, "dedup: duplicate across geos, kept highest-traffic copy"))
            continue
        hit = _blacklist_hit(t)
        if hit:
            results.append(FilterResult(t, False, f"blacklist {hit}"))
            continue
        if not t.news:
            results.append(FilterResult(t, False, "C5-sources: no named news source in feed"))
            continue
        if (t.traffic_lower_bound or 0) < min_traffic:
            results.append(FilterResult(t, False, f"low-volume: {t.traffic_lower_bound} < {min_traffic}"))
            continue
        if k in recent:
            results.append(FilterResult(t, False, "dedup: same keyword published within 7 days"))
            continue
        if k in batch_seen:
            results.append(FilterResult(t, False, "dedup: duplicate within batch"))
            continue
        batch_seen.add(k)
        score, category = _intent_score(t)
        scored.append(FilterResult(t, True, "passed all gates", category=category, score=score))

    # Tier A 优先、分数降序，超出容量的降级为 skipped
    scored.sort(key=lambda r: (-(r.category == "consumer-tech"), -r.score))
    for i, r in enumerate(scored):
        if i >= max_accept:
            r.accepted = False
            r.reason = f"skipped-capacity: rank {i + 1} > max {max_accept}"
    results.extend(scored)
    return results
