# 同类深度调研：F-UJI 与 DataSeer

> 调研日期：2026-10-17。对象：科研数据检查领域两个最近的同类——一个学术基础设施，一家商业公司。
> 目的：拆解两者的组织形态、资金链、产品边界，提炼对 oed 的可复用模式。

---

## 一、F-UJI：公共资助链上的学术基础设施

### 基本盘
| 项 | 内容 |
|---|---|
| 开发者 | Anusuriya Devaraju & Robert Huber（PANGAEA/GFZ 与不来梅大学生态） |
| 起源 | EU Horizon 2020 **FAIRsFAIR** 项目（已 2022 年结题） |
| 维护 | 后续项目 **FAIR-IMPACT**（Horizon，grant 101057344，2022-06 启动，支持约 50 家机构）延续开发，现由 **PANGAEA** 组织维护 |
| 覆盖 | 17 项 FAIR 核心评估指标中的 16 项；后增地球环境科学专属指标 + 学科无关指标；在 5 个认证仓储试点 |
| 影响力 | 论文被引 61+；进入 FAIR-IMPACT 资源目录、EOSC 生态；REST API 服务 |

### 资金链与组织形态
**欧盟科研资助链**：FAIRsFAIR（H2020）→ FAIR-IMPACT（Horizon Europe）→ 关联 OSCARS 项目。没有商业公司、没有订阅收入——**纯公共资助的学术基础设施**，靠项目链条续命，影响力来自 EOSC（欧洲开放科学云）政策网络的嵌入。

### 产品边界（确认）
只评估**元数据层 FAIR 合规**：DOI、license、标准格式、仓储可信度。不触碰数据内容——单位声明、时间对齐、身份一致性均不在 16 项指标内。

## 二、DataSeer：资助孵化 → 机构订阅的商业公司

### 基本盘
| 项 | 内容 |
|---|---|
| 创始人/CEO | **Tim Vines**（温哥华）：学术出版圈知名人物——Molecular Ecology 期刊创始执行主编、数据仓库 **Flow** 创始人；同时创立了另一家研究诚信公司 **Clear Skies** |
| 资金起源 | **Sloan Foundation 资助**——用资助金开发"使研究数据实践对齐数据共享政策"的工具集，之后商业化 |
| 客户 | 机构、出版商、资助者（批量上传研究文本） |

### 产品线
1. **SnapShot**：秒级扫描手稿，识别开放科学实践指标与错失机会；
2. **Compliance Checks**：AI 分析手稿，按机构的具体政策（资助方/出版商的数据共享政策）生成合规报告；
3. **Open Science Metrics**：出版组合层面的开放科学采用统计。

### 关键商业案例
- **IOP Publishing**（2024-02）：学协会物理出版商，试点期刊组合范围的开放科学指标 + 开放数据实践；
- **Taylor & Francis**（2024-10）：数据共享合规检查案例研究，发表于 *International Journal of Digital Curation*——用学术论文为商业产品背书，是这个领域的标准打法。

### 商业模式
**B2B 订阅/服务**：向出版商（投稿门禁）、资助者（合规验证）、大学（诚信审查）收费。创始人的学术出版圈声望（期刊创办人+数据仓库创办人）是获客的核心资产。

## 三、两个模式的对比

| 维度 | F-UJI | DataSeer |
|---|---|---|
| 组织形态 | 学术基础设施（项目链续命） | 初创公司（资助孵化→B2B 订阅） |
| 资金 | EU Horizon 项目链 | Sloan Foundation 资助 → 出版商/机构订阅 |
| 检查对象 | 元数据 FAIR 合规 | 手稿与政策合规（数据共享声明） |
| 检查对象**不**含 | 数据内容可信 | 数据内容可信 |
| 获客资产 | EOSC 政策网络嵌入 | 创始人学术出版圈声望 + 顶刊案例背书 |
| 可持续性 | 依赖资助链延续 | 订阅续费 |

## 四、对 oed 的四条可复用启示

