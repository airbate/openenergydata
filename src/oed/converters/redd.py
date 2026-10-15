"""REDD (Reference Energy Disaggregation Dataset) -> unified oed format.

Source layout (low_freq):
    house_<n>/channel_<m>.dat   tab-separated: <unix_seconds>\t<watts>
    house_<n>/labels.dat        lines of "<channel> <appliance label>"

Semantics (following the dataset documentation and the nilmtk reference
implementation, Apache-2.0):
  * channels 1-2 are the two mains legs -> site_meter, apparent power
  * channels >= 3 are submeters -> active power
  * timestamps are wall-clock seconds in America/New_York
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

import oed
from oed.io import sha256_file, write_channel_parquet, write_manifest

DATASET_ID = "redd"
SOURCE_URL = "http://redd.csail.mit.edu"
SOURCE_LICENSE = "Free for academic research use (see REDD project page)"
CITATION = (
    "J. Zico Kolter and Matthew J. Johnson. REDD: A public data set for "
    "energy disaggregation research. SustKDD workshop, 2011."
)

# REDD appliance labels -> normalized appliance types (nilm_metadata taxonomy).
APPLIANCE_TYPES = {
    "oven": "electric oven",
    "refrigerator": "fridge",
    "dishwaser": "dish washer",  # upstream label is misspelled in REDD
    "dish_washer": "dish washer",
    "dishwasher": "dish washer",
    "kitchen_outlets": "sockets",
    "bathroom_gfi": "sockets",
    "lighting": "light",
    "lights": "light",
    "washer_dryer": "washer dryer",
    "microwave": "microwave oven",
    "furnace": "electric furnace",
    "well_pump": "pump",
    "electronics": "consumer electronics",
    "subpanel": "distribution board",
    "smoke_alarm": "smoke alarm",
    "stove": "electric stove",
    "air_conditioning": "air conditioner",
    "miscellaeneous": "sockets",
    "electric_heat": "electric space heater",
}


@dataclass
class ReddConverter:
    dataset_id: str = DATASET_ID
    source_url: str = SOURCE_URL
    source_license: str = SOURCE_LICENSE
    citation: str = CITATION
    appliance_types: dict = field(default_factory=lambda: dict(APPLIANCE_TYPES))

    def convert(self, input_dir: Path, output_dir: Path) -> Path:
        input_dir = Path(input_dir)
        output_dir = Path(output_dir)
        houses = sorted(p for p in input_dir.glob("house_*") if p.is_dir())
        if not houses:
            raise FileNotFoundError(
                f"no house_* directories under {input_dir}; "
                "expected the extracted REDD low_freq tree"
            )
        sites, distributions, record_sets = [], [], []
        for house in houses:
            site = self._convert_house(house, output_dir, distributions, record_sets)
            sites.append(site)

        manifest = self._manifest(sites, distributions, record_sets)
        return write_manifest(manifest, output_dir)

    # ------------------------------------------------------------------

    def _convert_house(self, house: Path, output_dir: Path,
                       distributions: list, record_sets: list) -> dict:
        labels = self._read_labels(house / "labels.dat")
        channels = sorted(
            (p for p in house.glob("channel_*.dat")),
            key=lambda p: int(p.stem.split("_")[1]),
        )
        site_channels = []
        appliance_instances: dict[str, int] = {}
        for chan_file in channels:
            chan_id = int(chan_file.stem.split("_")[1])
            rel = f"sites/{house.name}/ch{chan_id:02d}.parquet"
            df = self._load_channel(chan_file, is_site_meter=chan_id <= 2)
            path = output_dir / rel
            write_channel_parquet(df, path)

            if chan_id <= 2:
                role, ac_type, appliance = "site_meter", "apparent", None
            else:
                role, ac_type = "submeter", "active"
                raw_label = labels.get(chan_id)
                normalized = self.appliance_types.get(raw_label or "", raw_label)
                if normalized is None:
                    appliance = None
                else:
                    instance = appliance_instances.get(normalized, 0) + 1
                    appliance_instances[normalized] = instance
                    appliance = {
                        "type": normalized,
                        "original_name": raw_label,
                        "instance": instance,
                    }

            site_channels.append({
                "id": f"ch{chan_id:02d}",
                "path": rel,
                "role": role,
                "physical_quantity": "power",
                "ac_type": ac_type,
                "unit": "W",
                "nominal_interval_s": float(df["timestamp"].diff().dt.total_seconds().median()),
                "appliance": appliance,
            })
            distributions.append({
                "@type": "cr:FileObject",
                "name": rel,
                "contentUrl": rel,
                "encodingFormat": "application/x-parquet",
                "sha256": sha256_file(path),
            })
            record_sets.append(self._record_set(house.name, chan_id))
        return {
            "id": house.name,
            "original_name": house.name,
            "timezone": "America/New_York",
            "geo": {"country": "US", "locality": "Massachusetts",
                    "latitude": 42.360091, "longitude": -71.09416},
            "channels": site_channels,
        }

    def _load_channel(self, chan_file: Path, is_site_meter: bool) -> pd.DataFrame:
        df = pd.read_csv(
            chan_file, sep=r"\s+", names=["epoch_s", "power_w"],
            dtype={"epoch_s": "int64", "power_w": "float64"},
        )
        naive = pd.to_datetime(df["epoch_s"], unit="s")
        try:
            ts = naive.dt.tz_localize(
                "America/New_York", ambiguous="infer", nonexistent="shift_forward"
            ).dt.tz_convert("UTC")
        except (pd.errors.AmbiguousTimeError, pd.errors.NonExistentTimeError):
            ts = naive.dt.tz_localize("UTC")
        n_dropped = int(ts.isna().sum())
        if n_dropped:
            keep = ts.notna()
            df, ts = df.loc[keep], ts.loc[keep]
        out = pd.DataFrame({
            "timestamp": ts,
            "power_w": df["power_w"].to_numpy(),
            "quality": 0,
        })
        out = out.sort_values("timestamp", kind="stable")
        out = out[~out["timestamp"].duplicated(keep="first")]
        return out.reset_index(drop=True)

    @staticmethod
    def _read_labels(path: Path) -> dict[int, str]:
        labels: dict[int, str] = {}
        if not path.exists():
            return labels
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            parts = line.split(None, 1)
            if len(parts) == 2 and parts[0].isdigit():
                labels[int(parts[0])] = parts[1].strip()
        return labels

    @staticmethod
    def _record_set(house: str, chan_id: int) -> dict:
        fields = [
            {"@type": "cr:Field", "name": "timestamp", "dataType": "sc:DateTime",
             "description": "UTC ISO-8601"},
            {"@type": "cr:Field", "name": "power_w", "dataType": "sc:Float",
             "description": "W"},
            {"@type": "cr:Field", "name": "quality", "dataType": "sc:Integer",
             "description": "bitmask, see oed quality vocabulary"},
        ]
        return {"@type": "cr:RecordSet", "name": f"{house}/ch{chan_id:02d}",
                "description": "power time series", "field": fields}

    def _manifest(self, sites, distributions, record_sets) -> dict:
        return {
            "@context": "https://raw.githubusercontent.com/mlcommons/croissant/main/croissant-rdf/croissant.jsonld",
            "@type": "cr:Dataset",
            "name": "redd-oed",
            "description": "REDD converted to the OpenEnergyData unified format",
            "url": SOURCE_URL,
            "license": SOURCE_LICENSE,
            "creator": ["Kolter, Zico", "Johnson, Matthew"],
            "datePublished": "2011-04-18",
            "keywords": ["energy", "nilm", "disaggregation", "redd", "oed"],
            "distribution": distributions,
            "recordSet": record_sets,
            "x-oed": {
                "spec": "oed/1.0",
                "source": {
                    "dataset": DATASET_ID,
                    "url": SOURCE_URL,
                    "license": SOURCE_LICENSE,
                    "citation": CITATION,
                },
                "converter": {
                    "name": "oed.converters.redd",
                    "version": oed.__version__,
                    "upstream": "https://github.com/nilmtk/nilmtk (Apache-2.0), metadata design reference",
                },
                "sites": sites,
            },
        }
