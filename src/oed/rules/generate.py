"""Rule generators: heuristic knowledge base + LLM (OpenAI-compatible).

The heuristic generator mines channel statistics and a built-in appliance
knowledge base to propose plausible domain rules. The LLM generator sends
the schema digest plus per-channel statistics to any OpenAI-compatible
endpoint (OED_LLM_BASE_URL / OED_LLM_API_KEY / OED_LLM_MODEL) and parses
its JSON answer into the same rule list. Both mark rules as unconfirmed --
a human always has the last word.
"""
from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path

from oed.io import load_manifest, read_channel_parquet
from oed.rules.dsl import Rule

APPLIANCE_BOUNDS_W = {
    "fridge": (0, 400),
    "fridge-freezer": (0, 500),
    "electric oven": (0, 5500),
    "microwave oven": (0, 2000),
    "electric kettle": (0, 3000),
    "washing machine": (0, 2500),
    "dish washer": (0, 2500),
    "electric furnace": (0, 8000),
    "air conditioner": (0, 4000),
    "light": (0, 1200),
    "television": (0, 400),
    "electric space heater": (0, 3000),
    "pump": (0, 1500),
}


def channel_stats(dataset_dir: Path) -> list[dict]:
    dataset_dir = Path(dataset_dir)
    manifest = load_manifest(dataset_dir)
    stats = []
    for site in manifest["x-oed"]["sites"]:
        for ch in site["channels"]:
            df = read_channel_parquet(dataset_dir / ch["path"])
            p = df["power_w"]
            appliance = ch.get("appliance") or {}
            stats.append({
                "site": site["id"], "channel": ch["id"], "path": ch["path"],
                "role": ch["role"], "quantity": ch.get("physical_quantity"),
                "unit": ch.get("unit"),
                "appliance_type": appliance.get("type"),
                "n": int(len(p)),
                "median_w": None if p.empty else round(float(p.median()), 2),
                "p99_w": None if p.empty else round(float(p.quantile(0.99)), 2),
                "max_w": None if p.empty else round(float(p.max()), 2),
                "min_w": None if p.empty else round(float(p.min()), 2),
                "zero_ratio": None if p.empty else round(float((p == 0).mean()), 4),
            })
    return stats


def generate_heuristic(dataset_dir: Path) -> list[Rule]:
    rules: list[Rule] = []
    seen_types: set[str] = set()
    for s in channel_stats(dataset_dir):
        atype = s.get("appliance_type")
        if atype and atype in APPLIANCE_BOUNDS_W and atype not in seen_types:
            lo, hi = APPLIANCE_BOUNDS_W[atype]
            seen_types.add(atype)
            rules.append(Rule(
                id=f"bounds-{atype.replace(' ', '-')}",
                description=f"{atype} 功率合理范围为 {lo}-{hi} W（家电常识库）",
                selector={"appliance_type": atype},
                check={"type": "bounds", "min": lo, "max": hi, "unit": "W"},
                severity="warning", origin="heuristic", confirmed=False))
        # per-channel p99 sanity
        if s.get("max_w") is not None and s["max_w"] > 0:
            ceiling = max(3.0 * max(s["max_w"], 1.0), 1.0)
            rules.append(Rule(
                id=f"sanity-{s['site']}-{s['channel']}",
                description=f"{s['site']}/{s['channel']} 数值不应为负",
                selector={"channel_id": s["channel"]},
                check={"type": "min", "value": 0, "unit": s.get("unit", "W")},
                severity="critical", origin="heuristic", confirmed=False))
    return _dedupe(rules)


def generate_llm(dataset_dir: Path, timeout_s: int = 60) -> list[Rule]:
    base = os.environ.get("OED_LLM_BASE_URL", "").rstrip("/")
    api_key = os.environ.get("OED_LLM_API_KEY", "")
    model = os.environ.get("OED_LLM_MODEL", "qwen2.5-7b-instruct")
    if not base or not api_key:
        raise RuntimeError(
            "未配置 LLM 端点。请设置 OED_LLM_BASE_URL / OED_LLM_API_URL 兼容变量：\n"
            "  export OED_LLM_BASE_URL=https://api.deepseek.com/v1   # 或本地 vLLM/Ollama\n"
            "  export OED_LLM_API_KEY=sk-...\n"
            "  export OED_LLM_MODEL=deepseek-chat\n"
            "未配置时可先使用 --heuristic 生成规则。")

    stats = channel_stats(dataset_dir)
    prompt = (
        "你是电网与家电领域的的数据质量专家。以下是能耗数据集的通道统计：\n"
        + json.dumps(stats, ensure_ascii=False, indent=1)
        + "\n请提出最多 8 条数据质量规则，仅输出 JSON（无其他文字），格式：\n"
        '[{"id":"kebab-case-id","description":"中文说明","appliance_type":null,'
        '"channel_id":null,"role":null,"check":{"type":"bounds|max|min|'
        'median_above|zero_run", ...},"severity":"warning|critical"}]\n'
        "check 参数：bounds 用 min/max；max/min 用 value；zero_run 用 minutes；"
        "median_above 用 value。单位均为 W（或通道声明的单位）。"
    )
    body = json.dumps({
        "model": model, "temperature": 0.2,
        "messages": [{"role": "user", "content": prompt}],
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{base}/chat/completions", data=body,
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {api_key}"})
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        content = json.loads(resp.read())["choices"][0]["message"]["content"]
    content = content.strip().removeprefix("```json").removesuffix("```").strip()
    proposed = json.loads(content)
    rules = []
    for p in proposed[:8]:
        selector = {k: p[k] for k in ("appliance_type", "channel_id", "role") if p.get(k)}
        rules.append(Rule(
            id=p["id"], description=p.get("description", ""),
            selector=selector or None, check=p["check"],
            severity=p.get("severity", "warning"),
            origin="llm", confirmed=False))
    return rules


def _dedupe(rules: list[Rule]) -> list[Rule]:
    seen: set[str] = set()
    out = []
    for r in rules:
        if r.id not in seen:
            seen.add(r.id)
            out.append(r)
    return out
