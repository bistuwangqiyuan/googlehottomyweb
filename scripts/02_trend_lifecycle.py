# -*- coding: utf-8 -*-
"""
02_trend_lifecycle.py — 热词/热点话题的注意力生命周期实证分析（一手数据 [D2]）

方法（全程数据驱动，无人工挑选，任何第三方可复现）：
1. 在 2025 年每月各取一个采样日（每月 15 日），调用 Wikimedia Pageviews API 的
   top 端点，取英文维基百科当日浏览量 Top 50 文章；
2. 过滤站务页面（Main_Page、Special:、Wikipedia: 等）；
3. 对每篇候选文章拉取其前后各 60 天的逐日浏览量；
4. 判定"事件驱动型热点"：峰值日浏览量 / 峰值前 30 天基线中位数 >= 5；
5. 对热点样本计算生命周期指标：
   - half_life_days：峰值后浏览量首次跌破峰值 50% 所需天数
   - decay_to_10pct_days：跌破峰值 10%（相对基线以上部分）所需天数
   - first3day_share：峰值起 30 天窗口内，前 3 天占总超额浏览量的比例

数据源：Wikimedia REST API（CC0 开放许可，无需鉴权）
    https://wikimedia.org/api/rest_v1/

产出：
    data/lifecycle_candidates.csv   全部候选与判定结果
    data/lifecycle_metrics.csv      热点样本的生命周期指标
    data/lifecycle_summary.json     汇总统计（供报告正文引用）
    assets/lifecycle_decay.png      衰减曲线图（归一化叠加 + 中位数曲线）
    assets/lifecycle_hist.png       半衰期分布直方图

说明：维基百科浏览量是"公众注意力"的公开代理指标，与 Google 搜索热度高度同源
（同一事件同时驱动搜索与百科浏览）。选它是因为 Google Trends 不提供绝对量的
逐日历史 API，而 Wikimedia 数据绝对量、逐日、开放、可复现。
"""
import csv
import json
import statistics
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
ASSETS = ROOT / "assets"
DATA.mkdir(exist_ok=True)
ASSETS.mkdir(exist_ok=True)

API = "https://wikimedia.org/api/rest_v1/metrics/pageviews"
UA = {"User-Agent": "trend-lifecycle-research/1.0 (reproducible business research)"}

SAMPLE_DATES = [date(2025, m, 15) for m in range(1, 13)]
TOP_N = 50
SPIKE_RATIO_THRESHOLD = 5.0
WINDOW_BEFORE = 60
WINDOW_AFTER = 60

META_PREFIXES = (
    "Main_Page", "Special:", "Wikipedia:", "Portal:", "Help:", "File:",
    "Template:", "Category:", "Talk:", "User:", "Module:", "Draft:",
)


def get_json(url: str, retries: int = 3) -> dict | None:
    for i in range(retries):
        try:
            r = requests.get(url, headers=UA, timeout=30)
            if r.status_code == 200:
                return r.json()
            if r.status_code == 404:
                return None
            time.sleep(2 * (i + 1))
        except requests.RequestException:
            time.sleep(2 * (i + 1))
    return None


def top_articles(day: date) -> list[str]:
    url = f"{API}/top/en.wikipedia/all-access/{day:%Y/%m/%d}"
    js = get_json(url)
    if not js:
        return []
    arts = js["items"][0]["articles"]
    names = [a["article"] for a in arts]
    return [n for n in names if not n.startswith(META_PREFIXES)][:TOP_N]


def daily_series(article: str, start: date, end: date) -> dict[date, int]:
    url = (
        f"{API}/per-article/en.wikipedia/all-access/user/"
        f"{article}/daily/{start:%Y%m%d}/{end:%Y%m%d}"
    )
    js = get_json(url)
    if not js:
        return {}
    out = {}
    for item in js.get("items", []):
        ts = item["timestamp"]  # YYYYMMDDHH
        out[date(int(ts[:4]), int(ts[4:6]), int(ts[6:8]))] = item["views"]
    return out


def analyze(article: str, sample_day: date) -> dict | None:
    start = sample_day - timedelta(days=WINDOW_BEFORE)
    end = min(sample_day + timedelta(days=WINDOW_AFTER), date(2026, 7, 1))
    series = daily_series(article, start, end)
    if len(series) < 60:
        return None
    days = sorted(series)
    views = [series[d] for d in days]

    peak_idx = max(range(len(views)), key=views.__getitem__)
    peak_day, peak_views = days[peak_idx], views[peak_idx]

    baseline_window = views[max(0, peak_idx - 40): max(1, peak_idx - 10)]
    if len(baseline_window) < 10:
        return None
    baseline = statistics.median(baseline_window)
    ratio = peak_views / max(baseline, 1)

    rec = {
        "article": article,
        "sample_day": sample_day.isoformat(),
        "peak_day": peak_day.isoformat(),
        "peak_views": peak_views,
        "baseline_median": int(baseline),
        "spike_ratio": round(ratio, 2),
        "is_spike": ratio >= SPIKE_RATIO_THRESHOLD,
    }
    if not rec["is_spike"]:
        return rec

    # 峰值后的衰减指标（超额浏览量 = 浏览量 - 基线）
    post = views[peak_idx:]
    half_life = next(
        (i for i, v in enumerate(post) if v - baseline < 0.5 * (peak_views - baseline)),
        None,
    )
    decay10 = next(
        (i for i, v in enumerate(post) if v - baseline < 0.1 * (peak_views - baseline)),
        None,
    )
    horizon = post[:30]
    excess = [max(v - baseline, 0) for v in horizon]
    total_excess = sum(excess)
    first3_share = sum(excess[:3]) / total_excess if total_excess > 0 else None

    rec.update(
        half_life_days=half_life,
        decay_to_10pct_days=decay10,
        first3day_share=round(first3_share, 4) if first3_share is not None else None,
        post_peak_days_observed=len(post),
        # 归一化衰减曲线（峰值=1，基线=0），供绘图
        norm_curve=json.dumps(
            [round(max(v - baseline, 0) / max(peak_views - baseline, 1), 4) for v in post[:31]]
        ),
    )
    return rec


