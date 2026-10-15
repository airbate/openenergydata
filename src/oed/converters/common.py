"""Shared helpers for building unified datasets and manifests."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

import oed
from oed.io import sha256_file, write_channel_parquet

CHANNEL_FIELDS = [
    {"@type": "cr:Field", "name": "timestamp", "dataType": "sc:DateTime",
     "description": "UTC ISO-8601"},
    {"@type": "cr:Field", "name": "power_w", "dataType": "sc:Float",
     "description": "W"},
    {"@type": "cr:Field", "name": "quality", "dataType": "sc:Integer",
     "description": "bitmask, see oed quality vocabulary"},
]


class DatasetBuilder:
    """Accumulates channels/sites while writing parquet files, then
    emits a Croissant-compatible manifest."""

    def __init__(self, output_dir: Path, *, name: str, description: str,
                 source_url: str, source_license: str, citation: str,
                 dataset_id: str, creators: list[str] | None = None,
                 keywords: list[str] | None = None,
                 date_published: str | None = None):
        self.output_dir = Path(output_dir)
        self.meta = dict(name=name, description=description, source_url=source_url,
                         source_license=source_license, citation=citation,
                         dataset_id=dataset_id, creators=creators or [],
                         keywords=keywords or ["energy", "oed"],
                         date_published=date_published)
        self.sites: list[dict] = []
        self._distributions: list[dict] = []
        self._record_sets: list[dict] = []

    def add_site(self, site: dict) -> None:
        self.sites.append(site)

    def add_channel(self, site_id: str, channel: dict, df: pd.DataFrame,
                    fields: list[dict] | None = None) -> Path:
        rel = channel["path"]
        path = self.output_dir / rel
        write_channel_parquet(df, path)
        self._distributions.append({
            "@type": "cr:FileObject", "name": rel, "contentUrl": rel,
            "encodingFormat": "application/x-parquet",
            "sha256": sha256_file(path),
        })
        self._record_sets.append({
            "@type": "cr:RecordSet", "name": f"{site_id}/{channel['id']}",
            "description": channel.get("description", "power time series"),
            "field": fields or CHANNEL_FIELDS,
        })
        return path

    def build(self) -> dict:
        m = self.meta
        manifest = {
            "@context": "https://raw.githubusercontent.com/mlcommons/croissant/main/croissant-rdf/croissant.jsonld",
            "@type": "cr:Dataset",
            "name": m["name"],
            "description": m["description"],
            "url": m["source_url"],
            "license": m["source_license"],
            "creator": m["creators"] or "unknown",
            "keywords": m["keywords"],
            "distribution": self._distributions,
            "recordSet": self._record_sets,
            "x-oed": {
                "spec": "oed/1.0",
                "source": {
                    "dataset": m["dataset_id"], "url": m["source_url"],
                    "license": m["source_license"], "citation": m["citation"],
                },
                "converter": {
                    "name": f"oed.converters.{m['dataset_id']}",
                    "version": oed.__version__,
                },
                "sites": self.sites,
            },
        }
        if m["date_published"]:
            manifest["datePublished"] = m["date_published"]
        return manifest


def clean_series(df: pd.DataFrame) -> pd.DataFrame:
    """Sort by timestamp, drop duplicate timestamps (keep first)."""
    df = df.sort_values("timestamp", kind="stable")
    df = df[~df["timestamp"].duplicated(keep="first")]
    return df.reset_index(drop=True)


def nominal_interval(df: pd.DataFrame, fallback: float = 1.0) -> float:
    diffs = df["timestamp"].diff().dt.total_seconds().dropna()
    return float(diffs.median()) if len(diffs) else fallback
