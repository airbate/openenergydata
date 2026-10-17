"""Read-only evidence checks. Passing checks are not a certification of a dataset."""
from __future__ import annotations
import html
import json
from datetime import datetime, timezone
from pathlib import Path
import pyarrow as pa
from oed.io import sha256_file, validate_manifest
from oed.units import watts_factor
from oed.content_checks import check_dataset_contents


def check_inputs(sources: list[Path], dataset: Path | None = None,
                 expected_hashes: dict[str, str] | None = None) -> dict:
    findings = []
    identities = []

    def add(code, status, subject, evidence, impact, action):
        findings.append(dict(code=code, status=status, subject=str(subject),
                             evidence=evidence, impact=impact, action=action))

    for path in sources:
        try:
            digest = sha256_file(path)
        except OSError as error:
            add('source.readable', 'fail', path, {'error': str(error)},
                '文件无法读取，不能完成检查。', '检查文件路径和访问权限。')
            continue
        expected = (expected_hashes or {}).get(path.name)
        add('source.checksum', 'unknown' if not expected else ('pass' if digest == expected else 'fail'), path,
            {'sha256': digest, 'expected_sha256': expected, 'bytes': path.stat().st_size},
            '哈希匹配仅证明与提供的参考版本一致，不证明上游文件完整或内容正确。',
            '缺少参考哈希时向发布方获取；不匹配时隔离并核对版本。')
        rows = batches = 0
        try:
            with pa.memory_map(str(path), 'r') as source:
                reader = pa.ipc.open_file(source)
                schema = reader.schema
                if 'LCLid' in schema.names:
                    kind = schema.field('LCLid').type
                    if pa.types.is_dictionary(kind):
                        kind = kind.value_type
                    family = 'numeric' if pa.types.is_integer(kind) or pa.types.is_floating(kind) else 'text' if pa.types.is_string(kind) or pa.types.is_large_string(kind) else 'other'
                    sample = reader.get_batch(0).column(schema.get_field_index('LCLid')).slice(0,5).to_pylist() if reader.num_record_batches else []
                    identities.append({'file': str(path), 'type': str(kind), 'family': family, 'sample': sample})
                for index in range(reader.num_record_batches):
                    batch = reader.get_batch(index)
                    batch.validate(full=True)
                    rows += batch.num_rows
                    batches += 1
            add('source.structure', 'pass', path, {'decoded_rows': rows, 'decoded_batches': batches},
                '全部 IPC 批次可解码；尚不证明所有预期时间和家庭都在文件中。', '继续检查发布方覆盖范围及身份映射。')
        except (pa.ArrowInvalid, pa.ArrowIOError, OSError, ValueError) as error:
            add('source.structure', 'fail', path, {'error': str(error), 'decoded_rows': rows, 'decoded_batches': batches},
                '文件不能作为完整 Feather 数据输入；可能存在截断或格式损坏。',
                '保留原文件，核对参考哈希；如恢复完整批次，单独标记为部分恢复，不能补造缺失记录。')

    if sources:
        families = {x['family'] for x in identities}
        mixed = len(families) > 1
        add('identity.cross_file', 'fail' if mixed else 'unknown', '输入文件的户号关联',
            {'schemas': identities, 'mapping_provided': False},
            '户号表示不同，未经映射的跨文件关联不受支持。' if mixed else '相同类型或相似编号不能证明跨文件家庭身份一致；本检查不验证户号映射。',
            '取得包含版本与来源的映射表；此前按文件/年份命名空间隔离，不按序号猜测 MAC 户号。')

    if dataset is not None:
        try:
            manifest = json.loads((dataset / 'dataset.oed.json').read_text())
            errors = validate_manifest(manifest)
            add('manifest.schema', 'fail' if errors else 'pass', dataset, {'errors': errors},
                '结构有效不等于字段声明真实。', '修正清单结构错误后再解释数值。')
            if not errors:
                records = {r['name']: r for r in manifest.get('recordSet', [])}
                failures = []
                checked = 0
                for site in manifest['x-oed']['sites']:
                    for channel in site['channels']:
                        checked += 1
                        subject = f"{site['id']}/{channel['id']}"
                        try:
                            factor = watts_factor(channel)
                        except (ValueError, TypeError) as error:
                            failures.append({'channel': subject, 'reason': str(error)})
                            continue
                        fields = records.get(subject, {}).get('field', [])
                        description = next((f.get('description') for f in fields if f.get('name') == 'power_w'), None)
                        if description != channel.get('unit'):
                            failures.append({'channel': subject, 'declared_unit': channel.get('unit'),
                                             'field_unit_description': description,
                                             'factor_to_watts': factor,
                                             'reason': 'recordSet 数值字段单位与通道声明不一致或缺失'})
                add('units.declaration', 'fail' if failures else 'pass', dataset,
                    {'channels_checked': checked, 'failure_count': len(failures), 'failures': failures},
                    '单位声明冲突会影响阈值和误差解释；通过只说明已声明元数据一致，不能反推原始测量单位。',
                    '核实来源单位和采样区间，统一元数据；能量需除以区间时长后再与功率阈值比较。')
                findings.extend(check_dataset_contents(dataset, manifest))
                add('units.measurement_truth', 'unknown', dataset, {'verified_against_source_specification': False},
                    '本工具未独立验证原始测量单位、时区或采样区间声明。', '用来源说明、标定信息或已知样本交叉验证。')
        except (OSError, ValueError, TypeError, KeyError) as error:
            add('manifest.readable', 'fail', dataset, {'error': str(error)}, '无法解释数据集元数据。', '修复或补充清单。')
    if not sources and dataset is None:
        raise ValueError('Provide at least one source or dataset')
    return {'schema_version': 'oed-trust/2', 'generated_at': datetime.now(timezone.utc).isoformat(),
            'status': 'fail' if any(f['status'] == 'fail' for f in findings) else 'review_required' if any(f['status'] == 'unknown' for f in findings) else 'pass',
            'scope': 'Feather V2 文件可解码性、参考哈希比对、LCL 户号表示、清单单位一致性、Parquet 哈希与实际内容；不认证完整覆盖或适合建模。',
            'findings': findings}


