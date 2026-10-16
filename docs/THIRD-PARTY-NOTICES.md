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
| UK-DALE (Imperial College) | 学术研究使用，再分发受限 | 同上；引用 Kelly & Knottenbelt, Scientific Data 2015 |
| REFIT (Univ. of Strathclyde) | CC-BY-NC-SA 4.0 | 同上；引用 Makonin et al. |
| Low Carbon London (UK Power Networks) | UK OGL v3 | 同上 |
| ECO (ETH Zürich vs.inf) | 学术研究使用 | 同上；引用 Beckel et al., BuildSys 2014 |
| IDEAL (Univ. of Edinburgh, DataShare DOI 10.7488/ds/2836) | CC-BY-NC 4.0，需注册下载 | 同上；引用 Pullinger et al., Scientific Data 2021 |
| PV-Augmented NILM Dataset (HF: wangxudong/PV-Augmented-NILM-Datasets) | 学术研究使用（REDD 衍生） | 仅作为真实数据验证通道（`scripts/import_pvaug.py`），不分发；其 `aggregate_power_with_injection` 通道含光伏注入实验伪影，oed 质量扫描已将其标出 |
| 蒙西电网边界条件数据集 (AI Camp Energy 2026, ModelScope) | 赛事提供 | 原生格式接入；`git lfs pull` 后本地转换 |

## 运行时依赖

pandas (BSD-3) · pyarrow (Apache-2.0) · typer (MIT) · jsonschema (MIT)

## 引用义务

若您在研究中使用经本项目转换的 REDD 数据，请引用原始数据集：
J. Zico Kolter and Matthew J. Johnson. REDD: A public data set for energy
disaggregation research. SustKDD workshop, 2011.
