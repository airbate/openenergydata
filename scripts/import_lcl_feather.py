#!/usr/bin/env python3
"""LCL 清洗版 Feather（Sufiyan83 发布，约 4.8GB / 1.1 亿读数）→ oed 统一格式。

内存友好的两段式流处理（本机 7.6GB RAM，单个 2012 年文件磁盘 2.9GB）：
  Pass 1: 每个 feather 按 ~2M 行切片 → 组内按 LCLid 分组 → 写每户每年
          的 pickle 分片（shards/）。
  Pass 2: 每户合并其全部分片 → 排序去重 → 写最终 channel parquet + 清单。

用法：
    python scripts/import_lcl_feather.py df_2011.feather [df_2012.feather ...] \
        -o out/lcl --work shards/ [--limit 500]
"""
from __future__ import annotations

import argparse
import pickle
import re
import shutil
import sys
from pathlib import Path

import pandas as pd

REPO = "https://hf-mirror.com/datasets/Sufiyan83/Low-Carbon-London-Smart-Meter-Cleaned-FeatureReady"
CITATION = (
    "Low Carbon London smart meter energy consumption data (UK Power "
    "Networks / London Datastore, OGL v3); cleaned Feather release by "
    "S. Rehman (Hugging Face)."
)
KWH_COL_CANDIDATES = ("KWH/hh (per half hour)", "KWH/hh (per half hour) ", "KWH/hh")
SLICE_ROWS = 2_000_000


def kwh_column(cols: list[str]) -> str:
    for c in KWH_COL_CANDIDATES:
        if c in cols:
            return c
    raise SystemExit(f"找不到 kWh 列，现有列: {cols}")


def pass_one(feathers: list[Path], work: Path, limit: int | None) -> dict[str, list[Path]]:
    """切片分组，写每户每年分片；返回 household → shard 文件列表。

    使用 pyarrow 内存映射 + 逐切片物化（每片约 2M 行），避免把
    2.9GB 的 feather 整体读入内存触发 OOM。
    """
    import pyarrow.feather as pa_feather

    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    shards: dict[str, list[Path]] = {}
    n_slices = 0
    for fea in feathers:
        print(f"[pass1] 读 {fea.name} (mmap)...", flush=True)
        tbl = pa_feather.read_table(fea, memory_map=True)
        kwh = kwh_column(list(tbl.column_names))
        cols = tbl.select(["DateTime", "LCLid", kwh])
        n = cols.num_rows
        if limit:
            # 先小物化一次取前 N 户名单
            head = cols.slice(0, min(n, 500_000)).to_pandas()
            head.columns = ["timestamp", "lclid", "kwh"]
            keep = set(head["lclid"].dropna().drop_duplicates().iloc[:limit])
            del head
            print(f"[pass1] limit 模式: 仅导入 {len(keep)} 户", flush=True)
        for start in range(0, n, SLICE_ROWS):
            n_slices += 1
            sl = cols.slice(start, SLICE_ROWS).to_pandas()
            sl.columns = ["timestamp", "lclid", "kwh"]
            sl = sl.dropna()
            if limit:
                sl = sl[sl["lclid"].isin(keep)]
            for lclid, g in sl.groupby("lclid", observed=True):
                p = work / f"{lclid}_{fea.stem}.pkl"
                g[["timestamp", "kwh"]].to_pickle(p)
                shards.setdefault(str(lclid), []).append(p)
            print(f"  slice {start}: 累计 {len(shards)} 户", flush=True)
            del sl
        print(f"[pass1] {fea.name} 完成", flush=True)
    print(f"[pass1] 全部完成: {len(shards)} 户, {n_slices} 个切片", flush=True)
    return shards


def pass_two(shards: dict[str, list[Path]], output: Path) -> Path:
    from oed.converters.common import DatasetBuilder, clean_series, nominal_interval
    from oed.io import write_manifest

    b = DatasetBuilder(
        output, name="lcl-oed",
        description="Low Carbon London 智能电表数据（5,567 户 / 半小时 kWh）统一为 oed 格式",
        source_url="https://data.london.gov.uk/dataset/smartmeter-energy-use-data-at-half-hour-interval",
        source_license="UK OGL v3",
        citation=CITATION, dataset_id="lcl",
        creators=["UK Power Networks", "Greater London Authority"],
        keywords=["energy", "smart-meter", "lcl", "oed"],
        date_published="2015-01-01")
    for i, (lclid, paths) in enumerate(sorted(shards.items()), 1):
        parts = [pd.read_pickle(p) for p in paths]
        df = pd.concat(parts, ignore_index=True)
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        sub = pd.DataFrame({"timestamp": df["timestamp"],
                            "power_w": df["kwh"].astype("float32"), "quality": 0})
        sub = clean_series(sub)
        site_id = lclid.lower().replace("/", "_")
        channel = {
            "id": "energy", "path": f"sites/{site_id}/energy.parquet",
            "role": "site_meter", "physical_quantity": "energy",
            "ac_type": "active", "unit": "kWh",
            "nominal_interval_s": nominal_interval(sub, fallback=1800.0),
            "description": "half-hourly energy (kWh)", "appliance": None,
        }
        b.add_channel(site_id, channel, sub)
        b.add_site({"id": site_id, "original_name": lclid,
                    "timezone": "UTC",
                    "geo": {"country": "GB", "locality": "London"},
                    "channels": [channel]})
        if i % 250 == 0:
            print(f"[pass2] {i}/{len(shards)} 户", flush=True)
    return write_manifest(b.build(), output)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("feathers", nargs="+", type=Path)
    ap.add_argument("-o", "--output", type=Path, required=True)
    ap.add_argument("--work", type=Path, default=Path("shards"))
    ap.add_argument("--limit", type=int, default=None, help="仅导入前 N 户（调试用）")
    args = ap.parse_args()
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
    shards = pass_one(args.feathers, args.work, args.limit)
    manifest_path = pass_two(shards, args.output)
    print(f"✅ 完成: {len(shards)} 户 → {manifest_path}")


if __name__ == "__main__":
    main()
