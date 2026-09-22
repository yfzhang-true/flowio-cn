# 文献台账（孪生物理 + 界面设计）

> 检索：AMiner MCP（26 工具，2026-09-21/22）；下载：开放获取直链 + 用户手动补充；提取：pypdf 全文 → 同名 .txt
> 规矩：**先阅读，后 SPEC/PLAN**（SPEC 见 `firmware/twin/PHYSICS-SPEC.md` 与 `UI-DESIGN-REF.md`）

## 已入手（7 篇，均已全文提取）

| 文件 | 文献 | 出处 | 价值 |
|------|------|------|------|
| `flowio-chi2021.pdf` | FlowIO Development Platform（Shtarbanov） | CHI'21 EA，被引 101（AMiner `60a7892691e0110affd71d5d`） | **对标本体**：7 常闭阀架构、单传感器分时测量、−26~+30 psi/3.2 L/min 包线、泵 PWM 调流 |
| `xavier-frontiers2022.pdf` | Model-Based Nonlinear Feedback Controllers…（Xavier/Fleming/Yong） | Front. Robot. AI 9:818187, 2022 | **物理模型权威**：dP/dt=γP/V·Q + ANSI/(NFPA)T3.21.3 阀孔流方程 + choked flow、γ=1.2 |
| `xavier-pumpsources-2021.pdf` | Modelling and Simulation of Pneumatic Sources（同组） | IEEE | **泵源动力学**：正排量泵=理想流量源近似（每循环定容、与出口压力无关）；储气罐平滑间歇；FCB 平台综述（用户手动下载） |
| `pneui-uist2013.pdf` | PneUI（Yao 等，MIT） | UIST'13，被引 201-1000 | **界面设计参考**：压力→形变连续映射、各向异性材料控制形变 |
| `omnifiber-uist2021.pdf` | OmniFiber: Integrated Fluidic Fiber Actuators（Shtarbanov 合作） | UIST'21 | 流体纤维驱动、绕线交互（用户下载；原文件名误标 MorphIO，按实际内容更正） |
| `pneubots-tei2022.pdf` | PneuBots: Modular Inflatables（Youn/Shtarbanov） | TEI'22 | 模块化充气教育套件——P0 教育定位直接对标（用户下载） |
| `AlHajri-…-thesis.pdf` | Self-Shaping Mechanisms: PneuKnit（Aljomairi） | MIT SMArchS 2022 | 气压针织自成形——建筑/可穿戴气动方向（用户自选） |

## 学术地图

引用 FlowIO 的 83 篇论文全量挖掘 + 中国实验室客户清单 → **[../study-notes/14-学术地图与潜在客户.md](../study-notes/14-学术地图与潜在客户.md)**

## 检索方法备注（AMiner 实战）

- `search_paper` 只传 keyword 常返回 no data，**精确标题走 `search_paper_by_title`**，人物走 `search_person`→`get_person_papers`，被引清单用 Semantic Scholar API（AMiner 的 `get_paper_citations` 返回的是参考文献不是被引）
- **DOI 勘误**：Xavier 2022 正确 DOI 为 10.3389/frobt.2022.**818187**（web 检索所得 882515 为误）
- FlowIO 论文正式发表于 **CHI'21 EA**（某 web 结果称 TEI'21 为误）
- 下载坑：远端会静默截断（无 %%EOF），必须校验后 `-C -` 续传重下
