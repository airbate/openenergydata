"""Fixtures and parametrized tests for every converter."""
from __future__ import annotations

from pathlib import Path

import pytest


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def build_ukdale(root: Path) -> Path:
    d = root / "ukdale"
    rows1 = "".join(f"{1357800000 + i}\t{3000 + i % 50}\n" for i in range(600))
    rows3 = "".join(f"{1357800000 + i}\t{2000 + i % 30}\n" for i in range(600))
    _write(d / "house_1" / "channel_1.dat", rows1)
    _write(d / "house_1" / "channel_3.dat", rows3)
    _write(d / "house_1" / "labels.dat", "1 mains\n2 mains\n3 kettle\n")
    return d


def build_refit(root: Path) -> Path:
    from datetime import datetime, timedelta

    d = root / "refit"
    base = datetime(2014, 4, 1)
    lines = ["Time,Unix,Aggregate,Appliance1,Appliance2"]
    for i in range(600):
        t = base + timedelta(seconds=i * 8)
        lines.append(f"{t:%Y-%m-%d %H:%M:%S},{1396300800 + i * 8},"
                     f"{2.5 + i % 7 * 0.1:.2f},{0.9 + i % 5 * 0.05:.2f},{0.4:.2f}")
    _write(d / "House_1.csv", "\n".join(lines) + "\n")
    return d


def build_lcl(root: Path) -> Path:
    from datetime import datetime, timedelta

    d = root / "lcl"
    base = datetime(2013, 10, 5)
    lines = ["LCLid,stdorToU,DateTime,KWH/hh ,Acorn"]
    for i in range(200):
        t = base + timedelta(minutes=i * 30)
        lines.append(f"MAC000002,Std,{t:%Y-%m-%d %H:%M:%S},"
                     f"{0.20 + (i % 8) * 0.01:.2f},ACORN-A")
    _write(d / "lcl-sample.csv", "\n".join(lines) + "\n")
    return d


def build_eco(root: Path) -> Path:
    d = root / "eco" / "household_1"
    lines = ["Date;Time;Power1;Power2;Power3"]
    for i in range(600):
        lines.append(f"06.09.2013;00:{i // 60:02d}:{i % 60:02d};"
                     f"{300 + i % 40};{200 + i % 30};{100 + i % 20}")
    _write(d / "sm.csv", "\n".join(lines) + "\n")
    return d


def build_mengxi(root: Path) -> Path:
    from datetime import datetime, timedelta

    d = root / "mengxi"
    base = datetime(2026, 3, 1)
    lines = ["times,系统负荷实际值,系统负荷预测值,风电实际值,光伏实际值"]
    for i in range(300):  # 15-min steps across ~3 days
        t = base + timedelta(minutes=i * 15)
        lines.append(f"{t:%Y-%m-%d %H:%M:%S},{8000 + i % 40 * 10},"
                     f"{7950 + i % 40 * 10},{1500 + i % 30 * 5},{300 + i % 20 * 3}")
    _write(d / "data" / "train" / "mengxi_boundary_anon_filtered.csv",
           "\n".join(lines) + "\n")
    return d


BUILDERS = {
    "ukdale": build_ukdale,
    "refit": build_refit,
    "lcl": build_lcl,
    "eco": build_eco,
    "mengxi": build_mengxi,
}


@pytest.fixture(scope="session", params=sorted(BUILDERS))
def converted(tmp_path_factory, request):
    from oed.converters import CONVERTERS

    src = BUILDERS[request.param](tmp_path_factory.mktemp(f"src-{request.param}"))
    out = tmp_path_factory.mktemp(f"out-{request.param}")
    CONVERTERS[request.param].convert(src, out)
    return request.param, out


def test_manifest_valid(converted):
    from oed.io import load_manifest, validate_manifest

    dataset_id, out = converted
    errors = validate_manifest(load_manifest(out))
    assert errors == [], "\n".join(errors)


def test_channels_present(converted):
    from oed.io import load_manifest

    dataset_id, out = converted
    manifest = load_manifest(out)
    channels = [c for s in manifest["x-oed"]["sites"] for c in s["channels"]]
    assert channels, f"{dataset_id}: no channels"
    for c in channels:
        assert (out / c["path"]).exists()


def test_refit_kw_to_w(tmp_path_factory):
    from oed.converters.refit import RefitConverter
    from oed.io import read_channel_parquet

    src = build_refit(tmp_path_factory.mktemp("refit-src2"))
    out = tmp_path_factory.mktemp("refit-out2")
    RefitConverter().convert(src, out)
    df = read_channel_parquet(out / "sites/house_1/aggregate.parquet")
    assert df["power_w"].min() >= 2500.0      # 2.5 kW -> 2500 W floor
    assert df["power_w"].max() <= 3200.0      # 3.1 kW -> 3100 W ceiling


def test_ukdale_timezone(tmp_path_factory):
    from oed.converters.ukdale import UkdaleConverter
    from oed.io import read_channel_parquet

    src = build_ukdale(tmp_path_factory.mktemp("ukd-src"))
    out = tmp_path_factory.mktemp("ukd-out")
    UkdaleConverter().convert(src, out)
    df = read_channel_parquet(out / "sites/house_1/ch01.parquet")
    # epoch 1357800000 == 2013-01-10 06:40 UTC == 06:40 London (GMT, winter)
    assert str(df["timestamp"].iloc[0]) == "2013-01-10 06:40:00+00:00"


def test_mengxi_semantics(tmp_path_factory):
    from oed.converters.mengxi import MengxiConverter
    from oed.io import load_manifest, read_channel_parquet

    src = build_mengxi(tmp_path_factory.mktemp("mx-src"))
    out = tmp_path_factory.mktemp("mx-out")
    MengxiConverter().convert(src, out)
    manifest = load_manifest(out)
    site = manifest["x-oed"]["sites"][0]
    assert site["timezone"] == "Asia/Shanghai"
    roles = {c["id"]: c["role"] for c in site["channels"]}
    assert roles["system_load"] == "site_meter"
    assert roles["wind"] == "submeter"
    units = {c["id"]: c["unit"] for c in site["channels"]}
    assert units["system_load"] == "MW"
    df = read_channel_parquet(out / "sites/mengxi_grid/system_load.parquet")
    # 2026-03-01 00:00 +08:00 == 2026-02-28 16:00 UTC
    assert str(df["timestamp"].iloc[0]).startswith("2026-02-28 16:00")


def test_lcl_energy_channel(tmp_path_factory):
    from oed.converters.lcl import LclConverter
    from oed.io import load_manifest, read_channel_parquet

    src = build_lcl(tmp_path_factory.mktemp("lcl-src"))
    out = tmp_path_factory.mktemp("lcl-out")
    LclConverter().convert(src, out)
    manifest = load_manifest(out)
    ch = manifest["x-oed"]["sites"][0]["channels"][0]
    assert ch["physical_quantity"] == "energy" and ch["unit"] == "kWh"
    df = read_channel_parquet(out / ch["path"])
    assert 0.19 < df["power_w"].min() < 0.21   # kWh preserved as energy values


def test_eco_phases(tmp_path_factory):
    from oed.converters.eco import EcoConverter
    from oed.io import load_manifest

    src = build_eco(tmp_path_factory.mktemp("eco-src"))
    out = tmp_path_factory.mktemp("eco-out")
    EcoConverter().convert(src, out)
    manifest = load_manifest(out)
    ids = [c["id"] for c in manifest["x-oed"]["sites"][0]["channels"]]
    assert ids == ["phase1", "phase2", "phase3"]
