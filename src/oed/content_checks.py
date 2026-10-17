"""Bounded-memory validation of actual OED Parquet contents and manifest hashes."""
from collections import Counter
from pathlib import Path
import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
from oed.io import sha256_file

BATCH_ROWS = 65_536


def inspect_channel(path: Path) -> dict:
    """Strictly increasing UTC timestamps imply no duplicate timestamps.

    For invalid unsorted input, adjacent equal and descending steps are reported;
    this is not a global duplicate count. Comparisons include batch boundaries.
    """
    stats = dict(rows=0, timestamp_nulls=0, value_nonfinite=0, quality_invalid=0,
                 adjacent_duplicate_timestamps=0, descending_timestamp_steps=0,
                 first_timestamp=None, last_timestamp=None)
    with pq.ParquetFile(path) as reader:
        schema = reader.schema_arrow
        if any(schema.names.count(n) != 1 for n in ('timestamp', 'power_w', 'quality')):
            raise ValueError('Required columns timestamp, power_w, quality must each exist exactly once')
        ts_type, value_type, quality_type = [schema.field(n).type for n in ('timestamp','power_w','quality')]
        if not pa.types.is_timestamp(ts_type) or ts_type.tz != 'UTC':
            raise ValueError(f'timestamp must be a UTC Arrow timestamp, got {ts_type}')
        if not (pa.types.is_floating(value_type) or pa.types.is_integer(value_type)):
            raise ValueError(f'power_w must be numeric, got {value_type}')
        if not pa.types.is_integer(quality_type):
            raise ValueError(f'quality must be integer, got {quality_type}')
        previous = None
        for batch in reader.iter_batches(batch_size=BATCH_ROWS, columns=['timestamp','power_w','quality']):
            batch.validate(full=True)
            ts, values, quality = batch.columns
            stats['rows'] += batch.num_rows
            stats['timestamp_nulls'] += ts.null_count
            valid = ts.is_valid().to_numpy(zero_copy_only=False)
            ticks = pc.fill_null(pc.cast(ts,pa.int64()),0).to_numpy(zero_copy_only=False)[valid]
            if len(ticks):
                nonnull = pc.drop_null(ts)
                if stats['first_timestamp'] is None:
                    stats['first_timestamp'] = str(nonnull[0].as_py())
                stats['last_timestamp'] = str(nonnull[-1].as_py())
                left, right = ticks[:-1], ticks[1:]
                stats['adjacent_duplicate_timestamps'] += int(np.count_nonzero(right == left))
                stats['descending_timestamp_steps'] += int(np.count_nonzero(right < left))
                if previous is not None:
                    stats['adjacent_duplicate_timestamps'] += int(ticks[0] == previous)
                    stats['descending_timestamp_steps'] += int(ticks[0] < previous)
                previous = ticks[-1]
            # Arrow converts nullable numeric arrays to floating NumPy arrays with NaNs.
            vals = values.to_numpy(zero_copy_only=False)
            stats['value_nonfinite'] += int(np.count_nonzero(~np.isfinite(vals)))
            qs = quality.to_numpy(zero_copy_only=False)
            stats['quality_invalid'] += int(np.count_nonzero(~np.isfinite(qs) | (qs < 0)))
    stats['valid'] = stats['rows'] > 0 and not any(stats[k] for k in (
        'timestamp_nulls','value_nonfinite','quality_invalid',
        'adjacent_duplicate_timestamps','descending_timestamp_steps'))
    return stats


