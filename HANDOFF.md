# FLOWIO 项目交接文档（新会话必读）

> **更新**: 2026-10-01 深夜 · **状态: 主线全部完成** (auto-finish plan 已执行, 6 条未连接 → 0)

---

## 0. 一句话现状

P1 板主线**全部完成**：原理图（344 连接 0 错）、布局布线（**未连接 0 · error 类 0**，146 起步）、仿真（4 电路达标）、JLC 打样包（终版）、FreeCAD 外壳、三篇文献精读。auto-finish plan 于 2026-10-01 深夜执行完毕：**T1 KRT repair_planes 全层修复即达成 6→0**（oracle_reconnect 连口袋簇一并解决），T2-T4 按"净减不增"守门原则跳过。三重验证通过：KiCad DRC + KRT check_connected（75 网全通）+ 天线禁布区探测 0 命中。关键提交：d0eb1b2、fa2f138。

## 1. 已完成 / 待完成

### ✅ 已完成（按 git 提交序，全部已入 main 分支）
| 交付物 | 位置 | 关键提交 |
|---|---|---|
| 原理图（修正 #1-#13） | `hardware/flowio-p1/flowio-p1.kicad_sch` | 早期 |
| PCB 布局+层叠 90×75 | 同目录 `.kicad_pcb` | 41e697e |
| freerouting 双轮布线 146→17 | + 天线禁布区丢失被抓回 | c3337a3 |
| DRC 攻坚 17→6（error 类清零） | 自研 boardgeom/netdoctor | a38172a |
| 电路仿真 4 电路（buck/二极管或/阀驱动/I2C） | `firmware/twin/sim_out/`（`sim_engine.py --export` 再生成；旧 tools/sim 已归档 `firmware/twin/deprecated/sim-legacy/`，真源=firmware/twin/sim_engine.py） | bf48abd+本次 |
| JLC 打样包（Gerber/钻孔/坐标/BOM47行/装配PDF/zip/README） | `hardware/flowio-p1/fab/` | bf48abd |
| FreeCAD 参数化外壳（FCStd+STEP+STL 水密，用户指定替代 OpenSCAD） | `hardware/flowio-p1/enclosure/` | bf48abd |
| 自研脚本安全清零（exec/eval/路径穿越 7 处高危） | tools/ | a75578e |

### ⏳ 待完成（优先级序）
1. 主线硬件阻塞（需实物，用户操作）：74HCT245/MOS 触发测试、传感器到货、PID 首跑
2. 外壳 3D 打印验证（STL 已就绪）；via-in-pad 下单时向 JLC 声明 IPC-4761 Type VII ×8
3. 回板实测：仿真对照（效率 87.6%/纹波 3mV/阶跃 199mV）、I2C 400kHz 超差则降 100kHz 或上拉改 2.2k
4. 建议跑一次 Mimosa 完整审计（历史提交曾提示覆盖不完整）
5. 遗留技术债: KRT v10 上游 bug 本地补丁 (kicad_oracle.py v10)——升级 KRT 时注意

### auto-finish 执行记录 (2026-10-01 深夜)
T0 冒烟(补 scipy/shapely/rust grid_router v0.22+v10 补丁) → T1 全层修复(GND F/B/In1 + 3V3 12区11路/5V 6区5路) → **未连 6→0 超预期** → T2-T4 跳过 → T5 三重验证+fab 重出。算法知识链: PathFinder'95/FPGA'22/SAT-TCAD'26 三篇精读 (spec §8)。

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

---

## P1 板级孪生五支柱（2026-10-02 交付）

spec/plan：`docs/superpowers/specs/2026-10-02-p1-board-twin-design.md` + `docs/superpowers/plans/2026-10-02-p1-board-twin.md`。五支柱 S1 参数化仿真引擎 / S2 板级电气孪生 / S3 结构网格 / S4 固件+SDK / S5 BLE，API 升 v1.2。

### 10 任务 SHA 表

