# 数字孪生前端 v2 实施计划（产品爆炸视图核心 · Apple Liquid Glass）

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 按 spec `2026-10-02-twin-frontend-v2-design.md` 重做孪生前端——全屏 3D 产品场景为唯一主角，气流粒子与电流辉光由实时数据驱动"长在"产品上，仪表盘降级为玻璃抽屉/浮层，视觉对标 Apple Liquid Glass。

**Architecture:** 零构建 ES Modules（server.py 直服 /webapp），Three.js r16x module + 自定义 CSS 设计令牌系统；流拓扑由 make_flows.py 从 pos.csv 同源生成 flows.json/hotspots.json；数据层沿用 API v1.2 与 BLE 契约零改动；旧 gui.html 挂 /classic 过渡。

**Tech Stack:** Three.js r16x (module + OrbitControls/STLLoader/RoomEnvironment jsm) · 原生 ES Modules + CSS 设计令牌 · ECharts(仅遥测抽屉小图) · Playwright 测试 · KPY（server 运行时）

**SPEC:** `docs/superpowers/specs/2026-10-02-twin-frontend-v2-design.md`
**约定:** 命令自 `E:/FLOWIO/`；KPY=`"E:/Program Files/KiCad/10.0/bin/python.exe"`；源码一律 Write/Edit 工具（Mimosa：禁 open(w)/eval/exec/上跳路径，产物落盘用 Path.write_bytes）；每 Task 末提交 main。

---

### Task 1: Vendor Three r16x + server.py 静态路由 + webapp 骨架

**Files:**
- Create: `firmware/twin/webapp/index.html`、`css/twin.css`（令牌+骨架样式）、`js/main.js`（空壳）
- Create: `firmware/twin/webapp/vendor/`（three.module.js、addons/）
- Modify: `firmware/twin/server.py`（路由）

- [ ] **Step 1: Vendor 三件下载（任一成功源）**

```bash
cd firmware/twin/webapp && mkdir -p vendor/addons
for base in "https://unpkg.com/three@0.160.0" "https://cdn.jsdelivr.net/npm/three@0.160.0"; do
  curl -sfL "$base/build/three.module.js" -o vendor/three.module.js && \
  curl -sfL "$base/examples/jsm/controls/OrbitControls.js" -o vendor/addons/OrbitControls.js && \
  curl -sfL "$base/examples/jsm/loaders/STLLoader.js" -o vendor/addons/STLLoader.js && \
  curl -sfL "$base/examples/jsm/environments/RoomEnvironment.js" -o vendor/addons/RoomEnvironment.js && break
done
ls -la vendor/three.module.js vendor/addons/*.js   # 三个均 >5KB；任一为 0 字节→按 spec §9 退 r155 再失败 BLOCKED
```

- [ ] **Step 2: server.py 增路由（do_GET 分支，仿 echarts 静态模式）**

```python
        elif path == "/" or path == "/webapp" or path == "/webapp/":
            self._send(200, open(os.path.join(WEBAPP, "index.html"), 'rb').read(), "text/html")
        elif path == "/gui":
            self._send(301, b"", "text/html", extra_headers={"Location": "/"})
        elif path == "/classic":
            self._send(200, open(os.path.join(HERE, "gui.html"), 'rb').read(), "text/html")
        elif path.startswith("/webapp/"):
            rel = path[len("/webapp/"):]
            if not re.fullmatch(r"[A-Za-z0-9_./-]+", rel) or ".." in rel: self._send(404, b"", "text/plain"); return
            fp = os.path.join(WEBAPP, rel)
            mime = {".js": "text/javascript", ".css": "text/css", ".json": "application/json",
                    ".html": "text/html", ".png": "image/png"}.get(os.path.splitext(rel)[1], "application/octet-stream")
            if os.path.isfile(fp): self._send(200, open(fp, 'rb').read(), mime)
            else: self._send(404, b"not found", "text/plain")
```
（`WEBAPP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "webapp")`；`_send` 支持可选 `extra_headers` 参数，若现有签名无则加 `extra_headers=None` 形参。）

- [ ] **Step 3: index.html + twin.css 设计令牌 + main.js 空壳**

