# FlowIO-CN 数字孪生 — 前后端接口文档（API.md）

> 版本：v1.2（2026-10-02：P1 板级孪生/仿真/时间/录制端点收录；TinyML 泄漏检测端点 `/api/leakdetect` 下线——spec §12。
> 2026-10-02 晚：前端 v2 上线——入口改 `/`（webapp/），旧 gui.html 挂 `/classic` 过渡；**API 端点零改动**）
> 本文档是前后端开发的**唯一契约来源**。改接口必须同步改本文档（宪法第七章）。

## 0. 架构与端口

```
浏览器 /（v2 webapp：3D 产品场景 + 玻璃抽屉）或 /classic（旧 gui.html，过渡期）
   │  HTTP + JSON（localhost）·  v2 另取 /webapp/* 静态资源（js/css/json，零构建 ES Modules）
   ▼
server.py（:8000 用户实例 / :8017 测试隔离实例）
   │  ctypes
   ▼
pn_twin.dll（pn_core 控制逻辑【与 ESP32 固件同一份代码】+ 物理 v2 + 泄漏注入）
```

- 启动命令：`"E:/Program Files/KiCad/10.0/bin/python.exe" server.py`（KPY=KiCad 自带 Python，本机唯一装了 stdlib 之外无依赖需求的解释器；其余带 numpy 的环境亦可）
- 基址：`http://127.0.0.1:8000`（用户）；测试一律用 `TWIN_PORT=8017` 起隔离实例
- 全部接口无鉴权（本机开发工具，不暴露公网）

## 1. HTTP 端点

### 1.1 前端入口 `GET /` · `GET /classic` · `GET /gui`（301）
`/`（及 `/index.html`、`/webapp`）返回 v2 前端 `webapp/index.html`（产品爆炸视图核心）；
`/classic` 返回旧 gui.html（**过渡期保留**，退线时间待定）；`/gui` 与 `/gui.html` 301 → `/`。
静态资源：`GET /webapp/<rel>`（vendor three r16x / js / css / flows.json / hotspots.json，防路径穿越）。

### 1.2 `GET /api/state` — 状态查询（前端每 200ms 轮询）

**响应**（`application/json`）：

```json
{
  "state": 512,          // 32 位状态字（位定义见 §2）
  "valves": [0,0,0,0,0,0,0],   // 7 路阀占空比 0-255：[P1,P2,P3,P4,P5,INLET,VENT]
  "pump": 0,             // 泵占空比 0-255
  "sensors": [29.75, 0.0],     // kPa，按 XGZP 量程 ±100 饱和；传感器缺失报 -1.0? → 见 §2 注
  "ports_p": [29.7,0,0,0,0],   // 5 端口侧压力（物理 v2.1）：阀开=汇流管值，阀关=端口独立节点（含密封微漏缓降）
  "cl": "DONE",          // 闭环状态机：IDLE|RUNNING|DONE|TIMEOUT|ERR
  "err": 0,              // pn_last_error() 错误码（0=无错）
  "leaks": [0.0,0.0,0.0,0.0,0.0,0.0,0.0]  // 7 维泄漏系数 0-1（/api/leak 开发工具状态回读）
}
```

> 2026-10-02：TinyML 泄漏检测全下线（spec §12），`ml` 字段随 DLL 导出一并移除；CLI `L` 应答 `leak=off (TinyML retired 2026-10-02)`。

### 1.3 `POST /api/cmd` — 执行 CLI 命令

**请求体**：纯文本，一条 CLI 命令（命令集见 §3）。
**响应**：`{"ok": true, "out": "inflate=0\n"}`（`out` 为固件 CLI 原样回显——与真机串口输出逐字一致）。

```
curl -d 'G 7 30 0' http://127.0.0.1:8000/api/cmd
→ {"ok": true, "out": "inflate_to=0\n"}
```

### 1.4 `POST /api/sim` — 传感器物理注入（仿真专属）

**请求体**：`"<sensor_idx> <kPa>"`，如 `1 66`。置 0 复位。
超出 ±100 kPa 按传感器量程饱和（模拟真实 XGZP 行为）。
**响应**：`{"ok": true}` / 非法体 `{"ok": false}`。

### 1.5 `POST /api/leak` — 泄漏注入（仿真专属）

> 开发调试工具（物理故障注入），非产品功能。

**请求体**：`"<idx> <k>"`——idx 0-4=端口阀、5=进气阀、6=排气阀；k∈[0,1]；`reset` 清零全部。
**响应**：`{"ok": true}` / 非法参数 `{"ok": false}`。
泄漏语义（**物理 v2.1 修正**，`twin_api.c`）：
- 端口泄漏（0-4）作用于**端口侧节点**：阀开时对汇流管可见（下游连通）；**阀关时汇流管传感器不可见**（隔离容积独立衰减，读 `ports_p` 可见）；
- 进气阀泄漏（5）在阀关时半幅作用于汇流管；排气阀泄漏（6）在阀关时全幅作用于汇流管；
- **汇流管侧可见的正确工况 = `H` 诊断保压**（泵侧密封+端口保持通），不是 `S` 隔离保压。