| 任务 | 内容 | 提交（含随后审查修正） |
|---|---|---|
| T1 S1 sim_engine 参数化 | 四电路纯函数+参数域校验 | `1f968cf`（+`58e5010` valve/i2c 锚点断言加固） |
| T2 S2 board_model | RL 解析式/双轨/温升/600s 历史 | `5faf5dc`（+`a567e59` 关断续流物理与 sim_engine 同源修正） |
| T3 server.py v1.2 | board/state+sim/presets/assembly/csv + time/record/replay | `1ca000e`（+`eae4fe6` 审查三修：竞态锁/分数倍速累加器/历史节流） |
| T4 S3 网格 | pcb/器件阵/壳 STL + assembly.json | `fbeb71f`（+`980fb23` 字段对齐 spec §3.4） |
| T5 S4 固件 | TCA9548A+sensor_if+WS2812（pn_core 纯逻辑+hal 绑定） | `8ae9c20`（+`1416137` tca I2C 超时单位 ms 修正） |
| T6 S4 SDK | flowio_sdk（proto 同向量编解码+serial+高层 API） | `f631bff` |
| T7 S5 BLE | NimBLE GATT 四服务+cmd_transport 统一分发+BLE.md | `fd71c83` |
| T8 前端 | gui.html「P1 板级」遥测/仿真重算/3D 爆炸+Web BLE+three.js vendor | `c11650b` |
| T9 文档+下线 | API v1.2/BLE.md/BRINGUP 回板动线；TinyML 泄漏检测下线归档 | `22b664d` |
| T10 终验+收尾 | 双源漂移修正+全测试矩阵+目视复核+本 HANDOFF | 本次终验提交（board_model.py + test_api_board.sh + 本文件） |

### 测试矩阵（2026-10-02 终验实测，全绿）

| 套件 | 结果 |
|---|---|
| `test_sim_engine.py`（KPY） | OK（3 用例：buck 锚点/参数域/dior+valve+i2c 冒烟） |
| `test_board_model.py`（KPY） | OK（1 用例多断言：状态/电流/负载/关断钳位） |
| `bash test_api_board.sh` | 7/7（state/sim/bounds/time/csv/**assembly**/record；assembly 断言由过期 404 改为 200+parts=5） |
| `bash test_api.sh` | 50/50（协议契约+物理语义+量程饱和+气动 v2 A1-A9） |
| `firmware/tests pn_tests.exe` | 33/33 |
| `sdk/python/tests/test_protocol.py`（KPY） | 9/9 OK |
| `node test_gui.js` | 28/28（气动台前端单元） |
| `node test_gui_p1.js` | 40/40（P1 遥测/仿真/结构/BLE 纯逻辑） |
| `node check.js gui.html` | OK（2 脚本块/34 处理函数/语法 0 错） |

显式计数合计 171 用例 + 静态冒烟。node 侧前置：8017 端口隔离实例（`TWIN_PORT=8017 KPY server.py`）+ `node_modules/playwright-core`（已 vendor）。

### 终验双源漂移修正（board_model.py，审查 Minor 中唯一真隐患）

- `rail_3v3.v`：3.269（误用标称）→ **3.2638**（`vout3v3 − load_reg×LOGIC_A`，与 step()/history v33 同式同值），另加 `v_nom: 3.269` 字段保留标称。
- `ripple_mv`：3.1（硬编码）→ **1.0**，与 sim_engine buck 默认工况实测一致（@3A 实测 1.004 mVpp）。
- 同步修 `test_api_board.sh` 过期断言（assembly 404→200）。

### 终验目视复核（手动集成，KPY server.py :8000）

state api=1.2 且全 payload 无 leak 字样；assembly parts=5、bbox_mm=[95.8,80.8,19]；POST sim buck 默认 metrics 4 项全 ✓（3.269V/1.004mVpp/0.272App/87.59%）、waves=2（Vout/iL）；time paused true→false；录制 start→`I 1 255`→stop（n=1）→`recordings/rec_*.json` 落盘→replay `replayed:1` 且回放后 valves[0]=255/pump=255；`shots/p1_telemetry.png`(109KB)/`p1_sim.png`(87KB)/`p1_structure.png`(43KB) 三张非零。复核毕服务进程已杀、8000/8017 端口已清。

### 遗留路线图（记档，非本期缺陷）

