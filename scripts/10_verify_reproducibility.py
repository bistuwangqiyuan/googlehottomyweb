# -*- coding: utf-8 -*-
"""
10_verify_reproducibility.py — 全链复现性自动验证（任何第三方可执行）

验证目标：兑现附录 C 的"可复现"承诺——重跑全部计算脚本，断言输出与仓库内
提交的数据一致（确定性脚本逐数值比对；联网脚本按其性质分级验证）。

分级验证策略：
  A. 确定性脚本（03/04/05/06/08/09）：重跑后输出 JSON 必须与重跑前逐数值一致
     （忽略 generated_utc 时间戳；浮点用容差比较）；CSV 必须逐行一致；
     图表 PNG 必须重新生成且非空。
  B. 01（Google Trends 实时热词）：结果随时点变化，验证的是"方法可复现"——
     跑通、输出 schema 合法后，恢复 2026-07-14 快照基线（保住正文引用的审计链），
     并删除本次运行新产生的原始 XML。
  C. 02（Wikimedia 历史数据）：2025 年历史数据的核心统计应复现。实测发现
     Wikimedia per-article 端点的单篇数据可用性存在小幅时点波动（多次运行的
     有效候选数在 ±15% 内波动，但半衰期/衰减天数的中位数与四分位完全稳定），
     故验证标准为：分布统计精确一致 + 样本量在容差带内；验证后恢复提交基线
     （正文引用的审计锚点），与 01 的处理一致。
  D. 07（docx 导出）：对两份完整版 md 实际导出，断言 docx 生成且体积合理。

用法：
    python scripts/10_verify_reproducibility.py                 # 全量（含联网，最慢）
    python scripts/10_verify_reproducibility.py --offline       # 仅确定性脚本
    python scripts/10_verify_reproducibility.py --skip-lifecycle # 跳过最慢的 02

退出码：0 = 全部执行的检查通过；1 = 存在失败项。
"""
import argparse
import csv
import io
import json
import math
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
DATA = ROOT / "data"
ASSETS = ROOT / "assets"

VOLATILE_KEYS = {"generated_utc"}

RESULTS: list[dict] = []


def record(check: str, passed: bool, detail: str = "") -> None:
    RESULTS.append({"check": check, "passed": passed, "detail": detail})
    mark = "PASS" if passed else "FAIL"
    print(f"[{mark}] {check}" + (f" — {detail}" if detail else ""))


def json_diff(a, b, path="$") -> list[str]:
    """递归比较两个 JSON 值，返回差异列表（忽略 VOLATILE_KEYS，浮点容差比较）。"""
    diffs = []
    if isinstance(a, dict) and isinstance(b, dict):
        keys = (set(a) | set(b)) - VOLATILE_KEYS
        for k in sorted(keys):
            if k not in a:
                diffs.append(f"{path}.{k}: 仅存在于新输出")
            elif k not in b:
                diffs.append(f"{path}.{k}: 仅存在于基线")
            else:
                diffs.extend(json_diff(a[k], b[k], f"{path}.{k}"))
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            diffs.append(f"{path}: 列表长度 {len(a)} != {len(b)}")
        else:
            for i, (x, y) in enumerate(zip(a, b)):
                diffs.extend(json_diff(x, y, f"{path}[{i}]"))
    elif isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool) and not isinstance(b, bool):
        if not math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-9):
            diffs.append(f"{path}: {a} != {b}")
    elif a != b:
        diffs.append(f"{path}: {a!r} != {b!r}")
    return diffs


def run_script(name: str, args: list[str] | None = None, timeout: int = 3600) -> bool:
    cmd = [sys.executable, str(SCRIPTS / name)] + (args or [])
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=timeout, cwd=str(ROOT))
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-8:]
        record(f"运行 {name}", False, "退出码 %d：%s" % (proc.returncode, " | ".join(tail)))
        return False
    return True


