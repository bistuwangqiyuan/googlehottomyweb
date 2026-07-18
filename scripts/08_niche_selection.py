# -*- coding: utf-8 -*-
"""
08_niche_selection.py — 阶段一自营站领域（niche）选择评分模型

对 12 个候选领域按 6 项准则评分（数据来源逐项标注），输出建议组合。
硬约束：
  - YMYL 高危（医疗建议/投资建议）一票否决（合规护栏，风险登记册 R7）
  - 组合必须跨 >=6 个相互独立的领域（算法风险分散，风险登记册 R1）

准则与权重：
  rpm_score        0.22  展示广告 RPM 区间中值 [S14][S15]
  affiliate_score  0.18  联盟变现潜力（佣金率×转化场景丰富度）[S17][S19]
  trend_supply     0.18  热词供给密度（该领域事件驱动热词的出现频率）。
                         本项为专家判断分（标注 H23），锚点为 [D1] 快照
                         （data/trending_now.csv，脚本运行时读取并把快照统计
                         写入输出 JSON 作为审计锚点）+ lifecycle 样本的定性观察；
                         快照仅 80 条热词，不足以支撑逐领域的统计分布，
                         故如实按"有数据锚点的专家打分"处理，不伪称统计推断。
  aio_resilience   0.16  AIO 冲击韧性：交易/对比类查询占比高者得分高 [S1][S2]
  competition_inv  0.14  竞争强度反向分（大众领域低分，标注 H24 推测）
  evergreen_ratio  0.12  热点内容可常青化比例（延长资产寿命，标注 H25 推测）

产出：
    data/niche_selection.json
    assets/niche_scores.png
"""
import csv
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


