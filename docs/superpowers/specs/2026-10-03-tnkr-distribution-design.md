# Tnkr 平台接入 — 设计规格书（评估 + 轻发布 + 反向输血）

> **日期**: 2026-10-03 · **状态**: 待用户审查
> **背景**: 用户发现 tnkr.ai（GitHub org: github.com/tnkrai），要求评估其对"数字孪生 FLOWIO-CN"的价值
> **考察结论先行**: **有价值，且是两层价值**——①它是为 FLOWIO-CN 这类项目量身定做的分发渠道；②它的项目页形态是我们数字孪生的"已验证产品镜鉴"。

---

## 1. 平台考察结论（2026-10-03 实地抓取）

**Tnkr（tnkr.ai）= "GitHub for Robots"**：开源机器人硬件 + 具身智能项目平台，覆盖"物理智能四要素：Hardware / Software / Data / Models"。

| 考察点 | 事实 | 来源 |
|---|---|---|
| 定位 | 开源机器人硬件的托管/展示/协作平台，自述"the onboarding funnel to bring millions of new developers and data collectors into robotics" | tnkr.ai 主站 |
| 项目页形态 | **3D 交互可视化 + 零件分解**（exploded breakdown）、**BOM 管理 + 供应商连接**、分步装配说明（含 POV 视频 AI 生成）、控制系统/传感器代码文档、数据集、可部署模型 | tnkr.ai 主站 + explore |
| 与 GitHub 关系 | **集成而非替代**（GitHub/Onshape/SolidWorks 均为连接工具），GitHub 仍是代码权威源 | tnkr.ai 主站 |
| Leonardo（AI 助手） | "AI Hardware Engineer"：分析建造视频/CAD/代码 → 一键生成文档与装配说明、实时排障（beta） | tnkr.ai 主站 |
| 社区现状 | ~31 个项目（四足/人形/机械臂/灵巧手为主），**软体机器人/气动方向空白**；star/fork/agent 社交机制 | tnkr.ai/explore |
| 商业模式 | SaaS 定价 + 免费试用（free tier 具体限额待 T0 核实） | tnkr.ai pricing |
| 开源动作 | 已发布 Python-first 机器人学习框架（tnkrai org，GitHub 组织页访问超时，T0 复查） | tnkr.ai blog |

## 2. 对"数字孪生 FLOWIO-CN"的价值判断

### 2.1 第一层：分发渠道（直接价值，推荐做）

FLOWIO-CN 的资产与 Tnkr 项目页模型**一一对应**：

| Tnkr 项目页要素 | FLOWIO-CN 现有资产 | 状态 |
|---|---|---|
| 3D 零件分解 | `firmware/twin/meshes/`（case_top/bottom、parts_f/b、pcb 共 5 个 STL）+ enclosure STEP | ✅ 现成 |
| BOM + 供应商 | `hardware/flowio-p1/fab/flowio-p1-bom-jlc.csv`（107 行，LCSC 编码 100%） | ✅ 现成 |
| 装配说明 | `firmware/BRINGUP.md`（9 章 30 检查项）+ JLC 制造包 README | ⚠️ 需英文化/重构为分步 |
| 代码文档 | GitHub repo（MIT/CERN OHL-S 双开源，200+ commits） | ✅ 现成 |
| 数据/模型 | 数字孪生 sim_engine + flows.json（气动仿真数据） | ✅ 现成（差异化亮点） |

- **时机红利**：平台仅 ~31 个项目、软体气动方向空白——早期进入有 trending 曝光机会；
- **B2B 副作用**：康复手套厂商/具身智能数据团队可能经此发现 FLOWIO-CN（目标客群触达）；
- **求职副作用**：Tnkr 精选项目 = 乐鑫投递弹药的一部分（AIoT 生态叙事加强）。

### 2.2 第二层：产品镜鉴（反向输血，记入 backlog）

Tnkr 项目页验证了三个我们孪生前端尚未做/可加强的特性 → 记入 twin v2.1 候选（**本期只记录不实现**）：

1. **零件注释（Annotations are to hardware what comments are to code）**——我们已有 `hotspots.json` 基础，升级为点击零件弹出文档/规格/BOM 行；
2. **BOM 面板 + 供应商直链**——孪生侧栏显示 107 行 BOM，LCSC 编码可点（采购转化）；
3. **分步装配模式**——"assembly as a programming language"：爆炸滑杆按 BRINGUP 章节步进（每步高亮相关零件 + 检查项）。

### 2.3 明确不做（YAGNI）

