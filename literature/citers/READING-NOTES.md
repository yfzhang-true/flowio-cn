# 阅读笔记（literature 全库 90 篇）

> 分层：A 核心深读（9）｜B 竞品对标（4，规格表）｜C 全库主题分组扫读（81 被引）
> 生成 2026-09-22，全部基于本地提取文本

## A. 核心深读（根目录 9 篇——结论已沉淀进 PHYSICS-SPEC / UI-DESIGN-REF / 客户清单）

1. **FlowIO CHI'21**：7 常闭阀+汇流管、单传感器分时复用（S0 定位依据）、泵 PWM 调流、被动释放（泵单向性）、5 种泵配置（串=高压/并=大流量）。
2. **Shtarbanov 博士论文 2025**：Table 2/3 实测锚点（Small -38~+61kPa、Medium -61~+165kPa、流量 0.3→3.4 L/min）；模块生态与 12 部署案例；同型号泵个体差异警示。
3. **Xavier Frontiers 2022**：dP/dt=γP/V·Q + ANSI/(NFPA)T3.21.3 阀孔流 √(ΔP·P_low) + choked 分支，γ=1.2；控制仿射形式 ẋ=f(x)+g(x)u。
4. **Xavier AIM 2020**：正排量泵=理想流量源近似；储气罐平滑间歇需求（P1 参考）；FCB 是社区最常用开源平台。
5. **Stanley ASME 2020**：RC 时序模型；次要损失阻力 ΔP=½Kρu²（管路/弯头/阀）；验证区 0.5–16mL、5–200kPa（与 P0 尺度互洽）。
6. **PneUI UIST'13**：压力→形变连续映射（bend→curl）；材料各向异性定向；交互词汇 stretch/bend/embrace/stroke/squeeze。
7. **OmniFiber UIST'21**：流体纤维驱动，绕线即编程；管径细、压降低的场景。
8. **PneuBots TEI'22**：模块化充气教育套件（连杆+气囊即搭即玩）——P0 教育定位最直接对标。
9. **PneuKnit 2022**：气压针织自成形（建筑尺度），展示气动在建造/穿戴外延。

## B. 竞品对标（规格横表——P0 定位校准）

| 产品 | 压力 | 流量/控制 | 架构特点 | 对 P0 的启示 |
|------|------|----------|---------|-------------|
| **FlowIO（本尊）** | -30~+30 psi（模块包线至 -179/+207 kPa） | ≤3.4 L/min、泵 PWM | 7 常闭阀集中式、5 端口、Web/BLE/串口 | 平台标杆；被竞品共同诟病"小尺度、集中式布线" |
| **iSoRD**（南科大/深技大， RA-L'25） | -53~+83 kPa | 泵 PID 连续流量 15 mL/s | 单泵+四通阀/通道、2.95W/通道、模块化 wearable | 与 P0 最贴身的对手；其"连续流量"固件特性值得跟进 |
| **PneuDrive**（UW, DIS'24?） | 目标 80 psi（552 kPa） | RS-485 菊花链 4 板×4 阀腔对、10-28V | **分布式嵌入式**闭环，点对点一米级布线 | 差异化区在"大规模分布式"——P0 的 ESP-NOW 多设备协议（doc10 §7）正面迎击该场景 |
| **phloSAR**（Stanford? DIS'24） | ~690 kPa（储气罐 100 psi 级） | 比例阀+Venturi 泵 | 便携高压（70-77g 部件） | "高压便携"细分；P0 0~61kPa 教育档与其错位 |

**竞争结论**：P0 不与"高压/分布式/连续流量"正面竞争——**教育/科研入门档（0~61 kPa、开箱即用、中文生态、数字孪生先行）**是空位；iSoRD 是最近邻，其论文承认复杂度门槛，恰是我们的切入叙事。

## C. 被引 81 篇主题分组（每篇一句价值）

### C1 平台与控制（含 FlowIO 同类，12 篇）
UCL 特征化平台（RoboSoft'23，MATLAB GUI+Arduino Due/NI——测试台路线）｜PneuDrive｜phloSAR｜**Xavier IEEE Access 综述（被引 313！设计/制造/建模/传感/控制全谱——第二物理参考）**｜FPGA 混合阀（深大）｜蠕动泵压力源（清华医）｜iSoRD 相关｜WICCU｜PneuSoRD｜SleeIO（可穿戴触觉平台）｜VIREO（Web 图形化气动编程）｜Fluidic Control（UCSD 水下）。

### C2 触觉与穿戴（20 篇）
du Pasquier 系（Wearable Pneumatic 连续闭环双向触觉 CHI'26、Haptiknit Science Robotics'24 分布刚度针织）｜Texas A&M SHD 工具包（4×4 阵列 4mm 分辨率、8Hz）｜Kang 18g 力觉戒指（Nature Electronics'25，6.5N）｜EPFL Jamie Paik 系｜MemoGlove（XR 触觉回放）｜Touchibo/In-Flat/NugiTex/Corsetto 等。

### C3 形变界面与 HCI（25 篇）
浙大圈（KiPneu/SnapInflatables/MiuraKit/Xstrings/DuoMorph/LivingLoom）｜HPI（AirForce 8m T-rex、480-2330N）｜HydroMod/InflatableMod（东大 Morita 液压/充气模块——模块化思路同类）｜Aeromorph/MorphingSkin（Berkeley+清华）｜AirCraft（空气作为设计材料）等。

### C4 抓取与机器人（12 篇）
港理工飞行软爪（RoboSoft'24，217g 载荷）｜MIT Peristaltic Suit（宇航压缩服）｜软爪综述/水下/爬行等多篇。

### C5 教育与综述（7 篇）
**软体机器人教育系统综述（IEEE TLT'24）——市场证据：教育赛道真实且增长**｜KiPneu 儿童工作坊（21 名 5-12 岁，前后测有效）｜PneuBots。

### C6 其他（5 篇）
静电执行器综述（Rauf CHI'26）、电永磁肌肉（Castillo——用户补充）、KnitSkin（Kim，机器编织爬行皮肤——用户补充）、响应式建筑（Wang/Aljomairi 建筑视角）。

## 待办

- 真缺 2 篇：**AirPinch**（充气触觉推子，meta 内未下载）、"MIT Open Access"（疑似 S2 垃圾条目，可忽略）——AirPinch 已入 DOWNLOAD-CITERS 清单
- 深读候选（按需）：Xavier IEEE Access 综述（313 被引）→ 物理细节补充；教育综述 → 市场章节