def load_trend_snapshot_evidence() -> dict:
    """读取 [D1] 热词快照（data/trending_now.csv），返回 trend_supply 打分的审计锚点统计。"""
    path = DATA / "trending_now.csv"
    if not path.exists():
        return {"snapshot_file": "data/trending_now.csv", "available": False,
                "note": "快照缺失：请先运行 scripts/01_fetch_trending_now.py；trend_supply 为专家判断分（H23）"}
    with path.open(encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    geos = sorted({r["geo"] for r in rows})
    return {
        "snapshot_file": "data/trending_now.csv",
        "available": True,
        "n_terms": len(rows),
        "geos": geos,
        "snapshot_utc": rows[0]["snapshot_utc"] if rows else None,
        "note": ("trend_supply 为专家判断分（H23），以本快照与 lifecycle 样本为定性锚点；"
                 "样本量（80 条）不足以做逐领域统计分布，故不伪称统计推断"),
    }

WEIGHTS = {
    "rpm_score": 0.22,
    "affiliate_score": 0.18,
    "trend_supply": 0.18,
    "aio_resilience": 0.16,
    "competition_inv": 0.14,
    "evergreen_ratio": 0.12,
}

# 每项分值 1-10，附依据。rpm_mid = 区间中值（美元/千次会话，[S14] 表）
NICHES = {
    "consumer_tech": {
        "label": "消费电子/科技产品（对比评测）",
        "rpm_mid": 23.5,  # 科技/SaaS $12-35 [S14]
        "ymyl_banned": False,
        "scores": {
            "rpm_score": (7, "RPM $12-35 区间 [S14]"),
            "affiliate_score": (7, "产品联盟场景密集；Amazon 电子类佣金低(2-4%)但客单高 [S19]"),
            "trend_supply": (9, "产品发布/泄露/评测热词高频（快照见 samsung/iphone 词条 [D1]）"),
            "aio_resilience": (8, "对比类查询占比高，AIO 出现率 95% 但引用者获 2.3 倍点击 [S1][S2]"),
            "competition_inv": (4, "评测站众多，但热词响应速度是差异化维度（H24）"),
            "evergreen_ratio": (7, "评测/对比可持续更新为常青页（H25）"),
        },
    },
    "home_garden": {
        "label": "家居/园艺/DIY",
        "rpm_mid": 11.5,  # DIY $7-16 [S14]
        "ymyl_banned": False,
        "scores": {
            "rpm_score": (5, "RPM $7-16 [S14]"),
            "affiliate_score": (7, "工具/家居用品联盟丰富，Amazon 家居 3% [S19]"),
            "trend_supply": (5, "季节性强，事件驱动中等（H23）"),
            "aio_resilience": (7, "how-to+产品对比混合，交易意图占比较高"),
            "competition_inv": (6, "中等竞争（H24）"),
            "evergreen_ratio": (8, "how-to 内容长寿（H25）"),
        },
    },
    "personal_finance_info": {
        "label": "个人理财（仅资讯/工具对比，不做投资建议）",
        "rpm_mid": 27.5,  # 理财 $15-40 [S14]
        "ymyl_banned": True,  # YMYL 高危：即便只做对比也易滑向建议；初期禁入（护栏 C 黑名单）
        "scores": {
            "rpm_score": (9, "RPM $15-40 全场最高 [S14]"),
            "affiliate_score": (9, "金融线索单价极高 [S19]"),
            "trend_supply": (6, "政策/利率事件驱动（H23）"),
            "aio_resilience": (5, "YMYL 领域 AIO 引用需自然前 10 [S32]，新站难"),
            "competition_inv": (2, "银行/大媒体盘踞（H24）"),
            "evergreen_ratio": (7, "工具对比可常青（H25）"),
        },
    },
    "entertainment_streaming": {
        "label": "影视/流媒体指南（上映日历、平台指南）",
        "rpm_mid": 5.0,  # 娱乐 $3-7 [S16]
        "ymyl_banned": False,
        "scores": {
            "rpm_score": (2, "RPM $3-7 低 [S16]"),
            "affiliate_score": (4, "流媒体订阅联盟有限"),
            "trend_supply": (10, "热词供给全场最高（快照娱乐词条占比最大 [D1]）"),
            "aio_resilience": (6, "'哪里能看X'类查询意图明确"),
            "competition_inv": (5, "热词响应速度可差异化（H24）"),
            "evergreen_ratio": (4, "时效性强，常青化率低（H25）"),
        },
    },
    "gaming_guides": {
        "label": "游戏攻略/发售追踪",
        "rpm_mid": 4.0,  # 游戏 $2-6 [S16]
        "ymyl_banned": False,
        "scores": {
            "rpm_score": (2, "RPM $2-6 低且广告拦截率 15-35% [S16][S5:organicarbitrage]"),
            "affiliate_score": (5, "游戏/外设联盟中等"),
            "trend_supply": (9, "版本更新/发售事件高频（H23）"),
            "aio_resilience": (7, "攻略长查询 AI 难完整作答，点击留存较好（H25 推测）"),
            "competition_inv": (4, "大型攻略站盘踞（H24）"),
            "evergreen_ratio": (5, "版本迭代快（H25）"),
        },
    },
    "travel_deals": {
        "label": "旅行目的地/装备（事件驱动：签证政策、航线、装备）",
        "rpm_mid": 12.0,  # 旅行 $6-18 [S14]
        "ymyl_banned": False,
        "scores": {
            "rpm_score": (5, "RPM $6-18，Q4 有旺季溢价 [S14]"),
            "affiliate_score": (7, "酒店/保险/装备联盟丰富，旅行类联盟月收入锚点高 [S17]"),
            "trend_supply": (7, "政策/事件/季节热词稳定（H23）"),
            "aio_resilience": (7, "行程规划长尾+装备对比交易意图"),
            "competition_inv": (5, "OTA 与大博主竞争（H24）"),
            "evergreen_ratio": (7, "目的地指南可常青（H25）"),
        },
    },
    "pets": {
        "label": "宠物用品/养护",
        "rpm_mid": 9.5,  # 宠物 $5-14 [S14]
        "ymyl_banned": False,
        "scores": {
            "rpm_score": (4, "RPM $5-14 [S14]"),
            "affiliate_score": (7, "宠物食品/保险联盟活跃 [S14]"),
            "trend_supply": (4, "事件驱动热词较少（H23）"),
            "aio_resilience": (6, "产品对比+养护 how-to 混合"),
            "competition_inv": (6, "中等（H24）"),
            "evergreen_ratio": (8, "养护内容长寿（H25）"),
        },
    },
    "food_recipes": {
        "label": "食谱/厨房电器（节庆与热点食谱）",
        "rpm_mid": 14.0,  # 美食 $8-20 [S14]
        "ymyl_banned": False,
        "scores": {
            "rpm_score": (6, "RPM $8-20，Mediavine 最强类目 [S14][S5:organicarbitrage]"),
            "affiliate_score": (6, "厨电/食材配送联盟 [S14]"),
            "trend_supply": (6, "节庆/病毒食谱周期性（H23）"),
            "aio_resilience": (6, "食谱结构化易被 AIO 消化，但完整步骤仍引点击"),
            "competition_inv": (3, "食谱站红海（H24）"),
            "evergreen_ratio": (9, "经典食谱常青（H25）"),
        },
    },
    "sports_events": {
        "label": "体育赛事数据/日程（不涉博彩）",
        "rpm_mid": 5.5,  # 新闻/时事 $3-8 [S16]
        "ymyl_banned": False,
        "scores": {
            "rpm_score": (3, "RPM $3-8 [S16]"),
            "affiliate_score": (3, "变现路径窄（装备联盟弱、坚决不做博彩）"),
            "trend_supply": (10, "赛事热词全年高频 [D1]"),
            "aio_resilience": (5, "比分/日程类易被 AIO 直接回答"),
            "competition_inv": (3, "ESPN 级巨头盘踞（H24）"),
            "evergreen_ratio": (3, "强时效（H25）"),
        },
    },
    "ai_saas_tools": {
        "label": "AI/SaaS 工具评测与对比",
        "rpm_mid": 23.5,  # 科技/SaaS $12-35 [S14]
        "ymyl_banned": False,
        "scores": {
            "rpm_score": (7, "RPM $12-35 [S14]"),
            "affiliate_score": (9, "SaaS 联盟佣金 20-70% 且经常性 [S17]"),
            "trend_supply": (8, "新工具/模型发布高频（本项目一手经验：AI 赛道周更）"),
            "aio_resilience": (8, "'X vs Y'对比查询是 AIO 引用主场 [S2]"),
            "competition_inv": (4, "测评站增多但事实密度普遍低，有工艺差异化空间（H24）"),
            "evergreen_ratio": (6, "工具迭代快但对比页可滚动更新（H25）"),
        },
    },
    "home_energy_ev": {
        "label": "家庭能源/电动出行（太阳能、EV 配件、电价）",
        "rpm_mid": 16.0,  # 介于家居与科技之间，取 $10-22 中值（H26 推测）
        "ymyl_banned": False,
        "scores": {
            "rpm_score": (6, "估计 $10-22（H26，介于家居/科技类目之间）"),
            "affiliate_score": (7, "高客单（充电桩/储能）联盟"),
            "trend_supply": (7, "政策补贴/新车发布/电价事件（H23）"),
            "aio_resilience": (7, "计算器/对比工具类内容 AI 难替代"),
            "competition_inv": (7, "垂直玩家少，成长期领域（H24）"),
            "evergreen_ratio": (7, "指南可常青（H25）"),
        },
    },
    "celebrity_gossip": {
        "label": "名人八卦",
        "rpm_mid": 5.0,  # 娱乐/名人 $3-7 [S16]
        "ymyl_banned": True,  # 公序良俗风险：隐私侵扰/诽谤风险高，编辑成本不可控，黑名单
        "scores": {
            "rpm_score": (2, "RPM $3-7 [S16]"),
            "affiliate_score": (2, "几乎无联盟场景"),
            "trend_supply": (10, "热词供给最高 [D1]"),
            "aio_resilience": (4, "事实型八卦被 AIO 直接消化"),
            "competition_inv": (3, "TMZ 级巨头（H24）"),
            "evergreen_ratio": (2, "强时效（H25）"),
        },
    },
}


def main() -> None:
    results = []
    for key, n in NICHES.items():
        total = sum(n["scores"][c][0] * w for c, w in WEIGHTS.items())
        results.append(
            {
                "id": key,
                "label": n["label"],
                "rpm_mid_usd": n["rpm_mid"],
                "weighted_total": round(total, 2),
                "banned": n["ymyl_banned"],
                "detail": {c: {"score": s, "rationale": r} for c, (s, r) in n["scores"].items()},
            }
        )
    results.sort(key=lambda r: (r["banned"], -r["weighted_total"]))

    eligible = [r for r in results if not r["banned"]]
    portfolio = eligible[:8]  # 基准情景 8 站
    out = {
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "weights": WEIGHTS,
        "trend_supply_evidence": load_trend_snapshot_evidence(),
        "hard_constraints": [
            "YMYL 高危与公序良俗风险领域一票否决（个人理财建议、名人八卦被排除）",
            "组合跨 >=6 个独立领域分散算法风险",
        ],
        "ranking": results,
        "recommended_portfolio_base8": [
            {"rank": i + 1, "id": r["id"], "label": r["label"], "score": r["weighted_total"]}
            for i, r in enumerate(portfolio)
        ],
        "portfolio_note": (
            "开站顺序=评分序：前 4 站（月1-4）取 Top4，验证信号最强的领域先行；"
            "月 5-8 补齐 5-8 名，保持领域独立性。"
            "组合加权平均 RPM（按评分排名前8站均权）="
            f"{round(sum(r['rpm_mid_usd'] for r in portfolio) / len(portfolio), 1)} 美元/千次，"
            "与财务模型基准 RPM=15 假设一致性核对用。"
        ),
    }
    (DATA / "niche_selection.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Noto Sans CJK SC", "PingFang SC", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False

    fig, ax = plt.subplots(figsize=(11, 6.5))
    names = [r["label"] + ("  [黑名单]" if r["banned"] else "") for r in results][::-1]
    vals = [r["weighted_total"] for r in results][::-1]
    banned = [r["banned"] for r in results][::-1]
    in_top8 = [(not b) and (r["id"] in {p["id"] for p in out["recommended_portfolio_base8"]})
               for b, r in zip(banned, results[::-1])]
    colors = ["#999999" if b else ("#6aa84f" if t else "#e69138") for b, t in zip(banned, in_top8)]
    ax.barh(names, vals, color=colors)
    for i, v in enumerate(vals):
        ax.text(v + 0.05, i, f"{v:.2f}", va="center", fontsize=9)
    ax.set_xlim(0, 10)
    ax.set_xlabel("加权总分（绿=入选组合，橙=候补，灰=合规黑名单）")
    ax.set_title("阶段一自营站领域评分（权重与逐项依据见 data/niche_selection.json）")
    fig.tight_layout()
    fig.savefig(ASSETS / "niche_scores.png", dpi=150)

    for r in results:
        flag = " [黑名单]" if r["banned"] else ""
        print(f"{r['weighted_total']:>5.2f}  {r['label']}{flag}")
    print("\n入选组合（基准 8 站）：", [p["id"] for p in out["recommended_portfolio_base8"]])
    print("写出：data/niche_selection.json, assets/niche_scores.png")


if __name__ == "__main__":
    main()
