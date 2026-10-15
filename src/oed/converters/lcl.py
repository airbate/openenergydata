"""Low Carbon London (LCL) converter: smart-meter half-hourly kWh.

Input: CSV file(s) with columns
    LCLid, stdorToU, DateTime, KWH/hh (per half hour), Acorn, Acorn_grouped
Each LCLid household becomes one site with a single energy channel
(kWh, 1800 s nominal interval). Timestamps are GMT.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from oed.converters.common import DatasetBuilder, clean_series, nominal_interval

DATASET_ID = "lcl"
SOURCE_URL = "https://data.london.gov.uk/dataset/smartmeter-energy-use-data-at-half-hour-interval"
SOURCE_LICENSE = "OGL v3 (UK Open Government Licence)"
CITATION = (
    "Low Carbon London: smart meter energy consumption data in London "
    "households, UK Data Service / London Datastore."
)


class LclConverter:
    dataset_id = DATASET_ID
    source_url = SOURCE_URL
    source_license = SOURCE_LICENSE
    citation = CITATION

    def convert(self, input_dir: Path, output_dir: Path) -> Path:
        from oed.io import write_manifest

        input_dir, output_dir = Path(input_dir), Path(output_dir)
        files = sorted(input_dir.glob("*.csv"))
        if not files:
            raise FileNotFoundError(f"no *.csv under {input_dir}")
        b = DatasetBuilder(
            output_dir, name="lcl-oed",
            description="Low Carbon London smart-meter data in the oed unified format",
            source_url=SOURCE_URL, source_license=SOURCE_LICENSE,
            citation=CITATION, dataset_id=DATASET_ID,
            creators=["UK Power Networks", "Greater London Authority"],
            keywords=["energy", "smart-meter", "lcl", "oed"],
            date_published="2015-01-01")
        for f in files:
            self._convert_file(f, b)
        return write_manifest(b.build(), output_dir)

    def _convert_file(self, f: Path, b: DatasetBuilder) -> None:
        df = pd.read_csv(f, usecols=["LCLid", "DateTime", "KWH/hh "])
        # the raw header carries a trailing space: normalize defensively
        df.columns = [c.strip() for c in df.columns]
        energy_col = "KWH/hh"
        if energy_col not in df.columns:
            energy_col = [c for c in df.columns if c.lower().startswith("kwh")][0]
        df[energy_col] = pd.to_numeric(df[energy_col], errors="coerce")
        ts = pd.to_datetime(df["DateTime"], dayfirst=True).dt.tz_localize("UTC")
        for lclid, group in df.groupby("LCLid"):
            site_id = str(lclid).lower().replace("/", "_")
            if any(s["id"] == site_id for s in b.sites):
                continue
            sub = pd.DataFrame({
                "timestamp": ts[group.index],
                "power_w": group[energy_col].to_numpy(),
                "quality": 0,
            }).dropna()
            sub = sub[sub["power_w"].notna()]
            if sub.empty:
                continue
            rel = f"sites/{site_id}/energy.parquet"
            channel = {
                "id": "energy", "path": rel, "role": "site_meter",
                "physical_quantity": "energy", "ac_type": "active", "unit": "kWh",
                "nominal_interval_s": nominal_interval(sub, fallback=1800.0),
                "description": "half-hourly energy (kWh)",
                "appliance": None,
            }
            b.add_channel(site_id, channel, clean_series(sub))
            b.add_site({"id": site_id, "original_name": str(lclid),
                        "timezone": "UTC", "channels": [channel]})
