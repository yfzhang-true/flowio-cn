# 资源清理与去 Tnkr 化实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: subagent-driven-development / executing-plans。
> **前置**: spec `2026-10-03-detnkr-cleanup-design.md` 获批（含决策 A/B/C 选定）。
> **说明**: 纯文档移动/删除/浏览器操作，全程 git 可回滚，不经 worktree（用户未要求）。

**Goal:** 消除 Tnkr 影响（仓库+平台+授权），校正失实表述，刷新 HANDOFF，全部入 main 并 push。

---

### Task 1: 仓库归档与工件下架

- [ ] `cd E:/FLOWIO && mkdir -p docs/archive && git mv docs/tnkr docs/archive/tnkr-2026-10 && git mv tools/serve_step_once.mjs docs/archive/tnkr-2026-10/`
- [ ] `git rm --cached hardware/flowio-p1/enclosure/flowio-p1-assembly.step`（保留本地文件）+ `printf "hardware/flowio-p1/enclosure/flowio-p1-assembly.step\n" >> .gitignore`
- [ ] 弃用横幅（Edit 头部插入）：
  - `docs/superpowers/specs/2026-10-03-tnkr-distribution-design.md`
  - `docs/superpowers/plans/2026-10-03-tnkr-distribution.md`
  - `docs/superpowers/specs/2026-10-03-tnkr-assembly-step-design.md`
  - `docs/superpowers/plans/2026-10-03-tnkr-assembly-step.md`
  - 横幅文案：`> **[已弃用 2026-10-03]** tnkr.ai 平台已放弃（展示切换 GitHub Pages）。本文仅作工程史留档，执行结论见 docs/archive/tnkr-2026-10/asset-manifest.md。`
- [ ] `twin-v2.1-backlog.md`：来源句 "Tnkr 镜鉴" → "已归档平台镜鉴（docs/archive/tnkr-2026-10/tnkr-操作手册.md）"
- [ ] `docs/archive/tnkr-2026-10/asset-manifest.md` 顶部加终局注记：平台已放弃/项目已删除/装配体工件已移出 HEAD，再生命令两条（kicad-cli + make_assembly.py，见 platform-notes）
- [ ] Commit: `chore: 去 Tnkr 化 — 档案归档+装配体工件下架+弃用横幅`

### Task 2: 简历表述校正（本地，不入 git）

- [ ] 中文简历"硬件与制造"：`用于 GitHub Pages 在线演示的 3D 拆解展示` → `供 CAD 交付与制造复核（两条命令一键重建）`
- [ ] 英文简历同条目：`powering the 3D exploded view on the GitHub Pages live demo` → `for CAD hand-off and manufacturing review (one-command regeneration)`

### Task 3: 平台侧撤除（browser-use，需用户在场可旁观）

- [ ] tnkr.ai → `/projects/settings/edb4fbab-7e85-4913-a40a-0802c2830a07/general` → 滚至 Delete Project → 点击 → 确认弹窗（若有输入确认名按提示）
- [ ] 验证：`/yuefeizzzs-workspace/flowio-cn` 返回 404/不存在
- [ ] github.com/settings/installations → Tnkr AI → Uninstall → 确认
- [ ] 验证：installations 列表无 Tnkr AI

### Task 4: HANDOFF.md 全面刷新

- [ ] 头部时间戳 → 2026-10-03 深夜；§0 重写三主线现状：
  - **产品线**：PCB 已交付 JLC 制造参数（板 5 装 2，~360-720 元）、等待实物到货 → 触发 A201-A224 硬件验收 + A301-A306 标定（= BRINGUP 30 检查项 = 专著 ch13/14 素材）
  - **展示线**：GitHub Pages 演示站上线（yfzhang-true.github.io/flowio-cn，sim_demo 对拍零误差）；构建管线 `tools/build_site.py`（改 webapp 后重跑+subtree push）；76MB 装配体已下架 HEAD（再生命令见 archive）
  - **求职线**：尽调完成（简历/公司尽调报告，乐鑫第一优先）；双简历就绪（GitHub+Live Demo 双链接）；**待用户投递**
- [ ] 铁律增补三条：ES module 裸说明符（import 必须带 ./）；Mimosa 完整扫描会拦 open(x,"w")（一律 Path.write_bytes）；GitHub 单文件 >50MB 警告/100MB 拒收
- [ ] MCP 状态：tyc-cli 已验证（尽调已毕）、mcp-jobs 已连通、aminer 有效期至 2026-10-21；Tnkr 线已关闭（archive）
- [ ] 新会话必读文件表更新（指向本次 specs/plans 与 archive）

### Task 5: 收尾

- [ ] 验收清单逐项过（spec §4 六条）
- [ ] `git add -A && git commit -m "docs: HANDOFF 刷新至 2026-10-03（三主线现状+新铁律）" && git push origin main`
- [ ] 汇报：删除截图/验收结果/回滚方式（`git revert` 两提交或恢复 archive 目录）

---

**执行注记（执行时填写）:**
- 决策 A/B/C 用户选定：____
- Tnkr 项目删除验证：____ · App 卸载验证：____
- 异常记录：____
