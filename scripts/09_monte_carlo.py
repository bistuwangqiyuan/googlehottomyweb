# -*- coding: utf-8 -*-
"""
09_monte_carlo.py — 关键假设联合分布下的蒙特卡洛风险量化（10,000 次模拟）

模型结构与 06_financial_model.py 完全一致（基准情景的开站计划 + 月12阶段门槛 +
达标上SaaS/未达标止损收缩），但对 7 个关键参数按概率分布抽样：

  参数            分布                        锚点依据
  ----------------------------------------------------------------------
  H12 成熟期单篇月PV  对数正态 中位120, σ=0.78    P10≈44/P90≈325，覆盖保守40~乐观300
  RPM             三角(8, 15, 25)             [S14][S15] AdSense~Mediavine 带宽
  爬坡中点 ramp_mid 均匀(9, 14)                 新站起量 6-12 个月的经验带（H12 附属）
  H13 ARPU        三角(59, 99, 129)           竞品定价带 [S20][S24][S25]
  H15 月流失       三角(0.03, 0.045, 0.08)     SMB SaaS 基准 3-5%、尾部 8% [S38][S39][S40]
  H18 SaaS月增速   三角(0.04, 0.12, 0.18)      内容驱动获客的增长带（经营假设）
  SaaS首月新客     三角(8, 20, 35)             waitlist 转化的不确定性（经营假设）

阶段门槛（同 06，三条准则全部满足）：月12 组合PV>=100K（G1）且 月收入>=$1,500（G2）
且 近3个月组合PV月环比增速（几何平均）>=25%（G3）→ 上SaaS；否则止损收缩。

产出：
    data/monte_carlo.json        概率结论（供财务章/成功概率章引用）
    assets/mc_distributions.png  ARR 与期末现金分布
    assets/mc_tornado.png        龙卷风敏感性图（单参数 P10/P90 扫描）
"""
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
ASSETS = ROOT / "assets"

N_SIMS = 10_000
MONTHS = 36
GATE_MONTH = 12
SEED = 20260714  # 固定种子保证可复现

# --- 与 06 号模型一致的常量 ---
ARTICLES_PER_MONTH = 60
# 与 06 一致：单篇成本读取 05 号脚本输出，消除手工抄数
_UNIT_ECON_PATH = DATA / "unit_economics.json"
if not _UNIT_ECON_PATH.exists():
    sys.exit("缺少 data/unit_economics.json，请先运行 scripts/05_unit_economics.py")
ARTICLE_COST = json.loads(_UNIT_ECON_PATH.read_text(encoding="utf-8"))["article_cost"]["budget"]["total_usd"]
SITE_FIXED_MONTHLY = 60.0
SITES_PLAN = [1, 2, 3, 4, 5, 6, 7, 8, 8, 8, 8, 8]        # 基准开站计划
SAAS_GM = 0.78
SAAS_CAC = 350.0
INFRA_MONTHLY = 2_500
INITIAL_CASH = 1_500_000
PAYROLL_PHASE1 = 32_000
PAYROLL_PHASE2 = 50_000
PAYROLL_WINDDOWN = 4_000
INFRA_WINDDOWN = 800
GATE_PV = 100_000
GATE_REV = 1_500
GATE_GROWTH = 0.25   # G3：月9->12 组合PV几何平均环比增速阈值（同 06）


def logistic(t, mid, k=0.40):
    return 1.0 / (1.0 + math.exp(-k * (t - mid)))


