# 资源/ 信息源纳编 + 外部参考/ 去留 — 设计规格书

> **日期**: 2026-10-03 · **状态**: 待用户审查
> **背景**: 资源/ 含采购器件实拍图、规格书、FlowIO 官方源码与 3MF 结构件、开发板原理图——是**实物级信息源**（与 literature/ 论文、docs/ 工程文档互补的第三层）。E:/FLOWIO-外部参考 23GB 中大部分为工具链（非信息源）。

---

## 1. 资源/ 分类盘点（遍历完成，四类价值）

### A 类·器件实拍+规格书（书稿"选型与实物"素材，最高价值）
| 资源 | 书稿用途 |
|---|---|
| handes_p1-p18.png（18 图） | ch3 生态位/ch5 制造：**厂商实物图**（汉戴斯=FlowIO 代工平替商——B2B 供应链实证） |
| valve0520d_*/0520f_*（16 图） | ch2 气动驱动理论：**两种阀实物对照**（常闭 2 通 vs 两位三通——阀选型节配图） |
| mos_p1-p7.png + MOS.pdf | ch7 固件：MOS 管（74HCT245 相关采购验证）实物 |
| sanjian_p1-p9.png + 散件.pdf | ch5 制造：散件清点/BOM 实物对照 |
| xgzp_p3.png + XGZP6897D-C(V1.1).pdf + 数据手册/XGZP6897D_V2.5.pdf | ch2 压力传感器（孪生物理的量程来源 ±100kPa 实证） |
| 电磁阀0520D/0520F规格书（中文） | ch2 阀参数表（动作压力 -53.3kPa 来源→**修正 PHYSICS-SPEC P_min 的直接依据**，bib 补引） |
| 数据手册/（AO3400A/电感/DC005/XH/CH340N 等 8+ PDF） | ch3 原理图各章：器件选型节引用（bib @misc 逐条入） |
| datasheets/（ESP32-S3-WROOM 中文/TCA TI 版/XGZP V2.5 + HARDWARE-VERIFICATION.md） | ch7/ch2 引用源；**HARDWARE-VERIFICATION.md 是到手开发板验证记录→ch3 开发板选型节** |
| dmm.png / solder_check.png / 1-4.png | ch13 下篇验收：万用表/焊接检查现场照（工单 A201 配图预置） |

### B 类·FlowIO 官方资产（对标素材，版权敏感须区分）
| 资源 | 处置 |
|---|---|
| FlowIO.cpp/.h 等 7 个源文件（官方 Arduino 库源码） | **仅作对照参考**——本书 100% 自研原则：ch1 对比节可引 API 形态差异（文字描述+接口签名对照表），**不逐行摘录代码**（GPL/版权尊重）；bib 补引 softrobotics.io |
| FLOWIO.mp4（16MB 官方演示视频） | ch1 转述其演示场景（五指充放气循环），书稿以文字+自绘时间线图呈现 |
| flowio-official-gui-reference.png / flowio_gui.html | ch9 前端：官方 GUI 布局参照（我们的 P0 气动台 SVG 示意图对标来源——补一句引注即可） |
| 3MF ×23（L/M/S/Main/TubeGuide/ValveCap 等官方结构件） | ch6 结构：**尺寸对照表素材**（官方 S/M/L 模块 vs 本书 92×77 单体——设计取舍论证）；不直接复用模型 |
| FlowIO Development Platform PDF（CHI'21 论文副本） | 已在 literature/ 有全文+bib，此副本不重复入库 |

### C 类·开发板资料（原理图对标）
| 资源 | 用途 |
|---|---|
| SCH_ESP32-S3-DevKitC-1 PDF + 资源/ESP32/（N16R8 原理图 PNG/BOM xlsx/产品介绍 docx） | ch3 原理图章：**官方参考设计 vs 本书自研对照表**（strapping 处理/电源树/USB 差分三处对照——我们已有 spec §2.1 三件套审计，配图用资源 PNG） |
| Arduino API Documentation.pdf | ch12 SDK：官方 Arduino API vs flowio_sdk 对照（方法名/参数风格对照表） |

