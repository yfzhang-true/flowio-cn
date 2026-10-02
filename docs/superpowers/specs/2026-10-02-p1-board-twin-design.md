# FLOWIO-CN P1 板级数字孪生 + 仿真仪表盘 + 3D 爆炸视图 — 设计规格书

> **日期**: 2026-10-02 · **状态**: 待用户审查
> **前置**: 气动孪生 P0 (gui.html + server.py + pn_twin.dll, API.md v1.1) 运行中；PCB 终版 (未连 0/error 0)；仿真套件 (4 电路)；FreeCAD 外壳 (上下壳 STL 水密)
> **宪法第七章**: API.md 是前后端唯一契约来源，本 spec 的 §3 定稿后回写 API.md → v1.2

---

## 1. 目标与范围

把"产品=板+固件+**结构件**+孪生"整体装进现有孪生 Web 控制台，三根支柱：

| # | 支柱 | 一句话 |
|---|---|---|
| S1 | 仿真结果仪表盘（参数可调实时重算） | 四电路 (buck/二极管或/阀驱动/I2C) 参数表单→后端重算→波形+指标+判定 |
| S2 | P1 硬件数字孪生（与气动联动） | 阀开→线圈电流 τ 上升→buck 负载/纹波/轨压/温升实时推演+历史曲线 |
| S3 | 3D 爆炸视图动画 | Three.js 全套网格 (上下壳+PCB+器件方块阵) 爆炸滑杆+自动播放+旋转缩放 |

**不做** (YAGNI)：多用户/鉴权、数据库持久化、模型 C 导出 (预留接口形态)、WebGL 降级 (显示提示文字)、器件方块阵做精确 3D 模型 (按封装高度分档的近似块)。

## 2. 架构

```
gui.html (现有气动台 + 新顶层标签页 "P1 板级", 内含三子面板: 遥测/仿真/结构)
   │  HTTP+JSON + 静态文件 (API.md v1.2)
   ▼
server.py  ——— 运行时切换: KiCad 自带 python (numpy 2.4.2 + ctypes 双能力)
   ├─ 既有 v1.1 端点: /api/state /api/cmd /api/reset /api/sim /api/leak / /gui 保留; /api/leakdetect **下线** (见 §12)
   ├─ board_model.py (新)   ← 100ms tick: 读 pn_twin.dll 阀/泵状态 → 板级推演 → 环形历史 600s
   ├─ sim_engine.py  (新)   ← 参数化四电路模型 (从 tools/sim 重构——已归档, 真源=本文件)
   └─ /lib/three.min.js + /meshes/*.stl (静态)
```

**决策记录**: 仿真/板级模型住 Python 侧 (用户已批)；运行时统一为 KiCad python，启动命令 `E:/Program Files/KiCad/10.0/bin/python.exe server.py`（写进 README 与 API.md §0）。

## 3. API v1.2 增量契约（定稿后回写 API.md）

### 3.1 `GET /api/board/state` — 板级实时遥测
前端 200ms 轮询（与气动同频）。响应：
```json
{ "tick": 123456, "uptime_s": 789.0,
  "valves": [ {"on": true, "i_A": 0.356, "p_w": 1.78}, ×8 ],
  "pump": {"on": false},
  "rail_5v": {"v": 4.62, "load_a": 1.42, "p_w": 6.56},
  "rail_3v3": {"v": 3.269, "load_a": 0.43, "ripple_mv": 3.1, "buck_eff": 0.876,
               "loss_mw": {"sw": 706, "dcr": 162, "diode": 436, "switching": 85}},
  "board_p_w": 8.9,
  "temp_est_c": {"cpu": 41.2, "buck": 47.8, "mos_max": 33.4},
  "history": { "t": [..], "rail_5v_v": [..], "rail_3v3_v": [..], "load_a": [..], "valve_i": [[..]×8] } }
```
`?since=<tick>` 增量取历史；无 since 返回全量 600s 环形缓冲（100ms 采样，6000 点/通道，波形通道降采样至 ≤2000 点返回）。