index.html 骨架（顶栏/场景容器/左右抽屉/运输条/状态行/仿真浮层容器，全部 id 前缀 `t2_`）：
```html
<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">
<title>FLOWIO-CN · 数字孪生</title><link rel="stylesheet" href="/webapp/css/twin.css">
</head><body>
<header id="t2_topbar"><span class="t2_brand">FLOWIO-CN</span>
  <span id="t2_modeBadge" class="t2_badge">孪生</span>
  <button id="t2_bleBtn" class="t2_btn ghost">连接真机</button></header>
<main id="t2_stage"><canvas id="t2_canvas"></canvas>
  <aside id="t2_ctrlDrawer" class="t2_drawer left"></aside>
  <div id="t2_transport" class="t2_pill"></div>
  <aside id="t2_tlmDrawer" class="t2_drawer right"></aside>
  <div id="t2_hotspotCard" class="t2_card"></div></main>
<footer id="t2_statusbar"><span id="t2_calBadge" class="t2_badge warn">模型参数：理论值（未本机标定）</span>
  <span id="t2_timeInfo"></span><button id="t2_simLabBtn" class="t2_btn ghost">仿真实验室</button></footer>
<div id="t2_simOverlay" hidden></div>
<script type="module" src="/webapp/js/main.js"></script></body></html>
```
twin.css 核心（完整令牌见 spec §4，此处为全量必需集）：
```css
:root{ --bg0:#101014;--bg1:#0a0a0c;--txt:rgba(255,255,255,.92);--txt2:rgba(255,255,255,.55);
  --accent:#6aa9ff;--air-p:#6ad4ff;--air-v:#ffb454;--e5:#e8b64c;--e3:#7ee2b8;--eg:#6aa9ff;
  --glass:rgba(255,255,255,.06);--hair:rgba(255,255,255,.12);
  --ease:cubic-bezier(.22,1,.36,1);--font:-apple-system,"SF Pro Display","PingFang SC","Microsoft YaHei",sans-serif}
*{box-sizing:border-box;margin:0}html,body{height:100%;color:var(--txt);font-family:var(--font);background:var(--bg1)}
body{display:grid;grid-template-rows:48px 1fr 36px}
.t2_glass{background:var(--glass);backdrop-filter:blur(24px) saturate(180%);-webkit-backdrop-filter:blur(24px) saturate(180%);
  border:1px solid var(--hair);border-radius:20px;box-shadow:0 8px 32px rgba(0,0,0,.35)}
#t2_topbar{display:flex;align-items:center;gap:16px;padding:0 20px;border-bottom:1px solid var(--hair);
  background:rgba(10,10,12,.55);backdrop-filter:blur(24px);z-index:10}
.t2_brand{font-weight:600;letter-spacing:.02em}
.t2_badge{font-size:12px;padding:3px 10px;border-radius:99px;border:1px solid var(--hair);color:var(--txt2)}
.t2_badge.warn{color:#ffd479;border-color:rgba(255,212,121,.35)}
#t2_stage{position:relative;overflow:hidden;background:radial-gradient(120% 100% at 50% 20%,var(--bg0),var(--bg1))}
#t2_canvas{width:100%;height:100%;display:block}
.t2_drawer{position:absolute;top:60px;bottom:52px;width:264px;transition:transform .2s var(--ease);z-index:5}
.t2_drawer.left{left:12px}.t2_drawer.right{right:12px}
.t2_drawer.collapsed{transform:translateX(calc(-100% - 24px))}
.t2_drawer.right.collapsed{transform:translateX(calc(100% + 24px))}
.t2_pill{position:absolute;left:50%;bottom:44px;transform:translateX(-50%);display:flex;gap:10px;align-items:center;
  padding:10px 18px;z-index:5}
.t2_btn{font:inherit;color:var(--txt);background:var(--glass);border:1px solid var(--hair);border-radius:10px;
  padding:6px 14px;cursor:pointer;transition:all .15s var(--ease)}
.t2_btn:hover{background:rgba(255,255,255,.12)} .t2_btn:disabled{opacity:.4;cursor:default}
.t2_btn.ghost{background:transparent}
.t2_card{position:absolute;right:292px;bottom:52px;width:240px;padding:16px;z-index:6;
  transition:opacity .2s var(--ease),transform .2s var(--ease)}
.t2_card.hidden{opacity:0;transform:translateY(8px);pointer-events:none}
#t2_statusbar{display:flex;align-items:center;gap:16px;padding:0 20px;border-top:1px solid var(--hair);
  font-size:12px;color:var(--txt2);background:rgba(10,10,12,.55);backdrop-filter:blur(24px)}
#t2_simOverlay{position:fixed;inset:0;z-index:20;background:rgba(10,10,12,.6);backdrop-filter:blur(8px)}
#t2_simOverlay[hidden]{display:none}
.t2_num{font-variant-numeric:tabular-nums}
input[type=range].t2_explode{width:220px;accent-color:var(--accent)}
```
main.js 空壳（模块入口 + 抽屉开合 + 占位渲染循环）：
```javascript
// firmware/twin/webapp/js/main.js — v2 应用壳
const $ = (id) => document.getElementById(id);
export const store = { mode: "twin", explode: 0, telemetry: null, pnu: null };
const subs = new Set();
export function onState(fn) { subs.add(fn); return () => subs.delete(fn); }
export function setState(patch) { Object.assign(store, patch); subs.forEach((f) => f(store)); }
function initChrome() {
  $("t2_ctrlDrawer").innerHTML = '<h3>控制</h3><p style="color:var(--txt2)">待 Task 6 填充</p>';
  $("t2_tlmDrawer").innerHTML = '<h3>遥测</h3><p style="color:var(--txt2)">待 Task 6 填充</p>';
  $("t2_transport").innerHTML = '<span style="color:var(--txt2)">待 Task 6 填充</span>';
}
initChrome();
```

