"""Forecasting benchmark: baselines on aggregate (site_meter) channels.

Task: predict the next ``horizon`` samples of each site's aggregate power
channel, given its history. Split is temporal (train = first
``train_frac``). Baselines are deliberately simple and reproducible:

  * naive        -- persist the last observed value
  * daily_profile-- per time-of-day mean estimated on the train split
  * seasonal_lag -- value observed 24 h earlier (naive fallback)

Energy channels (kWh per interval) are converted to average power before
forecasting so all datasets share the W/MW semantics of their channel.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from oed.io import load_manifest, read_channel_parquet


def _series_for_benchmark(df: pd.DataFrame, channel: dict) -> pd.Series:
    from oed.units import watts_factor
    unit = _benchmark_unit(channel)
    scale = {"W": 1.0, "kW": 1000.0, "MW": 1_000_000.0}.get(unit)
    if scale is None:
        raise ValueError(f"Unsupported benchmark unit: {unit}")
    return df["power_w"] * (watts_factor(channel) / scale)


def _benchmark_unit(channel: dict) -> str:
    unit = channel.get("unit", "W")
    # Energy-per-interval values are converted to average power above.
    if channel.get("physical_quantity") == "energy":
        return {"Wh": "W", "kWh": "kW", "MWh": "MW"}.get(unit, unit)
    return unit


def _metrics(actual: np.ndarray, pred: np.ndarray, unit: str) -> dict:
    err = actual - pred
    mae = float(np.abs(err).mean())
    rmse = float(np.sqrt((err ** 2).mean()))
    nz = np.abs(actual) > 1e-9
    mape = float((np.abs(err[nz] / actual[nz])).mean() * 100) if nz.any() else 0.0
    return {"mae": round(mae, 3), "rmse": round(rmse, 3),
            "mape_pct": round(mape, 2), "unit": unit, "n_test": int(len(actual))}


def run_forecast(dataset_dir: Path, train_frac: float = 0.8) -> list[dict]:
    dataset_dir = Path(dataset_dir)
    manifest = load_manifest(dataset_dir)
    rows: list[dict] = []
    for site in manifest["x-oed"]["sites"]:
        agg = [c for c in site["channels"] if c["role"] == "site_meter"]
        if not agg:
            continue
        channel = agg[0]
        df = read_channel_parquet(dataset_dir / channel["path"])
        series = _series_for_benchmark(df, channel).reset_index(drop=True)
        if len(series) < 20:
            continue
        unit = _benchmark_unit(channel)
        n_train = int(len(series) * train_frac)
        train, test = series.iloc[:n_train], series.iloc[n_train:]
        times = df["timestamp"].reset_index(drop=True)

        baselines: dict[str, np.ndarray] = {
            "naive": np.full(len(test), train.iloc[-1]),
        }
        # daily profile
        local = times.dt.tz_convert(site.get("timezone", "UTC"))
        key = local.dt.strftime("%H:%M")
        profile = train.groupby(key.iloc[:n_train]).mean()
        fallback = float(train.mean())
        baselines["daily_profile"] = np.array(
            [profile.get(k, fallback) for k in key.iloc[n_train:]])
        # seasonal lag (24 h) with naive fallback
        nominal = float(pd.Series(times.diff().dt.total_seconds()).median() or 1.0)
        lag = max(1, int(round(24 * 3600 / nominal)))
        def lag_or_naive(i):
            j = i - lag
            return series.iloc[j] if j >= 0 else train.iloc[-1]
        baselines["seasonal_lag_24h"] = np.array(
            [lag_or_naive(i) for i in range(n_train, len(series))])

        for name, pred in baselines.items():
            m = _metrics(test.to_numpy(), pred, unit)
            rows.append({"task": "forecast", "dataset": manifest["name"],
                         "site": site["id"], "channel": channel["id"],
                         "baseline": name, **m})
    return rows


# ---------------------------------------------------------------------
# NILM evaluation framework (v0: daily-profile persistence baseline)
# ---------------------------------------------------------------------

def run_nilm(dataset_dir: Path, train_frac: float = 0.8) -> list[dict]:
    """Evaluate per-submeter predictions against ground-truth submetering.

    Baseline ``daily_profile`` predicts each submeter's time-of-day mean
    learned on the train split. Metric MAE is per appliance; SAE is the
    Signal Aggregate Error over the test window. This is the reference
    point that learned NILM algorithms must beat.
    """
    dataset_dir = Path(dataset_dir)
    manifest = load_manifest(dataset_dir)
    rows: list[dict] = []
    for site in manifest["x-oed"]["sites"]:
        subs = [c for c in site["channels"] if c["role"] == "submeter"]
        if not subs:
            continue
        for channel in subs:
            df = read_channel_parquet(dataset_dir / channel["path"])
            series = _series_for_benchmark(df, channel).reset_index(drop=True)
            if len(series) < 20:
                continue
            n_train = int(len(series) * train_frac)
            train, test = series.iloc[:n_train], series.iloc[n_train:]
            times = df["timestamp"].reset_index(drop=True)
            local = times.dt.tz_convert(site.get("timezone", "UTC"))
            key = local.dt.strftime("%H:%M")
            profile = train.groupby(key.iloc[:n_train]).mean()
            fallback = float(train.mean())
            pred = np.array([profile.get(k, fallback) for k in key.iloc[n_train:]])
            actual = test.to_numpy()
            m = _metrics(actual, pred, _benchmark_unit(channel))
            gt_energy = float(np.abs(actual).sum())
            pred_energy = float(np.abs(pred).sum())
            m["sae_pct"] = round(
                abs(pred_energy - gt_energy) / gt_energy * 100, 2) if gt_energy else 0.0
            appliance = (channel.get("appliance") or {}).get("type", channel["id"])
            rows.append({"task": "nilm", "dataset": manifest["name"],
                         "site": site["id"], "channel": channel["id"],
                         "appliance": appliance, "baseline": "daily_profile", **m})
    return rows


def write_leaderboard(rows: list[dict], dataset_dir: Path) -> Path:
    import json

    dataset_dir = Path(dataset_dir)
    (dataset_dir / "benchmark.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# oed 基准排行榜",
        "",
        "切分: 前 80% 训练 / 后 20% 测试（时间顺序）。指标: MAE/RMSE（通道单位）, MAPE%。",
        "",
        "| 任务 | 数据集 | 站点 | 通道/电器 | 基线 | MAE | RMSE | MAPE% | SAE% |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| {r['task']} | {r['dataset']} | {r['site']} "
            f"| {r.get('appliance', r['channel'])} | {r['baseline']} "
            f"| {r['mae']} | {r['rmse']} | {r['mape_pct']} | {r.get('sae_pct', '')} |")
    path = dataset_dir / "benchmark.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
