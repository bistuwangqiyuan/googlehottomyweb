# -*- coding: utf-8 -*-
"""
publish.py — 发布：把通过审核的内容写入 site/content/briefings/，
并把每条决策追加到 site/content/audit/pipeline_log.json（/admin 后台可见）。

发布到线上由 git 提交驱动：GitHub Actions 工作流在流水线跑完后 commit+push，
Vercel 检测到推送自动构建部署。零数据库、全程可审计。
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

AUDIT_CAP = 1000


def write_article(article: dict, content_dir: Path) -> Path:
    content_dir.mkdir(parents=True, exist_ok=True)
    out = content_dir / f"{article['slug']}.json"
    out.write_text(json.dumps(article, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def append_audit(entries: list[dict], audit_dir: Path) -> Path:
    audit_dir.mkdir(parents=True, exist_ok=True)
    log_path = audit_dir / "pipeline_log.json"
    existing: list[dict] = []
    if log_path.exists():
        try:
            existing = json.loads(log_path.read_text(encoding="utf-8"))
        except Exception:
            existing = []
    existing.extend(entries)
    log_path.write_text(
        json.dumps(existing[-AUDIT_CAP:], ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return log_path


def audit_entry(keyword: str, geo: str, decision: str, reason: str, slug: str | None = None) -> dict:
    e = {
        "runAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "keyword": keyword,
        "geo": geo,
        "decision": decision,
        "reason": reason,
    }
    if slug:
        e["slug"] = slug
    return e
