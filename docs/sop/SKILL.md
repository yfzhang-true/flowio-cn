---
name: flowio-sop
description: FLOWIO-CN 硬件工程全流程 SOP——真值链铁律、五层测试守门、变更重走矩阵、环境陷阱（SWIG/Mimosa/worktree）、布线收敛、双阶段评审、器件选型、部署。任何 FLOWIO-CN 仓库的硬件/CAD/固件/孪生改动前必读；用于"改了 X 之后该重跑什么"的流程重放。
---

# FLOWIO-CN 工程 SOP

> 本文件是流程单一真相源（仓库 docs/sop/SKILL.md 为源，
> `tools/deploy_sop_skill.py` 单向同步到用户级 skill 目录）。
> 每节=触发条件→步骤→命令→验收。**先读 §2 变更矩阵，再动手。**

## 0a. 产品五位一体（全流程总纲）

数字孪生产品 = 物理实体与其数字镜像共享同一份真值：
```
devices.json（单一真值：devices 贴装段 + pneumatic_devices 气动段）
  ├─ 硬件域  sch→pcb→fab        (flowio.hw)
  ├─ 结构域  case/manifold/pump  (flowio.geom)
  ├─ 固件域  pn_core+driver      (flowio.fwgen→types.h 生成)
  ├─ 孪生域  仿真模型            (flowio.twin: IActuator/BaseModel 体系)
  └─ 呈现域  webapp/site         (params_gen.js 生成 + 组件)
```
第一原则：**真值到介质的映射必须生成，不许手抄**（三语 codegen + CI diff 门）。
统一入口：`python -m flowio <域> <子命令>`（`--help` 看全树；hw 危险命令需显式确认旗标）。
变更重走链可直接执行：`python -m flowio rebuild --after <change-key>`（矩阵 15 键机读消费，M5 已实现）。

## 0. 三环境路径表（命令即复制即跑）

| 环境 | 解释器/路径 | 用途 |
|------|------------|------|
| 系统 Python | `python` (3.14) | 纯 stdlib 测试/L1-L3 |
| CAD venv | `E:/FLOWIO/tools/venv-cad/Scripts/python.exe` | L5（trimesh/FCL/networkx） |
| KiCad python | `"E:/Program Files/KiCad/10.0/bin/python.exe"` | pcbnew（gen_pcb/route_pcb，SWIG 铁律） |
| FreeCAD python | `E:/FreeCAD/bin/python.exe` | L4 干涉/装配（原生 UTF-8） |
| kicad-cli | `"E:/Program Files/KiCad/10.0/bin/kicad-cli.exe"` | ERC/DRC/netlist/pos/gerber/STEP（STEP 需 KICAD9_3RD_PARTY=~/Documents/KiCad/9.0/3rdparty） |
| freerouting | `E:/FLOWIO/资源/工具链/jdk-25/bin/java.exe -jar E:/FLOWIO/资源/工具链/freerouting-2.4.1.jar` | 布线优化（KiCad10 无 dsn/ses 子命令，DSN/SES 走 pcbnew API） |
| 工作根 | worktree（如 E:/FLOWIO/.worktrees/p1.1-spin-b） | **一切工作在 worktree，禁止直接改主树** |

> **cwd 基准统一**：下列相对路径均以 worktree 根为基准；`tools/gen_sch.py`、`tools/gen_pcb.py`、
> `tools/route_pcb.py`、`tools/ingest_device_dims.py` 实际位于 `hardware/flowio-p1/tools/`
> （运行目录 `hardware/flowio-p1/`）；`make_*.py`/`test_*.py`/`case_geom.py`/`device_graph.py`
> 位于 `hardware/flowio-p1/enclosure/`；netlist/drl 位于 `hardware/flowio-p1/fab/`。

## 1. 真值链铁律（数据流单向）

```
devices.json (devices 段: PCB 贴装 / pneumatic_devices 段: 气动)
  → case_geom.py (壳几何常量+高度链: TALLEST 派生)
  → gen_sch.py → flowio-p1.kicad_sch → netlist → graph
  → gen_pcb.py (AST 提取 PARTS) → .kicad_pcb → route_pcb → DSN/SES
  → pos/drl/gerber/STEP (fab)
  → make_case/make_meshes/make_flows/make_assembly (enclosure 产物)
  → 孪生 webapp / site
```
- **禁手编产物**：.kicad_sch/.kicad_pcb/flows.json/STL/装配体一律生成器产出；改源重跑。
- 改源后"产物与提交版 uuid 归一化对比"确认等价（防 uuid churn 重提）。
- 参数变更顺序：**先改 registry/文档 → 再改 devices.json → 重跑链**。

