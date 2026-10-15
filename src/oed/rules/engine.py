"""Rule execution engine: runs confirmed rules over a unified dataset."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from oed.io import load_manifest, read_channel_parquet
from oed.rules.dsl import Rule


def run_rules(dataset_dir: Path, rules: list[Rule]) -> list[dict]:
    """Execute rules (only confirmed ones are honoured by callers, but the
    engine itself runs whatever it is given) and return findings."""
    dataset_dir = Path(dataset_dir)
    manifest = load_manifest(dataset_dir)
    findings: list[dict] = []
    for site in manifest["x-oed"]["sites"]:
        for channel in site["channels"]:
            df = read_channel_parquet(dataset_dir / channel["path"])
            for rule in rules:
                if not rule.matches(channel):
                    continue
                findings.extend(_run_one(rule, channel, df))
    return findings


def _run_one(rule: Rule, channel: dict, df: pd.DataFrame) -> list[dict]:
    out: list[dict] = []
    where = channel["path"]
    ts, power = df["timestamp"], df["power_w"]
    c = rule.check
    kind = c["type"]

    def emit(mask, detail):
        if not mask.any():
            return
        idx = mask[mask].index
        out.append({
            "type": f"rule:{rule.id}", "severity": rule.severity, "channel": where,
            "start": str(ts.loc[idx[0]]), "end": str(ts.loc[idx[-1]]),
            "detail": f"[{rule.id}] {rule.description} -- {detail}"
            f"（来源: {rule.origin}, 审核: {rule.reviewed_by or '未审核'}）",
        })

    if kind == "bounds":
        emit((power < c["min"]) | (power > c["max"]),
             f"{int(((power < c['min']) | (power > c['max'])).sum())} 个样本越界 "
             f"[{c['min']}, {c['max']}] {c.get('unit', 'W')}")
    elif kind == "max":
        emit(power > c["value"], f"超过上限 {c['value']}")
    elif kind == "min":
        emit(power < c["value"], f"低于下限 {c['value']}")
    elif kind == "median_above":
        if len(power) and float(power.median()) > c["value"]:
            emit(pd.Series(True, index=power.index[:1]),
                 f"中位数 {float(power.median()):.0f} 高于 {c['value']}")
    elif kind == "zero_run":
        threshold_s = float(c.get("minutes", 60)) * 60.0
        nominal = float(df["timestamp"].diff().dt.total_seconds().median() or 1.0)
        need = max(2, int(threshold_s / max(nominal, 0.1)))
        is_zero = (power == 0).to_numpy()
        i, n = 0, len(is_zero)
        hit = pd.Series(False, index=power.index)
        while i < n:
            if is_zero[i]:
                j = i
                while j + 1 < n and is_zero[j + 1]:
                    j += 1
                if j - i + 1 >= need:
                    hit.iloc[i:j + 1] = True
                i = j + 1
            else:
                i += 1
        emit(hit, f"零功率持续超过 {c.get('minutes', 60)} 分钟")
    return out


def render_findings(findings: list[dict]) -> str:
    lines = [
        "# 规则评注报告",
        "",
        "| 级别 | 规则 | 通道 | 时间范围 | 说明 |",
        "|---|---|---|---|---|",
    ]
    for f in findings:
        lines.append(
            f"| {f['severity']} | {f['type'].removeprefix('rule:')} | {f['channel']} "
            f"| {str(f['start'])[:19]} ~ {str(f['end'])[:19]} | {f['detail']} |")
    if len(findings) == 0:
        lines.append("| -- | -- | -- | -- | 无命中 |")
    return "\n".join(lines) + "\n"
