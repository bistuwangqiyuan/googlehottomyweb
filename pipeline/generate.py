# -*- coding: utf-8 -*-
"""
generate.py — 内容生成（双模式）：

  1. briefing 模式（默认，无需 LLM key）：确定性模板，只复述 RSS 中可验证的事实
     （热词、Google 报告的搜索量下界、地区、具名新闻标题+链接、时间），零生成式文本，不编造。
  2. llm 模式（设置 LLM_API_KEY 后自动启用）：OpenAI 兼容接口成稿，提示词强制
     "只使用提供的事实、必须引用来源、禁止编造数字/引语"，输出结构化 JSON。

两种模式输出同一 schema（site/lib/content.ts 的 Briefing），可直接被站点消费。
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

import requests

from .fetch_trends import Trend
from .opportunity_filter import slugify

LLM_TIMEOUT = 120


def llm_config() -> dict | None:
    key = os.environ.get("LLM_API_KEY", "").strip()
    if not key:
        return None
    return {
        "api_key": key,
        "base_url": os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/"),
        "model": os.environ.get("LLM_MODEL", "gpt-4o-mini"),
    }


def llm_configs() -> list[dict]:
    """生成用供应商链：主力 + 可选备用（LLM_FALLBACK_*），依次尝试。

    全部失败时 generate() 回退确定性 briefing 模式，24/7 无人值守不中断。
    """
    configs = []
    primary = llm_config()
    if primary:
        configs.append(primary)
    fb_key = os.environ.get("LLM_FALLBACK_API_KEY", "").strip()
    if fb_key:
        configs.append({
            "api_key": fb_key,
            "base_url": os.environ.get("LLM_FALLBACK_BASE_URL", "https://api.openai.com/v1").rstrip("/"),
            "model": os.environ.get("LLM_FALLBACK_MODEL", "gpt-4o-mini"),
        })
    return configs


def _fmt_traffic(n: int | None) -> str:
    return f"{n:,}" if n else "an unreported number of"


def _facts_block(t: Trend) -> dict:
    """给 LLM 的唯一事实来源；也是审计记录的一部分。"""
    return {
        "keyword": t.keyword,
        "region": t.geo,
        "google_reported_search_lower_bound": t.traffic_lower_bound,
        "trend_feed_published_at": t.pub_date,
        "snapshot_taken_at_utc": t.snapshot_utc,
        "news_coverage": [{"title": n.title, "source": n.source, "url": n.url} for n in t.news],
    }


def generate_briefing(t: Trend, category: str) -> dict:
    """确定性简报模式：模板只填入 RSS 事实，无任何推测性语句。"""
    now = datetime.now(timezone.utc)
    date_h = now.strftime("%B %d, %Y")
    slug = f"{now.strftime('%Y-%m-%d')}-{slugify(t.keyword)}"
    traffic_s = _fmt_traffic(t.traffic_lower_bound)
    outlets = sorted({n.source for n in t.news})

    sections = [
        {
            "heading": f"What is trending: “{t.keyword}”",
            "paragraphs": [
                f"“{t.keyword}” appeared on Google Trends' Trending Now list for {t.geo} "
                f"(snapshot taken {t.snapshot_utc} UTC). Google reports at least {traffic_s} "
                f"searches for this term — that figure is a lower bound published in the official "
                f"Trends feed, not an exact count.",
            ],
        },
        {
            "heading": "What's behind the spike — the coverage",
            "paragraphs": [
                f"The Trends feed associates this search spike with {len(t.news)} news "
                f"{'story' if len(t.news) == 1 else 'stories'} from "
                f"{', '.join(outlets)}. The headlines, exactly as published:",
            ],
            "list": [f"“{n.title}” — {n.source}" for n in t.news],
        },
        {
            "heading": "Timeline",
            "paragraphs": [
                f"The trend entry was published to the Google Trends feed at {t.pub_date or 'an unspecified time'}. "
                f"Our snapshot was taken at {t.snapshot_utc} UTC and this briefing was assembled at "
                f"{now.isoformat(timespec='seconds')} UTC.",
            ],
        },
        {
            "heading": "How to read these numbers",
            "paragraphs": [
                "Google Trends reports approximate search volume as a lower bound (for example "
                "“20K+”). Actual volume can be significantly higher. Trending status reflects "
                "acceleration in searches, not the absolute size of a topic. For the full story "
                "behind the spike, read the cited coverage below — this briefing intentionally "
                "adds no speculation beyond the sourced facts.",
            ],
        },
    ]

    faq = [
        {
            "q": f"Why is “{t.keyword}” trending?",
            "a": (
                f"Google's Trending Now feed links the spike to coverage from {', '.join(outlets)}. "
                f"The associated headline{'s are' if len(t.news) > 1 else ' is'}: "
                + "; ".join(f"“{n.title}” ({n.source})" for n in t.news[:3])
                + "."
            ),
        },
        {
            "q": f"How many people searched for “{t.keyword}”?",
            "a": (
                f"Google reports at least {traffic_s} searches in {t.geo} as of the feed snapshot. "
                f"This is a published lower bound, not an exact count."
            ),
        },
        {
            "q": f"Where is “{t.keyword}” trending?",
            "a": f"This snapshot covers {t.geo}. The same term may trend differently in other regions.",
        },
    ]

    title = f"Why “{t.keyword}” is trending in {t.geo}: {traffic_s}+ searches, the facts ({date_h})"
    description = (
        f"“{t.keyword}” is trending in {t.geo} with {traffic_s}+ searches reported by Google. "
        f"The verified coverage behind the spike, from {outlets[0]}"
        + (f" and {len(outlets) - 1} more" if len(outlets) > 1 else "")
        + "."
    )

    return {
        "slug": slug,
        "title": title[:140],
        "description": description[:300],
        "keyword": t.keyword,
        "geo": t.geo,
        "trafficLowerBound": t.traffic_lower_bound,
        "category": category,
        "mode": "briefing",
        "publishedAt": now.isoformat(timespec="seconds"),
        "updatedAt": now.isoformat(timespec="seconds"),
        "sources": [{"title": n.title, "url": n.url, "source": n.source} for n in t.news],
        "sections": sections,
        "faq": faq,
        "facts": _facts_block(t),
    }


LLM_SYSTEM_PROMPT = """You are a fact-restricted news briefing writer. You will receive a JSON facts block \
about a trending search term. Write a short briefing article in English.

