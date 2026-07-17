# -*- coding: utf-8 -*-
"""
05_unit_economics.py — 单位经济模型：单篇内容成本、单站月度损益、SaaS 单客经济

所有输入参数注明来源（SOURCES.md 编号）或标注为假设（H 编号），
三情景（保守/基准/乐观）覆盖参数不确定性。

产出：
    data/unit_economics.json
    assets/site_breakeven.png   单站月度损益与回本曲线
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
ASSETS = ROOT / "assets"

# ---------------------------------------------------------------------------
# 1) 单篇内容的直接成本（自动化流水线 + 人工编辑关口）
# ---------------------------------------------------------------------------
# LLM 用量假设（H7）：一篇 1,800 词成稿，多轮流水线（调研摘要→草稿→事实核对→SEO/GEO 优化）
# 合计约 60K 输入 + 15K 输出 token（含重试冗余），采用中间层模型价格 [S26]
LLM_IN_TOK, LLM_OUT_TOK = 60_000, 15_000
LLM_PRICE = {  # 每百万 token 美元 [S26]
    "budget": {"in": 0.10, "out": 0.40},    # 经济层（Gemini Flash-Lite / GPT Nano 级）
    "mid": {"in": 3.00, "out": 15.00},      # 中间层（Claude Sonnet 级）
}
# 人工编辑关口（H8）：编辑审核+事实抽查，每篇 15 分钟，编辑时薪 $30（美国自由编辑市价量级）
EDITOR_MIN_PER_ARTICLE = 15
EDITOR_HOURLY = 30.0
# 图片/结构化数据等杂项（H9）
MISC_PER_ARTICLE = 0.50


def article_cost(tier: str) -> dict:
    p = LLM_PRICE[tier]
    llm = LLM_IN_TOK / 1e6 * p["in"] + LLM_OUT_TOK / 1e6 * p["out"]
    editor = EDITOR_MIN_PER_ARTICLE / 60 * EDITOR_HOURLY
    return {
        "llm_usd": round(llm, 3),
        "editor_usd": round(editor, 2),
        "misc_usd": MISC_PER_ARTICLE,
        "total_usd": round(llm + editor + MISC_PER_ARTICLE, 2),
    }


# ---------------------------------------------------------------------------
# 2) 单站月度损益（36 个月爬坡）
# ---------------------------------------------------------------------------
# 站点固定成本（H10）：域名摊销 + 托管 + CDN + 必备工具分摊，每站每月
SITE_FIXED_MONTHLY = 60.0
ARTICLES_PER_MONTH = 60  # H11：每站每月 60 篇（每天 2 篇，编辑关口可承受）

# 流量爬坡（H12，关键假设）：新站自然流量典型爬坡为 6-12 个月起量。
# 采用逻辑斯蒂曲线：第 t 月每篇存量文章平均带来的月度页面浏览数。
# 情景锚点：成熟期（月 24+）每篇文章月均 PV —— 保守 40 / 基准 120 / 乐观 300。
# 依据：热词内容有时效衰减（见 lifecycle 分析），但常青化改写可保留长尾；
#       行业无公开权威基准，此为经营假设，由阶段一实盘校准。
SCENARIOS = {
    "conservative": {"mature_pv_per_article": 40, "rpm": 8.0,  "ramp_mid": 14, "ramp_k": 0.35},
    "base":         {"mature_pv_per_article": 120, "rpm": 15.0, "ramp_mid": 11, "ramp_k": 0.40},
    "optimistic":   {"mature_pv_per_article": 300, "rpm": 25.0, "ramp_mid": 9,  "ramp_k": 0.45},
}
# rpm 依据 [S14][S15]：AdSense 阶段 $3–12，达到 Mediavine 门槛后 $15–40；
# 保守 8 = 长期停留在 AdSense 中位；基准 15 = 第二年进入 Mediavine 低位；乐观 25 = 中高位。


def logistic(t: float, mid: float, k: float) -> float:
    import math
    return 1.0 / (1.0 + math.exp(-k * (t - mid)))


def site_pnl(scn: dict, months: int = 36, tier: str = "budget") -> list[dict]:
    ac = article_cost(tier)["total_usd"]
    rows = []
    cum = 0.0
    for t in range(1, months + 1):
        stock = ARTICLES_PER_MONTH * t  # 累计文章存量
        pv_per_article = scn["mature_pv_per_article"] * logistic(t, scn["ramp_mid"], scn["ramp_k"])
        pv = stock * pv_per_article
        revenue = pv / 1000 * scn["rpm"]
        cost = SITE_FIXED_MONTHLY + ARTICLES_PER_MONTH * ac
        profit = revenue - cost
        cum += profit
        rows.append(
            {
                "month": t, "articles_stock": stock, "monthly_pv": round(pv),
                "revenue": round(revenue, 2), "cost": round(cost, 2),
                "profit": round(profit, 2), "cum_profit": round(cum, 2),
            }
        )
    return rows


# ---------------------------------------------------------------------------
# 3) SaaS 单客经济（阶段二）
# ---------------------------------------------------------------------------
SAAS = {
    # 定价对标 [S20][S24][S25]：Exploding Topics $39-249、Surfer $49-299、Otterly $29-489
    "arpu_monthly": 99.0,          # H13：混合 ARPU $99/月（入门 $49 / 专业 $149 / 机构 $399）
    "gross_margin": 0.78,          # H14：扣除 LLM 推理与基础设施后毛利 78%（LLM 成本见上）
    "monthly_churn": 0.045,        # H15：SMB SaaS 月流失 4.5%（对标 [S29] 中 SMB 工具高流失特征）
    "cac": 350.0,                  # H16：内容驱动获客为主的混合 CAC（自营站群即获客渠道）
}


def saas_unit() -> dict:
    lifetime_months = 1 / SAAS["monthly_churn"]
    ltv = SAAS["arpu_monthly"] * SAAS["gross_margin"] * lifetime_months
    return {
        **SAAS,
        "expected_lifetime_months": round(lifetime_months, 1),
        "ltv_usd": round(ltv, 0),
        "ltv_cac_ratio": round(ltv / SAAS["cac"], 2),
        "cac_payback_months": round(SAAS["cac"] / (SAAS["arpu_monthly"] * SAAS["gross_margin"]), 1),
    }


def main() -> None:
    result = {
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "article_cost": {tier: article_cost(tier) for tier in LLM_PRICE},
        "assumptions_note": "H7-H16 为经营假设，来源锚点见脚本内注释与 SOURCES.md",
        "site_scenarios": {},
        "saas_unit_economics": saas_unit(),
    }

    curves = {}
    for name, scn in SCENARIOS.items():
        rows = site_pnl(scn)
        curves[name] = rows
        breakeven = next((r["month"] for r in rows if r["cum_profit"] > 0), None)
        result["site_scenarios"][name] = {
            "params": scn,
            "monthly_breakeven_month": next((r["month"] for r in rows if r["profit"] > 0), None),
            "cumulative_breakeven_month": breakeven,
            "month12": rows[11], "month24": rows[23], "month36": rows[35],
        }

    (DATA / "unit_economics.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
    colors = {"conservative": "#c0504d", "base": "#4878a8", "optimistic": "#6aa84f"}
    zh = {"conservative": "保守", "base": "基准", "optimistic": "乐观"}
    for name, rows in curves.items():
        ax1.plot([r["month"] for r in rows], [r["profit"] for r in rows],
                 color=colors[name], label=f"{zh[name]}（RPM={SCENARIOS[name]['rpm']}）")
        ax2.plot([r["month"] for r in rows], [r["cum_profit"] for r in rows], color=colors[name], label=zh[name])
    for ax, title in ((ax1, "单站月度利润（美元）"), (ax2, "单站累计利润（美元）")):
        ax.axhline(0, color="gray", lw=0.8, ls="--")
        ax.set_xlabel("月份")
        ax.set_title(title)
        ax.legend()
    fig.suptitle("单站 36 个月损益（每月 60 篇，经济层 LLM + 编辑关口）")
    fig.tight_layout()
    fig.savefig(ASSETS / "site_breakeven.png", dpi=150)

    print(json.dumps({k: v for k, v in result.items() if k != "site_scenarios"}, ensure_ascii=False, indent=2))
    for name, s in result["site_scenarios"].items():
        print(f"\n[{name}] 月度盈亏平衡: 第{s['monthly_breakeven_month']}月, "
              f"累计回本: 第{s['cumulative_breakeven_month']}月, "
              f"36月单月利润: ${s['month36']['profit']}")
    print("\n写出：data/unit_economics.json, assets/site_breakeven.png")


if __name__ == "__main__":
    main()
