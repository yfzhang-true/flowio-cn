# 文献库总台账

> 命名规范：`YYYY-一作姓[-venue]-slug.pdf`（经内容验证后统一重命名，2026-09-22）
> 结构：根目录 = 9 篇精读核心；`citers/` = 81 篇 FlowIO 被引（S2 元数据对账）
> 全部 PDF 配同名 `.txt` 提取文本；原始数据 `s2_*.json`

## 一、核心文献（根目录，9 篇，全部深读）

| 文件 | 文献 | 价值 |
|------|------|------|
| `2021-shtarbanov-chi-ea-flowio.pdf` | FlowIO 平台（CHI'21 EA，被引 101） | 对标本体：7 常闭阀架构、单传感器分时、±179/+207kPa 包线、泵 PWM 调流 |
| `2025-shtarbanov-phd-thesis.pdf` | Shtarbanov 博士论文（303 页） | **Table 2/3 泵实测锚点**（Small -38~+61kPa/±0.3L/min）、5 配置、12 部署案例、模块生态 |
| `2022-xavier-frontiers-nonlinear-controllers.pdf` | Xavier 控制器论文（Front. Robot. AI） | 物理模型权威：dP/dt=γP/V·Q + ANSI 阀孔方程 + choked、γ=1.2 |
| `2020-xavier-aim-pneumatic-sources.pdf` | Xavier 泵源建模（IEEE/ASME AIM 2020） | 正排量泵=理想流量源；储气罐平滑；FCB 综述 |
| `2020-stanley-asme-lumped-param-circuits.pdf` | Stanley & Amini RC 时序（ASME） | 次要损失阻力 ΔP=½Kρu²；RC 动力学；验证区 0.5–16mL 互洽 |
| `2013-yao-uist-pneui.pdf` | PneUI（UIST'13，被引 201-1000） | 界面设计参考：压力→形变连续映射、各向异性材料 |
| `2021-afsar-uist-omnifiber.pdf` | OmniFiber（UIST'21） | 流体纤维驱动、绕线交互（Shtarbanov 合作） |
| `2022-youn-tei-pneubots.pdf` | PneuBots（TEI'22） | 模块化充气教育套件——P0 教育定位直接对标 |
| `2022-aljomairi-smarchs-thesis-pneuknit.pdf` | PneuKnit（MIT SMArchS 2022） | 气压针织自成形（建筑/可穿戴） |

## 二、被引文献（citers/，81 篇）

- 完整索引（标题/一作/venue/被引/本地文件）：**[citers/INDEX.md](citers/INDEX.md)**
- 阅读笔记（分层：深读/扫读）：**[citers/READING-NOTES.md](citers/READING-NOTES.md)**
- 学术地图与客户清单：**[../study-notes/14-学术地图与潜在客户.md](../study-notes/14-学术地图与潜在客户.md)**

## 三、检索与整理方法存档

- AMiner：精确标题走 `search_paper_by_title`（keyword-only 常返回 no data）；被引清单用 S2 API；机构信息 `get_paper_detail`
- DOI 勘误：Xavier 2022 = 10.3389/frobt.2022.**818187**；FlowIO 系 CHI'21 EA
- 下载坑：远端静默截断（无 %%EOF）需续传重下；ACM/DSpace 反爬交用户浏览器
- 重命名流程：pypdf 提取首页 → 归一化标题前缀匹配 S2 元数据（75/82 自动）→ DOI/人工补 6 篇 → 重复件（Xavier controllers citers 副本）删除
