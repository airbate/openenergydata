# 贡献指南

感谢为 OpenEnergyData 贡献！我们欢迎：新数据集转换器、质量规则、基准算法、文档纠错。

## 贡献一个新数据集转换器（最需要的贡献）

1. **建文件**：`src/oed/converters/<dataset_id>.py`，实现 `convert(input_dir, output_dir) -> Path`，返回清单路径。
2. **推荐路径**：继承 `.dat` 家族（`dat_family.DatFamilyConverter`，适合 house/channel 文本格式）或使用 `common.DatasetBuilder`（CSV 类数据集）。
3. **必须遵守的规格**：
   - 输出 `sites/<site_id>/<channel>.parquet`，列为 `timestamp`（UTC）、`power_w`（float）、`quality`（int32，初始 0）
   - 单位统一换算到 W（电网级数据可声明 MW/kWh，须在通道 `unit` 显式声明）
   - 时区必须显式处理（`tz_localize(源时区).tz_convert("UTC")`），禁止裸 UTC 假设
   - 清单通过 `oed.io.validate_manifest` 校验（Croissant 兼容 + x-oed 扩展）
   - 源数据集许可与引用写入 `citation`/`source_license`，并登记到 `docs/THIRD-PARTY-NOTICES.md`
4. **测试**：在 `tests/` 添加格式精确的夹具（<1MB）+ 转换语义断言（参考 `test_converters_all.py`）。
5. **登记**：`src/oed/converters/__init__.py` 注册实例；README 状态表更新一行。

## 贡献质量规则

编辑社区规则 YAML（`confirmed: true` 需注明 `reviewed_by`），规则格式见 `src/oed/rules/dsl.py` 的 docstring。家电功率常识库（`APPLIANCE_BOUNDS_W`）欢迎增补并给出出处。

## 贡献基准算法

在 `src/oed/benchmark.py` 的 baseline 注册处新增，保持统一切分与指标口径，附测试。

## 流程

fork → 分支 → `pytest -q` 全绿 → PR（描述动机与测试证据）。Apache-2.0，贡献即同意以该协议授权。
