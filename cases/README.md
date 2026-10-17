> 最新进展：[官方全年数据恢复、分级户号映射与旧 2012 报告撤回](../LCL-SOURCE-RECOVERY.md)。本目录原案例保留最初发现时的证据。

# 可信能源数据检查：三个可复现案例

本工具在建模前检查可验证的前提，提供证据、影响和处理建议。它不会给出“数据已可信”的笼统认证，也不把未知项当作通过。

**三个真实问题，四份最小演示报告**：第三个案例分别保存修复前与修复后报告。演示数据均为合成小样本；真实证据与演示结果分开保存。

| 案例 | 已验证的事实 | 检查边界 |
|---|---|---|
| [01 文件截断](01-truncated-source.md) | 2013 文件与参考哈希一致，仍无法作为 Feather 文件打开 | 哈希一致不保证发布方文件完整 |
| [02 户号映射缺失](02-household-identity.md) | 2012 户号是整数，其他可读年份使用 MAC 字符串 | 表示不同不证明一定不同户；没有映射就不能直接关联 |
| [03 单位混用](03-unit-consistency.md) | 原代码存在能量/功率比较错误；10,781 个通道的清单字段单位描述冲突 | 声明一致不保证原始传感器单位或时间区间声明真实 |

## 一条命令复现

在项目根目录、依赖已安装的情况下：

```bash
.venv/bin/python scripts/reproduce_trust_cases.py
```

无需下载数据或插入 SD 卡。输出位于 `cases/reproduced/`。程序断言前两个案例和单位修复前为 `fail`，单位修复后为 `review_required`，而不是“已认证”。

- [文件截断演示报告](reproduced/01-truncated/check-report.html)
- [户号关联演示报告](reproduced/02-identities/check-report.html)
- [单位修复前](reproduced/03-units-before/check-report.html) / [单位修复后](reproduced/03-units-after/check-report.html)

## 检查自己的数据

```bash
.venv/bin/oed check file1.feather file2.feather --checksums reference-sha256.json -o checks/sources
.venv/bin/oed check --dataset runs/lcl-original-ids-partial -o checks/dataset
```

`--checksums` 接受 JSON 文件名到 SHA-256 的映射。参考哈希的来源需要使用者确认；工具不会将随意输入的哈希当作权威来源。文件名重复时请分别检查并提供对应参考。

当前支持 Feather V2 / Arrow IPC 文件、LCLid 户号字段，以及本项目 OED 清单里的能源/功率单位；其他格式不在这一版覆盖范围。

每次生成 JSON、Markdown、HTML 三种报告。输入只读，报告写入 `-o` 目录。

- `fail`：存在证据支持的阻断项；退出码 2。户号阻断针对跨文件身份关联，不代表单年数据全部不可使用。
- `review_required`：没有发现阻断项，但有未知事项待核实；退出码 0，自动流程必须再检查 JSON 状态。
- `pass`：只表示请求范围内的检查通过；不是通用的数据质量保证。

## 真实运行证据

`real-checks/` 保留真实文件检查和两个大规模数据集单位修复前后的报告；`evidence/` 保存参考清单和历史恢复审计。报告包含运行机器的路径，便于追溯，但不包含原始大数据文件。

真实文件检查已读取所有可解码批次；缺少文件尾的 2013 文件在打开阶段失败。恢复的 20,643,840 条记录来自此前独立执行的恢复工具，不能把它们当成本次标准文件检查通过的结果。

## 未解决事项

1. 上游完整 2013 文件和 2012 户号映射仍未取得。
2. 原始单位、时区和观测覆盖范围仍需来源规范核对。
3. 预测基准协议和旧质量评分仍不适合直接用于正式模型优劣结论。

本轮的成功标准是正确暴露这些限制，而不是消除报告中的所有未知项。

## 从声明检查推进到实际内容检查

现在还会检查统一格式数据文件的哈希、必要列、UTC 时间顺序和非有限数值。详见 [内容检查记录](../CONTENT-VALIDATION.md)。使用 `scripts/reproduce_content_checks.py` 可演示“文件可读、哈希匹配，但内容仍有问题”的情形。
