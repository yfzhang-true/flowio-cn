# FLOWIO-P1 剩余 6 条未连接的纯自动化补线 — 设计规格书

> **日期**: 2026-10-01
> **状态**: 待用户审查（用户指令：先 spec+plan 后审查；必须自动化，禁止 KiCad GUI 手工操作）
> **前置**: `2026-10-01-flowio-p1-completion.md` §10（现状：6 未连接，其余 error 类全零）
> **检索说明**: 本会话无 aminer/github MCP 绑定，研究以 WebSearch/WebFetch 等价完成（来源已在 §2 标注，含 ACM/IEEE 论文与 GitHub 仓库链接）

---

## 1. 为什么现有自动化工具链止步于 6 条？（根因剖析，程序化取证）

对每个死点做了逐障碍取证（板文件坐标级），失败不是"不可能"，而是**三类算法能力缺失**：

| # | 根因 | 证据（板级坐标） | 缺失的算法能力 |
|---|---|---|---|
| R1 | 我的路由器是**单网避障型**：把所有既有铜当刚性障碍，口袋区域按构造不可解 | R13/R14 口袋 (x20-24.2, y26-33) 被 IO6(In1 竖线 x=20.1, y14-51.8)、IO7(In1 x=24.2, y26.1-32.5)、BUCK_EN 过孔场三面围死；F.Cu 走廊被 freerouting 0.2/0.2 通道占满（我的 0.25 线+0.21 裕量需 0.87mm 通道 > 实际 0.6mm 线距） | **撕布重布（rip-up & reroute）**：允许把 IO6/IO7 挪走再放回 |
| R2 | freerouting 第三轮用的是**默认贪心策略 + 2.5% 改进阈值提前停机** | 日志原话 "Stopping optimizer because the improvement in this pass (0.0000%) is below the threshold (1.00%)"——它还没来得及把 ripup 代价升到足以撕开 IO6/IO7 就停了 | **策略火力**：`-us hybrid/global`、`improvement_threshold=0.0`、`-mp 200`（官方文档确认这些旗标存在且未被我使用） |
| R3 | KiCad 自带**推挤引擎（push-and-shove）没有 Python API**，脚本无法调用其"挤开邻居"能力 | 官方 dev-docs 与社区确认：交互路由器不可脚本化 | 自建**障碍微移（shove 语义）**：删除阻挡段→绕行重画→连通性保持 |
| R4 | 平面岛探测的锚判定有**假阳性**（焊盘中心落在岛轮廓内≠焊盘与填充连通，填充让位洞里的焊盘被误判为锚） | GND F.Cu↔In1 岛对在"缝合 0 岛"后依然报未连 | **填充感知的岛修复**（repair_planes 语义：探测断区→铺短宽桥） |
| R5 | 我的净距模型一刀切 0.21mm，JLC 实际支持 0.15/0.15——窄通道存在但被模型拒绝 | 口袋区 0.4mm 走廊：0.15 线+0.15 间距=0.45 半距 < 0.6mm 可行 | **分级净距**（最后一档 0.15/0.15） |

**结论：是的，明确存在算法改进空间，而且大部分零件已经开源存在**——KiCadRoutingTools（用户最初指定的 baseline！）的本地副本经核查包含：`rip_up_reroute.py`（**支持段级部分撕布 #510 + history_conflict 历史冲突成本**，这正是 PathFinder 协商拥塞思想）、`blocking_analysis.py`（A* frontier 的 N+1 障碍归因）、`repair_planes.py`（独立 CLI，专治平面断区）、`add_gnd_vias.py`（自动缝合孔）。

## 2. 检索依据（研究来源）

