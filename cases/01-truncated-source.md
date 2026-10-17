# 案例 01：哈希匹配的文件仍然被截断

## 真实证据

对象：SD 卡 `df_2013.feather`，1,219,620,962 字节。

SHA-256：`fc38a590d5bfc6472959657155d6d4562ce4902186f685d09d547cb83eef262d`。

该值与保存的 [Hugging Face 文件清单快照](evidence/lcl-source-tree.json) 中 LFS oid 一致。来源 API：`https://huggingface.co/api/datasets/Sufiyan83/Low-Carbon-London-Smart-Meter-Cleaned-FeatureReady/tree/main?expand=false`。快照取于 2026-10-16，只代表该版本。

普通 Feather 打开报 `Not an Arrow file`，文件头为 ARROW1，文件尾不是 ARROW1。独立的 [恢复审计](evidence/recovery-2013.json) 显示，前 315 个批次可读取；后续消息体预期 3,939,672 字节，实际只剩 117,674 字节。恢复了 20,643,840 行，但不能确认其覆盖范围完整。

## 会造成什么影响

按文件大小判断下载完成，或看到哈希匹配就开始建模，都会漏掉这个问题。正常读取会失败；把恢复数据当作全年数据，则会使覆盖率、连续性和预测评估失真。

这里能够确认“与上游发布版本一致且结构损坏”，不能据此确定上游在哪一步发生了损坏。

## 工具如何处理

`source.checksum` 独立记录参考一致性，`source.structure` 读取全部 IPC 批次并验证结构。前者通过不会覆盖后者失败。报告不自动修改或修复原文件。

处理建议：隔离原文件，保留校验值；联系发布方取得完整版本。必须抢救时，将完整批次写到新文件，并保留“不保证完整”的恢复审计。

## 最小复现与验收

```bash
.venv/bin/python scripts/reproduce_trust_cases.py
.venv/bin/oed check cases/reproduced/truncated.feather -o cases/reproduced/manual-truncated
```

生成器在合成的 Feather 文件尾移除 20 字节，并使用损坏版本自身的哈希模拟“上游参考也损坏”的场景。这是机制复现，不是 2013 年原文件的复制。

验收：生成报告中哈希匹配为 `pass`，结构为 `fail`，整体为 `fail`；检查前后输入哈希不变。CLI 返回 2 是预期结果。