def main() -> None:
    print("步骤 1/3：抓取 2025 年 12 个采样日的英文维基 Top50 文章 ...")
    candidates: dict[str, date] = {}
    for d in SAMPLE_DATES:
        arts = top_articles(d)
        print(f"  {d}: {len(arts)} 篇")
        for a in arts:
            candidates.setdefault(a, d)  # 同一文章只取首次出现的采样日
        time.sleep(0.3)
    print(f"  去重后候选文章：{len(candidates)} 篇")

    print("步骤 2/3：逐篇拉取 ±60 天逐日浏览量并判定热点 ...")
    all_recs, spikes = [], []
    for i, (art, d) in enumerate(candidates.items(), 1):
        rec = analyze(art, d)
        if rec:
            all_recs.append(rec)
            if rec["is_spike"]:
                spikes.append(rec)
        if i % 50 == 0:
            print(f"  进度 {i}/{len(candidates)}，已识别热点 {len(spikes)} 个")
        time.sleep(0.15)
    print(f"  完成：候选 {len(all_recs)}，事件驱动型热点 {len(spikes)}")

    cand_fields = [
        "article", "sample_day", "peak_day", "peak_views",
        "baseline_median", "spike_ratio", "is_spike",
    ]
    with (DATA / "lifecycle_candidates.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=cand_fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(all_recs)

    spike_fields = cand_fields + [
        "half_life_days", "decay_to_10pct_days", "first3day_share",
        "post_peak_days_observed", "norm_curve",
    ]
    with (DATA / "lifecycle_metrics.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=spike_fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(spikes)

    print("步骤 3/3：汇总统计与图表 ...")
    hl = [r["half_life_days"] for r in spikes if r["half_life_days"] is not None]
    d10 = [r["decay_to_10pct_days"] for r in spikes if r["decay_to_10pct_days"] is not None]
    f3 = [r["first3day_share"] for r in spikes if r["first3day_share"] is not None]

    def qtile(vals, q):
        if not vals:
            return None
        s = sorted(vals)
        return s[min(int(q * len(s)), len(s) - 1)]

    summary = {
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "method": "en.wikipedia top-50 on 12 monthly sample days in 2025; spike = peak/baseline >= 5",
        "n_candidates": len(all_recs),
        "n_spikes": len(spikes),
        "spike_share_of_top50": round(len(spikes) / max(len(all_recs), 1), 4),
        "half_life_days": {
            "median": qtile(hl, 0.5), "p25": qtile(hl, 0.25), "p75": qtile(hl, 0.75), "n": len(hl),
        },
        "decay_to_10pct_days": {
            "median": qtile(d10, 0.5), "p25": qtile(d10, 0.25), "p75": qtile(d10, 0.75), "n": len(d10),
        },
        "first3day_share_of_30d_excess": {
            "median": qtile(f3, 0.5), "p25": qtile(f3, 0.25), "p75": qtile(f3, 0.75), "n": len(f3),
        },
    }
    (DATA / "lifecycle_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    curves = [json.loads(r["norm_curve"]) for r in spikes if r.get("norm_curve")]
    fig, ax = plt.subplots(figsize=(9, 5.5))
    for c in curves:
        ax.plot(range(len(c)), c, color="steelblue", alpha=0.12, lw=1)
    max_len = max((len(c) for c in curves), default=0)
    med_curve = [
        statistics.median([c[i] for c in curves if len(c) > i]) for i in range(max_len)
    ]
    ax.plot(range(len(med_curve)), med_curve, color="crimson", lw=2.5, label="Median decay curve")
    ax.axhline(0.5, color="gray", ls="--", lw=0.8)
    ax.axhline(0.1, color="gray", ls=":", lw=0.8)
    ax.set_xlabel("Days after peak")
    ax.set_ylabel("Normalized excess attention (peak=1)")
    ax.set_title(f"Attention decay of {len(curves)} event-driven spikes (en.wikipedia, 2025)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(ASSETS / "lifecycle_decay.png", dpi=150)

    fig2, ax2 = plt.subplots(figsize=(8, 5))
    ax2.hist(hl, bins=range(0, 32), color="steelblue", edgecolor="white")
    ax2.set_xlabel("Half-life (days after peak)")
    ax2.set_ylabel("Number of spikes")
    ax2.set_title("Distribution of attention half-life")
    fig2.tight_layout()
    fig2.savefig(ASSETS / "lifecycle_hist.png", dpi=150)

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print("\n写出文件：lifecycle_candidates.csv / lifecycle_metrics.csv / lifecycle_summary.json")
    print("图表：assets/lifecycle_decay.png, assets/lifecycle_hist.png")


if __name__ == "__main__":
    main()