## 2. 变更重走矩阵（核心——改了什么就重跑什么）

机读源 `rebuild-matrix.json`（本目录），人读速查：

| 改动 | 必须重跑（按序） | 必须同步更新 |
|------|----------------|-------------|
| devices.json `devices` 段 | gen_pcb→pos 导出→ingest_device_dims→make_case→make_meshes→make_flows→L1-L3+L5 | registry、standoffs（若孔变） |
| devices.json `pneumatic_devices` 段 | L5 pneumatic 断言→(P1.1)T6 结构→T7 仿真参数 | registry、component-param-audit |
| gen_sch.py（电气） | gen_sch→ERC→netlist 导出(net.net+fab/*.net)→device_graph→make_flows→test_flows | 黄金值（nets/refs/edges 数，附推导） |
| PLACE 布局坐标 | gen_pcb→route_pcb 全阶段→freerouting→DRC→pos→make_flows→L5→check_route 双绿门（未连0+铜柱环0）→fab 重出（README-fab 再生命令）→check_fab 22 断言门 | standoffs、drc 差分基线、README-fab 钻孔谱/线宽谱黄金值+check_fab 黄金计数（450 孔/148 pos 行） |
| case_geom.py 常量 | make_case→make_meshes→make_assembly→L1-L4；scene.js bbox 同源断言会抓 | 测试标签动态引 G 常量（禁写死数字文本） |
| 新器件（JLC 件） | jlcpcb MCP 摄取→ingest→registry 六元组→datasheet 存 literature | DOWNLOAD-LIST、audit |
| 新器件（淘宝件） | devices.json CURATED_NOPART 手工条目→同上 | 同上+采购单 |
| 固件/孪生 js | firmware/twin/run_tests.sh 六段→build_site→双态截图目视 | HANDOFF |
| gen_pcb.py footprint/规则 | gen_pcb→DRC→pos→（若孔/板变）make_case 链→check_route 双绿门→fab 重出（README-fab 再生命令）→check_fab 22 断言门 | 测试黄金值、README-fab 钻孔谱/线宽谱黄金值+check_fab 黄金计数 |

历史返工案例（矩阵的来源，勿再踩）：壳高链漂移（Z_TOP 4.0→9.0 测试写死）、端子换型
（WJ500V→XH-2P 连带 TERM 槽/锚点/TALLEST）、双带出线（右壁 +X 语义 vs 底壁公式断言）、
POS_P11 过渡表（pos.csv 行优先+自动提示删除）、DSN 剥电源网（SES 导入连座清除全部电源铜）。

## 3. 五层测试守门（任何改动后的验收线）

| 层 | 内容 | 运行 |
|----|------|------|
| L1-L3 | STL bbox/锚点/装配契约 30 断言 | `python hardware/flowio-p1/enclosure/test_assembly.py` |
| L4 | FreeCAD OCC 干涉（0.000mm³） | 同上脚本内探测 FreeCAD 后自动跑 |
| L5 | 器件几何/图匹配/钻孔避让（默认档 13）+ pneumatic schema（15） | `E:/FLOWIO/tools/venv-cad/Scripts/python.exe hardware/flowio-p1/enclosure/test_device_geom.py`（命令行参数 `all`=追加 T2 图匹配/T3 flows/T4 钻孔避让段，合计 13 条 geom 侧断言；无参数=仅 schema 15 条） |
| flows | 流路与网表/pos 同源 | `python hardware/flowio-p1/enclosure/test_flows.py` |
| graph | 网↔槽完美匹配+flows 交叉校验 | device_graph.py 入口 |
| 全量 | 六段一键 | `firmware/twin/run_tests.sh`（自动探测 venv） |

**pneumatic schema 关键域约束（新增气动件必读）**：负压专用阀（pressure_kpa 上限 ≤0，
如 F0520B）**只允许出现在 `valve_vacuum_master` 组**，正压通用阀组 `valves` 禁止混入；
执行器 electrical.rated_v 必须全等 4.5（P1.1 定案）；泵压力窗必须严格包络全部阀压力窗；
refs 四组内唯一且不与 devices 段冲突；负测试=deepcopy 坏数据翻红 + 段残缺早退防空洞 PASS。
新断言必须带常驻负测试。

## 4. 环境铁律（血泪，违反必返工）

1. **SWIG/pcbnew**：一进程一操作，状态靠文件往返；`board.Remove()` 后再查询=毒化；
   KiCad10 层常量**非连续**（F=0/B=2/In1=4/In2=6）；zone getter 可能撒谎（用 HitTestFilledArea 多点探测，禁数顶点）。
2. **Mimosa 钩子**：源码落盘一律 Write/Edit 工具（bash heredoc 会被拦）；脚本内写文件用
   `Path.write_bytes(...)`；禁 eval/exec；提交绕行模板：
   `git -c core.hooksPath=/dev/null commit -m "<msg>[--no-verify 理由: 拦截项均为 gitignored venv 第三方测试夹具]"`。
3. **worktree**：一切改动在 `.worktrees/<branch>`；**外层目录禁 `git add -A`**（.worktrees/
   无 .git，会向上解析劫持主树 untracked——933MB 事故先例）；提交前
   `git pack-objects --revs --stdout <<< origin/main..main | wc -c` 体检。
4. **FreeCAD**：Matrix 平移在**第 4 列**（列向量）；中文脚本用 E:/FreeCAD/bin/python.exe。
5. **freerouting**：必加 `--router.optimizer.max_passes=3`（improvement_threshold=0.0 默认跑满 200 轮≈5h 空转）；
   火力：`-mp 200 -us hybrid -hr 1:1 --router.optimizer.improvement_threshold=0.0 --router.via_costs=80`；
   **DSN 必须含电源网**（剥离电源网→SES 导入清除全部电源铜）。
6. **GitHub**：>50MB 警告>100MB 拒收；大工件 gitignore+脚本再生；PAT 只在简历/（gitignored）。
7. **LCSC datasheet 下载**：wmsc 直链模式
   `https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/<YYYYMMDDHHMMSS>_<MFR>_<MPN>_<C号>.pdf`。
8. **生成物禁手编**：types.h/params_gen.js 由 fwgen 生成——改 devices.json → `python -m flowio fwgen` 重生成；
   CI 门 `tools/check_codegen.py --ci` 手编即红（修生成物=改模板源头再重生成）。

## 5. 布线收敛 SOP（route_pcb 6 阶段 + freerouting）

| 阶段 | 用途 |
|------|------|
| 1 | 平面区+GND 缝合过孔+电源焊盘过孔（净空搜索） |
| 2-3 | 网表驱动直布（驱动通道/曼哈顿） |
| 4 | SES 导入后电源重建 |
| 5 | 通用修补（DSN 导出/SES 导入的 pcbnew API 封装在本文件内，grep `dsn` 定位） |
| 6 | 定点收尾（0.25mm 栅格 A* `_auto6`，逐 rat 补线） |

节奏：每阶段后 `kicad-cli pcb drc --severity-error` **差分净减不增** + git 回滚点；drc 基线 json 存 `hardware/flowio-p1/drc-*.json`（命名 drc-<阶段>.json）；
拥挤区（如 BOOT 走廊）先挪无关走线开廊再补线；退化残段（<0.1mm）先删；
验收=0 未连 + DRC 0 + L5 T4 钻孔避让断言绿。布线只动铜，**禁动 PLACE**；standoffs 真值=`hardware/flowio-p1/standoffs.txt`（HD 孔位变更时重出）；**PLACE 若改了孔位/板边（如 HD 移位），连带触发 `devices_json_pcb` 整行**（make_case→meshes→flows→L1-L3）。

## 6. 固件开发流程（fw 域）
1. **规格源唯一**：docs/firmware-driver-spec.md（寄存器流程/三态占空比表/过压互锁）——改规格先改它；
2. 参数常量：一律 `pn_core/types.h`（**生成文件禁手编**）——真值位置
   `devices.json → pneumatic_devices._meta.drive_policy.valve`（如 full_open_hold "90%"）；
   改后 `python -m flowio fwgen` 重生成（CI 门 `tools/check_codegen.py --ci` 抓手编）。
   **行重叠裁定**：凡进三语链的参数变更走 `params_trilingual` 行（超集，含 fw_constant 全步骤+
   compare_baseline+run_tests）；fw_constant 行仅用于"不进 codegen 的拓扑/协议常量"（模板段，
   分类表 flowio/fwgen/templates.py）。**锚点联动**：selftest/场景锚点若因参数变更需更新，
   走 twin_model 行的 baseline.json 评审规则（有意变更+评审，禁静默改）。
3. 组件实现：firmware/components/pn_core（逻辑拓扑常量如 PN_PORT_COUNT 属模板段，分类表在 flowio/fwgen/templates.py）；
4. 验证：build_twin.sh 重建（exe 用 /tmp 副本法）→ twin_selftest 锚点比对 → 烧录 flash_com3.ps1；
5. 固件常量变更重走链：见矩阵 `fw_constant`。

## 7. 孪生开发流程（twin 域）
1. **模型模板**：新建模型 = 继承 `BaseModel`（params/step/reset 三方法）+ 参数从 TruthSource 视图注入（零器件常量手抄，board_model 拆分三模型是范式样本）；
2. **执行器扩展三步**（IActuator 契约：`ref` 属性 + `current(state)->A` + `effective_v(duty)->V`
   + `duty(state)->0~1`（报告钩子）；state ∈ pull_in/hold/economy/off）——盲测 test_blind_extension.py 固化：①devices.json 加真值条目（schema 谓词合规）②定义 IActuator 子类（不入工厂即测试内可注入）③注入 ElectricalModel 求解——**零改仿真器**；型号串知识只许在工厂登记点；
3. 场景矩阵：flowio/twin/scenarios.py（验收语料与模型生命周期分离）；跑 `python -m flowio twin electrical [--json]`；
4. 锚点钉值：测试锚点绑真值冻结值（r_coil 10Ω/worst 4.525A）；对拍 `tools/compare_baseline.py`；
5. C 侧孪生常量（twin_api.c 标定段如 PUMP_P_MAX 61）：属孪生标定非真值映射——分类裁定见 fwgen 分类表，勿盲目"对齐"。

## 8. 呈现域流程（web 域）
1. 组件架构：webapp/js/components/ 11 组件（Custom Elements+shadow DOM）；通信=CustomEvent（composed）+store；新增面板=新组件文件+组件契约测；
2. **ES 铁律**：import 一律 `./`/`../` 相对（唯 importmap 豁免的 `three` 裸说明符）；
3. 参数消费：`params_gen.js`（生成物禁手编）import FLOWIO_PARAMS；
4. 测试：test_webapp.js（55=47 行为+8 契约；playwright+NODE_PATH 主仓 node_modules）；视觉回归截图对照（像素差 <1% 噪声带）；
5. 站点：tools/build_site.py → site/；部署 gh-pages subtree（§12）；生产终验（首屏+assembly.json 关键数字+资源 200）。

## 9. 双阶段评审（subagent 开发流程）

每任务：实现者（TDD 红→绿+自审+commit）→ **规格合规审**（对照任务书逐条+独立验证，
防"声称绿实际红"）→ 修复 → **质量审**（Must/Should 分级，Should 也要修）→ 复审 → 完结。
实现者状态协议：DONE / DONE_WITH_CONCERNS / NEEDS_CONTEXT / BLOCKED（BLOCKED 必附证据，
换代理时携带前代理的关键情报清单）。

## 10. 器件选型 SOP

四类参数审计（电气/几何/协议/工艺）逐项标证据级（🅰一手 datasheet/🅱 多源交叉/🅲 推定待实测）；
**参数两说裁决**：多源交叉→按最坏情况兜底设计→BRINGUP 实测一锤定音（判据表先行）；
否决件留档（DFR0866/BMP180/惠州阀……）写明否决理由；硬约束=气动件全国产淘宝/1688 可购；
registry（docs/component-registry.md）六元组闭环：型号↔店铺↔一手档↔参数↔状态↔决策。

## 11. 部署 SOP

gh-pages = site 目录 subtree：`git subtree split -P site -b gh-pages-deploy &&
git push -f origin gh-pages-deploy:gh-pages`；部署后生产终验（双态截图目视+关键数字核对）。
STEP 导出前设 `KICAD9_3RD_PARTY=C:/Users/yuefe/Documents/KiCad/9.0/3rdparty`。
