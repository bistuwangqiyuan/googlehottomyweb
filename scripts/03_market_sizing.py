# -*- coding: utf-8 -*-
"""
03_market_sizing.py — TAM / SAM / SOM 双口径测算（自上而下 + 自下而上）

全部输入参数均来自 SOURCES.md 中标注的来源（在下方 ASSUMPTIONS 中逐项注明），
任何第三方修改参数即可重算。结果供机会报告第 3 章与商业计划书市场分析章引用。

产出：
    data/market_sizing.json      测算结果
    assets/market_funnel.png     TAM/SAM/SOM 漏斗图
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

# ---------------------------------------------------------------------------
# 输入参数（每项后注明来源编号，见 SOURCES.md）
# ---------------------------------------------------------------------------
ASSUMPTIONS = {
    # --- 自上而下（top-down）---
    "seo_software_market_2025_usd": 85.0e9,   # [S9][S10][S11] 三家机构 84.9~86.3e9，取中值 85e9
    "seo_software_cagr": 0.11,                # [S9]13.26% [S10]7.89% [S11]13.65% 的保守折中
    "geo_tools_market_2025_usd": 0.85e9,      # [S12][S13] 两家均约 8.5 亿
    "geo_tools_cagr": 0.42,                   # [S12]50.5% [S13]38.5% 的折中偏保守
    # 本产品可服务的子集：自动化内容+热词+GEO 一体化工作流，
    # 对应 SEO 软件市场中"内容优化+关键词研究+自动化"模块。
    # 推测性参数：行业报告未单列该子集，按功能模块占比估 12%（标注为假设 H1）
    "serviceable_share_of_seo_market": 0.12,  # 假设 H1（推测，敏感性分析覆盖 8%~20%）
    "serviceable_share_of_geo_market": 0.60,  # 假设 H2：GEO 工具中 SaaS 部署占 60% [S12]

    # --- 自下而上（bottom-up）---
    # 客群 1：美国 SMB 中为 SEO 付费者
    "us_smb_total": 36.2e6,                   # [S27] SBA 2025-06
    "us_smb_paying_seo_share": 0.39,          # [S27] 39% 以某种形式向机构/服务付费
    "us_smb_avg_monthly_seo_spend": 497.0,    # [S29] Backlinko 1200 家调查
    # 客群 2：全球营销/SEO 机构
    "global_agencies": 437_000,               # [S28] 2024 年全球广告与营销机构数
    "agency_avg_monthly_retainer": 3209.0,    # [S29] Ahrefs 439 家调查（机构向客户收费口径）
    "agency_tool_spend_share": 0.10,          # 假设 H3：机构将约 10% 收入用于工具（推测）
    # 客群 3：职业内容站长/联盟营销者（自营模式的同类人群，SaaS 潜在客户）
    "pro_publishers_global": 900_000,         # [S19] Amazon Associates 活跃联盟客 90 万+（下界）
    "publisher_tool_budget_monthly": 100.0,   # 假设 H4：职业站长月工具预算 $100（对标 [S20][S22] 入门价）

    # --- SAM 约束 ---
    "target_geo_share": 0.47,                 # [S19] 北美占联盟支出 47%，作为英文市场代理
    "reachable_segment_share": 0.35,          # 假设 H5：定位适配（需要自动化+热词工作流的子群）
    # --- SOM ---
    "som_share_y3_low": 0.001,                # 假设 H6：3 年市占 0.1%（保守）
    "som_share_y3_mid": 0.003,                #          0.3%（基准）
    "som_share_y3_high": 0.008,               #          0.8%（乐观，对标 Peec AI 10 个月 $4M ARR [S24]）
}


def project(value: float, cagr: float, years: int) -> float:
    return value * (1 + cagr) ** years


def main() -> None:
    a = ASSUMPTIONS

    # ---------------- 自上而下 ----------------
    seo_2028 = project(a["seo_software_market_2025_usd"], a["seo_software_cagr"], 3)
    geo_2028 = project(a["geo_tools_market_2025_usd"], a["geo_tools_cagr"], 3)
    tam_topdown_2025 = (
        a["seo_software_market_2025_usd"] * a["serviceable_share_of_seo_market"]
        + a["geo_tools_market_2025_usd"] * a["serviceable_share_of_geo_market"]
    )
    tam_topdown_2028 = (
        seo_2028 * a["serviceable_share_of_seo_market"]
        + geo_2028 * a["serviceable_share_of_geo_market"]
    )

    # ---------------- 自下而上 ----------------
    seg_smb = a["us_smb_total"] * a["us_smb_paying_seo_share"] * a["us_smb_avg_monthly_seo_spend"] * 12
    seg_agency = a["global_agencies"] * a["agency_avg_monthly_retainer"] * a["agency_tool_spend_share"] * 12
    seg_publisher = a["pro_publishers_global"] * a["publisher_tool_budget_monthly"] * 12
    tam_bottomup = seg_smb + seg_agency + seg_publisher

    # SAM：英文市场 × 定位适配子群（对两口径 TAM 的较小者取，保守）
    tam_conservative = min(tam_topdown_2025, tam_bottomup)
    sam = tam_conservative * a["target_geo_share"] * a["reachable_segment_share"]

    som = {
        "low_y3": sam * a["som_share_y3_low"],
        "mid_y3": sam * a["som_share_y3_mid"],
        "high_y3": sam * a["som_share_y3_high"],
    }

    # 敏感性：H1 在 8%~20% 区间对自上而下 TAM 的影响
    sensitivity_h1 = {
        f"{int(s * 100)}%": round(
            (a["seo_software_market_2025_usd"] * s
             + a["geo_tools_market_2025_usd"] * a["serviceable_share_of_geo_market"]) / 1e9, 2
        )
        for s in (0.08, 0.12, 0.16, 0.20)
    }

    result = {
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "assumptions": a,
        "top_down": {
            "tam_2025_usd_b": round(tam_topdown_2025 / 1e9, 2),
            "tam_2028_usd_b": round(tam_topdown_2028 / 1e9, 2),
            "seo_market_2028_usd_b": round(seo_2028 / 1e9, 2),
            "geo_market_2028_usd_b": round(geo_2028 / 1e9, 2),
        },
        "bottom_up": {
            "tam_usd_b": round(tam_bottomup / 1e9, 2),
            "segment_us_smb_usd_b": round(seg_smb / 1e9, 2),
            "segment_agencies_usd_b": round(seg_agency / 1e9, 2),
            "segment_publishers_usd_b": round(seg_publisher / 1e9, 2),
        },
        "tam_conservative_usd_b": round(tam_conservative / 1e9, 2),
        "sam_usd_b": round(sam / 1e9, 2),
        "som_y3_usd_m": {k: round(v / 1e6, 1) for k, v in som.items()},
        "sensitivity_h1_tam_topdown_usd_b": sensitivity_h1,
    }

    (DATA / "market_sizing.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # ---------------- 漏斗图 ----------------
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    labels = [
        f"TAM (conservative)\n${result['tam_conservative_usd_b']}B",
        f"SAM\n${result['sam_usd_b']}B",
        f"SOM year-3 (base)\n${result['som_y3_usd_m']['mid_y3']}M",
    ]
    values = [tam_conservative, sam, som["mid_y3"]]
    fig, ax = plt.subplots(figsize=(8, 5))
    colors = ["#4878a8", "#6aa84f", "#e69138"]
    widths = [1.0, a["target_geo_share"] * a["reachable_segment_share"], 0.05]
    for i, (label, v, w, c) in enumerate(zip(labels, values, widths, colors)):
        ax.barh(2 - i, w, height=0.6, color=c, alpha=0.85)
        ax.text(w + 0.02, 2 - i, label, va="center", fontsize=11)
    ax.set_xlim(0, 1.6)
    ax.set_ylim(-0.6, 2.6)
    ax.axis("off")
    ax.set_title("TAM / SAM / SOM (bar width = share of conservative TAM)", fontsize=12)
    fig.tight_layout()
    fig.savefig(ASSETS / "market_funnel.png", dpi=150)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("\n写出：data/market_sizing.json, assets/market_funnel.png")


if __name__ == "__main__":
    main()
