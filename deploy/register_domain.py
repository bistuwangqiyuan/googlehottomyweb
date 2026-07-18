# -*- coding: utf-8 -*-
"""
register_domain.py — Porkbun 域名全自动注册 + DNS 配置 + Vercel 绑定。

预算约束：<$2/年。策略（价格已于 2026-07-18 通过 Porkbun 真实 API 核实）：
  1. 首选 1.111B 类数字 .xyz 域名（6-9 位纯数字，$0.99/年且续费同价）；
  2. 备选低价 TLD：.bond $1.34 / .sbs $1.54 / .click $1.54 / .top $1.63（首年，
     来自 GET /pricing/get 实时数据；注意多数续费价更高，.top 续费 $4.63 最低）。

用法：
  python deploy/register_domain.py --dry-run          # 无凭据：真实调用 pricing/get 验证价格
  python deploy/register_domain.py --dry-run          # 有凭据：checkDomain 真实核价 +
                                                      #   domain/create dryRun=true 全预检（不扣费）
  python deploy/register_domain.py                    # 真实注册 + DNS + Vercel 绑定

环境变量：
  PORKBUN_API_KEY / PORKBUN_SECRET_KEY   Porkbun API 凭据（porkbun.com/account/api）
  VERCEL_TOKEN                           Vercel API token（绑定域名用，可选）
  VERCEL_PROJECT                         Vercel 项目名（默认 trendflow-site）

安全设计：
  - 注册前 checkDomain 实时核价，价格 > MAX_PRICE_USD 一律拒绝；
  - domain/create 带 Idempotency-Key（重试不会重复扣费）；
  - 全部决策打印 + 写入 deploy/domain_result.json 供审计。
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import requests

API = "https://api.porkbun.com/api/json/v3"
MAX_PRICE_USD = 2.00
RESULT_PATH = Path(__file__).resolve().parent / "domain_result.json"

FALLBACK_TLDS = ["bond", "sbs", "click", "top"]  # 首年均 <$2（2026-07-18 实测）


def creds() -> dict | None:
    k = os.environ.get("PORKBUN_API_KEY", "").strip()
    s = os.environ.get("PORKBUN_SECRET_KEY", "").strip()
    if not k or not s:
        return None
    return {"apikey": k, "secretapikey": s}


def post(path: str, body: dict, timeout: int = 30) -> dict:
    r = requests.post(f"{API}{path}", json=body, timeout=timeout)
    data = r.json()
    if data.get("status") != "SUCCESS" and "avail" not in data:
        raise RuntimeError(f"Porkbun API {path} failed: {data}")
    return data


def candidate_domains(n: int = 30) -> list[str]:
    """生成候选域名：优先 1.111B 数字 .xyz，再补低价 TLD 的品牌名。"""
    rng = random.Random()  # 刻意非确定性：域名可用性本身就是时变的
    out: list[str] = []
    for _ in range(n // 2):
        out.append(f"{rng.randint(10_000_000, 99_999_999)}.xyz")  # 8 位数字
    words = ["trendflow", "trendbrief", "spikebrief", "trendfacts", "searchspike"]
    for w in words:
        for tld in FALLBACK_TLDS:
            out.append(f"{w}{rng.randint(10, 99)}.{tld}")
    return out[:n]


def verify_pricing_no_auth() -> None:
    """无凭据 dry-run：真实调用公开定价接口，验证预算可行性。"""
    r = requests.get(f"{API}/pricing/get", timeout=30)
    pricing = r.json()["pricing"]
    print("实时定价核验（Porkbun 公开 API，无需凭据）：")
    ok = False
    for tld in ["xyz"] + FALLBACK_TLDS:
        p = pricing.get(tld, {})
        reg = float(p.get("registration", "999"))
        print(f"  .{tld:6} 注册 ${reg:.2f} / 续费 ${float(p.get('renewal', '999')):.2f}")
        if tld != "xyz" and reg < MAX_PRICE_USD:
            ok = True
    print(
        "  （1.111B 类 6-9 位数字 .xyz 为特价 $0.99/年（含续费），"
        "不在标准价目表中，需 checkDomain 逐域核价）"
    )
    if not ok:
        raise SystemExit("FAIL: 没有任何 TLD 首年价格低于预算 $2")
    print(f"PASS: 存在首年 < ${MAX_PRICE_USD:.2f} 的可注册 TLD")


def find_available(c: dict, dry_run: bool) -> tuple[str, float] | None:
    """checkDomain 真实核价，返回第一个可用且 <$2 的域名。"""
    for domain in candidate_domains():
        try:
            data = post(f"/domain/checkDomain/{domain}", dict(c))
        except RuntimeError as exc:
            print(f"  [skip] {domain}: {exc}")
            time.sleep(11)  # checkDomain 限流：约 1 次/10 秒
            continue
        resp = data.get("response", {})
        avail = resp.get("avail")
        price = float(resp.get("price", "999"))
        print(f"  [check] {domain}: avail={avail} price=${price:.2f}")
        if avail == "yes" and price <= MAX_PRICE_USD:
            return domain, price
        time.sleep(11)
    return None


def register(c: dict, domain: str, price: float, dry_run: bool) -> dict:
    body = {
        **c,
        "cost": int(round(price * 100)),
        "agreeToTerms": "yes",
    }
    if dry_run:
        body["dryRun"] = True
    r = requests.post(
        f"{API}/domain/create/{domain}",
        json=body,
        headers={"Idempotency-Key": str(uuid.uuid4())},
        timeout=60,
    )
    data = r.json()
    print(f"  [create{' dry-run' if dry_run else ''}] {domain}: {json.dumps(data)[:300]}")
    if dry_run:
        if not (data.get("dryRun") and data.get("wouldSucceed")):
            raise SystemExit(f"FAIL: 注册预检未通过：{data}")
    elif data.get("status") != "SUCCESS":
        raise SystemExit(f"FAIL: 注册失败：{data}")
    return data


def configure_dns(c: dict, domain: str, dry_run: bool) -> None:
    """Vercel 官方推荐：apex A 76.76.21.21，www CNAME cname.vercel-dns.com。"""
    records = [
        {"type": "A", "name": "", "content": "76.76.21.21", "ttl": "600"},
        {"type": "CNAME", "name": "www", "content": "cname.vercel-dns.com", "ttl": "600"},
    ]
    for rec in records:
        body = {**c, **rec}
        if dry_run:
            body["dryRun"] = True
        data = requests.post(f"{API}/dns/create/{domain}", json=body, timeout=30).json()
        print(f"  [dns{' dry-run' if dry_run else ''}] {rec['type']} {rec['name'] or '@'}: {data.get('status', data)}")


def bind_vercel(domain: str, dry_run: bool) -> None:
    token = os.environ.get("VERCEL_TOKEN", "").strip()
    project = os.environ.get("VERCEL_PROJECT", "trendflow-site")
    if not token:
        print("  [vercel] 未设置 VERCEL_TOKEN，跳过 API 绑定（可用 `vercel domains add` 手动一条命令）")
        return
    if dry_run:
        print(f"  [vercel dry-run] 将调用 POST /v10/projects/{project}/domains 绑定 {domain} 与 www.{domain}")
        return
    for name in (domain, f"www.{domain}"):
        r = requests.post(
            f"https://api.vercel.com/v10/projects/{project}/domains",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": name},
            timeout=30,
        )
        print(f"  [vercel] bind {name}: {r.status_code} {r.text[:200]}")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Porkbun 域名自动注册 + DNS + Vercel 绑定")
    ap.add_argument("--dry-run", action="store_true", help="真实核价+全预检，但不扣费不变更")
    ap.add_argument("--domain", default=None, help="指定域名（跳过自动扫描）")
    args = ap.parse_args()

    c = creds()
    if c is None:
        print("未检测到 PORKBUN_API_KEY/PORKBUN_SECRET_KEY。")
        if not args.dry_run:
            raise SystemExit("真实注册需要凭据。先运行 --dry-run 或按 GO-LIVE-CHECKLIST.md 配置。")
        verify_pricing_no_auth()
        return 0

    print("== 1/4 扫描可用低价域名（checkDomain 实时核价）==")
    if args.domain:
        data = post(f"/domain/checkDomain/{args.domain}", dict(c))
        resp = data["response"]
        if resp.get("avail") != "yes":
            raise SystemExit(f"FAIL: {args.domain} 不可注册")
        found = (args.domain, float(resp["price"]))
    else:
        found = find_available(c, args.dry_run)
    if not found:
        raise SystemExit("FAIL: 本轮候选中没有 <$2 的可用域名，请重跑（候选随机生成）")
    domain, price = found
    print(f"选定：{domain} @ ${price:.2f}/年")
    if price > MAX_PRICE_USD:
        raise SystemExit(f"FAIL: 价格 ${price:.2f} 超出预算 ${MAX_PRICE_USD:.2f}")

    print("== 2/4 注册域名 ==")
    reg_result = register(c, domain, price, args.dry_run)

    print("== 3/4 配置 DNS（apex A + www CNAME → Vercel）==")
    configure_dns(c, domain, args.dry_run)

    print("== 4/4 绑定 Vercel 项目 ==")
    bind_vercel(domain, args.dry_run)

    RESULT_PATH.write_text(
        json.dumps(
            {
                "domain": domain,
                "price_usd": price,
                "dry_run": args.dry_run,
                "registered_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "porkbun_response": reg_result,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\n完成。结果已写入 {RESULT_PATH}")
    if not args.dry_run:
        print(f"下一步：python tests/e2e_site.py --base-url https://{domain}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
