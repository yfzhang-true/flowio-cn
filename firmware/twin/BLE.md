# BLE.md — FLOWIO-P1 BLE GATT 契约（S5，先契约后代码）

> 版本：2026-10-01 · 状态：**契约冻结**（实现 `firmware/components/pn_hal_esp32/src/ble_twin.c`，
> 载荷编解码 `firmware/components/pn_core/src/ble_frame.c`，统一分发 `firmware/main/main.c` `pn_cmd_feed()`）。
> GUI（twin Web 端 Web-Bluetooth）与固件都以本文档为唯一真源；改字段先改这里。

---

## 1. 架构

```
┌─────────────────────────┐                        ┌──────────────────────────────────┐
│  GUI（浏览器）           │                        │  ESP32-S3（YD-ESP32-S3 N16R8）    │
│                         │   BLE 4.2 (2M PHY)     │                                  │
│  Web-Bluetooth API      │◄──────────────────────►│  NimBLE 主机栈（IDF 内置组件 bt） │
│  navigator.bluetooth    │   GATT client           │        │                          │
│                         │   just-works 配对       │        ▼                          │
│  ├ DeviceInfo   (180A)  │                         │  四服务 GATT 表（ble_twin.c）     │
│  ├ Command svc  (0001)  │                         │        │                          │
│  ├ Telemetry svc(0004)  │                         │        ├ cmd write → 字节队列     │
│  └ Config svc   (0007)  │                         │        │   → pn_cmd_feed()        │
│                         │                         │        │     （与串口同一入口）     │
│                         │                         │        ├ resp ← CLI 应答行捕获    │
│                         │                         │        ├ state ← 10ms 控制节拍    │
│                         │                         │        │   每 100ms 组 20B 帧     │
│                         │                         │        └ pwm_params ↔ RAM 配置   │
│                         │                         │  pn_core 动作层 / CLI（不变）     │
└─────────────────────────┘                        └──────────────────────────────────┘
```

命令路径不新开解析器：BLE `cmd` 特征与串口 `fgets(stdin)` 汇入**同一个**
`pn_cmd_feed()`（行缓冲聚合 + 0xA5 帧翻译 → `pn_cli_process_line()`），
保证三个宿主（串口 / BLE / twin DLL）行为一致。

## 2. UUID 方案

- 自定 128bit 基址（写死，改 = 破坏兼容）：
  **`f10a5c00-0000-4b1e-9c2d-8e3a1b0f0000`**
- 派生规则：UUID = 基址末 4 个 hex 位替换为下表后缀（0001/0002/…顺序编号）。
- 代码同名宏：`pn_hal_esp32/src/ble_twin.c` 的 `PN_BLE_UUID_BASE_LE(suffix)`
  与 `PN_BLE_UUID_SUFFIX_*`；文档 §3 表一一对应。

| 后缀 | UUID（全 128bit） | 用途 |
|------|-------------------|------|
| 0001 | f10a5c00-0000-4b1e-9c2d-8e3a1b0f**0001** | Command 服务 |
| 0002 | …1b0f**0002** | 特征 cmd（write） |
| 0003 | …1b0f**0003** | 特征 resp（read+notify） |
| 0004 | …1b0f**0004** | Telemetry 服务 |
| 0005 | …1b0f**0005** | 特征 state（read+notify，20B） |
| 0006 | …1b0f**0006** | 特征 notify_en（read+write，u8） |
| 0007 | …1b0f**0007** | Config 服务 |
| 0008 | …1b0f**0008** | 特征 pwm_params（read+write，4B） |
| 0009 | …1b0f**0009** | 特征 board_rev（read，ASCII） |

DeviceInfo 服务走 SIG 标准 UUID（服务 0x180A，特征 0x2A26/0x2A25），
仅 board_rev 无标准号用自定 0009。

## 3. 服务表

### 3.1 DeviceInfo（服务 0x180A，SIG 标准）

| 特征 | UUID | 属性 | 格式 |
|------|------|------|------|
| fw_version | 0x2A26 | read | ASCII，如 `0.5.0-s5`（宏 `PN_FW_VERSION`） |
| serial_no  | 0x2A25 | read | ASCII 12 位 hex，BT MAC（`esp_read_mac(ESP_MAC_BT)`） |
| board_rev  | 0009（自定） | read | ASCII，如 `P1-N16R8` |

### 3.2 FlowIO Command（服务 0001）

| 特征 | UUID | 属性 | 语义 |
|------|------|------|------|
| cmd  | 0002 | write（with response） | 命令帧，见 §4.1；单次 write ≤ MTU−3 |
| resp | 0003 | read + notify | 最近一条 CLI 应答行（ASCII，去 `\n`）；每次新应答且 CCCD 已订阅读 notify |

