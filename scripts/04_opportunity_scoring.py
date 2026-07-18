# -*- coding: utf-8 -*-
"""
04_opportunity_scoring.py — 候选商业机会加权评分模型（可复现）

对 5 条候选路径按 8 项准则打分（1–10），加权汇总排序。
每个分值附打分依据（rationale），引用 SOURCES.md 来源编号或脚本产出，
使评分过程可审计、可质疑、可重算。

产出：
    data/opportunity_scores.json
    assets/opportunity_scores.png
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
ASSETS = ROOT / "assets"
DATA.mkdir(exist_ok=True)
ASSETS.mkdir(exist_ok=True)

# 权重（合计 1.0）。设计原则：合规风险与自动化可行性是本项目的两大主要矛盾，
# 各占 0.18；市场规模/增速合计 0.24；其余为次要矛盾。
CRITERIA = {
    "market_size":        {"weight": 0.12, "label": "市场规模"},
    "market_growth":      {"weight": 0.12, "label": "市场增速"},
    "competition_inverse":{"weight": 0.12, "label": "竞争格局(越空越高)"},
    "compliance_risk_inverse": {"weight": 0.18, "label": "合规安全(风险越低越高)"},
    "automation_feasibility":  {"weight": 0.18, "label": "自动化可行性"},
    "capital_efficiency": {"weight": 0.10, "label": "资本效率"},
    "moat_potential":     {"weight": 0.10, "label": "护城河潜力"},
    "validation_speed":   {"weight": 0.08, "label": "验证速度"},
}

OPPORTUNITIES = {
    "A_pure_ai_site_farm": {
        "label": "A. 纯 AI 站群（无编辑监督的规模化程序内容）",
        "scores": {
            "market_size": (7, "广告变现空间大，联盟市场 2026 年约 $20B [S17]"),
            "market_growth": (3, "零点击搜索挤压：83% 带 AIO 的搜索无点击 [S4]"),
            "competition_inverse": (4, "门槛极低，同质竞争者海量（AI 降低了造垃圾站成本 [S7]）"),
            "compliance_risk_inverse": (1, "直接违反 Scaled Content Abuse 政策 [S5]；2026-03 核心更新致此类站流量 -50~80% [S7]"),
            "automation_feasibility": (9, "技术上完全可自动化，这正是它被打击的原因"),
            "capital_efficiency": (8, "单站成本极低"),
            "moat_potential": (1, "无护城河，随时可被复制且随时可被清零"),
            "validation_speed": (8, "上线即可测"),
        },
        "verdict": "证伪：期望收益为负。收入依赖 Google 索引，而该模式被 Google 明文列为头号打击对象，惩罚是移除索引（收入归零）。不合规也不可持续，违背向善与合法合规原则，排除。",
    },
    "B_owned_quality_portfolio": {
        "label": "B. 质量优先自营内容站组合（热词驱动+编辑监督）",
        "scores": {
            "market_size": (6, "自营模式收入上限受限于站点数×流量×RPM（$3–40 RPM [S14][S15]）"),
            "market_growth": (5, "信息类查询流量被 AIO 侵蚀 [S1][S4]，但 AI 渠道访客价值高 4.4 倍 [S4]、联盟转化 14% vs 2.8% [S17]"),
            "competition_inverse": (6, "质量+速度组合有差异化；纯拼量者将被 [S5][S7] 出清，反而利好合规玩家"),
            "compliance_risk_inverse": (5, "白帽路线合规，但平台单一依赖仍在：算法更新是最大经营风险"),
            "automation_feasibility": (8, "流水线 90% 环节可自动化，编辑关口保留人工（合规要求）"),
            "capital_efficiency": (7, "单站月成本数百美元级（见 05_unit_economics.py）"),
            "moat_potential": (4, "站点品牌与历史数据有一定积累性，但可复制"),
            "validation_speed": (7, "3–6 个月可见自然流量信号"),
        },
        "verdict": "可行但天花板有限：适合作为现金流业务与数据验证场，不适合作为独立的风投级业务。",
    },
    "C_pure_saas": {
        "label": "C. 直接做 SaaS（热词→内容→SEO/GEO 自动化工具）",
        "scores": {
            "market_size": (8, "保守 TAM $10.7B、SAM $1.76B（03_market_sizing.py）"),
            "market_growth": (9, "GEO 工具 CAGR 38.5–50.5% [S12][S13]；赛道 1 年融资 $300M+ [S24]"),
            "competition_inverse": (5, "巨头（Semrush/Ahrefs）与新锐（Profound $155M）都在 [S22][S24]，但'热词→成稿→GEO'一体化自动流水线仍是空位"),
            "compliance_risk_inverse": (7, "工具商不直接承担站点处罚风险，但需内置合规护栏避免助纣为虐"),
            "automation_feasibility": (8, "LLM 成本已低至可规模化（$0.1–0.4/百万 token 经济层 [S26]）"),
            "capital_efficiency": (5, "SaaS 获客成本高，无自营数据背书则需烧钱证明效果"),
            "moat_potential": (6, "效果数据闭环+工作流深度可建护城河，但冷启动缺数据"),
            "validation_speed": (4, "无实盘证据时销售周期长、可信度低"),
        },
        "verdict": "市场对，但冷启动缺'效果证据'——这恰是路径 D 要解决的。",
    },
    "D_hybrid_two_stage": {
        "label": "D. 两阶段混合（先自营验证，再 SaaS 产品化）",
        "scores": {
            "market_size": (8, "阶段二承接 C 的全部 TAM，阶段一另有自营现金流"),
            "market_growth": (9, "同 C：GEO 赛道爆发期 [S12][S13][S24]"),
            "competition_inverse": (7, "自营实盘数据是差异化销售武器：'我们用它赚到了钱'，竞品多为纯监测工具 [S24]"),
            "compliance_risk_inverse": (6, "阶段一承担平台风险但受编辑关口控制；阶段二风险转为工具商角色"),
            "automation_feasibility": (8, "同 B/C，引擎复用"),
            "capital_efficiency": (7, "阶段一自营收入部分覆盖研发；引擎一次开发两次变现"),
            "moat_potential": (7, "实盘效果数据集（哪类热词×哪类内容×何种优化→何种流量/收入）是竞品没有的私有资产"),
            "validation_speed": (7, "阶段一 6 个月出可检验信号，用客观指标决定是否进入阶段二"),
        },
        "verdict": "最优：以自营实盘解决 SaaS 冷启动的信任与数据问题，以 SaaS 打开天花板；阶段门槛制天然内置退出机制。",
    },
    "E_agency_service": {
        "label": "E. 代运营服务（人力密集型 agency）",
        "scores": {
            "market_size": (7, "全球 SEO 服务市场 2026 约 $87.8B [S29]"),
            "market_growth": (5, "稳增但 AI 正在压缩传统服务价值"),
            "competition_inverse": (2, "仅美国就有 36.3 万家同行 [S29]，年流失率约 38%"),
            "compliance_risk_inverse": (7, "风险由客户站点分担"),
            "automation_feasibility": (4, "服务交付高度依赖人力沟通，规模不经济"),
            "capital_efficiency": (6, "轻资产但线性增长"),
            "moat_potential": (2, "无护城河，客户切换成本低（65% SMB 换过 2+ 家供应商 [S29]）"),
            "validation_speed": (6, "接单即验证"),
        },
        "verdict": "不符合'全自动软件'的项目定位，作为阶段二的补充收入线可选，不作主路径。",
    },
}


# 硬约束（一票否决）：合规安全分 <= 2 即取消资格。
# 依据：违反 [S5] 政策的处罚是移除索引，收入归零，加权平均无法反映这种毁灭性尾部风险；
# 且不合规路径违背本项目"合法合规、向善"的总纲，无论得分高低一律排除。
COMPLIANCE_VETO_THRESHOLD = 2


def main() -> None:
    results = []
    for key, opp in OPPORTUNITIES.items():
        total = 0.0
        detail = {}
        for crit, meta in CRITERIA.items():
            score, rationale = opp["scores"][crit]
            total += score * meta["weight"]
            detail[crit] = {"score": score, "weight": meta["weight"], "rationale": rationale}
        disqualified = opp["scores"]["compliance_risk_inverse"][0] <= COMPLIANCE_VETO_THRESHOLD
        results.append(
            {
                "id": key,
                "label": opp["label"],
                "weighted_total": round(total, 3),
                "disqualified_by_compliance_veto": disqualified,
                "verdict": opp["verdict"],
                "detail": detail,
            }
        )
    # 排序：先按是否被否决（未否决在前），再按加权总分
    results.sort(key=lambda r: (r["disqualified_by_compliance_veto"], -r["weighted_total"]))

    out = {
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "criteria": {k: v for k, v in CRITERIA.items()},
        "compliance_veto_threshold": COMPLIANCE_VETO_THRESHOLD,
        "ranking": results,
    }
    (DATA / "opportunity_scores.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Noto Sans CJK SC", "PingFang SC", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False

    fig, ax = plt.subplots(figsize=(10, 5.5))
    names = [r["label"].split("（")[0] + ("  [合规否决]" if r["disqualified_by_compliance_veto"] else "") for r in results][::-1]
    vals = [r["weighted_total"] for r in results][::-1]
    vetoed = [r["disqualified_by_compliance_veto"] for r in results][::-1]
    colors = ["#999999" if dq else ("#e69138" if v < 6 else "#6aa84f") for v, dq in zip(vals, vetoed)]
    ax.barh(names, vals, color=colors)
    for i, v in enumerate(vals):
        ax.text(v + 0.05, i, f"{v:.2f}", va="center")
    ax.set_xlim(0, 10)
    ax.set_xlabel("加权总分（满分 10）")
    ax.set_title("候选商业机会加权评分（权重与依据见 data/opportunity_scores.json）")
    fig.tight_layout()
    fig.savefig(ASSETS / "opportunity_scores.png", dpi=150)

    for r in results:
        flag = " [合规一票否决]" if r["disqualified_by_compliance_veto"] else ""
        print(f"{r['weighted_total']:>5.2f}  {r['label']}{flag}")
    print("\n写出：data/opportunity_scores.json, assets/opportunity_scores.png")


if __name__ == "__main__":
    main()
