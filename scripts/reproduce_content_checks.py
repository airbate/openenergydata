#!/usr/bin/env python3
"""Synthetic demonstration: readable or rehashed files can still be invalid."""
import argparse
import json
import shutil
from pathlib import Path
import pandas as pd
from oed.converters.common import DatasetBuilder
from oed.io import write_manifest, sha256_file
from oed.trust import check_inputs, write_check_report


def main(output: Path):
    clean=output/'clean-data'
    builder=DatasetBuilder(clean,name='synthetic-content-check',description='Synthetic, not a real LCL defect',source_url='https://example.org/synthetic',source_license='CC0-1.0',citation='reproduce_content_checks.py',dataset_id='synthetic')
    channel={'id':'energy','path':'sites/demo/energy.parquet','role':'site_meter','physical_quantity':'energy','ac_type':'active','unit':'kWh','nominal_interval_s':1800}
    frame=pd.DataFrame({'timestamp':pd.date_range('2014-01-01',periods=4,freq='30min',tz='UTC'),'power_w':[1.,2.,3.,4.],'quality':[0,0,0,0]})
    builder.add_channel('demo',channel,frame)
    builder.add_site({'id':'demo','timezone':'UTC','channels':[channel]})
    write_manifest(builder.build(),clean)
    changed=output/'changed-data'
    shutil.copytree(clean,changed,dirs_exist_ok=True)
    bad=frame.copy()
    bad['timestamp']=pd.to_datetime(['2014-01-01 00:00','2014-01-01 01:00','2014-01-01 01:00','2014-01-01 00:30'],utc=True)
    bad['power_w']=[1.,float('nan'),float('inf'),4.]
    bad.to_parquet(changed/channel['path'],index=False)
    rehashed=output/'rehashed-data'
    shutil.copytree(changed,rehashed,dirs_exist_ok=True)
    manifest=json.loads((rehashed/'dataset.oed.json').read_text())
    manifest['distribution'][0]['sha256']=sha256_file(rehashed/channel['path'])
    write_manifest(manifest,rehashed)
    summary={}
    for label,root in [('clean',clean),('changed',changed),('rehashed',rehashed)]:
        report=check_inputs([],root)
        write_check_report(report,output/(label+'-report'))
        summary[label]={f['code']:f['status'] for f in report['findings']}
    assert summary['clean']['dataset.contents']=='pass'
    assert summary['changed']['dataset.integrity']=='fail'
    assert summary['changed']['dataset.contents']=='fail'
    assert summary['rehashed']['dataset.integrity']=='pass'
    assert summary['rehashed']['dataset.contents']=='fail'
    (output/'summary.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path('cases/content-demo'))
    main(parser.parse_args().output)
