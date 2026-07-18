# -*- coding: utf-8 -*-
"""
06_financial_model.py — 公司级 36 个月财务模型（三情景，月度现金流）

结构：
  阶段一（月 1–12）：自营站组合（滚动开站）+ 引擎研发
  阶段门槛（月 12 评估，客观可检验；阈值取基准情景月 12 产出的约 60%，
  即"达到基准轨迹的六成即可继续"，避免用无法达到的标准自欺）：
    G1: 组合月自然 PV >= 100,000（基准情景月12为 ~170K，见模型输出）
    G2: 组合月收入 >= $1,500（基准情景月12为 ~$2,554）
    G3: 近 3 个月组合 PV 月环比增速 >= 25%（确认仍在爬坡而非见顶）
  阶段二（月 13–36）：
    达标 -> SaaS 上线（基准/乐观情景）
    未达标 -> 有序收缩：停止新内容生产、团队降至维护规模、保留存量站点现金流
             （保守情景演示该止损分支——这正是阶段门槛的资本保护价值）

获客成本处理：SaaS 营销支出 = 新客数 × CAC（不另设营销费科目，避免重复计算）。

输入参数继承 05_unit_economics.py 的单位经济假设（H7-H16）；
新增组织与获客假设 H17-H22（脚本内注明）。

产出：
    data/financial_model.json         三情景年度汇总与关键指标
    data/financial_model_monthly.csv  三情景月度明细
    assets/financial_scenarios.png    收入/现金曲线
"""
import csv
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
ASSETS = ROOT / "assets"

MONTHS = 36
GATE_MONTH = 12

# ---------------- 单站模型（与 05_unit_economics.py 保持一致） ----------------
ARTICLES_PER_MONTH = 60
# 单篇成本直接读取 05 号脚本的输出（budget 层：LLM $0.012 + 编辑 $7.5 + 杂项 $0.5 = $8.01），
# 消除手工抄数导致的参数漂移；若 05 尚未运行则明确报错提示先跑 05。
_UNIT_ECON_PATH = Path(__file__).resolve().parent.parent / "data" / "unit_economics.json"
if not _UNIT_ECON_PATH.exists():
    sys.exit("缺少 data/unit_economics.json，请先运行 scripts/05_unit_economics.py")
ARTICLE_COST = json.loads(_UNIT_ECON_PATH.read_text(encoding="utf-8"))["article_cost"]["budget"]["total_usd"]
SITE_FIXED_MONTHLY = 60.0


def logistic(t, mid, k):
    return 1.0 / (1.0 + math.exp(-k * (t - mid)))


# ---------------- 情景定义 ----------------
SCENARIOS = {
    "conservative": {
        "label": "保守（月12门槛未达标，止损收缩）",
        "mature_pv_per_article": 40, "rpm": 8.0, "ramp_mid": 14, "ramp_k": 0.35,
        "sites_plan": [1, 1, 2, 2, 3, 3, 4, 4, 4, 4, 4, 4],
        "saas_new_customers_m1": 0, "saas_growth": 0.0,
        # H17：验证期团队 3 人（2 创始人低薪 + 1 编辑）
        "payroll_phase1": 18_000,
        # 止损分支：维护模式，1 名兼职维护存量站点
        "payroll_winddown": 4_000, "infra_winddown": 800,
    },
    "base": {
        "label": "基准（门槛达标，月13上线 SaaS）",
        "mature_pv_per_article": 120, "rpm": 15.0, "ramp_mid": 11, "ramp_k": 0.40,
        "sites_plan": [1, 2, 3, 4, 5, 6, 7, 8, 8, 8, 8, 8],
        # H18：SaaS 首月新客 20，月增 12%（自营站群+实盘案例做内容获客）
        "saas_new_customers_m1": 20, "saas_growth": 0.12,
        # H19：阶段一 4 人（$32K/月）；阶段二 6 人（$50K/月，2 工程 1 编辑 1 运营 1 增长 1 客成）
        "payroll_phase1": 32_000, "payroll_phase2": 50_000,
    },
    "optimistic": {
        "label": "乐观（强产品市场匹配）",
        "mature_pv_per_article": 300, "rpm": 25.0, "ramp_mid": 9, "ramp_k": 0.45,
        "sites_plan": [1, 2, 4, 6, 8, 10, 12, 12, 12, 12, 12, 12],
        "saas_new_customers_m1": 40, "saas_growth": 0.18,
        "payroll_phase1": 32_000, "payroll_phase2": 70_000,
    },
}

