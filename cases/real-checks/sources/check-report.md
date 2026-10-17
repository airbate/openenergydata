# 能源数据可信性检查

状态：fail

Feather V2 文件可解码性、参考哈希比对、LCL 户号表示与清单单位一致性；不认证完整性或适合建模。

## source.checksum · pass

对象：data_seed/df_2011.feather

影响：哈希匹配仅证明与提供的参考版本一致，不证明上游文件完整或内容正确。

建议：缺少参考哈希时向发布方获取；不匹配时隔离并核对版本。

```json
{
  "sha256": "4ccfb7f043d69c2e1df2cdfaea1bf784c0d14298accd8ef64035ca2d7df25c3b",
  "expected_sha256": "4ccfb7f043d69c2e1df2cdfaea1bf784c0d14298accd8ef64035ca2d7df25c3b",
  "bytes": 19581186
}
```

## source.structure · pass

对象：data_seed/df_2011.feather

影响：全部 IPC 批次可解码；尚不证明所有预期时间和家庭都在文件中。

建议：继续检查发布方覆盖范围及身份映射。

```json
{
  "decoded_rows": 399737,
  "decoded_batches": 7
}
```

## source.checksum · pass

对象：/Volumes/Ventoy/data_lcl/df_2012.feather

影响：哈希匹配仅证明与提供的参考版本一致，不证明上游文件完整或内容正确。

建议：缺少参考哈希时向发布方获取；不匹配时隔离并核对版本。

```json
{
  "sha256": "963471299039408ed6742e96cf9d64f3cd1b114bf3dc448b56f8f52f6dcc2ce5",
  "expected_sha256": "963471299039408ed6742e96cf9d64f3cd1b114bf3dc448b56f8f52f6dcc2ce5",
  "bytes": 2889925738
}
```

## source.structure · pass

对象：/Volumes/Ventoy/data_lcl/df_2012.feather

影响：全部 IPC 批次可解码；尚不证明所有预期时间和家庭都在文件中。

建议：继续检查发布方覆盖范围及身份映射。

```json
{
  "decoded_rows": 60393414,
  "decoded_batches": 922
}
```

## source.checksum · pass

对象：/Volumes/Ventoy/data_lcl/df_2013.feather

影响：哈希匹配仅证明与提供的参考版本一致，不证明上游文件完整或内容正确。

建议：缺少参考哈希时向发布方获取；不匹配时隔离并核对版本。

```json
{
  "sha256": "fc38a590d5bfc6472959657155d6d4562ce4902186f685d09d547cb83eef262d",
  "expected_sha256": "fc38a590d5bfc6472959657155d6d4562ce4902186f685d09d547cb83eef262d",
  "bytes": 1219620962
}
```

## source.structure · fail

对象：/Volumes/Ventoy/data_lcl/df_2013.feather

影响：文件不能作为完整 Feather 数据输入；可能存在截断或格式损坏。

建议：保留原文件，核对参考哈希；如恢复完整批次，单独标记为部分恢复，不能补造缺失记录。

```json
{
  "error": "Not an Arrow file",
  "decoded_rows": 0,
  "decoded_batches": 0
}
```

## source.checksum · pass

对象：/Volumes/Ventoy/data_lcl/df_2014.feather

影响：哈希匹配仅证明与提供的参考版本一致，不证明上游文件完整或内容正确。

建议：缺少参考哈希时向发布方获取；不匹配时隔离并核对版本。

```json
{
  "sha256": "a60a8203ee5d6dca57c04d66b94bcd1d8be5fddb32e21de830f061ca5bcca08d",
  "expected_sha256": "a60a8203ee5d6dca57c04d66b94bcd1d8be5fddb32e21de830f061ca5bcca08d",
  "bytes": 688550394
}
```

## source.structure · pass

对象：/Volumes/Ventoy/data_lcl/df_2014.feather

影响：全部 IPC 批次可解码；尚不证明所有预期时间和家庭都在文件中。

建议：继续检查发布方覆盖范围及身份映射。

```json
{
  "decoded_rows": 14034834,
  "decoded_batches": 215
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
      "file": "data_seed/df_2011.feather",
      "type": "string",
      "family": "text",
      "sample": [
        "MAC000016",
        "MAC000016",
        "MAC000016",
        "MAC000016",
        "MAC000016"
      ]
    },
    {
      "file": "/Volumes/Ventoy/data_lcl/df_2012.feather",
      "type": "int64",
      "family": "numeric",
      "sample": [
        0,
        0,
        0,
        0,
        0
      ]
    },
    {
      "file": "/Volumes/Ventoy/data_lcl/df_2014.feather",
      "type": "string",
      "family": "text",
      "sample": [
        "MAC000002",
        "MAC000002",
        "MAC000002",
        "MAC000002",
        "MAC000002"
      ]
    }
  ],
  "mapping_provided": false
}
```
