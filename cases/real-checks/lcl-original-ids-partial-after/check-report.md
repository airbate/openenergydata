# 能源数据可信性检查

状态：review_required

Feather V2 文件可解码性、参考哈希比对、LCL 户号表示与清单单位一致性；不认证完整性或适合建模。

## manifest.schema · pass

对象：runs/lcl-original-ids-partial

影响：结构有效不等于字段声明真实。

建议：修正清单结构错误后再解释数值。

```json
{
  "errors": []
}
```

## units.declaration · pass

对象：runs/lcl-original-ids-partial

影响：单位声明冲突会影响阈值和误差解释；通过只说明已声明元数据一致，不能反推原始测量单位。

建议：核实来源单位和采样区间，统一元数据；能量需除以区间时长后再与功率阈值比较。

```json
{
  "channels_checked": 5229,
  "failure_count": 0,
  "failures": []
}
```

## units.measurement_truth · unknown

对象：runs/lcl-original-ids-partial

影响：本工具未独立验证原始测量单位、时区或采样区间声明。

建议：用来源说明、标定信息或已知样本交叉验证。

```json
{
  "verified_against_source_specification": false
}
```
