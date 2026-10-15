"""ECO converter: Swiss household smart-meter CSVs.

Input layout (per official documentation; validated against real data
still pending -- see README status table): one CSV per household/month
with semicolon-separated rows
    Date;Time;Power1;Power2;Power3
where Power1..3 are the three phase powers in W at ~1 s sampling,
Europe/Zurich local time. Each phase becomes a site_meter channel.
"""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from oed.converters.common import DatasetBuilder, clean_series, nominal_interval

DATASET_ID = "eco"
SOURCE_URL = "https://www.vs.inf.ethz.ch/res/eco-smart-meter-data.html"
SOURCE_LICENSE = "Academic research use (see project page)"
CITATION = (
    "Christoph Beckel et al. The ECO data set and the performance of "
    "non-intrusive load monitoring algorithms. BuildSys 2014."
)

SITE_RE = re.compile(r"household_(\d+)", re.IGNORECASE)


class EcoConverter:
    dataset_id = DATASET_ID
    source_url = SOURCE_URL
    source_license = SOURCE_LICENSE
    citation = CITATION

    def convert(self, input_dir: Path, output_dir: Path) -> Path:
        from oed.io import write_manifest

        input_dir, output_dir = Path(input_dir), Path(output_dir)
        files = sorted(input_dir.rglob("*.csv"))
        if not files:
            raise FileNotFoundError(f"no *.csv under {input_dir}")
        b = DatasetBuilder(
            output_dir, name="eco-oed",
            description="ECO converted to the OpenEnergyData unified format",
            source_url=SOURCE_URL, source_license=SOURCE_LICENSE,
            citation=CITATION, dataset_id=DATASET_ID,
            creators=["Beckel, Christoph", "Kleiminger, Wilhelm", "Santini, Silvia"],
            keywords=["energy", "nilm", "eco", "switzerland", "oed"],
            date_published="2014-01-01")
        sites: dict[str, list[dict]] = {}
        for f in files:
            m = SITE_RE.search(str(f))
            site_id = f"household_{m.group(1)}" if m else f.stem.lower()
            sites.setdefault(site_id, []).append(f)

        site_records = []
        for site_id, sfiles in sites.items():
            frames = [self._read_one(f) for f in sfiles]
            df = pd.concat(frames, ignore_index=True)
            df = clean_series(df)
            channels = []
            for phase in (1, 2, 3):
                col = f"power_w_{phase}"
                if col not in df.columns or df[col].notna().sum() == 0:
                    continue
                sub = pd.DataFrame({
                    "timestamp": df["timestamp"],
                    "power_w": df[col],
                    "quality": 0,
                }).dropna()
                rel = f"sites/{site_id}/phase{phase}.parquet"
                channel = {
                    "id": f"phase{phase}", "path": rel, "role": "site_meter",
                    "physical_quantity": "power", "ac_type": "active", "unit": "W",
                    "nominal_interval_s": nominal_interval(sub),
                    "description": f"phase {phase} mains power",
                    "appliance": None,
                }
                b.add_channel(site_id, channel, sub)
                channels.append(channel)
            site_records.append({"id": site_id, "original_name": site_id,
                                 "timezone": "Europe/Zurich",
                                 "channels": channels})
        for s in site_records:
            b.add_site(s)
        return write_manifest(b.build(), output_dir)

    @staticmethod
    def _read_one(f: Path) -> pd.DataFrame:
        raw = pd.read_csv(f, sep=";", header=None,
                          names=["date", "time", "power_w_1", "power_w_2", "power_w_3"],
                          dtype=str, skiprows=1)
        naive = pd.to_datetime(raw["date"] + " " + raw["time"],
                               dayfirst=True, errors="coerce")
        try:
            ts = naive.dt.tz_localize("Europe/Zurich", ambiguous="infer",
                                      nonexistent="shift_forward").dt.tz_convert("UTC")
        except (pd.errors.AmbiguousTimeError, pd.errors.NonExistentTimeError):
            ts = naive.dt.tz_localize("UTC")
        out = pd.DataFrame({"timestamp": ts})
        for i in (1, 2, 3):
            out[f"power_w_{i}"] = pd.to_numeric(raw[f"power_w_{i}"],
                                                errors="coerce")
        return out.dropna(subset=["timestamp"])
