import json
from pathlib import Path
import pandas as pd
import pytest
from oed.content_checks import inspect_channel, check_dataset_contents
from oed.io import sha256_file
from oed.trust import write_check_report, check_inputs


def make_file(tmp_path, times=None, values=None, quality=None):
    path=tmp_path/'channel.parquet'
    times=times if times is not None else pd.date_range('2014-01-01',periods=4,freq='30min',tz='UTC')
    pd.DataFrame({'timestamp':times,'power_w':values if values is not None else [1.]*len(times),
                  'quality':quality if quality is not None else [0]*len(times)}).to_parquet(path,index=False)
    return path


def manifest(path):
    return {'distribution':[{'contentUrl':path.name,'sha256':sha256_file(path)}],
            'x-oed':{'sites':[{'id':'demo','channels':[{'id':'energy','path':path.name}]}]}}


def by_code(findings,code):
    return next(f for f in findings if f['code']==code)


def test_cross_batch_duplicate_and_descending(tmp_path,monkeypatch):
    monkeypatch.setattr('oed.content_checks.BATCH_ROWS',2)
    times=pd.to_datetime(['2014-01-01 00:00','2014-01-01 01:00','2014-01-01 01:00','2014-01-01 00:30'],utc=True)
    result=inspect_channel(make_file(tmp_path,times))
    assert not result['valid']
    assert result['adjacent_duplicate_timestamps']==1
    assert result['descending_timestamp_steps']==1


def test_null_nan_inf_and_negative_quality(tmp_path):
    times=pd.to_datetime(['2014-01-01',None,'2014-01-03','2014-01-04'],utc=True)
    result=inspect_channel(make_file(tmp_path,times,[1.,float('nan'),float('inf'),-2.],[0,-1,0,0]))
    assert result['timestamp_nulls']==1
    assert result['value_nonfinite']==2
    assert result['quality_invalid']==1


def test_negative_readings_alone_are_not_invalid(tmp_path):
    assert inspect_channel(make_file(tmp_path,values=[-1.,0.,1.,2.]))['valid']


def test_submicrosecond_order_is_not_lost_to_float_conversion(tmp_path,monkeypatch):
    monkeypatch.setattr('oed.content_checks.BATCH_ROWS',2)
    times=pd.date_range('2026-01-01',periods=4,freq='ns',tz='UTC')
    assert inspect_channel(make_file(tmp_path,times))['valid']


def test_tampered_but_readable_file_fails_hash(tmp_path):
    path=make_file(tmp_path);m=manifest(path)
    make_file(tmp_path,values=[2.,2.,2.,2.])
    findings=check_dataset_contents(tmp_path,m)
    assert by_code(findings,'dataset.integrity')['status']=='fail'
    assert by_code(findings,'dataset.contents')['status']=='pass'


def test_missing_file_is_failure(tmp_path):
    path=make_file(tmp_path);m=manifest(path);path.unlink()
    findings=check_dataset_contents(tmp_path,m)
    assert by_code(findings,'dataset.integrity')['status']=='fail'
    assert by_code(findings,'dataset.contents')['status']=='fail'


def test_missing_hash_is_unknown(tmp_path):
    path=make_file(tmp_path);m=manifest(path);m['distribution']=[]
    findings=check_dataset_contents(tmp_path,m)
    assert by_code(findings,'dataset.integrity')['status']=='unknown'
    assert by_code(findings,'dataset.contents')['status']=='pass'
    assert by_code(findings,'dataset.coverage')['status']=='unknown'


def test_outside_and_symlink_paths_are_not_read(tmp_path,monkeypatch):
    outer=tmp_path/'outside';outer.mkdir();outside=make_file(outer)
    root=tmp_path/'dataset';root.mkdir()
    (root/'escape.parquet').symlink_to(outside)
    m=manifest(outside)
    def forbidden(*args):
        raise AssertionError('must not read escaped paths')
    monkeypatch.setattr('oed.content_checks.sha256_file',forbidden)
    monkeypatch.setattr('oed.content_checks.inspect_channel',forbidden)
    for path in ['../outside/channel.parquet',str(outside),'escape.parquet']:
        m['x-oed']['sites'][0]['channels'][0]['path']=path
        assert by_code(check_dataset_contents(root,m),'dataset.references')['status']=='fail'


def test_duplicate_references_rejected(tmp_path):
    path=make_file(tmp_path);m=manifest(path)
    m['x-oed']['sites'][0]['channels'].append({'id':'other','path':path.name})
    findings=check_dataset_contents(tmp_path,m)
    assert by_code(findings,'dataset.references')['status']=='fail'
    assert by_code(findings,'dataset.contents')['evidence']['rows_examined']==4


def test_timezone_missing_columns_and_empty(tmp_path):
    path=make_file(tmp_path,times=pd.date_range('2014-01-01',periods=4))
    with pytest.raises(ValueError,match='UTC'):
        inspect_channel(path)
    pd.DataFrame({'timestamp':[1]}).to_parquet(path)
    with pytest.raises(ValueError,match='Required columns'):
        inspect_channel(path)
    times=pd.DatetimeIndex([],tz='UTC')
    path=make_file(tmp_path,times,[],pd.Series([],dtype='int32'))
    assert not inspect_channel(path)['valid']


def test_reports_must_not_write_into_input_dataset(oed_dataset):
    report=check_inputs([],oed_dataset)
    with pytest.raises(ValueError,match='outside the input dataset'):
        write_check_report(report,oed_dataset/'reports')
