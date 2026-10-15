"""IDEAL household energy dataset converter.

Per the dataset paper (Pullinger et al., Scientific Data 2021; DOI
10.7488/ds/2836) the sensor CSVs are **headerless** with two
comma-separated columns::

    YYYY-MM-DD hh:mm:ss,value

with timestamps already in UTC. Whole-home electricity is 1 Hz apparent
power (W); appliance sensors report real power in W. A metadata
inventory (headered CSVs with a ``sensor`` id column and sensor type)
ships with the dataset.

Discovery contract implemented here (real-data validation pending, see
README status table):

1. Every ``*.csv`` / ``*.csv.gz`` under the input root is a candidate
   sensor file (2-column headerless layout above).
2. If a sensor inventory CSV is found (path contains ``metadata`` and
   header contains a ``sensor`` column), a file belongs to the dataset's
   electricity domain when the sensor id embedded in its filename maps
   to an electricity-like ``sensor_type``/``units`` row; site and room
   come from the inventory ``home``/``room`` columns.
3. Without an inventory, filenames containing electricity tokens
   (``power``, ``electricity``, ``elec``, ``apparent``) are converted,
   and the site is taken from the first path component matching
   ``house[_-]?<n>``.
4. A channel is ``site_meter`` when the inventory type or filename
   indicates whole-home measurement (``apparent``/``mains``/``ct``/
   ``whole``/``aggregate``), otherwise ``submeter``.
"""
from __future__ import annotations

import gzip
import re
from pathlib import Path

import pandas as pd

from oed.converters.common import DatasetBuilder, clean_series, nominal_interval

DATASET_ID = "ideal"
SOURCE_URL = "https://datashare.ed.ac.uk/handle/10283/3647"
SOURCE_LICENSE = "CC-BY-NC 4.0 (Edinburgh DataShare, registration required)"
CITATION = (
    "Pullinger, M., et al. The IDEAL household energy dataset, electricity, "
    "gas, and contextual data from 255 UK homes. Scientific Data 8, 146, 2021."
)

ELEC_TOKENS = ("power", "electricity", "elec", "apparent")
MAINS_TOKENS = ("apparent", "mains", "whole", "ct", "aggregate")

_ID_RE = re.compile(r"(\d+)")
_HOUSE_RE = re.compile(r"house[_-]?(\d+)", re.IGNORECASE)


def _find_inventory(root: Path) -> pd.DataFrame | None:
    for p in sorted(root.rglob("*.csv")):
        if "metadata" not in str(p.relative_to(root)).lower():
            continue
        try:
            df = pd.read_csv(p)
        except Exception:
            continue
        cols = {c.strip().lower(): c for c in df.columns}
        if "sensor" in cols:
            return df
    return None


def _inventory_lookup(inventory: pd.DataFrame | None,
                      filename: str) -> dict | None:
    if inventory is None:
        return None
    ids = {int(m.group(1)) for m in _ID_RE.finditer(filename)}
    cols = {c.strip().lower(): c for c in inventory.columns}
    sensor_col = cols.get("sensor")
    if sensor_col is None:
        return None
    for _, row in inventory.iterrows():
        try:
            sid = int(row[sensor_col])
        except (TypeError, ValueError):
            continue
        if sid in ids:
            info: dict = {"sensor_id": sid}
            for key in ("home", "room", "sensor_type", "units", "appliance"):
                if key in cols:
                    v = row[cols[key]]
                    if pd.notna(v):
                        info[key] = str(v)
            return info
    return None


class IdealConverter:
    dataset_id = DATASET_ID
    source_url = SOURCE_URL
    source_license = SOURCE_LICENSE
    citation = CITATION

    def convert(self, input_dir: Path, output_dir: Path) -> Path:
        from oed.io import write_manifest

        input_dir, output_dir = Path(input_dir), Path(output_dir)
        candidates = sorted(
            p for p in input_dir.rglob("*")
            if p.is_file() and p.name.lower().endswith((".csv", ".csv.gz")))
        if not candidates:
            raise FileNotFoundError(f"no sensor csv files under {input_dir}")
        inventory = _find_inventory(input_dir)

        b = DatasetBuilder(
            output_dir, name="ideal-oed",
            description="IDEAL household energy dataset in the oed unified format",
            source_url=SOURCE_URL, source_license=SOURCE_LICENSE,
            citation=CITATION, dataset_id=DATASET_ID,
            creators=["Pullinger, Martin", "Hawkins, John", "Zakula, Tanya"],
            keywords=["energy", "nilm", "ideal", "uk", "oed"],
            date_published="2021-05-27")

        sites: dict[str, list[dict]] = {}
        for f in candidates:
            rel_name = f.name.lower().removesuffix(".gz").removesuffix(".csv")
            info = _inventory_lookup(inventory, f.name) or {}
            stype = str(info.get("sensor_type", "")).lower()
            if info:
                is_elec = any(t in stype for t in ELEC_TOKENS) or not stype
            else:
                is_elec = any(t in rel_name for t in ELEC_TOKENS)
            if not is_elec:
                continue

            df = self._read_sensor(f)
            if df.empty:
                continue

            sensor_id = info.get("sensor_id")
            cid = f"sensor{sensor_id}" if sensor_id else re.sub(r"\W+", "_", f.stem)
            home = info.get("home") or (
                m.group(1) if (m := _HOUSE_RE.search(str(f.relative_to(input_dir))))
                else "unknown")
            site_id = f"house_{home}"

            tokens = f"{stype} {rel_name}"
            is_mains = any(t in tokens for t in MAINS_TOKENS)
            role = "site_meter" if is_mains else "submeter"
            ac_type = "apparent" if "apparent" in tokens else "active"

            channel = {
                "id": cid,
                "path": f"sites/{site_id}/{cid}.parquet",
                "role": role, "physical_quantity": "power",
                "ac_type": ac_type, "unit": "W",
                "nominal_interval_s": nominal_interval(df),
                "description": f"IDEAL sensor {cid}"
                               f"{' (' + info['room'] + ')' if info.get('room') else ''}",
                "appliance": ({"type": info["appliance"], "original_name": cid,
                               "instance": 1} if info.get("appliance") else None),
            }
            b.add_channel(site_id, channel, df)
            sites.setdefault(site_id, []).append(channel)

        if not sites:
            raise ValueError(
                "no electricity sensor files matched the discovery contract "
                f"under {input_dir} (see converters/ideal.py docstring)")
        for site_id, channels in sites.items():
            b.add_site({"id": site_id, "original_name": site_id,
                        "timezone": "UTC", "channels": channels})
        return write_manifest(b.build(), output_dir)

    @staticmethod
    def _read_sensor(f: Path) -> pd.DataFrame:
        df = pd.read_csv(f, header=None, names=["ts", "power_w"],
                         compression="gzip" if f.name.endswith(".gz") else None,
                         dtype={"ts": "str", "power_w": "float64"})
        ts = pd.to_datetime(df["ts"], format="%Y-%m-%d %H:%M:%S",
                            errors="coerce").dt.tz_localize("UTC")
        out = pd.DataFrame({"timestamp": ts, "power_w": df["power_w"], "quality": 0})
        out = out.dropna(subset=["timestamp"])
        out = out[out["power_w"].notna()]
        return clean_series(out)
