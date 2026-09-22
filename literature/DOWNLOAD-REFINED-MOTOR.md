# 待下载文献清单（精细动作控制技术方案，2026-09-22，v3 状态更新）

> 下载后放入 `E:\FLOWIO\literature\`，AI 将继续提取阅读并纳入 SPEC/PLAN。
>
> **v3（2026-09-22 晚）**：5 篇已下载并精读完成（见 `study-notes/21-精细动作文献吸收.md`）。
> **当前仅剩 2 篇待下**：#2（ScienceDirect 付费墙）和 #3（链接已修正，见下）。
> 误下载说明：原 #3 链接（Actuators 11(3):81）实际指向 Sansone 的 SMA 论文（已留档 `2022-sansone-actuators-sma-torsion.pdf`）；3C-ACT 正确出处是 **Applied Sciences 12(8):3735**。

## ⭐ 待下载（仅 2 篇）

| # | 文献 | 正确链接 | 获取方式 | 为什么重要 |
|---|------|---------|---------|-----------|
| 3 | **Towards an Extensive Thumb Assist: A Comparison between Whole-Finger and Modular Types of Soft Pneumatic Actuators**（Wang Y, Kokubu S, Chiba Univ, 2022） | [Applied Sciences 12(8):3735](https://www.mdpi.com/2076-3417/12/8/3735) ✅Crossref已验证 DOI 10.3390/app12083735 | MDPI 开放获取，**浏览器打开**（拦脚本）→ Download PDF | 整指 vs 模块化拇指执行器对比——决定 Pro 版拇指是"整指 1 通道"还是"分关节多通道" |
| 2 | **Thumb-inspired Multidirectional Bending Soft Pneumatic Actuator**（天津理工，Sensors & Actuators A 2025） | [ScienceDirect](https://www.sciencedirect.com/science/article/pii/S0924424715006124) | 付费墙，机构订阅/预印本/邮件作者 | 仿生拇指多方向弯曲：1 通道实现复合运动（若拿不到可跳过——Xie 双腔方案已覆盖需求） |

## ✅ 已下载并精读（2026-09-22，笔记 21）

| # | 文献 | 本地文件 | 核心收获 |
|---|------|---------|---------|
| 1 | Chen 2026 CNC 热封手套（arXiv 2604.00768） | `2026-chen-arxiv-cnc-ergonomic-glove.pdf` | ESP32+12 阀+浏览器 GUI 架构同构验证；CNC 热封 DIY 工艺；50-100kPa 工作区间 |
| 4 | Xie 2026 便携拇指手套（**Advanced Science**, CUHK） | `2026-xie-advsci-portable-thumb-glove.pdf` | 双腔折纸差压 143°；18N；**XGZP6857A 与我们 BOM 同款**；贝叶斯 AAN 控制 |
| 5 | Yilmaz 2026 织物综述（Adv. Mater. Technol.） | `2026-yilmaz-amt-fabric-gloves-review.pdf` | 5 大制造家族；开环被判死刑（我们闭环卖点）；行业无测试标准（评估卖点） |
| 6 | Xu 2026 气动回路博士论文（Uppsala） | `2026-xu-uppsala-pneumatic-circuits-thesis.pdf` | 多路复用（技术雷达）；RC 类比验证一阶建模 |
| — | 专利 CN108392375A（郑州大学） | `2018-cn108392375a-patent-pneumatic-glove.pdf`（图片扫描件） | 双泵/双作用/12 传感/迭代学习控制（拆解见笔记 20） |
| — | ~~Sansone SMA 扭转执行器~~（误下载） | `2022-sansone-actuators-sma-torsion.pdf` | 与产品无关，留档 |

## ③ 可选（低优先级，可放弃）

| # | 文献 | 来源 | 备注 |
|---|------|------|------|
| 7 | A Dexterous Soft Hand Exoskeleton Restores Intentional Movement | Nature | 付费墙；Yilmaz 综述已覆盖织物灵巧手进展 |
| 8 | PneuNet Actuators Design: Trade-offs | ScienceDirect | 付费墙；我们路线是织物热封非 PneuNet 弹性体 |
| 9 | Pneumatic Soft Actuator: A Review | SAGE | 付费墙；已有 Yilmaz 2026 更新综述 |
| 10 | Electronics-Free Pneumatic Robots | ScienceDirect | Xu 论文已覆盖该方向（笔记 21 判为"观察项"） |

## ④ 已在手（无需下载）

| 文献 | 位置 | 状态 |
|------|------|------|
| FlowIO CHI'21（平台架构） | `literature/2021-shtarbanov-chi-ea-flowio.pdf` | ✅ 已读 |
| Shtarbanov 博士论文（泵实测数据） | `literature/2025-shtarbanov-phd-thesis.pdf` | ✅ 已读 |
| Xavier Frontiers 2022（气动方程） | `literature/2022-xavier-frontiers-nonlinear-controllers.pdf` | ✅ 已读 |
| Syrebo SY-HR03E 产品手册 | `literature/Brochure-SYHR03E.pdf` | ✅ 已读（图片 PDF） |
| Syrebo RCT 论文（华山医院） | AMiner 元数据 `6a933b620a96f8c83cffe1dc` | 摘要已读，PDF 未下载 |
| **专利 CN108392375A 全文（气动康复手套，郑州大学）** | [Google Patents](https://patents.google.com/patent/CN108392375A/zh) | ✅ **已抓取全文并完成拆解**，见 `study-notes/20-专利CN108392375A拆解.md`（替代 C12 实物拆机） |

## 补充：实物采购建议（配合文献阅读）

| 物品 | 渠道 | 预估价格 | 用途 |
|------|------|---------|------|
| **TPU 涂层尼龙织物**（40D 单面 + 20D 双面） | 1688 搜"TPU 涂层尼龙布" | ¥15-25/米 | 路线 A 的执行器材料 |
| **TPU 气管**（外径 4mm / 内径 2.5mm） | 1688（已在采购车？） | ¥1-2/米 | 气路连接 |
| **硅胶 Ecoflex 00-30**（备选制造） | 淘宝 | ¥80-120/套 | 路线 B 的硅胶模具 |
| **Kevlar 纤维线** | 淘宝 | ¥10-20/卷 | 纤维增强（路线 B） |
| ~~Syrebo C12 家用版（竞品拆机）~~ | ~~京东~~ | ~~¥2000-3000~~ | **已取消**：用专利 CN108392375A 免费分析替代（双泵/双作用执行器/12 传感器/迭代学习控制等关键规格已提取，见 study-notes/20） |
