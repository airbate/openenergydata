#!/usr/bin/env python3
"""Recover identities using independently matched contiguous energy fingerprints.

Searches every official 2012 household, not a presumed sorted-ID pairing. Hash
hits are confirmed with exact 1e-6 kWh quantized blocks. Timestamp positions are
reported but deliberately not required to match: this detects corrupted time
alignment. Mapping is limited to source Feather SHA256 in the output receipt.
"""
import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
from rebuild_lcl_official import ENERGY, digest

WIDTH = 16
POWERS = np.array([pow(1000003, i, 2**64) for i in range(WIDTH)], dtype=np.uint64)


def fingerprints(values):
    return np.convolve(values.astype(np.uint64), POWERS, mode='valid') if len(values) >= WIDTH else np.array([], dtype=np.uint64)


def quantize(values):
    return np.rint(np.nan_to_num(values, nan=-999.) * 1_000_000).astype(np.int64)


def recover(feather, raw_root, output):
    raw_root, output = Path(raw_root), Path(output)
    manifest = json.loads((raw_root / 'source-manifest.json').read_text())
    low, high = (manifest['years']['2012'][k] for k in ('min_energy', 'max_energy'))
    samples = defaultdict(list)
    counts = Counter()
    with pa.memory_map(str(feather), 'r') as source:
        schema = pa.ipc.open_file(source).schema
        options = pa.ipc.IpcReadOptions(included_fields=[schema.get_field_index(k) for k in ('LCLid', ENERGY, 'DateTime')])
        reader = pa.ipc.open_file(source, options=options)
        for bi in range(reader.num_record_batches):
            frame = reader.get_batch(bi).to_pandas(ignore_metadata=True)
            for code, group in frame.groupby('LCLid', sort=False):
                values = quantize(group[ENERGY].to_numpy() * (high-low) + low)
                count_before = counts[int(code)]
                counts[int(code)] += len(group)
                for offset in range(0, len(values)-WIDTH+1, 512):
                    block = values[offset:offset+WIDTH]
                    if len(np.unique(block)) < 6 or np.any(block < 0):
                        continue
                    key = int(fingerprints(block)[0])
                    samples[key].append((int(code), count_before+offset, block.copy(), str(group.DateTime.iloc[offset])))
            if bi % 100 == 0:
                print(f'Sampled source batch {bi+1}/{reader.num_record_batches}', flush=True)
    keys = np.array(sorted(samples), dtype=np.uint64)
    matches = defaultdict(lambda: defaultdict(set))
    examples = defaultdict(list)
    raw_counts = Counter()
    for part in manifest['partitions']:
        frame = pd.read_parquet(raw_root / 'year=2012' / f"part-{part['number']:03d}.parquet")
        for household, group in frame.groupby('LCLid', sort=False):
            raw_counts[household] += len(group)
            values = quantize(pd.to_numeric(group[ENERGY].str.strip(), errors='coerce').to_numpy())
            hashes = fingerprints(values)
            pos = np.searchsorted(keys, hashes)
            valid = pos < len(keys)
            hits = np.flatnonzero(valid & (keys[np.minimum(pos, len(keys)-1)] == hashes))
            for offset in hits:
                for code, encoded_offset, block, encoded_time in samples[int(hashes[offset])]:
                    if not np.array_equal(values[offset:offset+WIDTH], block):
                        continue
                    matches[code][household].add(encoded_offset)
                    if len(examples[code]) < 5:
                        examples[code].append(dict(original_id=household, encoded_row_within_household=encoded_offset,
                            encoded_timestamp=encoded_time, raw_timestamp=str(group.DateTime.iloc[offset]),
                            raw_partition=part['number'], raw_partition_row=int(group.index[offset]),
                            raw_kwh=(block/1_000_000).tolist()))
        if part['number'] % 20 == 0:
            print(f"Searched {part['number']+1}/168 raw partitions", flush=True)
    results = []
    for code in sorted(counts):
        candidates = matches[code]
        unique = len(candidates) == 1
        household = next(iter(candidates)) if unique else ''
        blocks = len(candidates[household]) if unique else 0
        results.append(dict(encoded_id=code, original_id=household, source_rows=counts[code],
            raw_rows=raw_counts[household] if unique else None, matched_blocks=blocks,
            candidate_count=len(candidates), status='verified' if unique and blocks >= 3 else 'unresolved'))
    output.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(results).to_csv(output / 'mapping-2012.csv', index=False)
    receipt = dict(method='Search all raw households for sampled 16-reading sequences after reversing global MinMax (0,9.71); no sorted-ID assumption',
        verification_rule='One candidate household across all matching blocks, >=3 distinct sampled offsets, >=6 distinct readings per block; hash hits confirmed by exact quantized arrays',
        limits='Sampled energy identity verification, not all-row equivalence; timestamps NOT validated; nulls and imputation not repaired',
        quantization_kwh=1e-6, sample_stride=512, block_width=WIDTH,
        source_feather_sha256=digest(feather), official_archive_sha256=manifest['archive_sha256'],
        mapping_sha256=digest(output / 'mapping-2012.csv'), source_rows=sum(counts.values()),
        households=len(results), verified=sum(r['status']=='verified' for r in results),
        unresolved=[r for r in results if r['status']!='verified'],
        examples=examples)
    (output / 'identity-evidence.json').write_text(json.dumps(receipt, indent=2))
    print({k: v for k, v in receipt.items() if k != 'examples'}, flush=True)


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('feather');p.add_argument('raw_root');p.add_argument('output')
    a=p.parse_args();recover(a.feather,a.raw_root,a.output)