### D 类·低价值/冗余（不纳编）
kicad-libraries-main.zip（53MB，已解压于 _ref 且入 bib）、kicad/（32MB 中间产物）、TCA9548A.rar（有 datasheets/ TI 版足矣）、FLOWIO-外部参考/（资源内的嵌套残留）、extracted/（116MB 临时解压）、FT232 驱动、Gerber zip（开发板资料冗余）

## 2. 纳编动作（书稿增补点汇总）

1. **bib 增补 ≥10 条** @misc（电磁阀 0520D/0520F 规格书、XGZP6897D、AO3400A、CDRH103RNP 电感、DC005、XH2.54、CH340N、DevKitC-1 原理图、FlowIO Arduino 库、FlowIO 官方 3MF 结构件集）
2. **ch2** 阀选型节：0520D vs 0520F 对照表 + 实拍图 2 张 + 规格书引（P_min -53.3kPa 闭环验证句）
3. **ch3** 开发板对照节：DevKitC-1 原理图 PNG + 三处设计对照表（strapping/电源/USB）
4. **ch5** 供应链节：汉戴斯/三剑（sanjian）实拍对照——国产平替供应链叙事（B2B 卖点）
5. **ch6** 官方 3MF 尺寸对照表（S/M/L vs 本书单体）
6. **ch1/ch9** 官方 GUI 参照引注 + mp4 场景转述
7. **ch13 下篇** 预置现场图位（dmm/solder_check → 工单 A201/A202 配图说明）
8. 版权纪律：官方代码只引签名不摘实现；3MF 只列尺寸不复制模型；图仅自摄/自绘 + 厂商公开规格书截图注明出处

## 3. E:/FLOWIO-外部参考（23GB）去留裁决建议

| 目录 | 大小 | 价值 | 建议 |
|---|---|---|---|
| freerouting-src/ | **15G** | 源码已精读完毕，知识在 spec §8/文档；**git 历史膨胀**（.git 占绝大部分） | **可删**（保留 jar 62MB 供三轮布线复用；论文公式已入书） |
| fr-src.tar.gz | 983M | 同上压缩包 | **可删**（与 src 二选一已无用） |
| jdk-21（448M）/jdk-25（487M） | 935M | Java 25 必须保留（freerouting 运行时）；21 从未用上 | **删 21 留 25** |
| KiCadRoutingTools-main/ | 1.8G | repair_planes/route CLI 仍被 BRINGUP 后校准对拍引用（工具依赖） | **保留**（但可删其 .git 约 1G？检查后裁） |
| 艾谷教程资料/ | 2.9G | PDF 已纳 bib；PPT/示例工程**回板后固件参考**（WIFI/OTA 路线图垫脚石 V3） | **保留 PDF+PPT，可删 4_Program 示例（~1G？）与 node_modules** |
| kicad-libs/ | 349M | Espressif 官方库（gen_sch 解析真源） | **保留** |
| jre.zip/jre25.zip | ~900M? | 解压残留 | **可删** |
| papers/ | ~3M | 三篇精读文献 | **保留**（bib 依据） |

**预计释放 ~17-18GB**（15G src + 1G tar + 448M jdk21 + zip 残留 + KRT .git + 艾谷工程冗余），保留 ~5G 有效资产。**裁决权在用户**——建议分两档：立即删（src/tar/jdk21/zip 残留 16.4G 零风险）；谨慎删（KRT .git、艾谷示例 ~1.5G，删前确认 BRINGUP 无依赖路径）。

## 4. 完成定义
1. bib +≥10 条真实条目；书稿 6 章增补点落位且编译零错
2. 器件图入 book/figures/ 时重命名规范化（fig-<器件>-<视角>.png）并记录出处
3. 外部参考删除动作**待用户逐档批准后执行**（本 spec 只给建议清单）
