# -*- coding: utf-8 -*-
"""
review.py — 审核关口（内容不通过则不发布，拒绝原因写入审计日志）。

  1. 规则审核（所有内容必过）：来源完整性、结构完整性、长度边界、黑名单复查、
     数字事实落地（正文出现的搜索量必须等于事实块里的数字）。
  2. LLM 独立审核（llm 模式内容必过；由第二模型按 rubric 打分）：
     事实性、来源归属、无夸大、公序良俗。阈值 0.75。

设计原则：briefing 模式为确定性模板（输入即事实），规则审核即可闭环；
llm 模式存在编造风险，必须叠加独立模型审核（双模型关口）。
"""
from __future__ import annotations

import json
import os
import re

import requests

from .opportunity_filter import BLACKLIST, _norm_text

REVIEW_TIMEOUT = 120
LLM_REVIEW_THRESHOLD = 0.75


def review_config() -> dict | None:
    """独立审核配置（原子成套）。

    有 REVIEW_API_KEY 时用完整的 REVIEW_* 三元组；没有时整套借用 LLM_* 三元组，
    并忽略任何残留的部分 REVIEW_* 变量——混搭（如 REVIEW_MODEL + LLM key/base）
    会把不存在的模型名发给错误的厂商端点，必然 400。"""
    review_key = os.environ.get("REVIEW_API_KEY", "").strip()
    if review_key:
        return {
            "api_key": review_key,
            "base_url": (
                os.environ.get("REVIEW_BASE_URL")
                or os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1")
            ).rstrip("/"),
            "model": os.environ.get("REVIEW_MODEL", "gpt-4o"),
        }
    llm_key = os.environ.get("LLM_API_KEY", "").strip()
    if not llm_key:
        return None
    return {
        "api_key": llm_key,
        "base_url": os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/"),
        "model": os.environ.get("LLM_MODEL", "gpt-4o-mini"),
    }


def review_configs() -> list[dict]:
    """审核用供应商链：主审 + 可选备审（REVIEW_FALLBACK_*）。

    全链失败仍然 fail-closed（llm 模式内容一律拒发）。备审可能与生成方
    是同一厂商（仅在主审宕机的降级场景），规则审核与阈值关口不变。
    """
    configs = []
    primary = review_config()
    if primary:
        configs.append(primary)
    fb_key = os.environ.get("REVIEW_FALLBACK_API_KEY", "").strip()
    if fb_key:
        configs.append({
            "api_key": fb_key,
            "base_url": os.environ.get("REVIEW_FALLBACK_BASE_URL", "https://api.openai.com/v1").rstrip("/"),
            "model": os.environ.get("REVIEW_FALLBACK_MODEL", "gpt-4o"),
        })
    return configs


def _article_text(article: dict) -> str:
    parts = [article.get("title", ""), article.get("description", "")]
    for s in article.get("sections", []):
        parts.append(s.get("heading", ""))
        parts.extend(s.get("paragraphs", []))
        parts.extend(s.get("list", []) or [])
    for f in article.get("faq", []):
        parts.append(f.get("q", ""))
        parts.append(f.get("a", ""))
    return "\n".join(parts)


