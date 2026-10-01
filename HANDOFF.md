# FLOWIO 项目交接文档（新会话必读）

> **生成**: 2026-10-01 晚 · **目的**: 切换新会话（为加载 aminer MCP）后快速恢复上下文
> **新会话第一动作**: 通读本文档 → 按需读 §2 的 spec/plan → 等用户指令（大概率是批准执行 auto-finish plan）

---

## 0. 一句话现状

P1 板（FLOWIO-CN"升级大脑"，B2B 康复手套白牌厂商，¥300-500/套）已完成：原理图（344 连接 0 错）、布局布线（**146→6 未连接，零短路，其余 error 类全零**）、电路仿真（4 电路达标）、JLC 制造包、FreeCAD 参数化外壳。**唯一主线待办：6 条未连接的纯自动化补线**——spec/plan 已写好等用户批准；用户明确**拒绝 KiCad GUI 手工操作，必须自动化**。

## 1. 已完成 / 待完成

### ✅ 已完成（按 git 提交序，全部已入 main 分支）
| 交付物 | 位置 | 关键提交 |
|---|---|---|
| 原理图（修正 #1-#13） | `hardware/flowio-p1/flowio-p1.kicad_sch` | 早期 |
| PCB 布局+层叠 90×75 | 同目录 `.kicad_pcb` | 41e697e |
| freerouting 双轮布线 146→17 | + 天线禁布区丢失被抓回 | c3337a3 |
| DRC 攻坚 17→6（error 类清零） | 自研 boardgeom/netdoctor | a38172a |
| 电路仿真 4 电路（buck/二极管或/阀驱动/I2C） | `hardware/flowio-p1/tools/sim/out/` | bf48abd |
| JLC 打样包（Gerber/钻孔/坐标/BOM47行/装配PDF/zip/README） | `hardware/flowio-p1/fab/` | bf48abd |
| FreeCAD 参数化外壳（FCStd+STEP+STL 水密，用户指定替代 OpenSCAD） | `hardware/flowio-p1/enclosure/` | bf48abd |
| 自研脚本安全清零（exec/eval/路径穿越 7 处高危） | tools/ | a75578e |

### ⏳ 待完成（优先级序）
1. **【主线·等用户批准 spec/plan 后执行】6 条未连接自动化清零**——见 §2 的 auto-finish spec+plan
2. 执行完 plan 后：fab 包同步重出 + README 去掉遗留清单
3. 主线硬件阻塞（需实物，用户操作）：74HCT245/MOS 触发测试、传感器到货、PID 首跑
4. 外壳 3D 打印验证（STL 已就绪）
5. 建议跑一次 Mimosa 完整审计（上次提交提示扫描覆盖不完整，勿宣称项目安全）

### 当前 6 条未连接（freerouting 三轮+脚本攻坚后的死角，均已坐标级取证）
R13/R14 strap 供电簇（口袋被 IO6/IO7 In1 竖线+BUCK_EN 围死）· R29 簇 · C3-U3.2 buck 输入簇×2 · GND F↔In1 平面岛对 · 3V3 平面岛对。根因 R1-R5 与算法对策详见 spec §1。

## 2. 新会话必读文件（按序）

| 文件 | 作用 |
|---|---|
| `docs/superpowers/specs/2026-10-01-p1-auto-finish-design.md` | **主线 spec**：根因 R1-R5、检索来源、三方案（推荐 A 三引擎级联）、验收标准、§6 KRT 能力、§7 文献下载清单 |
| `docs/superpowers/plans/2026-10-01-p1-auto-finish.md` | **主线 plan**：T0 KRT 冒烟→T1 repair_planes→T2 freerouting 火力全开→T3 KRT 撕布 CLI（mincut）→T3b 兜底→T4 细线档→T5 渲染目视+fab 同步 |
| `docs/superpowers/specs/2026-10-01-flowio-p1-completion.md` | 上一轮收尾 spec（含 §9 执行变更 C7 FreeCAD/C8 仿真/C9 HD 移位、§10 结果对照） |
| `docs/superpowers/specs/2026-10-01-flowio-p1-pcb-design.md` | 总设计 spec v1.1（修正 #1-#13 全记录、引脚表、电源拓扑） |
| `hardware/flowio-p1/fab/README-fab.md` | JLC 打样参数 + 已知遗留说明 |

工作流约定：用户强制要求使用 superpowers skills（using-superpowers→brainstorming→writing-plans→executing-plans），**修复完成后必须"目视检查"**（渲染+程序化探测）。