| 主题 | 来源 | 对本设计的贡献 |
|---|---|---|
| 协商拥塞路由 | [PathFinder (McMurchie & Ebeling, FPGA'95, ACM)](https://dl.acm.org/doi/10.1145/201310.201328) / [ICCAD'22 修订](https://dl.acm.org/doi/abs/10.1145/3490422.3502356) | 迭代撕布+历史/当前占用双成本，让竞争网络"谈判"——R1 的理论解 |
| freerouting 算法与 CLI | [算法页](https://freerouting.org/freerouting/autorouter-algorithm)（ripup 代价逐轮递增）、[官方 CLI 文档](https://github.com/freerouting/freerouting/blob/master/docs/command_line_arguments.md) | `-us hybrid -hr 1:1`、`--router.optimizer.improvement_threshold=0.0`、`-mp`、`--router.via_costs`——R2 的现成火力 |
| KiCad 脚本化边界 | [官方 Python 绑定文档](https://dev-docs.kicad.org/en/apis-and-binding/pcbnew/index.html)、[论坛讨论](https://forum.kicad.info/t/remote-control-pcbnew-via-python-scripts/47995) | 证实推挤引擎不可脚本化 → R3 必须自建语义 |
| 开源布线工程 | [KiCadRoutingTools](https://github.com/drandyhaas/KiCadRoutingTools)（含 rip-up/N+1 障碍分析/ripped-corridor，本地已下载精读）、[freerouting](https://github.com/freerouting/freerouting)、TopoR（非开源，仅作概念参照）、[GPU 拓扑布线](https://nicheloom.com/launches/3547) | 直接借用其撕布/障碍归因/平面修复实现，改造适配 |
| Specctra 生态 | DSN/SES 格式（FreeRouting/TopoR/ELECTRA 共用） | 我已有的 DSN↔pcbnew 往返管线继续复用 |

## 3. 方案选型（三选一，含推荐）

### 方案 A（推荐）：三引擎级联 —— KRT 平面修复 → freerouting 火力全开 → KRT 段级协商撕布补刀
1. `repair_planes.py` CLI 先清 2 对平面岛（独立工具，直接吃 .kicad_pcb）；
2. freerouting 第四轮：`-mp 200 -us hybrid -hr 1:1 --router.optimizer.improvement_threshold=0.0 --router.via_costs=80`（降过孔代价鼓励换层绕行；每步 DRC JSON 验证）；
3. 仍剩的口袋簇：用 KRT 的 `rip_up_net(only_segments=...)`（部分撕布）+ `blocking_analysis` 归因，定向撕 IO6/IO7/BUCK_SS 的**阻挡腿**→重布电源网→重布被撕信号腿，历史冲突成本逐轮 ×2（PathFinder 语义），最多 8 轮；
4. 最后一档：0.15/0.15 细通道路由。
- **优点**: 每一步都是可验证的独立阶段；KRT 零件现成（省 80% 自研）；freerouting 成本机制成熟。
- **缺点**: KRT 栈独立解析 .kicad_pcb（非 pcbnew SWIG），需环境适配 + 与我 pcbnew 管线的文件往返纪律（一进程一操作仍适用）。

### 方案 B：纯 freerouting 迭代轰炸
只做第 2 步的各种参数组合轮询（含 DSN 里给 strap 网设高优先级 net class）。
- **优点**: 最少工程量。**缺点**: 对 R4（平面岛）无效——freerouting 不理解 zone 填充碎裂；且若其成本函数局部最优，纯调参可能仍卡死。

### 方案 C：全自研 PathFinder
把协商拥塞完整实现进我的 netdoctor。
- **优点**: 完全可控。**缺点**: 重造 KRT 已有轮子，预计多花 5-10 倍工时，违背"以成熟仓库为 baseline"的用户既定方针。

## 4. 验收标准（全自动化判定）

| 项 | 门槛 |
|---|---|
| unconnected_items | **0**（含两对平面岛） |
| 其他 error 类（短路/间距/孔距/悬空/叠孔/禁布区/出界） | **0**，且修复过程**净减不增**（每步 DRC 差分） |
| 制造规则 | 最小线宽/间距 ≥ 0.15mm，过孔 ≥ 0.3/0.6（JLC 经济档） |
| 自动化程度 | 全程脚本/CLI，零 GUI 人工操作 |
| 目视检查（用户长期强制要求） | 修复后重渲染顶/底 + 禁布区探测 0 命中 + 外壳铜柱位核对 |
| 回归 | 仿真结论不受影响（电源拓扑未变）；fab 包同步重出 |

## 5. 风险与对策

| 风险 | 对策 |
|---|---|
| KRT 栈跑不起来（依赖/版本） | Task 0 冒烟测试；失败则退化为方案 B+自建段级撕布（借 KRT 源码逻辑，移植进 netdoctor） |
| freerouting 重布把我已修好的 10+ 处又改坏 | 每轮 SES 回灌后立即 DRC 差分，回滚点用 git；必要时 DSN 锁定已好网（net class 排除 `-inc`） |
| 撕布信号腿后重布失败（IO6/IO7 回不去） | rip_restore 机制（KRT 自带）；失败即回滚该轮，换撕别的阻挡腿（N+1 归因给全候选） |
| 0.15/0.15 细线良率 | 仅作最后手段且只用于 6 条补线（<10mm 短线），JLC 经济档支持 |
