# -*- coding: utf-8 -*-
"""
11_verify_doc_consistency.py — 文档声明与数据文件一致性自动核对

把商业计划书/机会报告正文中的关键计算类数字，逐条与 data/ 下脚本输出
（market_sizing / unit_economics / financial_model / monte_carlo /
lifecycle_summary / trending_now_summary / opportunity_scores / niche_selection）
比对：期望字面值由数据实时计算生成，再断言其出现在指定章节中。
数据变了而文档没更新（或反之）即失败并精确定位。

另含结构性检查：两份"完整版"合并文档必须逐字包含全部分章内容。

用法：python scripts/11_verify_doc_consistency.py
退出码：0 = 全部断言通过；1 = 存在失败。
"""
import json
import sys
from decimal import Decimal, ROUND_HALF_EVEN, ROUND_HALF_UP
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
BP = ROOT / "business-plan"
OR_ = ROOT / "opportunity-report"


def load(name: str) -> dict:
    return json.loads((DATA / name).read_text(encoding="utf-8"))


# ---------------- 格式化辅助 ----------------
def cands(value: float, nd: int) -> set[str]:
    """返回按指定小数位数四舍五入的候选字面值（仅 .x5 边界同时接受两种取整）。"""
    q = Decimal(1).scaleb(-nd) if nd > 0 else Decimal(1)
    # 先按 nd+4 位消除二进制浮点尾差（如 97.85000000000001），再做十进制取整
    d = Decimal(str(round(value, nd + 4)))
    return {f"{d.quantize(q, rounding=r):,f}" for r in (ROUND_HALF_UP, ROUND_HALF_EVEN)}


def comma(v: float) -> set[str]:
    return {f"{round(v):,}"}


CHECKS: list[tuple[str, list[str], set[str]]] = []  # (说明, 文件列表, 可接受字面值集合)


def claim(desc: str, files: list[str], literals: set[str]) -> None:
    CHECKS.append((desc, files, literals))


