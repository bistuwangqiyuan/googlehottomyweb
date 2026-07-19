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

# ---------- AI/算力基础设施词表（→ Tier S "ai-infra"，赞助位受众相关性最高） ----------
# 支持多词短语；匹配方式与黑名单一致（规范化后子串匹配 keyword + 新闻标题）。
# 词表选择依据：铭信业务域（存储加速 / 国产算力 / 算力中心）+ AI 基础设施公共话题词，
# 命中率基线见 scripts/12_ai_infra_keyword_baseline.py（可复现）。
# 精度优先原则：只收在新闻语境下几乎无歧义的词；刻意排除高歧义单词
# （如 "arm"=手臂、"gemini"=星座、"sora" 单用、"kimi"=人名、"fab"），
# 歧义品牌用限定短语（"google gemini"、"moonshot ai"、"mistral ai"）。
AI_INFRA_TERMS = [
    # 芯片与算力硬件（厂商 / 产品 / 部件）
    "gpu", "nvidia", "h100", "h200", "b200", "b300", "gb200", "gb300", "gh200",
    "blackwell", "nvidia rubin", "dgx", "geforce rtx",
    "tpu", "npu", "ai chip", "ai chips", "ai accelerator", "ai accelerators",
    "semiconductor", "semiconductors", "tsmc", "sk hynix", "micron", "broadcom",
    "qualcomm", "snapdragon", "amd", "intel", "arm holdings",
    "hbm", "hbm3", "hbm3e", "hbm4", "cuda", "ascend", "instinct",
    "mi300", "mi308", "mi325", "mi355", "trainium", "inferentia",
    "cerebras", "groq", "sambanova", "graphcore", "chip plant", "chip factory",
    "chipmaker", "chip maker", "foundry", "wafer",
    # 大模型与推理（组织 / 模型 / 概念）
    "llm", "large language model", "large language models", "ai model", "ai models",
    "model training", "inference", "openai", "anthropic", "deepseek", "qwen",
    "mistral ai", "moonshot ai", "frontier model", "artificial intelligence",
    "generative ai", "genai", "agi", "chatgpt", "gpt 5", "gpt5", "gpt 6",
    "claude", "grok", "meta llama", "llama 3", "llama 4",
    "google gemini", "gemini ai", "copilot",
    "perplexity", "hugging face", "stability ai", "meta ai", "xai",
    "openai sora", "midjourney",
    # 数据中心与存储基础设施
    "data center", "data centers", "datacenter", "datacenters", "data centre",
    "data centres", "supercomputer", "supercomputers", "ai server", "ai servers",
    "nvme", "ssd", "flash storage", "ai infrastructure", "compute cluster",
    "gpu cluster", "colocation", "hyperscaler", "hyperscale", "server farm",
    "liquid cooling", "coreweave", "nebius", "lambda labs", "stargate",
    "colossus", "kv cache", "object storage",
    # 行业事件
    "gtc", "computex",
    # 覆盖地区的本地语言 AI/算力词（与英文词同一匹配口径；normalization 两侧一致，
    # 含变音符的词照常工作）
    "inteligencia artificial", "inteligência artificial", "intelligence artificielle",
    "intelligenza artificiale", "künstliche intelligenz", "sztuczna inteligencja",
    "kunstmatige intelligentie", "kecerdasan buatan", "artificiell intelligens",
    "centro de datos", "centros de datos", "centro de dados", "rechenzentrum",
    "datacentrum",
]

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


def _ai_infra_hits(trend: Trend) -> list[str]:
    """AI/算力基础设施词命中（短语级子串匹配，与黑名单同一匹配口径）。"""
    corpus = " " + _norm_text(trend.keyword) + " "
    for n in trend.news:
        corpus += " " + _norm_text(n.title) + " "
    return [term for term in AI_INFRA_TERMS if f" {_norm_text(term)} " in corpus]


def _intent_score(trend: Trend) -> tuple[float, str]:
    """返回 (score, category)。Tier S（ai-infra）> Tier A（consumer-tech）> general。"""
    corpus_words = set(_norm_text(trend.keyword).split())
    for n in trend.news:
        corpus_words |= set(_norm_text(n.title).split())
    hits = corpus_words & set(TECH_PRODUCT_TERMS)
    traffic = trend.traffic_lower_bound or 0
    # 量级分 0-1（1M+ 封顶）+ 意图分 0-1（3 个词命中封顶）
    volume_score = min(traffic / 1_000_000, 1.0)
    infra_hits = _ai_infra_hits(trend)
    if infra_hits:
        infra_intent = min(len(infra_hits) / 3.0, 1.0)
        return 0.5 * infra_intent + 0.5 * volume_score + 1.0, "ai-infra"  # Tier S 加 1.0 基础分
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
        # ai-infra 词量级天然低于大众热词，豁免流量门槛（其余合规/来源/去重关口不变）
        if (t.traffic_lower_bound or 0) < min_traffic and not _ai_infra_hits(t):
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

    # Tier S（ai-infra）> Tier A（consumer-tech）> general，同层内分数降序；超出容量的降级为 skipped
    tier_rank = {"ai-infra": 2, "consumer-tech": 1}
    scored.sort(key=lambda r: (-tier_rank.get(r.category, 0), -r.score))
    for i, r in enumerate(scored):
        if i >= max_accept:
            r.accepted = False
            r.reason = f"skipped-capacity: rank {i + 1} > max {max_accept}"
    results.extend(scored)
    return results
