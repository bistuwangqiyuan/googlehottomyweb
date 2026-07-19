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
# 覆盖铭信全业务域（存储加速 / 国产算力 / 算力中心 / 效能优化 / AI 软件栈）。
# 精度原则：排除会污染品牌安全的高歧义单词（"arm"=手臂、"gemini"=星座、"sora" 单用、
# "kimi"=人名、"fab"、"rtx"=雷神公司、"intel"=军事情报、"gaudi"=建筑师、"azure"=天蓝色、
# "raid"=突袭、"runway"=跑道），歧义品牌一律用限定短语。误报后果仅是赞助卡出现在
# 弱相关页（有明确标注），C1-C5 黑名单先于本词表执行，品牌安全不受影响。
AI_INFRA_TERMS = [
    # ---- 芯片与算力硬件：厂商 ----
    "nvidia", "tsmc", "sk hynix", "micron", "broadcom", "qualcomm", "snapdragon",
    "amd", "arm holdings", "intel chip", "intel chips", "intel ceo", "intel foundry",
    "cerebras", "groq", "sambanova", "graphcore", "chipmaker", "chip maker",
    "chip plant", "chip factory", "foundry", "wafer", "semiconductor",
    "semiconductors", "chip ban", "chip export", "chip exports", "export controls",
    "chips act", "chip shortage", "chip war",
    # ---- 芯片与算力硬件：产品与部件 ----
    "gpu", "gpus", "tpu", "npu", "ai chip", "ai chips", "ai accelerator",
    "ai accelerators", "h100", "h200", "a100", "b200", "b300", "gb200", "gb300",
    "gh200", "blackwell", "nvidia rubin", "dgx", "geforce rtx", "rtx 5090",
    "rtx 5080", "rtx 6090", "cuda", "nvlink", "hbm", "hbm3", "hbm3e", "hbm4",
    "radeon", "instinct", "mi300", "mi308", "mi325", "mi355", "epyc", "ryzen",
    "threadripper", "xeon", "intel arc", "intel gaudi", "trainium", "inferentia",
    "risc v", "dram", "ddr5", "ddr6", "nand", "3d nand", "qlc", "memory chip",
    "memory chips", "cxl",
    # ---- 国产算力生态（铭信核心业务域）----
    "ascend", "ascend 910", "huawei ai", "cambricon", "moore threads", "biren",
    "hygon", "loongson", "kunlunxin", "enflame", "smic", "ymtc", "cxmt",
    # ---- 大模型与 AI 组织 ----
    "llm", "llms", "large language model", "large language models", "ai model",
    "ai models", "model training", "inference", "openai", "anthropic", "deepseek",
    "qwen", "qwen3", "mistral ai", "moonshot ai", "kimi k2", "zhipu", "minimax ai",
    "doubao", "ernie bot", "iflytek", "sensetime", "deepmind", "meta ai", "xai",
    "stability ai", "perplexity", "hugging face", "cohere", "elevenlabs",
    "eleven labs", "notebooklm",
    # ---- 模型与产品 ----
    "chatgpt", "gpt 4", "gpt4", "gpt 5", "gpt5", "gpt 6", "claude", "grok",
    "meta llama", "llama 3", "llama 4", "google gemini", "gemini ai", "gemini 2",
    "gemini 3", "copilot", "openai sora", "midjourney", "frontier model",
    # ---- AI 概念与议题 ----
    "artificial intelligence", "generative ai", "genai", "agi", "superintelligence",
    "ai agent", "ai agents", "agentic ai", "ai chatbot", "ai assistant",
    "ai search", "ai video", "ai coding", "vibe coding", "ai boom", "ai bubble",
    "ai race", "eu ai act", "ai regulation",
    # ---- AI 行业人物 ----
    "sam altman", "jensen huang", "dario amodei", "demis hassabis",
    # ---- 数据中心 / HPC / 云 ----
    "data center", "data centers", "datacenter", "datacenters", "data centre",
    "data centres", "supercomputer", "supercomputers", "supercomputing", "hpc",
    "high performance computing", "exascale", "exaflop", "petaflops", "ai server",
    "ai servers", "ai infrastructure", "compute cluster", "gpu cluster",
    "gpu shortage", "colocation", "hyperscaler", "hyperscale", "server farm",
    "liquid cooling", "infiniband", "coreweave", "nebius", "lambda labs",
    "stargate", "colossus", "equinix", "digital realty", "vertiv", "supermicro",
    "microsoft azure", "google cloud", "oracle cloud", "aws", "cloud computing",
    # ---- 存储基础设施（铭信核心业务域）----
    "nvme", "ssd", "ssds", "flash storage", "all flash", "storage array",
    "storage arrays", "object storage", "kv cache", "pcie", "iops",
    "pure storage", "netapp", "vast data", "weka",
    # ---- AI 软件栈 ----
    "vllm", "tensorrt", "pytorch",
    # ---- 行业事件 ----
    "gtc", "computex",
    # ---- 覆盖地区的本地语言 AI/算力词（normalization 两侧一致，含变音符照常匹配）----
    "inteligencia artificial", "inteligência artificial", "intelligence artificielle",
    "intelligenza artificiale", "künstliche intelligenz", "sztuczna inteligencja",
    "kunstmatige intelligentie", "kecerdasan buatan", "artificiell intelligens",
    "ia generativa", "centro de datos", "centros de datos", "centro de dados",
    "centre de données", "centres de données", "rechenzentrum", "datacentrum",
    "pusat data",
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

    # Tier S（ai-infra）> Tier A（consumer-tech）> general，同层内分数降序。
    # ai-infra 不占发布容量（通过全部合规关口的 ai-infra 机会全量放行）；
    # max_accept 仅约束其余类别，控制大众话题内容量。
    tier_rank = {"ai-infra": 2, "consumer-tech": 1}
    scored.sort(key=lambda r: (-tier_rank.get(r.category, 0), -r.score))
    non_infra_rank = 0
    for r in scored:
        if r.category == "ai-infra":
            continue
        non_infra_rank += 1
        if non_infra_rank > max_accept:
            r.accepted = False
            r.reason = f"skipped-capacity: non-infra rank {non_infra_rank} > max {max_accept}"
    results.extend(scored)
    return results
