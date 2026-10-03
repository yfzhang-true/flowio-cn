# 数字孪生项目实现 × 专著一致性审查 — 设计规格书

> **日期**: 2026-10-03 · **状态**: 待用户审查
> **原则**: 书稿里每一行代码列表、每一个数值、每一条命令、每一处架构描述，都必须与仓库真源（实现+测试+文档）可指认一致。**书骗人比代码错更严重**——这是"专著"二字的底线。

---

## 1. 审查对象映射（14 章逐章 → 真源）

| 章 | 书稿文件 | 真源（唯一比对基准） |
|---|---|---|
| 1 理论·DT | ch00a-dt-theory | book/reference.bib 条目真实性（aminer/DOI 核对） |
| 2 理论·气动 | ch00b-pneumatic-theory | literature/2020-xavier-aim 全文（公式）+ PHYSICS-SPEC.md |
| 3 生态位 | ch01-intro | flowio-softrobotics-docs/ + spec pcb-design §1 |
| 4 孪生先行 | ch02-twin | firmware/twin/{twin_api.c,PHYSICS-SPEC.md} + board_model.py 参数 |
| 5 原理图 | ch03-schematic | tools/gen_sch.py（修正 #9/#11/#12 案例行号锚点）+ spec 修正日志 |
| 6 PCB | ch04-pcb | git log 布线提交链（c3337a3..fa2f138）+ drc 数字（146→17→6→0） |
| 7 制造 | ch05-manufacturing | fab/README-jlc-order.md + README-fab.md（费用/标准版/TypeVIII×8） |
| 8 结构 | ch06-enclosure | enclosure/{make_case,make_meshes}.py（HD (68,65)/壁厚/水密） |
| 9 固件 | ch07-firmware | components/pn_core（CLI 命令表 13 条/TCA/WS2812 五模式）+ tests 33 |
| 10 BLE | ch08-ble | firmware/twin/BLE.md（UUID 表/20B 载荷/翻译表）+ ble_frame.c |
| 11 前端 | ch09-host | webapp/（令牌值/flows uGain 映射/装配动画参数）+ spec v2 §4 |
| 12 SDK | ch10-sdk | sdk/python/flowio_sdk/{protocol,client}.py + vectors.json |
| 13 验收 | ch11-acceptance | book/tickets/*.yaml（36 工单状态表）+ test_webapp 44 断言计数 |
| 14 产品化 | ch12-product | HANDOFF.md 路线图（OTA/HIL/多设备/BLE SDK/报表） |

## 2. 七类一致性检查项（每章跑同一清单）

1. **代码列表逐行比对**：书稿 lstlisting 与真源文件对应函数/片段 diff（允许排版省略号与注释裁剪，禁止语义漂移）
2. **数值核对**：所有出现的技术常数（VOUT 3.269/τ 1.79ms/R 14Ω/L 25mH/CRC 0x07/UUID 基址/阀 GPIO 表/孔口系数 114.5/γ=1.2/费用区间/页数计数等）与真源逐一相等
3. **命令/接口核对**：CLI 命令表、API 端点、GATT 特征、SDK 方法签名——名称、参数序、语义与实现一致
4. **文件路径引用**：书稿提到的仓库路径存在且内容相符（如 `components/pn_core/src/cli.c`）
5. **架构图/表**：分层、服务表、状态映射与实现一致
6. **交叉引用完整性**：\ref 无 undefined、\cite 与 reference.bib 键一一对应、图文件存在
7. **数字孪生专项**（用户点名）：ch2 理论公式 ↔ PHYSICS-SPEC ↔ sim_engine/board_model 三方一致；ch9 前端描述 ↔ webapp 实现一致

## 3. 审查方法（防"自己查自己"）

- **双独立代理**：一致性审计代理（持真源与书稿做比对，输出发现清单）与修复代理分离
- **机器辅助**：写 `book/tools/consistency_check.py`（stdlib）做可自动化部分：真源常数提取→书稿 grep 核对；路径存在性；\cite↔bib 键集合差；代码列表片段在真源文件中模糊匹配（去空白后子串）——机器过一遍后人工/AI 审"语义漂移"
- **真源优先裁决**：书与码冲突时，以仓库当前实现为准改书（除非书描述的是历史版本且已标注）

## 4. 修复策略

| 发现类型 | 处置 |
|---|---|
| 代码列表与实现漂移 | 以当前实现重录书列表 |
| 数值不一致 | 逐个改书稿值；若书稿值才是实现该有的→开独立修复任务修实现（本 spec 不扩scope，记录） |
| 命令/接口过时（如 GUI v1 描述残留） | 更新书稿 |
| 路径失效 | 改书稿路径或补 alias |
| bib/引用断链 | 补键或删引 |

## 5. 完成定义

1. `consistency_check.py` 全绿（机器项）
2. 14 章人工/AI 审计报告：每章 ✅ 或发现+修复+复验 ✅
3. 发现的仓库侧真 bug（若有）单独列清单交用户裁决是否修
4. xelatex 重编译零错；全部修复提交 git