- [ ] **Step 4: 路由冒烟**

起服 KPY server.py 后：`curl -s localhost:8000/ | head -3` 含 `t2_canvas`；`curl -s -o /dev/null -w "%{http_code}" localhost:8000/webapp/js/main.js` = 200 且 `curl -sI localhost:8000/webapp/js/main.js | grep -i content-type` 含 `text/javascript`；`curl -s -o /dev/null -w "%{http_code}" localhost:8000/classic` = 200；`curl -s -o /dev/null -w "%{http_code}" "localhost:8000/webapp/../server.py"` = 404。

- [ ] **Step 5: 提交** — `git add firmware/twin/webapp firmware/twin/server.py && git commit -m "feat(webapp): v2 骨架——Liquid Glass 令牌/路由(//classic)/vendor three r16x"`

---

### Task 2: make_flows.py → flows.json + hotspots.json（同源流拓扑）

**Files:**
- Create: `hardware/flowio-p1/enclosure/make_flows.py`
- Output: `firmware/twin/webapp/flows.json`、`hotspots.json`
- Test: `hardware/flowio-p1/enclosure/test_flows.py`

- [ ] **Step 1: 拓扑表（写进脚本，数据源=pos.csv+引脚表）**

电气路径（板坐标 mm，z=4.0 板面；走曼哈顿折线；**器件 ref 从 pos.csv 查坐标**）：
```python
ELEC = [
 ("vin_dc",  "#e8b64c", ["J1","D1","C1"],            "rail_5v.load_a"),
 ("vin_usb", "#e8b64c", ["J2","D2","C17"],           "rail_5v.load_a"),
 ("buck_in", "#e8b64c", ["C1","U3","L1"],            "rail_3v3.load_a"),
 ("rail3v3", "#7ee2b8", ["L1","C8","U1"],            "rail_3v3.load_a"),
] + [(f"gate{i+1}", "#6aa9ff", ["U1", f"R{39+i}", f"Q{3+i}", f"J{10+i}"], f"valves[{i}].i_A")
     for i in range(8)]
AIR = [(f"port{i+1}", 9.0, f"J{10+i}") for i in range(8)]   # 端子 ref, 延伸长 9mm? → 25mm 定長
```
（ref 若在 pos.csv 查不到→报错列出，不许静默跳过。）
- [ ] **Step 2: 生成逻辑**：读 `fab/flowio-p1-pos.csv`（Y=-PosY 已在 S3 验证）；板→壳坐标 +2.9、顶器件 z=4.0、底 z=2.0；电气相邻器件焊盘间生成曼哈顿折线（先 x 后 y，段数=中点数+1）；气流路径=端子中心出发，沿 -Y 弧线（QuadraticBezier 控制点 (x, y-14, z)）至 (x, y-25, z)；hotspots.json=精选取 6 器件 {U1,U3,Q3,J1,J10,U2} 的 {center,size,live 字段映射, 中文名}；全部 `Path.write_bytes(json.dumps(...).encode())` 落 webapp/。
- [ ] **Step 3: 同源断言测试（test_flows.py）**：每条 elec 路径首尾点=对应首尾器件坐标±0.1；gate 路径数=8；air 路径起点=对应端子±0.1 且终点 y=端子y-25±0.1；hotspots 6 项。跑通输出 `flows tests OK`。
- [ ] **Step 4: 提交** — `git add hardware/flowio-p1/enclosure/make_flows.py hardware/flowio-p1/enclosure/test_flows.py firmware/twin/webapp/flows.json firmware/twin/webapp/hotspots.json && git commit -m "feat(webapp): 流拓扑同源生成 (pos.csv→flows/hotspots.json, 同源断言)"`

