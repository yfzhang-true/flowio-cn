# FLOWIO-P1 自动化补线实施计划（6→0 未连接）

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 用三引擎级联（KRT 平面修复 → freerouting 火力全开 → KRT 段级协商撕布）把 6 条未连接清零，全程零 GUI。

**Architecture:** 每阶段独立可验证：CLI 工具吃 .kicad_pcb 文件，阶段间用 git 提交做回滚点；DRC JSON 差分做守门（净减不增）。KRT 栈（`E:/FLOWIO/资源/工具链/KiCadRoutingTools/py_router/`）独立解析板文件，与 pcbnew SWIG 管线通过文件传递协作，规避内存腐败。

**Tech Stack:** KiCadRoutingTools py_router CLI · freerouting v2.4.1 (Java 25 headless) · KiCad 10 kicad-cli/pcbnew · git

**SPEC:** `docs/superpowers/specs/2026-10-01-p1-auto-finish-design.md`（方案 A，已含根因 R1-R5 对照）

**基线**: 6 未连接 = R13/R29 strap 簇、C3-U3.2 buck 输入簇×2、GND F↔In1 岛对、3V3 岛对。其余 error 类全零。
**约定**: 命令从 `E:/FLOWIO/hardware/flowio-p1/` 执行；KPY=`"E:/Program Files/KiCad/10.0/bin/python.exe"`；KRT=`E:/FLOWIO/资源/工具链/KiCadRoutingTools`；每 Task 结束 `DRC && 提交`。

---

### Task 0: KRT 栈冒烟测试

**Files:** 无新增（只验证）

- [ ] **Step 1: 依赖检查**

Run: `KPY -c "import numpy; print(numpy.__version__)"` → Expected: `2.4.2`

- [ ] **Step 2: repair_planes 冒烟（干跑当前板，输出到临时副本）**

```bash
KPY "E:/FLOWIO/资源/工具链/KiCadRoutingTools/py_router/repair_planes.py" flowio-p1.kicad_pcb /tmp/smoke-p1.kicad_pcb --nets GND --plane-layers F.Cu
```

Expected: 正常退出并打印探测到的断区数量；若报 import 错误，将 KRT 的 `py_router` 与其 `kicad_parser` 等依赖目录加入 `PYTHONPATH` 重试；仍失败 → 记录并在 Task 3 改用移植路线（源码逻辑并入 netdoctor）。

- [ ] **Step 3: 提交（仅当有任何配置修复）**

```bash
git add -A; git commit -m "chore: KRT 环境适配" || true
```

### Task 1: KRT 平面岛修复（清 2 对 zone 未连）

**Files:**
- Modify: `flowio-p1.kicad_pcb`（经 KRT 输出回写）

- [ ] **Step 1: repair_planes 处理 GND (F.Cu + B.Cu + In1.Cu)**

```bash
KPY "$KRT/py_router/repair_planes.py" flowio-p1.kicad_pcb flowio-p1.kicad_pcb --nets GND --plane-layers F.Cu,B.Cu,In1.Cu
```

- [ ] **Step 2: repair_planes 处理电源平面 (+3V3/+5V @ In2.Cu)**

```bash
KPY "$KRT/py_router/repair_planes.py" flowio-p1.kicad_pcb flowio-p1.kicad_pcb --nets +3V3,+5V --plane-layers In2.Cu
```

- [ ] **Step 3: pcbnew 重灌 + DRC 差分**

```bash
KPY -c "import pcbnew; b=pcbnew.LoadBoard('flowio-p1.kicad_pcb'); pcbnew.ZONE_FILLER(b).Fill(list(b.Zones())); pcbnew.SaveBoard('flowio-p1.kicad_pcb',b)"
"E:/Program Files/KiCad/10.0/bin/kicad-cli" pcb drc --format json --severity-all --output drc.json flowio-p1.kicad_pcb
KPY -c "import json; d=json.load(open('drc.json')); print('unconnected:', len(d['unconnected_items']))"
```

Expected: unconnected 6→**4**（两对 zone 消失）或更少；若新增任何 error 类违规 → `git checkout -- flowio-p1.kicad_pcb` 回滚并改走 Task 3 处理平面。

- [ ] **Step 4: 提交**

```bash
git add flowio-p1.kicad_pcb drc.json && git commit -m "fix(pcb): KRT repair_planes 清平面岛对 (6→4)"
```

### Task 2: freerouting 第四轮（火力全开）

- [ ] **Step 1: DSN 导出 + 高压参数布线**

```bash
KPY -c "import pcbnew; b=pcbnew.LoadBoard('flowio-p1.kicad_pcb'); pcbnew.ExportSpecctraDSN(b,'flowio-p1-round4.dsn')"
"E:/FLOWIO/资源/工具链/jdk-25/bin/java.exe" -Djava.awt.headless=true -jar "E:/FLOWIO/资源/工具链/freerouting-2.4.1.jar" \
  -de flowio-p1-round4.dsn -do flowio-p1-round4.ses -mp 200 -us hybrid -hr 1:1 \
  --router.optimizer.improvement_threshold=0.0 --router.via_costs=80 -l en
```

