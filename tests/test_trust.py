import json
from pathlib import Path
import pandas as pd
import pyarrow as pa
import pytest
from typer.testing import CliRunner
from oed.cli import app
from oed.trust import check_inputs, write_check_report
from oed.io import sha256_file
from oed.units import watts_factor


def feather(path, ids):
    pd.DataFrame({'DateTime': pd.date_range('2012-01-01', periods=len(ids), freq='30min'),
                  'LCLid': ids, 'KWH/hh': [1.] * len(ids)}).to_feather(path)
    return path


def finding(report, code):
    return next(f for f in report['findings'] if f['code'] == code)


def test_matching_hash_does_not_hide_truncation(tmp_path):
    source = feather(tmp_path/'bad.feather', ['MAC1']*4)
    source.write_bytes(source.read_bytes()[:-20])
    digest = sha256_file(source)
    report = check_inputs([source], expected_hashes={source.name:digest})
    assert finding(report, 'source.checksum')['status'] == 'pass'
    assert finding(report, 'source.structure')['status'] == 'fail'
    assert report['status'] == 'fail'
    write_check_report(report, tmp_path/'report')
    assert sha256_file(source) == digest


def test_mixed_identity_is_not_silently_joined(tmp_path):
    text = feather(tmp_path/'text.feather', ['MAC1'])
    number = feather(tmp_path/'number.feather', [0])
    assert finding(check_inputs([text, number]), 'identity.cross_file')['status'] == 'fail'
    assert finding(check_inputs([text]), 'identity.cross_file')['status'] == 'unknown'


def test_full_batches_read_and_missing_checksum_explicit(tmp_path):
    source = feather(tmp_path/'good.feather', ['MAC1']*10)
    report = check_inputs([source])
    assert finding(report, 'source.structure')['evidence']['decoded_rows'] == 10
    assert finding(report, 'source.checksum')['status'] == 'unknown'
    assert report['status'] == 'review_required'


def test_hash_mismatch_and_missing_file(tmp_path):
    source = feather(tmp_path/'good.feather', ['MAC1'])
    report = check_inputs([source, tmp_path/'missing'], expected_hashes={source.name:'0'*64})
    assert finding(report, 'source.checksum')['status'] == 'fail'
    assert finding(report, 'source.readable')['status'] == 'fail'


@pytest.mark.parametrize('interval', [0,-1,float('nan'),float('inf')])
def test_invalid_energy_interval_fails_closed(interval):
    with pytest.raises(ValueError):
        watts_factor({'physical_quantity':'energy','unit':'kWh','nominal_interval_s':interval})


def test_energy_conversion_is_dimensionally_correct():
    factor = watts_factor({'physical_quantity':'energy','unit':'kWh','nominal_interval_s':1800})
    assert 30*factor == 60000
    with pytest.raises(ValueError):
        watts_factor({'physical_quantity':'power','unit':'V'})


def test_manifest_unit_conflict_and_fix(oed_dataset):
    path = oed_dataset/'dataset.oed.json'
    manifest = json.loads(path.read_text())
    channel = manifest['x-oed']['sites'][0]['channels'][0]
    channel.update(physical_quantity='energy',unit='kWh',nominal_interval_s=1800)
    path.write_text(json.dumps(manifest))
    assert finding(check_inputs([],oed_dataset),'units.declaration')['status'] == 'fail'
    name = manifest['x-oed']['sites'][0]['id']+'/'+channel['id']
    record = next(r for r in manifest['recordSet'] if r['name']==name)
    next(f for f in record['field'] if f['name']=='power_w')['description']='kWh'
    path.write_text(json.dumps(manifest))
    assert finding(check_inputs([],oed_dataset),'units.declaration')['status'] == 'pass'
    assert check_inputs([],oed_dataset)['status']=='review_required'


def test_cli_exit_codes_and_reports(tmp_path):
    source = feather(tmp_path/'bad.feather',['MAC1'])
    source.write_bytes(source.read_bytes()[:-20])
    runner=CliRunner()
    result=runner.invoke(app,['check',str(source),'-o',str(tmp_path/'report')])
    assert result.exit_code==2, result.output
    assert (tmp_path/'report/check-report.html').exists()
    assert runner.invoke(app,['check']).exit_code==2
    good=feather(tmp_path/'good.feather',['MAC1'])
    result=runner.invoke(app,['check',str(good),'-o',str(tmp_path/'good-report')])
    assert result.exit_code==0 and 'review_required' in result.output


def test_report_cannot_overwrite_an_input(tmp_path):
    source = feather(tmp_path/'check-report.json',['MAC1'])
    digest = sha256_file(source)
    with pytest.raises(ValueError,match='overwrite'):
        write_check_report(check_inputs([source]),tmp_path)
    assert sha256_file(source)==digest


def test_generated_energy_manifest_has_consistent_units(tmp_path):
    from oed.converters.common import DatasetBuilder
    from oed.io import write_manifest
    root=tmp_path/'dataset'
    builder=DatasetBuilder(root,name='unit-test',description='fixture',source_url='https://example.org',source_license='CC0-1.0',citation='fixture',dataset_id='fixture')
    ch={'id':'energy','path':'sites/test/energy.parquet','role':'site_meter','physical_quantity':'energy','ac_type':'active','unit':'kWh','nominal_interval_s':1800}
    df=pd.DataFrame({'timestamp':pd.date_range('2012-01-01',periods=3,freq='30min',tz='UTC'),'power_w':[1.,2.,3.],'quality':[0,0,0]})
    builder.add_channel('test',ch,df)
    builder.add_site({'id':'test','timezone':'UTC','channels':[ch]})
    write_manifest(builder.build(),root)
    assert finding(check_inputs([],root),'units.declaration')['status']=='pass'
