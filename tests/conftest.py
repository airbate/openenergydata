"""Shared fixtures: a miniature but format-exact REDD tree."""
from __future__ import annotations

from pathlib import Path

import pytest

# 2011-04-17 00:00:00 wall clock (away from DST transitions); REDD uses
# America/New_York wall-clock seconds. April 17 is EDT (UTC-4).
BASE_EPOCH = 1302998400
N_SAMPLES = 30 * 60  # 30 minutes at 1 Hz


def _write_channel(path: Path, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(f"{t}\t{p}\n" for t, p in rows), encoding="ascii")


def build_redd_source(root: Path) -> Path:
    house = root / "low_freq" / "house_1"

    # mains leg 1: healthy sinusoid-ish load
    _write_channel(house / "channel_1.dat",
                   ((BASE_EPOCH + i, 2400 + 30 * ((i % 60) - 30)) for i in range(N_SAMPLES)))
    # mains leg 2: healthy, slightly lower
    _write_channel(house / "channel_2.dat",
                   ((BASE_EPOCH + i, 1800 + 20 * ((i % 60) - 30)) for i in range(N_SAMPLES)))

    # oven submeter with injected anomalies:
    rows = []
    for i in range(N_SAMPLES):
        # gap: skip 90 consecutive seconds
        if 600 <= i < 690:
            continue
        # zero run: 150 seconds of exact zeros (~2.5 min, above 1-min threshold)
        if 1200 <= i < 1350:
            rows.append((BASE_EPOCH + i, 0.0))
            continue
        # negative spike (impossible value)
        if i == 1500:
            rows.append((BASE_EPOCH + i, -35.0))
            continue
        # outlier above submeter ceiling
        if i == 1600:
            rows.append((BASE_EPOCH + i, 45000.0))
            continue
        rows.append((BASE_EPOCH + i, 350.0 + 10 * ((i % 30) - 15)))
    _write_channel(house / "channel_3.dat", rows)

    (house / "labels.dat").write_text(
        "1 mains\n2 mains\n3 oven\n", encoding="ascii")
    return root / "low_freq"


@pytest.fixture(scope="session")
def redd_source(tmp_path_factory) -> Path:
    return build_redd_source(tmp_path_factory.mktemp("redd-src"))


@pytest.fixture(scope="session")
def oed_dataset(tmp_path_factory, redd_source) -> Path:
    from oed.converters.redd import ReddConverter

    out = tmp_path_factory.mktemp("oed-out")
    ReddConverter().convert(redd_source, out)
    return out
