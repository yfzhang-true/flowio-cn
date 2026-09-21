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

**Web 前端三层测试（cd firmware/twin，改 gui.html 必跑）**

| 层 | 命令 | 覆盖 |
|----|------|------|
| 静态冒烟 | `node check.js gui.html` | 内联脚本语法 / 处理函数 / id 引用 |
| 单元 | `node test_gui.js` | buildFlowPaths 气流路径 / balloonScale / 端口掩码 / Scheduler 计时器编排 / 请求体（需 playwright-core） |
| 接口 | `bash test_api.sh` | /api/state /api/cmd /api/sim 协议契约 + 物理语义（32 项，纯 curl） |
| 功能 | `node test_e2e.js` | 真实浏览器：加载/充/保/释/抽/卡片/序列/刷新（27 项，需 playwright-core） |

单元与功能测试依赖 playwright-core（`npm i playwright-core`；Chromium 用本地 ms-playwright 缓存，`TWIN_CHROME` 可指定路径；启动命令示例 `NODE_PATH=<其 node_modules 父目录> node test_gui.js`）。
注意：固件超压保护是**硬规则锁存**（state bit15 置位后重启服务才清），接口测试带前置守卫会明确提示。

**主机单元测试（改逻辑必跑）** 与 **目标机构建/烧录**：见 `firmware/README.md`。

## 版本管理说明

本仓库为单一根仓库：资料（笔记/文档镜像/资源包）直接在根历史中；
`firmware/` 由原独立 git 仓库经 `git subtree add` 合并而来（9+3 条提交全部保留），
firmware 内部的 `.gitignore` 继续生效（忽略 `build/`、`*.dll`、`*.exe` 等可重建产物）。