Expected: 日志显示多轮 pass 且 "N unrouted" 中 N < 6；若 ripup 把已好网络改坏（见 Step 2 DRC），改加 `-inc` 排除已好网类重跑。

- [ ] **Step 2: SES 回灌 + 重灌 + DRC**

```bash
KPY -c "import pcbnew; b=pcbnew.LoadBoard('flowio-p1.kicad_pcb'); pcbnew.ImportSpecctraSES(b,'flowio-p1-round4.ses'); pcbnew.ZONE_FILLER(b).Fill(list(b.Zones())); pcbnew.SaveBoard('flowio-p1.kicad_pcb',b)"
```
DRC 同 Task 1 Step 3。

Expected: unconnected ≤2（strap 簇与 buck 簇或被撕布解决）；error 类保持 0。**任何回退 → git 回滚本 Task。**

- [ ] **Step 3: 提交**

```bash
git add -A && git commit -m "fix(pcb): freerouting 第四轮 hybrid 全火力 (ripup 代价递增至解开死角)"
```

### Task 3: KRT 段级协商撕布（PathFinder 语义，口袋终局）

**Files:**
- Create: `tools/negotiated_reroute.py`（驱动 KRT 模块：rip_up_net(only_segments)+blocking_analysis）

- [ ] **Step 1: 写驱动脚本（骨架，核心循环）**

```python
# tools/negotiated_reroute.py — PathFinder 协商撕布 (KRT 零件驱动)
# 伪代码即实现蓝图, 每轮:
#   1. 对每个失败网络端点跑 A* (KRT grid_router), 收集 frontier blocked_cells
#   2. blocking_analysis.analyze_frontier_blocking -> 候选阻挡腿 (IO6/IO7/BUCK_SS...)
#   3. 选 history_cost 最低的阻挡腿 S: rip_up_net(net=S.net, only_segments=[S])
#   4. 重布目标电源网 (boardgeom + KRT route_multipoint); 成功 -> 重布被撕的 S
#      失败 -> rip_restore(S); S.history_cost *= 2
#   5. 全部连通或轮次>8 -> 结束
# 文件往返: 每轮落盘 -> pcbnew 重灌 -> kicad-cli DRC (净减不增守门)
```

实现要点（从 KRT 源码取证）：`rip_up_net` 的 `only_segments` 参数（段级部分撕布 #510）+ `history_conflict=True`（历史冲突成本）+ `rip_restore`（失败还原）；阻挡腿归因用 `analyze_frontier_blocking(blocked_cells, pcb_data, config, routed_net_paths)`。

- [ ] **Step 2: 只针对剩余簇运行（R13/R29 或 C3-U3.2）**

Run: `KPY tools/negotiated_reroute.py --targets R13.1,R29.1,U3.2 --max-rounds 8`

Expected: 每轮打印 [轮次/撕了谁/成败/成本]；结束后 DRC unconnected 减少。

- [ ] **Step 3: DRC + 提交（有进展才提交）**

```bash
git add tools/negotiated_reroute.py flowio-p1.kicad_pcb && git commit -m "fix(pcb): 段级协商撕布清口袋簇 (PathFinder 语义)"
```

### Task 4: 最后一档 0.15/0.15 细通道（仅当仍 >0）

- [ ] **Step 1: netdoctor BFS 路由器加"细线档"**

boardgeom `CLR` 分级：`CLR_FINE=0.16`（0.15 线+0.15 间距=0.31 半距，JLC 经济档合规），仅对剩余补线网启用；落点仍须全障碍+填充验证。

Run: `KPY tools/netdoctor.py heal10`（heal10 = 细线档重试剩余目标）

- [ ] **Step 2: DRC 终验 → 必须 0/0**

Expected: `unconnected: 0` 且 error 类 0。

### Task 5: 收尾三连（强制）

- [ ] **Step 1: 重渲染 + 禁布区探测**

```bash
"E:/Program Files/KiCad/10.0/bin/kicad-cli" pcb render --side top --width 2400 --height 2000 -o r_top.png flowio-p1.kicad_pcb
"E:/Program Files/KiCad/10.0/bin/kicad-cli" pcb render --side bottom --width 2400 --height 2000 -o r_bot.png flowio-p1.kicad_pcb
KPY -c "<6 点禁布区探测, 期望 hits=0>"
```

- [ ] **Step 2: 目视检查两渲染图**（新走线不压线/无乱麻/撕布区无残骸）

- [ ] **Step 3: fab 包同步重出 + README 更新（去掉遗留清单）+ 最终提交**

```bash
cd fab && rm -f flowio-p1-jlc.zip && zip -q flowio-p1-jlc.zip <同前文件清单> && cd ..
git add -A && git commit -m "feat(pcb): 6 条未连接全自动化清零; fab 包同步"
```

---

## 完成定义
1. `kicad-cli pcb drc --severity-all`: **unconnected_items = 0，error 类 = 0**（外观类豁免不变）
2. 全程零 GUI（脚本/CLI/git 记录可审计）
3. 渲染目视检查通过 + 禁布区 0 命中
4. fab 包与最终板同步
5. 若 Task 3/4 后仍有个位数残留：输出"剩余障碍 N+1 归因报告"（blocking_analysis 原始输出）作为下一轮改进输入——不静默放弃
