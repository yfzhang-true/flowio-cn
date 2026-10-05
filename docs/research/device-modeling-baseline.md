# 数字孪生器件建模学术 baseline（aminer MCP 检索 · 2026-10-05）

> 目的：device-modeling spec §6 的学术 baseline 落地——为"器件精确建模+连接图谱+孪生仿真"
> 提供方法论对照。检索姿势：aminer `search_paper_by_title` 短片段（长短语恒空，项目教训复现）。

## 🎯 主对照（与本项目孪生域同题）

**Ruzarovsky et al., "Behaviour-Based Digital Twin for Electro-Pneumatic Actuator:
Modelling, Simulation, and Validation Through Virtual Commissioning", Electronics 14(12):2434, 2025.
DOI 10.3390/electronics14122434**（斯洛伐克技术大学；引 4）

- **三级保真度数字孪生对比**：离散控制级（验逻辑）→ 无气动动力学模拟级 → 含压力/摩擦/
  气流的复杂级（复现延迟相位与压力影响）——**只有高级模型能真实复现气动动态行为**；
- 工具链：Siemens NX MCD + SIMIT 仿真平台 + PLC（OPC UA 协议）；与 Jiménez 实验强相关验证；
- **对本项目的映射**：我们的三层结构与该文分级一致——
  L3 逻辑级（flows/graph）≈ 其"basic discrete control"；
  L5 物理级（devices3d 几何+连接）≈ 其"complex model"方向；
  §2.7.1 电气仿真层（电流/电压/告警）= 我们自建的"analogue control"级。
  该文证实：**几何+连接图谱之外，气动动态（延迟/压力影响）是孪生可信度的分水岭**——
  支持 spec §2.7.1 已有的压力动态方向，并将"摩擦/气流阻力项"列为孪生 P2 增强项。

## 次级对照（方法学借鉴）

1. **"Efficient Pneumatic Actuation Modeling Using Hybrid Physics-Based and Data-Driven
   Framework", Cell Reports Phys. Sci. 2022**——物理+数据混合建模：与我们"确定性物理内核
   (electrical_sim/board_model)+BRINGUP 实测校准"同构；其框架可作为孪生 P2 的参数辨识层。
2. **"Soft Pneumatic Actuator Model Based on a Pressure-Dependent Spatial Nonlinear Rod
   Theory", RA-L 2022**——软执行器非线性理论（若 P2 做连续体软致动器时启用）。
3. **电磁阀健康管理簇**（Mazaev IEEE TII 2021 贝叶斯 CNN RUL / Vantilborgh ICRA 2024
   数据驱动虚拟传感 / Angadi Eng. Fail. Anal. 2022 可靠性综述）——**阀 RUL/状态监测**
   是 P2 医疗安全叙事的学术支点（对应我们 BRINGUP 线圈电阻三档判据的学术化升级路径）。
4. Tao Fei, "Digital Twin Modeling", J. Manuf. Syst. 2022（引 1001-5000）——孪生建模
   方法论总纲（五维模型概念），用作 HANDOFF 的引用背景。

## 检索方法备忘

- aminer `search_paper_by_title` **短片段**（"digital twin"/"solenoid valve"/"pneumatic
  actuator modeling"）有效；`search_paper` 长关键词恒空（项目教训复现，姿势入库）；
- 待深挖：get_paper_detail（Cell Reports 2022 混合框架）/ search_patent（电磁阀专利族）。
