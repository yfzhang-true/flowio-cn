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

一键运行（推荐，自起 8017 隔离实例，不干扰浏览器正在用的 8000）：

```bash
bash run_tests.sh        # 静态冒烟 + 接口 36 + 单元 28 + 功能 39
```

| 层 | 单独运行 | 覆盖 |
|----|------|------|
| 静态冒烟 | `node check.js gui.html` | 内联脚本语法 / 处理函数 / id 引用 |
| 单元 | `node test_gui.js` | buildFlowPaths 气流路径 / balloonScale / 端口掩码 / Scheduler 计时器编排 / 请求体 |
| 接口 | `bash test_api.sh` | 三端点协议契约 + 物理语义 + 超压锁存/虚拟断电（纯 curl，自起隔离实例） |
| 功能 | `node test_e2e.js` | 真实浏览器全场景（加载/充/保/释/抽/卡片/序列/闭环/注入/超压/刷新） |

用例明细见 `firmware/twin/TEST-CASES.md`（103 项，含未覆盖项与审查指引）。
单元与功能测试依赖 playwright-core（`npm i playwright-core`；Chromium 用本地 ms-playwright 缓存，`TWIN_CHROME` 可指定路径）。
注意：测试与手工操作**必须用不同端口实例**（脚本默认 8017），否则命令串扰产生假失败；固件超压保护是硬规则锁存，接口测试带虚拟断电自愈。

**主机单元测试（改逻辑必跑）** 与 **目标机构建/烧录**：见 `firmware/README.md`。

## 版本管理说明

本仓库为单一根仓库：资料（笔记/文档镜像/资源包）直接在根历史中；
`firmware/` 由原独立 git 仓库经 `git subtree add` 合并而来（9+3 条提交全部保留），
firmware 内部的 `.gitignore` 继续生效（忽略 `build/`、`*.dll`、`*.exe` 等可重建产物）。
