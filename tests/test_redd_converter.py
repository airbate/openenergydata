"""REDD converter tests."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from oed.io import load_manifest, read_channel_parquet, validate_manifest


def test_manifest_schema_valid(oed_dataset: Path):
    manifest = load_manifest(oed_dataset)
    errors = validate_manifest(manifest)
    assert errors == [], "\n".join(errors)


def test_channel_semantics(oed_dataset: Path):
    manifest = load_manifest(oed_dataset)
    sites = manifest["x-oed"]["sites"]
    assert len(sites) == 1 and sites[0]["id"] == "house_1"
    channels = {c["id"]: c for c in sites[0]["channels"]}
    assert set(channels) == {"ch01", "ch02", "ch03"}

    assert channels["ch01"]["role"] == "site_meter"
    assert channels["ch01"]["ac_type"] == "apparent"
    assert channels["ch03"]["role"] == "submeter"
    assert channels["ch03"]["ac_type"] == "active"
    appliance = channels["ch03"]["appliance"]
    assert appliance["type"] == "electric oven"
    assert appliance["original_name"] == "oven"
    assert channels["ch01"]["nominal_interval_s"] == 1.0


def test_parquet_layout_and_tz(oed_dataset: Path):
    manifest = load_manifest(oed_dataset)
    ch03 = manifest["x-oed"]["sites"][0]["channels"][2]
    path = oed_dataset / ch03["path"]
    assert path.exists() and path.suffix == ".parquet"
    df = read_channel_parquet(path)
    assert list(df.columns) == ["timestamp", "power_w", "quality"]
    assert str(df["timestamp"].dtype).endswith(", UTC]")
    # gap removed 90 samples of 1800
    assert len(df) == 1800 - 90
    # timestamps strictly increasing, unique
    assert df["timestamp"].is_monotonic_increasing
    assert not df["timestamp"].duplicated().any()
    # 2011-04-17 04:00 UTC == 2011-04-17 00:00 America/New_York (EDT, UTC-4)
    assert df["timestamp"].iloc[0] == pd.Timestamp("2011-04-17 04:00:00+00:00")


def test_distribution_hashes(oed_dataset: Path):
    manifest = load_manifest(oed_dataset)
    from oed.io import sha256_file
    for dist in manifest["distribution"]:
        assert sha256_file(oed_dataset / dist["contentUrl"]) == dist["sha256"]
