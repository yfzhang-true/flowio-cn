# Tnkr 平台操作手册（用户视角）

> **版本**: 2026-10-03（平台早期，UI 可能随时变化）· **作者**: 基于对 tnkr.ai 的逐标签实机探索
> **背景**: 官方无网页平台手册（github.com/tnkrai/studio-docs 仅覆盖桌面端 Tnkr Studio）
> **实测项目**: FLOWIO-CN（/yuefeizzzs-workspace/flowio-cn，ID edb4fbab-7e85-4913-a40a-0802c2830a07）

---

## 1. 平台地图（三层结构）

```
公开层（访客所见）
  /explore                    项目广场（按 formFactor 分类浏览：hands/arms/humanoids/quadrupeds/drones/droids/bipeds）
  /{workspace}/{project}      项目公开页（Overview/Documentation/Files/Merge Requests/Mods/Help Center）
                             ⚠️ 文档需 Publish 后才在此可见；3D viewer 需平台后台转换完成

工作台层（登录后）
  /overview                   个人仪表盘（新手 5 步引导、Leo 全局聊天——限额 10 条/天）
  /projects                   项目管理列表（Makers/Kits 标签；Kits 需条件解锁）
  /builds                     Agents（连接实体机器人；Add Agent = 档案向导）
  /overview/settings/*        工作区设置（General 改组织名/Billing/Integrations）

项目后台层（维护者专用，公开页不可见！）
  /projects/home/{id}             项目控制台（7 步设置清单、活动流、MR 列表）
  /projects/central-docs/{id}     文档编辑器（左侧文档树 + 富文本 + Publish）
  /projects/hardware-docs/{id}    ★ 硬件工作台（Explorer/Assembly/Simulation/Wiring/BOM 五标签 + 3D 视口）
  /projects/file-management/{id}  文件管理
  /projects/settings/{id}/general 项目设置（含 Replace STEP / Delete Project！）
```

**关键认知**：公开项目页的 "Manage" 按钮只是贡献者管理弹窗——真正的管理入口是 `/projects/home/{项目ID}` 路由（从 /projects 列表点项目卡片进入）。

## 2. 建项目全流程（GitHub 导入路径，推荐）

1. 注册/登录（GitHub OAuth 一键）
2. 工作台 Integrations → **GitHub** → Connect → 安装 GitHub App（**选 "Only select repositories" 最小权限**，只勾目标仓库；权限为只读）
3. `/projects/add-project` → **Connect to GitHub**
4. 选仓库 → **Select STEP File**：平台扫描仓库内全部 STEP，要求**恰好选 1 个主模型**（≤100MB）
5. Project Details：名称（定 slug）/描述（≤350 字符，建议含双 license 声明）/Form Factor（可多选）/Visibility=Public → Create Project
6. Leonardo 自动后台处理（文档导入、3D 转换——异步，需等待）

**经验**：仓库里放一个多 solid 装配体 STEP 作为主模型（我们用 557 零件装配体），零件分解视图才有料。

## 3. 七步设置清单（Setting up ...）

| # | 步骤 | 完成方法 | FLOWIO-CN 实况 |
|---|---|---|---|
| 1 | Describe what you're building | Settings→General 的名称+描述 | ✅ |
| 2 | Bring in your code | GitHub App 安装 | ✅ |
| 3 | Bring in your CAD | 导入时选 STEP / 后续原位替换 | ✅ |
| 4 | Add your bill of materials | Hardware Docs→BOM 标签 | ✅ 34 项 |
| 5 | Create your assembly instructions | Hardware Docs→Assembly 标签 | ⏸ 4 阶段待完善 |
| 6 | Connect your robot | Agents→Add Agent + 桌面端 Tnkr Studio 配对 | ⏸ 等板子到货 |
| 7 | Publish your build | Central Docs→Publish + 各项就绪 | ⏸ |

## 4. 硬件工作台（/projects/hardware-docs/{id}?mode=edit）

左侧五标签：

