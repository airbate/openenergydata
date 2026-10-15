"""蒙西电网边界条件数据集转换器（自有原生格式数据集）。

Input: 数据集根目录（含 data/train/mengxi_boundary_anon_filtered.csv）
或直接指向该 CSV。取各 *_实际值 列作为通道（预测值列为模型特征，
不入库）；站点为蒙西电网，单位 MW，时区 Asia/Shanghai。

注：原始仓库使用 Git LFS，转换前需 `git lfs pull` 拉取实体文件。
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from oed.converters.common import DatasetBuilder, clean_series, nominal_interval

DATASET_ID = "mengxi"
SOURCE_URL = "https://modelscope.cn/datasets/AI_camp_energy_2026"
SOURCE_LICENSE = "Dataset provided for the 2026 AI camp energy competition"
CITATION = "AI Camp Energy 2026: 蒙西电网节点电价预测竞赛数据集."

CHANNEL_SPECS = [
    ("system_load", "系统负荷实际值", "site_meter", "系统总负荷"),
    ("wind", "风电实际值", "submeter", "风电出力"),
    ("solar", "光伏实际值", "submeter", "光伏出力"),
    ("hydro", "水电实际值", "submeter", "水电出力"),
    ("tie_line", "联络线实际值", "submeter", "省间联络线功率"),
    ("non_market", "非市场化机组实际值", "submeter", "非市场化机组出力"),
]
TIME_COLUMN = "times"


class MengxiConverter:
    dataset_id = DATASET_ID
    source_url = SOURCE_URL
    source_license = SOURCE_LICENSE
    citation = CITATION

    def convert(self, input_dir: Path, output_dir: Path) -> Path:
        from oed.io import write_manifest

        input_dir = Path(input_dir)
        csv = self._locate(input_dir)
        df = pd.read_csv(csv)
        if TIME_COLUMN not in df.columns:
            raise ValueError(f"missing '{TIME_COLUMN}' column in {csv}")
        ts = self._parse_times(df[TIME_COLUMN])

        b = DatasetBuilder(
            output_dir, name="mengxi-oed",
            description="蒙西电网边界条件时序（负荷/新能源/联络线），oed 统一格式",
            source_url=SOURCE_URL, source_license=SOURCE_LICENSE,
            citation=CITATION, dataset_id=DATASET_ID,
            creators=["AI Camp Energy 2026"],
            keywords=["energy", "grid", "renewables", "mengxi", "oed"])
        site_id = "mengxi_grid"
        channels = []
        for cid, col, role, desc in CHANNEL_SPECS:
            if col not in df.columns:
                continue
            values = pd.to_numeric(df[col], errors="coerce")
            sub = pd.DataFrame({"timestamp": ts, "power_w": values, "quality": 0})
            sub = sub.dropna(subset=["timestamp"])
            sub = sub[sub["power_w"].notna()]
            if sub.empty:
                continue
            rel = f"sites/{site_id}/{cid}.parquet"
            channel = {
                "id": cid, "path": rel, "role": role,
                "physical_quantity": "power", "ac_type": "active", "unit": "MW",
                "nominal_interval_s": nominal_interval(sub, fallback=900.0),
                "description": desc,
                "appliance": None,
            }
            b.add_channel(site_id, channel, clean_series(sub))
            channels.append(channel)
        b.add_site({"id": site_id, "original_name": "蒙西电网",
                    "timezone": "Asia/Shanghai",
                    "geo": {"country": "CN", "locality": "内蒙古"},
                    "channels": channels})
        return write_manifest(b.build(), output_dir)

    @staticmethod
    def _locate(input_dir: Path) -> Path:
        candidates = [
            input_dir / "data" / "train" / "mengxi_boundary_anon_filtered.csv",
            input_dir / "mengxi_boundary_anon_filtered.csv",
        ]
        for c in candidates:
            if c.is_file():
                return c
        found = list(input_dir.rglob("mengxi_boundary_anon*.csv"))
        if found:
            return found[0]
        raise FileNotFoundError(
            f"mengxi_boundary_anon_filtered.csv not found under {input_dir}")

    @staticmethod
    def _parse_times(s: pd.Series) -> pd.Series:
        ts = pd.to_datetime(s, errors="coerce")
        numeric = pd.to_numeric(s, errors="coerce")
        epoch = numeric.notna() & ts.isna()
        if epoch.any():
            unit = "ms" if numeric.dropna().abs().max() > 1e12 else "s"
            ts.loc[epoch] = pd.to_datetime(numeric.loc[epoch], unit=unit)
        return ts.dt.tz_localize("Asia/Shanghai",
                                 nonexistent="shift_forward").dt.tz_convert("UTC")