cmd 帧即 `pn_core/proto.h` 的 v1 二进制帧 `[0xA5][cmd][ports][pwm][crc8]`（crc8
多项式 0x07 初值 0x00 覆盖前 4 字节）。`pn_cmd_feed()` 把帧翻译成等价 CLI 行后走
**同一** `pn_cli_process_line()`。翻译表：

| 帧内 cmd 字节 | ASCII 码 | 等价 CLI 行 | 语义 |
|---|---|---|---|
| `'+'` | PN_CMD_INFLATE | `I <ports> <pwm>` | 充气 |
| `'-'` | PN_CMD_VACUUM   | `V <ports> <pwm>` | 抽气 |
| `'^'` | PN_CMD_RELEASE  | `R <ports>`       | 释放 |
| `'!'` | PN_CMD_STOP     | `S <ports>`       | 停止/保压 |
| `'o'` | PN_CMD_OPEN     | `O <ports>`       | 开端口阀 |
| `'c'` | PN_CMD_CLOSE    | `C <ports>`       | 关端口阀 |
| `'?'` | PN_CMD_QUERY    | `P`               | 读全部传感器（pwm 字段=传感器号，本期并入全量打印） |
| `'S'` | PN_CMD_STATE    | `T`               | 回状态字 |
| `'R'` | PN_CMD_RESET    | `X`               | 闭环复位 |

CRC 错的帧静默丢弃（与 proto 流式解析器同一策略）。ASCII 明文行
（如 `I 1 255\n`）同样被 `pn_cmd_feed()` 接受——两种编码可混用。

### 3.3 FlowIO Telemetry（服务 0004）

| 特征 | UUID | 属性 | 语义 |
|------|------|------|------|
| state     | 0005 | read + notify | 20B 状态帧（§4.2），10Hz notify |
| notify_en | 0006 | read + write (u8) | 应用级遥测开关：非 0 才发 state notify（CCCD 订阅是第二道必要条件） |

打包纯逻辑在 `pn_core/ble_frame.h`：`ble_state_pack()/ble_state_unpack()`（主机可测）。
P0 现挂 2 只传感器（slot0/1），slot2–4 为 P1 预留恒 0。传感器读失败 → 该 slot 填
`0x8000`（−32768；物理量程 ±100 kPa×10=±1000，不会与之混淆）。

### 3.4 FlowIO Config（服务 0007）

| 特征 | UUID | 属性 | 语义 |
|------|------|------|------|
| pwm_params | 0008 | read + write (4B) | `[0]=pump_max_pwm`（预留，未接线）`[1]=hold_duty` `[2:4]=hold_delay_ms` LE |

P0 无现成运行时 PWM 配置接口（`PN_HOLD_DEFAULT_DUTY/…_DELAY_MS` 为编译期宏），
本期实现：**read 返回 RAM 镜像（初值=宏默认 255/170/500），write 存 RAM**；
`hold_duty/hold_delay_ms` 立即生效——10ms 控制节拍的 `pn_optimize_power()` 改读
`ble_twin_hold_duty()/ble_twin_hold_delay_ms()`（BT 关闭/QEMU 时返回默认值）。
掉电不保存（NVS 持久化留 P1）。

## 4. 载荷字节流

### 4.1 cmd 写（0xA5 帧，5B，小端无关）

```
字节  0     1      2      3      4
     ┌──────┬──────┬──────┬──────┬──────┐
     │ 0xA5 │ cmd  │ports │ pwm  │ crc8 │
     └──────┴──────┴──────┴──────┴──────┘
例：充气 端口1 PWM255 →  A5 2B 01 FF F8   ('+'=0x2B; crc8(A5 2B 01 FF)=0xF8，
与 tests/ble_tests.c 单测同实现：多项式 0x07、初值 0x00)
```

### 4.2 state 通知（20B，全部小端 LE）

```
偏移  0    2         12   14            20
     ┌────┬──────────┬────┬─────────────┐
     │ u16│ 5 × i16  │u16 │ 6B 保留=0   │
     └────┴──────────┴────┴─────────────┘
      ▲      ▲        ▲
      │      │        └ tick：ms/100 mod 65536（100ms 序号，用于丢帧检测/时序对齐）
      │      └ 压力×10（i16，kPa×10；0x8000=无效；slot2-4 预留 0）
      └ 状态字（pn_get_state() 低 16 位，位定义见 pn_core/types.h PN_SW_*）

例：state=0x0221（端口1+进气+传感器OK=0x001|0x020|0x200），
    p0=+12.3kPa(123) p1=-53.3kPa(-533) p2-4=0，tick=0x01F4：
     21 02 | 7B 00 | EB FD | 00 00 | 00 00 | 00 00 | F4 01 | 00 00 00 00 00 00
                      ▲▲▲▲
                      -533 = 0xFDEB，小端字节序 EB FD（tests/ble_tests.c 同向量）
```

