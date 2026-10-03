# GitHub Pages 数字孪生展示站 — 设计规格书

> **日期**: 2026-10-03 · **状态**: 待用户审查
> **决策背景**: 用户决定弃用 Tnkr（其机器人专属功能对气动控制器不适用、无 EDA 查看器），改以 GitHub 仓库 + GitHub Pages 作为唯一展示面："将数字孪生网页放在 github.io 上"。

---

## 1. 目标与非目标

**目标**：`https://yfzhang-true.github.io/flowio-cn/` 上线一个**零后端、可交互**的数字孪生演示站——面试官点开即见 3D 爆炸视图 + 气流/电流可视化 + 可调参数的电路仿真。

**非目标**：不动 main 分支的孪生源码架构（server.py 本地/带板场景照旧）；不迁移 Tnkr 已发布内容（项目保留但去引用）；不做 BLE/真机功能（静态站无硬件）。

## 2. 现状侦察结论

- 前端（`firmware/twin/webapp/`）7 个 JS 模块，依赖 6 类 `/api/*`：assembly、board/state、board/sim(+presets)、state、cmd、record/replay；静态资源 flows.json/hotspots.json/STL 均本地。
- **无现成离线模式**——静态化的全部工作量在一个 demo 数据层。
- `sim_engine.py` 356 行：4 电路（buck/二极管或/阀驱动/I2C）确定性参数计算 → 波形+指标，**可 1:1 移植 JS**。
- 路径假设：前端 fetch 用绝对路径 `/webapp/...`、`/api/...`——Pages 部署在**仓库子路径** `/flowio-cn/` 下，需相对化（部署构建时替换或 demo 层统一改相对路径）。

## 3. 方案比选

| 方案 | 内容 | 工作量 | 效果 |
|---|---|---|---|
| **A. JS 移植 demo 层（推荐）** | 4 电路仿真移植为 `sim_demo.js`；`demo_api.js` 拦截 fetch：assembly/presets 用静态 JSON、board/state 与 state 用客户端时序合成（气动+电气简化模型循环出数）、cmd/record 本地内存实现；BLE/命令面板入演示只读态 | ~1 天（移植 300 行 + shim 200 行） | 滑杆可调、波形实时算、3D 气流随数据动——"活"的演示 |
| B. 纯录制回放 | 本地跑 server.py 录 60s 会话，前端只做回放 | ~2 小时 | 滑杆死、数据 canned，展示力打折 |

选 A：求职演示的核心卖点就是"交互+仿真正在算"。

## 4. 技术设计（方案 A）

### 4.1 目录与构建

```
site/                      ← 演示站源（新增，入 main 仓）
  index.html               ← 自 webapp/index.html 派生（资产路径相对化 + demo_api 注入）
  js/ css/ vendor/         ← 自 webapp 拷贝（构建脚本同步，不手改双份）
  js/demo_api.js           ← fetch 拦截层（先于 main.js 加载）
  js/sim_demo.js           ← sim_engine.py 的 JS 移植（4 电路 + presets）
  data/assembly.json       ← 从本地 server.py 抓取固化
  meshes/*.stl             ← 拷贝
tools/build_site.py        ← 从 webapp/ 同步 + 路径重写 + 数据抓取（跑本地 server 后执行）
tools/deploy_site.ps1      ← gh-pages 分支构建推送（subtree 方式，不污染 main 历史）
```

### 4.2 demo_api 行为表

| 原端点 | demo 实现 |
|---|---|
| GET /api/board/assembly | `data/assembly.json`（构建时固化） |
| GET /api/board/sim/presets | `sim_demo.js` 内置常量 |
| POST /api/board/sim | `sim_demo.run(circuit, params)`（JS 移植，输出同构 JSON） |
| GET /api/board/state、/api/state | 客户端 20Hz 时序合成器：气动通道压力按正弦+设定值漂移、电气量按 sim 结果缩放；600s 环形历史 |
| POST /api/cmd、/api/record(/replay)、/api/time | 内存实现（演示态命令面板可打字、录制可回放，刷新即失） |
| BLE（Web Bluetooth） | 检测 `location.protocol === 'https:' && !navigator.bluetooth` 场景直接隐藏入口（Pages 无板） |

### 4.3 部署

- gh-pages 分支仅含 `site/` 构建产物（index 在根，便于子路径部署）
- 仓库 Settings → Pages → Source: gh-pages（用户点一次，或 gh api 代设）
- main 的 README 顶部加 Demo 徽章与链接

### 4.4 安全红线

- site/ 内容全部来自 webapp/ 公开资产与合成数据——**构建脚本显式排除**任何 record 真数据、密钥、简历/ 目录
- Mimosa 约束照旧：写文件用 Write/Edit 工具，构建脚本用 Path.write_bytes

## 5. 简历与既有引用的切换

1. 中英简历头部 Tnkr 行 → 改为 **Live Demo: yfzhang-true.github.io/flowio-cn**（3D 爆炸视图 + 实时气流/电流 + 可调电路仿真）；"硬件与制造"条目里的 "发布于 Tnkr" 措辞改为 "GitHub Pages 在线演示"
2. Tnkr 项目**保留不删**（零成本期权）：在其 Settings→描述尾部追加一句 "Live demo: <pages-url>" 导流；简历不再提 Tnkr
3. `docs/tnkr/` 档案全部保留（历史记录），新增本 spec 的关联注记

## 6. 验收标准

1. Pages URL 可访问：3D 爆炸/装配视图渲染、气流与电流可视化随数据流动
2. SimLab 四电路滑杆可调、波形与指标实时重算（与 Python 版同数量级：抽 3 组参数对比相对误差 <5%）
3. 全站零 `/api/` 网络错误（控制台干净）
4. gh-pages 分支无密钥/简历内容（构建脚本断言）
5. 中英简历、README 徽章切换完成；Tnkr 描述含导流链接

## 7. 开放问题（审查时定夺）

1. 演示站语言：界面沿用中文（当前 webapp 为中文 UI）还是出英文版？**建议：先中文上线（零成本），后续视投递外企需求再 i18n**
2. 是否同时把原理图 SVG/PCB 渲染图挂进 site/ 的"硬件"页签？**建议：本期只做孪生主页，硬件图纸作为下一个小迭代**（原 Tnkr 补丁方案的迁移版）

## 8. FAQ：为什么不用"前端+接口+后端"部署？（2026-10-03 审查问询补记）

- **GitHub 能力边界**：Pages 仅静态；Actions 是触发式 CI 不能按 HTTP 服务；Codespaces 是开发环境非生产托管。
- **架构判断**：后端三职责（仿真/遥测/录制）在演示场景分别化为"浏览器内 JS 仿真（访客 CPU 即算力，比远程 API 更快）"/"演示站无板不适用"/"内存实现"——**不需要后端，需要的是把数学搬进前端**。
- **真后端的唯一不可替代场景（路线图，本期不做）**：板子到货后，server.py 跑在常开机器 + Cloudflare Tunnel 公网暴露 → "Live Demo 显示真机实时压力曲线"。
- **国内可达性风险**：github.io 在国内时好时坏（vercel/workers 更差）。对策：①接受+仓库兜底（本期默认）②自定义域名+CDN ③国内对象存储静态镜像。