- ❌ 不迁移仓库：GitHub 保持唯一权威源，Tnkr 只做展示/导流（它本来就集成 GitHub）；
- ❌ 不付费：先 free tier，限额不够再说；
- ❌ 不用 Leonardo 生成文档：beta + 我们已有 94 页专著和 BRINGUP 体系；
- ❌ 本期不实现 v2.1 特性：那是下一个 spec 的事。

## 3. 方案比选

| 方案 | 内容 | 工作量 | 推荐 |
|---|---|---|---|
| **A. 轻发布 + 反向输血** | free tier 发布精选项目页（3D+BOM+装配+GitHub 链）+ v2.1 backlog 记录 | ~1-2 天 | ⭐ **推荐**：可逆、零成本、拿满分发与镜鉴两层价值 |
| B. 深度集成 | 双端同步维护 + Leonardo 全量文档生成 + 数据集托管 | 1-2 周+ | 否：平台太早期（~31 项目），投入产出不成比例 |
| C. 仅观察不发布 | 只偷产品设计不入驻 | 0.5 天 | 否：白白放弃早期曝光与 B2B 触达 |

## 4. 方案 A 设计

### 4.1 流程

```
T0 平台深调 → T1 资产适配包 → T2 账号+发布（用户配合）→ T3 v2.1 backlog 落档 → T4 提交汇报
```

### 4.2 T0 平台深调（只读，不注册）

- 项目页创建入口与字段清单；3D 格式（STL/STEP/GLB?）与大小限额
- BOM 导入格式（CSV schema）；GitHub 同步机制（repo 链接 vs 深度集成）
- free tier 权限边界（项目数/存储/可见性）；License 展示方式（MIT + CERN OHL-S 双声明）
- github.com/tnkrai 组织复查（Python 框架 repo 是否可复用）

### 4.3 T1 发布资产包（本地制作，`docs/tnkr/` 归档）

1. **EN one-pager**：项目简介（对标 MIT FlowIO 的国产气动软体机器人控制平台，B2B 康复手套）
2. **3D 包**：5×STL（孪生网格）+ 2×STEP（外壳可编辑源）
3. **BOM**：flowio-p1-bom-jlc.csv 原样（LCSC 编码即供应商连接）
4. **装配分步（EN）**：BRINGUP.md 9 章压缩为 8-12 步带检查项
5. **License 声明**：代码 MIT / 硬件 CERN OHL-S，双开源
6. **安全红线**：发布物中**不得含**任何密钥（PAT/天眼查 key 均在 简历/，天然隔离）；只引用 GitHub 公开内容

### 4.4 T2 账号 + 发布

- 用户动作：注册 Tnkr 账号（邮箱/GitHub OAuth，二选一，建议 GitHub OAuth）
- Agent 动作：创建项目页、填 one-pager、传 3D/BOM、连 GitHub repo、设 license
- 验收：项目页公开可访问、3D 分解可交互、BOM 可见、GitHub 链接正确

### 4.5 T3 反向输血 backlog

将 §2.2 三特性写入 `docs/superpowers/specs/` 的 twin v2.1 候选清单（含验收标准草案，引用 hotspots.json/bom-jlc.csv/BRINGUP.md 现有基础）。**若未来实施，走 using-git-worktrees 开分支**（用户已引用该技能，此处呼应）。

### 4.6 风险与对策

| 风险 | 对策 |
|---|---|
| 平台早夭（startup，~31 项目） | 轻投入：项目页可随时弃养，资产全在本地/GitHub |
| 免费层限额不明 | T0 先核实，超出则只发精简版（3D+简介+GitHub 链） |
| 英文内容工作量 | 复用专著/简历英文化的既有语料，one-pager 控制在一页 |
| 平台内容政策/审核 | 发布前人工过目（用户验收 T2） |

## 5. 验收标准

1. Tnkr 项目页上线：3D 分解可交互、BOM 可见、GitHub 双链正确、license 明示
2. 发布物零密钥泄漏（Mimosa 扫描通过）
3. v2.1 backlog 文档落档并提交 git
4. 主仓无破坏性变更（docs/tnkr/ 新增目录 + specs 新文件而已）

## 6. 开放问题（请用户审查时定夺）

1. **账号注册方式**：建议 GitHub OAuth（免新密码）——由你在 T2 操作
2. **发布内容的商业口径**：one-pager 是否明示 B2B（"面向康复手套厂商的控制板方案"）还是纯开源社区口吻？**建议：开源为主 + 一句 B2B 备注**（社区平台硬广易冷场）
3. v2.1 三特性是否排期（本期只记录；若你说"排"，我再走 brainstorming→spec 流程立项）