`ble_state_unpack()` 校验：长度 ≥20、保留字节全 0，违者返回 −1。

### 4.3 pwm_params（4B）

```
字节  0            1          2         3
     ┌────────────┬──────────┬──────────┐
     │pump_max_pwm│ hold_duty│hold_ms LE│
     └────────────┴──────────┴──────────┘
默认：FF AA F4 01   (255, 170, 500)
```

### 4.4 resp 通知（ASCII，变长 ≤63B）

最后一条 CLI 应答行（去换行），如 `inflate=0`、`state=0x0221 err=0`。
未产生应答时 read 返回 `boot`。

## 5. 广播与 GAP

- 广播名：**`FLOWIO-P1-XXXX`**（XXXX = BT MAC 末 2 字节 4 位 hex，`%04X`）。
- AdvData（31B 内）：Flags=0x06（可发现+无 BR/EDR）+ 128bit 服务 UUID 0001（complete）；
  ScanRsp：完整本地名。GAP 服务（0x1800/Device Name 0x2A00）由 NimBLE 内建。
- 连接参数：从机默认，1 连接（`CONFIG_BT_NIMBLE_MAX_CONNECTIONS=1`）；
  断开 → 自动重新广播。
- 配对：**just-works**（`sm_io=NO_INPUT_OUTPUT`，bonding 开、MITM 关、
  LE Secure Connections 开）。密钥 NVS 持久化（`CONFIG_BT_NIMBLE_NVS_PERSIST=y`，
  断电保 bond）。本期特征不做加密强制（bring-up 期开放，真机验证后可收紧，
  见 §7）。
- MTU：主机默认请求 256（`CONFIG_BT_NIMBLE_ATT_PREFERRED_MTU`）；cmd 单次 write
  长度上限 = 协商 MTU−3；更长命令拆多次 write（`pn_cmd_feed()` 做行聚合）或走 ASCII 行。

## 6. 线程模型与时序

- NimBLE host 任务（port 自建）跑协议栈；cmd write 回调只投 FreeRTOS 队列，
  `cmd_task` 出队调 `pn_cmd_feed()`——解析/动作不占 BLE 栈时序。
- `pn_cmd_feed()` 内互斥锁：串口线程、BLE cmd_task、演示任务三处入口串行化。
- state notify 由既有 10ms `control_task` 驱动：每 10 拍（100ms）pack 一次，
  `notify_en≠0` 且 CCCD 已订阅才发送；帧内 tick 用 `esp_timer` 毫秒时钟派生。
- resp 捕获：`pn_cli_set_resp_sink()`（pn_core/cli.c）每条命令应答行转发
  ble_twin 存储并 notify（已订阅时）。

## 7. BRINGUP（真机验证清单，后续任务执行）

1. 手机 nRF Connect / Web-Bluetooth 扫描：见 `FLOWIO-P1-XXXX`，连上后四服务齐全，
   180A 读 fw/serial/board_rev。
2. 订阅 resp → 写 cmd `A5 2B 01 FF <crc>` → 板上泵启动 + resp 收到 `inflate=0`。
3. `notify_en` 写 01 → state 10Hz 20B，负压抽气时 p 呈 `EB FD` 型负数。
4. pwm_params 写 `FF C8 F4 01` → 串口 `T` 查状态，保压 500ms 后阀电压/电流下降
   （hold_duty=200 生效）。
5. 断电重启：bond 仍在（直连不重配对）；广播名后缀与 serial 一致。
6. 收紧：确认后评估给 cmd/pwm_params 特征加加密访问要求（BLE_ERR_INSUFFICIENT_AUTHEN）。

## 8. QEMU / 无 BT 环境

`ble_twin_init()` 双保险：编译期 `#ifdef CONFIG_BT_ENABLED`（BT 关闭编 stub），
运行时 `pn_hal_esp32_is_qemu()`（QEMU esp32s3 无 BT 控制器仿真，chip v0.0 检测）
→ 打印 `[BLE] QEMU …skip` 后跳过初始化，`ble_twin_tick_10ms()` 空转。
其余（串口 CLI、遥测填充逻辑）不受影响；载荷正确性由主机单测覆盖。
