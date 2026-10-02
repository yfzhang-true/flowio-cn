# 数字孪生前端 v2 — 产品爆炸视图为核心 · Apple Liquid Glass 风格 — 设计规格书

> **日期**: 2026-10-02 · **状态**: 待用户审查（方向已口头认可，工具选型"零构建 ES Modules"为默认假设）
> **前置**: 孪生平台 v1.2（gui.html + server.py 五支柱已交付）；S3 网格管线（meshes/*.stl + assembly.json）
> **用户核心裁定**: 仪表盘只是辅助；**数字孪生的核心视图 = 产品及其爆炸视图上的气流、电流走向**；审美对标 Apple 官网（Liquid Glass）
> **审美依据**: [Apple Liquid Glass (Newsroom/WWDC25)](https://www.apple.com/newsroom/2025/06/apple-introduces-a-delightful-and-elegant-new-software-design) · [HIG Materials](https://developer.apple.com/design/human-interface-guidelines/materials) · [CSS 复刻指南](https://dev.to/gruszdev/apples-liquid-glass-revolution-how-glassmorphism-is-shaping-ui-design-in-2025-with-css-code-1221) · [Apple 产品页滚动叙事手法](https://css-tricks.com/lets-make-one-of-those-fancy-scrolling-animations-used-on-apple-product-pages)

---

## 1. 目标与非目标

**目标**：重做孪生前端——3D 产品场景成为唯一主角，气流/电流以数据驱动的方式"长在"产品上；旧仪表盘降级为辅助抽屉/浮层；整体达到可对标 Apple 产品页的视觉品质。

**非目标（YAGNI）**：不换 React/Vite（零构建假设，用户可推翻）；不改 API v1.2 契约；不做 P0 气动 SVG 示意图的 3D 化（旧 gui 保留一个过渡版本）；不做移动端专项优化（桌面 Chrome/Edge 优先，可用即可）；不做多语言。

## 2. 信息架构：布局倒转

```
┌──────────────────────────────────────────────────────┐
│ 顶栏(细玻璃): 产品名 FLOWIO-CN · 模式徽章(孪生/真机BLE) · 连接/断开 │
│──────────────────────────────────────────────────────│
│                                                      │
│              全屏 3D 产品场景（唯一主角）              │
│   装配/爆炸 · 气流粒子 · 电流辉光 · 器件热点卡          │
│                                                      │
│ 左缘抽屉   底部中央运输条(玻璃胶囊)      右缘抽屉       │
│ "控制"(阀/泵)  播放/暂停/单步/速度/录制/爆炸滑杆  "遥测" │
│──────────────────────────────────────────────────────│
│ 底部状态行: stale/未标定黄徽/时间·录制状态 · 仿真实验室入口 │
└──────────────────────────────────────────────────────┘
```

- **首屏 = 装配叙事**：五部件从四散位飞入合体（~1.5s，`cubic-bezier(0.22,1,0.36,1)` 出舱曲线），合体后轻微呼吸悬浮（振幅 0.3mm、周期 4s）
- 爆炸滑杆 = 底部玻璃胶囊内大滑杆 + "展开/合拢"电影模式（2s 往返缓动，同 S3 语义 explode*k）
- **遥测抽屉（右，默认收起）**：sparkline 小卡（5V 轨/3.3V 轨/负载/温度三值），点卡片展开小图（ECharts 保留但重皮肤，深底玻璃、去网格线、细线柔光）
- **仿真实验室 = 全屏接管浮层**：从底部升起，玻璃卡片四电路选择+参数+波形，关闭回落；不常驻、不抢主场景
- **控制抽屉（左）**：阀×8/泵的 Apple 风分段控件（替代旧按钮阵），命令走 p1_sendCmd 双模（HTTP/BLE）
- P0 气动台（旧 gui.html）：保留为 `/classic` 一个过渡版本（仅改链接不改代码），v2 验收后下线决策另定

## 3. 核心：气流与电流可视化

### 3.1 电流走向（板上真实拓扑）
- **路径来源**：`make_flows.py`（新，跑在 mesh 管线旁）读 `fab/flowio-p1-pos.csv` 器件坐标 + `docs` 引脚表拓扑 → 生成 `webapp/flows.json`：
```json
{ "elec": [
    {"id":"vin5v","color":"#e8b64c","points":[[x,y,z]…],"desc":"DC/USB→SS34→5V轨","live":"rail_5v.load_a"},
    {"id":"buck_in", …}, {"id":"rail3v3","color":"#7ee2b8","live":"rail_3v3.load_a"},
    {"id":"gate1..8","color":"#6aa9ff","points":[U1→R39..→Q3..→J10..],"live":"valves[n].i_A"}, …],
  "air": [
    {"id":"port1..8","dir_out":[…],"desc":"端子→执行器","live":"valve_duty[n]","pressure":"/api/state p"} ] }
```
  坐标沿用 S3 板→壳坐标系（+2.9 偏移、z=板面 4.0mm），器件焊盘间用 3-5 段折线（曼哈顿走线感），手写拓扑表约 20 条路径。
- **渲染**：`THREE.Line`（或细 TubeGeometry）+ 自定义 shader：`dashOffset = u_time * speed`，speed/亮度 = live 值归一化（0 负载=静止微光，满载=快速流动强光）；AdditiveBlending 辉光。
- **联动**：telemetry 200ms 更新 → uniforms 直写；阀一开其栅极支路即"通电动起来"（board_model i_A 驱动）。

### 3.2 气流走向（端子→执行器）
- 8 条 `CatmullRomCurve3`：从各端子(板坐标)出发，沿 -Y 向外弧线延伸 ~25mm（到"执行器方向"）；
- **粒子**：`THREE.Points` + 小圆点纹理，每路径 ~50 粒沿曲线参数 t 循环推进；速度与密度 ∝ PWM duty；**方向反转**于真空（回流），颜色青 `#6ad4ff`（正压）/琥珀 `#ffb454`（真空，取 /api/state 压力符号）；
- **爆炸跟随**：所有流线端点绑定部件锚点（端子属 pcb 部件），爆炸时随 explode*k 平移拉伸——形成 Apple 爆炸图"连线不断"的观感；
- 端口静默时留 8% 底光提示通道存在。

### 3.3 器件热点卡（Apple 产品页 hotspot 模式）
- Raycaster 点击器件（复用 S3 raycaster；部件级=5 大件，器件级用 parts_f 的包围盒表（make_flows 一并导出 `hotspots.json`：ref→{center,size,live 字段映射}））
- 点击 → 右下滑入玻璃卡：器件名 + 2-4 个实时值（如 buck: 3.263V/0.43A/94%效率；阀道: 电流/功率）+ 迷你条；再点空白关闭；hover=发光脉冲（emissive 0.15→0.4）

## 4. 视觉系统：Liquid Glass 设计令牌

| 令牌 | 值 |
|---|---|
| 画布底 | 径向渐变 `#101014→#0a0a0c`，场景地面 ContactShadow |
| 字体栈 | `-apple-system,"SF Pro Display","PingFang SC","Microsoft YaHei",sans-serif`；标题 300 细体 28-40px，数字用 `font-variant-numeric: tabular-nums` |
| 玻璃面板 | `rgba(255,255,255,.06)` + `backdrop-filter: blur(24px) saturate(180%)` + 1px `rgba(255,255,255,.12)` 边 + 20px 圆角 + `0 8px 32px rgba(0,0,0,.35)` |
| 主文本/次文本 | `rgba(255,255,255,.92)` / `.55`；强调色仅两档：电蓝 `#6aa9ff`（交互）与信号色（§3 流色） |
| 动效 | 全局 `cubic-bezier(.22,1,.36,1)`；面板进出 12px 位移+200ms；数值变化不跳动（等宽数字） |
| 3D 材质升级 | MeshStandardMaterial+RoomEnvironment；PCB 墨绿微金属、器件中性灰、壳喷砂灰 `#9a9a9e roughness .55`；ACESFilmic 色调映射 |
| 克制红线 | 一屏主色≤两档；**禁止网格状仪表盘布局**；曲线图去网格线只留细轴线 |

## 5. 工程形态（零构建，可推翻假设）

```
firmware/twin/webapp/
  index.html            骨架+顶栏+抽屉+运输条 DOM
  css/twin.css          设计令牌+组件样式（~400 行）
  js/main.js            应用壳：状态store(纯对象+订阅)、标签/抽屉/浮层路由
  js/scene.js           Three r16x：装配动画/爆炸/材质/灯光/hotspot raycaster
  js/flows.js           flows.json 加载、电流 shader 虚线、气流粒子系统
  js/telemetry.js       轮询 /api/board/state + /api/state（双源合并进 store）
  js/panels.js          遥测抽屉 sparkline、控制抽屉、热点卡、运输条
  js/simlab.js          仿真浮层（复用 v1.2 端点，重皮肤）
  js/ble.js             Web Bluetooth 真机模式（沿用 BLE.md 契约与 0xA5 编码）
  vendor/three.module.js r16x + OrbitControls/STLLoader/RoomEnvironment（jsm）
  flows.json + hotspots.json ← tools/make_flows.py（读 pos.csv，mesh 管线旁）
```
- **server.py 增路由**：`/` → webapp/index.html；`/webapp/*` 静态（含 `.js`→`text/javascript` module、`.json`、`.css`）；`/classic` → 旧 gui.html；`/gui` → 重定向 `/`（一个版本过渡期后移除）
- **Three 升级 r128→r16x**：unpkg/jsdelivr vendor 单次下载（three.module.js + 三个 jsm addon），S3 STL 不变；旧 gui 继续用 r128 不动
- 兼容：`/lib/echarts.min.js` 保留供遥测抽屉小图

## 6. 数据与错误处理

- 数据源不变：孪生模式 `/api/state`（气动/阀 duty/压力）+ `/api/board/state`（电气遥测）；真机 BLE 模式 state notify 20B → 同一 store（p1_renderState 语义延续）
- 断连/stale：主场景流光淡出为底光，顶栏徽章变灰"连接中断"（不弹窗——Apple 式安静）
- WebGL 不可用：场景区显示优雅提示卡（玻璃风），其余抽屉仍可用
- 性能预算：桌面 i5/核显 ≥45fps（粒子总量≤500、dpr≤2、面板 blur 层数≤3）；debug 浮层（`?debug`）显示 fps/粒子数/请求延迟

## 7. 测试与验收

- **playwright 迁移**：test_gui_p1.js → test_webapp.js（新 DOM 锚点：场景 canvas、抽屉开关、热点卡、sim 浮层、运输条）；旧 test_gui.js 继续跑 /classic 一版
- **flows 同源性测试**：make_flows.py 输出断言（每条 elec 路径起止点=对应器件 pos.csv 坐标±0.1mm；air 路径起点=端子坐标）
- **强制目视检查**（用户长期铁律）：装配动画、爆炸跟随流线、阀开→栅极电流亮起+端子气流喷出、真空回流反向、热点卡、sim 浮层、断连态——截图 + 机内视觉逐项审（F3 模式），不通过即修
- **性能冒烟**：`?debug` 模式 60s 采样 fps 均值≥45

## 8. 交付物与退线

| 交付 | 说明 |
|---|---|
| webapp/ 全部源 + vendor | 零构建，server.py 直服 |
| tools/make_flows.py + flows/hotspots.json | 流拓扑与板同源 |
| server.py 路由增量 + /classic 过渡 | v1.2 端点零改动 |
| test_webapp.js + flows 同源测试 + 截图目视档 | 验收三件 |
| 旧 gui.html | 打"经典版"标，暂留 /classic |

## 9. 风险

| 风险 | 缓解 |
|---|---|
| Three r16x vendor 拉取失败（网络） | 备选 jsdelivr；再失败退 r155；全失败则 BLOCKED 上报 |
| 粒子+blur 性能不足 | 令牌化降级（blur 减层/粒子减半/?perf=low 预设） |
| 流拓扑表手工错误 | make_flows 同源断言 + 热点抽查 3 器件坐标 |
| 旧 gui 依赖无人迁移 | /classic 保留一个版本；v2 验收通过后再定下线 |
