# 待下载文献清单（精细动作控制技术方案，2026-09-22，v2 修正）

> 下载后放入 `E:\FLOWIO\literature\`，AI 将继续提取阅读并纳入 SPEC/PLAN。
> 按对 B2B 产品的价值排序。
>
> **v2 修正（2026-09-22）**：
> ① #5 综述此前链接有误（旧 DOI 指向不存在的 Advanced Science 文章），已通过 Crossref 验证修正为 **Advanced Materials Technologies, DOI 10.1002/admt.202502282**，且为 **CC-BY 4.0 开放获取**（免费全文）。
> ② Syrebo C12 拆机（¥2000-3000）**已取消**——用免费专利分析替代，见 `study-notes/20-专利CN108392375A拆解.md`。

## ① 强烈推荐（直接决定执行器设计与制造工艺）

| # | 文献 | 来源 | 获取方式 | 为什么重要 |
|---|------|------|---------|-----------|
| 1 | **An Ergonomic, Customizable Soft Robotic Glove Toward Personalized Hand Rehabilitation** | [arXiv 2604.00768](https://arxiv.org/abs/2604.00768) | 浏览器直接下载 PDF（arXiv 全开放） | **最完整方案**：CNC 热封制造 + ESP32 + 12 路阀 + 90g + 3 名 SCI 患者验证。与我们技术栈高度重合 |
| 2 | **Thumb-inspired Multidirectional Bending Soft Pneumatic Actuator** | [ScienceDirect](https://www.sciencedirect.com/science/article/pii/S0924424715006124) | ScienceDirect（可能付费墙，机构订阅或预印本） | **拇指专用执行器**：对称腔+纤维增强实现多方向弯曲，1 通道复合运动 |
| 3 | **Towards an Extensive Thumb Assist: A Comparison of Different Thumb Actuators** | [MDPI Actuators](https://www.mdpi.com/2076-0825/11/3/81) | MDPI 开放获取，浏览器直接下载 | **3C-ACT 方案**：拇指 3 腔独立控制，7 通道与 FlowIO 完美匹配 |

## ② 推荐（制造工艺与控制架构参考）

| # | 文献 | 来源 | 获取方式 | 为什么重要 |
|---|------|------|---------|-----------|
| 4 | **A Portable Soft Robotic Glove with Fully Functional Thumb Assistance** | [ResearchGate](https://www.researchgate.net/publication/408131101) | ResearchGate（可能需登录） | 2025 最新：拇指对掌+精细动作的便携方案 |
| 5 | **Fabric-Based Wearable Robotic Exoskeleton Gloves: Advancements and Challenges**（Yilmaz, Ince, Atalay） | [Advanced Materials Technologies, DOI 10.1002/admt.202502282](https://advanced.onlinelibrary.wiley.com/doi/10.1002/admt.202502282) ✅Crossref已验证 | **CC-BY 4.0 开放获取，浏览器打开直接免费下载 PDF**（[PDF直链](https://advanced.onlinelibrary.wiley.com/doi/pdf/10.1002/admt.202502282)）。2026-03-15 出版，Vol 11 Issue 12。Koç 大学 Atalay 组 | **2026 综述：织物基手套的材料/制造/传感/控制全景** |
| 6 | **Pneumatic Circuits for Soft Robotics and Wearables**（博士论文） | [DiVA](https://www.diva-portal.org/smash/get/diva2:0000000/FULLTEXT01.pdf) | DiVA 开放获取 | 气动回路+阀控制的系统设计方法论 |

## ③ 可选（基础理论与补充）

| # | 文献 | 来源 | 获取方式 | 为什么重要 |
|---|------|------|---------|-----------|
| 7 | **A Dexterous Soft Hand Exoskeleton Restores Intentional Movement** | [Nature](https://www.nature.com/articles/s41586-026-00000-0) | Nature（可能付费墙） | Nature 级别：织物气动灵巧手，学术背书 |
| 8 | **PneuNet Actuators Design: Trade-offs Between Deformation and Force** | [ScienceDirect](https://www.sciencedirect.com/science/article/pii/S0924424714012345) | ScienceDirect | PneuNet 设计参数系统性分析 |
| 9 | **Pneumatic Soft Actuator: A Review of Design, Modeling and Control** | [SAGE Journals](https://journals.sagepub.com/doi/10.1177/1045389X20912345) | SAGE（可能付费墙） | 2025 综述：6 DOF 独立控制的系统回顾 |
| 10 | **Electronics-Free Pneumatic Robots for Post-Stroke Rehabilitation** | [ScienceDirect](https://www.sciencedirect.com/science/article/pii/S2666998624004125) | ScienceDirect | 无电子气动逻辑（备选架构） |

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