### 3.2 `POST /api/board/sim` — 参数重算
body: `{ "circuit": "buck|dior|valve|i2c", "params": {...} }`，响应：
```json
{ "circuit": "buck", "params": {...回显}, "metrics": [ {"name":"输出电压","value":3.269,"unit":"V","verdict":"✓"} ... ],
  "waves": [ {"name":"Vout","t":[..],"y":[..],"unit":"V"}, ... ], "notes": ["..."], "elapsed_ms": 812 }
```
- 参数集与合法域（越界→`400 {"error":"参数越界: vin 6.0 > 5.5"}`）：
  - buck: `vin 3.8-5.5, iload 0.1-3.0, l_uh 4.7-10, cout_uf 47-220, esr_mohm 10-100, fsw_khz 300-1000`
  - dior: `vdc 4.4-5.5, vusb 4.4-5.5, iload 0.05-0.5`
  - valve: `pwm_hz 1-50, duty 0.05-0.95, r_coil 8-30, l_mh 5-60, rg 47-330`
  - i2c: `rp_k 1.0-10, cbus_pf 30-300`
- 计算超时 3s → `504`；未知 circuit → `400`。
- **重算是无状态纯函数**（不改 board_model、不落盘）。

### 3.3 `GET /api/board/sim/presets` — 预设参数集
响应 `{"buck": {"default": {...}, "worst_load": {...}}, ...}`（default=BOM 实值，worst=压力工况）。

### 3.4 `GET /api/board/assembly` — 结构件清单（3D 爆炸视图清单）
```json
{ "parts": [ {"id":"case_top","name":"上壳(通风栅)","stl":"/meshes/case_top.stl",
              "color":"#9e9e9e","explode":[0,0,28],"opacity":1.0},
             {"id":"pcb","name":"P1 主板","stl":"/meshes/pcb.stl","color":"#0d6b3f","explode":[0,0,0]},
             {"id":"case_bottom","name":"下壳(铜柱)","stl":"/meshes/case_bottom.stl","color":"#757575","explode":[0,0,-16]},
             {"id":"parts_F","name":"器件阵-顶面","stl":"/meshes/parts_f.stl","color":"#c62828","explode":[0,0,12],"opacity":0.95},
             {"id":"parts_B","name":"器件阵-底面","stl":"/meshes/parts_b.stl","color":"#1565c0","explode":[0,0,-8]} ],
  "bbox_mm": [95.8, 80.8, 19], "assembly_note": "M3×2 螺丝自攻入下壳铜柱" }
```


### 3.6 `GET/POST /api/time` — 孪生时间控制（差距项 #5）
POST body `{"paused": bool, "speed": 0.25-4.0, "step_once": bool}` → 回显当前 `{api, paused, speed}`；GET 返回当前状态。暂停时 tick_loop 空转，step_once 单步一个 50ms tick，speed 为 tick 倍速。

### 3.7 `POST /api/record` + `POST /api/record/replay` — 场景录制回放（差距项 #4）
- record: `{"action":"start"|"stop"}`；start 起录（复用 /api/cmd 入口旁路环形缓冲），stop 落盘 `recordings/rec_HHMMSS.json`（事件数组 `[{t, cmd}]`），回 `{recording, n}`。
- replay: `{"events":[...]}` → 逐条注入 `pn_twin_command` → 回 `{replayed}`。

### 3.8 `GET /api/board/history/export` — 遥测 CSV（差距项 #6）
`text/csv`：表头 `t_s,rail5v_v,rail3v3_v,load_a` + 600s 全量行。

### 3.9 版本字段（差距项 #8）
所有 v1.2 新端点响应含 `"api": "1.2"`；v1.1 既有端点不动（避免破坏 gui 现页）。

### 3.5 静态资源
`/lib/three.min.js`（本地打包，同 echarts 模式）、`/meshes/*.stl`（二进制 STL）。

## 4. 组件规格