# ---------------- 阶段门槛（月12评估，三条准则全部满足才通过） ----------------
GATE_PV = 100_000      # G1：组合月自然 PV
GATE_REV = 1_500       # G2：组合月收入（美元）
GATE_GROWTH = 0.25     # G3：近 3 个月组合 PV 月环比增速（几何平均）


def evaluate_gate(pv_history: list[float], rev_m12: float) -> dict:
    """月12门槛判定。pv_history 为月1..12的组合PV；G3 用月9->12 的几何平均环比增速。"""
    pv_m12 = pv_history[GATE_MONTH - 1]
    pv_m9 = pv_history[GATE_MONTH - 4]
    growth = (pv_m12 / pv_m9) ** (1 / 3) - 1 if pv_m9 > 0 else 0.0
    g1, g2, g3 = pv_m12 >= GATE_PV, rev_m12 >= GATE_REV, growth >= GATE_GROWTH
    return {
        "g1_pv": {"value": round(pv_m12), "threshold": GATE_PV, "passed": g1},
        "g2_revenue": {"value": round(rev_m12), "threshold": GATE_REV, "passed": g2},
        "g3_growth_3m_geomean": {"value": round(growth, 4), "threshold": GATE_GROWTH, "passed": g3},
        "passed": g1 and g2 and g3,
    }

# SaaS 单客经济（与 05 一致，H13-H16）
SAAS_ARPU = 99.0
SAAS_GM = 0.78
SAAS_CHURN = 0.045
SAAS_CAC = 350.0

INFRA_MONTHLY = 2_500        # H21：基础设施+工具+数据订阅
INITIAL_CASH = 1_500_000     # H22：种子轮 150 万美元（融资章依据：覆盖基准情景现金低谷×1.3 安全垫）
PAYROLL_WINDDOWN_DEFAULT = 4_000   # 止损分支默认维护成本（情景未单独定义时使用）
INFRA_WINDDOWN_DEFAULT = 800


def run_scenario(name: str, s: dict) -> tuple[list[dict], dict]:
    """返回 (月度明细, 月12门槛判定结果)。门槛由模型内生判定，不再作为情景输入。"""
    rows = []
    cash = INITIAL_CASH
    saas_customers = 0.0
    sites: list[dict] = []   # 每站：{"launch": 月, "stock": 文章存量}
    pv_history: list[float] = []
    gate: dict | None = None
    for m in range(1, MONTHS + 1):
        winddown = gate is not None and not gate["passed"] and m > GATE_MONTH

        # ---- 开站与内容生产 ----
        if m <= len(s["sites_plan"]):
            while len(sites) < s["sites_plan"][m - 1]:
                sites.append({"launch": m, "stock": 0})
        producing = not winddown
        if producing:
            for site in sites:
                site["stock"] += ARTICLES_PER_MONTH

        # ---- 自营组合收入（流量随站龄爬坡，存量冻结则流量停留在冻结存量水平） ----
        portfolio_rev = portfolio_pv = 0.0
        for site in sites:
            age = m - site["launch"] + 1
            pv = site["stock"] * s["mature_pv_per_article"] * logistic(age, s["ramp_mid"], s["ramp_k"])
            portfolio_pv += pv
            portfolio_rev += pv / 1000 * s["rpm"]
        content_cost = len(sites) * ARTICLES_PER_MONTH * ARTICLE_COST if producing else 0.0
        hosting_cost = len(sites) * SITE_FIXED_MONTHLY
        portfolio_cost = content_cost + hosting_cost

        # ---- 月12门槛判定（G1 PV + G2 收入 + G3 近3月环比增速） ----
        pv_history.append(portfolio_pv)
        if m == GATE_MONTH:
            gate = evaluate_gate(pv_history, portfolio_rev)

        # ---- SaaS ----
        saas_rev = saas_cost = new_customers = 0.0
        saas_live = gate is not None and gate["passed"] and m > GATE_MONTH
        if saas_live:
            k = m - GATE_MONTH - 1
            new_customers = s["saas_new_customers_m1"] * (1 + s["saas_growth"]) ** k
            saas_customers = saas_customers * (1 - SAAS_CHURN) + new_customers
            saas_rev = saas_customers * SAAS_ARPU
            saas_cost = saas_rev * (1 - SAAS_GM) + new_customers * SAAS_CAC

        # ---- 组织与共用 ----
        if winddown:
            payroll = s.get("payroll_winddown", PAYROLL_WINDDOWN_DEFAULT)
            infra = s.get("infra_winddown", INFRA_WINDDOWN_DEFAULT)
        elif saas_live:
            payroll, infra = s["payroll_phase2"], INFRA_MONTHLY
        else:
            payroll, infra = s["payroll_phase1"], INFRA_MONTHLY

        revenue = portfolio_rev + saas_rev
        cost = portfolio_cost + saas_cost + payroll + infra
        net = revenue - cost
        cash += net
        rows.append(
            {
                "scenario": name, "month": m, "sites": len(sites),
                "portfolio_pv": round(portfolio_pv), "portfolio_rev": round(portfolio_rev),
                "saas_customers": round(saas_customers, 1), "saas_rev": round(saas_rev),
                "revenue": round(revenue), "cost": round(cost),
                "net": round(net), "cash": round(cash),
            }
        )
    assert gate is not None
    return rows, gate


