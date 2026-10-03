# Plan: 器件几何与拓扑约束框架（T1-T7）

> 日期: 2026-10-03 · 前置: spec `2026-10-03-device-geometry-framework.md` 获用户批准 · 分支: device-geometry
> 全程走 worktree `.worktrees/device-geometry`；每任务 TDD（先写失败断言再实现）；完成标准 = 新 L5 层全绿 + 既有五层回归全绿。

## T1 器件数据层（~1 次会话）
1. `tools/ingest_device_dims.py`：读 `hardware/flowio-p1/fab/flowio-p1-bom-jlc.csv` 33 行 C 号
   → 调 jlcpcb MCP `component_search(C号)` → 抽取 Height Above Board / 长×宽 / 安装朝向类
   → 生成 `enclosure/devices.yaml` 骨架（port.dir_local 留空待人工）。
2. 人工钉 15 个连接器的 `port.dir_local`（对照 datasheet §钉一次，写入 yaml 注释来源）。
3. **测试先行**：`test_device_geom.py::test_schema` —— 33 行全覆盖、字段类型、
   EDGE_OUT 器件必须有 port.dir_local 与 exit_z。先跑（红）→ 实现 → 绿。

## T2 几何核 OBB/端口射线/SAT
1. `device_geom.py::obb(ref)`（任意 rot 四舍五入到 1°，非 90° 特判）；`port_ray(ref)`。
2. `sat_overlap(a,b)`：15 轴分离测试（3+3 面 + 9 叉积），零依赖。
3. 测试：J10 port_ray 与 +Y 壁外法向夹角 < 45°（用真实 rot=180 验证）；两已知分离/
   相交 OBB 对拍；顺带验证 J2 朝 +X。

## T3 关系图（networkx）
1. `device_graph.py`：电气边（T4 决策点：阶段 1 从 make_flows 的 ELEC/AIR 拓扑表读取）；
   空间边（EDGE_OUT→槽绑定，槽清单 import case_geom）。
2. `slots_satisfied()`：二部匹配（`nx.bipartite.matching`），断言完全匹配无孤点。
3. 测试：15 连接器 ↔ 15 槽（L@27/L@46/R@6/R@22/R@32.5/R@46/T@46/T@59.5/T@73 + B×8
   角部 relief 计 2）全命中；人为删一个槽必须红。

## T4 钻孔/禁布层
1. `drl.py`：解析 flowio-p1.drl 全部刀径段（复用 T9 解析经验）→ 孔位+孔径表。
2. courtyard：阶段 1 用 pos.csv+dims 生成的 2D OBB 替代（gbr 解析记入 backlog）。
3. 测试：器件 2D OBB 与 M3 安装孔（Ø3.2×4）间隙 > 0.3mm；TH 焊盘点与铜柱投影不冲突。

## T5 切换数据源 + 真值对拍（决策点 1 落地）
1. `case_geom.H` 改为从 devices.yaml 派生（保留 DEFAULT 兜底）；WJ500V 高度按用户裁定
   （建议 14.07+0.6）重算 Z_CEIL/OUTER_H/TERM_SLOT/TERM_RELIEF。
2. 重跑 make_case/make_meshes/make_flows/make_assembly 全链 + L1-L4 必须全绿
   （若壳收紧：bbox_mm/EXPLODE/scene.js 回退值同步，双态截图目视）。
3. 三方对拍测试：devices.yaml ↔ case_geom.H ↔ JLC 属性快照（防再分叉）。

## T6 FlowIO 差距文档
`docs/flowio-parity-gap.md`：§1 差距表（spec §1.3 扩展为 P2 候选清单+每项的空间/拓扑
约束描述）；§2 框架如何支撑（加数据+加断言模式）；§3 P2 排期建议（阀板载化优先）。

## T7 收尾
1. run_tests.sh 加 2c/5 层（test_device_geom.py）；
2. 全量回归（主树）+ build_site + 生产部署（若 T5 改了壳）；
3. HANDOFF 增补：devices.yaml 为器件尺寸唯一真相源；L5 层说明；
4. worktree 合并 main → 删分支。

## 依赖与风险
- jlcpcb MCP 逐 C 号检索（33 次）——离线时 yaml 手工补齐兜底；
- networkx 若无：`pip install networkx`（纯 python，无编译，Mimosa 树外安装）；
- 壳高度收紧会改 3D 打印件尺寸——需用户明确批准后才执行 T5.2。
