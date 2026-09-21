# 文献台账（孪生物理 + 界面设计）

> 检索：AMiner MCP（26 工具，2026-09-21）；下载：开放获取直链；提取：pypdf 全文 → 同名 .txt
> 规矩：**先阅读，后 SPEC/PLAN**（SPEC 见 `firmware/twin/PHYSICS-SPEC.md` 与 `UI-DESIGN-REF.md`）

## 已入手（3 篇，均已全文阅读）

| 文件 | 文献 | 出处 | AMiner 元数据 | 对本项目的价值 |
|------|------|------|---------------|---------------|
| `flowio-chi2021.pdf` | FlowIO Development Platform – the Pneumatic "Raspberry Pi" for Soft Robotics（Shtarbanov, 单作者） | CHI'21 EA | ID `60a7892691e0110affd71d5d`，DOI 10.1145/3411763.3451513，被引 101 | **对标本体**：7 常闭电磁阀+汇流管架构、单传感器分时测量（S0 定位依据）、规格包线 −26~+30 psi(≈−179~+207 kPa)/3.2 L/min、泵 PWM 调流、被动释放、串/并联配置 |
| `xavier-frontiers2022.pdf` | Model-Based Nonlinear Feedback Controllers for Pressure Control of Soft Pneumatic Actuators Using On/Off Valves（Xavier, Fleming, Yong） | Frontiers in Robotics and AI 9:818187, 2022（开放获取） | ID `625531e75aee126c0fe0a595`，被引 11 | **物理模型权威依据**：多变气体定律 dP/dt=γP/V·Q（Eq.1-4）+ ANSI/(NFPA)T3.21.3 阀孔流方程 Q=114.5·u·Cv·√(ΔP·P_low)/√T（Eq.3-7）、γ=1.2、40Hz PWM 占空比控制、控制仿射形式 ẋ=f(x)+g(x)u |
| `pneui-uist2013.pdf` | PneUI: Pneumatically Actuated Soft Composite Materials for Shape Changing Interfaces（Yao, Niiyama, Ou, Follmer, Della Silva, Ishii） | UIST'13 | ID `5390bb7b20f70186a0f40032`，DOI 10.1145/2501988.2502037，被引 201-1000 | **界面设计参考**：压力→形变连续映射（bending→curling 随气压连续）、材料各向异性控制形变方向、交互词汇（stretch/bend/embrace/stroke/squeeze）、亚秒级响应目标 |

## 检索中发现的关联文献（按需补充）

| 文献 | 出处 | 状态 |
|------|------|------|
| OmniFiber: Integrated Fluidic Fiber Actuators（Shtarbanov 合作） | UIST'21 | 见 DOWNLOAD-LIST（可选） |
| PneuBots: Modular Inflatables for Playful Exploration（Shtarbanov） | TEI'22 | 见 DOWNLOAD-LIST（可选） |
| MorphIO: Entirely Soft Sensing and Actuation Modules（FlowIO 引文） | — | 见 DOWNLOAD-LIST（可选） |
| Soft Robotics Toolkit（FlowIO 引文） | — | 教育套件对标，暂缓 |

## 检索方法备注（AMiner 实战）

- `search_paper` 只传 keyword 常返回 no data，**精确标题走 `search_paper_by_title`**，人物走 `search_person`→`get_person_papers`，引文网络 `get_paper_citations`，会议 `search_venue`
- **DOI 勘误**：Xavier 2022 正确 DOI 为 10.3389/frobt.2022.**818187**（此前 web 检索所得 882515 为误，导致下载失败）
- FlowIO 论文正式发表于 **CHI'21 EA**（此前某 web 结果称 TEI'21 为误；与用户所述一致）