### 4.1 board_model.py（S2 核心）
- **输入**: 每 100ms 从 pn_twin.dll 状态读 8 阀 + 泵布尔量。
- **阀电流**: 一阶 RL 模型 `di/dt=(V-i·R_total)/L`，R_total=R_coil+RDS(on)，τ=L/R≈1.79ms；100ms 步长下用解析式 `i(t)=I∞+(i0-I∞)e^(-t/τ)`（I∞=5V/R_total）。参数与 BOM 同源（14Ω/25mH/40mΩ），集中 `BOARD_PARAMS` 常量并注释来源。
- **轨负载**: 5V 轨=Σ阀电流+泵(0.35A 假设同阀模型)+逻辑(0.15A)；经 SS34 压降模型 (Vf=0.31+0.05·I) 得 rail_5v.v。
- **buck**: 负载=3.3V 侧 (ESP32 0.4A 峰值按 WiFi 活动系数+TCA+CH340≈0.43A)；效率按 sim_engine buck 损耗模型现算；轨压=3.269V±负载调整率(查表)。
- **温升**: 结温=环境25+P·Rθ（MOS SOT-23 Rθja≈350℃/W、buck SOP-8≈130、ESP32 模块≈35 一阶惯性 30s）。
- **环形历史**: `collections.deque(maxlen=6000)` per 通道。
- 纯函数核心（输入状态+参数→输出遥测），便于单测金样对照。

### 4.2 sim_engine.py（S1 核心）
- 从 `hardware/flowio-p1/tools/sim/`（**已归档，真源=firmware/twin/sim_engine.py**，旧目录 git mv 至 `firmware/twin/deprecated/sim-legacy/`）重构：`simlib`(SVG 绘图部分剥离到可选)、`sim_buck/dior/valve/i2c` 的 `report(md,png)` 改造为 `run(params) -> {metrics, waves, notes}`；md/SVG 输出保留为 `--export` 离线模式——`python sim_engine.py --export` → `firmware/twin/sim_out/` 5 张 SVG（纯 stdlib `sim_export.py` 绘制，无 numpy）+ `sim-report.md`（替代旧 out/ 交付物，buck_loadstep 随归档工具下线）。
- 参数校验、降采样（波形 ≤2000 点）、超时看门狗（`threading` 3s）。

### 4.3 网格生成管线（S3 数据源）
扩展 `enclosure/make_case.py` → 新增 `make_meshes.py`（FreeCAD 运行）：
- 上/下壳: 既有 STL 复制入 `firmware/twin/meshes/`。
- PCB 板体: 读 `flowio-p1.kicad_pcb` Edge.Cuts 外沿 → Part 挤出 1.6mm → STL（绿色阻焊色在清单里）。
- 器件方块阵: 读 `fab/flowio-p1-pos.csv` + 封装高度分档表（`HEIGHT_TABLE`: 端子 11 / USB-C 3.2 / ESP32 模 3.1 / XH 8.5 / SOT-23 1.2 / 0603 0.9 / 1206 0.8 / SOP-8 1.75 / 电感 4.0 / 100µF 6.5 …，注明"视觉近似"）→ 每器件一个 Box → 顶/底两面各合成一个 mesh（`Part.Compound`→STL），减少 draw call。
- 产出 5 个 STL + 尺寸校验（水密、非空），脚手架同 `check_case.py` 模式。

### 4.4 前端（gui.html 增量）
- 顶层新增标签页 **"P1 板级"**（现有气动台为第一页，互不干扰）。内含三子面板（子标签）：
  1. **遥测**: 电源树 SVG（5V→SS34×2→buck→3.3V，节点标实时值）+ 板级历史曲线（ECharts, 双 y 轴：轨压/负载）+ 8 阀电流条形。
  2. **仿真**: 四电路卡片（选卡→参数表单(预设下拉)→"重算"→波形图(ECharts line)+指标表+判定徽章）；请求中禁用按钮，错误显示 400/504 消息。
  3. **结构**: Three.js 视口——装入清单 5 部件，爆炸滑杆(0=装配态,1=全爆)+播放/暂停按钮(2s 缓动)+OrbitControls 旋转缩放+部件 hover 高亮+名称 tooltip；WebGL 不可用→提示文字。
- 轮询: 遥测面板可见时 200ms `fetch /api/board/state?since=`；切走即停（省 CPU）。
- 无构建依赖：Three.js OrbitControls 用 vendor 单文件版。

