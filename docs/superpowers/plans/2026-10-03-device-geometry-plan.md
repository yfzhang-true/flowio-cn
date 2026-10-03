# Plan: 器件几何与拓扑约束框架（T0-T8 · v2）

> 日期: 2026-10-03 · 前置: spec v2 `2026-10-03-device-geometry-framework.md`（四决策点已定案）· 分支: device-geometry
> v2 变更: T0 基线精读（已完成）；T2 碰撞内核改 trimesh+FCL；T3 电气边改网表解析；T5 高度链按 JLC 真值修正（总高 26.07）；新增 T8 P2 阀板载化里程碑。
> 全程走 worktree `.worktrees/device-geometry`；每任务 TDD（先写失败断言再实现）；完成标准 = L5 层全绿 + 既有五层回归全绿。

## T0 基线下载与精读（✅ 已完成，2026-10-03）
产物（2026-10-03 已整合入仓）：`third_party/repos/`×7 + `literature/` 11 篇（原名→规范名映射见
`literature/DOWNLOAD-LIST.md` 2026-10-03 节）+ `tools/venv-cad`（冒烟通过）+
`docs/research/2026-10-03-baseline-reading.md`（精读笔记与落地映射表）。

## T1 器件数据层（~1 次会话）
1. `tools/ingest_device_dims.py`：读 `bom-jlc.csv` 38 行 C 号 → jlcpcb MCP
   → 抽取 Height Above Board / 长宽 / 安装朝向类 / datasheet URL → 生成
   `enclosure/devices.yaml` 骨架。
2. 人工钉 17 个连接器的 `port.dir_local`（datasheet 一次定锚，来源写注释）。
3. **测试先行**：`test_device_geom.py::test_schema` —— 38 行全覆盖、字段类型、
   EDGE_OUT 必有 port.dir_local 与 exit_z。先红后绿。

## T2 几何核（trimesh+FCL，venv-cad 正式化）
1. ✅ 环境已就绪（2026-10-03 整合时完成）：`tools/venv-cad` 已建并冒烟通过、
   `requirements-cad.txt` 已提交；run_tests.sh 探测该解释器在 T7 接线。
2. `device_geom.py`：`obb()`（JLC 构盒首选 / STEP→oriented_bounds 校验）、
   `port_ray()`、`hull()`；`CollisionManager` 注册 case STL+器件体。
3. 测试：J10 port_ray·(+Y 壁法向) > cos45°；相交/分离盒冒烟已过的等价断言；
   装配态 in_collision_internal 空表；min_distance 关键对（U1↔L1）。

## T3 网表解析 + 关系图
1. `kicad-cli sch export netlist`（sch → netlist，S-expr）→ `netlist.py` 解析器
   → 网络名→refs 电气边（剔电源/地）。
2. `device_graph.py`：电气边 + 空间边（EDGE_OUT→槽，槽清单 import case_geom）。
3. `slots_satisfied()`：`minimum_weight_full_matching`（权=端口射线到槽中心距离）；
   flows 拓扑表降级为交叉校验（不一致即红）。
4. 测试：17 连接器↔17 槽（9 侧槽 + 8 端子槽；角部 relief 为附属几何不计槽）完美
   匹配；人为删槽必红。

## T4 钻孔/禁布层
1. `drl.py` 全刀径段解析 → 孔位+孔径表；courtyard 阶段 1 用 pos+OBB 替代。
2. 测试：器件 OBB 与 M3 孔（Ø3.2×4）间隙 >0.3mm；TH 焊盘与铜柱投影不冲突。

## T5 真值切换 + 壳高收紧（JLC 真值，决策 ①）
1. `case_geom` 派生自 devices.yaml（DEFAULT 兜底）；高度链定稿：
   TALLEST=14.07 → Z_CEIL=23.67 → **OUTER_H=26.07**；TERM_SLOT z_hi=23.27、
   宽度/角部 relief 按 JLC 尺寸复核；EXPLODE/bbox_mm/scene.js 回退值同步。
2. 重跑 make_case/make_meshes/make_flows/make_assembly 全链 + L1-L4 全绿 +
   双态截图目视。
3. 三方对拍测试（devices.yaml ↔ case_geom ↔ JLC 快照）。

## T6 FlowIO 差距文档（决策 ③ 前半）
`docs/flowio-parity-gap.md`：差距表扩展为 P2 候选清单（每项含空间/拓扑约束描述）
+ 框架支撑方式（加数据+加断言模式）。

## T7 收尾
1. run_tests.sh 加 L5 层（venv-cad 解释器）；2. 全量回归 + build_site + 部署
（T5 改了壳）；3. HANDOFF 增补（devices.yaml 真相源/L5 层/venv-cad）；4. 合并
main → 删分支。

## T8 P2 阀板载化排期（决策 ③ 后半，M2 里程碑）
按 spec §7：M2-0 前置（本框架交付+P1 BRINGUP）→ M2-1 选型（JLC 真值入
devices.yaml）→ M2-2 布局约束（域亲和/EDGE_OUT/气口阵列）→ M2-3 P2 全链交付
（原理图增量+布局+外壳+孪生+L1-L5）。启动时点：P1 板到货验证后；本期只立里程碑
不实施。

## 依赖与风险
- python-fcl Windows wheel 已实测（0.7.0.11）；trimesh 克隆损坏已弃，读 pip 版源码；
- aminer MCP 可用但仅限三通道（title 短片段 / person / recommend；search_paper 的
  keyword/长短语恒空勿用）——后续文献检索照此姿势；
- 壳收紧改 3D 打印件尺寸 —— 已获用户批准（板到货实测二次校验）。
