# E:/FLOWIO 项目根整理 — 唯一入口 — 设计规格书

> **日期**: 2026-10-03 · **状态**: 待用户审查
> **目标**: `E:/FLOWIO-外部参考` 并入 `E:/FLOWIO/资源/工具链/`，E:/FLOWIO 成为**唯一入口**；顺带清理根目录冗余与构建产物。
> **约束**: 所有路径引用（bib/spec/plan/HANDOFF/scripts）同步改写；git 历史不破坏。

---

## 1. 目标结构

```
E:/FLOWIO/                          ← 唯一入口
├── 资源/
│   ├── 实物图/ 器件规格书/ 官方参考/ 开发板资料/   ← 既有四类
│   └── 工具链/                        ← 从 E:/FLOWIO-外部参考/_ref 迁入
│       ├── freerouting-2.4.1.jar
│       ├── jdk-25/                    ← 改短名
│       ├── KiCadRoutingTools/         ← 改短名（工作区无 .git）
│       ├── kicad-libs/  papers/  aeonlabs/
│       ├── 艾谷-ESP32S3教程/           ← 改短名（PDF+PPT+接线图+模块）
│       └── README.md                  ← 迁移后更新路径表
├── firmware/ book/ docs/ hardware/ sdk/ literature/ ...  ← 不动
```

## 2. 迁移清单（1.6G，mv 同盘秒级）

| 源（E:/FLOWIO-外部参考/_ref/…） | → 目标（E:/FLOWIO/资源/工具链/…） |
|---|---|
| freerouting-2.4.1.jar | freerouting-2.4.1.jar |
| jdk-25.0.4.1+1-jre/ | jdk-25/ |
| KiCadRoutingTools-main/ | KiCadRoutingTools/ |
| kicad-libs/ | kicad-libs/ |
| papers/ | papers/（含 3 篇精读 PDF） |
| aeonlabs/ | aeonlabs/ |
| 【艾谷科技】ESP32S3入门视频教程资料/ | 艾谷-ESP32S3教程/ |

迁完后 `E:/FLOWIO-外部参考/` 整目录删除。

## 3. 路径引用同步（8 处已定位）

| 文件 | 改法 |
|---|---|
| book/reference.bib L206/L238 | `E:/FLOWIO-外部参考/_ref/【艾谷…`→`E:/FLOWIO/资源/工具链/艾谷-ESP32S3教程/` |
| docs/superpowers/plans/2026-10-01-p1-auto-finish.md（KRT 三处） | `E:/FLOWIO-外部参考/_ref/KiCadRoutingTools-main`→`E:/FLOWIO/资源/工具链/KiCadRoutingTools` |
| HANDOFF.md 追加"路径迁移记录"节 | 新旧路径对照表 |
| 资源/工具链/README.md | 从 外部参考/README.md 迁移并更新 |
| firmware/BRINGUP.md 若引用 KRT 路径 | 同步改 |
| grep 全仓残留 | 兜底清零 |

## 4. 根目录顺带清理

| 项 | 大小 | 动作 |
|---|---|---|
| FlowIO-Arduino-Libraries-master/ + .zip | 453M+? | zip 删；目录移入 资源/官方参考/arduino-libraries/（FlowIO 官方 API 对照素材，bib 已引） |
| firmware/build/ | **1.8G** | git rm --cached + .gitignore（idf 构建产物，重编即得）——**最大单项** |
| firmware/twin/deprecated/ | 361M | git rm --cached 保留磁盘（归档纪律），.gitignore 加 firmware/twin/deprecated/ml-leak/dataset（306M 二进制） |
| .mimosa/ | 196M | 确认 .gitignore 已盖（既有） |
| lootdrop_call.py / save_softrobotics_docs.py | 2 文件 | 移入 tools/ 或删（一次性脚本，git 历史有） |
| literature/ 1.3G | — | 保留（全文已入 bib；检查是否有 git 大二进制→git rm --cached PDF 仅留 txt） |

## 5. 完成定义

1. `E:/FLOWIO-外部参考` 目录不存在；`ls E:/FLOWIO` 无散落 zip/脚本
2. `grep -rn "FLOWIO-外部参考" --include="*.py" --include="*.sh" --include="*.bib" firmware/ book/ hardware/ sdk/ 资源/工具链/README.md` = 0（docs/superpowers 历史文档与 HANDOFF 允许保留旧路径作为历史记录，但 HANDOFF 追加新路径表）
3. 五套测试不回归（test_webapp/classic×3/api×2 各跑一遍）
4. xelatex+biber 零错（bib 路径改后）
5. git 提交干净
