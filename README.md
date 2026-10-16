# OpenEnergyData 能源数据基座

> 双碳时代的开源能耗时序数据基座：统一规格 × 转换器集 × LLM 智能评注 × 基准评测
> 第四届开放原子大赛·2026 开源行业解决方案创新赛·赛道一参赛作品

**`oed convert` 一条命令接入全球公开能耗数据集 → `oed scan` 质量扫描 → `oed rule --ai` LLM 生成领域质量规则 → `oed report` 质量报告卡 → `oed bench` 基准排行榜**

## 战绩（全部真实可复现）

| 指标 | 数值 |
|---|---|
| 接入公开数据源 | **7** 个（REDD / UK-DALE / REFIT / ECO / IDEAL / LCL / 蒙西电网） |
| 统一格式化真实读数 | REDD 衍生真实数据已接入（9 通道，含 105 处质量发现）；**LCL 5,567 户全量导入就绪待运行**（内存安全脚本 + 一步手册见 [RUN-ON-MAC.md](RUN-ON-MAC.md)） |
| 已发表数据集的真实质量问题 | **105** 处（REDD 衍生集白天总表置零伪影，逐条带时间戳证据） |
| 测试与 CI | 33 用例 + GitHub Actions 双版本 Python 全绿 |
| 使用成本 | 0 元硬件，`pip install -e .` 即用 |

- 参赛方案：`docs/参赛方案-v1.md`
- 方向 idea 池：`docs/方向idea池.md`

## 仓库结构

```
src/oed/
  schema/         # oed-manifest-v1: Croissant 兼容清单 + x-oed 领域扩展
  converters/     # 源数据集转换器（当前: REDD）
  quality/        # 确定性质量扫描引擎（缺口/越界/零段/单位/抖动）
  quality_flags.py / io.py / cli.py
tests/            # 格式精确的 REDD 夹具 + 转换器/扫描器测试（7 用例）
scripts/          # 真实数据集下载脚本
docs/             # 参赛方案、方向 idea 池、第三方声明
```

## 支持的数据源（转换器状态）

| 数据集 | 类型 | 转换器状态 |
|---|---|---|
| REDD | 户内 NILM，1-3s | ✅ 原始格式夹具验证；**真实数据管线已验证**（PV-Augmented 衍生版，见 `scripts/import_pvaug.py`，扫描器在其中发现了已发表数据集的白天置零伪影） |
| UK-DALE | 户内 NILM，1-6s | ✅ 夹具验证（.dat 家族） |
| REFIT | 户内 8s，kW→W | ✅ 夹具验证 |
| LCL | 半小时 kWh 智能电表 | ✅ 夹具验证 |
| ECO | 瑞士三相 1s | ⚠️ 按官方文档实现，待真实数据验证 |
| IDEAL | 英国 255 户，1s 视在功率 | ⚠️ 按论文格式实现（无表头 UTC 两列 + 元数据清单），夹具验证 |
| 蒙西电网（自有） | 电网级 MW 时序 | ✅ 原生格式（Git LFS 拉取后接入） |

## 快速开始

```bash
pip install -e ".[dev]"
pytest -q                              # 29 个用例全绿
oed convert redd <redd低频根目录> out/  # 转换为统一格式
oed scan out/ --annotate               # 质量扫描 + 标记写回
oed rule generate out/                 # 生成候选规则（--ai 走大模型）
oed rule confirm out/ <规则id> --by 你  # 人工确认（人机协同留痕）
oed rule run out/                      # 执行已确认规则
oed report out/                        # 自包含 HTML 质量报告卡
oed bench out/                         # 负荷预测/NILM 基准排行榜
```

完整教程见 `docs/tutorial.md`（30 分钟上手）。

## 时间线

- 2026-10-15 立项（距提交截止 16 天）
- 2026-10-31 作品提交截止
- 2026-11-13 北京亦庄线下总决赛