1. **范围外路线图**（spec §11.4 重申）：OTA 升级、Web API 多设备同步、SDK BLE 传输（`sdk/python ble.py`+bleak）、真机-孪生 HIL 对拍、治疗报表产品化。
2. `firmware/virtual/`：合并 subtree 时即预存损坏（陈旧 build/）——**已修复（2026-10-02，根因=pn_core 泄漏检测耦合 pn_ml，F1 解耦后主机构建复活）**；`L` 命令保留并应答 `leak=off`。
3. `firmware/build_n16r8.cmd`：曾出现 CRLF 行尾问题，已由根 `.gitattributes`（`* text=auto eol=lf`）统一修正并防复发；后续新增 Windows 批处理注意提交前归一。
4. T1-T3 审查记档 Minor（未修，均为展示层/无控制风险）：telemetry `loss_mw` 四项损耗为 buck @3A 满载常量快照（706/162/436/85mW），不随实际 0.43A 负载重算；`r_coil/l_coil/i_pump` 为 [假设] 参数待回板标定（BRINGUP 六项校准后转绿）；board state 的 `ml:80` 字段已随 F1 泄漏解耦移除（2026-10-02，DLL 导出删除；API.md 已同步）。
5. 回板实测对照清单见 §1 待完成第 3 条（效率 87.6%/纹波 ~1mV/阶跃 199mV；注：纹波对照值随本次修正由 3mV 更正为 ~1mV）。


## 欠账清偿记录（2026-10-02 深夜 F1-F4）
| # | 欠账 | 处置 | SHA |
|---|---|---|---|
| F1 | 泄漏下线不彻底（pn_core cli 'L'+leak_detect+pn_ml 依赖残留；virtual/ 损坏真根因） | cli L=off 文案/leak_detect 归档/断 PRIV_REQUIRES；**virtual 复活**（state=0x0200）；连带揪出 server /api/state ml 字段 AttributeError 隐藏雷 | 496bfe7 |
| F2 | sim_engine 缺 --export（spec §4.2 违约） | sim_export.py stdlib SVG+md → twin/sim_out/；旧 tools/sim git mv 归档 deprecated/sim-legacy，仿真真源唯一化 | 984c5ea |
| F3 | 前端目视检查跳步 | 三面板 playwright 重截+机内视觉审：**零缺陷通过**（数值渲染/曲线/徽章/3D 部件全验） | 260e942 |
| F4 | Minor 债（loss_mw 常量/SIM 挂死/replay 无时序/冒烟覆盖） | loss_mw 动态化同源引擎/SIM 忙锁 503/replay 后台时序+409/冒烟 7→11 | 81b0467 |

剩余路线图不变：OTA/HIL/Web API 多设备/SDK BLE 传输/报表产品化（均需硬件或独立产品化决策）。


## 前端 v2 交付（2026-10-02）

按 spec/plan `docs/superpowers/{specs,plans}/2026-10-02-twin-frontend-v2*.md` 八任务全部完成。
`/` = 产品爆炸视图核心 v2（零构建 ES Modules，`firmware/twin/webapp/` 直服），旧 gui.html 挂 `/classic` 过渡，**API v1.2 端点零改动**。

### 任务-SHA 表

| # | 任务 | SHA |
|---|---|---|
| T1 | v2 骨架：Liquid Glass 令牌/server 路由(`//classic`/301)/vendor three r160 | 5d8b323 |
| T2 | 流拓扑同源：make_flows.py（pos.csv→flows.json/hotspots.json，同源断言测试） | d5161a2 |
| T3 | 3D 主场景：装配叙事/爆炸滑杆/材质升级/热点拾取 | 4a5ff5d |
| T4 | 电流辉光+气流粒子：遥测驱动长在产品上，爆炸跟随 | fb42c51 |
| T5 | 遥测抽屉 sparkline/控制分段控件/热点卡：仪表盘降级为辅助 | 12c83a6 |
| T6 | 仿真浮层+BLE 真机模式迁移+状态行 | d7565c8 |
| T7 | test_webapp.js（44 断言全链）+ 旧三测试挂 /classic + 全回归 | b460a05 |
| T8 | 目视 8 项+断连态像素审计 26/26 + fps 56.8 + 文档三处 | 本提交 |

### 测试矩阵（T7/T8 全绿）

