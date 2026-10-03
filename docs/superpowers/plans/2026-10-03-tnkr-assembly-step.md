# Tnkr 主模型升级实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: subagent-driven-development / executing-plans。
> **前置**: spec `2026-10-03-tnkr-assembly-step-design.md` 获批 · REQUIRED: using-git-worktrees（Task 0 建隔离工作区）

**Goal:** 生成 PCB+顶盖+底壳合并装配体 STEP，升级为 Tnkr 主模型，并补全 Documentation。

**Architecture:** 三段流水线（kicad-cli 导出 → FreeCAD 合并 → 入库同步平台）；全部仓库改动在 `.worktrees/tnkr-assembly` 隔离分支完成；平台侧操作走 browser-use。

**Tech Stack:** kicad-cli 10.0 · FreeCADCmd 1.1（E:/FreeCAD/bin/）· git worktree · browser-use。

---

### Task 0: Worktree 隔离工作区

- [ ] `cd E:/FLOWIO && git check-ignore -q .worktrees || echo ".worktrees/" >> .gitignore && git add .gitignore && git commit -m "chore: ignore .worktrees"`
- [ ] `git worktree add .worktrees/tnkr-assembly -b tnkr/assembly-step`
- [ ] 基线：`"E:/FreeCAD/bin/FreeCADCmd.exe" .worktrees/tnkr-assembly/hardware/flowio-p1/enclosure/check_case.py`（或以 python 直跑）→ 通过才继续
- [ ] 记录 worktree 路径与基线结果

### Task 1: PCB STEP 导出（A 段）

**Files:**
- Create（工件）: `hardware/flowio-p1/fab/flowio-p1.step`

- [ ] 命令（worktree 内执行）:
```bash
cd E:/FLOWIO/.worktrees/tnkr-assembly
"E:/Program Files/KiCad/10.0/bin/kicad-cli" pcb export step \
  --force -o hardware/flowio-p1/fab/flowio-p1.step \
  hardware/flowio-p1/flowio-p1.kicad_pcb
```
- [ ] 验证：`ls -la hardware/flowio-p1/fab/flowio-p1.step`（预期 1-10 MB）；用 FreeCAD 一行脚本数 solid：
```bash
"E:/FreeCAD/bin/FreeCADCmd.exe" -c "import Import; s=Import.read('hardware/flowio-p1/fab/flowio-p1.step'); print(len(s.RootObjects))"
```
- [ ] 判定：solid ≥ 数十（板+元件）→ 完整版；≈1（仅板）→ 记录元件 3D 体缺失，按 spec §4.1 走降级
- [ ] 若降级重试：补 KiCad 环境变量 `KICAD8_3DMODEL_DIR`/`KICAD9_3DMODEL_DIR` 指向 `E:/Program Files/KiCad/10.0/share/kicad/3dmodels` 后重跑一次；仍缺则接受降级并记录

### Task 2: 合并装配脚本（B 段）

**Files:**
- Create: `hardware/flowio-p1/enclosure/make_assembly.py`（用 Write 工具写源码）
- Create（工件）: `hardware/flowio-p1/enclosure/flowio-p1-assembly.step`
- Create（工件，可选）: `hardware/flowio-p1/enclosure/flowio-p1-assembly.stl`

- [ ] 脚本要点（FreeCADCmd 运行）：
  1. `Import.read()` 三个 STEP：fab/flowio-p1.step、enclosure/case-bottom.step、enclosure/case-top.step
  2. 定位：读 standoffs.txt 柱高（PCB 悬浮高度）；case-bottom 原位；PCB 置于柱顶；case-top 平移至闭合位（参数与 make_case.py 的 lid 偏移一致——先读 make_case.py 提取常量）
  3. 合成 compound → 导出 STEP；顺带导出 STL（spec §4.2 默认做）
  4. 断言：装配体包围盒 X/Y ≈ 外壳外形（从 make_case.py 常量），Z = 底+高+顶盖厚，容差 ±2mm；不满足则退出码非零
- [ ] 运行 + 断言通过
- [ ] 目视：将装配体 STEP 拖入数字孪生本地页或 FreeCAD 截图留档 `enclosure/assembly_preview.png`
- [ ] Commit: `git add hardware/flowio-p1/enclosure/make_assembly.py hardware/flowio-p1/enclosure/flowio-p1-assembly.* hardware/flowio-p1/fab/flowio-p1.step && git commit -m "feat(enclosure): 合并装配体 STEP（PCB+顶+底）供 Tnkr 主模型"`

### Task 3: 合回 main + 推送

- [ ] `cd E:/FLOWIO && git merge tnkr/assembly-step --no-ff -m "merge: Tnkr 装配体主模型流水线"`
- [ ] `git push origin main`（Tnkr Files 同步的触发源）
- [ ] 清理：`git worktree remove .worktrees/tnkr-assembly && git branch -d tnkr/assembly-step`（finishing-a-development-branch 收尾）

### Task 4: Tnkr 主模型更换（browser）

- [ ] 认领用户持有的项目页标签（`browser.user.openTabs()` 匹配 tnkr.ai）；无则新开
- [ ] 打开 `https://tnkr.ai/yuefeizzzs-workspace/flowio-cn` → **Manage** → 找主 STEP/3D 模型设置项
- [ ] 改选 `flowio-p1-assembly.step`（若 Files 区未同步到新 commit，找 re-sync 入口或等待平台轮询）
- [ ] 若 Manage 无更换入口 → 执行退路：记录"主模型维持 case-top，装配体在 Files 区"，写入 asset-manifest
- [ ] 验证：Overview 出现 canvas（3D viewer），截图留档

### Task 5: Documentation 补全（browser）

- [ ] 读 Documentation 标签当前内容（Leonardo 是否已生成）
- [ ] 判定：有实质装配文档 → 仅核对；空/劣 → 进入编辑模式粘贴 `docs/tnkr/assembly-steps-en.md` 内容（10 步 + A201-A302 票号）
- [ ] 发布并验证公开可见

### Task 6: 档案回填 + 汇报

- [ ] 回填 `docs/tnkr/asset-manifest.md`（主模型状态/Documentation 状态/装配体路径）
- [ ] 回填 spec 执行注记（降级与否、solid 数、尺寸断言值）
- [ ] Commit 文档 + 向用户汇报（含项目页最终截图）
