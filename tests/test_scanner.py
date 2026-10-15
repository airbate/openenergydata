"""Quality scanner tests."""
from __future__ import annotations

from pathlib import Path

from oed.io import read_channel_parquet
from oed.quality.scanner import ScanConfig, scan_dataset, write_report


def test_scan_detects_all_injected_issues(oed_dataset: Path):
    cfg = ScanConfig(zero_run_minutes=1.0)
    report = scan_dataset(oed_dataset, cfg=cfg)
    types = set(report["summary"])
    assert "gap" in types
    assert "impossible_value" in types
    assert "outlier" in types
    assert "zero_run" in types
    # healthy mains channels contribute nothing critical
    crit = [f for f in report["findings"] if f["severity"] == "critical"]
    assert all("ch03" in f["channel"] for f in crit)
    assert 0 <= report["quality_score"] <= 100


def test_annotate_writes_quality_flags(tmp_path_factory, redd_source: Path):
    out = tmp_path_factory.mktemp("oed-annot")
    from oed.converters.redd import ReddConverter
    ReddConverter().convert(redd_source, out)
    cfg = ScanConfig(zero_run_minutes=1.0)
    scan_dataset(out, cfg=cfg, annotate=True)
    df = read_channel_parquet(out / "sites/house_1/ch03.parquet")
    assert (df["quality"] != 0).any()
    # negative spike sample must carry IMPOSSIBLE_VALUE
    from oed.quality_flags import QualityFlag
    neg_rows = df[df["power_w"] < 0]
    assert len(neg_rows) == 1
    assert bool(neg_rows["quality"].iloc[0] & QualityFlag.IMPOSSIBLE_VALUE)


def test_report_files_written(tmp_path_factory, redd_source: Path):
    out = tmp_path_factory.mktemp("oed-report")
    from oed.converters.redd import ReddConverter
    ReddConverter().convert(redd_source, out)
    report = scan_dataset(out, cfg=ScanConfig(zero_run_minutes=1.0))
    path = write_report(report, out)
    assert path.exists()
    assert (out / "quality-report.json").exists()
    text = path.read_text(encoding="utf-8")
    assert "质量得分" in text and "| critical |" in text
