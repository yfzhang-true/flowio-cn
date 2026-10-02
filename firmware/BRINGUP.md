# BRINGUP.md — P1 回板动线清单（固件侧视角）

> 范围：`docs/superpowers/specs/2026-10-02-p1-board-twin-design.md` §8.5（回板验证清单）
> + §10.2（电气校准 6 项）+ §10.1（泵三实验）合流。每项跑完打勾并记录产物。
> 硬件假设：ESP32-S3-N16R8（YD-ESP32-S3），阀 GPIO 4/5/6/7/10/11/12、泵 21、I2C SDA=8/SCL=9、WS2812=48。
> 串口 115200（CH340K 丝印 COM 口）；上电 30s 内按住 BOOT（GPIO0）≥1s 可禁用呼吸演示循环。

## 1. CH340K 烧录与自动复位

- [ ] `powershell build_n16r8.ps1` 全量构建通过（16MB Flash / 8MB PSRAM / 240MHz）
- [ ] `powershell flash_com3.ps1`（esptool 直烧 COM3 @460800，`--before default_reset` 自动进下载模式）完成三镜像：bootloader@0x0 / partition-table@0x8000 / flowio_p0.bin@0x10000
- [ ] 烧毕 `hard_reset` 自动重启，串口见到 `[BOOT] hal init...` → `FlowIO-compatible P0 ready. state=0x0000`
- [ ] **产物**：flash_output.log 片段（含 hash 校验行）贴回本节

## 2. 74HCT245 / MOS 触发

- [ ] 串口发 `O 1` / `C 1`，示波器/万用表确认 74HCT245 输出侧随 GPIO4 电平翻转（3.3V→5V 电平迁移正确）
- [ ] 确认 AO3400 栅极波形干净（无振荡），导通时 Vds 接近手册值（见 §7 RDS 项）
- [ ] **产物**：波形照片 + 测得 Vds 数值记录

## 3. TCA9548A 五通道实测扫描

- [ ] 串口发 `W`（bring-up 诊断：I2C 全总线扫描），期望每通道报 0x58（XGZP）而空通道仅 0x70（TCA 自身）
- [ ] `P` 命令双传感器读数非错误码（实测 kPa 或 ABSENT 明确区分）
- [ ] **产物**：`W` + `P` 的串口输出贴回

## 4. WS2812 点亮

- [ ] 上电后 `[HAL] ws2812@GPIO48 ready`，IDLE=呼吸蓝
- [ ] 发 `I 1 255` → 转绿（RUNNING）；`S 1` → 回蓝；注：ERR=红闪 / HOLD=青 映射表见固件常量
- [ ] **产物**：状态灯随命令切换的短录像/描述

## 5. 8 阀全功能

- [ ] 逐路 `O <mask>` 掩码扫描（1/2/4/8/10/INLET/VENT——阀 7 只 + 泵共 8 执行器），听阀咔哒、看状态字位
- [ ] `I 31 255` 全充 → `V 31 255` 抽 → `R 31` 释放 → `S 31` 保压，`T` 查状态字全程正确
- [ ] **产物**：`T` 输出序列记录

## 6. I2C 速率决策

- [ ] 首选 100kHz（当前固件默认，`hal_esp32.c` scl_speed_hz=100000）实测 tr/波形干净即保持
- [ ] 需提速时 400kHz 须示波器量 tr（上拉强度/线长决定），不达标不切换
- [ ] **产物**：示波器 SCL/SDA 截图 + 结论（100k 或 400k）

## 7. 电气校准 6 项（spec §10.2 表 → 改 `twin/board_model.py` BOARD_PARAMS → UI 黄徽章转绿）

| # | 参数 | 现值来源 | 回板校准法 | 完成 |
|---|------|---------|-----------|------|
| 1 | 阀线圈 R=14Ω / L=25mH | 行业典型值（假设） | 万用表测 R + LCR 表测 L，改 BOARD_PARAMS | - [ ] |
| 2 | AO3400 RDS=40mΩ@3.3V | 数据手册曲线 | 示波器 Vds 波形反推 | - [ ] |
| 3 | buck ESR=45mΩ / Cout | 仿真标称 | 示波器纹波实测反推 ESR | - [ ] |
| 4 | 负载调整率 / 效率 87.6% | 仿真套件输出 | 回板 4 线法效率实测 | - [ ] |
| 5 | θja（MOS 350 / buck 130 / ESP32 35 ℃/W） | 封装热阻手册值 | 红外/热电偶对照修正 | - [ ] |
| 6 | ESP32 逻辑电流 0.43A | 峰值估算 | 电流钳实测（含 WiFi 活动系数） | - [ ] |

- [ ] 六项实测后更新 BOARD_PARAMS + 同步金样单测（`test_board_model.py`），孪生遥测面板"模型参数：理论值（未本机标定）"黄徽章转绿
- [ ] **产物**：实测值对照表（本表扩展列）+ board_model.py diff

## 8. BLE 三步（契约：`twin/BLE.md`）

- [ ] nRF Connect（手机/App）扫描到广播名 `FLOWIO-P1-<序列后缀>`（just-works 配对）
- [ ] 向 Command 服务 cmd 特征（write，UUID 后缀 0002）写 0xA5 帧（≤20B）→ resp 特征（notify，0003）收到应答帧
- [ ] 订阅 Telemetry state 特征（notify，0005，写 notify_en=1）→ 10Hz 20B state 帧（state u16 + 5×pressure i16LE(kPa×10) + tick u16）
- [ ] **产物**：nRF Connect 截图（四服务树 + notify 流）

## 9. 泵三实验（气动参数标定，`twin/calibrate_pump.py`）

- [ ] 实验A 充气死点：堵死充气口（或全密封），`I 31 255` 30s 每秒记录 sensors[0] → CSV
- [ ] 实验B 真空死点：堵死气路，`V 31 255` 30s 每秒记录 → CSV
- [ ] 实验C 升压曲线：接实际执行器容积，`I 1 255` 从 0 到死点每 0.5s 记录 → CSV
- [ ] `python calibrate_pump.py <csv>` 拟合 → 按输出改 `twin_api.c` PUMP_* 常数
- [ ] **产物**：三份 CSV + 拟合输出 + twin_api.c diff

## 完成标准

全部勾选后：本文件无空 checkbox；电气黄徽章转绿（§7）；气动常数换本机实测值（§9）。