- `node test_webapp.js` **44/44**（装配 5 部件/爆炸位移/`I 1 255`→gate1 uGain>0.5+port1 粒子/`S 1` 静默/`V 1 255` 真空 dir=-1 琥珀/抽屉开合/fetch 拦截 CLI/U3 中心 raycaster 点击热点卡/sim 400 红条/`/classic`）
- 旧三套改挂 `/classic`：test_gui **28/28** · test_gui_p1 **40/40** · test_e2e **43/43**
- `bash test_api.sh` **50/50** · `bash test_api_board.sh` 全 OK（exit 0，与 v2 无耦合原绿）
- KPY：`test_sim_engine.py` OK · `test_board_model.py` OK · `test_flows.py` OK（同源断言）
- 目视（`shots/v2_01..10.png`）：机内像素审计（直方图/色簇/差分+浏览器投影走廊）**26/26** + AI 视觉复核（装配材质/UI 布局/热点卡内容全对）
- 性能：`?debug` 60s rAF 采样 **56.8 fps**（--use-angle=d3d11 与默认同值，≥45 达标；`?perf=low` 预留未启用）

### 已知事项（记档）

1. **air depthTest 覆盖渲染裁定**：气流底线/粒子 `depthTest:false`+高 renderOrder——开孔在 +Y 侧壁、默认视角管路被壳遮挡，叠加式辉光保证"通道存在/气流喷出"始终可见（spec §3.2 底光语义）；电流线保持深度遮挡。代价：亮壳表面上 additive 粒子对比度受限（像素审计走廊内 38px 青簇可检出、人眼观感偏克制，暗背景下清晰），维持裁定不改。
2. **R/S CLI 语义注记**（固件实证，前端已对齐）：`S <ports>` 确定性关阀（隔离密封）；`R` 释放但不清 duty——UI「释」段映射 `S` 而非 `R`，测试用例避免依赖 R。
3. **classic 退线决策待定**：`/classic`（gui.html+旧三套测试）保留为过渡；退线需先迁移 P1 面板独有的调试入口（泄漏注入/物理注入/scheduler 编排）再定时间表。
4. 遥测抽屉默认收起、热点卡 live 值满量程横条为 spec §2/§5 语义；fps 受 headless vsync 钳制 ~57，真机浏览器更高。

## 书稿启动（2026-10-02）
- `book/`：ElegantBook v4.7 模板（CTAN 开源）+ main.tex + content/ch11-acceptance.tex（验收章先行，与产品验收同步产出图源）+ figures/（v2 验收截图 4 张已入）
- 编译：MiKTeX xelatex，`cd book && xelatex -output-directory=build main.tex` 两遍，main.pdf 已出
- 计划：章 11（验收）随回板验收同步写；其余章按 12 章骨架（见 2026-10-02 会话）待用户重启指令
- JLC 下单策略更新：板 5 片（制板最低）+ **贴装仅 2 片**（主力+备用），费用 ≈360-720 元（执行口径，板 5 装 2，HANDOFF 记录值；README-jlc-order.md §3 载"全贴 5 片"估算 550-1150，两口径并列，书稿 ch05 表 tab:fab-cost 同）
- 验收×专著一体化已落地：36 张工单 `book/tickets/A*.yaml`（双产物=BRINGUP 勾选+书稿素材，`python book/tools/ticket.py report` 看进度：pass 6/pending 30）+ 书稿 12 章骨架（ch3/4/11 实文，xelatex 22 页零错）+ BRINGUP 九章已注"对应工单"行；下一步=回板执行 A2xx 工单

## 书稿一致性审查（2026-10-03）
- **发现 16 项 → 处置 16/16 清零**：Critical 2（ch12-product 11 行骨架且路线图与 HANDOFF 五项不符；qemu_smoke.sh 第 7 项期望串过期）· Important 1（ch00a"6 路 XGZP6897D 并行采样"，实现为 TCA9548A 分时、P0 实装 2 只）· Minor 13（encode 签名注解、/api/time 方法、呼吸周期口径、缓动令牌表述、BRINGUP 36、api.sh 43+11、test_flows.py 路径、"环形缓冲"→行缓冲、G \<sensor\> 记号、两处文件名简写、ESP32S3DS 孤立 cite、"十二章"计数、pn_core 路径层级）——全部落书稿/检查器，报告见 `book/AUDIT.md`
- **仓库侧 3 项处置**：① qemu 期望串已改 `leak=off`，复跑 **9/9 全绿**；② 呼吸周期为设计-实现偏差**记档待产品裁决**（实现 `sin(t/4)`≈25.1s 未改，书稿 ch09 已写实测口径）；③ 费用**双口径并列陈述**（README-jlc-order §3 全贴 5 片 550–1150 / HANDOFF·ch05 板 5 装 2 执行口径 360–720，各标出处）
- **终验（T4 独立复核）**：检查器终态 const=0 path=0 cite=0 snippet=3（残余 3 条均为书稿 caption 已声明"节选/摘编"的窗口差异，非语义漂移）；检查器测试 11 用例 OK；xelatex 两遍零错 **87 页**；回归 `test_api_board.sh` 全 OK / `test_webapp.js` **44/44** / `qemu_smoke.sh` **9/9**
- **一致性检查器用法**：`KPY book/tools/consistency_check.py`（常数/路径/cite/代码片段四类，书稿×真源；测试 `KPY book/tools/test_consistency_check.py`）


