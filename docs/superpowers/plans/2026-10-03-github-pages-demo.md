# GitHub Pages 数字孪生展示站实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: subagent-driven-development / executing-plans。
> **前置**: spec `2026-10-03-github-pages-demo-design.md` 获批 · worktree: `.worktrees/pages-demo`（分支 `pages/demo-site`）

**Goal:** 零后端可交互数字孪生演示站上线 `yfzhang-true.github.io/flowio-cn`，并完成简历/README/Tnkr 引用切换。

**Architecture:** webapp 源不动；`site/` 为构建产物源（fetch 拦截层 + JS 仿真移植 + 固化数据）；gh-pages 分支部署。

**Tech Stack:** 原生 JS（three.js r160 vendor 已有）· Python 构建脚本 · git subtree · GitHub Pages。

---

### Task 0: Worktree

- [ ] `git worktree add .worktrees/pages-demo -b pages/demo-site`（.worktrees 已 ignore）
- [ ] 基线：`ls firmware/twin/webapp/js` 7 模块在位；`python firmware/twin/server.py --help` 或端口探测确认本地服务可起

### Task 1: 移植 sim_demo.js（4 电路）

**Files:**
- Reference: `firmware/twin/sim_engine.py`（356 行）
- Create: `site/js/sim_demo.js`

- [ ] 逐函数移植：`_check` 参数校验、`_buck/_diode_i/_dior/_valve/_i2c`、`_wave/_metric/_dec` 输出结构
- [ ] `SIM_PRESETS` 常量 = presets 端点输出（从本地 server 抓取固化）
- [ ] 模块导出 `window.SimDemo = { presets, run(circuit, params) }`
- [ ] 一致性自测：内置 3 组参数的期望输出（从 Python 版跑出写入 `site/js/sim_test_data.json`），页面加载时 console.assert 相对误差 <5%

### Task 2: demo_api.js（fetch 拦截层）

**Files:**
- Create: `site/js/demo_api.js`

- [ ] 在 `window.fetch` 包装：匹配 `/api/*` 路由到本地实现（行为表见 spec §4.2），其余透传
- [ ] 时序合成器：`setInterval` 20Hz 产 board/state 与 state（气动压力正弦+目标漂移、电气量挂钩当前 sim 结果），600s 环形缓冲
- [ ] cmd/record/time 内存实现；无 `navigator.bluetooth` 时 body 加 `no-ble` 类隐藏 BLE 入口
- [ ] index.html 于 main.js 之前注入 `demo_api.js` 与 `sim_demo.js`

### Task 3: 构建脚本 build_site.py

**Files:**
- Create: `tools/build_site.py`

- [ ] 步骤：① 起本地 server.py（子进程）② 抓 `/api/board/assembly` → `site/data/assembly.json` ③ 拷贝 webapp/{js(除注入顺序调整),css,vendor,index.html,meshes 上溯一级} → `site/` ④ index.html 资产路径相对化（去 `/webapp/`、`/api/` 前缀）+ 注入 demo 脚本 ⑤ 断言：site/ 内无 `简历`、无 `ghp_`/`mcpk2_` 模式、无 .kicad_pcb 等大文件泄漏
- [ ] 幂等：重跑覆盖；产物不写入 firmware/twin 源

### Task 4: 本地验收（对照 spec §6）

- [ ] `python -m http.server -d site 8080` → 打开 `http://localhost:8080/`（子路径模拟：`http-server` 下再套 `/flowio-cn/` 目录验证相对路径）
- [ ] 浏览器验收（browser-use）：3D 渲染、爆炸滑杆、SimLab 四电路滑杆实时重算、控制台零 `/api/` 报错、sim 一致性 console.assert 通过
- [ ] Commit（分支内）

### Task 5: 部署

- [ ] `tools/deploy_site.ps1`：`git subtree split --prefix=site -b gh-pages` → 强推 gh-pages → `gh api repos/yfzhang-true/flowio-cn/pages -X POST -f source[branch]=gh-pages`（或提示用户在 Settings→Pages 手选）
- [ ] 等 Pages 构建绿（`gh api repos/.../pages/builds`）→ 记录最终 URL
- [ ] main 合并 `pages/demo-site` + push

### Task 6: 引用切换

- [ ] README 顶部：Demo 徽章 + 链接
- [ ] 中英简历：Tnkr 行 → `Live Demo: https://yfzhang-true.github.io/flowio-cn`（描述改为 3D 爆炸+实时气流/电流+可调仿真）；"发布于 Tnkr" 措辞 → "GitHub Pages 在线演示"（简历/ 本地文件，Edit 工具）
- [ ] Tnkr 项目描述尾部追加 "Live demo: <url>"（browser-use，Settings→General→描述 350 字内追加）
- [ ] `docs/tnkr/asset-manifest.md` 追加弃用注记 + 指向本 spec
- [ ] Commit + 汇报（含 Pages URL 与本地验收截图路径）
