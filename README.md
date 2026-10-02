# FlowIO-CN — 气动软体机器人国产化平台

> **根本法**：**[宪法.md](宪法.md)**（34 条工程/安全/硬件/文档纪律，任何工作先读它）
> **定位**：对标 FlowIO 的国产替代 B2B 方案——给康复手套白牌厂商供"升级大脑"
> **开发者**：独立开发者（上海，2 年嵌入式经验），全职开发中（计划求职后业余继续）
> **财务**：爱人在职 + 储蓄 = 可持续开发

## 商业模式

**唯一主线 = B2B 部件供应**：给 1688 白牌康复手套厂商（已售 5100+ 件、91% 回头率）
提供"5 路压力闭环控制板 + 固件 + 小程序报表"整套方案，方案价 ¥300-500/套。

**四大核心卖点**：
1. **分指控制**——5 端口独立压力闭环（竞品基础版不分指）
2. **客观评估**——压力数据 + TinyML → FMA 趋势报表（竞品无评估输出）
3. **国产化低成本**——全 1688 采购 BOM ¥150-250
4. **API 开源**——CLI + Web GUI + 数字孪生，可二次开发

**明确不做**：整机价格战（¥69 白牌）、医用注册（二类械）、BCI 方向、通用平台故事

## 目录结构

| 位置 | 内容 |
|------|------|
| `firmware/` | P0 固件（ESP32-S3-N16R8）+ 数字孪生 + Web 控制台 + TinyML |
| `study-notes/` | 战略文档（竞品分析/市场分层/临床调研/B2B 方案） |
| `literature/` | 文献库（9 篇核心精读 + 81 篇被引 + 阅读笔记） |
| `资源/` | FlowIO 官方资源包 + 数据手册 + 硬件验证报告 |

## 快速开始

**数字孪生（无需硬件）**

```bash
cd firmware/twin
./build_twin.sh            # 编译 pn_twin.dll（一条命令重建）
"E:/Program Files/KiCad/10.0/bin/python.exe" server.py   # KPY → http://127.0.0.1:8000/gui
```

**三层测试（改代码必跑）**

```bash
cd firmware/twin && bash run_tests.sh   # 冒烟 + 接口45 + 单元28 + 功能37 = 110 项
```

**目标机（需 ESP32-S3-N16R8）**

```bash
cd firmware && powershell build_n16r8.ps1   # 已配置 16MB Flash + 8MB PSRAM + 240MHz
```

**上位机 SDK（sdk/python）**

```bash
pip install pyserial                                       # 仅串口传输需要
python sdk/python/examples/hello_glove.py COM3             # 充→保→释→抽 一个来回
```

```python
from flowio_sdk import FlowIO
io = FlowIO("COM3")            # 0xA5 帧协议与固件 proto.c 同向量（详 sdk/python/README.md）
io.inflate(1, 180); io.hold(1); print(io.state())
```

## 项目阶段

| 阶段 | 状态 | 产出 |
|------|------|------|
| 数字孪生 | ✅ 完成 | 物理 v2（孔口方程）+ 泄漏注入 + Web 控制台 + 110 项测试 |
| P0 硬件 | ⏳ 等待到货 | ESP32-S3 + 阀 + 泵 + 传感器（1688 已采购） |
| TinyML | 🗄️ 已下线归档 | 泄漏检测管线归档 `firmware/twin/deprecated/ml-leak/`（spec §12，可复活） |
| B2B 对接 | ⏳ 等 P0 demo | 3 家白牌厂商联系（天津大晴天/深圳晟烨/云天星） |

## 开发节奏

- **现在（全职）**：P0 到货前完成 TinyML 仿真管线 + B2B 销售材料准备
- **求职后（业余）**：下班后 + 周末——实物调试、白牌对接、临床合作（远期）