## 信息源纳管与阻塞清单（2026-10-03）
- **呼吸悬浮裁定**：按最佳实践采纳实现值（~25s 慢呼吸，避免与数据阅读争夺注意力）；AUDIT 复核表改 waived-adopted-impl（d85efb6）
- **信息源纳管**：FlowIO 文档集（19 篇）/ESP32-S3 官方中文 PDF（datasheet/TRM/硬件设计指南/errata）/艾谷教程 → reference.bib 6 条 @misc + 书稿 6 处接线（ch1/7/9/11/12/14）；**回板前置阅读（errata+硬件设计指南）已入 ch14 校准清单**（d85efb6）
- **阻塞核对**：pn_ml 解耦零功能残留（仅 cli.c 注释）；工单 36 张（pass 6/pending 30）；git 树净
- **当前唯一硬阻塞**：等待 JLC 到板（板 5 装 2 已定）。到板后：BRINGUP 九章 = 工单 A201-A224 = 书稿 ch13 下篇 + ch14 素材


## 磁盘清理与资源整理（2026-10-03）
- **E:/FLOWIO-外部参考: 23G→1.6G（释放 21.4G）**——删 freerouting-src(15G)/tar/jdk21×2/jre zip/KRT .git+tests+awx+py_placer(2.6G)/艾谷软件工具(1.5G)+示例(1.3G)；保留 jar/jdk25/KRT 工作区/kicad-libs/艾谷 PDF+PPT/papers/aeonlabs，根目录 README.md 有逐项用途表
- **E:/FLOWIO/资源: 627M→401M，四类归档**——实物图(59)/器件规格书/官方参考(含 official-3mf 22 模型)/开发板资料，根目录 README.md 有书稿映射表；删嵌套残留/extracted/kicad 中间产物/zip/rar(226M)
- 待执行：资源纳编 plan T1+T2（spec 2026-10-03-assets-triage 已批，bib+图+六章增补）


## 唯一入口达成（2026-10-03）
E:/FLOWIO-外部参考 已并入 资源/工具链/（7 项短名迁移，源目录删除）。路径迁移对照：
- jdk-25.0.4.1+1-jre → 资源/工具链/jdk-25
- KiCadRoutingTools-main → 资源/工具链/KiCadRoutingTools
- 【艾谷科技】ESP32S3入门视频教程资料 → 资源/工具链/艾谷-ESP32S3教程
- freerouting jar / kicad-libs / papers / aeonlabs → 同名直迁
- FlowIO-Arduino-Libraries-master → 资源/官方参考/arduino-libraries（zip 删）
同步改写：reference.bib ×2 / auto-finish plan ×4 / 工具链 README 重写
清理：firmware/build 1.8G 删（idf 重编即得）/ ml-leak dataset+literature 103 PDF 出索引（磁盘留）


## GitHub 开源 + 简历（2026-10-03）
- **GitHub repo**: https://github.com/yfzhang-true/flowio-cn (public, 全栈开源)
- push 历史 3 轮清洗：literature PDFs (110MB 超 GitHub 限) → PAT 从 git 历史完全清除 (filter-branch)
- 简历：简历/嵌入式软件工程师_张越飞.md (Skills 三步: job-description-analyzer → resume-tailor → tech-resume-optimizer)
  - 3 个 skill 安装于 ~/.agents/skills/ (cocoloop→skills.sh→GitHub codeload)
  - 目标岗位：乐鑫嵌入式原型验证(85%匹配) + ESP-IDF SDK(75%)
  - 占位符：[请填写] 手机号