HARD RULES (violating any means your output is rejected):
1. Use ONLY facts present in the facts block. Do not add numbers, quotes, names, dates or events that are not in it.
2. Attribute every claim about the news to its named source (e.g. "according to <source>").
3. You may explain general, timeless background about how Google Trends works, but nothing topical beyond the facts block.
4. No medical, financial, legal or betting advice. Neutral, respectful tone.
5. Output VALID JSON only, matching exactly this schema:
{"title": str (<=120 chars, must mention the keyword),
 "description": str (50-250 chars),
 "sections": [{"heading": str, "paragraphs": [str, ...], "list": [str, ...] (optional)}, ...] (3-6 sections),
 "faq": [{"q": str, "a": str}, ...] (2-4 items)}"""


def generate_llm(t: Trend, category: str, cfg: dict) -> dict:
    """LLM 成稿模式：结构化提示词 + 事实块，输出与 briefing 模式相同 schema。"""
    facts = _facts_block(t)
    resp = requests.post(
        f"{cfg['base_url']}/chat/completions",
        headers={"Authorization": f"Bearer {cfg['api_key']}", "Content-Type": "application/json"},
        json={
            "model": cfg["model"],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": LLM_SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(facts, ensure_ascii=False)},
            ],
        },
        timeout=LLM_TIMEOUT,
    )
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"]["content"]
    draft = json.loads(content)

    now = datetime.now(timezone.utc)
    return {
        "slug": f"{now.strftime('%Y-%m-%d')}-{slugify(t.keyword)}",
        "title": str(draft["title"])[:140],
        "description": str(draft["description"])[:300],
        "keyword": t.keyword,
        "geo": t.geo,
        "trafficLowerBound": t.traffic_lower_bound,
        "category": category,
        "mode": "llm",
        "publishedAt": now.isoformat(timespec="seconds"),
        "updatedAt": now.isoformat(timespec="seconds"),
        "sources": [{"title": n.title, "url": n.url, "source": n.source} for n in t.news],
        "sections": draft["sections"],
        "faq": draft["faq"],
        "facts": facts,
    }


def generate(t: Trend, category: str) -> dict:
    for cfg in llm_configs():
        try:
            return generate_llm(t, category, cfg)
        except Exception as exc:
            print(f"[generate] LLM ({cfg['model']}) failed for '{t.keyword}' ({exc}); trying next")
    return generate_briefing(t, category)
