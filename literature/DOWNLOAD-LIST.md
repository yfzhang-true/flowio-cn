# 待下载文献清单（自动化受阻，请用户手动获取）

> 下载后放入本目录（E:\FLOWIO\literature\），AI 将继续提取阅读并纳入 SPEC。

## ✅ 用户已解决（2026-10-03 · 器件几何框架基线 11 篇，已从 FLOWIO-3rdparty 归位并全文精读）

- [x] AlphaChip 正主（Nature 2021）→ `2021-mirhoseini-nature-alphachip.pdf`（可行性掩码一手方法论）
- [x] AlphaChip 官方 Addendum（Nature 2024）→ `2024-goldie-nature-alphachip-addendum.pdf`
- [x] UCSD RL 宏布置更新评估（arXiv 2302.11014）→ `2023-cheng-arxiv-rl-macro-assessment.pdf`
- [x] DREAMPlace（DAC'19）→ `2019-lin-dac-dreamplace.pdf`
- [x] OpenPARF（arXiv 2306.16665）→ `2023-mai-arxiv-openparf-fpga.pdf`
- [x] ODIM 斜方向几何可行性 ASP（JESTCH 2022）→ `2022-kumar-jestch-odim-oblique-asp.pdf`（P0，板级 GF 依据）
- [x] SOS-ACO ASP（FME 2021）→ `2021-han-fme-sos-aco-asp.pdf`
- [x] Expertise-RL（ICLR 2026）→ `2026-gao-iclr-expertise-rl-placement.pdf`（periphery bias/I-O keepout = EDGE_OUT 学名）
- [x] RollPlace（TCAD 45(7) 2026）→ `2026-zhou-tcad-rollplace.pdf`
- [x] VeoPlace（VLM 布局）→ `2026-uchendu-vlm-veoplace.pdf`
- [x] OrderPlace（ICML'26，摆放顺序多米诺）→ `2026-mo-icml-orderplace.pdf`
> 精读要点：`docs/research/2026-10-03-baseline-reading.md` §7/§9（device-geometry 分支）

## ✅ 用户已解决（2026-09-22）

- [x] Xavier 等《Modelling and Simulation of Pneumatic Sources…》→ `xavier-pumpsources-2021.pdf`
- [x] OmniFiber（UIST'21）→ `omnifiber-uist2021.pdf`（原文件名误标 MorphIO，已按内容更正）
- [x] PneuBots（TEI'22）→ `pneubots-tei2022.pdf`
- [x] PneuKnit 学位论文（MIT SMArchS 2022，用户自选）→ `AlHajri-…-thesis.pdf`
- [x] **Lumped-Parameter Response Time Models（ASME 2020）** → `Lumped-Parameter Response Time Models for Pneumatic Circuit Dynamics.pdf`（已提取 `lumped-param-asme2020.txt`，阻力模型已并入 PHYSICS-SPEC）

## ⚠ 待用户下载（链接已用 DSpace API 元数据验证）

**Shtarbanov 博士学位论文**《Modular Development Platforms and Creative Ecosystems: Design & Deployment for Wide Impact Across Fields》
- 作者：Shtarbanov, Ali ｜ 类型：Thesis ｜ 时间：2025-05 ｜ handle：1721.1/164267
- 文件：`Shtarbanov-alims-PHD-MAS-2025-thesis.pdf`（约 25 MB）
- **正确直链（浏览器打开，过一次人机验证）**：https://dspace.mit.edu/bitstreams/1312d343-1433-453b-acb8-6653e9339e4d/download
- 论文详情页（备选入口）：https://dspace.mit.edu/handle/1721.1/164267
- ⚠ 勘误记录：此前提供的 `e2f98dce-…` 直链来自搜索引擎误标，实测指向 Aljomairi 的 PneuKnit 论文（DSpace API 已核实该 bitstream 官方名称）。本次链接由 DSpace 官方 API 的 bitstreams 清单直接取得。
- 下载后放入 `literature/`——它是各泵模块实测压力-流量数据的唯一来源，物理标定表等它落地。

## ① 仍强烈推荐（物理 SPEC 标定关键）

**Shtarbanov MIT 硕士学位论文**（FlowIO 完整设计/制作指南，含各泵模块实测压力-流量数据）
- 直链：https://dspace.mit.edu/bitstreams/e2f98dce-97ec-4c01-b53d-8954074cc039/download
- 受阻：**AWS WAF 人机验证**（浏览器打开触发验证，人工通过后可下载）

## ② 可选（未获取）

| 文献 | 入口 | 受阻原因 |
|------|------|---------|
| **MorphIO**: Entirely Soft Sensing and Actuation Modules（FlowIO 引文） | ACM DL 搜 "MorphIO" | ACM 拦截 |

## ③ 可选（付费墙，优先级低）

| 文献 | 入口 |
|------|------|
| Lumped-Parameter Response Time Models for Pneumatic Circuits（ASME 2020） | asmedigitalcollection.asme.org |
