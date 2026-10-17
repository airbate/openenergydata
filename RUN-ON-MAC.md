> 最新数据与 2012 年归一化更正见 [来源恢复报告](LCL-SOURCE-RECOVERY.md)。下面的旧清洗文件仅供复核。

# 在 Mac 上运行 OpenEnergyData

本版本已在 Python 3.13 / pandas 3.0.6 / pyarrow 26.0.0 验证，40 项测试通过。实际运行结果见 `MAC-FULL-RESULTS.md`。

## 环境

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/pytest -q
```

需要 Python 3.11 或更新版本。`requirements-mac-tested.txt` 保存了本机验证时的依赖版本。

## 快速演示

```bash
./run-mac.command
```

导入包内 2011 年数据，生成质量报告和预测基准，并打开 HTML 报告。

## 处理 SD 卡全部可读取数据

```bash
./scripts/run_full_mac.sh /Volumes/Ventoy/data_lcl
```

脚本读取 SD 卡，输出写入本项目 `runs/`，不修改原始输入。

必须保留的限制：

- 2013 年上游 Feather 文件被截断。本机文件 SHA-256 与数据源 LFS 哈希一致，重新下载相同版本无法补全。恢复工具仅保留完整 IPC 批次，并输出 JSON 审计；恢复结果始终标记为不保证完整。
- 2012 年户号是整数编码，其他年份是原始 MAC 户号。缺少编码映射时，不得自行推测对应关系。脚本将其独立导入为 `encoded2012_` 命名空间。
- `runs/lcl-original-ids-partial` 包含 2011、2013 部分恢复数据、2014；`runs/lcl-2012-encoded` 包含独立的 2012 数据。两组户数不能相加作为独立家庭总数。
- 导入按 record batch 读取三列，临时分片按户保存，转换完成后自动清理。`--work` 指定的父目录及既有文件不会被删除。
- 重跑会重新生成目标目录中的结果；如需保留某次结果，请使用不同的 `-o` 路径。

## 独立使用导入与恢复工具

```bash
.venv/bin/python scripts/recover_truncated_feather.py input.feather new-recovered.feather
.venv/bin/python scripts/import_lcl_feather.py input.feather -o runs/custom --work runs/temp --value-unit kWh
```

整数编码户号需额外传入 `--encoded-id-prefix`。`--limit N` 在全部输入文件间使用同一户号集合。

## 结果与解释

- `import-audit.json`：输入有效行、输出行、去重数及户号数。
- `source-audit.json`：逐文件读取、有效、选中行数。
- `quality-report.{json,md,html}`：质量规则发现及内部评分。
- `benchmark.{json,md}`：探索性预测基准，能源通道换算后单位为 kW。

质量分数按每通道发现数量扣分，受时长和缺失覆盖范围影响，不应直接跨不同覆盖范围比较。零值段是待解释的现象，不能据此认定电表故障。

当前预测基准还混用了固定训练末值与可使用测试期过去观测的季节滞后策略，正式比较模型前需要统一滚动预测协议；现有结果仅作为流程与基线诊断。
