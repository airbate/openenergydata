#!/usr/bin/env python3
"""Recover complete IPC batches from a truncated Feather V2 file.

Recovery does not establish upstream completeness, even at end-of-stream.
Never replace the original. The adjacent JSON audit records the exact stop reason.
"""
import argparse
import json
from pathlib import Path
import pyarrow as pa


def recover(source: Path, output: Path) -> dict:
    if output.exists() or source.resolve() == output.resolve():
        raise ValueError('Choose a new output path; source and existing files are preserved')
    output.parent.mkdir(parents=True, exist_ok=True)
    audit = {'source': str(source.resolve()), 'recovered_file': str(output.resolve()),
             'complete': False, 'rows': 0, 'batches': 0}
    with pa.memory_map(str(source), 'r') as stream:
        if stream.read(6) != b'ARROW1':
            raise ValueError('Only Feather V2 / Arrow IPC files are supported')
        stream.seek(8)
        reader = pa.ipc.open_stream(stream)
        names = ['DateTime', 'LCLid', next(n for n in reader.schema.names if n.strip() in ('KWH/hh', 'KWH/hh (per half hour)'))]
        schema = pa.schema([reader.schema.field(n) for n in names])
        with pa.OSFile(str(output), 'wb') as sink, pa.ipc.new_file(
            sink, schema, options=pa.ipc.IpcWriteOptions(compression='lz4')
        ) as writer:
            while True:
                try:
                    batch = reader.read_next_batch().select(names)
                except StopIteration:
                    audit['stream_exhausted'] = True
                    # Exhaustion alone cannot establish completeness of an upstream file.
                    break
                except (pa.ArrowInvalid, OSError) as error:
                    audit['error'] = str(error)
                    break
                writer.write_batch(batch)
                audit['rows'] += batch.num_rows
                audit['batches'] += 1
    output.with_suffix('.recovery.json').write_text(json.dumps(audit, indent=2))
    return audit


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    print(json.dumps(recover(args.source, args.output), indent=2))