---

### Task 3: scene.js — 3D 主场景（装配叙事/爆炸/材质/热点）

**Files:**
- Create: `firmware/twin/webapp/js/scene.js`
- Modify: `js/main.js`（挂载场景）

- [ ] **Step 1: 场景核心（完整实现要点+关键代码）**

```javascript
// scene.js — 全屏产品场景: 装配叙事 / 爆炸 / Liquid Glass 材质 / 热点
import * as THREE from "/webapp/vendor/three.module.js";
import { OrbitControls } from "/webapp/vendor/addons/OrbitControls.js";
import { STLLoader } from "/webapp/vendor/addons/STLLoader.js";
import { RoomEnvironment } from "/webapp/vendor/addons/RoomEnvironment.js";

export async function createScene(canvas, onPartClick) {
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  const scene = new THREE.Scene();
  scene.environment = new THREE.PMREMGenerator(renderer).fromScene(new RoomEnvironment(), .04).texture;
  const camera = new THREE.PerspectiveCamera(38, 2, .1, 500);
  camera.position.set(70, -95, 60); camera.lookAt(0, 0, 10);   // 板 y 已翻转后自定
  const controls = new OrbitControls(camera, canvas); controls.enableDamping = true;
  // 装配动画: 每部件从 explode*3 的散位 lerp 回 explode*k; t∈[0,1] easeOutQuint
  // 材质: parts_f→#b9bcc2 roughness.5 metalness.1; pcb→#0f3d2a roughness.65 metalness.25;
  //       壳→#9a9a9e roughness.55; 顶亮/底暗平行光+环境, ContactShadow 用地面圆盘渐变纹理替代(r16x 无内建)
  // raycaster: pointerdown→intersectObjects(parts)→onPartClick(part.userData)
  // resize: ResizeObserver(canvas.parentElement)→renderer.setSize/camera.aspect
  // 返回句柄: { setExplode(k), setHighlight(partId|null), pulsePart(partId), parts, render(t) }
  // render 每帧: 装配 lerp、呼吸悬浮 sin(t/4)*0.3、controls.update、内部调 flows 渲染回调
}
```
（装配叙事：初始 k=1 全爆 + 部件额外位移 ×2.5、页面加载后 1.5s 内 k:1→0 缓动 `easeOutQuint(t)=1-(1-t)^5`；呼吸=整机组 y += sin·0.3mm。ContactShadow 替代方案：半径 60mm 圆盘 + 径向透明渐变 CanvasTexture 贴地 y=-20。）

- [ ] **Step 2: main.js 挂载 + 爆炸滑杆入运输条**

main.js 增：`createScene($("t2_canvas"), onHotspot).then(h => scene = h)`；运输条注入：播放/暂停/单步按钮（POST /api/time）+ `<input type="range" class="t2_explode" min="0" max="1" step="0.01">` → `scene.setExplode(k)` + `setState({explode:k})`。

- [ ] **Step 3: 冒烟** — 起服，playwright 打开 `/` 等 3s 截图：canvas 非空白、5 部件渲染（借视觉分析）；`?debug` 叠 fps。
- [ ] **Step 4: 提交** — `git commit -m "feat(webapp): 3D 主场景——装配叙事/爆炸滑杆/材质升级/热点拾取"`

