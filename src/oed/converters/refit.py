"""REFIT converter: per-building CSV, power in kW, 8-second sampling.

Input: House_<n>.csv files with columns
    Time (UTC wall clock), Unix, Aggregate, Appliance1..Appliance9
Power columns are kW in the source and are converted to W.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from oed.converters.common import DatasetBuilder, clean_series, nominal_interval

DATASET_ID = "refit"
SOURCE_URL = "https://pureportal.strath.ac.uk/en/datasets/refit-smart-home-electricity-consumption-dataset"
SOURCE_LICENSE = "CC-BY-NC-SA 4.0 (see project page)"
CITATION = (
    "Stephen Makonin et al. Electricity disaggregation via viral adaptive "
    "LOADing (VAL). eGnosis 2016. REFIT: Electrical load measurements, "
    "2013-2015, University of Strathclyde."
)

APPLIANCE_NAMES = {
    1: "sockets", 2: "sockets", 3: "electric oven", 4: "electric kettle",
    5: "microwave oven", 6: "dish washer", 7: "television", 8: "washing machine",
    9: "fridge-freezer",
}


class RefitConverter:
    dataset_id = DATASET_ID
    source_url = SOURCE_URL
    source_license = SOURCE_LICENSE
    citation = CITATION

    def convert(self, input_dir: Path, output_dir: Path) -> Path:
        from oed.io import write_manifest

        input_dir, output_dir = Path(input_dir), Path(output_dir)
        files = sorted(input_dir.glob("House_*.csv"))
        if not files:
            raise FileNotFoundError(f"no House_*.csv under {input_dir}")
        b = DatasetBuilder(
            output_dir, name="refit-oed",
            description="REFIT converted to the OpenEnergyData unified format",
            source_url=SOURCE_URL, source_license=SOURCE_LICENSE,
            citation=CITATION, dataset_id=DATASET_ID,
            creators=["Makonin, Stephen", "Popowich, Fred", "Barsim, Bob", "Wood, Bob"],
            keywords=["energy", "nilm", "refit", "oed"],
            date_published="2015-10-01")
        for f in files:
            site_id = f.stem.lower()          # house_1
            b.add_site(self._convert_building(f, site_id, b))
        return write_manifest(b.build(), output_dir)

    def _convert_building(self, f: Path, site_id: str, b: DatasetBuilder) -> dict:
        df = pd.read_csv(f)
        ts = pd.to_datetime(df["Time"]).dt.tz_localize("UTC")
        channels = []
        specs = [("aggregate", "Aggregate", "site_meter", None)]
        for i in range(1, 10):
            col = f"Appliance{i}"
            if col in df.columns:
                specs.append((f"appliance_{i:02d}", col, "submeter",
                              APPLIANCE_NAMES.get(i, "appliance")))
        for cid, col, role, appliance_type in specs:
            if col not in df.columns:
                continue
            sub = pd.DataFrame({
                "timestamp": ts,
                "power_w": pd.to_numeric(df[col], errors="coerce") * 1000.0,  # kW -> W
                "quality": 0,
            }).dropna(subset=["timestamp"])
            sub = sub[sub["power_w"].notna()]
            rel = f"sites/{site_id}/{cid}.parquet"
            appliance = None
            if appliance_type:
                appliance = {"type": appliance_type, "original_name": col, "instance": 1}
            channel = {
                "id": cid, "path": rel, "role": role,
                "physical_quantity": "power", "ac_type": "active", "unit": "W",
                "nominal_interval_s": nominal_interval(sub, fallback=8.0),
                "description": f"REFIT {col} (kW->W)",
                "appliance": appliance,
            }
            b.add_channel(site_id, channel, clean_series(sub))
            channels.append(channel)
        return {"id": site_id, "original_name": f.stem,
                "timezone": "UTC", "channels": channels}
