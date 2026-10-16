# ⚡ RUN-ON-MAC：在 Mac 上跑完 LCL 全量接入

> 本文件是唯一需要看的操作手册。按顺序执行，⚡ 标记 = 需要你跑的命令。
> 预计总耗时：环境 5 分钟 + 下载 15-40 分钟 + 全量导入/体检 20-40 分钟（视 Mac 内存与网络）。

## 0. 这是什么

项目其余部分（7 个转换器、质量引擎、基准、33 个测试）已在 Linux 上完成并推送 GitHub；
**唯一没跑完的是 LCL 5567 户全量的"导入→体检→基准"**——因为这台 Linux 机只有 7.6GB 内存，
读 2.9GB 的 feather 会 OOM。你的 Mac（建议 ≥16GB 内存）正好补上这最后一环。

LCL 数据源 = Low Carbon London（5567 户 × 2011-2014 × 半小时 kWh，全球最大公开智能电表
数据集之一）。清洗版 Feather 来自 HuggingFace `Sufiyan83/Low-Carbon-London-Smart-Meter-Cleaned-FeatureReady`。

## 1. ⚡ 环境（一次性）

```bash
cd openenergydata            # 解压本包，或 git clone https://github.com/airbate/openenergydata
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -q                    # 预期: 33 passed（验证环境 OK）
```
要求 Python ≥ 3.11。已验证的组合: pandas 3.0.6 + pyarrow 26（Mac 上新版同主版本即可）。

## 2. ⚡ 下载数据（四个年份的 feather，共约 4.8GB）

包内 `data_seed/df_2011.feather`（18MB）已附带，可先跳过 2011。
其余三个文件（Mac 若能直连 HuggingFace 就把 `hf-mirror.com` 换成 `huggingface.co`）：

```bash
mkdir -p ~/datasets/lcl && cd ~/datasets/lcl
BASE="https://hf-mirror.com/datasets/Sufiyan83/Low-Carbon-London-Smart-Meter-Cleaned-FeatureReady/resolve/main"
for y in 2012 2013 2014; do
  curl -L --retry 5 -C - -o df_${y}.feather "$BASE/df_${y}.feather"
done
# 期望大小: 2012≈2.76GB, 2013≈1.16GB, 2014≈0.69GB（-C - 支持断点续传，断了重跑同一命令即可）
```
⚠️ 断点验证：`ls -la` 对照期望大小，小了就重跑同一条 curl（会续传）。

## 3. ⚡ 全量导入（本包的核心待跑项）

```bash
cd openenergydata && source .venv/bin/activate
python scripts/import_lcl_feather.py \
  ~/datasets/lcl/df_2011.feather ~/datasets/lcl/df_2012.feather \
  ~/datasets/lcl/df_2013.feather ~/datasets/lcl/df_2014.feather \
  -o ~/datasets/lcl/unified --work ~/datasets/lcl/shards
```
- 实现是**内存安全**的：pyarrow 内存映射 + 200 万行切片 + 按户分片两段式；
  16GB 内存的 Mac 稳够，8GB 也大概率可行（切片在脚本顶部 `SLICE_ROWS` 可调小）。
- 预期产出：`~/datasets/lcl/unified/` 下 5567 个 `sites/macXXXXXX/energy.parquet`
  + 一份 Croissant 兼容清单 `dataset.oed.json`。
- 预期耗时：10-30 分钟（磁盘速度决定）。

## 4. ⚡ 质量体检 + 基准 + 报告卡

```bash
oed scan  ~/datasets/lcl/unified --annotate   # 全量体检（几千通道，几分钟）
oed report ~/datasets/lcl/unified             # HTML 质量报告卡
oed bench  ~/datasets/lcl/unified             # 负荷预测基线（时间较久，见下）
```
- `bench` 会对每一户跑 3 个基线，5567 户约需 30-60 分钟。想先快速看效果可抽样：
  ```bash
  # 抽样 200 户建个子目录再 bench（可选）
  ```
- 预期看点：真实城市级数据的缺口/异常分布；daily_profile 基线对 naive 的 MAE 优势。

## 5. ⚡ 收尾（跑完后把结果写回项目）

1. 把真实数字填进 README「战绩」表（当前该表 LCL 行标注的是"待 Mac 运行"状态）；
2. `docs/sample-lcl-report.html`（scan 生成的报告卡）放进 docs/ 并 git 提交；
3. 有意思的质量发现（LCL 一定有断表/搬家/置零）记录进 `docs/`。

## 附：文件地图（哪里有逻辑哪里跑）

| 文件 | 作用 | 是否需要跑 |
|---|---|---|
| `scripts/import_lcl_feather.py` | **LCL feather → oed 统一格式（内存安全两段式）** | ⚡ 第 3 步 |
| `src/oed/cli.py`（oed 命令） | convert / scan / rule / report / bench | ⚡ 第 4 步 |
| `src/oed/quality/scanner.py` | 确定性质量扫描（缺口/越界/置零/单位/抖动） | 被 oed scan 调用 |
| `src/oed/benchmark.py` | 预测基线 + NILM 框架 | 被 oed bench 调用 |
| `src/oed/rules/` | 启发式 + LLM 规则生成与确认流 | 可选（`oed rule generate --ai` 需配 `OED_LLM_*` 环境变量） |
| `scripts/import_pvaug.py` | REDD 衍生真实数据通道（已在 Linux 验证过，无需重跑） | 否 |
| `docs/宣传文案.md` | 可直接发布的宣传稿（数字以你跑完的实测为准） | 否 |
