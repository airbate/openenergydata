#!/usr/bin/env python3
"""LCL 清洗版 Feather（Sufiyan83 发布，约 4.8GB / 1.1 亿读数）→ oed 统一格式。

按 Arrow IPC record batch 读取所需三列，再按户写临时分片。
只在第二阶段物化单户的数据，排序去重后生成 Parquet 与行数审计。
整数编码户号必须显式指定命名空间，不自动猜测与原始 MAC 户号的映射。

用法：
    python scripts/import_lcl_feather.py df_2011.feather [df_2012.feather ...] \
        -o out/lcl --work shards/ --value-unit kWh [--limit 500]
"""
from __future__ import annotations

import argparse
import json
import tempfile
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


def pass_one(feathers: list[Path], work: Path, limit: int | None,
             encoded_id_prefix: str | None = None) -> dict[str, list[Path]]:
    """Read only three columns in bounded IPC batches; never materialize a file."""
    import pyarrow as pa

    if limit is not None and limit <= 0:
        raise ValueError("limit must be positive")
    if work.exists() and any(work.iterdir()):
        raise ValueError("work directory must be empty; existing files are preserved")
    work.mkdir(parents=True, exist_ok=True)
    shards: dict[str, list[Path]] = {}
    keep: set[str] = set()
    audit = []
    for file_index, fea in enumerate(feathers):
        counts = {"file": str(fea), "source_rows": 0, "valid_rows": 0,
                  "selected_rows": 0, "encoded_id_prefix": encoded_id_prefix}
        print(f"[pass1] stream {fea.name}", flush=True)
        with pa.memory_map(str(fea), "r") as source:
            schema = pa.ipc.open_file(source).schema
            kwh = kwh_column(schema.names)
            names = ["DateTime", "LCLid", kwh]
            options = pa.ipc.IpcReadOptions(
                included_fields=[schema.get_field_index(n) for n in names])
            reader = pa.ipc.open_file(source, options=options)
            for batch_index in range(reader.num_record_batches):
                batch = reader.get_batch(batch_index)
                for start in range(0, batch.num_rows, SLICE_ROWS):
                    sl = batch.slice(start, SLICE_ROWS).select(names).to_pandas(ignore_metadata=True)
                    sl.columns = ["timestamp", "lclid", "kwh"]
                    counts["source_rows"] += len(sl)
                    sl["timestamp"] = pd.to_datetime(sl["timestamp"], utc=True, errors="coerce")
                    sl["kwh"] = pd.to_numeric(sl["kwh"], errors="coerce")
                    sl = sl.dropna()
                    counts["valid_rows"] += len(sl)
                    if pd.api.types.is_numeric_dtype(sl["lclid"].dtype):
                        if not encoded_id_prefix:
                            raise ValueError(f"{fea}: encoded numeric household IDs require --encoded-id-prefix; no original ID mapping is known")
                        sl["lclid"] = encoded_id_prefix + sl["lclid"].astype(str)
                    else:
                        sl["lclid"] = sl["lclid"].astype(str)
                    if limit:
                        for value in sl["lclid"].drop_duplicates():
                            if len(keep) < limit:
                                keep.add(value)
                        sl = sl[sl["lclid"].isin(keep)]
                    counts["selected_rows"] += len(sl)
                    for group_index, (lclid, g) in enumerate(sl.groupby("lclid", observed=True)):
                        path = work / f"{file_index}_{batch_index}_{start}_{group_index}.pkl"
                        g[["timestamp", "kwh"]].to_pickle(path)
                        shards.setdefault(str(lclid), []).append(path)
                if batch_index % 100 == 0:
                    print(f"  batch {batch_index + 1}/{reader.num_record_batches}: {counts['source_rows']:,} rows, {len(shards)} households", flush=True)
        audit.append(counts)
    (work / "source-audit.json").write_text(json.dumps(audit, indent=2))
    return shards


def pass_two(shards: dict[str, list[Path]], output: Path, value_unit: str = "kWh") -> Path:
    if value_unit not in ("kWh", "normalized"):
        raise ValueError("value_unit must be kWh or normalized")
    from oed.converters.common import DatasetBuilder, clean_series, nominal_interval
    from oed.io import write_manifest

    b = DatasetBuilder(
        output, name="lcl-oed",
        description=f"Low Carbon London 智能电表数据（本次导入 {len(shards)} 个户号 / {value_unit}）；覆盖范围见 source-audit.json",
        source_url="https://data.london.gov.uk/dataset/smartmeter-energy-use-data-at-half-hour-interval",
        source_license="UK OGL v3",
        citation=CITATION, dataset_id="lcl",
        creators=["UK Power Networks", "Greater London Authority"],
        keywords=["energy", "smart-meter", "lcl", "oed"],
        date_published="2015-01-01")
    totals = {"input_rows": 0, "output_rows": 0, "duplicates_removed": 0}
    for i, (lclid, paths) in enumerate(sorted(shards.items()), 1):
        parts = [pd.read_pickle(p) for p in paths]
        df = pd.concat(parts, ignore_index=True)
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        sub = pd.DataFrame({"timestamp": df["timestamp"],
                            "power_w": df["kwh"].astype("float32"), "quality": 0})
        totals["input_rows"] += len(sub)
        sub = clean_series(sub)
        totals["output_rows"] += len(sub)
        site_id = lclid.lower().replace("/", "_")
        channel = {
            "id": "energy", "path": f"sites/{site_id}/energy.parquet",
            "role": "site_meter", "physical_quantity": "normalized" if value_unit == "normalized" else "energy",
            "ac_type": "active", "unit": "1" if value_unit == "normalized" else "kWh",
            "nominal_interval_s": nominal_interval(sub, fallback=1800.0),
            "description": "normalized dimensionless reading" if value_unit == "normalized" else "half-hourly energy (kWh)", "appliance": None,
        }
        b.add_channel(site_id, channel, sub)
        b.add_site({"id": site_id, "original_name": lclid,
                    "timezone": "UTC",
                    "geo": {"country": "GB", "locality": "London"},
                    "channels": [channel]})
        if i % 250 == 0:
            print(f"[pass2] {i}/{len(shards)} 户", flush=True)
    totals["duplicates_removed"] = totals["input_rows"] - totals["output_rows"]
    totals["households"] = len(shards)
    output.mkdir(parents=True, exist_ok=True)
    (output / "import-audit.json").write_text(json.dumps(totals, indent=2))
    return write_manifest(b.build(), output)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("feathers", nargs="+", type=Path)
    ap.add_argument("-o", "--output", type=Path, required=True)
    ap.add_argument("--work", type=Path, default=Path("shards"))
    ap.add_argument("--limit", type=int, default=None, help="仅导入前 N 户（调试用）")
    ap.add_argument("--encoded-id-prefix", help="Explicit namespace for numeric IDs; does not recover original household identity")
    ap.add_argument("--value-unit", choices=["kWh", "normalized"], required=True, help="Declare verified source value semantics; encoded 2012 release uses normalized")
    args = ap.parse_args()
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
    args.work.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="lcl-", dir=args.work) as temporary:
        work = Path(temporary)
        shards = pass_one(args.feathers, work, args.limit, args.encoded_id_prefix)
        manifest_path = pass_two(shards, args.output, args.value_unit)
        manifest = json.loads(manifest_path.read_text())
        manifest["name"] = args.output.name
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
        (args.output / "source-audit.json").write_bytes((work / "source-audit.json").read_bytes())
    print(f"✅ 完成: {len(shards)} 户 → {manifest_path}")


if __name__ == "__main__":
    main()
