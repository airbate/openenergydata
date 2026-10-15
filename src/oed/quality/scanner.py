"""Deterministic quality scanner (v0).

Checks per channel:
  * gaps            -- timestamp deltas larger than ``gap_factor`` x nominal
  * impossible      -- negative power (physically impossible here)
  * outlier         -- power above plausibility ceilings
  * zero_run        -- sustained exact-zero sequences longer than a threshold
  * unit_anomaly    -- submeter statistics suggesting a W/kW mix-up
  * jitter (info)   -- high sampling-interval dispersion
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from oed.io import load_manifest, read_channel_parquet, write_channel_parquet
from oed.quality_flags import QualityFlag

SEVERITY_WEIGHT = {"info": 0.0, "warning": 1.0, "critical": 4.0}


@dataclass
class ScanConfig:
    gap_factor: float = 3.0
    zero_run_minutes: float = 60.0
    max_site_w: float = 50_000.0
    max_sub_w: float = 20_000.0
    sub_unit_anomaly_median_w: float = 10_000.0
    jitter_cv_threshold: float = 0.5


def scan_channel(df: pd.DataFrame, channel: dict, cfg: ScanConfig) -> list[dict]:
    findings: list[dict] = []
    site = channel["role"] == "site_meter"
    ts = df["timestamp"]
    power = df["power_w"]
    diffs = ts.diff().dt.total_seconds().dropna()
    nominal = float(diffs.median()) if len(diffs) else channel.get("nominal_interval_s", 1.0)

    where = f"{channel['path']}"

    # gaps
    gap_mask = diffs > cfg.gap_factor * nominal
    for idx in diffs[gap_mask].index:
        findings.append({
            "type": "gap", "severity": "warning", "channel": where,
            "start": str(ts.loc[idx - 1]) if idx - 1 in ts.index else None,
            "end": str(ts.loc[idx]),
            "detail": f"采样间隔 {diffs.loc[idx]:.1f}s 超过标称 {nominal:.1f}s 的 {cfg.gap_factor} 倍",
        })

    # impossible values
    neg = power < 0
    for idx in power[neg].index[:5]:
        findings.append({
            "type": "impossible_value", "severity": "critical", "channel": where,
            "start": str(ts.loc[idx]), "end": str(ts.loc[idx]),
            "detail": f"负功率 {power.loc[idx]:.1f} W（该量纲下物理不可能）",
        })
    if int(neg.sum()) > 5:
        findings.append({
            "type": "impossible_value", "severity": "critical", "channel": where,
            "start": str(ts[neg.idxmin()]), "end": str(ts[neg.idxmax()]),
            "detail": f"共 {int(neg.sum())} 个负功率样本",
        })

    # outliers
    ceiling = cfg.max_site_w if site else cfg.max_sub_w
    out = power > ceiling
    if int(out.sum()):
        findings.append({
            "type": "outlier", "severity": "warning", "channel": where,
            "start": str(ts[out.idxmax()]), "end": str(ts[out.idxmax()]),
            "detail": f"{int(out.sum())} 个样本超过 {ceiling:.0f} W 合理性上限，"
                      f"最大 {power.max():.0f} W",
        })

    # zero runs
    zero_run_s = cfg.zero_run_minutes * 60.0
    min_zero_samples = max(2, int(zero_run_s / max(nominal, 0.1)))
    is_zero = (power == 0).to_numpy()
    i, n = 0, len(is_zero)
    while i < n:
        if is_zero[i]:
            j = i
            while j + 1 < n and is_zero[j + 1]:
                j += 1
            if j - i + 1 >= min_zero_samples:
                findings.append({
                    "type": "zero_run", "severity": "warning", "channel": where,
                    "start": str(ts.iloc[i]), "end": str(ts.iloc[j]),
                    "detail": f"持续零功率约 {(j - i + 1) * nominal / 60:.0f} 分钟",
                })
            i = j + 1
        else:
            i += 1

    # unit anomaly heuristic (submeters only)
    if not site:
        med = float(power.median()) if len(power) else 0.0
        if med > cfg.sub_unit_anomaly_median_w:
            findings.append({
                "type": "unit_anomaly", "severity": "critical", "channel": where,
                "start": str(ts.iloc[0]), "end": str(ts.iloc[-1]),
                "detail": f"子表功率中位数 {med:.0f} W，疑似原始单位为 kW 而未换算",
            })

    # jitter info
    if len(diffs) > 10:
        cv = float(diffs.std() / diffs.mean()) if diffs.mean() else 0.0
        if cv > cfg.jitter_cv_threshold:
            findings.append({
                "type": "jitter", "severity": "info", "channel": where,
                "start": str(ts.iloc[0]), "end": str(ts.iloc[-1]),
                "detail": f"采样间隔变异系数 {cv:.2f}（标称 {nominal:.1f}s），读取时建议重采样",
            })
    return findings


def scan_dataset(output_dir: Path, cfg: ScanConfig | None = None,
                 annotate: bool = False) -> dict:
    cfg = cfg or ScanConfig()
    output_dir = Path(output_dir)
    manifest = load_manifest(output_dir)
    all_findings: list[dict] = []
    n_channels = 0
    for site in manifest["x-oed"]["sites"]:
        for channel in site["channels"]:
            path = output_dir / channel["path"]
            df = read_channel_parquet(path)
            n_channels += 1
            findings = scan_channel(df, channel, cfg)
            all_findings.extend(findings)
            if annotate:
                df = _annotate(df, findings)
                write_channel_parquet(df, path)

    summary = {t: sum(1 for f in all_findings if f["type"] == t)
               for t in sorted({f["type"] for f in all_findings})}
    penalty = sum(SEVERITY_WEIGHT[f["severity"]] for f in all_findings)
    score = max(0.0, round(100.0 - penalty / max(n_channels, 1) * 10.0, 1))
    return {
        "dataset": manifest["name"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "channels_scanned": n_channels,
        "config": cfg.__dict__,
        "summary": summary,
        "quality_score": score,
        "findings": all_findings,
    }


def _annotate(df: pd.DataFrame, findings: list[dict]) -> pd.DataFrame:
    """Best-effort: mark samples covered by each finding range with flags."""
    ts = df["timestamp"]
    flags: dict[str, int] = {name: QualityFlag[name.upper()].value for name in (
        "gap", "outlier", "zero_run", "unit_anomaly", "impossible_value")}
    for f in findings:
        bit = flags.get(f["type"])
        if not bit or not f.get("start") or not f.get("end"):
            continue
        lo = pd.Timestamp(f["start"])
        hi = pd.Timestamp(f["end"])
        mask = (ts >= lo) & (ts <= hi)
        df.loc[mask, "quality"] = df.loc[mask, "quality"] | bit
    return df


def write_report(report: dict, output_dir: Path) -> Path:
    import json
    (output_dir / "quality-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        f"# 质量报告 · {report['dataset']}",
        "",
        f"- 扫描时间: {report['generated_at']}",
        f"- 通道数: {report['channels_scanned']}",
        f"- 质量得分: **{report['quality_score']} / 100**",
        f"- 发现汇总: {report['summary'] or '无'}",
        "",
        "| 级别 | 类型 | 通道 | 时间范围 | 说明 |",
        "|---|---|---|---|---|",
    ]
    for f in report["findings"]:
        lines.append(
            f"| {f['severity']} | {f['type']} | {f['channel']} "
            f"| {str(f['start'])[:19]} ~ {str(f['end'])[:19]} | {f['detail']} |")
    path = output_dir / "quality-report.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
