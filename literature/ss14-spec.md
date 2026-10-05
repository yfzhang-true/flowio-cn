# SS14 飞轮/续流二极管 + 驱动管（P1.1 · 2026-10-05）

## SS14（MDD，C2480）——阀/泵线圈续流

- JLC 一手属性：**1A / 40V 反向 / Vf 550mV@1A / 浪涌 25A / Ir 300µA@40V / SMA(DO-214AC)**，
  基本库（装配费最低），115.7 万库存，¥0.14。
- 手册：`C2480_SS14_MDD.pdf`（3 页，文本层完好，Schottky Barrier Rectifier DO-214AC/SMA）。
- 用途：10 路执行通道各 1 只（8×0520D + 0520F + 370 泵），反向并联线圈两端。
- 校验：线圈电流最大 0520F 320mA < 1A ✓；反向 40V >> 5V 轨 ✓；泵路启动 1A 时二极管不导通主回路
  （仅续流瞬间）✓。onsemi 版 C83852（40A 浪涌）作为备选不必——续流无浪涌应力。

## AO3400A（Alpha & Omega）——Q1-Q14 全部低边开关

- 手册已在库：`资源/器件规格书/数据手册/AO3400A_datasheet.pdf`（用户供）。
- 要点：30V / 连续 5.7A / Vgs(th) 0.65~1.45V / 3.3V GPIO 直驱 RDS(on)≈28mΩ@4.5V /
  SOT-23 / 0520F 320mA 与泵启动 ~1A 均远低于额定。
- 泵路 Q14 栅极 PWM：ESP32-S3 ledc 25kHz（高于人耳音频），栅阻 100Ω + 下拉 100k。

## 已在库无须再找的（本轮核对）

| 器件 | 状态 |
|------|------|
| 0520D / 0520F | ✅ 用户供 PDF（资源/器件规格书/）+ valve-0520df-spec.md |
| XGZP6897D-C | ✅ V1.1 PDF（资源/器件规格书/ + literature/xgzp6897d-c-datasheet-v1.1.pdf） |
| TCA9548A | ✅ literature/tca9548a-datasheet-ti.pdf + cjmcu-9548 模块图（仅 8 传感方案需要） |
| WAFER-XH2.54-4PZZ | ✅ C5359632 规格书（数据手册/） |
| TPS54331 / ESP32-S3-WROOM-1 / CH340 | ✅ 数据手册/ 目录已备 |