def build_claims() -> None:
    ms = load("market_sizing.json")  # 键：tam_conservative_usd_b / sam_usd_b / som_y3_usd_m{low_y3,mid_y3,high_y3}
    ue = load("unit_economics.json")
    fm = load("financial_model.json")
    mc = load("monte_carlo.json")
    ls = load("lifecycle_summary.json")
    ts = load("trending_now_summary.json")
    os_ = load("opportunity_scores.json")
    ns = load("niche_selection.json")

    # ---------- 市场规模（scripts/03） ----------
    tam = ms["tam_conservative_usd_b"]
    sam = ms["sam_usd_b"]
    som = ms["som_y3_usd_m"]
    claim("保守 TAM（$107 亿）", ["bp/00", "bp/02"],
          {f"{v} 亿" for v in cands(tam * 10, 1) | cands(tam * 10, 0)})
    claim("SAM（$17.6 亿）", ["bp/00", "bp/02"], {f"{v} 亿" for v in cands(sam * 10, 1)})
    claim("SOM 基准（$530 万）", ["bp/00", "bp/02"],
          {f"{v} 万" for v in cands(som["mid_y3"] * 100, 0)})
    claim("SOM 保守（$180 万）", ["bp/02"], {f"{v} 万" for v in cands(som["low_y3"] * 100, 0)})
    claim("SOM 乐观（$1,410 万）", ["bp/02"],
          {f"{round(som['high_y3'] * 100):,} 万", f"{round(som['high_y3'] * 100)} 万"})

    # ---------- 单位经济（scripts/05） ----------
    ac = ue["article_cost"]["budget"]["total_usd"]
    claim("单篇成本 $8.01", ["bp/00", "bp/04"], {f"${ac:.2f}"})
    claim("编辑占成稿成本 94%", ["bp/03"],
          {f"{v}%" for v in cands(ue["article_cost"]["budget"]["editor_usd"] / ac * 100, 0)})
    claim("单篇成本中间层 $8.41", ["bp/04"], {f"${ue['article_cost']['mid']['total_usd']:.2f}"})
    sa = ue["saas_unit_economics"]
    claim("LTV $1,716", ["bp/00", "bp/04"], {f"${round(sa['ltv_usd']):,}"})
    claim("LTV:CAC 4.9", ["bp/00", "bp/04"], {f"{sa['ltv_cac_ratio']:.1f}"})
    claim("CAC 回收 4.5 个月", ["bp/00", "bp/04"], {f"{sa['cac_payback_months']:.1f} 个月"})
    claim("客户生命周期 22.2 月", ["bp/04"], {f"{sa['expected_lifetime_months']:.1f}"})
    claim("CAC $350", ["bp/00", "bp/04", "bp/07"], {f"${round(sa['cac'])}"})
    base_site = ue["site_scenarios"]["base"]
    claim("单站基准累计回本第 17 月", ["bp/00", "bp/04"],
          {f"第 {base_site['cumulative_breakeven_month']} 月"})
    claim("单站基准月度盈亏平衡第 11 月", ["bp/04"],
          {f"第 {base_site['monthly_breakeven_month']} 月"})
    claim("单站基准月36利润 $3,347", ["bp/04"],
          {f"${round(base_site['month36']['profit']):,}"})
    claim("单站月投入 $541", ["bp/04"],
          {f"${round(60 * ac + 60)}", f"${round(60 * ac + 60):,}"})

    # ---------- 财务模型（scripts/06） ----------
    sc = fm["scenarios"]
    b, c, o = sc["base"], sc["conservative"], sc["optimistic"]
    claim("基准月36 ARR $2,138,028", ["bp/07"], comma(b["arr_m36"]))
    claim("基准月36 ARR ≈$214 万", ["bp/00"], {f"{v} 万" for v in cands(b["arr_m36"] / 1e4, 0)})
    claim("乐观月36 ARR $11,146,680", ["bp/07"], comma(o["arr_m36"]))
    claim("乐观月36 ARR ≈$1,115 万", ["bp/00"],
          {f"{round(o['arr_m36'] / 1e4):,} 万", f"{round(o['arr_m36'] / 1e4)} 万"})
    claim("基准月36客户 ~1,800", ["bp/00", "bp/07"],
          {f"{round(b['saas_customers_m36']):,}", "1,800"})
    claim("乐观月36客户 ~9,383", ["bp/00", "bp/07"], {f"{round(o['saas_customers_m36']):,}"})
    for label, key, val in [("基准年1收入", "bp/07", b["revenue_y1"]),
                            ("基准年2收入", "bp/07", b["revenue_y2"]),
                            ("基准年3收入", "bp/07", b["revenue_y3"])]:
        claim(f"{label} ${val:,}", [key], comma(val))
    tot_b = b["revenue_y1"] + b["revenue_y2"] + b["revenue_y3"]
    tot_c = c["revenue_y1"] + c["revenue_y2"] + c["revenue_y3"]
    tot_o = o["revenue_y1"] + o["revenue_y2"] + o["revenue_y3"]
    claim("基准3年收入合计 ≈$183 万", ["bp/00"],
          {f"{v} 万" for v in cands(tot_b / 1e4, 0)})
    claim("保守3年收入合计 ≈$1.4 万", ["bp/00"],
          {f"{v} 万" for v in cands(tot_c / 1e4, 1)})
    claim("乐观3年收入合计 ≈$846 万", ["bp/00"],
          {f"{v} 万" for v in cands(tot_o / 1e4, 0)})
    claim("基准月12组合PV 170,254", ["bp/07"], comma(b["portfolio_pv_m12"]))
    claim("保守月12组合PV 17,224", ["bp/07"], comma(c["portfolio_pv_m12"]))
    claim("乐观月12组合PV 923,575", ["bp/07"], comma(o["portfolio_pv_m12"]))
    claim("基准现金低谷 $347,376", ["bp/07"], comma(b["cash_trough"]))
    claim("基准现金低谷 ≈$35 万（月 33）", ["bp/00"],
          {f"{v} 万" for v in cands(b["cash_trough"] / 1e4, 0)})
    claim("基准现金低谷月份 33（正文）", ["bp/00"], {f"月 {b['cash_trough_month']}"})
    claim("乐观现金低谷月份 19（正文）", ["bp/00"], {f"月 {o['cash_trough_month']}"})
    claim("基准现金低谷月份 33（表格）", ["bp/07"], {f"（{b['cash_trough_month']}）"})
    claim("乐观现金低谷月份 19（表格）", ["bp/07"], {f"（{o['cash_trough_month']}）"})
    claim("保守期末现金 $1,127,315", ["bp/07"], comma(c["cash_m36"]))
    claim("保守期末现金 ≈$113 万", ["bp/00"], {f"{v} 万" for v in cands(c["cash_m36"] / 1e4, 0)})
    claim("基准期末现金 $375,757", ["bp/07"], comma(b["cash_m36"]))
    claim("乐观期末现金 $2,278,437", ["bp/07"], comma(o["cash_m36"]))
    claim("基准单月现金流转正月 34", ["bp/07"],
          {f"月 {b['first_cashflow_positive_month']}"})
    # 门槛判定必须由模型内生（修复后新增字段）
    for name in ("conservative", "base", "optimistic"):
        assert "gate" in sc[name], f"financial_model.json 缺少 {name}.gate（门槛须由模型内生判定）"
    claim("止损分支最大损失 ≈25%（1,127,315/1,500,000）", ["bp/00"],
          {f"{v}%" for v in cands((1 - c["cash_m36"] / fm["initial_cash_usd"]) * 100, 0)})

    # ---------- 蒙特卡洛（scripts/09） ----------
    claim("门槛通过概率 63%", ["bp/00", "bp/07", "bp/13"],
          {f"{v}%" for v in cands(mc["p_gate_pass"] * 100, 0)})
    claim("止损分支概率约 37%", ["bp/00", "bp/10", "bp/13"],
          {f"{v}%" for v in cands((1 - mc["p_gate_pass"]) * 100, 0)})
    claim("现金全程为正概率 97.8%", ["bp/00", "bp/07", "bp/13"],
          {f"{v}%" for v in cands((1 - mc["p_cash_ever_negative"]) * 100, 1)})
    claim("现金跌破零概率 2.2%", ["bp/07", "bp/13"],
          {f"{v}%" for v in cands(mc["p_cash_ever_negative"] * 100, 1)})
    claim("通过条件下跌破零概率 3.4%", ["bp/07"],
          {f"{v}%" for v in cands(mc["p_cash_negative_given_pass"] * 100, 1)})
    arr = mc["arr_m36_usd"]
    claim("ARR 中位数 ≈$112 万", ["bp/00", "bp/07"],
          {f"{v} 万" for v in cands(arr["p50"] / 1e4, 0)})
    claim("ARR P90 ≈$319 万", ["bp/00", "bp/07", "bp/13"],
          {f"{v} 万" for v in cands(arr["p90"] / 1e4, 0)})
    claim("通过条件下 ARR 中位数 ≈$181 万", ["bp/07", "bp/13"],
          {f"{v} 万" for v in cands(arr["p50_given_gate_pass"] / 1e4, 0)})
    claim("ARR≥$100 万概率 53%", ["bp/07", "bp/13"],
          {f"{v}%" for v in cands(mc["p_arr_m36_over_1m"] * 100, 0)})
    claim("ARR≥$200 万概率 27%", ["bp/07", "bp/13"],
          {f"{v}%" for v in cands(mc["p_arr_m36_over_2m"] * 100, 0)})
    cash36 = mc["cash_m36_usd"]
    claim("期末现金 P10 ≈$21 万", ["bp/07"], {f"{v} 万" for v in cands(cash36["p10"] / 1e4, 0)})
    claim("期末现金 P50 ≈$95 万", ["bp/07"], {f"{v} 万" for v in cands(cash36["p50"] / 1e4, 0)})
    claim("期末现金 P90 ≈$114 万", ["bp/07"], {f"{v} 万" for v in cands(cash36["p90"] / 1e4, 0)})
    # 赔率四分支（13.4）：未过门槛 / 过但 ARR<1M / 1-2M / >=2M
    b1 = (1 - mc["p_gate_pass"]) * 100
    b2 = (mc["p_gate_pass"] - mc["p_arr_m36_over_1m"]) * 100
    b3 = (mc["p_arr_m36_over_1m"] - mc["p_arr_m36_over_2m"]) * 100
    b4 = mc["p_arr_m36_over_2m"] * 100
    for name, v in [("赔率分支1(未过门槛)", b1), ("赔率分支2(过但<1M)", b2),
                    ("赔率分支3(1-2M)", b3), ("赔率分支4(>=2M)", b4)]:
        claim(f"{name} ≈{v:.0f}%", ["bp/13"], {f"{x}%" for x in cands(v, 0)})
    tor = {t["param"]: t for t in mc["tornado_arr_m36"]["sweeps"]}
    g = tor["H18 SaaS增速"]
    claim("龙卷风 H18 增速 ARR 下界 ≈$92 万", ["bp/07"],
          {f"{v} 万" for v in cands(g["arr_low"] / 1e4, 0)})
    claim("龙卷风 H18 增速 ARR 上界 ≈$411 万", ["bp/07"],
          {f"{v} 万" for v in cands(g["arr_high"] / 1e4, 0)})
    ch = tor["H15 月流失"]
    claim("龙卷风流失率 ARR 下界 ≈$190 万", ["bp/07"],
          {f"{v} 万" for v in cands(ch["arr_low"] / 1e4, 0)})
    claim("龙卷风流失率 ARR 上界 ≈$225 万", ["bp/07"],
          {f"{v} 万" for v in cands(ch["arr_high"] / 1e4, 0)})

    # ---------- 生命周期（scripts/02） ----------
    claim("278 个事件驱动热点", ["bp/00", "bp/01", "or/03"], {str(ls["n_spikes"])})
    claim("候选 298 篇", ["or/03"], {str(ls["n_candidates"])})
    hl = ls["half_life_days"]
    claim("半衰期中位数 2 天", ["bp/00", "bp/01", "or/03"], {f"{hl['median']} 天"})
    claim("半衰期 P25", ["or/03"], {f"{hl['p25']} 天"})
    claim("半衰期 P75", ["or/03"], {f"{hl['p75']} 天"})
    f3 = ls["first3day_share_of_30d_excess"]
    claim("前3天消耗 65% 窗口价值", ["bp/00", "bp/01"],
          {f"{v}%" for v in cands(f3["median"] * 100, 0)})
    claim("前3天份额精确值 64.8%", ["or/03"], {f"{v}%" for v in cands(f3["median"] * 100, 1)})
    claim("跌破10%中位 4 天", ["or/03"], {f"{ls['decay_to_10pct_days']['median']} 天"})

    # ---------- 热词快照（scripts/01） ----------
    claim("快照 80 条热词", ["or/03"], {str(ts["total"]["trend_count"])})
    claim("快照流量下界合计 185,000", ["or/03"], comma(ts["total"]["sum_traffic_lower_bound"]))

    # ---------- 机会评分（scripts/04） ----------
    ranked = {r["id"]: r for r in os_["ranking"]}
    claim("两阶段混合评分 7.36", ["bp/00", "or/04"],
          {f"{ranked['D_hybrid_two_stage']['weighted_total']:.2f}"})
    claim("纯 SaaS 评分 6.76", ["or/04"], {f"{ranked['C_pure_saas']['weighted_total']:.2f}"})
    claim("自营组合评分 6.04", ["or/04"],
          {f"{ranked['B_owned_quality_portfolio']['weighted_total']:.2f}"})

    # ---------- 领域选择（scripts/08） ----------
    port = {p["id"]: p for p in ns["recommended_portfolio_base8"]}
    for nid, zh in [("ai_saas_tools", "AI/SaaS 工具"), ("consumer_tech", "消费电子"),
                    ("home_energy_ev", "家庭能源"), ("travel_deals", "旅行"),
                    ("home_garden", "家居园艺"), ("food_recipes", "食谱"),
                    ("pets", "宠物"), ("gaming_guides", "游戏攻略")]:
        claim(f"领域评分 {zh} {port[nid]['score']:.2f}", ["bp/04"], {f"{port[nid]['score']:.2f}"})
    top8_ids = [p["id"] for p in ns["recommended_portfolio_base8"]]
    rpm_vals = {r["id"]: r["rpm_mid_usd"] for r in ns["ranking"]}
    rpm_mean = sum(rpm_vals[i] for i in top8_ids) / len(top8_ids)
    claim("组合均权 RPM ≈14.2", ["bp/04"], {f"{v}" for v in cands(rpm_mean, 1)})


