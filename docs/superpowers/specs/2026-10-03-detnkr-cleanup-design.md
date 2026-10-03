# 资源清理与去 Tnkr 化 — 设计规格书

> **日期**: 2026-10-03 · **状态**: 待用户审查
> **决策背景**: 用户已决定放弃 tnkr.ai 平台（其机器人专属功能与气动控制器不适配），展示主阵地切换为 GitHub + GitHub Pages（已上线）。本期清理 Tnkr 残留影响并整理项目资源。

---

## 1. 影响面盘点（2026-10-03 实测）

| # | 落点 | 内容 | 处置方向 |
|---|---|---|---|
| 1 | `docs/tnkr/`（6 文件） | 平台备忘/one-pager/装配指南/资产清单/runbook/操作手册 | 归档保留 |
| 2 | superpowers specs/plans ×4 | Tnkr 分发、装配体升级两对（另有 Pages 一对为背景引用） | 历史保留+弃用横幅 |
| 3 | `tools/serve_step_once.mjs` | Tnkr 专用上传突破工具 | 随档归档 |
| 4 | `hardware/flowio-p1/enclosure/flowio-p1-assembly.step`（**76MB**） | Tnkr 主模型工件；**site/ 零引用**（demo 用 meshes/*.stl） | 移出 HEAD（脚本可再生成） |
| 5 | 中英简历各 1 处 | "装配体 STEP 用于 GitHub Pages 演示的 3D 拆解展示"——**失实**（demo 用 5 个 STL） | 校正表述 |
| 6 | tnkr.ai 平台 | 项目页 + 描述导流 | 删除项目 |
| 7 | GitHub 账号 | **Tnkr AI App 安装授权**（对 flowio-cn 只读） | 卸载授权（安全卫生） |
| 8 | `HANDOFF.md` | 停在 2026-10-01 PCB 时代，缺 Pages/尽调/求职/发布全貌 | 全面刷新 |
| 9 | 简历/Tnkr 字样 | 已零残留（上轮完成） | 无需动作 |

## 2. 方案比选（三个关键决策）

### 决策 A：tnkr.ai 平台项目——删除 vs 留作导流页

- **推荐：删除**（Settings→Delete Project，一键且不可逆但无价值损失）。理由：用户明示"消除影响"；导流价值≈0（平台 ~31 项目无自然流量）；保留=持续的心智负担与维护幻觉。
- 备选：保留导流页（零成本），仅在用户仍看好平台期权时选。

### 决策 B：76MB 装配体 STEP——移出 HEAD vs 保留

- **推荐：移出 HEAD**（`git rm --cached` + .gitignore）。理由：无任何代码/站点引用；76MB 让每次 clone/checkout 白背；`make_assembly.py` 一键再生（两条命令：kicad-cli 导出 + FreeCAD 合并）。
- 诚实声明：git **历史**中该 blob 永久存在（仓库 .git 已 4GB，非它主导）；彻底清除需 history 重写（filter-repo），成本高且改写所有 commit hash——**本期不做**，列为可选未来项。
- 保留物：make_assembly.py / inspect_pcb.py（制造与 CAD 复核价值独立于 Tnkr）。

### 决策 C：docs/tnkr/ ——归档 vs 物理删除

- **推荐：归档至 `docs/archive/tnkr-2026-10/`**。理由：装配指南/操作手册内容仍有复用价值（onepager-en 是现成英文项目介绍）；工程决策史是"200+ commits 可追溯"叙事的一部分；specs 交叉引用不断链。
- 备选：彻底删除（最干净，牺牲历史）。

## 3. 具体动作清单

### 3.1 仓库侧（本地 git 操作，全程可回滚）

1. `git mv docs/tnkr docs/archive/tnkr-2026-10` + `git mv tools/serve_step_once.mjs docs/archive/tnkr-2026-10/`
2. 两对 Tnkr spec/plan 头部加 `> **[已弃用 2026-10-03]** 平台已放弃，本文仅作工程史` 横幅；twin-v2.1-backlog 保留（价值独立），来源注记改"已归档的 Tnkr 镜鉴（docs/archive/）"
3. `git rm --cached hardware/flowio-p1/enclosure/flowio-p1-assembly.step` + .gitignore 追加该路径；asset-manifest 增终局注记（工件下架、再生命令）
4. Pages spec/plan 中的 Tnkr 背景段**保留原文**（历史事实，不改写）

### 3.2 简历侧（本地文件，不入 git）

中英简历"硬件与制造"条目校正为真实表述：装配体 STEP 定位改为"**CAD 交付与制造复核**（557 零件一键重建）"，与 Pages 演示解耦。

### 3.3 平台侧（browser-use）

1. tnkr.ai → 项目 Settings→General→底部 **Delete Project** → 确认
2. github.com/settings/installations → **Tnkr AI** → Uninstall（收回对 flowio-cn 的只读授权）

### 3.4 整理侧

**HANDOFF.md 全面刷新**至 2026-10-03 深夜现状：
- §0 一句话现状：产品线（板待 JLC 到货）/ 展示线（Pages 上线+构建管线）/ 求职线（尽调完成、简历就绪、待投递）
- 已完成/待办清单重写（对齐 A201-A302 验收票体系）
- 铁律增补：ES module 裸说明符陷阱、Mimosa `Path.write_bytes` 拦截、GitHub >50MB 警告线
- MCP 状态更新（tyc/mcp-jobs 已验证；tnkr 线关闭）

## 4. 验收标准

1. `grep -rn "tnkr" --include="*"` 在**活跃目录**（docs/ 除 archive、tools、site、firmware、hardware、README）零命中；archive/ 与 specs 历史横幅除外
2. tnkr.ai 项目页 404；GitHub App installations 列表无 Tnkr AI
3. HEAD 中无 flowio-p1-assembly.step；`git status` 干净；clone 后工作树不含该文件
4. 中英简历无"Tnkr"字样且装配体表述与事实一致
5. HANDOFF.md 时间戳为 2026-10-03，含三大主线现状
6. main 已 push；操作全程 git 可回滚

## 5. 开放问题（审查时定夺）

1. 决策 A：Tnkr 项目**删除**（推荐）还是留作导流？
2. 决策 B：76MB 工件**移出 HEAD**（推荐）？历史级清除（filter-repo）确认本期不做？
3. 决策 C：docs/tnkr **归档**（推荐）还是彻底删除？
