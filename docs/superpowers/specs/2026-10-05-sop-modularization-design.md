# Spec: FLOWIO-CN SOP 沉淀（工具链模块化 + 流程 Skill 化 + 布线算法决策）

> 日期: 2026-10-05 · 分支: p1.1-spin-b · 状态: **待用户审查**
> 来源: 用户指示——"逐渐形成了一套 SOP，程序层面应形成可复用的低耦合高内聚模块，
> 流程层面形成 SOP 的 skill，以便未来不同环节调整后的重新走流程"+"算法条件松弛、
> 升级可微分？思考清楚优化目标与约束"。
> 时序约束: **期 A（纯文档）立即可做；期 B（代码重构）排在 P1.1 T8 之后**——
> 与正在执行的 T4/T5 撞文件（route_pcb/gen_pcb 等），big-bang 重构会毁掉收敛中的布线。

## 1. 布线算法决策记录（回应"可微分化"）

### 1.1 优化问题形式化
- 硬目标: 100% 连通（离散判定）；硬约束: DRC（线宽/间距 0.127mm、过孔、铜柱净空 3.7、
  禁短路）——违反即废板，无"轻微违反"；软目标: 线长/过孔数/层均衡/EMC/良率。
- 可微分适用边界: 布局（placement）目标 HPWL 可连续松弛（DREAMPlace, 文献库在档）；
  布线（routing）输出=格点图离散路径 + 硬 DRC——罚函数软化后投影回可行域即再违反，
  学术有论文、工业零采用。T4 实战印证: 338→17 由确定性 A*（_auto6）+通道布线+
  freerouting 达成，剩余为组合挪线问题非梯度问题。

### 1.2 裁定（决策点 S1）
| 层 | 决策 | 动作 |
|----|------|------|
| 布线主算法 | **不微分化**（推荐） | 维持 6 阶段混合布线；把 T4 收获固化（见 §3 route/ 模块） |
| 约束分级松弛 | ✅ 本版 | `drc_rules.py` 两档: JLC 工艺硬线（不可破）vs 美观线（微跳线 0.2mm 级、绕行偏好——收尾/优化可破，CI 只守硬线）；布线器读档 |
| 布局可微分辅助 | P2 实验项 | DREAMPlace 式 HPWL 梯度初始化给 auto_place 提供候选（scipy 起步）；文献链 literature/2019-lin-dac-dreamplace.pdf；本版只在 SOP 登记，不写代码 |

## 2. 期 A: 流程 SOP Skill 化（可立即执行，纯文档）

### 2.1 产物
- **用户级 skill**: `C:\Users\yuefe\.agents\skills\flowio-sop\SKILL.md`（未来任意会话
  Skill(flowio-sop) 一键加载全流程）
- **仓库镜像**: `docs/sop/SKILL.md` + `docs/sop/`（git 版本化、PR 可审、随项目演进）
- 两处同源: 仓库为源，用户级为部署副本（SOP 部署小脚本同步）

### 2.2 SKILL.md 内容骨架（八节，每节=可执行 checklist 而非散文）
1. **真值链铁律**: devices.json(两段)→case_geom→生成器→产物；**禁手编产物**
   （.kicad_sch/.kicad_pcb/flows.json/STL 一律生成）；改源重跑。
2. **五层测试守门**: L1-L5 清单+运行命令（venv-cad/FreeCAD python/Node 三环境路径表）。
3. **变更重走矩阵**（核心资产——"不同环节调整后重新走流程"的机器可读表）:
   | 改了什么 | 必须重跑 | 必须更新 |
   |---------|---------|---------|
   | devices.json devices 段 | ingest→gen_sch?否→gen_pcb→make_case→meshes→flows→全测试 | registry |
   | devices.json pneumatic 段 | L5 pneumatic 断言→T6 结构→T7 仿真参数 | registry+孪生 |
   | gen_sch.py | gen_sch→ERC→netlist→graph→flows | net.net/fab net |
   | PLACE（布局） | gen_pcb→route_pcb 1-6→freerouting→pos→make_flows→L5 | standoffs |
   | case_geom.py | make_case→meshes→assembly→L1-L4 | scene.js bbox |
   | 器件新增 | JLC MCP 摄取→devices.json→registry 六元组→datasheet 入 literature | DOWNLOAD-LIST |
   | 固件/孪生 | run_tests.sh 六段 | 站点双态目视 |