### 1.6 `POST /api/reset` — 虚拟断电

清空：状态字、闭环状态机（锁存错误一并清除——对应真机"断电重启才能清超压锁存"）、泄漏系数、物理状态。
**响应**：`{"ok": true}`。

## 2. 状态字 `state` 位定义

| 位 | 含义 | 置位条件 |
|----|------|---------|
| 0-4 | PORT1-5 端口阀开 | 端口动作激活 |
| 5 | INLET 进气阀开 | 充气类动作 |
| 6 | VENT 排气阀开 | 放气/抽真空类动作 |
| 7 | PUMP 泵运行 | 泵启动 |
| 15 | **超压保护锁存** | 压力 >120kPa；**仅 /api/reset 可清**（真机语义=断电重启） |

`cl` 状态机：`IDLE`（未运行）→ `RUNNING`（充气中，泵满载）→ `DONE`（达目标±容差，自动关阀停泵）/ `TIMEOUT`（30s 超时中止）/ `ERR`（传感器读数失败中止）。闭环验证记录见 §5。

`sensors` 注：真机传感器缺失时 `pn_read_pressure` 返回错误，孪生侧以注入值/物理值呈现；QEMU 整固件仿真下为 ABSENT（自检输出可见）。

## 3. CLI 命令集（`/api/cmd` 请求体；与 ESP32 真机串口 CLI 完全同集）

| 命令 | 参数 | 作用 | CLI 回显 |
|------|------|------|---------|
| `I <ports> <pwm>` | 端口掩码 1-31；泵占空比 0-255 | 充气（开进气阀+泵+端口阀） | `inflate=0` |
| `V <ports> <pwm>` | 同上 | 抽真空（开排气阀+泵反向） | `vacuum=0` |
| `R <ports>` | 端口掩码 | 释放（主动排气至大气） | `release=0` |
| `S <ports>` | 端口掩码 | 停止并隔离密封端口（端口侧与汇流管隔离） | `stop=0` |
| `H <ports>` | 端口掩码 | **诊断保压**：泵侧密封+端口保持通（汇流管+下游单一密封容积，泄漏检测窗口） | `hold_open=0` |
| `O <ports>` / `C <ports>` | 端口掩码 | 纯开/关端口阀（不动作泵） | （无回显） |
| `G <ports> <target_kPa> <sensor>` | 目标压力；传感器 idx | **闭环充气**：RUNNING→达目标自动 DONE 并关阀停泵 | `inflate_to=0` |
| `X` | — | 复位闭环状态机 | `closed-loop reset` |
| `F` | — | 硬件自检（传感器检测+阀咔哒+汇流管 ΔP） | `[ST] ...` 多行 |
| `P` | — | 读全部传感器 | `sensor0=29.75 kPa` |
| `T` | — | 查询状态字与错误码 | `state=0x0200 err=0` |
| `L` | — | TinyML 泄漏检测（CLI 层保留=开发工具；Web 端点已随 spec §12 下线） | `leak=normal conf=0.98` / `leak=detecting samples=37/80` |

未识别命令回 `?`。端口掩码：`1`=仅 PORT1，`7`=PORT1-3，`31`=全部五口。

## 4. 前后端交互契约（gui.html 实现的既定行为）

| 方向 | 行为 | 频率/触发 |
|------|------|----------|
| 前端→后端 | `GET /api/state` 轮询 | ~200ms（render 调度） |
| 前端→后端 | `POST /api/cmd`（按钮→CLI 命令映射：充=I、停=S、放=R、◎闭环=G、自检=F） | 点击触发 |
| 前端→后端 | `POST /api/sim`、`/api/leak`、`/api/reset`（注入面板/断电按钮） | 面板触发 |
| 后端→前端 | 无推送；一切变化经轮询反映 | — |
| 展示规则 | 气球/叶轮/气流=前端对 state 数值的视觉解释；压力表读数= sensors[0] 原值 | — |

**真机切换契约**：前端只依赖本文件的 HTTP+JSON 协议与 CLI 命令集；把 server.py 换成 ESP32 直连网关（WiFi/BLE）后 gui.html **零修改**控真机——协议即固件 CLI。

## 5. 验证记录（证据锚点）

