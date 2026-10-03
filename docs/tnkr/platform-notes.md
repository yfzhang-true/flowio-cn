# Tnkr 平台深调备忘（T0）

> **考察日期**: 2026-10-03 · **方式**: WebFetch 静态抓取（未注册账号）
> **来源**: tnkr.ai 主站/explore/pricing、3 个项目页、github.com/tnkrai
> **局限**: Files/Documentation 标签内容与 Pricing 页为 JS 渲染/登录墙后，静态不可见——已列为本备忘"待注册核实"项

## 1. 平台身份

| 项 | 结论 | 来源 |
|---|---|---|
| 定位 | "GitHub for Robots"——开源机器人硬件+具身智能项目托管 | tnkr.ai |
| 四要素 | Hardware / Software / Data / Models | tnkr.ai |
| 与 GitHub | 集成不替代：项目页外链 GitHub 仓库（3/3 抽样项目均有） | 项目页抽样 |
| 商业模式 | SaaS 定价（页面 JS 渲染，静态不可见）+ **套件销售** | tnkr.ai/pricing + 项目页 |

## 2. 项目页解剖（3 个样本：xlerobot / open-duck-mini-v2 / aero-hand-open）

| 要素 | 观察 |
|---|---|
| 标签结构 | Overview / Documentation / Files / Merge Requests / Mods / Help Center |
| 社交机制 | Clone Project（克隆）、Create Mod（二创）、Skins、Stats（数据登录后可见） |
| 维护主体 | 分组托管（komak-robotics、open-duck-mini 等组名），"Powered By Tnkr" |
| **套件销售** | **XLeRobot kit $550、Open Duck Mini V2 kit $600**（"parts, hardware, and electronics, ready to assemble"）——平台内直接卖硬件套件 |
| GitHub 外链 | 每个项目页均有 repo 链接（Reza2kn/aero-hand-open、Maker-Mods/MakerMods-XLeRobot、apirrone/Open_Duck_Mini） |
| AI 助手 | Leo/Leonardo 需登录使用 |
| License 展示 | 抽样项目页静态内容未见（待注册核实） |

## 3. 品类与空白

浏览分类（formFactor）：quadrupeds×4 · arms×10 · drones×2 · bipeds×0 · humanoids×8 · hands×7（合计 ~31）。

**无 soft robotics / pneumatic 分类，无气动项目**。最接近的是 aero-hand-open（腱驱动欠驱动手，非软体气动）。→ FLOWIO-CN 是该平台首个气动软体机器人方向项目，差异化明显。

## 4. github.com/tnkrai 组织（复查成功）

| 仓库 | 语言 | Stars | 说明 |
|---|---|---|---|
| tnkr-site | TypeScript | 4 | 着陆页 |
| Open_Duck_Mini_Runtime | Python | 2 | Duck 运行时代码 |
| trlc-dk1-runtime | Python | 0 | fork 自 robot-learning-co |
| studio-docs | MDX | 0 | 文档（MIT） |

→ 组织仅托管**示例运行时与文档**，平台本身不开源；无通用 CLI/SDK 可用于自动化发布。

## 5. 待注册核实清单（2026-10-03 发布后已全部核实 ✅）

1. 项目创建入口：`/projects/add-project` 两路径（GitHub 导入 / 从零手写）；GitHub 导入自动扫描 repo 内 STEP 并要求**恰好选 1 个主 STEP**（其余文件走 Files 区）
2. 3D 上传：STP/STEP 支持，**单文件上限 100 MB**；仓库内自动发现；本地 STL 网格经仓库 Files 区直接可得
3. BOM 导入：无专用导入步骤；BOM csv 随仓库文件树进入 Files 区，Leo 助手可 AI 解答（"Show me the BOM"）
4. Pricing：**GitHub 导入 + 公开项目全流程零付费墙**（free tier 够用）
5. License：无专用字段；以 description 文本承载双声明（已含 "Code MIT / HW CERN OHL-S"）
6. 套件上架：项目列表有 Kits 标签（当前 disabled，疑似需条件解锁）；站内先例 XLeRobot $550 / Open Duck Mini $600
7. 文档与 3D viewer 均为 **Leonardo 异步处理**（发布后 "Leonardo is processing…"，Documentation 与 canvas 稍后自动出现）
8. 附加发现：GitHub App 安装支持最小权限（仅授权 flowio-cn 单仓库，只读）

## 6. 对本项目的三点策略修正（相对 spec §4）

1. **套件销售渠道升级为一级目标**：原 spec 把 Tnkr 当"展示/导流"，实际它支持站内卖 kit——与 FLOWIO-CN 的 B2B 套件模式直接对口，$550/$600 先例证明价格带成立。
2. 发布深度维持"轻发布"不变：静态抓取已证明项目页核心信息（简介+GitHub 链）可轻量建立，重内容（3D/BOM）依赖 Files 机制，注册后按实际支持度决定填充深度。
3. 自动化预期调低：无公开 CLI/API，发布需网页操作（browser-use 辅助或用户手动）。