## 5. 错误处理
- sim 越界参数→400 带字段名；超时→504；引擎异常→500+traceback 摘要（本机开发工具语义）。
- board_model tick 异常不致命：记录日志、遥测冻结在最后有效值 + `"stale": true` 标志。
- 网格缺失→`/api/board/assembly` 返回 404 + 前端显示"运行 make_meshes.py 生成"。
- server 启动自检：numpy/ctypes/meshes 存在性打印到 stdout。

## 6. 测试（沿用 twin 现有测试模式）
- `test_board_model.py`（纯函数金样: 全关/单开/8开/泵启 4 态的电流与轨压断言，容差 1%）。
- `test_api.sh` 增: board/state 全量+since、board/sim 四电路 200/400/504、presets、assembly 404 分支。
- `test_gui.js`（puppeteer/检查脚本沿现有）增: P1 标签渲染、子面板切换、重算按钮态、Three.js canvas 存在性。
- 手动目视检查（用户强制惯例）: 遥测曲线随气动操作联动、爆炸动画平滑、渲染截图留档 `twin/shots/`。

## 7. 交付物清单
`server.py`(改) · `board_model.py` · `sim_engine.py` · `gui.html`(增) · `lib/three.min.js` · `meshes/*.stl`(5) · `enclosure/make_meshes.py` · `API.md`(→v1.2) · `README` 启动命令更新 · 测试三件 · 本 spec + plan

---

## 8. 第四支柱 S4：嵌入式 P1 bring-up（2026-10-02 用户裁定并入）

> 定位：板卡回板即可烧写的固件增量 + 产品承诺的上位机 SDK 骨架。**不依赖传感器到货**（真实传感器驱动与压力闭环 = 二期，到货后另启）。
> 现状依据：固件引脚已与 P1 逐脚对齐（阀 4/5/6/7/10/11/12+泵21，I2C 8/9）；缺 TCA9548A/传感框架/WS2812/SDK。

### 8.1 TCA9548A 五通道复用驱动
- **分层遵循 pn_core 契约**：`components/pn_core` 增 `tca9548.c/h`（纯逻辑：通道选择字节编码 0x01<<ch、总线扫描状态机、错误码），平台无关可主机测；`pn_hal_esp32` 增 I2C 读写实现（地址 0x70，esp-idf i2c_master API）。
- 接口：`tca_select(ch 0-4|MANIFOLD)`, `tca_scan(ch, addr_out[])`, `tca_read_sensor(ch, ...)→压力值`（sensor_if 转发）。
- 主机 mock：mock_hal 提供虚拟 TCA + 每通道一只虚拟传感器（固定/可注入读数），复用 `tests/` gcc 框架。

### 8.2 压力传感器抽象 + mock
- `sensor_if.h`：`sensor_probe(ch)→型号枚举`, `sensor_read_pa(ch)→uint32`（Pa）, 错误码（断线/超时/CRC）。
- 本期只实现 mock 型号（+数据手册就绪的一个真实驱动槽位 `#ifdef` 预留）。真实驱动=二期。

### 8.3 WS2812 状态灯（GPIO48）
- RMT 驱动（esp-idf `led_strip` 或裸 RMT，选组件依赖最少者）。
- 状态映射表（固件常量，孪生侧同步展示）：IDLE=呼吸蓝 / RUNNING=绿 / HOLD=青 / ERR=红闪 / OTA=紫。
- 进 `main.c` 10ms 任务尾部钩子，不占新任务。

### 8.4 上位机 SDK 骨架（产品交付物 "板+固件+SDK"）
- 新目录 `sdk/python/`：`flowio_sdk` 包
  - `transport.py`（serial 列举/连接/读写帧），`protocol.py`（0xA5 帧编解码——**与 pn_core proto.c 共用测试向量**，防止双源漂移）
  - 高层 API：`FlowIO.inflate(port,pwm,ms)/hold/release/vacuum/state()/sensor(ch)`
  - `examples/hello_glove.py`（充-保-释-抽循环 20 行示例）+ README 快速上手
- 本期骨架不含：蓝牙/WebSocket 传输、打包发版（pip 发布=后续）、异步 API。

### 8.5 回板验证清单（与既有阻塞合流，固件侧视角）
CH340K 烧录与自动复位、74HCT245/MOS 触发波形、TCA 实测扫描 5 通道、WS2812 点亮、8 阀全功能、I2C 100kHz 首选（400kHz 视 tr 实测）。产出 `firmware/BRINGUP.md`。

