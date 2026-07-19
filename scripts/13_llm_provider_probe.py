# -*- coding: utf-8 -*-
"""
13_llm_provider_probe.py — LLM 供应商可用性探测（可复现，key 从环境变量读取，不入库）

用与流水线完全相同的请求形态（OpenAI 兼容 /chat/completions +
response_format=json_object）逐一探测各家 API key 是否真实可用，
输出 data/llm_provider_probe.json（脱敏：只记录 key 前 8 位指纹）。

运行前把各家 key 放入环境变量（见 PROVIDERS 表），然后：
    python scripts/13_llm_provider_probe.py
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
OUT_JSON = ROOT / "data" / "llm_provider_probe.json"

# 与 pipeline.generate/review 一致的请求形态
PROBE_MESSAGES = [
    {"role": "system", "content": 'Reply with VALID JSON only: {"ok": true, "model_family": "<your model family name>"}'},
    {"role": "user", "content": "probe"},
]

PROVIDERS = [
    {"name": "deepseek", "env": "DEEPSEEK_API_KEY", "base_url": "https://api.deepseek.com/v1", "model": "deepseek-chat"},
    {"name": "glm (zhipu)", "env": "GLM_API_KEY", "base_url": "https://open.bigmodel.cn/api/paas/v4", "model": "glm-4-flash"},
    {"name": "moonshot", "env": "MOONSHOT_API_KEY", "base_url": "https://api.moonshot.cn/v1", "model": "moonshot-v1-8k"},
    {"name": "tongyi (dashscope)", "env": "TONGYI_API_KEY", "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1", "model": "qwen-plus"},
    {"name": "tencent hunyuan", "env": "TENGCENT_API_KEY", "base_url": "https://api.hunyuan.cloud.tencent.com/v1", "model": "hunyuan-turbos-latest"},
    {"name": "spark (iflytek)", "env": "SPARK_API_KEY", "base_url": "https://spark-api-open.xf-yun.com/v1", "model": "generalv3.5"},
    {"name": "doubao (ark)", "env": "DOUBAO_API_KEY", "base_url": "https://ark.cn-beijing.volces.com/api/v3", "model": "doubao-1-5-pro-32k-250115"},
]


def probe_openai_compatible(base_url: str, api_key: str, model: str) -> dict:
    t0 = time.time()
    try:
        resp = requests.post(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "temperature": 0.2,
                "response_format": {"type": "json_object"},
                "messages": PROBE_MESSAGES,
            },
            timeout=60,
        )
        latency = round(time.time() - t0, 2)
        if resp.status_code != 200:
            return {"usable": False, "latency_s": latency,
                    "error": f"HTTP {resp.status_code}: {resp.text[:300]}"}
        content = resp.json()["choices"][0]["message"]["content"]
        json.loads(content)  # 必须是合法 JSON（流水线依赖）
        return {"usable": True, "latency_s": latency, "sample": content[:120]}
    except Exception as exc:
        return {"usable": False, "latency_s": round(time.time() - t0, 2), "error": str(exc)[:300]}


def probe_anthropic(api_key: str) -> dict:
    t0 = time.time()
    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": api_key, "anthropic-version": "2023-06-01",
                     "Content-Type": "application/json"},
            json={"model": "claude-3-5-haiku-latest", "max_tokens": 32,
                  "messages": [{"role": "user", "content": "Reply with the word ok"}]},
            timeout=60,
        )
        latency = round(time.time() - t0, 2)
        if resp.status_code != 200:
            return {"usable": False, "latency_s": latency,
                    "error": f"HTTP {resp.status_code}: {resp.text[:300]}"}
        return {"usable": True, "latency_s": latency,
                "note": "anthropic 原生协议，与流水线 OpenAI 兼容接口不同，接入需适配层"}
    except Exception as exc:
        return {"usable": False, "latency_s": round(time.time() - t0, 2), "error": str(exc)[:300]}


def probe_gemini(api_key: str) -> dict:
    t0 = time.time()
    try:
        resp = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}",
            json={"contents": [{"parts": [{"text": "Reply with the word ok"}]}]},
            timeout=60,
        )
        latency = round(time.time() - t0, 2)
        if resp.status_code != 200:
            return {"usable": False, "latency_s": latency,
                    "error": f"HTTP {resp.status_code}: {resp.text[:300]}"}
        return {"usable": True, "latency_s": latency}
    except Exception as exc:
        return {"usable": False, "latency_s": round(time.time() - t0, 2), "error": str(exc)[:300]}


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    results = []
    for p in PROVIDERS:
        key = os.environ.get(p["env"], "").strip()
        if not key:
            results.append({"provider": p["name"], "usable": False, "error": f"env {p['env']} not set"})
            continue
        r = probe_openai_compatible(p["base_url"], key, p["model"])
        r.update(provider=p["name"], base_url=p["base_url"], model=p["model"],
                 key_fingerprint=key[:8] + "...")
        results.append(r)
        print(f"[{p['name']}] usable={r['usable']} latency={r.get('latency_s')}s "
              f"{r.get('error', '')[:120]}")

    for name, env, fn in (("anthropic", "ANTHROPIC_API_KEY", probe_anthropic),
                          ("gemini", "GEMINI_API_KEY", probe_gemini)):
        key = os.environ.get(env, "").strip()
        if not key:
            results.append({"provider": name, "usable": False, "error": f"env {env} not set"})
            continue
        r = fn(key)
        r.update(provider=name, key_fingerprint=key[:8] + "...")
        results.append(r)
        print(f"[{name}] usable={r['usable']} latency={r.get('latency_s')}s {r.get('error', '')[:120]}")

    out = {"probed_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "method": "identical request shape to pipeline.generate/review "
                     "(OpenAI-compatible chat/completions + response_format=json_object)",
           "results": results}
    OUT_JSON.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n写出 {OUT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