def check_dataset_contents(root: Path, manifest: dict) -> list[dict]:
    findings = []
    root = root.resolve()
    channels = [(s['id']+'/'+c['id'], c['path']) for s in manifest['x-oed']['sites'] for c in s['channels']]
    references = {}
    for entry in manifest.get('distribution',[]):
        references.setdefault(entry.get('contentUrl'),[]).append(entry.get('sha256'))
    counts = Counter()
    examples = {'references':[], 'integrity':[], 'content':[]}
    evidence_counts = Counter()
    rows = 0
    seen = set()
    subjects = set()

    def record(kind, data):
        evidence_counts[kind] += 1
        if len(examples[kind]) < 20:
            examples[kind].append(data)

    for subject, relative in channels:
        try:
            path = (root/relative).resolve()
            if Path(relative).is_absolute() or not path.is_relative_to(root):
                raise ValueError('Channel path must stay inside the dataset directory')
            if path in seen or subject in subjects:
                raise ValueError('Duplicate channel identity or shared physical file reference')
            seen.add(path); subjects.add(subject)
        except (OSError, ValueError, RuntimeError) as error:
            record('references',{'channel':subject,'path':relative,'error':str(error)})
            continue
        try:
            digest = sha256_file(path)
            expected = references.get(relative,[])
            if len(expected)>1:
                counts['hash_failed'] += 1
                record('integrity',{'channel':subject,'reason':'Ambiguous distribution references','expected':expected})
            elif not expected or not expected[0]:
                counts['hash_unknown'] += 1
                record('integrity',{'channel':subject,'reason':'No expected checksum','actual_sha256':digest})
            elif digest.lower()!=expected[0].lower():
                counts['hash_failed'] += 1
                record('integrity',{'channel':subject,'expected_sha256':expected[0],'actual_sha256':digest})
            else:
                counts['hash_matched'] += 1
        except OSError as error:
            counts['hash_failed'] += 1
            record('integrity',{'channel':subject,'error':str(error)})
        try:
            result = inspect_channel(path)
            counts['files_decoded'] += 1
            rows += result['rows']
            if not result['valid']:
                counts['content_failed'] += 1
                record('content',{'channel':subject,**result})
        except (OSError, ValueError, pa.ArrowException) as error:
            counts['content_failed'] += 1
            record('content',{'channel':subject,'error':str(error)})

    def add(code,status,evidence,impact,action):
        findings.append(dict(code=code,status=status,subject=str(root),evidence=evidence,impact=impact,action=action))
    add('dataset.references','fail' if evidence_counts['references'] else ('pass' if channels else 'unknown'),
        {'channels_declared':len(channels),'failure_count':evidence_counts['references'],'examples':examples['references']},
        '通道路径必须在数据目录内，且通道身份和物理文件引用不能重复。', '修正重复引用或越界路径；被拒绝的路径不会读取。')
    add('dataset.integrity','fail' if counts['hash_failed'] else 'unknown' if counts['hash_unknown'] or evidence_counts['references'] or not channels else 'pass',
        {'matched':counts['hash_matched'],'failed':counts['hash_failed'],'missing_reference':counts['hash_unknown'],
         'issue_count':evidence_counts['integrity'],'examples':examples['integrity']},
        '哈希匹配证明文件与当前清单一致；清单不是独立发布方签名，不能证明来源真实。',
        '发现不匹配时保留现场，确认合法修改或损坏原因；不要自动更新哈希以消除告警。')
    add('dataset.contents','fail' if counts['content_failed'] else 'unknown' if evidence_counts['references'] or not channels else 'pass',
        {'files_decoded':counts['files_decoded'],'rows_examined':rows,'failed_channels':counts['content_failed'],
         'issue_count':evidence_counts['content'],'examples':examples['content'],'batch_rows':BATCH_ROWS,
         'example_limit':20,'duplicate_definition':'strict ascending order; counts are adjacent equal/descending steps, including batch boundaries'},
        '检查 UTC 时间戳严格递增、必要列、空时间戳、NaN/Inf、质量标记类型及非负值。不会把负能耗直接认定为错误。',
        '按具体通道复核异常；保留原始记录，不自动排序、去重或填补。')
    add('dataset.coverage','unknown',{'expected_observation_window_provided':False,'expected_household_inventory_provided':False},
        '文件完整可读、内部有序，不意味着时间覆盖或家庭覆盖完整。', '提供预期观测窗口和户号清单后再判断完整覆盖。')
    return findings