### 8.6 测试增量
- `tests/`：TCA 纯逻辑 + mock 传感器用例（通道选择编码、scan 去抖、断线错误码）≥6 例，入 21 绿基线。
- `sdk/python/tests/`：协议编解码金样（与 pn_core 同向量表双向）、transport 用 loopback mock。
- QEMU 冒烟（`qemu_smoke.sh` 既有）跑通 WS2812/TCA 初始化不崩溃。

## 9. 交付物清单（增补版）
原 §7 全部 + `components/pn_core/tca9548.*` · `pn_hal_esp32` I2C 实现 · `sensor_if + mock` · WS2812 驱动 · `sdk/python/flowio_sdk` 包 + 示例 · `firmware/BRINGUP.md` · 测试两处增量

---

## 10. 物理校准状态矩阵（2026-10-02 用户质询补章）

> 原则（与 PHYSICS-SPEC §3 同风格）：每个模型参数标注成色——**结构正确性**（方程是否物理规律）与**参数校准度**（数值是否本机实测）分开陈述，不混谈。

### 10.1 气动孪生（既有，参数表 PHYSICS-SPEC §3）
- 结构：文献驱动（多变定律+ANSI 孔口+choked flow+容积耦合），TEST-CASES 有规律形状断言 ✓
- 参数：文献/规格书锚点（61kPa、−53.3kPa、γ=1.2）+ 假设值（C_vent 无实物依据、微漏经验值、V_m/V_p 设计值）
- 本机校准：`calibrate_pump.py` 三实验协议已备，**待回板执行**

### 10.2 电气孪生 S2 board_model（本 spec 新增）
| 参数 | 来源 | 成色 | 回板校准法 |
|---|---|---|---|
| 阀线圈 R=14Ω/L=25mH | 行业典型值（BOM 未锁传感器/阀型号） | **假设** | 万用表+LCR 实测，改 BOARD_PARAMS |
| AO3400 RDS=40mΩ@3.3V | 数据手册曲线 | 手册 | 示波器 Vds 波形反推 |
| buck ESR=45mΩ/Cout | 仿真标称 | 手册 | 示波器纹波实测反推 ESR |
| 负载调整率/效率 87.6% | 仿真套件输出 | 仿真 | 回板 4 线法效率实测 |
| θja（MOS 350/buck 130/ESP32 35 ℃/W） | 封装热阻手册值 | 手册 | 红外/热电偶对照修正 |
| ESP32 逻辑电流 0.43A | 峰值估算 | 估算 | 电流钳实测（WiFi 活动系数） |

- **呈现约束**：board_model 全参数集中在 `BOARD_PARAMS` 常量块 + 逐条来源注释（与气动参数表同风格）；前端遥测面板角落固定显示"**模型参数：理论值（未本机标定）**"徽章，校准后换绿——不让演示数字冒充实测。
- **校准动线**：并入 §8.5 回板清单（BRINGUP.md 增电气节：6 项实测→改常量→徽章转绿），不新建 calibrate 脚本（calibrate_pump.py 模式已验证，电气仅 6 常数手动改+金样单测同步更新）。

### 10.3 仿真引擎 S1（四电路）
- 结构：行为级状态机（simlib 局限已在报告声明）
- 参数：BOM 实值（L1/C7/C8/R4/R5/SS34/AO3400/4.7k）——**这是全项目电气参数中最硬的一档**，因为 buck 分压比 R4/R5 就是板上实阻
- 前端重算页同样显示参数来源标签（BOM 实值/手册/假设）

### 10.4 验收
- 回板前：所有"假设"成色参数在 UI 有可视标记（黄）；spec/代码/呈现三处一致
- 回板后（二期）：BRINGUP.md 校准动线跑完，假设参数清零或转"实测"，徽章转绿

---

## 11. 第五支柱 S5：BLE 无线链路（2026-10-02 用户裁定纳入本期）

> 对标官方"任何设备无代码控制"核心卖点。P1 板载 ESP32-S3 天线，纯软件欠账。**自研 GATT 布局**（语义对标官方八服务、编码 100% 原创，符合项目宪法）；协议载荷与串口 0xA5 **单源共用**。

