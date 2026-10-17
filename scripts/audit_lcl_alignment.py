#!/usr/bin/env python3
"""Audit timestamp and value alignment using a separately recovered mapping.

Requires the official rebuild and the earlier audited, unmodified Feather import.
This compares float32 imported values against global MinMax transformed raw kWh;
original null readings remain excluded from value validation, never fabricated.
"""
import argparse
import json
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
from rebuild_lcl_official import ENERGY, digest

AUTHOR_COMMIT = '9192b8874f5bdf1eed3c99a6deba3896bd2ae090'


def compare(raw, encoded, low, high):
    raw = raw.copy()
    raw['timestamp'] = pd.to_datetime(raw.DateTime, utc=True)
    raw['raw_kwh'] = pd.to_numeric(raw[ENERGY].str.strip(), errors='coerce')
    # Match the importer's stable keep-first duplicate policy, without imputation.
    raw = raw.sort_values('timestamp', kind='stable').drop_duplicates('timestamp', keep='first')
    joined = raw[['timestamp', 'raw_kwh']].merge(encoded[['timestamp', 'power_w']], on='timestamp', how='outer', indicator=True, validate='one_to_one')
    both = joined['_merge'].eq('both')
    valid = both & joined.raw_kwh.notna()
    expected = (joined.loc[valid, 'raw_kwh'] - low) / (high - low)
    error = abs(expected - joined.loc[valid, 'power_w'])
    matches = np.isclose(expected, joined.loc[valid, 'power_w'], rtol=0, atol=5e-8)
    return dict(raw_unique_timestamps=len(raw), imported_rows=len(encoded),
                timestamps_matched=int(both.sum()), raw_only=int(joined['_merge'].eq('left_only').sum()),
                imported_only=int(joined['_merge'].eq('right_only').sum()),
                values_checked=int(valid.sum()), values_matched=int(matches.sum()),
                value_mismatches=int((~matches).sum()), original_nulls=int((both & joined.raw_kwh.isna()).sum()),
                max_absolute_error=float(error.max()) if len(error) else None)


def verify(raw_root, imported, mapping, output):
    raw_root, imported, output = map(Path, (raw_root, imported, output))
    manifest = json.loads((raw_root / 'source-manifest.json').read_text())
    classes = pd.read_csv(mapping).sort_values('encoded_id').original_id.tolist()
    index = {}
    for part in manifest['partitions']:
        for household in part['2012']['households']:
            index.setdefault(household, []).append(part['number'])
    @lru_cache(maxsize=2)
    def partition(number):
        return pd.read_parquet(raw_root / 'year=2012' / f'part-{number:03d}.parquet')
    low, high = (manifest['years']['2012'][key] for key in ('min_energy', 'max_energy'))
    results = []
    for code, household in enumerate(classes):
        frames = [partition(n).loc[lambda df: df.LCLid.eq(household)] for n in index[household]]
        raw = pd.concat(frames, ignore_index=True)
        path = imported / 'sites' / f'encoded2012_{code}' / 'energy.parquet'
        values = pd.read_parquet(path)
        result = dict(encoded_id=code, original_id=household, imported_parquet_sha256=digest(path), **compare(raw, values, low, high))
        result['status'] = 'aligned' if result['values_checked'] >= 48 and not any(result[k] for k in ('raw_only', 'imported_only', 'value_mismatches')) else 'misaligned'
        results.append(result)
        if code % 250 == 0:
            print(f'{code+1}/{len(classes)} households checked: {result}', flush=True)
    output.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(results).to_csv(output / 'alignment-2012.csv', index=False)
    summary = dict(author_commit=AUTHOR_COMMIT, method='Timestamp/value audit using the separately reconstructed household mapping',
                   scope='Compares matching clock labels only; UTC tagging is a join convention, not source timezone validation; original null values excluded',
                   float32_absolute_tolerance=5e-8, normalization=dict(method='global MinMaxScaler', min=low, max=high),
                   households=len(results), aligned=sum(r['status']=='aligned' for r in results),
                   totals={key: sum(r[key] for r in results) for key in ('raw_unique_timestamps','imported_rows','timestamps_matched','raw_only','imported_only','values_checked','values_matched','value_mismatches','original_nulls')},
                   raw_source_manifest_sha256=digest(raw_root / 'source-manifest.json'),
                   imported_manifest_sha256=digest(imported / 'dataset.oed.json'), alignment_sha256=digest(output / 'alignment-2012.csv'), input_mapping_sha256=digest(mapping))
    (output / 'alignment-summary.json').write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    return summary


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('raw_root'); p.add_argument('imported'); p.add_argument('mapping'); p.add_argument('output')
    a = p.parse_args()
    verify(a.raw_root, a.imported, a.mapping, a.output)
