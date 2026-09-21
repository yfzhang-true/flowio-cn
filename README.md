# FlowIO-CN — 气动软体机器人通用控制器（国产替代 · 科研/教育套件）

对标 softrobotics.io FlowIO 的自主实现：`pn_core` 纯逻辑层（C，主机/ESP32 双宿主）→ ESP32-S3 固件 → Windows 数字孪生（pn_twin.dll + Web 控制台）。

## 目录结构

| 位置 | 内容 |
|------|------|
| `firmware/` | P0 固件与数字孪生：ESP-IDF 工程 + pn_core 逻辑层（主机测试 21/21）+ `twin/` Web 孪生控制台 |
| `study-notes/` | 研究笔记 01–13（架构 / 协议 / 国产替代路线 / 采购清单 / 对标表 / 康复方案…） |
| `flowio-softrobotics-docs/` | softrobotics.io 官方文档镜像（抓取脚本 `save_softrobotics_docs.py`） |
| `资源/` | FlowIO 官方资源包：3MF 结构件、Arduino 源码、数据手册（ESP32-S3 / XGZP6897D / TCA9548A）、演示视频 |
| `FlowIO-Arduino-Libraries-master.zip` | 官方 Arduino 库参考压缩包（解包目录 453M 不入库） |

## 快速开始

**数字孪生（无需硬件）**

```bash
cd firmware/twin
./build_twin.sh            # 编译 pn_twin.dll（git 不跟踪二进制，一条命令重建）
python server.py           # → http://127.0.0.1:8000/gui
```

**主机单元测试（改逻辑必跑）** 与 **目标机构建/烧录**：见 `firmware/README.md`。

## 版本管理说明

本仓库为单一根仓库：资料（笔记/文档镜像/资源包）直接在根历史中；
`firmware/` 由原独立 git 仓库经 `git subtree add` 合并而来（9+3 条提交全部保留），
firmware 内部的 `.gitignore` 继续生效（忽略 `build/`、`*.dll`、`*.exe` 等可重建产物）。
