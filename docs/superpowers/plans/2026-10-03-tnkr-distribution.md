# Tnkr 平台接入实施计划（评估结论：轻发布 + 反向输血）

> **[已弃用 2026-10-03]** tnkr.ai 平台已放弃（展示切换 GitHub Pages）。本文仅作工程史留档，执行结论见 docs/archive/tnkr-2026-10/asset-manifest.md。

> **For agentic workers:** REQUIRED SUB-SKILL: subagent-driven-development / executing-plans。
> **前置**: spec `2026-10-03-tnkr-distribution-design.md` 已获用户批准。

**Goal:** 在 Tnkr（tnkr.ai）发布 FLOWIO-CN 精选项目页（3D + BOM + 装配 + GitHub 链），并把 Tnkr 产品形态反哺为孪生 v2.1 backlog。

**Architecture:** 纯增量文档/内容工作，不动主仓代码；新目录 `docs/tnkr/` 归档全部发布物；GitHub 保持唯一权威源，Tnkr 仅展示导流。

**Tech Stack:** WebFetch（平台考察）/ 本地资产（5×STL + 2×STEP + bom-jlc.csv）/ markdown。

---

### Task 1: T0 平台深调（只读考察，产出备忘）

**Files:**
- Create: `docs/tnkr/platform-notes.md`

- [ ] 抓取并记录（WebFetch，仅 https、校验 host 为 tnkr.ai/github.com）：
  - 项目页创建入口 URL、必填字段清单
  - 3D 上传：接受格式（STL/STEP/GLB）、单文件/总大小限额
  - BOM 导入：CSV/模板 schema
  - GitHub 集成：是链接还是深度同步（能否自动读 README/releases）
  - free tier 边界：项目数/存储/公开性；付费墙在哪一步出现
  - license 展示方式（能否双声明 MIT + CERN OHL-S）
  - github.com/tnkrai 组织页复查（Python 框架 repo 清单）
- [ ] 将以上写入 `docs/tnkr/platform-notes.md`（表格化，每条注明来源 URL 与抓取时间）
- [ ] 若 3D 限额 < 现有 STL 总大小：记录各 STL 文件大小（`ls -la firmware/twin/meshes/`），给出压缩/取舍建议
- [ ] Commit: `git add docs/tnkr/platform-notes.md && git commit -m "docs(tnkr): 平台深调备忘"`

### Task 2: T1a 英文 one-pager 撰写

**Files:**
- Create: `docs/tnkr/onepager-en.md`

- [ ] 写入以下完整内容（发布正文，开源社区口吻 + 一句 B2B 备注，见 spec §6.2 建议口径）：

```markdown
# FLOWIO-CN — Open Pneumatic Soft-Robotics Control Platform

An independently engineered, fully open-source alternative to MIT's FlowIO:
a complete "brain upgrade" for pneumatic soft robots, built around ESP32-S3.

**What it is**
- 4-layer PCB (90×75 mm) designed in KiCad, DRC-clean, JLC-ready SMT package
  (107 parts, 100% LCSC-coded BOM)
- ESP-IDF / FreeRTOS firmware with a platform-independent C core (pn_core):
  8-channel PWM valve drive, TCA9548A I2C mux, WS2812 RMT, NimBLE GATT
- Python SDK (0xA5 protocol, CRC-8, cross-verified against firmware vectors)
- Web digital twin: Three.js exploded view with live airflow/current
  visualization, 4-circuit physics simulation, BLE console
- Five-layer test automation: 181 cases, 200+ assertions
- 94-page LaTeX book (31 references) documenting the whole build

**Why it matters**
Soft robotics needs an affordable, hackable controller. FLOWIO-CN brings
that to rehabilitation gloves, lab research, and embodied-AI data collection
— at a B2B kit price of ¥300–500 (comparable to one dinner, not one grant).

**Licenses**: code MIT · hardware CERN OHL-S
**Source of truth**: github.com/yfzhang-true/flowio-cn
```

- [ ] Commit: `git add docs/tnkr/onepager-en.md && git commit -m "docs(tnkr): EN one-pager"`

### Task 3: T1b 装配分步（EN，源自 BRINGUP.md）

**Files:**
- Create: `docs/tnkr/assembly-steps-en.md`
- Reference: `firmware/BRINGUP.md`（9 章 30 检查项）