1. **"内容可信"仍是无人区（双重确认）**：F-UJI 止步元数据，DataSeer 止步政策合规——两家都验证了"检查类产品在科研领域有生存空间"，也都没碰"数据本身可不可信"。oed 的 LCL 模式（声明 vs 实测尽调）依然没有同类。
2. **DataSeer 是最近的模板**：路径 = 资助孵化（Sloan/开放原子/基金委均可类比）→ 机构订阅（出版商/大学/资助者）；冷启动资产 = 创始人领域公信力。oed 的对应物：LCL 调查 + 官方源恢复——这已经是我们手里最大的公信力资产，应当置顶于一切对外材料。
3. **用学术论文给商业背书**：DataSeer 把 T&F 合规案例发表在 *IJDC*（数字策展期刊）——oed 的 LCL 调查同样可以写成论文/技术报告投 D&B 类会议或数据期刊，一举两得（学术背书 + 获客）。
4. **与 F-UJI 的关系是互补而非竞争**：F-UJI 查元数据、DataSeer 查政策合规、oed 查内容可信——三层检查可以组合销售（"FAIR 合规 + 政策合规 + 内容可信"全套尽调），甚至可以申请与 FAIR-IMPACT 生态对接。

## 五、来源

- [F-UJI 官网](https://www.f-uji.net) / [GitHub（PANGAEA）](https://github.com/pangaea-data-publisher/fuji) / [FAIR-IMPACT 目录](https://catalogue.fair-impact.eu/resources/f-uji)
- [FAIRsFAIR 项目页](https://www.fairsfair.eu/f-uji-automated-fair-data-assessment-tool) / [FAIR-IMPACT（CORDIS 101057344）](https://cordis.europa.eu/project/id/101057344/reporting)
- [DataSeer 官网](https://dataseer.ai) / [关于页（Tim Vines 与 Sloan 资助）](https://dataseer.ai/about)
- [DataSeer × IOP Publishing 合作公告（2024-02）](https://dataseer.ai/2024/02/26/dataseer-ai-and-iop-publishing-collaborate-on-open-science-indicators-and-open-data-pilot)
- [CASRAI：F-UJI 指南](https://casrai.org/guides/f-uji-automated-fair-assessment-tool)

---

## 六、代码级审计（2026-10-17，克隆实地检查）

### F-UJI 仓库（pangaea-data-publisher/fuji）
- **许可证 MIT**（PANGAEA 2020）；180 个 Python 文件；最新提交 2026-09-24（活跃）；Docker + CI + simpleclient 齐备。
- **架构**：`harvester/`（元数据采集）与 `evaluators/`（逐指标评测）分离；`fuji_server/yaml/metrics_v0.5.yaml` 声明式定义全部指标，另有 `metrics_v0.7_software.yaml`（已从数据集扩展到软件对象）。

**指标 YAML 的设计要点（值得 oed 借鉴）**：
1. 每条指标带 `metric_identifier`（如 FsF-F1-01D）+ 指标规范本身的 DOI 版本引用（`metric_specification: https://doi.org/10.5281/zenodo.6461229`）——**指标目录是可引用、可版本化的规范对象**；
2. 每指标拆 `metric_tests[]`，**每个测试有独立分数（0/0.5/1）与成熟度等级（1-3）**——不是布尔通过/失败，而是分级打分；
3. `evaluation_mechanism` 用自然语言写明判定机制——检查项自带可读的"方法学说明书"。

### 开源状态对比（GitHub API 实测）

| 项目 | ⭐ | 许可证 | 活跃度 | 备注 |
|---|---|---|---|---|
| fuji (F-UJI) | 中量级 | **MIT** | 2026-09 提交 | 学术托管 |
| soda-core | 2,436 | NOASSERTION（自定义/变更） | 2026-10 活跃 | **已重新定位为 "Data Contracts engine"**——品类漂移信号 |
| elementary | 2,422 | Apache-2.0 | 2026-10 活跃 | dbt 原生 |
| cleanlab | 11,709 | Apache-2.0 | 2026-01（**9 个月未推**，节奏放缓） | 商业重心转 Studio |
| datahub | 12,857 | Apache-2.0 | 2026-10 活跃 | 元数据平台 |
| DataSeer | dataseer-ml 29⭐ | 开放 ML 核心 | — | **混合模式：ML 核心开源建信任，产品闭源收费** |

### 对 oed 的三项工程决策建议
1. **检查项目录 YAML 化 + 规范 DOI 化**：把《标准映射表》做成 F-UJI 式的版本化 YAML（每项检查带国标条款引用、分级分数、成熟度），而非纯文档；
2. **检查结果分级打分**：借鉴 maturity 1-3 与 0/0.5/1 计分，替代布尔结论——与"不把未验证包装成通过"的定位一致；
3. **参考 DataSeer 混合模式**：检查核心（规则引擎+标准映射）开源建信任，批量服务/尽调报告收费。
