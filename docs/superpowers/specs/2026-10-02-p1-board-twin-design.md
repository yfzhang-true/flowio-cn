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
   ├─ 既有 v1.1 端点全部不动 (/api/state /api/cmd /api/reset /api/sim /api/leak /api/leakdetect / /gui)
   ├─ board_model.py (新)   ← 100ms tick: 读 pn_twin.dll 阀/泵状态 → 板级推演 → 环形历史 600s
   ├─ sim_engine.py  (新)   ← 参数化四电路模型 (从 tools/sim 重构 import, 去 report 化)
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
- 从 `hardware/flowio-p1/tools/sim/` 重构：`simlib`(SVG 绘图部分剥离到可选)、`sim_buck/dior/valve/i2c` 的 `report(md,png)` 改造为 `run(params) -> {metrics, waves, notes}`；md/SVG 输出保留为 `--export` 离线模式（既有交付物不变）。
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