def simulate(pv_art, rpm, ramp_mid, arpu, churn, growth, m1_customers) -> dict:
    """单次 36 个月模拟，返回关键结果。"""
    cash = INITIAL_CASH
    saas_customers = 0.0
    sites = []           # 每站 [launch_month, stock]
    gate_passed = None
    cash_min = cash
    arr_m36 = rev_m12 = pv_m12 = 0.0
    pv_history = []
    for m in range(1, MONTHS + 1):
        winddown = gate_passed is False and m > GATE_MONTH
        if m <= len(SITES_PLAN):
            while len(sites) < SITES_PLAN[m - 1]:
                sites.append([m, 0])
        producing = not winddown
        if producing:
            for s in sites:
                s[1] += ARTICLES_PER_MONTH

        portfolio_rev = portfolio_pv = 0.0
        for lm, stock in sites:
            age = m - lm + 1
            pv = stock * pv_art * logistic(age, ramp_mid)
            portfolio_pv += pv
            portfolio_rev += pv / 1000 * rpm
        content_cost = len(sites) * ARTICLES_PER_MONTH * ARTICLE_COST if producing else 0.0
        portfolio_cost = content_cost + len(sites) * SITE_FIXED_MONTHLY

        pv_history.append(portfolio_pv)
        if m == GATE_MONTH:
            # 注意 bool()：portfolio_pv 可能是 np.float64，比较结果为 np.bool_，
            # 与 `is True/False` 判断不兼容，必须转为 Python bool
            pv_m9 = pv_history[GATE_MONTH - 4]
            growth_3m = (portfolio_pv / pv_m9) ** (1 / 3) - 1 if pv_m9 > 0 else 0.0
            gate_passed = (
                bool(portfolio_pv >= GATE_PV)
                and bool(portfolio_rev >= GATE_REV)
                and bool(growth_3m >= GATE_GROWTH)   # G3（同 06）
            )
            pv_m12, rev_m12 = float(portfolio_pv), float(portfolio_rev)

        saas_rev = saas_cost = 0.0
        saas_live = gate_passed is True and m > GATE_MONTH
        if saas_live:
            k = m - GATE_MONTH - 1
            new_c = m1_customers * (1 + growth) ** k
            saas_customers = saas_customers * (1 - churn) + new_c
            saas_rev = saas_customers * arpu
            saas_cost = saas_rev * (1 - SAAS_GM) + new_c * SAAS_CAC

        if winddown:
            payroll, infra = PAYROLL_WINDDOWN, INFRA_WINDDOWN
        elif saas_live:
            payroll, infra = PAYROLL_PHASE2, INFRA_MONTHLY
        else:
            payroll, infra = PAYROLL_PHASE1, INFRA_MONTHLY

        cash += (portfolio_rev + saas_rev) - (portfolio_cost + saas_cost + payroll + infra)
        cash_min = min(cash_min, cash)
        if m == MONTHS:
            arr_m36 = saas_rev * 12
    return {
        "gate_passed": bool(gate_passed),
        "pv_m12": pv_m12, "rev_m12": rev_m12,
        "arr_m36": arr_m36, "cash_m36": cash, "cash_min": cash_min,
        "ruin": cash_min < 0,
    }


# ---------------- 参数抽样 ----------------
def draw_params(rng: np.random.Generator, n: int) -> list[tuple]:
    pv_art = np.exp(rng.normal(math.log(120), 0.78, n))          # H12 对数正态
    rpm = rng.triangular(8, 15, 25, n)                            # [S14]
    ramp_mid = rng.uniform(9, 14, n)
    arpu = rng.triangular(59, 99, 129, n)                         # H13
    churn = rng.triangular(0.03, 0.045, 0.08, n)                  # H15 [S38-S40]
    growth = rng.triangular(0.04, 0.12, 0.18, n)                  # H18
    m1c = rng.triangular(8, 20, 35, n)
    return list(zip(pv_art, rpm, ramp_mid, arpu, churn, growth, m1c))


def pct(a, q):
    return float(np.percentile(a, q))


