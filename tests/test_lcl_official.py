"""Raw-source preservation and identity evidence regression checks."""
import importlib.util
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

SCRIPTS = Path(__file__).parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
from rebuild_lcl_official import rebuild, ENERGY
from recover_lcl_identity import fingerprints, quantize
from import_lcl_feather import pass_two
from oed.units import watts_factor
from oed.benchmark import run_forecast
from oed.io import validate_manifest


def test_official_rebuild_preserves_nulls_duplicates_and_clock_strings(tmp_path):
    archive = tmp_path / 'official.zip'
    header = f'LCLid,stdorToU,DateTime,{ENERGY}\n'
    rows = 'MAC1,Std,2013-01-01 00:00:00, 0.1 \nMAC1,Std,2013-01-01 00:00:00,Null\nMAC2,ToU,2012-12-31 23:30:00, 9.71 \n'
    with zipfile.ZipFile(archive, 'w') as z:
        for i in range(168):
            z.writestr(f'Small LCL Data/LCL-June2015v2_{i}.csv', header + (rows if i == 0 else ''))
    report = rebuild(archive, tmp_path / 'out')
    assert report['years']['2013']['rows'] == 2
    assert report['years']['2013']['null_energy'] == 1
    result = pd.read_parquet(tmp_path / 'out/year=2013/part-000.parquet')
    assert result[ENERGY].tolist() == [' 0.1 ', 'Null']
    assert result.DateTime.nunique() == 1
    assert report['years']['2012']['max_energy'] == 9.71


def test_missing_partition_is_rejected(tmp_path):
    with zipfile.ZipFile(tmp_path / 'partial.zip', 'w') as z:
        z.writestr('LCL-June2015v2_0.csv', 'incomplete')
    with pytest.raises(ValueError, match='exactly partitions'):
        rebuild(tmp_path / 'partial.zip', tmp_path / 'out')


def test_energy_fingerprint_survives_scaling_but_detects_reordering():
    raw = np.array([.117, .203, .019, .827, .998, .501, .331, .441, .992, .018, .002, .251, .672, .127, .781, .654, .501])
    encoded = raw / 9.71
    expected = quantize(raw)
    assert np.array_equal(expected, quantize(encoded * 9.71))
    assert fingerprints(expected)[0] == fingerprints(expected[:16])[0]
    assert fingerprints(expected)[1] == fingerprints(expected[1:])[0]
    assert fingerprints(expected)[0] != fingerprints(expected[:16][::-1])[0]


def test_normalized_import_cannot_produce_physical_benchmark(tmp_path):
    p = tmp_path / 'shard.pkl'
    pd.DataFrame({'timestamp': pd.date_range('2012-01-01', periods=32, freq='30min', tz='UTC'), 'kwh': np.linspace(0, 1, 32)}).to_pickle(p)
    pass_two({'encoded2012_0': [p]}, tmp_path / 'dataset', 'normalized')
    import json
    manifest = json.loads((tmp_path / 'dataset/dataset.oed.json').read_text())
    assert validate_manifest(manifest) == []
    channel = manifest['x-oed']['sites'][0]['channels'][0]
    assert channel['unit'] == '1'
    with pytest.raises(ValueError, match='Normalized'):
        watts_factor(channel)
    with pytest.raises(ValueError, match='Unsupported benchmark unit'):
        run_forecast(tmp_path / 'dataset')


def test_order_mapping_fills_only_unambiguous_gaps(tmp_path):
    import json
    from complete_lcl_mapping import complete
    raw, evidence = tmp_path / 'raw', tmp_path / 'evidence'
    raw.mkdir(); evidence.mkdir()
    (raw / 'households-2012.json').write_text(json.dumps(['MAC1', 'MAC2', 'MAC3']))
    (evidence / 'identity-evidence.json').write_text('{}')
    pd.DataFrame([
        dict(encoded_id=0, original_id='MAC1', candidate_count=1, matched_blocks=4, status='verified'),
        dict(encoded_id=1, original_id='', candidate_count=0, matched_blocks=0, status='unresolved'),
        dict(encoded_id=2, original_id='MAC3', candidate_count=1, matched_blocks=4, status='verified'),
    ]).to_csv(evidence / 'mapping-2012.csv', index=False)
    receipt = complete(raw, evidence, tmp_path / 'complete')
    assert receipt['evidence_levels']['order_reconstructed'] == 1
    result = pd.read_csv(tmp_path / 'complete/mapping-2012.csv')
    assert result.original_id.tolist() == ['MAC1','MAC2','MAC3']
    (raw / 'households-2012.json').write_text(json.dumps(['MAC1','MAC2','MAC2b','MAC3']))
    with pytest.raises(ValueError, match='Ambiguous gap'):
        complete(raw, evidence, tmp_path / 'ambiguous')
