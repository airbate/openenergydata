# 第三方声明（THIRD-PARTY NOTICES）

本项目（OpenEnergyData）采用 Apache License 2.0。以下列出项目参考、依赖或涉及的上游资源及其许可：

## 参考实现与设计借鉴

| 资源 | 许可证 | 使用方式 |
|---|---|---|
| [nilmtk](https://github.com/nilmtk/nilmtk) 及 [nilm_metadata](https://github.com/nilmtk/nilm_metadata) | Apache-2.0 | 元数据分层（building/meter/appliance）与 REDD 转换语义参考；本项目为独立实现，未复用其源码 |
| [Croissant](https://github.com/mlcommons/croissant)（MLCommons） | Apache-2.0 | 数据集清单顶层结构兼容（`@context`/`distribution`/`recordSet`） |

## 支持的源数据集

| 数据集 | 许可/使用条款 | 本项目分发策略 |
|---|---|---|
| REDD (MIT CSAIL) | 供学术研究免费使用（[项目页](http://redd.csail.mit.edu)） | **不分发原始数据**，仅提供转换器；统一后数据的再分发遵循源许可 |

后续接入的数据集（UK-DALE、REFIT、ECO、IDEAL、LCL）在接入时逐项补充本表。

## 运行时依赖

pandas (BSD-3) · pyarrow (Apache-2.0) · typer (MIT) · jsonschema (MIT)

## 引用义务

若您在研究中使用经本项目转换的 REDD 数据，请引用原始数据集：
J. Zico Kolter and Matthew J. Johnson. REDD: A public data set for energy
disaggregation research. SustKDD workshop, 2011.
