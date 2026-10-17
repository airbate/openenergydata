#!/usr/bin/env python3
"""Extract untouched 2012/2013 readings from all 168 official CSV partitions.

No timezone assignment, imputation, normalization or duplicate removal. Reads one
CSV at a time; verifies ZIP CRC and records each decompressed member's SHA256.
"""
import argparse
import hashlib
import io
import json
import re
import zipfile
from pathlib import Path

import pandas as pd

SOURCE_URL = 'https://data.london.gov.uk/download/vqm0d/04feba67-f1a3-4563-98d0-f3071e3d56d1/Partitioned%20LCL%20Data.zip'
ENERGY = 'KWH/hh (per half hour) '


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        while block := f.read(1024 * 1024):
            h.update(block)
    return h.hexdigest()


def rebuild(archive, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    manifest = dict(source_url=SOURCE_URL, archive_sha256=digest(archive),
                    timestamp_policy='Original timezone-unspecified wall-clock strings retained',
                    energy_unit='kWh per half hour', transformations='None; nulls and duplicates retained',
                    partitions=[], years={})
    ids = {year: set() for year in (2012, 2013)}
    stats = {year: dict(rows=0, null_energy=0, months={}, min_energy=None, max_energy=None) for year in ids}
    with zipfile.ZipFile(archive) as z:
        members = [(int(m.group(1)), n) for n in z.namelist()
                   if (m := re.search(r'(?:^|/)LCL-June2015v2_(\d+)\.csv$', n)) and not n.startswith('__MACOSX/')]
        members.sort()
        if [n for n, _ in members] != list(range(168)):
            raise ValueError('Expected exactly partitions 0..167')
        for number, name in members:
            raw = z.read(name)  # ZIP reader verifies CRC
            entry = dict(number=number, member=name, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
            df = pd.read_csv(io.BytesIO(raw), dtype=str, keep_default_na=False)
            if set(df.columns) != {'LCLid', 'stdorToU', 'DateTime', ENERGY}:
                raise ValueError(f'Unexpected columns: {list(df.columns)}')
            entry['rows'] = len(df)
            for year in ids:
                sub = df.loc[df.DateTime.str.startswith(str(year))].copy()
                target = output / f'year={year}' / f'part-{number:03d}.parquet'
                target.parent.mkdir(exist_ok=True)
                sub.to_parquet(target, index=False, compression='zstd')
                entry[str(year)] = dict(rows=len(sub), households=sorted(sub.LCLid.unique()), parquet_sha256=digest(target))
                ids[year].update(sub.LCLid)
                st = stats[year]
                st['rows'] += len(sub)
                values = pd.to_numeric(sub[ENERGY].str.strip(), errors='coerce')
                st['null_energy'] += int(values.isna().sum())
                if values.notna().any():
                    lo, hi = float(values.min()), float(values.max())
                    st['min_energy'] = lo if st['min_energy'] is None else min(lo, st['min_energy'])
                    st['max_energy'] = hi if st['max_energy'] is None else max(hi, st['max_energy'])
                for month, count in sub.DateTime.str[:7].value_counts().items():
                    st['months'][month] = st['months'].get(month, 0) + int(count)
            manifest['partitions'].append(entry)
            print(f'{number+1}/168 partitions extracted', flush=True)
    for year in ids:
        stats[year]['households'] = len(ids[year])
        manifest['years'][str(year)] = stats[year]
        (output / f'households-{year}.json').write_text(json.dumps(sorted(ids[year]), indent=2))
    (output / 'source-manifest.json').write_text(json.dumps(manifest, indent=2))
    return manifest


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('archive', type=Path)
    p.add_argument('output', type=Path)
    args = p.parse_args()
    rebuild(args.archive, args.output)
