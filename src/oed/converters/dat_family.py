"""Base for 'house_N/channel_M.dat' style datasets (REDD, UK-DALE).

Files: house_<n>/channel_<m>.dat with '<epoch_seconds>\\t<watts>' rows and
house_<n>/labels.dat with '<channel> <label>' rows. Subclasses declare
timezone, appliance vocabulary and mains semantics.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from oed.converters.common import DatasetBuilder, clean_series, nominal_interval


class DatFamilyConverter:
    dataset_id: str = ""
    timezone: str = "UTC"
    source_url: str = ""
    source_license: str = ""
    citation: str = ""
    name: str = ""
    description: str = ""
    creators: list[str] = []
    date_published: str | None = None
    keywords: list[str] = ["energy", "nilm", "oed"]
    n_site_meters: int = 2          # channels 1..n are mains legs
    site_meter_ac_type: str = "apparent"
    appliance_types: dict[str, str] = {}
    geo: dict | None = None

    def convert(self, input_dir: Path, output_dir: Path) -> Path:
        from oed.io import write_manifest

        input_dir, output_dir = Path(input_dir), Path(output_dir)
        houses = sorted(p for p in input_dir.glob("house_*") if p.is_dir())
        if not houses:
            raise FileNotFoundError(
                f"no house_* directories under {input_dir}")
        b = DatasetBuilder(
            output_dir, name=f"{self.dataset_id}-oed", description=self.description,
            source_url=self.source_url, source_license=self.source_license,
            citation=self.citation, dataset_id=self.dataset_id,
            creators=self.creators, keywords=self.keywords,
            date_published=self.date_published)
        for house in houses:
            b.add_site(self._convert_house(house, b))
        return write_manifest(b.build(), output_dir)

    def _convert_house(self, house: Path, b: DatasetBuilder) -> dict:
        labels = self._read_labels(house / "labels.dat")
        channels = sorted(house.glob("channel_*.dat"),
                          key=lambda p: int(p.stem.split("_")[1]))
        site_channels, instances = [], {}
        for chan_file in channels:
            cid = int(chan_file.stem.split("_")[1])
            rel = f"sites/{house.name}/ch{cid:02d}.parquet"
            df = self._load_channel(chan_file)
            if cid <= self.n_site_meters:
                role, ac_type, appliance = "site_meter", self.site_meter_ac_type, None
            else:
                role, ac_type = "submeter", "active"
                raw = labels.get(cid)
                norm = self.appliance_types.get(raw or "", raw)
                appliance = None
                if norm:
                    instances[norm] = instances.get(norm, 0) + 1
                    appliance = {"type": norm, "original_name": raw,
                                 "instance": instances[norm]}
            channel = {
                "id": f"ch{cid:02d}", "path": rel, "role": role,
                "physical_quantity": "power", "ac_type": ac_type, "unit": "W",
                "nominal_interval_s": nominal_interval(df),
                "appliance": appliance,
            }
            b.add_channel(house.name, channel, df)
            site_channels.append(channel)
        site = {"id": house.name, "original_name": house.name,
                "timezone": self.timezone, "channels": site_channels}
        if self.geo:
            site["geo"] = self.geo
        return site

    def _load_channel(self, chan_file: Path) -> pd.DataFrame:
        df = pd.read_csv(chan_file, sep=r"\s+",
                         names=["epoch_s", "power_w"],
                         dtype={"epoch_s": "int64", "power_w": "float64"})
        naive = pd.to_datetime(df["epoch_s"], unit="s")
        try:
            ts = naive.dt.tz_localize(self.timezone, ambiguous="infer",
                                      nonexistent="shift_forward").dt.tz_convert("UTC")
        except (pd.errors.AmbiguousTimeError, pd.errors.NonExistentTimeError):
            ts = naive.dt.tz_localize("UTC")
        keep = ts.notna()
        out = pd.DataFrame({"timestamp": ts[keep].to_numpy(),
                            "power_w": df.loc[keep, "power_w"].to_numpy(),
                            "quality": 0})
        return clean_series(out)

    @staticmethod
    def _read_labels(path: Path) -> dict[int, str]:
        labels: dict[int, str] = {}
        if path.exists():
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
                parts = line.split(None, 1)
                if len(parts) == 2 and parts[0].isdigit():
                    labels[int(parts[0])] = parts[1].strip()
        return labels