- 三层测试 110 项全绿（静态 1 + 接口 45 + 单元 28 + 功能 37），含闭环专项：`G 7 40 0` → RUNNING→DONE、终值 40.14kPa（40±3 达标）、自动关阀停泵；GUI 层 ◎闭环按钮 → DONE、停在 60±4kPa。复跑：`bash run_tests.sh`。
- 实时收敛演示（2026-09-22，:8018 临时实例）：`G 7 30 0` → 0.5s/3.71 → 1.0s/9.30 → 1.5s/15.17 → 2.0s/25.48 → **2.5s/30.05=DONE 泵停** → 之后密封微漏 ~-0.5kPa/s 缓降（物理真实）。
- 整固件层（QEMU esp32s3）：同一 CLI 命令集在真实固件镜像上响应一致（`bash firmware/qemu_smoke.sh`，7/7）。

## 6. v1.2 端点（P1 板级孪生 S1/S2，2026-10-02 收录）

> 启动命令（KPY）：`"E:/Program Files/KiCad/10.0/bin/python.exe" server.py`（§0 已同步）。

### 6.1 `GET /api/board/state[?since=<秒>]` — 板级电气遥测
- 方法：GET；无请求体。
- 响应：`{"api":"1.2", "rail_5v":{v,load_a,...}, "rail_3v3":{v,load_a}, ..., "history":{t,v5,v33,load,vi}}`（600s 四+一通道环形历史，0.05s 步长）。
- `?since=<秒>`：截取 `t>=since` 的历史尾部（增量拉取）；非法值忽略返回全量。
- 错误码：无（恒 200）。

### 6.2 `POST /api/board/sim` — 参数化电路仿真重算
- 方法：POST；请求体 JSON `{"circuit":"buck|dior|valve|i2c","params":{"iload":2.0}}`（可空对象=全默认）。
- 响应：`{circuit, params, metrics:[{name,value,unit,verdict}], waves:[{name,t,y,unit}], notes:[str], api}`。
- 错误码：400（未知电路/参数/超域，body `{"error":"..."}`）；504（仿真 >3s 超时保护）。

### 6.3 `GET /api/board/sim/presets` — 仿真参数域表
- 方法：GET；无请求体。
- 响应：`{"api":"1.2","presets":{circuit:{"default":{...},"bounds":{参数:[lo,hi]}}}}`——前端动态表单数据源。

### 6.4 `GET /api/board/assembly` — 3D 装配描述
- 方法：GET；无请求体。
- 响应：`meshes/assembly.json` 原样 + `api` 字段（部件 STL 引用相对 `/meshes/`）。
- 错误码：404（meshes 未生成——跑 `enclosure/make_meshes.py`）；500（JSON 解析失败）。

### 6.5 `GET /api/board/history/export` — 历史 CSV 导出
- 方法：GET；无请求体。
- 响应：`text/csv`，首行表头 `t_s,rail5v_v,rail3v3_v,load_a`，之后 600s 环形历史逐行。
- 错误码：无（恒 200）。

### 6.6 `POST /api/time` — 时间控制（暂停/倍速/单步）
- 方法：POST；请求体 JSON `{"paused":bool,"speed":0.25..4.0,"step_once":bool}`（字段均可选、可组合）。
- 响应：`{"api":"1.2","paused":..,"speed":..,"step_once":..}`（回显生效值；speed 域外钳到 [0.25,4]）。
- 错误码：无（非法值静默忽略，恒 200）。

### 6.7 `POST /api/record` — 命令录制起停
- 方法：POST；请求体 JSON `{"action":"start|stop"}`。
- 响应：`{"api":"1.2","recording":bool,"n":已录条数}`；stop 时写 `recordings/rec_HHMMSS.json`（墙钟时间戳+命令串数组）。
- 错误码：无（恒 200）。

### 6.8 `POST /api/record/replay` — 命令回放
- 方法：POST；请求体 JSON `{"events":[{"t":..,"cmd":"I 1 255"},...]}`（录制文件原样可喂）。
- 响应：`{"api":"1.2","replayed":实际执行条数}`（非 dict/无 cmd 字段的项跳过；时间轴由调用方掌握）。
- 错误码：无（恒 200）。

### 6.9 `GET /lib/*.js` — 前端第三方库静态资源
- 方法：GET；无请求体。
- 响应：`application/javascript`——echarts.min.js / three.min.js / OrbitControls.js / STLLoader.js（本地 vendor，离线可用）。
- 错误码：404（文件不存在/路径穿越，仅 `[A-Za-z0-9_.-]+.js` 白名单）。

### 6.10 `GET /meshes/*.stl` — 3D 网格静态资源
- 方法：GET；无请求体。
- 响应：`model/stl`——pcb.stl / case_top.stl / case_bottom.stl / parts_f.stl / parts_b.stl。
- 错误码：404（不存在/非法路径，仅 `[A-Za-z0-9_.]+` 且 `.stl` 后缀白名单）。
