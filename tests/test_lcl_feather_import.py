"""Regression coverage for households spanning Feather slices and files."""
import importlib.util
from pathlib import Path

import pandas as pd
import pytest

spec = importlib.util.spec_from_file_location(
    "import_lcl_feather", Path(__file__).parents[1] / "scripts/import_lcl_feather.py"
)
importer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(importer)


@pytest.mark.parametrize("same_basename", [False, True])
def test_all_readings_survive_slices_and_files(tmp_path, monkeypatch, same_basename):
    monkeypatch.setattr(importer, "SLICE_ROWS", 3)
    sources = []
    for year in range(2):
        folder = tmp_path / str(year)
        folder.mkdir()
        source = folder / ("data.feather" if same_basename else f"data_{year}.feather")
        pd.DataFrame({
            "DateTime": pd.date_range(f"201{year + 1}-01-01", periods=8, freq="30min"),
            "LCLid": ["MAC000001"] * 8,
            "KWH/hh": [float(year * 10 + i) for i in range(8)],
        }).to_feather(source)
        sources.append(source)
    shards = importer.pass_one(sources, tmp_path / "shards", None)
    importer.pass_two(shards, tmp_path / "out")
    result = pd.read_parquet(tmp_path / "out/sites/mac000001/energy.parquet")
    assert len(result) == 16
    assert result["power_w"].tolist() == [float(y * 10 + i) for y in range(2) for i in range(8)]
    assert result["timestamp"].is_unique

    from oed.benchmark import run_forecast
    # A longer channel verifies the energy-to-power benchmark unit.
    longer = pd.concat([result] * 2, ignore_index=True)
    longer["timestamp"] = pd.date_range("2011-01-01", periods=32, freq="30min", tz="UTC")
    longer.to_parquet(tmp_path / "out/sites/mac000001/energy.parquet", index=False)
    rows = run_forecast(tmp_path / "out")
    assert len(rows) == 3
    assert {row["unit"] for row in rows} == {"kW"}


def test_numeric_ids_require_explicit_namespace(tmp_path):
    source = tmp_path / 'numeric.feather'
    pd.DataFrame({'DateTime': pd.date_range('2012-01-01', periods=3, freq='30min'),
                  'LCLid': [0, 0, 1], 'KWH/hh': [1., 2., 3.]}).to_feather(source)
    with pytest.raises(ValueError, match='encoded numeric'):
        importer.pass_one([source], tmp_path / 'rejected', None)
    shards = importer.pass_one([source], tmp_path / 'accepted', None, 'encoded2012_')
    assert set(shards) == {'encoded2012_0', 'encoded2012_1'}


def test_limit_is_global_and_reads_record_batches(tmp_path):
    import pyarrow as pa
    import pyarrow.feather as feather
    sources = []
    for index, ids in enumerate([['MAC1', 'MAC2', 'MAC1'], ['MAC3', 'MAC1', 'MAC2']]):
        source = tmp_path / f'{index}.feather'
        frame = pd.DataFrame({'DateTime': pd.date_range(f'201{index+1}-01-01', periods=3, freq='30min'),
                              'LCLid': ids, 'KWH/hh': [1., 2., 3.]})
        feather.write_feather(pa.Table.from_pandas(frame), source, chunksize=1)
        sources.append(source)
    shards = importer.pass_one(sources, tmp_path / 'shards', 1)
    assert set(shards) == {'MAC1'}
    assert sum(len(pd.read_pickle(p)) for p in shards['MAC1']) == 3


def test_work_directory_preserves_existing_files(tmp_path):
    marker = tmp_path / 'keep.txt'
    marker.write_text('keep')
    with pytest.raises(ValueError, match='must be empty'):
        importer.pass_one([], tmp_path, None)
    assert marker.read_text() == 'keep'


def test_partial_recovery_is_explicit(tmp_path):
    import pyarrow as pa
    recovery_spec = importlib.util.spec_from_file_location(
        'recover', Path(__file__).parents[1] / 'scripts/recover_truncated_feather.py')
    recovery = importlib.util.module_from_spec(recovery_spec)
    recovery_spec.loader.exec_module(recovery)
    source = tmp_path / 'broken.feather'
    batch = pa.record_batch({'DateTime': [pd.Timestamp('2013-01-01')],
                             'LCLid': ['MAC1'], 'KWH/hh': [1.]})
    with pa.OSFile(str(source), 'wb') as sink, pa.ipc.new_file(sink, batch.schema) as writer:
        for _ in range(10):
            writer.write_batch(batch)
    raw = source.read_bytes()
    source.write_bytes(raw[:len(raw)//2])
    output = tmp_path / 'recovered.feather'
    audit = recovery.recover(source, output)
    assert audit['complete'] is False and 'error' in audit
    assert 0 < audit['rows'] < 10
    assert pa.ipc.open_file(str(output)).read_all().num_rows == audit['rows']
    assert source.read_bytes() == raw[:len(raw)//2]