---

### Task 4: flows.js — 电流辉光 + 气流粒子（数据驱动）

**Files:**
- Create: `firmware/twin/webapp/js/flows.js`
- Modify: `js/scene.js`（注册 flows 渲染回调）、`js/main.js`（装配数据）

- [ ] **Step 1: 电流 shader 虚线（关键代码）**

```javascript
// flows.js — 电流: Line+ShaderMaterial 行进虚线; 气流: Points 沿 Bezier
const LINE_VS = `attribute float aT; varying float vT; void main(){ vT=aT;
  gl_Position = projectionMatrix*modelViewMatrix*vec4(position,1.); }`;
const LINE_FS = `uniform float uTime,uSpeed,uGain; uniform vec3 uColor; varying float vT;
  void main(){ float d = fract(vT*40. - uTime*uSpeed); float dash = smoothstep(.0,.15,d)*smoothstep(.5,.35,d);
  float a = (0.08 + dash*0.92) * uGain; gl_FragColor = vec4(uColor, a); }`;
```
（每路径一条 `THREE.Line`：positions=折线点、aT=弧长归一；uniforms 每帧更新：`uGain=0.25+0.75*live01`、`uSpeed=0.6+2.2*live01`；material.transparent+AdditiveBlending+depthWrite:false。live01=遥测字段归一（valves[n].i_A/0.36、load_a/3.0）。）

- [ ] **Step 2: 气流粒子**：每端口 `THREE.Points`（50 粒，PointsMaterial size .8、圆点 CanvasTexture、Additive）；粒子沿 QuaBezier 参数 t 循环 `t=(t0+time*speed)%1`，speed=0.15+0.85*duty01；方向反向=真空（t 递减）；颜色 air-p/air-v 切换；**端点绑定**：曲线控制点=端子锚点+explode*k 位移（每帧重算曲线或对 Points 组做同位移）。
- [ ] **Step 3: 数据管道**：telemetry 轮询（Task 6 的 store）+ `/api/state`（阀 duty、压力符号）→ flows.update({valves, rail5, rail33, pressureSign}) → uniforms/粒子参数直写；断连→uGain 降为底光 0.08、粒子淡出。
- [ ] **Step 4: 冒烟（联动实证）**：playwright 起 `/`，POST /api/cmd `I 1 255` 等 1s 截图 A；`R 1` 等 .5s 截图 B；机内视觉审：A 中 1 号端子有粒子拖尾/栅极线亮于 B。
- [ ] **Step 5: 提交** — `git commit -m "feat(webapp): 电流辉光+气流粒子——遥测驱动长在产品上, 爆炸跟随"`

---

### Task 5: telemetry.js + panels.js — 抽屉/运输条/热点卡/状态行

**Files:**
- Create: `firmware/twin/webapp/js/telemetry.js`、`js/panels.js`
- Modify: `js/main.js`

- [ ] **Step 1: telemetry.js**：200ms 交替轮询 `/api/board/state?since=` 与 `/api/state`（阀 duty→阵列、压力 p、状态字）→ setState；document.hidden / 传服 paused 停轮询；错误→setState({stale:true})。
- [ ] **Step 2: panels.js 三件**
  - 遥测抽屉（右）：5 张 sparkline 玻璃小卡（5V/3.3V/负载/温度/buck 效率）——canvas 2D 手绘 sparkline（60 点折线，无网格，细线+末端数值 `t2_num`），点卡展开 ECharts 小图（复用 v1.2 历史 since 语义）
  - 控制抽屉（左）：阀 1-8 + 泵的 Apple 分段控件（玻璃胶囊内 4 段：充/保/释/抽 → p1_sendCmd 等价 'I/H/R/V' CLI；命令通道抽象 `sendCmd(line)`：孪生=POST /api/cmd、真机=BLE）
  - 热点卡：hotspots.json 器件表 → onPartClick(h) 填充卡（中文名+2-4 live 值+迷你横条）；transport 状态（录制红点/时间）
