#!/usr/bin/env python3
"""真实数据快速验证通道：PV-Augmented REDD 衍生数据 → oed 统一格式。

数据源：huggingface.co/datasets/wangxudong/PV-Augmented-NILM-Datasets
（国内经 hf-mirror.com 访问）。其 REDD_house* CSV 是 REDD 真实测量
（UTC 时间戳 + 总表功率 + 家电通道，W）的论文预处理版——本脚本不冒充
原始 REDD 低频格式转换（那走 oed convert redd），而是为"真实公开数据
→ 统一规格 → 质量 → 基准"链路提供一条可自动化验证的通道。

用法：
    python scripts/import_pvaug.py CSV [CSV ...] -o out/redd-pvaug
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import pandas as pd

REPO = "https://huggingface.co/datasets/wangxudong/PV-Augmented-NILM-Datasets"
CITATION = (
    "Derived from REDD (Kolter & Johnson, SustKDD 2011) via the "
    "PV-Augmented NILM Dataset release (wangxudong, Hugging Face)."
)
SKIP_COLS = {  # 非功率辅助列
    "hour_sin", "hour_cos", "power_factor",
    "GHI", "DNI", "DHI", "Wind Speed", "Temperature",
}
APPLIANCE_TYPES = {
    "microwave": "microwave oven", "fridge": "fridge",
    "dish washer": "dish washer", "washing machine": "washing machine",
    "oven": "electric oven", "kettle": "electric kettle",
    "light": "light", "lighting": "light", "sockets": "sockets",
}


def import_csv(csv: Path, output_dir: Path) -> Path:
    from oed.converters.common import DatasetBuilder, clean_series, nominal_interval
    from oed.io import write_manifest

    df = pd.read_csv(csv, index_col=0)
    df.index = pd.to_datetime(df.index, utc=True, format="mixed")
    house_match = re.search(r"(house\d+)", csv.stem + csv.parent.name, re.IGNORECASE)
    site_id = f"redd_{house_match.group(1).lower()}" if house_match else "redd_house"

    b = DatasetBuilder(
        output_dir, name="redd-pvaug-oed",
        description="REDD 真实测量数据（PV-Augmented 预处理版）统一为 oed 格式",
        source_url=REPO, source_license="Academic research use (derived from REDD)",
        citation=CITATION, dataset_id="redd-pvaug",
        creators=["wangxudong (PV-Augmented release)", "Kolter, Zico", "Johnson, Matthew"],
        keywords=["energy", "nilm", "redd", "real-data", "oed"],
        date_published="2024-01-01")

    channels: list[dict] = []
    for col in df.columns:
        if col in SKIP_COLS or col.endswith("_state") or col.endswith("_reactive"):
            continue
        values = pd.to_numeric(df[col], errors="coerce")
        sub = pd.DataFrame({"timestamp": df.index, "power_w": values, "quality": 0})
        sub = sub.dropna()
        if sub.empty:
            continue
        if col == "aggregate_power":
            cid, role, atype = "mains", "site_meter", None
        elif col == "micro_inverter":
            cid, role, atype = "solar_pv", "submeter", "PV inverter"
        else:
            cid, role = re.sub(r"\W+", "_", col), "submeter"
            atype = APPLIANCE_TYPES.get(col, col)
        channel = {
            "id": cid, "path": f"sites/{site_id}/{cid}.parquet", "role": role,
            "physical_quantity": "power", "ac_type": "active", "unit": "W",
            "nominal_interval_s": nominal_interval(sub, fallback=1.0),
            "description": f"{col} (PV-Augmented REDD derived)",
            "appliance": ({"type": atype, "original_name": col, "instance": 1}
                          if atype else None),
        }
        b.add_channel(site_id, channel, clean_series(sub))
        channels.append(channel)

    b.add_site({"id": site_id, "original_name": house_match.group(0) if house_match else site_id,
                "timezone": "UTC", "geo": {"country": "US", "locality": "Massachusetts"},
                "channels": channels})
    path = write_manifest(b.build(), output_dir)
    print(f"✅ 导入 {csv.name}: {len(channels)} 通道 → {path}")
    return path


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("csvs", nargs="+", type=Path, help="PV-Augmented REDD csv 文件")
    ap.add_argument("-o", "--output", type=Path, required=True)
    args = ap.parse_args()
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
    for csv in args.csvs:
        import_csv(csv, args.output)


if __name__ == "__main__":
    main()
