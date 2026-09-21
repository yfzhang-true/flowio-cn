# FlowIO 兼容 P0 固件（ESP32-S3）

对标 FlowIO 功能的自主实现固件（100% 原创代码，逻辑依据 study-notes/02 功能性笔记）。

## 目录结构

```
components/
  pn_core/       纯逻辑层（动作/闭环/协议）——不依赖任何平台，主机可测
  pn_hal_esp32/  ESP32-S3 硬件层（LEDC 阀/泵 + RMT 舵机 + I2C 传感器）
main/            app_main：10ms 控制任务 + 串口 CLI
tests/           主机单元测试（gcc/cmake/ninja，无需 ESP-IDF）
```

## 分层架构

```
应用层   main.c（CLI + 10ms 控制任务）
协议层   proto.c  [0xA5][cmd][ports][pwm][crc8]
动作层   actions.c / closedloop.c（端口三胞胎/方向阀/泵/状态字/节能/超压保护/压力闭环）
HAL      hal_if.h 契约 ← pn_hal_esp32 实现（目标机）/ mock_hal（测试）
```

## 主机单元测试（改逻辑必跑）

```bash
cd tests
cmake -B build-test -G Ninja -DCMAKE_BUILD_TYPE=Debug
cmake --build build-test
./build-test/pn_tests.exe        # 21 tests 全绿 = 逻辑层可信
```

## 目标机构建/烧录（需 ESP-IDF v5.5.5 @ E:\Espressif）

```bash
./idf_build.sh build     # 编译（生成 build/flowio_p0.bin，目标 esp32s3）
./idf_build.sh flash     # 烧录（接开发板 USB 口）
./idf_build.sh monitor   # 串口监视器（Ctrl+] 退出）
```

## 串口 CLI（115200）

| 命令 | 功能 | 示例 |
| --- | --- | --- |
| `I <ports> <pwm>` | 充气 | `I 1 255` |
| `V <ports> <pwm>` | 抽气 | `V 1 200` |
| `R <ports>` | 释放 | `R 1` |
| `S <ports>` | 停止/保压 | `S 1` |
| `O <ports>` / `C <ports>` | 开/关端口阀 | `O 7` |
| `P` | 读传感器（kPa） | |
| `T` | 打印状态字 | |
| `L` | 阀保持节能 | |

## 状态字位定义

bit0-4=端口1-5 开、bit5=进气阀、bit6=排气阀、bit7=泵、bit9=传感器在线、bit15=错误。
协议层预留设备 ID 字段位（多设备同步，对标 FlowIO JS API 多机协同）。

## 安全设计

- 上电默认全关（常闭阀 + duty=0）；
- 超压保护为**硬规则**（pn_check_overpressure），任何上层不可关闭；
- TinyML/智能层永远是并行观察者，不进控制路径（study-notes/11）。
