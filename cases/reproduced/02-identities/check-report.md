# 能源数据可信性检查

状态：fail

Feather V2 文件可解码性、参考哈希比对、LCL 户号表示、清单单位一致性、Parquet 哈希与实际内容；不认证完整覆盖或适合建模。

## source.checksum · pass

对象：cases/reproduced/text-ids.feather

影响：哈希匹配仅证明与提供的参考版本一致，不证明上游文件完整或内容正确。

建议：缺少参考哈希时向发布方获取；不匹配时隔离并核对版本。

```json
{
  "sha256": "92733a370310c38c5764bb2934f9f0261f1ab0ba0a4c5300bb812e4eb3302b20",
  "expected_sha256": "92733a370310c38c5764bb2934f9f0261f1ab0ba0a4c5300bb812e4eb3302b20",
  "bytes": 2514
}
```

## source.structure · pass

对象：cases/reproduced/text-ids.feather

影响：全部 IPC 批次可解码；尚不证明所有预期时间和家庭都在文件中。

建议：继续检查发布方覆盖范围及身份映射。

```json
{
  "decoded_rows": 3,
  "decoded_batches": 1
}
```

## source.checksum · pass

对象：cases/reproduced/numeric-ids.feather

影响：哈希匹配仅证明与提供的参考版本一致，不证明上游文件完整或内容正确。

建议：缺少参考哈希时向发布方获取；不匹配时隔离并核对版本。

```json
{
  "sha256": "38bfe3c49538cf77b340a072d1e3da51c4408d7bfd4af8fefee19aef895ca997",
  "expected_sha256": "38bfe3c49538cf77b340a072d1e3da51c4408d7bfd4af8fefee19aef895ca997",
  "bytes": 2482
}
```

## source.structure · pass

对象：cases/reproduced/numeric-ids.feather

影响：全部 IPC 批次可解码；尚不证明所有预期时间和家庭都在文件中。

建议：继续检查发布方覆盖范围及身份映射。

```json
{
  "decoded_rows": 3,
  "decoded_batches": 1
}
```

## identity.cross_file · fail

对象：输入文件的户号关联

影响：户号表示不同，未经映射的跨文件关联不受支持。

建议：取得包含版本与来源的映射表；此前按文件/年份命名空间隔离，不按序号猜测 MAC 户号。

```json
{
  "schemas": [
    {
      "file": "cases/reproduced/text-ids.feather",
      "type": "large_string",
      "family": "text",
      "sample": [
        "MAC000001",
        "MAC000001",
        "MAC000001"
      ]
    },
    {
      "file": "cases/reproduced/numeric-ids.feather",
      "type": "int64",
      "family": "numeric",
      "sample": [
        0,
        0,
        0
      ]
    }
  ],
  "mapping_provided": false
}
```