def verify_deterministic(script: str, json_outputs: list[str], csv_outputs: list[str],
                         png_outputs: list[str]) -> None:
    """重跑前保存基线，重跑后逐数值比对。"""
    baselines_json = {}
    for rel in json_outputs:
        p = DATA / rel
        if not p.exists():
            record(f"{script}: 基线 {rel}", False, "基线文件缺失")
            return
        baselines_json[rel] = json.loads(p.read_text(encoding="utf-8"))
    baselines_csv = {}
    for rel in csv_outputs:
        p = DATA / rel
        if not p.exists():
            record(f"{script}: 基线 {rel}", False, "基线文件缺失")
            return
        baselines_csv[rel] = p.read_text(encoding="utf-8-sig")

    t0 = time.time()
    if not run_script(script):
        return

    ok_all = True
    for rel, base in baselines_json.items():
        new = json.loads((DATA / rel).read_text(encoding="utf-8"))
        diffs = json_diff(new, base)
        if diffs:
            ok_all = False
            record(f"{script}: {rel} 与基线一致", False, "; ".join(diffs[:5]) +
                   (f"（共 {len(diffs)} 处差异）" if len(diffs) > 5 else ""))
        else:
            record(f"{script}: {rel} 与基线一致", True)
    for rel, base in baselines_csv.items():
        new = (DATA / rel).read_text(encoding="utf-8-sig")
        same = new.replace("\r\n", "\n") == base.replace("\r\n", "\n")
        record(f"{script}: {rel} 与基线一致", same, "" if same else "CSV 内容有差异")
        ok_all = ok_all and same
    for rel in png_outputs:
        p = ASSETS / rel
        fresh = p.exists() and p.stat().st_size > 1000 and p.stat().st_mtime >= t0 - 1
        record(f"{script}: 图表 {rel} 重新生成", fresh,
               "" if fresh else "文件缺失/为空/未更新")
        ok_all = ok_all and fresh


