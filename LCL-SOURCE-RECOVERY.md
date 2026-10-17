# 官方源恢复与 2012 年身份映射

2026-10-16。已下载并完整读取 UK Power Networks 在 London Datastore 发布的全部 168 个 CSV 分区，校验 ZIP CRC、逐 CSV SHA256 和输出 Parquet SHA256。每个 CSV 均与作者 Hugging Face 发布版本的 LFS SHA256 一致（168/168）。

## 交付结果

| 年份 | 官方原始记录 | 户号 | 分区 | 原始空读数 | 覆盖月份 |
|---|---:|---:|---:|---:|---|
| 2013 | 93,087,837 | 5,528 | 168 | 12 | 1–12 月 |
| 2012 | 60,410,060 | 5,554 | 168 | 5,548 | 1–12 月 |

- [2013 年原始 Parquet](runs/lcl-official-raw/year=2013/)：301,319,107 字节。
- [2012 年原始 Parquet](runs/lcl-official-raw/year=2012/)：181,959,109 字节；直接包含 MAC 户号，后续分析优先使用这一版。
- [源文件与输出清单](runs/lcl-official-raw/source-manifest.json)、[输出验证](runs/lcl-official-raw/output-verification.json)。
- [2012 年编码户号映射 CSV](cases/real-lcl/mapping-2012/mapping-2012.csv)、[映射证据说明](cases/real-lcl/mapping-2012/mapping-receipt.json)。

“全年完整”仅指从全部官方分区提取了所有标注为 2013 年的记录，不表示每个家庭每天都有完整读数。没有插值、去重、补零或赋予时区；四个原始字段均保留字符串，包括空读数标记和重复时间戳。文件内容与官方 CSV 对应，不是修补旧版 Feather 尾部或恢复作者全部衍生特征。

## 户号映射的证据强度

编码文件有 5,552 户。官方 2012 年原始数据有 5,554 户；其中 MAC005559、MAC005560 未出现在重建的编码映射中。

| 证据等级 | 户数 | 判定 |
|---|---:|---|
| sequence_verified | 5,524 | 至少三段连续读数匹配，搜索全部官方家庭后只有一个候选户号 |
| sequence_and_order | 16 | 一至两段独有读数匹配，并与作者 LabelEncoder 顺序一致 |
| order_reconstructed | 12 | 缺乏足够有区分度的读数；根据作者编码规则和两侧已匹配锚点唯一重建 |

这是一张 **完整但证据分级的重建映射**，不是作者提供的原始编码字典。最后 12 户没有独立读数匹配证明；其成立依赖公开代码中的 LabelEncoder 确实用于该版本。需要最高置信度时只选 `sequence_verified`。

比对直接读取 SD 卡 Feather 的原始 double 值，逆向全局 MinMax（最小值 0、最大值 9.71），以 0.000001 kWh 量化后的 16 个连续读数为片段。每段至少有六个不同读数；抽样间隔 512 行。哈希命中后逐元素复核，并在全部官方家庭中搜索候选。随后使用作者代码的排序编码规则，只填入锚点间数量完全一致的空段，拒绝有歧义的空段。它验证家庭身份，不验证整个时间序列。

## 新发现：旧版 2012 年不能作为可信时序继续使用

作者 Notebook 第 149 个单元（从 0 开始编号）对包括用电量在内的数值列执行全局 `MinMaxScaler`。因此旧文件中的用电量是无量纲归一化值；此前将其声明为 kWh、再生成 kW 基准结果的解释已撤回。

此外，匹配的同一连续读数片段出现在不同时间。例如编码户号 0 对应 MAC000002：从 `[0.284, 0.282, 0.441, 0.705, …]` 开始的一段，旧文件时间为 `2012-10-22 16:30:00`，官方原始时间为 `2012-10-22 19:30:00`。作者代码还包含将备份 DateTime 列重新赋给清洗表的操作，这提供了排查线索，但不能据此断言全部错位都由同一操作造成。

[完整时间对齐审计](runs/evidence/lcl-alignment-2012/alignment-summary.json)使用恢复后的映射，对官方和此前导入数据按同一时钟标签连接、按导入器规则保留首个重复时间戳。59,893,917 个可比较非空值中，59,108,685 个在归一化后仍不相符（绝对容差 5e-8）。这个结果涉及已去重的 float32 导入数据，不等于对原始 Feather 每一行的无损审计；也不证明官方时钟的时区。它足以说明不能仅改户号、乘回 9.71 就恢复可靠时序。

已执行的纠正：

- 旧 2012 清单改为 `physical_quantity=normalized`、`unit=1`；物理功率扫描和预测基准拒绝此类通道。
- 旧质量报告和预测报告原路径改为撤回说明；原报告和修改前清单保存在 `runs/evidence/lcl-2012-correction/` 供复核。
- Feather 导入命令必须显式指定 `--value-unit kWh` 或 `--value-unit normalized`，避免继续默认解释归一化值。
- 新官方原始数据单独存放，未改写 SD 卡文件、旧读数或旧时间戳。后续训练和跨年连接应从官方源重新建立清洗流程。

## 复现

在项目目录执行（完整源 ZIP 与原始数据保存在本机 runs 下，不包含在轻量代码压缩包中）：

```bash
.venv/bin/python scripts/rebuild_lcl_official.py runs/lcl-official-source.zip runs/lcl-official-raw
.venv/bin/python scripts/recover_lcl_identity.py /Volumes/Ventoy/data_lcl/df_2012.feather runs/lcl-official-raw runs/evidence/lcl-identity-2012
.venv/bin/python scripts/complete_lcl_mapping.py runs/lcl-official-raw runs/evidence/lcl-identity-2012 cases/real-lcl/mapping-2012
.venv/bin/python scripts/audit_lcl_alignment.py runs/lcl-official-raw runs/lcl-2012-encoded cases/real-lcl/mapping-2012/mapping-2012.csv runs/evidence/lcl-alignment-2012
.venv/bin/pytest -q
```

检查结果：69 项测试通过；336 个输出 Parquet 的行数和哈希全部与生成清单一致。读取大数据时请逐分区或批次处理，避免一次物化全部 9,308 万行。

## 来源与版本

- [UK Power Networks / London Datastore 官方发布页](https://data.london.gov.uk/dataset/smartmeter-energy-consumption-data-in-london-households-vqm0d)。半小时电量字段单位为 kWh；使用或再分发时保留发布方署名与官方页许可信息。
- [官方 ZIP](https://data.london.gov.uk/download/vqm0d/04feba67-f1a3-4563-98d0-f3071e3d56d1/Partitioned%20LCL%20Data.zip)，795,722,689 字节，SHA256：`149a6a9c43c622fd0a14b7d11be055665317d3018d9fb7e1043bd51420bfaea5`。
- [作者固定版本 Notebook](https://github.com/sufirehman/ElectricityConsumptionPredictionUsingDeepLearning/blob/9192b8874f5bdf1eed3c99a6deba3896bd2ae090/ECP.ipynb)，[本地关键代码与哈希](cases/real-lcl/author-code-evidence.json)。
- [作者 Hugging Face 数据版本](https://huggingface.co/datasets/Sufiyan83/Low-Carbon-London-Smart-Meter-Cleaned-FeatureReady/tree/30de733a9bc81c1a11d2f514ae054c6c0d1ab02a)，与官方 168 个 CSV 全部哈希一致。
- 本次编码 Feather SHA256：`963471299039408ed6742e96cf9d64f3cd1b114bf3dc448b56f8f52f6dcc2ce5`。映射只对这一文件版本有证据支持。