def main() -> None:
    all_rows = []
    summary = {
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "initial_cash_usd": INITIAL_CASH,
        "stage_gate": {
            "month": GATE_MONTH,
            "criteria": [
                f"G1: 组合月自然 PV >= {GATE_PV:,}（基准轨迹月12约170K的60%）",
                f"G2: 组合月收入 >= ${GATE_REV:,}（基准轨迹月12约$2,554的60%）",
                f"G3: 近3个月组合PV月环比增速（几何平均）>= {GATE_GROWTH:.0%}（确认在爬坡）",
            ],
            "note": "门槛由模型按上述三条准则内生判定（evaluate_gate），各情景判定明细见 scenarios.*.gate",
        },
        "scenarios": {},
    }

    for name, s in SCENARIOS.items():
        rows, gate = run_scenario(name, s)
        all_rows.extend(rows)
        cash_min = min(r["cash"] for r in rows)
        summary["scenarios"][name] = {
            "label": s["label"],
            "gate": gate,
            "revenue_y1": sum(r["revenue"] for r in rows[:12]),
            "revenue_y2": sum(r["revenue"] for r in rows[12:24]),
            "revenue_y3": sum(r["revenue"] for r in rows[24:36]),
            "saas_customers_m36": rows[-1]["saas_customers"],
            "arr_m36": round(rows[-1]["saas_rev"] * 12),
            "portfolio_pv_m12": rows[11]["portfolio_pv"],
            "portfolio_rev_m12": rows[11]["portfolio_rev"],
            "cash_m36": rows[-1]["cash"],
            "cash_trough": cash_min,
            "cash_trough_month": next(r["month"] for r in rows if r["cash"] == cash_min),
            "runway_ok": cash_min > 0,
            "first_cashflow_positive_month": next((r["month"] for r in rows if r["net"] > 0), None),
        }

    with (DATA / "financial_model_monthly.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(all_rows[0].keys()))
        w.writeheader()
        w.writerows(all_rows)
    (DATA / "financial_model.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Noto Sans CJK SC", "PingFang SC", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.5, 5))
    colors = {"conservative": "#c0504d", "base": "#4878a8", "optimistic": "#6aa84f"}
    for name, s in SCENARIOS.items():
        rows = [r for r in all_rows if r["scenario"] == name]
        ax1.plot([r["month"] for r in rows], [r["revenue"] for r in rows], color=colors[name], label=s["label"])
        ax2.plot([r["month"] for r in rows], [r["cash"] for r in rows], color=colors[name], label=s["label"])
    ax1.set_title("月度总收入（美元）")
    ax2.set_title(f"期末现金（美元，期初 ${INITIAL_CASH:,}）")
    ax2.axhline(0, color="black", lw=1)
    for ax in (ax1, ax2):
        ax.axvline(GATE_MONTH, color="gray", ls=":", lw=1)
        ax.set_xlabel("月份（虚线=阶段门槛评估）")
        ax.legend(fontsize=8.5)
    fig.suptitle("公司级 36 个月财务模型（两阶段混合模式，营销支出=新客数×CAC）")
    fig.tight_layout()
    fig.savefig(ASSETS / "financial_scenarios.png", dpi=150)

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print("\n写出：data/financial_model.json, data/financial_model_monthly.csv, assets/financial_scenarios.png")


if __name__ == "__main__":
    main()
