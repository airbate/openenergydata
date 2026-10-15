"""Benchmark and HTML report tests."""
from __future__ import annotations

from pathlib import Path

from oed.benchmark import run_forecast, run_nilm, write_leaderboard
from oed.quality.scanner import ScanConfig, scan_dataset
from oed.report import render_html


def test_forecast_baselines(oed_dataset: Path):
    rows = run_forecast(oed_dataset)
    baselines = {r["baseline"] for r in rows}
    assert baselines == {"naive", "daily_profile", "seasonal_lag_24h"}
    for r in rows:
        assert r["n_test"] > 0 and r["mae"] >= 0
        assert r["unit"] == "W"


def test_nilm_framework(oed_dataset: Path):
    rows = run_nilm(oed_dataset)
    assert rows, "no nilm rows"
    assert all(r["baseline"] == "daily_profile" for r in rows)
    assert any(r["appliance"] == "electric oven" for r in rows)
    assert all("sae_pct" in r for r in rows)


def test_leaderboard_files(oed_dataset: Path):
    rows = run_forecast(oed_dataset) + run_nilm(oed_dataset)
    path = write_leaderboard(rows, oed_dataset)
    text = path.read_text(encoding="utf-8")
    assert "| forecast |" in text and "| nilm |" in text
    assert (oed_dataset / "benchmark.json").exists()


def test_html_report_card(oed_dataset: Path):
    scan = scan_dataset(oed_dataset, cfg=ScanConfig(zero_run_minutes=1.0))
    path = render_html(oed_dataset, scan, rule_findings=[])
    html = path.read_text(encoding="utf-8")
    assert "质量得分" in html and "Croissant" in html
    assert "sites/house_1/ch03.parquet" in html   # findings surfaced
    assert html.startswith("<!DOCTYPE html>")
