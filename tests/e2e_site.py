# -*- coding: utf-8 -*-
"""
e2e_site.py — 端到端测试套件（本地生产模式与线上同一套断言）。

两种用法：
  1. 全链路本地模式（默认）：可选真实抓取流水线 → next build → next start（生产模式）
     → 全部断言 → 关停。
       python tests/e2e_site.py [--run-pipeline]
  2. 指向任意已运行站点（含真实域名）：
       python tests/e2e_site.py --base-url https://your-domain.xyz

断言清单（与计划书 SEO/GEO 六因子及合规要求对应）：
  - 首页 200、含 >=3 篇简报卡片、响应 < 2s
  - 每篇内容页：200、Article JSON-LD 合法、FAQPage JSON-LD 合法、AI 披露块存在、
    具名来源列表存在、canonical、og:title、响应 < 2s
  - /about 合规披露（AI 使用说明、纠错渠道）、/privacy 200
  - sitemap.xml 合法 XML 且所有 loc 可访问（200）
  - robots.txt 含 Sitemap 与 Disallow: /admin
  - feed.xml 为合法 RSS
  - /admin 未认证返回 401/503（fail-closed）；提供凭据时返回 200
  - 内链无死链；不存在的 slug 返回 404
  - 赞助位合规：页脚赞助位有可见标注 + rel=sponsored + UTM；上下文赞助卡
    当且仅当 ai-infra 类简报出现；/about 有广告与关联关系披露章节

退出码 0 = 全绿。
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlparse

import requests

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
PORT = 3123
RESP_BUDGET_S = 2.0

PASSED: list[str] = []
FAILED: list[tuple[str, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    if ok:
        PASSED.append(name)
        print(f"[PASS] {name}")
    else:
        FAILED.append((name, detail))
        print(f"[FAIL] {name} — {detail}")


def get(base: str, path: str, auth: tuple[str, str] | None = None, timeout: int = 30):
    t0 = time.monotonic()
    r = requests.get(
        base + path, timeout=timeout, auth=auth,
        headers={"User-Agent": "TrendFlowE2E/1.0"}, allow_redirects=True,
    )
    return r, time.monotonic() - t0


def extract_jsonld(html: str) -> list[dict]:
    blocks = re.findall(
        r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL
    )
    out = []
    for b in blocks:
        out.append(json.loads(b))  # 非法 JSON 会抛异常 → 测试失败
    return out


def run_assertions(base: str, admin_user: str | None, admin_pass: str | None) -> None:
    # ---------- 首页 ----------
    r, dt = get(base, "/")
    check("home: 200", r.status_code == 200, f"got {r.status_code}")
    check(f"home: responds < {RESP_BUDGET_S}s", dt < RESP_BUDGET_S, f"{dt:.2f}s")
    briefing_paths = sorted(set(re.findall(r'href="(/briefings/[^"#]+)"', r.text)))
    check("home: >=3 briefing cards", len(briefing_paths) >= 3, f"found {len(briefing_paths)}")
    try:
        lds = extract_jsonld(r.text)
        check("home: WebSite JSON-LD", any(d.get("@type") == "WebSite" for d in lds), str(lds)[:200])
    except Exception as exc:
        check("home: WebSite JSON-LD", False, f"invalid JSON-LD: {exc}")

    # ---------- 页脚赞助位（全站，合规三要素：可见标注 + rel=sponsored + UTM 可归因） ----------
    check("footer sponsor: slot present + labeled",
          'data-testid="footer-sponsor"' in r.text and "Sponsored" in r.text, "missing slot/label")
    check("footer sponsor: rel=sponsored", 'rel="sponsored noopener"' in r.text, "missing rel attr")
    check("footer sponsor: UTM attribution",
          "mingxinstorage.xyz" in r.text and "utm_source=trendflow" in r.text, "missing target/UTM")

    # ---------- 内容页（全部） ----------
    for path in briefing_paths:
        r, dt = get(base, path)
        name = path.rsplit("/", 1)[-1][:48]
        check(f"briefing {name}: 200", r.status_code == 200, f"got {r.status_code}")
        check(f"briefing {name}: < {RESP_BUDGET_S}s", dt < RESP_BUDGET_S, f"{dt:.2f}s")
        try:
            lds = extract_jsonld(r.text)
            types = {d.get("@type") for d in lds}
            check(f"briefing {name}: Article JSON-LD", "Article" in types, str(types))
            check(f"briefing {name}: FAQPage JSON-LD", "FAQPage" in types, str(types))
            art = next(d for d in lds if d.get("@type") == "Article")
            check(
                f"briefing {name}: Article LD has headline+dates+citation",
                bool(art.get("headline")) and bool(art.get("datePublished")) and bool(art.get("citation")),
                json.dumps(art)[:200],
            )
        except Exception as exc:
            check(f"briefing {name}: JSON-LD valid", False, str(exc))
        check(f"briefing {name}: AI disclosure block", 'data-testid="ai-disclosure"' in r.text, "missing")
        # 上下文赞助卡：当且仅当 ai-infra 类简报才出现，且必须带标注 + rel=sponsored
        has_card = 'data-testid="sponsor-card"' in r.text
        is_ai_infra = ">ai-infra<" in r.text
        check(f"briefing {name}: sponsor card iff ai-infra category",
              has_card == is_ai_infra, f"card={has_card}, ai-infra={is_ai_infra}")
        if has_card:
            check(f"briefing {name}: sponsor card labeled + rel=sponsored",
                  "Sponsored · Affiliated" in r.text and 'rel="sponsored noopener"' in r.text,
                  "missing label or rel attr")
        check(f"briefing {name}: named sources section", "Named sources" in r.text, "missing")
        check(f"briefing {name}: canonical link", 'rel="canonical"' in r.text, "missing")
        check(f"briefing {name}: og:title", 'property="og:title"' in r.text, "missing")

    # ---------- 合规页面 ----------
    r, _ = get(base, "/about")
    check("about: 200", r.status_code == 200, f"got {r.status_code}")
    check("about: AI usage disclosed", "AI" in r.text and "Review gate" in r.text or "review gate" in r.text, "missing disclosure wording")
    check("about: corrections channel", "corrections" in r.text.lower(), "missing corrections section")
    check("about: advertising & affiliation disclosure",
          'id="advertising"' in r.text and "MingXin" in r.text and "affiliated" in r.text.lower(),
          "missing advertising disclosure section")
    r, _ = get(base, "/privacy")
    check("privacy: 200", r.status_code == 200, f"got {r.status_code}")

    # ---------- SEO 基础设施 ----------
    r, _ = get(base, "/sitemap.xml")
    check("sitemap: 200", r.status_code == 200, f"got {r.status_code}")
    locs: list[str] = []
    try:
        tree = ET.fromstring(r.content)
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        locs = [e.text or "" for e in tree.findall(".//sm:loc", ns)]
        check("sitemap: valid XML with locs", len(locs) >= 4, f"{len(locs)} locs")
    except Exception as exc:
        check("sitemap: valid XML with locs", False, str(exc))
    base_host = urlparse(base).netloc
    for loc in locs:
        p = urlparse(loc)
        path = p.path or "/"
        r2, _ = get(base, path)
        check(f"sitemap loc reachable: {path}", r2.status_code == 200, f"got {r2.status_code}")
        check(f"sitemap loc host consistent: {path}", p.netloc == base_host or not p.netloc,
              f"loc host {p.netloc} != {base_host}")

    r, _ = get(base, "/robots.txt")
    check("robots: 200", r.status_code == 200, f"got {r.status_code}")
    check("robots: has Sitemap", "Sitemap:" in r.text, r.text[:200])
    check("robots: disallows /admin", re.search(r"Disallow:\s*/admin", r.text) is not None, r.text[:200])

    r, _ = get(base, "/feed.xml")
    check("rss: 200", r.status_code == 200, f"got {r.status_code}")
    try:
        tree = ET.fromstring(r.content)
        check("rss: valid RSS with items", tree.tag == "rss" and len(tree.findall(".//item")) >= 1, tree.tag)
    except Exception as exc:
        check("rss: valid RSS with items", False, str(exc))

    # ---------- /admin 关口 ----------
    r, _ = get(base, "/admin")
    check("admin: fail-closed without auth", r.status_code in (401, 503), f"got {r.status_code}")
    if admin_user and admin_pass:
        r, _ = get(base, "/admin", auth=(admin_user, admin_pass))
        check("admin: 200 with credentials", r.status_code == 200, f"got {r.status_code}")
        check("admin: shows audit log", "Pipeline audit log" in r.text, "missing audit table")

    # ---------- 死链与 404 ----------
    r, _ = get(base, "/")
    internal = sorted({
        h for h in re.findall(r'href="(/[^"#]*)"', r.text)
        if not h.startswith("/admin")
    })
    for h in internal:
        r2, _ = get(base, h)
        check(f"no dead link: {h}", r2.status_code == 200, f"got {r2.status_code}")
    r, _ = get(base, "/briefings/this-slug-does-not-exist")
    check("unknown slug returns 404", r.status_code == 404, f"got {r.status_code}")


def start_local_server(env_extra: dict) -> subprocess.Popen:
    import os
    env = {**os.environ, **env_extra}
    next_bin = SITE / "node_modules" / "next" / "dist" / "bin" / "next"
    proc = subprocess.Popen(
        ["node", str(next_bin), "start", "-p", str(PORT)],
        cwd=SITE, env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        try:
            if requests.get(f"http://localhost:{PORT}/", timeout=3).status_code < 500:
                return proc
        except Exception:
            pass
        time.sleep(1)
    proc.kill()
    raise RuntimeError("next start did not become ready within 60s")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="TrendFlow E2E suite")
    ap.add_argument("--base-url", default=None, help="测试已运行的站点（本地或真实域名）")
    ap.add_argument("--run-pipeline", action="store_true", help="本地模式下先真实抓取一轮流水线")
    ap.add_argument("--admin-user", default=None)
    ap.add_argument("--admin-pass", default=None)
    args = ap.parse_args()

    import os
    admin_user = args.admin_user or os.environ.get("ADMIN_USER")
    admin_pass = args.admin_pass or os.environ.get("ADMIN_PASS")

    proc: subprocess.Popen | None = None
    try:
        if args.base_url:
            base = args.base_url.rstrip("/")
        else:
            if args.run_pipeline:
                print("== running real content pipeline ==")
                p = subprocess.run(
                    [sys.executable, "-m", "pipeline.run_pipeline", "--max-publish", "5"],
                    cwd=ROOT, timeout=600,
                )
                if p.returncode != 0:
                    print("pipeline failed")
                    return 1
            n_content = len(list((SITE / "content" / "briefings").glob("*.json")))
            if n_content < 3:
                print(f"only {n_content} content files; running pipeline to populate")
                subprocess.run(
                    [sys.executable, "-m", "pipeline.run_pipeline", "--max-publish", "5"],
                    cwd=ROOT, timeout=600, check=True,
                )
            local_admin_user = admin_user or "admin"
            local_admin_pass = admin_pass or "e2e-local-secret"
            admin_user, admin_pass = local_admin_user, local_admin_pass
            env_extra = {
                "NEXT_PUBLIC_SITE_URL": f"http://localhost:{PORT}",
                "ADMIN_USER": local_admin_user,
                "ADMIN_PASS": local_admin_pass,
            }
            print("== next build (production) ==")
            next_bin = SITE / "node_modules" / "next" / "dist" / "bin" / "next"
            b = subprocess.run(
                ["node", str(next_bin), "build"],
                cwd=SITE, env={**os.environ, **env_extra}, timeout=600,
            )
            if b.returncode != 0:
                print("build failed")
                return 1
            print("== next start (production) ==")
            proc = start_local_server(env_extra)
            base = f"http://localhost:{PORT}"

        print(f"== running assertions against {base} ==\n")
        run_assertions(base, admin_user, admin_pass)
    finally:
        if proc:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()

    print(f"\n===== E2E RESULT: {len(PASSED)} passed, {len(FAILED)} failed =====")
    for name, detail in FAILED:
        print(f"  FAILED: {name} — {detail}")
    return 1 if FAILED else 0


if __name__ == "__main__":
    raise SystemExit(main())