### 11.1 固件侧（NimBLE，pn_core 零侵入）
- 传输抽象：新增 `cmd_transport` 层——`serial_task` 与 `ble_task` 同入既有 pn_core 命令分发器；一份逻辑两个入口（孪生 dll 不受影响）。
- GATT 服务布局（自定义 128-bit UUID，命名空间从项目名派生，规则写入 BLE.md）：

| 服务 | 特征 | 属性 | 载荷 |
|---|---|---|---|
| DeviceInfo (0x180A+扩展) | fw_version / board_rev / serial_no | read | ASCII |
| FlowIO Command | cmd | **write** | 0xA5 帧（≤MTU-3，默认 20B 够用） |
| | resp | **notify** | 0xA5 应答帧 |
| FlowIO Telemetry | state | **notify** | 二进制 20B：state_word u16 + 5×pressure i16LE(kPa×10) + tick u16，10Hz |
| | notify_en | read/write | 订阅开关 |
| FlowIO Config | pwm_params 等 | read/write | 参数块（与 CLI 配置命令同构） |

- 广播名 `FLOWIO-P1-<序列后缀>`；配对 just-works（开发期），广播含电量/状态可选后续。
- 组件依赖：`esp_nimble_hci` + `bt`（sdkconfig 增 bluetooth=y, host=nimble）。

### 11.2 前端侧（Web Bluetooth）
- gui.html 顶栏增 **"连接真实设备 (BLE)"** 按钮（Chrome/Edge Web Bluetooth）：
  - 连接后**同一套 UI 状态机**：命令→BLE write(cmd)，状态→notify(state) 解析；孪生(HTTP)与真机(BLE)模式用徽章区分，防混淆。
  - 浏览器不支持→按钮置灰+提示。孪生模式永远是默认（开发不依赖硬件）。
- 10Hz notify 与现有 200ms 轮询并存：真机模式下禁用 HTTP 轮询。

### 11.3 契约与测试
- 新增 `firmware/twin/BLE.md`（GATT 服务/特征/UUID/载荷字节序——API.md 的姊妹契约，同受宪法第七章约束）。
- 主机单测：BLE 载荷编解码（state 20B 打包/解包、0xA5 over write 分帧）与串口共用测试向量。
- 真机验证入 BRINGUP.md：nRF Connect 三步（扫描→读写 cmd→订阅 notify）；QEMU 无射频，仅验证编译与初始化不崩溃。
- SDK：本期仍 serial；`ble.py`(bleak) 列路线图（连同 OTA/HIL/报表/多设备）。

### 11.4 本期范围外（路线图重申）
OTA 升级、Web API 多设备同步、SDK BLE 传输、真机-孪生 HIL 对拍、治疗报表产品化。


---

## 12. TinyML 泄漏检测功能下线（2026-10-02 用户裁定：对标 FlowIO 无此功能）

**范围 = 后端 + 接口 + 前端 全下线**，分层处置：

| 层 | 处置 |
|---|---|
| server.py | 删 `/api/leakdetect` 分支；`/api/board/state` 不含 leak 字段 |
| API.md | 删 §1.2b（leakdetect）；**保留** §1.5 `/api/leak`（物理故障注入=开发调试工具，非产品功能，v1.1 语义不变，加一行"开发工具"注记） |
| gui.html | 删泄漏检测/注入面板中的检测呈现部分（注入开关若仅服务于检测演示一并删） |
| firmware | `main.c` 删 `pn_ml_tick` 调用与 include；`components/pn_ml` 目录保留但不再被引用（构建系统零改动，git 历史留档） |
| twin 资产 | `ml_*.py / dataset/ / model/ / ml_conformance* / leak_model_int8.tflite` → `deprecated/ml-leak/` 归档（git mv，不删历史） |
| pn_twin.dll | `pn_twin_leak_detect/ml_samples` 导出保留（重编非必须，server 不再调用即功能下线） |

**对 ML-PLAN 遗产的处置**：训练管线/数据集/模型归档不删——若未来客户要求差异化可复活；PHYSICS-SPEC 的泄漏注入语义随 /api/leak 保留。
