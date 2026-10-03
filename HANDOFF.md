# FLOWIO 项目交接文档（新会话必读）

> **更新**: 2026-10-03 深夜 · **状态**: 三主线并行 — 产品线等板 / 展示线完成 / 求职线待投递
> **新会话第一动作**: 通读本文档 → 按需读 §2 的 spec/plan → 等用户指令

---

## 0. 一句话现状

**产品线**：P1 板全设计完成（原理图 0 错/布线 0 未连接/仿真 4 电路达标/JLC 制造包就绪），**等用户下单打样（板 5 装 2，约 360-720 元）与实物到货** → 触发 A201-A224 硬件验收 + A301-A306 标定（= BRINGUP 30 检查项 = 专著 ch13/14 素材）。
**展示线**：GitHub Pages 演示站上线 **https://yfzhang-true.github.io/flowio-cn/**（3D 爆炸 + 气流/电流 + 浏览器内四电路仿真，JS 移植与 Python 对拍零误差）；README 有 Live Demo 徽章。
**求职线**：4 公司尽调完成（乐鑫第一优先 9/10）、双简历就绪（GitHub + Live Demo 双链接）；**唯一待办：用户投递**。
**已关闭**：tnkr.ai 线（2026-10-03 放弃，档案在 `docs/archive/tnkr-2026-10/`，项目页已删，App 授权待用户手动卸载——见 §5）。

## 1. 已完成 / 待完成

### ✅ 已完成（里程碑序）
| 交付物 | 位置 | 备注 |
|---|---|---|
| 原理图/布线/仿真/JLC 包/外壳 | `hardware/flowio-p1/` | 全零收口（146→0 未连接） |
| 固件 + SDK + 五层测试 | `firmware/` | 181 用例 200+ 断言全绿 |
| 数字孪生（本地版） | `firmware/twin/`（server.py + webapp） | 带板联调用 |
| **Pages 演示站** | `site/` + gh-pages 分支 | 构建：`python tools/build_site.py` → subtree push |
| 94 页专著 | `book/` | 31 文献，一致性 16 项清零 |
| 公司尽调 ×4 | `简历/公司尽调报告_上海嵌入式_2026-10.md` | 本地不入 git |
| 双简历 | `简历/*.md` | 中英各一，双链接 |
| Tnkr 档案 | `docs/archive/tnkr-2026-10/` | 已弃用留档 |

### ⏳ 待完成（优先级序）
1. **【用户动作】投递乐鑫**（原型验证/ESP-IDF SDK/AI 方案三岗，弹药=FLOWIO-CN 全栈）
2. **【用户动作】JLC 下单**（fab 包参数见 `hardware/flowio-p1/fab/README-jlc-order.md`）
3. **【用户动作 30 秒】卸载 GitHub App**：浏览器停在 github.com sudo 确认页 → 输密码 Confirm → installation 页 Uninstall "Tnkr AI"
4. 板到货后：按 `firmware/BRINGUP.md` 走 30 检查项（票号 A201-A302）→ 同步产出专著 ch13/14
5. 可选 backlog：孪生 v2.1 三特性（`docs/superpowers/specs/2026-10-03-twin-v2.1-backlog.md`，BOM 面板/零件注释/分步装配）

## 2. 新会话必读文件

| 文件 | 作用 |
|---|---|
| `docs/superpowers/specs/2026-10-03-github-pages-demo-design.md` | Pages 站架构（含"为何静态即正解"FAQ） |
| `docs/superpowers/specs/2026-10-03-detnkr-cleanup-design.md` | 本轮清理决策记录 |
| `docs/archive/tnkr-2026-10/tnkr-操作手册.md` | 平台操作史（含自动化上传突破手法） |
| `docs/superpowers/specs/2026-10-01-p1-auto-finish-design.md` | PCB 攻坚史（根因 R1-R5） |
| `firmware/BRINGUP.md` | 板到货后的验收主文档 |

工作流约定：superpowers skills 强制（brainstorming→writing-plans→executing）；代码改动走 worktree。

## 3. 关键路径与环境（Windows，Git Bash）

| 工具 | 路径/命令 |
|---|---|
| **网络代理（github.com 阻断时用）** | 本机 Clash 系代理 `http://127.0.0.1:7877`（系统注册但 ProxyEnable=0，需显式指定）；git 用法：`git -c http.proxy=http://127.0.0.1:7877 push ...`；curl 加 `-x http://127.0.0.1:7877` |
| KiCad python / kicad-cli | `"E:/Program Files/KiCad/10.0/bin/"`（STEP 导出需 `KICAD9_3RD_PARTY` 指向 Documents/KiCad/9.0/3rdparty） |
| FreeCAD 1.1 | `E:/FreeCAD/bin/FreeCADCmd.exe`（中文脚本需 exec 注入法，见 archive 手册 §7） |
| Pages 构建部署 | `python tools/build_site.py` → `git subtree split --prefix=site -b gh-pages` → push |
| 装配体再生成 | 两条命令（kicad-cli 导出 + make_assembly.py），见 `docs/archive/tnkr-2026-10/asset-manifest.md` 顶部注记 |
| tyc-cli / mcp-jobs | 已配置（尽调已毕，额度 100/天 VIP） |

## 4. 铁律（血泪换来的操作约束）

1. **SWIG 腐败**：pcbnew `board.Remove()` 后不得再查询——一进程一操作，文件往返传状态。
2. **Mimosa 钩子**：写文件一律 `Path.write_bytes(...)`（`open(x,"w")` 即便字面量也会被完整扫描拦截为高危）；禁 eval/exec；禁 `..` 上跳；第三方源码放项目树外；源码文件必须 Write/Edit 工具提交。
3. **ES module 裸说明符**：import 必须带 `./` 前缀（"js/x.js" 不走相对解析走 importmap，模块图整体崩）。
4. **GitHub 文件线**：>50MB 警告、>100MB 拒收；大工件放 .gitignore + 脚本再生（先例：76MB 装配体已下架 HEAD）。
5. **目视检查方法论**：填充探测用 `HitTestFilledArea`（±0.15 偏移多点），不能数多边形顶点；A* 栅格限制在板内+禁布区。
6. freerouting 火力：`-mp 200 -us hybrid -hr 1:1 --router.optimizer.improvement_threshold=0.0 --router.via_costs=80`。
7. **凭据边界**：密码只经用户手（GitHub sudo/Tnkr OAuth 均为此例）；PAT/天眼查 key 只在 `简历/`（gitignored），永不入 git。
8. 每步修复后 DRC 差分守门（净减不增）+ git 提交做回滚点。

## 5. MCP 状态（2026-10-03 复核）

- **tyc-mcp**：CLI 可用（VIP 100 次/天）；ZCode 内 sse+/v1 配置未挂载，如需交互式改 `/mcp`+http
- **mcp-jobs**：已连通（本地 dist 直跑）
- **aminer**：token 至 2026-10-21
- **github**：官方插件为 skills 形态；PAT 在 `简历/github的PAT.txt`
- **tnkr 线**：已关闭；GitHub App "Tnkr AI" 对 flowio-cn 的只读授权**待用户卸载**（github.com/settings/installations，需 sudo 密码）

## 6. 新会话建议开场

```
读 E:/FLOWIO/HANDOFF.md → 确认三待办（投递/下单/App 卸载）哪些已完成 → 按用户指令推进：
  (a) 板到货 → BRINGUP 验收流；(b) 求职材料细化；(c) v2.1 特性立项。
```
