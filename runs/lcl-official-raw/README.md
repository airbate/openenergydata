# 官方 LCL 原始记录

2013：93,087,837 行；2012：60,410,060 行。全部 168 个官方 CSV 分区均已读取并校验。来源、户号映射和旧版问题见 ../../LCL-SOURCE-RECOVERY.md。

字段保持官方字符串形式：LCLid、stdorToU、DateTime、KWH/hh (per half hour) （末尾有空格）。保留 Null、重复与未声明时区的时间字符串；没有推断 UTC。每个年份 168 个 Parquet，按原 CSV 分区编号。

逐批读取示例（在项目目录）：

```python
import pyarrow.dataset as ds
source = ds.dataset("runs/lcl-official-raw/year=2013", format="parquet")
for batch in source.to_batches(batch_size=65536):
    frame = batch.to_pandas()
    # 在此处理；不要把所有批次累积到内存。
```