- [ ] 按 BRINGUP 章节压缩为 10 步，每步 = 标题 + 检查项（checkbox），步骤骨架：
  1. Visual inspection & power rail resistance (no smoke test)
  2. Bench supply bring-up at 3.3 V (buck output check, A201 scope)
  3. Program ESP32-S3 via UART (build_n16r8.ps1, console boot log)
  4. I2C bus scan through TCA9548A (A203: 8 channels enumerated)
  5. Sensor readout (pressure/temperature, A205)
  6. PWM valve drive sweep (A206: 8 channels, duty sweep)
  7. WS2812 status LEDs (A207)
  8. BLE GATT connect + telemetry (A208, Web Bluetooth console)
  9. Closed-loop pressure PID first run (A301, calibrated setpoints)
  10. End-to-end: glove inflation profile via SDK + digital twin replay (A302)
- [ ] 每步附对应验收票号（A201–A302），与仓库 tickets/ 体系一致
- [ ] Commit: `git add docs/tnkr/assembly-steps-en.md && git commit -m "docs(tnkr): EN assembly steps"`

### Task 4: T1c 资产清单 + 安全检查

**Files:**
- Create: `docs/tnkr/asset-manifest.md`

- [ ] 清单内容（路径 + 用途 + 处理方式）：
  - `firmware/twin/meshes/*.stl`（5 个）→ 上传 3D viewer
  - `hardware/flowio-p1/enclosure/*.step`（2 个）→ 可编辑 CAD 源
  - `hardware/flowio-p1/fab/flowio-p1-bom-jlc.csv` → BOM 导入（LCSC 编码 = 供应商连接）
  - `docs/tnkr/onepager-en.md` / `assembly-steps-en.md` → 项目页正文
  - GitHub repo URL + license 双声明
- [ ] 安全扫描：对上述待发布文件运行密钥模式检查（PAT `ghp_`、`mcpk2_` 前缀 grep），预期零命中；`简历/` 目录不进入任何发布物
- [ ] Commit: `git add docs/tnkr/asset-manifest.md && git commit -m "docs(tnkr): 发布资产清单与安全检查"`

### Task 5: T2 账号注册 + 项目页发布（需用户配合）

- [ ] **用户动作**：注册 Tnkr 账号（建议 GitHub OAuth），告知 agent 已完成
- [ ] 依 Task 1 findings 选路径：
  - 若平台支持 GitHub repo 导入/CLI → agent 直接执行导入 + 字段填充
  - 若仅 Web 表单 → agent 用 browser-use 技能辅助填写（或提供 copy-paste 包由用户手动贴入）
- [ ] 发布字段核对单：标题/one-pager 正文/3D×7/BOM/license 双声明/GitHub 链
- [ ] 验收：项目页公开 URL 可访问、3D 分解可交互、BOM 表可见、GitHub 链接正确、license 明示
- [ ] 把项目页 URL 记入 `docs/tnkr/asset-manifest.md` 尾部 + Commit

### Task 6: T3 孪生 v2.1 反向输血 backlog 落档

**Files:**
- Create: `docs/superpowers/specs/2026-10-03-twin-v2.1-backlog.md`

- [ ] 写入三特性（每条含：动机/Tnkr 镜鉴来源/现有基础/验收标准草案）：
  1. **零件注释**：点击零件 → 弹出文档/规格/BOM 行（基础：`firmware/twin/webapp/hotspots.json` 已存在；验收：点击 5 个 STL 任一部件显示对应 BOM 行与 datasheet 链接）
  2. **BOM 面板 + 供应商直链**：侧栏 107 行 LCSC 编码可点（基础：`flowio-p1-bom-jlc.csv`；验收：面板渲染 107 行、编码跳转 lcsc.com 正确）
  3. **分步装配模式**：爆炸滑杆按 assembly-steps 步进、每步高亮零件 + 检查项（基础：scene.js explode + assembly-steps-en.md；验收：10 步导航与 BRINGUP 票号一致）
- [ ] 注明：实施时走 using-git-worktrees 开分支 + 完整 brainstorming→spec→plan 流程
- [ ] Commit: `git add docs/superpowers/specs/2026-10-03-twin-v2.1-backlog.md && git commit -m "docs: twin v2.1 反向输血 backlog（Tnkr 镜鉴）"`

### Task 7: 收尾汇报

- [ ] 向用户汇报：平台备忘要点 / 发布 URL（或待用户注册）/ v2.1 backlog 位置 / 主仓变更清单
- [ ] 提醒 spec §6 三个开放问题的答复（账号方式、B2B 口径、v2.1 是否排期）
