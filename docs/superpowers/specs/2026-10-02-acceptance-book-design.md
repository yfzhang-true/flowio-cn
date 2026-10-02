# 验收×专著一体化 — 设计规格书

> **日期**: 2026-10-02 · **状态**: 待用户审查
> **前置**: 前端 v2 交付（ec3cefa）· JLC 下单包就绪（板5装2）· book/ LaTeX 骨架+ch11 验收章已编译（093d81e）· BRINGUP.md 九章 30 待勾
> **核心思想**: 验收与写书不是两件事——**验收产物即书稿素材**。用一套"验收工单"机制把 BRINGUP 的 30 个 checkbox 变成书稿 12 章的图与代码引用源，验收完成日即书稿主体完成日。

---

## 1. 核心机制：验收工单（Acceptance Ticket）

每项验收 = 一张工单（YAML 头 + Markdown 正文），文件名 `book/tickets/A###-<slug>.yaml`：

```yaml
id: A001
title: 首电三测（万用表）
phase: hw            # sw=软件侧(回板前) | hw=回板后 | cal=标定
bringup: "1.1"       # 对应 firmware/BRINGUP.md 章节号
book_ch: 11          # 产物汇入的书稿章
status: pending      # pending | pass | fail | waived
evidence_required: [photo, multimeter_reading]
```

正文记录：操作步骤、实测值、判定（pass/fail + 容差）、**素材管线指令**（截图/照片拷入 `book/figures/`、代码块引用路径、数据 CSV 落 `book/data/`）。

**双产物**：一张工单完成 = BRINGUP 对应 checkbox 勾掉 + 书稿对应节的图/表/实测数据就位。fail 的工单同样入书（"踩坑实录"专栏——比 pass 更有教学价值）。

## 2. 验收工单清单（36 张，覆盖 BRINGUP 全 30 项 + 软件侧 6 项）

### Phase SW 软件侧（回板前即可执行，6 张）
| ID | 内容 | 书章 |
|---|---|---|
| A101 | 孪生 v2 首屏装配叙事 + 爆炸滑杆（已有 26 项目视记录归档为工单证据） | 11 |
| A102 | 电流/气流联动：I/V/S 命令差分截图（已归档） | 11 |
| A103 | 仿真实验室四电路重算（含 i2c ⚠ 案例） | 9 |
| A104 | SDK 协议向量双向 + hello_globe 冒烟 | 10 |
| A105 | 固件 QEMU 冒烟 + 主机 33 测试 | 7 |
| A106 | BLE 契约载荷向量（nRF Connect 待真机，向量先验） | 8 |

### Phase HW 回板后（BRINGUP 九章，24 张）
A201 首电三测 → A202 CH340 烧录/自动复位 → A203-204 74HCT245/MOS 触发（示波器） → A205 WS2812 状态灯 → A206 TCA 五通道扫描 → A207 8 阀全功能（听声+电流） → A208 I2C tr 实测（100/400kHz 裁决） → A209-210 BLE 三步 + gui 真机模式 → A211-215 电气校准 6 项（万用表/LCR/示波器/4线法/红外/电流钳 → BOARD_PARAMS 改 → 黄徽转绿） → A216-218 泵三实验（calibrate_pump.py） → A219 闭环充气到目标 kPa → A220 外壳装配（M3 自攻 + 端子开孔对位） → A221 整机气密（保压 60s） → A222-224 长跑温升/8阀轮巡/满载纹波

### Phase CAL 补充（6 张）
A301-306：孪生标定对拍（改 BOARD_PARAMS/PHYSICS 常数后，孪生 vs 实测曲线叠图）——产品级"数字孪生精度报告"，也是书第 12 章的核心卖点章。

## 3. 书稿结构（12 章骨架定稿，验收映射）

| 章 | 内容 | 素材源 |
|---|---|---|
| 1 | 软体机器人与 FlowIO-CN 生态位 | 文献 + 项目史 |
| 2 | 孪生先行：物理建模与仿真 | twin 物理引擎 + 仿真套件 |
| 3 | 原理图：从拓扑到 13 次修正 | gen_sch.py + 修正日志 |
| 4 | PCB 布线攻坚：从 146 到 0 | boardgeom/netdoctor/freerouting 三轮 |
| 5 | 制造：嘉立创全代工实战 | fab/ 全套 + 下单实录 |
| 6 | 结构：FreeCAD 参数化外壳 | enclosure/ |
| 7 | 固件：ESP-IDF 分层架构 | pn_core + 主机测试 |
| 8 | BLE 无线 | NimBLE + Web Bluetooth |
| 9 | 上位机与孪生前端 | webapp v2 + simlab |
| 10 | Python SDK | flowio_sdk |
| **11** | **验收实录**（ch11 已起稿） | **36 张工单双产物** |
| 12 | 产品化：标定、精度与路线 | Phase CAL 工单 |

## 4. 工作流（每张工单 15-30 分钟）

```
领工单 → 执行验收（截图/拍照/录数）→ 拷入 book/figures|data → 填实测值与判定
→ 更新工单 status → BRINGUP checkbox 勾 → 该章 .tex 增图/表 → xelatex 编译过 → git commit
```

辅助脚本 `book/tools/ticket.py`（stdlib）：`ticket.py new A205 "WS2812 状态灯" hw 5.1`生成模板；`ticket.py report` 输出进度表（pass/fail/pending × phase）——写书进度与验收进度一屏可见。

## 5. 范围与非目标

**范围**：36 张工单模板一次生成；ch11 已起稿；ticket.py；书稿 12 章 .tex 骨架文件（每章 \chapter + \label + 3-5 个 \section 占位标题——**有内容来源的章直接填实**：ch11 实、ch3-4 从修正日志/DRC 史填实，其余留骨架待写）。

**非目标**：不在本期写完全部 12 章正文（回板后事件驱动的章必须等工单）；不做出版社投稿包（待书稿 ≥60% 再议）；不做英文版。

## 6. 验收门槛（本 spec 自身的完成定义）

1. 36 张工单文件在 `book/tickets/`，YAML 合法（ticket.py report 可跑）
2. book/ xelatex 编译零错，ch1-ch12 骨架齐（ch3/ch4/ch11 有实文）
3. SW 六张工单预填 status=pass + 已有证据归档链接（26 项 v2 目视记录等）
4. BRINGUP.md 各章尾加"对应工单: A2xx"映射行