def verify_trending_now() -> None:
    """01：方法可复现验证（schema 校验后恢复 2026-07-14 快照基线）。"""
    csv_path = DATA / "trending_now.csv"
    json_path = DATA / "trending_now_summary.json"
    base_csv = csv_path.read_bytes()
    base_json = json_path.read_bytes()
    raw_before = set((DATA / "raw").glob("*.xml"))

    try:
        if not run_script("01_fetch_trending_now.py"):
            return
        # schema 校验
        with csv_path.open(encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
        expected_cols = {"geo", "keyword", "approx_traffic_text", "approx_traffic_lower_bound",
                         "pub_date", "news_item_count", "first_news_title", "snapshot_utc"}
        cols_ok = rows and set(rows[0].keys()) == expected_cols
        record("01: CSV schema 合法", bool(cols_ok),
               f"{len(rows)} 行，geo 覆盖 {sorted({r['geo'] for r in rows}) if rows else []}")
        summary = json.loads(json_path.read_text(encoding="utf-8"))
        keys_ok = {"snapshot_utc", "source", "geos", "total"} <= set(summary)
        total_ok = summary.get("total", {}).get("trend_count", 0) > 0
        record("01: summary JSON schema 合法且非空", keys_ok and total_ok,
               f"total.trend_count={summary.get('total', {}).get('trend_count')}")
    finally:
        # 恢复审计基线（正文引用的是 2026-07-14 快照），删除本次新增的原始 XML
        csv_path.write_bytes(base_csv)
        json_path.write_bytes(base_json)
        for p in set((DATA / "raw").glob("*.xml")) - raw_before:
            p.unlink()
        print("  （已恢复 2026-07-14 快照基线，删除本次运行新增的原始 XML）")


def verify_lifecycle() -> None:
    """02：核心统计复现验证（慢，约 500 次 API 调用），验证后恢复提交基线。"""
    files = ["lifecycle_summary.json", "lifecycle_candidates.csv", "lifecycle_metrics.csv"]
    pngs = ["lifecycle_decay.png", "lifecycle_hist.png"]
    baselines = {f: (DATA / f).read_bytes() for f in files}
    png_baselines = {f: (ASSETS / f).read_bytes() for f in pngs if (ASSETS / f).exists()}
    base = json.loads(baselines["lifecycle_summary.json"].decode("utf-8"))
    print("  （02 需拉取约 500 篇文章的历史浏览量，预计 3-10 分钟）")
    try:
        if not run_script("02_trend_lifecycle.py", timeout=3600):
            return
        new = json.loads((DATA / "lifecycle_summary.json").read_text(encoding="utf-8"))

        problems = []
        # 分布统计：中位数/四分位必须精确一致（历史数据的稳健结论）
        for key in ("half_life_days", "decay_to_10pct_days"):
            for q in ("median", "p25", "p75"):
                if new[key][q] != base[key][q]:
                    problems.append(f"{key}.{q}: {new[key][q]} != {base[key][q]}")
        for q in ("median", "p25", "p75"):
            a, b = new["first3day_share_of_30d_excess"][q], base["first3day_share_of_30d_excess"][q]
            if abs(a - b) > 0.02:
                problems.append(f"first3day.{q}: {a} 偏离基线 {b} 超过 0.02")
        # 样本量：容差带 ±15%（per-article 端点可用性存在时点波动，如实声明）
        for key in ("n_candidates", "n_spikes"):
            a, b = new[key], base[key]
            if abs(a - b) / b > 0.15:
                problems.append(f"{key}: {a} 偏离基线 {b} 超过 15%")
        if abs(new["spike_share_of_top50"] - base["spike_share_of_top50"]) > 0.02:
            problems.append("spike_share_of_top50 偏离超过 0.02")

        record("02: 核心统计复现（中位数/四分位精确一致，样本量±15%）",
               not problems, "; ".join(problems[:6]) if problems else
               f"重跑样本 n_spikes={new['n_spikes']}（基线 {base['n_spikes']}），分布统计一致")
    finally:
        for f, content in baselines.items():
            (DATA / f).write_bytes(content)
        for f, content in png_baselines.items():
            (ASSETS / f).write_bytes(content)
        print("  （已恢复提交基线数据与图表——正文引用的审计锚点）")


def verify_docx_export() -> None:
    """07：两份完整版文档实际导出。"""
    targets = [
        (ROOT / "opportunity-report" / "商业机会挖掘与分析报告-完整版.md", []),
        (ROOT / "business-plan" / "商业计划书-完整版.md", ["商业计划书"]),
    ]
    for md, extra in targets:
        out = md.with_suffix(".docx")
        t0 = time.time()
        if not run_script("07_export_docx.py", [str(md)] + extra, timeout=600):
            continue
        ok = out.exists() and out.stat().st_size > 100_000 and out.stat().st_mtime >= t0 - 1
        record(f"07: {out.name} 导出", ok,
               f"{out.stat().st_size // 1024} KB" if out.exists() else "文件未生成")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="跳过全部联网脚本（01/02/07）")
    ap.add_argument("--skip-lifecycle", action="store_true", help="跳过最慢的 02")
    args = ap.parse_args()

    print("=" * 72)
    print("全链复现性验证  ", datetime.now(timezone.utc).isoformat(timespec="seconds"))
    print("=" * 72)

    print("\n--- A. 确定性脚本：重跑并与基线逐数值比对 ---")
    verify_deterministic("03_market_sizing.py", ["market_sizing.json"], [], ["market_funnel.png"])
    verify_deterministic("04_opportunity_scoring.py", ["opportunity_scores.json"], [], ["opportunity_scores.png"])
    verify_deterministic("05_unit_economics.py", ["unit_economics.json"], [], ["site_breakeven.png"])
    verify_deterministic("06_financial_model.py", ["financial_model.json"],
                         ["financial_model_monthly.csv"], ["financial_scenarios.png"])
    verify_deterministic("08_niche_selection.py", ["niche_selection.json"], [], ["niche_scores.png"])
    verify_deterministic("09_monte_carlo.py", ["monte_carlo.json"], [],
                         ["mc_distributions.png", "mc_tornado.png"])

    if not args.offline:
        print("\n--- B. 01 Google Trends：方法可复现（结果随时点变化）---")
        verify_trending_now()
        if not args.skip_lifecycle:
            print("\n--- C. 02 Wikimedia 历史数据：精确复现 ---")
            verify_lifecycle()
        else:
            print("\n--- C. 02 已按 --skip-lifecycle 跳过 ---")
        print("\n--- D. 07 docx 导出 ---")
        verify_docx_export()
    else:
        print("\n--- B/C/D 已按 --offline 跳过（01/02/07 未验证）---")

    n_fail = sum(1 for r in RESULTS if not r["passed"])
    print("\n" + "=" * 72)
    print(f"结果：{len(RESULTS) - n_fail}/{len(RESULTS)} 项通过" +
          (f"，{n_fail} 项失败" if n_fail else "，全部通过"))
    for r in RESULTS:
        if not r["passed"]:
            print(f"  FAIL: {r['check']} — {r['detail']}")
    sys.exit(1 if n_fail else 0)


if __name__ == "__main__":
    main()