4. **环境铁律**: SWIG 一进程一操作/Mimosa(Write/Edit+write_bytes+hooksPath 绕行理由模板)/
   worktree 外层禁 add -A/FreeCAD Matrix 第4列/kicad-cli 路径/freerouting exe+max_passes=3。
5. **布线收敛 SOP**: 阶段1-6 用途表+freerouting 火力参数+DSN 电源网必须保留+差分守门节奏。
6. **双阶段评审模板**: spec 合规审（对照任务书逐条+独立验证）→质量审（Must/Should 分级）
   →修复→复审；实现者状态协议（DONE/DONE_WITH_CONCERNS/NEEDS_CONTEXT/BLOCKED）。
7. **器件选型 SOP**: 参数完备性审计表（电气/几何/协议/工艺四类）+"参数两说"裁决原则
   （多源交叉→最坏兜底→实测关闭）+否决留档。
8. **部署 SOP**: gh-pages subtree split push+生产终验清单。

### 2.3 验收（期 A）
- skill 部署后新会话可凭 `Skill(flowio-sop)` 拿到全部命令与铁律（盲测: 让 fresh 会话
  只靠 skill 完成一次"改 PLACE→重走矩阵"推演，无卡点）；
- 变更重走矩阵覆盖历史全部真实变更场景（P1→P1.1 的 13 类变更回溯核对）。

## 3. 期 B: 程序模块化重构（P1.1 T8 后执行，独立 worktree）

### 3.1 现状与病灶
生成器/测试散在 hardware/flowio-p1/tools/、enclosure/、fab/ 三处；命名不统一
（gen_sch/gen_pcb/route_pcb vs make_case/make_flows）；测试 check() 模式各文件重复实现；
import 跨目录 sys.path hack。

### 3.2 目标包结构（渐进式，re-export 过渡，禁 big-bang）
```
hardware/flowio/lib/flowio/          # 可安装包 (pip -e)
  truth/    devices.json 加载/schema/pneumatic（含 T1 断言谓词）
  gen/      sch_gen.py / pcb_gen.py（从 tools/gen_*.py 迁移）
  route/    stage1..stage6.py / dsn_io.py / auto6.py(0.25mm A*) / drc_rules.py(§1.2 分档)
  geom/     case_geom.py / device_geom.py / fcl_check.py
  flows/    flows.py / hotspots.py
  netlist/  parse.py / graph.py / drill.py
  testkit/  check.py（check() 统一实现）/ runner.py（L1-L5 分层入口）
  cli.py    flowio truth|gen|route|geom|flows|test <subcmd>
```
- 内聚: 每模块单一职责（route/auto6 只管 A* 补线，不知道 pcbnew 之外的任何事）；
- 耦合: 模块间只经 truth 层数据结构与显式参数（禁 sys.path hack）；
- 兼容: 旧路径保留 re-export shim 一个版本周期（tools/gen_sch.py → from flowio.gen import …）；
- run_tests.sh 六段改调 cli，行为与退出码不变（迁移期双跑对拍一次）。

### 3.3 验收（期 B）
- 全测试通过且**与迁移前输出逐字节一致**（产物确定性）；
- 新增一个器件端到端（devices.json→sch→pcb→case→flows→测试）只改 truth 层数据+一个
  PLACE 坐标，零代码改动（盲测用一颗假想电容走通）；
- cli 单命令可重放全链（flowio all）。

## 4. 不做的事（YAGNI）
- 布线可微分化（§1.2 已裁定，P2 只留布局实验项登记）；
- 期 B 不引入新功能（纯搬迁+去重，DRC 差分基线冻结）；
- 不做 GUI/看板类"流程可视化"。

## 5. 决策点（待用户裁定）
- **S1 布线算法**: A=不微分化+约束分级松弛（推荐）/ B=仍要投入可微分 routing 研究
- **S2 skill 位置**: A=用户级+仓库双源（推荐）/ B=仅仓库 / C=仅用户级
- **S3 期 B 时机**: A=P1.1 全交付后（推荐，零冲突）/ B=T8 回归后立即 / C=现在（需暂停 T5-T7，不推荐）
