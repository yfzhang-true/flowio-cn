# 待下载文献清单（精细动作控制技术方案，2026-09-22，v4 ✅ 清零）

> **v4（2026-09-22 晚）：下载清单正式清零**——3C-ACT 论文（#3）到手并精读（笔记 21"四点五"节）。
> 精细动作控制文献体系完整：架构（Chen）+ 拇指双方案（Wang 三腔/Xie 双腔差压）+ 行业地图（Yilmaz）+ 技术雷达（Xu）+ 竞品拆解（专利）。
> 唯一剩余可选项 #2（天津理工，付费墙）**建议放弃**——两套拇指方案已覆盖。

## ⭐ 待下载

**（无——已全部到手或决定放弃）**

## ✅ 已下载并精读（2026-09-22，笔记 21）

| # | 文献 | 本地文件 | 核心收获 |
|---|------|---------|---------|
| 1 | Chen 2026 CNC 热封手套（arXiv 2604.00768） | `2026-chen-arxiv-cnc-ergonomic-glove.pdf` | ESP32+12 阀+浏览器 GUI 架构同构验证；CNC 热封 DIY 工艺；50-100kPa 工作区间 |
| 3 | Wang 2022 拇指执行器对比（Applied Sciences 12:3735） | `2022-wang-appsci-thumb-assist-comparison.pdf` | **3C-ACT 三腔独立 Kapandji 满分**（vs 模块化 0-5）；Pro 版拇指=3 通道；"控制方法待开发"=B2B 定位原文 |
| 4 | Xie 2026 便携拇指手套（**Advanced Science**, CUHK） | `2026-xie-advsci-portable-thumb-glove.pdf` | 双腔折纸差压 143°；18N；**XGZP6857A 与我们 BOM 同款**；贝叶斯 AAN 控制 |
| 5 | Yilmaz 2026 织物综述（Adv. Mater. Technol.） | `2026-yilmaz-amt-fabric-gloves-review.pdf` | 5 大制造家族；开环被判死刑（我们闭环卖点）；行业无测试标准（评估卖点） |
| 6 | Xu 2026 气动回路博士论文（Uppsala） | `2026-xu-uppsala-pneumatic-circuits-thesis.pdf` | 多路复用（技术雷达）；RC 类比验证一阶建模 |
| — | 专利 CN108392375A（郑州大学） | `2018-cn108392375a-patent-pneumatic-glove.pdf`（图片扫描件） | 双泵/双作用/12 传感/迭代学习控制（拆解见笔记 20） |
| — | ~~Sansone SMA 扭转执行器~~（误下载） | `2022-sansone-actuators-sma-torsion.pdf` | 与产品无关，留档 |

## 📥 可选项（建议放弃）

| # | 文献 | 来源 | 备注 |
|---|------|------|------|
| 2 | Thumb-inspired Multidirectional Bending（天津理工 2025） | ScienceDirect 付费墙 | Wang 三腔 + Xie 双腔已覆盖拇指需求，放弃不影响 |

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