def main() -> None:
    rng = np.random.default_rng(SEED)
    params = draw_params(rng, N_SIMS)
    results = [simulate(*p) for p in params]

    gate = np.array([r["gate_passed"] for r in results])
    ruin = np.array([r["ruin"] for r in results])
    arr36 = np.array([r["arr_m36"] for r in results])
    cash36 = np.array([r["cash_m36"] for r in results])
    cashmin = np.array([r["cash_min"] for r in results])

    passed = gate.astype(bool)
    summary = {
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "n_sims": N_SIMS, "seed": SEED,
        "p_gate_pass": round(float(gate.mean()), 4),
        "p_cash_ever_negative": round(float(ruin.mean()), 4),
        "p_cash_negative_given_pass": round(float(ruin[passed].mean()), 4) if passed.any() else None,
        "arr_m36_usd": {
            "p10": round(pct(arr36, 10)), "p50": round(pct(arr36, 50)), "p90": round(pct(arr36, 90)),
            "p50_given_gate_pass": round(pct(arr36[passed], 50)) if passed.any() else None,
        },
        "cash_m36_usd": {
            "p10": round(pct(cash36, 10)), "p50": round(pct(cash36, 50)), "p90": round(pct(cash36, 90)),
        },
        "cash_m36_given_gate_fail_usd": {
            "p10": round(pct(cash36[~passed], 10)), "p50": round(pct(cash36[~passed], 50)),
            "p90": round(pct(cash36[~passed], 90)),
        } if (~passed).any() else None,
        "cash_trough_usd": {
            "p10": round(pct(cashmin, 10)), "p50": round(pct(cashmin, 50)), "p90": round(pct(cashmin, 90)),
        },
        "p_arr_m36_over_1m": round(float((arr36 >= 1_000_000).mean()), 4),
        "p_arr_m36_over_2m": round(float((arr36 >= 2_000_000).mean()), 4),
        "p_cash_m36_over_initial": round(float((cash36 >= INITIAL_CASH).mean()), 4),
    }

    # ---------------- 龙卷风图：单参数 P10/P90 扫描（其余取中位） ----------------
    med = {
        "pv_art": 120.0, "rpm": 15.0,  # 三角(8,15,25) 中位近似取众数 15
        "ramp_mid": 11.5, "arpu": 99.0, "churn": 0.045, "growth": 0.12, "m1c": 20.0,
    }
    sweeps = {
        "H12 单篇月PV": ("pv_art", math.exp(math.log(120) - 1.2816 * 0.78), math.exp(math.log(120) + 1.2816 * 0.78)),
        "RPM": ("rpm", 9.7, 21.4),                    # 三角(8,15,25) 的 P10/P90 近似
        "爬坡中点(月)": ("ramp_mid", 9.5, 13.5),
        "H13 ARPU": ("arpu", 70.5, 120.4),            # 三角(59,99,129) P10/P90 近似
        "H15 月流失": ("churn", 0.036, 0.068),
        "H18 SaaS增速": ("growth", 0.066, 0.161),
        "SaaS首月新客": ("m1c", 11.6, 30.3),
    }

    def run_with(**over):
        args = {**med, **over}
        return simulate(args["pv_art"], args["rpm"], args["ramp_mid"],
                        args["arpu"], args["churn"], args["growth"], args["m1c"])["arr_m36"]

    base_arr = run_with()
    tornado = []
    for label, (key, lo, hi) in sweeps.items():
        a_lo, a_hi = run_with(**{key: lo}), run_with(**{key: hi})
        tornado.append({"param": label, "arr_low": round(min(a_lo, a_hi)),
                        "arr_high": round(max(a_lo, a_hi)),
                        "span": round(abs(a_hi - a_lo))})
    tornado.sort(key=lambda t: t["span"], reverse=True)
    summary["tornado_arr_m36"] = {"base_case_arr": round(base_arr), "sweeps": tornado}

    (DATA / "monte_carlo.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # ---------------- 图表 ----------------
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Noto Sans CJK SC", "PingFang SC", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.5, 5))
    ax1.hist(arr36 / 1e6, bins=60, color="#4878a8", edgecolor="white")
    ax1.set_xlabel("月36 ARR（百万美元）")
    ax1.set_ylabel("模拟次数")
    ax1.set_title(f"ARR 分布（P10={summary['arr_m36_usd']['p10']/1e6:.2f}M, "
                  f"P50={summary['arr_m36_usd']['p50']/1e6:.2f}M, P90={summary['arr_m36_usd']['p90']/1e6:.2f}M）")
    ax2.hist(cash36 / 1e6, bins=60, color="#6aa84f", edgecolor="white")
    ax2.axvline(INITIAL_CASH / 1e6, color="gray", ls="--", lw=1, label="期初 $1.5M")
    ax2.axvline(0, color="black", lw=1)
    ax2.set_xlabel("月36 期末现金（百万美元）")
    ax2.set_title("期末现金分布")
    ax2.legend()
    fig.suptitle(f"蒙特卡洛 {N_SIMS:,} 次模拟（门槛通过率 {summary['p_gate_pass']:.0%}，"
                 f"现金曾为负概率 {summary['p_cash_ever_negative']:.1%}）")
    fig.tight_layout()
    fig.savefig(ASSETS / "mc_distributions.png", dpi=150)

    fig2, ax = plt.subplots(figsize=(10, 5.5))
    labels = [t["param"] for t in tornado][::-1]
    lows = [t["arr_low"] / 1e6 for t in tornado][::-1]
    highs = [t["arr_high"] / 1e6 for t in tornado][::-1]
    for i, (lo, hi) in enumerate(zip(lows, highs)):
        ax.barh(i, hi - lo, left=lo, color="#4878a8", alpha=0.8)
    ax.axvline(base_arr / 1e6, color="crimson", lw=1.5, label=f"基准 {base_arr/1e6:.2f}M")
    ax.set_yticks(range(len(labels)), labels)
    ax.set_xlabel("月36 ARR（百万美元）")
    ax.set_title("龙卷风敏感性：单参数 P10→P90 扫描（其余参数取中位）")
    ax.legend()
    fig2.tight_layout()
    fig2.savefig(ASSETS / "mc_tornado.png", dpi=150)

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print("\n写出：data/monte_carlo.json, assets/mc_distributions.png, assets/mc_tornado.png")


if __name__ == "__main__":
    main()
