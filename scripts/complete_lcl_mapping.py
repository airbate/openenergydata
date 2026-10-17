#!/usr/bin/env python3
"""Complete LabelEncoder order mapping only where evidence leaves one solution.

Distinct evidence levels remain explicit: >=3 raw sequence matches, 1–2
matches plus order, or order-only reconstruction between verified anchors.
Never fill a gap whose number of raw IDs differs from encoded IDs.
"""
import argparse
import json
from pathlib import Path
import pandas as pd
from rebuild_lcl_official import digest


def complete(raw_root, evidence, output):
    raw_root, evidence, output = map(Path, (raw_root, evidence, output))
    classes = json.loads((raw_root / 'households-2012.json').read_text())
    index = {name: i for i, name in enumerate(classes)}
    frame = pd.read_csv(evidence / 'mapping-2012.csv', keep_default_na=False)
    if frame.encoded_id.tolist() != list(range(len(frame))):
        raise ValueError('Encoded IDs must be contiguous from zero')
    anchors = [(-1, -1)] + [(int(r.encoded_id), index[r.original_id]) for r in frame.itertuples() if r.original_id and r.candidate_count == 1] + [(len(frame), len(classes))]
    if not all(b[1] > a[1] for a, b in zip(anchors, anchors[1:])):
        raise ValueError('Unique sequence matches contradict LabelEncoder ordering')
    for (left_code, left_id), (right_code, right_id) in zip(anchors, anchors[1:]):
        if right_code-left_code > 1 and right_code-left_code == right_id-left_id:
            for code in range(left_code+1, right_code):
                frame.loc[code, 'original_id'] = classes[left_id + code-left_code]
                frame.loc[code, 'status'] = 'order_reconstructed'
        elif right_code-left_code > 1:
            raise ValueError(f'Ambiguous gap between encoded IDs {left_code} and {right_code}; no guess allowed')
    frame['evidence_level'] = frame.apply(lambda r: 'sequence_verified' if r.status=='verified' else 'sequence_and_order' if int(r.matched_blocks)>0 else 'order_reconstructed', axis=1)
    if (frame.original_id == '').any() or not frame.original_id.is_unique:
        raise ValueError('Incomplete or non-unique mapping')
    frame['status'] = frame.evidence_level
    output.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output / 'mapping-2012.csv', index=False)
    receipt = dict(households=len(frame), evidence_levels=frame.evidence_level.value_counts().to_dict(),
        excluded_raw_2012_ids=sorted(set(classes)-set(frame.original_id)),
        author_notebook='https://github.com/sufirehman/ElectricityConsumptionPredictionUsingDeepLearning/blob/9192b8874f5bdf1eed3c99a6deba3896bd2ae090/ECP.ipynb',
        author_cell_zero_based=141, method='Monotonic LabelEncoder sorted-string order, constrained by unique energy-sequence anchors; only equal-sized gaps filled',
        limitation='Order reconstruction depends on published LabelEncoder implementation matching this Feather release; does not restore timestamps or authorize physical benchmarks',
        identity_evidence_sha256=digest(evidence / 'identity-evidence.json'),
        mapping_sha256=digest(output / 'mapping-2012.csv'))
    (output / 'mapping-receipt.json').write_text(json.dumps(receipt, indent=2))
    print(json.dumps(receipt, indent=2))
    return receipt


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('raw_root');p.add_argument('evidence');p.add_argument('output')
    a=p.parse_args();complete(a.raw_root,a.evidence,a.output)
