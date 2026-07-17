# -*- coding: utf-8 -*-
"""
07_export_docx.py — 将合并版 Markdown 导出为 docx

处理步骤：
1. 将文中 ```mermaid 代码块渲染为 PNG（mermaid.ink 公共渲染服务；失败则保留代码块并提示）；
2. 用 pandoc（pypandoc-binary）转换为 docx，图片全部内嵌。

用法：
    py scripts/07_export_docx.py                # 默认导出机会报告完整版
    py scripts/07_export_docx.py <md路径> <文档标题>   # 导出任意合并版 md
"""
import base64
import json
import re
import sys
from pathlib import Path

import requests

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
if len(sys.argv) >= 2:
    SRC = Path(sys.argv[1]).resolve()
    TITLE = sys.argv[2] if len(sys.argv) >= 3 else SRC.stem
else:
    SRC = ROOT / "opportunity-report" / "商业机会挖掘与分析报告-完整版.md"
    TITLE = "商业机会挖掘与分析报告"
OUT = SRC.with_suffix(".docx")
ASSETS = ROOT / "assets"

MERMAID_RE = re.compile(r"```mermaid\n(.*?)```", re.S)


def render_mermaid(code: str, idx: int) -> str | None:
    """通过 mermaid.ink 将 mermaid 源码渲染为 PNG，返回相对 md 的图片路径。"""
    state = json.dumps({"code": code.strip(), "mermaid": {"theme": "default"}})
    payload = base64.urlsafe_b64encode(state.encode("utf-8")).decode("ascii")
    url = f"https://mermaid.ink/img/{payload}?type=png&bgColor=FFFFFF&width=1400&scale=2"
    try:
        r = requests.get(url, timeout=60)
        if r.status_code == 200 and r.headers.get("content-type", "").startswith("image"):
            out = ASSETS / f"mermaid_{SRC.parent.name}_{idx}.png"
            out.write_bytes(r.content)
            print(f"  [OK] mermaid #{idx} -> {out.name} ({len(r.content)} bytes)")
            return f"../assets/{out.name}"
        print(f"  [FAIL] mermaid #{idx}: HTTP {r.status_code} {r.text[:300]}")
    except requests.RequestException as exc:
        print(f"  [FAIL] mermaid #{idx}: {exc}")
    return None


def main() -> None:
    text = SRC.read_text(encoding="utf-8")

    print("步骤 1/2：渲染 mermaid 图 ...")
    idx = 0

    def repl(m: re.Match) -> str:
        nonlocal idx
        idx += 1
        img = render_mermaid(m.group(1), idx)
        if img:
            return f"![流程图]({img})"
        return m.group(0)  # 渲染失败则保留代码块

    text = MERMAID_RE.sub(repl, text)

    tmp = SRC.with_suffix(".docx.tmp.md")
    tmp.write_text(text, encoding="utf-8")

    print("步骤 2/2：pandoc 转换为 docx ...")
    import pypandoc

    pypandoc.convert_file(
        str(tmp),
        "docx",
        outputfile=str(OUT),
        extra_args=[
            f"--resource-path={SRC.parent};{ROOT}",
            "--toc",
            "--toc-depth=2",
            "--metadata", f"title={TITLE}",
            "--metadata", "lang=zh-CN",
        ],
    )
    tmp.unlink()
    size_kb = OUT.stat().st_size / 1024
    print(f"完成：{OUT}（{size_kb:.0f} KB）")


if __name__ == "__main__":
    main()