FILE_MAP = {}


def resolve(tag: str) -> Path:
    if tag in FILE_MAP:
        return FILE_MAP[tag]
    prefix, num = tag.split("/")
    folder = BP if prefix == "bp" else OR_
    matches = sorted(folder.glob(f"{num}-*.md"))
    assert matches, f"找不到章节文件 {tag}"
    FILE_MAP[tag] = matches[0]
    return matches[0]


def check_full_version(folder: Path, full_name: str) -> list[str]:
    """完整版必须逐字包含全部分章内容。"""
    failures = []
    full = (folder / full_name).read_text(encoding="utf-8")
    for ch in sorted(folder.glob("[0-9][0-9]-*.md")):
        body = ch.read_text(encoding="utf-8").strip()
        if body not in full:
            failures.append(f"{full_name} 未包含 {ch.name} 的完整内容")
    return failures


def main() -> None:
    build_claims()
    failures = []
    texts: dict[str, str] = {}
    for desc, files, literals in CHECKS:
        for tag in files:
            p = resolve(tag)
            if tag not in texts:
                texts[tag] = p.read_text(encoding="utf-8")
            if not any(lit in texts[tag] for lit in literals):
                failures.append(f"{desc} → {p.name} 未找到任一期望值 {sorted(literals)}")

    struct_fail = check_full_version(BP, "商业计划书-完整版.md")
    struct_fail += check_full_version(OR_, "商业机会挖掘与分析报告-完整版.md")
    failures.extend(struct_fail)

    n_claims = sum(len(f) for _, f, _ in CHECKS) + 2
    print(f"共核对 {len(CHECKS)} 条数字断言（跨 {n_claims} 个文件位置）+ 2 项完整版结构检查")
    if failures:
        print(f"\n失败 {len(failures)} 项：")
        for f in failures:
            print("  FAIL:", f)
        sys.exit(1)
    print("全部一致：文档声明与 data/ 脚本输出逐条吻合。")
    sys.exit(0)


if __name__ == "__main__":
    main()