## 3. 关键路径与环境（Windows，Git Bash）

| 工具 | 路径/命令 |
|---|---|
| KiCad python（pcbnew） | `"E:/Program Files/KiCad/10.0/bin/python.exe"`（含 numpy 2.4.2，**无 matplotlib**） |
| kicad-cli | `"E:/Program Files/KiCad/10.0/bin/kicad-cli"`（drc 要 `--format json --severity-all`，unconnected 在顶层 `unconnected_items` 键，**不在 violations 里**） |
| freerouting 2.4.1 + Java 25 | `E:/FLOWIO-外部参考/_ref/freerouting-2.4.1.jar` + `E:/FLOWIO-外部参考/_ref/jdk-25.0.4.1+1-jre/bin/java.exe`，**必须 `-Djava.awt.headless=true`** |
| KRT（KiCadRoutingTools） | `E:/FLOWIO-外部参考/_ref/KiCadRoutingTools-main/`（**在项目树外**，Mimosa 要求）。核心：`py_router/repair_planes.py`（独立 CLI）、`py_router/route.py --nets X --rip-existing-nets Y --ripup-blocker-select mincut`、`docs/rip-up-reroute.md` |
| FreeCAD 1.1 | `E:/FreeCAD/bin/FreeCADCmd.exe`（外壳已建：`enclosure/make_case.py`） |
| DSN/SES 往返 | `ExportSpecctraDSN` → java → `ImportSpecctraSES` → `ZONE_FILLER.Fill` → SaveBoard |
| 我方布线工具链 | `tools/boardgeom.py`（全障碍落点库）、`tools/netdoctor.py`（岛探测/跳线/heal 系列）、`tools/final_assault.py` |
| 文献（用户可能已下载） | `E:/FLOWIO-外部参考/_ref/papers/`（PathFinder'95 + Revisiting PathFinder FPGA'22，Task 3b 按需） |

## 4. 铁律（血泪换来的操作约束）

1. **SWIG 腐败**：pcbnew 里 `board.Remove()` 后不得再查询——**一进程一查询一删除**，文件往返传递状态。
2. **Mimosa 钩子**（PreToolUse + commit 前扫描）：
   - 写文件用 `Path.write_bytes(...)`（`open(x,"w")` 一律报路径穿越高危，即使字面量）；禁 `eval`/`exec`（用 ast 受限解释，参考 `tools/gen_pcb.py`）；禁 `..`/parents 上跳推导；第三方源码放项目树外。
   - 直接写源码必须用 Write/Edit 工具（Bash 写会被拒）。
   - 服务器请求仅 http/https、校验 host、拒内网/环回。
3. **目视检查方法论**：填充探测必须用 `HitTestFilledArea`（多取 ±0.15 偏移点），**不能数多边形顶点**（大轮廓覆盖点但顶点在外→假阴性）；焊盘锚判定要防"焊盘在岛内≠与填充连通"假阳性。
4. **几何模型教训**：矩形焊盘对角伸出 max/2 圆外（需点对旋转矩形精确距离）；走线只与同层铜冲突（过孔才贯穿全层）；SMD 焊盘不挡内层；同网孔距规则仍适用（禁叠孔）；A* 栅格必须限制在板内+禁布区。
5. freerouting 火力（CLI 文档实证）：`-mp 200 -us hybrid -hr 1:1 --router.optimizer.improvement_threshold=0.0 --router.via_costs=80`；默认贪心+2.5%阈值会提前停机。
6. 每步修复后 `kicad-cli pcb drc` 差分守门（**净减不增**）+ git 提交做回滚点。

## 5. MCP 状态（本会话末复查结论）

- **aminer**：`~/.zcode/cli/config.json` 配置有效（SSE 端点 200、token 至 2026-10-21）——**新会话应已加载 `mcp__aminer__*`**；若用户要求检索文献优先用它。
- **github**：官方插件形态是 skills（github:repo/issue/pr…），无 `mcp__github__*` 函数，属设计如此。
- jlcpcb/lootdrop MCP 正常。

## 6. 新会话建议开场

```
读 E:/FLOWIO/HANDOFF.md → 读 §2 两份 auto-finish 文档 → 向用户确认:
  (a) spec/plan 是否批准执行；(b) papers/ 是否已放文献（Task 3b 按需）；
  (c) 是否先用 aminer MCP 补一轮文献检索（用户此前明确要求过用 aminer）。
```
