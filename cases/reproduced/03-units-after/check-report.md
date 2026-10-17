# 能源数据可信性检查

状态：review_required

Feather V2 文件可解码性、参考哈希比对、LCL 户号表示、清单单位一致性、Parquet 哈希与实际内容；不认证完整覆盖或适合建模。

## manifest.schema · pass

对象：cases/reproduced/energy-dataset

影响：结构有效不等于字段声明真实。

建议：修正清单结构错误后再解释数值。

```json
{
  "errors": []
}
```

## units.declaration · pass

对象：cases/reproduced/energy-dataset

影响：单位声明冲突会影响阈值和误差解释；通过只说明已声明元数据一致，不能反推原始测量单位。

建议：核实来源单位和采样区间，统一元数据；能量需除以区间时长后再与功率阈值比较。

```json
{
  "channels_checked": 1,
  "failure_count": 0,
  "failures": []
}
```

## dataset.references · pass

对象：/Users/airbate/Documents/Codex/2026-10-16/new-chat-2/outputs/openenergydata/cases/reproduced/energy-dataset

影响：通道路径必须在数据目录内，且通道身份和物理文件引用不能重复。

建议：修正重复引用或越界路径；被拒绝的路径不会读取。

```json
{
  "channels_declared": 1,
  "failure_count": 0,
  "examples": []
}
```

## dataset.integrity · pass

对象：/Users/airbate/Documents/Codex/2026-10-16/new-chat-2/outputs/openenergydata/cases/reproduced/energy-dataset

影响：哈希匹配证明文件与当前清单一致；清单不是独立发布方签名，不能证明来源真实。

建议：发现不匹配时保留现场，确认合法修改或损坏原因；不要自动更新哈希以消除告警。

```json
{
  "matched": 1,
  "failed": 0,
  "missing_reference": 0,
  "issue_count": 0,
  "examples": []
}
```

## dataset.contents · pass

对象：/Users/airbate/Documents/Codex/2026-10-16/new-chat-2/outputs/openenergydata/cases/reproduced/energy-dataset

影响：检查 UTC 时间戳严格递增、必要列、空时间戳、NaN/Inf、质量标记类型及非负值。不会把负能耗直接认定为错误。

建议：按具体通道复核异常；保留原始记录，不自动排序、去重或填补。

```json
{
  "files_decoded": 1,
  "rows_examined": 3,
  "failed_channels": 0,
  "issue_count": 0,
  "examples": [],
  "batch_rows": 65536,
  "example_limit": 20,
  "duplicate_definition": "strict ascending order; counts are adjacent equal/descending steps, including batch boundaries"
}
```

## dataset.coverage · unknown

对象：/Users/airbate/Documents/Codex/2026-10-16/new-chat-2/outputs/openenergydata/cases/reproduced/energy-dataset

影响：文件完整可读、内部有序，不意味着时间覆盖或家庭覆盖完整。

建议：提供预期观测窗口和户号清单后再判断完整覆盖。

```json
{
  "expected_observation_window_provided": false,
  "expected_household_inventory_provided": false
}
```

## units.measurement_truth · unknown

对象：cases/reproduced/energy-dataset

影响：本工具未独立验证原始测量单位、时区或采样区间声明。

建议：用来源说明、标定信息或已知样本交叉验证。

```json
{
  "verified_against_source_specification": false
}
```
