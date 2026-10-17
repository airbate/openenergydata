# 能源数据可信性检查

状态：fail

Feather V2 文件可解码性、参考哈希比对、LCL 户号表示、清单单位一致性、Parquet 哈希与实际内容；不认证完整覆盖或适合建模。

## source.checksum · pass

对象：cases/reproduced/truncated.feather

影响：哈希匹配仅证明与提供的参考版本一致，不证明上游文件完整或内容正确。

建议：缺少参考哈希时向发布方获取；不匹配时隔离并核对版本。

```json
{
  "sha256": "4a990576b953a95e943a275315a4237950dc78a01392e10a63e96e8512e8a68f",
  "expected_sha256": "4a990576b953a95e943a275315a4237950dc78a01392e10a63e96e8512e8a68f",
  "bytes": 2494
}
```

## source.structure · fail

对象：cases/reproduced/truncated.feather

影响：文件不能作为完整 Feather 数据输入；可能存在截断或格式损坏。

建议：保留原文件，核对参考哈希；如恢复完整批次，单独标记为部分恢复，不能补造缺失记录。

```json
{
  "error": "Not an Arrow file",
  "decoded_rows": 0,
  "decoded_batches": 0
}
```

## identity.cross_file · unknown

对象：输入文件的户号关联

影响：相同类型或相似编号不能证明跨文件家庭身份一致；本检查不验证户号映射。

建议：取得包含版本与来源的映射表；此前按文件/年份命名空间隔离，不按序号猜测 MAC 户号。

```json
{
  "schemas": [],
  "mapping_provided": false
}
```