def rules_review(article: dict) -> tuple[bool, float, list[str]]:
    """返回 (approved, score, failures)。所有 critical 检查必须全部通过。"""
    failures: list[str] = []
    checks = 0

    def check(ok: bool, msg: str) -> None:
        nonlocal checks
        checks += 1
        if not ok:
            failures.append(msg)

    sources = article.get("sources", [])
    check(len(sources) >= 1, "no sources cited")
    for s in sources:
        check(
            bool(s.get("title")) and str(s.get("url", "")).startswith("http") and bool(s.get("source")),
            f"incomplete source entry: {s}",
        )

    sections = article.get("sections", [])
    check(3 <= len(sections) <= 8, f"section count {len(sections)} outside [3,8]")
    for s in sections:
        check(bool(s.get("heading")) and len(s.get("paragraphs", [])) >= 1, f"empty section: {s.get('heading')}")

    faq = article.get("faq", [])
    check(2 <= len(faq) <= 6, f"faq count {len(faq)} outside [2,6]")
    for f in faq:
        check(bool(f.get("q")) and bool(f.get("a")), "empty FAQ entry")

    title = article.get("title", "")
    check(10 <= len(title) <= 140, f"title length {len(title)} outside [10,140]")
    desc = article.get("description", "")
    check(40 <= len(desc) <= 300, f"description length {len(desc)} outside [40,300]")

    text = _article_text(article)
    check(400 <= len(text) <= 20_000, f"total text length {len(text)} outside [400,20000]")

    corpus = f" {_norm_text(text)} "
    for rule, terms in BLACKLIST.items():
        for term in terms:
            if f" {_norm_text(term)} " in corpus:
                check(False, f"blacklist re-check {rule}: '{term}' appeared in generated text")

    # 数字落地检查：正文中出现的 4 位以上千分位数字必须能在事实块中找到
    facts = article.get("facts", {})
    fact_numbers = {str(facts.get("google_reported_search_lower_bound") or "")}
    fact_numbers.add(f"{facts.get('google_reported_search_lower_bound') or 0:,}")
    for m in re.finditer(r"\b\d{1,3}(?:,\d{3})+\b", text):
        num = m.group(0)
        check(
            num in fact_numbers or num.replace(",", "") in fact_numbers,
            f"ungrounded number in text: {num}",
        )

    score = (checks - len(failures)) / checks if checks else 0.0
    return len(failures) == 0, round(score, 4), failures


LLM_REVIEW_PROMPT = """You are an independent editorial reviewer. You receive a JSON article draft and \
the facts block it must be grounded in. Score it on this rubric, each 0.0-1.0:
- factuality: every topical claim is present in the facts block (no invented numbers/quotes/events)
- attribution: news claims are attributed to their named sources
- no_exaggeration: neutral tone, no clickbait beyond stating real numbers
- decency: respectful, safe-for-work, no advice in medical/financial/legal/betting domains

Output VALID JSON only: {"factuality": float, "attribution": float, "no_exaggeration": float, \
"decency": float, "overall": float, "verdict": "approve"|"reject", "notes": str}"""


def llm_review(article: dict, cfg: dict) -> tuple[bool, float, str]:
    payload = {
        "draft": {k: article[k] for k in ("title", "description", "sections", "faq", "sources")},
        "facts": article.get("facts", {}),
    }
    resp = requests.post(
        f"{cfg['base_url']}/chat/completions",
        headers={"Authorization": f"Bearer {cfg['api_key']}", "Content-Type": "application/json"},
        json={
            "model": cfg["model"],
            "temperature": 0.0,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": LLM_REVIEW_PROMPT},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
        },
        timeout=REVIEW_TIMEOUT,
    )
    resp.raise_for_status()
    verdict = json.loads(resp.json()["choices"][0]["message"]["content"])
    score = float(verdict.get("overall", 0.0))
    ok = verdict.get("verdict") == "approve" and score >= LLM_REVIEW_THRESHOLD
    return ok, round(score, 4), str(verdict.get("notes", ""))


def review(article: dict) -> dict:
    """完整审核关口。返回 review 块（写入内容 JSON）。"""
    from datetime import datetime, timezone

    rules_ok, rules_score, failures = rules_review(article)
    notes = "; ".join(failures) if failures else "all rules checks passed"
    mode = "rules"
    approved = rules_ok
    score = rules_score

    if article.get("mode") == "llm":
        mode = "llm"
        cfgs = review_configs()
        if not rules_ok:
            approved = False
        elif not cfgs:
            approved = False
            notes = "llm-mode content requires an independent LLM reviewer but no review key configured"
        else:
            approved = False
            last_exc: Exception | None = None
            for cfg in cfgs:
                try:
                    llm_ok, llm_score, llm_notes = llm_review(article, cfg)
                    approved = rules_ok and llm_ok
                    score = round((rules_score + llm_score) / 2, 4)
                    notes = f"rules: {notes} | reviewer({cfg['model']}): {llm_notes}"
                    last_exc = None
                    break
                except Exception as exc:
                    last_exc = exc
            if last_exc is not None:
                approved = False
                notes = f"all llm reviewers unavailable, fail-closed: {last_exc}"

    return {
        "approved": approved,
        "score": score,
        "mode": mode,
        "notes": notes[:1000],
        "reviewedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
