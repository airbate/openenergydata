# 30 分钟上手 OpenEnergyData

## 0. 你将得到什么

全球公开能耗数据集格式各异：REDD 是无表头文本、UK-DALE 是 house/channel 目录、REFIT 是 kW 单位 CSV、LCL 是半小时 kWh……oed 把它们统一成同一套 Parquet + 清单规格，并附带质量体检与基准评测。

## 1. 安装（2 分钟）

```bash
git clone <repo> && cd openenergydata
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -q        # 29 个用例应当全绿
```

## 2. 转换第一个数据集（5 分钟）

以 REDD 为例（其他数据集把 `redd` 换成 `ukdale/refit/lcl/eco/mengxi`，目录结构见各转换器 docstring）：

```bash
oed convert redd ~/datasets/redd/low_freq out/redd
```

得到：

```
out/redd/dataset.oed.json          # Croissant 兼容清单（含 sha256 血缘）
out/redd/sites/house_1/ch01.parquet  # UTC 时间戳 + power_w + quality
```

用 pandas 直接消费：

```python
import pandas as pd
df = pd.read_parquet("out/redd/sites/house_1/ch03.parquet")
print(df.describe())        # 电器类型、单位等看 dataset.oed.json
```

## 3. 质量体检（5 分钟）

```bash
oed scan out/redd --annotate          # 确定性扫描：缺口/负值/越界/零段/单位/抖动
cat out/redd/quality-report.md        # 中文报告，每条发现带时间范围与解释
```

`--annotate` 会把质量标记按位写回 parquet 的 `quality` 列（词汇表见 `src/oed/quality_flags.py`）。

## 4. 领域规则：生成 → 人工确认 → 执行（10 分钟）

```bash
oed rule generate out/redd            # 启发式常识库生成候选（全部未确认）
oed rule confirm out/redd bounds-electric-oven --by 你的名字   # 人工审核
oed rule run out/redd                 # 执行已确认规则
```

想用大模型生成规则（任意 OpenAI 兼容端点，含本地 vLLM/Ollama）：

```bash
export OED_LLM_BASE_URL=https://api.deepseek.com/v1
export OED_LLM_API_KEY=sk-...
oed rule generate out/redd --ai
```

所有规则——无论启发式还是 LLM 生成——都默认 `confirmed: false`，**必须人工确认才参与执行**，审核人署名随发现一起落盘，形成可审计的人机协同链路。

## 5. 报告卡与基准（8 分钟）

```bash
oed report out/redd     # 自包含 HTML 质量报告卡（浏览器直接打开）
oed bench out/redd      # 负荷预测基线 + NILM 框架 → benchmark.md 排行榜
```

预测基线：`naive` / `daily_profile` / `seasonal_lag_24h`（时间顺序 80/20 切分）；NILM 框架当前含 `daily_profile` 持久性基线与 MAE/SAE 指标，是学习型算法需要超越的参照点。

## 6. 接入你自己的数据

蒙西电网数据集（`mengxi`）展示了非 NILM 类时序的接入方式：声明单位（MW）、时区（Asia/Shanghai）、通道语义（system_load 为 site_meter）。照着 `src/oed/converters/mengxi.py` 写 100 行以内即可接入你的域。详见 `CONTRIBUTING.md`。

## 常见问题

- **真实数据从哪下？** 各数据集官方地址见 `docs/THIRD-PARTY-NOTICES.md`；国内网络建议 OpenDataLab 等镜像。
- **和 NILMTK 什么关系？** 互补：oed 交付规格标准 + AI 质量评注 + 基准；转换器语义参考了 nilmtk（Apache-2.0），并在元数据中致谢。