- **Explorer**：3D 视口（OCCT 引擎解析 STEP）。六正视/轴测、Save view（保存机位）、**Properties/Annotations 面板**（选中零件后编辑属性/加标注——零件注释的官方实现）
- **Assembly**：装配阶段编辑器。"Add an Assembly Phase" 建阶段 → 每阶段命名/描述/绑定零件与步骤（3D 标注动画）。⚠️ 标题编辑后要点工具栏 **Save** 才持久化
- **Simulation**：拖入仿真文件夹（支持 .urdf/.xacro/.stl/.dae/.obj）或 Import from Onshape
- **Wiring**：连线图画布——"Create your first wiring board" 从 BOM 拖零件画连接图；也有 Generate with Leo
- **BOM**：核心表。**Generate（Leo 起草）/ Import CSV / Add Part / Export CSV / Create Kit（套件上架！）**。BOM INFO 卡显示 总件数/唯一数/供应商数/库存数/预估成本（价格需手填）
  - **Leo 录 BOM 实测有效法**：Leo 读不到仓库文件，但它接受**直接粘贴的行**——格式 `MPN | qty N | LCSC C-number`，一次贴 33 行全部录入成功
  - 每天全局 Leo 限额 10 条（所有聊天共享），省着用

## 5. 文档系统（/projects/central-docs/{id}）

- 预置文档树：Introduction/Overview · Hardware（Print Guide/BOM/Assembly Instructions/Electronics & Wiring/Troubleshooting）· Software · Deployments；可 New Page/New Section/Add custom page
- **Edit** 模式：contenteditable 富文本（粘贴/selectAll+insertText 均可）；**Preview** 预览；**Publish** 发布（发布后公开页 Documentation 可见，3D canvas 随之渲染）
- 页面有 Draft/Copy page/Version history 状态管理

## 6. 项目设置（/projects/settings/{id}/general）

- 名称/描述/Form Factor/缩略图（可 **Generate from 3D model** 自动生成）/可见性/合并贡献者策略
- **Replace STEP file（原位替换主模型）**：上传新 STEP（≤100MB）→ "Analyze new model"（平台转换并比对零件结构，给出 added/removed/changed 与安全性判定）→ "Replace model"。**URL 与文档保持不变**
- **Delete Project**：页面底部（删除项目及全部文档设置——慎用）
- Members / Integrations / Customization（品牌色/字体/logo/URL）

## 7. 已验证的自动化技巧（本项目沉淀）

1. **绕过浏览器上传限制**（agent 场景）：本地起 CORS+PNA 服务器（`tools/serve_step_once.mjs`）→ 页面 fetch localhost 构造 File → DataTransfer 赋值 `input[type=file].files` → 派发 change——STEP/CSV/图片上传通用
2. **点击被拦截**：cookie 横幅会覆盖按钮致 Playwright 超时——先 dom_cua 关横幅；SPA 按钮 actionability 死锁时用页面内原生 `element.click()`
3. **FreeCADCmd 中文脚本**：报"not readable"，用 `exec(compile(open(p,encoding='utf-8').read(),p,'exec'),{'__file__':p})` 绕过
4. **KiCad 导出全元件 STEP**：需 `KICAD9_3RD_PARTY` 环境变量指向第三方模型目录，否则 JLC 元件 3D 体静默丢失

## 8. 已知坑与限制（截至 2026-10-03）

- 公开页 Leo 常答"未加载项目"（alpha bug）；BOM/Wiring 上下文的 Leo 可用
- 文件选择器为原生对话框（自动化不可达，见 §7.1 技巧）
- Files 区从 GitHub 自动同步（推送后延迟轮询，非即时 webhook）
- Export CSV 下载在应用内浏览器可能被吞（建议直接用 Leo 粘贴法或 Import）
- Wiring 的 Leo 起草会自作主张放种子板（如 Seeed Xiao）——需人工核对
- Kits 标签 disabled（解锁条件未知，先例：XLeRobot $550 / Duck $600）

## 9. 与本地工程的联动约定（FLOWIO-CN 专用）

- GitHub main = 唯一权威源；Tnkr 只是展示/文档/BOM/社区层
- 主模型：`hardware/flowio-p1/enclosure/flowio-p1-assembly.step`（76MB，557 solids，`make_assembly.py` 一键再生）
- BOM 源：`hardware/flowio-p1/fab/flowio-p1-bom-jlc.csv`（39 行→合并 33 唯一行录入平台）
- 装配阶段蓝本：`docs/tnkr/assembly-steps-en.md`（10 步 + A201-A302 票号）
- 待办：① 装配阶段标题/描述补全（目视操作 2 分钟）② 板到货后装 Tnkr Studio 连机器人 ③ Kits 解锁后上架套件