- [ ] **Step 3: 冒烟**：playwright 断言抽屉开合/控件点击发出命令（拦截 fetch 计数）/热点卡出现；目视截图。
- [ ] **Step 4: 提交** — `git commit -m "feat(webapp): 遥测抽屉sparkline/控制分段控件/热点卡——仪表盘降级为辅助"`

---

### Task 6: simlab.js（仿真浮层）+ ble.js（真机模式迁移）+ statusbar

**Files:**
- Create: `firmware/twin/webapp/js/simlab.js`、`js/ble.js`
- Modify: `js/main.js`

- [ ] **Step 1: simlab.js**：`仿真实验室` 按钮 → `#t2_simOverlay` 升起（玻璃全屏）；复用 v1.2 端点 presets/sim；四电路分段控件+参数表单（bounds 限值）+重算（禁用态"计算中…"）+波形 canvas 绘制（自绘细线，不复用 ECharts 亦可）+指标 ✓/⚠ 徽章；ESC/关闭回落。
- [ ] **Step 2: ble.js**：从旧 gui.html 移植 Web Bluetooth（BLE.md 契约、0xA5 CRC-8/0x07 编码、20B state 解析）→ state notify 进 store 同管道（p1_renderState 语义）；顶栏徽章 孪生↔真机 切换、真机停 HTTP 轮询；断连安静降级（徽章灰、流光回底光）。
- [ ] **Step 3: 状态行**：stale 红点/未标定黄徽（常驻）/时间与录制状态/`?debug`（fps+粒子+延迟浮层）。
- [ ] **Step 4: 冒烟+提交** — `git commit -m "feat(webapp): 仿真浮层+BLE真机模式迁移+状态行"`

---

### Task 7: test_webapp.js + 旧测试挂 /classic + 全回归

**Files:**
- Create: `firmware/twin/test_webapp.js`
- Modify: `firmware/twin/test_gui.js`、`test_gui_p1.js`（入口改 /classic；gui.html 不改代码仅路由语义变化）

- [ ] **Step 1: test_webapp.js（playwright，≥30 断言）**：装配动画后 5 部件在场（scene 句柄 window.__t2 暴露调试钩）；爆炸滑杆 setExplode(1) 部件位移>10mm；`I 1 255` 后 gate1 线 uniform uGain>0.5 且 1 号粒子系统 visible（经 __t2 读 uniforms）；真空反向（`V 255` 压力符号→粒子速度符号）；抽屉开合/控制命令 fetch 拦截计数；热点卡内容；sim 浮层 400 越域红条；/classic 旧测试照跑。
- [ ] **Step 2: 全回归**：`node test_webapp.js && node test_gui.js && node test_gui_p1.js && bash test_api.sh && bash test_api_board.sh`（后两者不受影响应原绿）+ KPY test_sim_engine/test_board_model。
- [ ] **Step 3: 提交** — `git commit -m "test(webapp): v2 全链断言(流光/粒子/爆炸/热点/浮层) + classic 挂载"`

---

### Task 8: 强制目视检查 + 性能冒烟 + 收尾

- [ ] **Step 1: 目视清单截图+机内视觉逐项审**（F3 模式，≥8 张）：首屏装配、爆炸 50%、阀开气流+电流对比（开/关各一）、真空回流、热点卡 buck、遥测抽屉展开、sim 浮层、断连态（停服截图）。发现 Critical/Important 即修即重截。
- [ ] **Step 2: 性能**：`?debug` 60s 采样 fps 均值≥45（playwright rAF 计数），超标则粒子减半/blur 降层（令牌化 `?perf=low`）。
- [ ] **Step 3: 文档**：twin/README v2 截图与用法一节；API.md §0 前端入口改 `/`（v1.2 端点零改）；HANDOFF 增 v2 交付节。
- [ ] **Step 4: 终提交** — `git add -A && git commit -m "feat: 孪生前端 v2 交付——产品爆炸视图核心, 气流电流长在产品上, Liquid Glass"`

---

## 完成定义
1. `/` = 产品场景核心的 v2（装配叙事/爆炸/数据驱动流光/玻璃抽屉），`/classic` 旧版可退
2. 流拓扑同源断言绿 + test_webapp ≥30 断言绿 + 旧五套回归全绿
3. 目视 8 项过 + fps≥45
4. spec §2-§7 逐条可指认落点；API v1.2 零改动
