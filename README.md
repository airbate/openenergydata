# OpenEnergyData 能源数据基座

> 双碳时代的开源能耗时序数据基座：统一规格 × 转换器集 × LLM 智能评注 × 基准评测
> 第四届开放原子大赛·2026 开源行业解决方案创新赛·赛道一参赛作品

**`oed convert` 一条命令接入全球公开能耗数据集 → `oed scan` 质量扫描 → `oed rule --ai` LLM 生成领域质量规则 → `oed report` 质量报告卡 → `oed bench` 基准排行榜**

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

## 快速开始

```bash
pip install -e ".[dev]"
pytest -q                              # 7 个用例全绿
oed convert redd <redd低频根目录> out/  # 转换为统一格式
oed scan out/ --annotate               # 质量扫描 + 标记写回
cat out/quality-report.md              # 人话质量报告
```

## 时间线

- 2026-10-15 立项（距提交截止 16 天）
- 2026-10-31 作品提交截止
- 2026-11-13 北京亦庄线下总决赛