def write_check_report(report: dict, output: Path) -> Path:
    targets = {(output/name).resolve() for name in ('check-report.json', 'check-report.md', 'check-report.html')}
    for finding in report['findings']:
        if finding['code'].startswith(('dataset.', 'manifest.', 'units.')) and any(target.is_relative_to(Path(finding['subject']).resolve()) for target in targets):
            raise ValueError('Report output must be outside the input dataset directory')
        if finding['code'].startswith('source.') and Path(finding['subject']).resolve() in targets:
            raise ValueError('Report output would overwrite a source file; choose another output directory')
    output.mkdir(parents=True, exist_ok=True)
    (output/'check-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
    lines = ['# 能源数据可信性检查', '', f"状态：{report['status']}", '', report['scope'], '']
    cards = []
    for f in report['findings']:
        evidence = json.dumps(f['evidence'], ensure_ascii=False, indent=2)
        lines += [f"## {f['code']} · {f['status']}", '', f"对象：{f['subject']}", '', f"影响：{f['impact']}", '', f"建议：{f['action']}", '', '```json', evidence, '```', '']
        esc = html.escape
        cards.append(f"<article><h2>{esc(f['code'])} · {esc(f['status'])}</h2><p>{esc(f['subject'])}</p><p>{esc(f['impact'])}</p><p>{esc(f['action'])}</p><details><summary>查看证据</summary><pre>{esc(evidence)}</pre></details></article>")
    (output/'check-report.md').write_text('\n'.join(lines))
    (output/'check-report.html').write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>能源数据可信性检查</title><style>body{max-width:1000px;margin:40px auto;padding:0 24px;font:16px/1.7 system-ui;background:#f5f7fa;color:#17243a}article{background:white;padding:20px;margin:18px 0;border-radius:12px}pre{white-space:pre-wrap;overflow-wrap:anywhere}h1{font-size:30px}</style><h1>能源数据可信性检查</h1><p>状态：'+html.escape(report['status'])+'</p><p>'+html.escape(report['scope'])+'</p>'+''.join(cards)+'</html>')
    return output/'check-report.html'
