# 硬件验证报告 — ESP32-S3-WROOM-1-N16R8

> 2026-09-22 | 数据来源：ESP32-S3-WROOM-1 中文数据手册（本地 PDF）+ Web 验证

## 目标模块规格（数据手册提取）

| 参数 | ESP32-S3-WROOM-1-N16R8 |
|------|------------------------|
| CPU | Xtensa 32-bit LX7 **双核 @ 240MHz**（含向量指令/SIMD，用于 ML 加速） |
| ROM | 384 KB |
| SRAM | **512 KB**（片内） |
| RTC SRAM | 16 KB |
| Flash | **16 MB**（Quad SPI） |
| PSRAM | **8 MB**（**Octal SPI**） |
| GPIO | 36 可用（4 个 strapping） |
| Wi-Fi | 802.11b/g/n（150 Mbps） |
| BLE | 5.0 |
| USB | USB 2.0 OTG |
| 工作温度 | -40 ~ +65°C |

## TinyML 兼容性验证

| 框架 | 兼容 | 依据 |
|------|------|------|
| **Edge Impulse** | ✅ | 官方支持 ESP32-S3，多个 N16R8 workshop/tutorial |
| **TFLite Micro** | ✅ | ESP32-S3 有官方 TFLM port，实践指南充分 |
| **ESP-DL / ESP-NN** | ✅ | 乐鑫官方 ML 库，利用 S3 向量指令 SIMD 加速 |
| **Arduino IDE** | ✅ | Edge Impulse 导出 Arduino 库可直接编译 |

### N16R8 的 ML 优势

- **16MB Flash** → model 分区 256KB 绰绰有余（模型 10-50KB）
- **8MB Octal PSRAM** → 特征缓冲可放 PSRAM（比 SRAM 大 16 倍）
- **240MHz 双核 + 向量指令** → 推理 <50ms（估算）
- **512KB SRAM** → 模型 + 推理可完全在 SRAM 内运行（零 PSRAM 依赖）

## 固件配置状态

| 配置项 | 旧值（错误） | **新值（已修正）** | 编译状态 |
|--------|------------|-------------------|---------|
| Flash 大小 | 2MB | **16MB** | ✅ 编译通过 |
| PSRAM | 未启用 | **已启用** | ✅ 编译通过 |
| CPU 频率 | 160MHz | **240MHz** | ✅ 编译通过 |
| PSRAM 模式 | — | Quad（当前） | ⚠️ 到货后改 `CONFIG_SPIRAM_MODE_OCTAL` |
| 分区表 | 单应用 | 单应用（待加 model 分区） | 📋 TinyML Phase 0 |

### 待到货后确认项

1. `CONFIG_SPIRAM_MODE_OCTAL=y`（N16R8 硬件为 Octal，当前为 Quad）
2. 实测 PSRAM 带宽（Octal 80MHz ≈ 40MB/s vs Quad 40MHz ≈ 20MB/s）
3. 实测推理延迟（1D CNN int8，目标 <50ms）
4. XGZP6897D I2C 通信验证（双传感器经 TCA9548A 分通道）

## 数字孪生 vs 真机差异（ML 域随机化已覆盖）

| 维度 | 孪生 | 真机 | ML-SPEC 域随机化 |
|------|------|------|-----------------|
| 采样率 | 20Hz（50ms/tick） | **100Hz**（10ms 任务） | ✅ 95-105Hz 模拟 |
| 传感器精度 | float32 | 24-bit ADC ≈ 15-bit 有效 | ✅ ADC 量化模拟 |
| I2C 延迟 | 即时 | ~1ms 总线延迟 | ✅ 采样抖动模拟 |
| CPU 限制 | 无 | 240MHz 双核 | 模型 <50KB 不构成瓶颈 |
| 内存限制 | 无 | 512KB SRAM + 8MB PSRAM | 模型 10KB 远小于限制 |
