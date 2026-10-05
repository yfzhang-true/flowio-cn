// firmware/twin/webapp/js/panels.js — 抽屉/运输条/热点卡 (Task5)
// 三件: ①遥测抽屉(右, 5 张 sparkline 玻璃小卡, 点卡展开 ECharts 小图)
//      ②控制抽屉(左, 阀1-8+全局 Apple 分段控件 充/保/释/抽 → sendCmd CLI)
//      ③热点卡(hotspots.json live 字段 → 中文名+实时值+迷你横条)
// 另: 运输条扩展 (速度/录制/回放) —— 与 main.js 的 sendCmd/postJSON 单向依赖 (无顶层求值, 循环安全)。
import { store, onState, setState, sendCmd, postJSON, rec } from "./main.js";
import { series, seriesFull } from "./telemetry.js";

const $ = (id) => document.getElementById(id);

/* ══════════ ① 遥测抽屉 (右) ══════════ */
const TLM_CARDS = [
  { id: "v5", name: "5V 轨", unit: "V", dec: 3, color: "#e8b64c", get: (t) => t.rail_5v.v },
  { id: "v33", name: "3.3V 轨", unit: "V", dec: 3, color: "#7ee2b8", get: (t) => t.rail_3v3.v },
  { id: "load", name: "5V 负载", unit: "A", dec: 2, color: "#6aa9ff", get: (t) => t.rail_5v.load_a },
  { id: "temp", name: "结温峰值", unit: "℃", dec: 1, color: "#ffb454", get: (t) => {
      const x = t.temp_est_c || {}; return Math.max(x.cpu || 0, x.buck || 0, x.mos || 0); } },
  { id: "eff", name: "Buck 效率", unit: "%", dec: 1, color: "#6ad4ff", get: (t) => t.rail_3v3.buck_eff * 100 },
];

let echartsLoading = null;          // 按需加载 /lib/echarts.min.js (仅展开小图用)
function loadECharts() {
  if (window.echarts) return Promise.resolve(window.echarts);
  if (!echartsLoading) echartsLoading = new Promise((res, rej) => {
    const s = document.createElement("script");
    s.src = "/lib/echarts.min.js";
    s.onload = () => res(window.echarts);
    s.onerror = () => { echartsLoading = null; rej(new Error("echarts 加载失败")); };
    document.head.appendChild(s);
  });
  return echartsLoading;
}

let expandId = null;                // 当前展开小图通道 (null=收起)
let expandChart = null;

// canvas 2D 手绘 sparkline: 60 点折线, 无网格, 细线+末端点 (spec §4 克制红线)
function drawSpark(cv, data, color) {
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  const w = cv.clientWidth || 216, h = cv.clientHeight || 34;
  if (cv.width !== w * dpr || cv.height !== h * dpr) { cv.width = w * dpr; cv.height = h * dpr; }
  const g = cv.getContext("2d");
  g.setTransform(dpr, 0, 0, dpr, 0, 0);
  g.clearRect(0, 0, w, h);
  if (!data || data.length < 2) return;
  let lo = Math.min(...data), hi = Math.max(...data);
  const span = (hi - lo) || Math.abs(hi) * 0.08 || 1;   // 防零跨度
  lo -= span * 0.18; hi += span * 0.18;
  const X = (i) => 2 + (i / (data.length - 1)) * (w - 8);
  const Y = (v) => h - 3 - ((v - lo) / (hi - lo)) * (h - 6);
  g.strokeStyle = color;
  g.lineWidth = 1.25;
  g.lineJoin = "round";
  g.lineCap = "round";
  g.beginPath();
  data.forEach((v, i) => (i ? g.lineTo(X(i), Y(v)) : g.moveTo(X(i), Y(v))));
  g.stroke();
  g.fillStyle = color;                                   // 末端亮点
  g.beginPath();
  g.arc(w - 4, Y(data[data.length - 1]), 2, 0, Math.PI * 2);
  g.fill();
}

function initTlmDrawer() {
  const d = $("t2_tlmDrawer");
  d.innerHTML = `
    <div class="t2_dHead"><h3>遥测</h3><button id="t2_tlmCollapse" class="t2_btn ghost">收起 ›</button></div>
    <div id="t2_tlmExpand"></div>
    <div id="t2_tlmCards">${TLM_CARDS.map((c) => `
      <div class="t2_tCard" data-ch="${c.id}">
        <div class="t2_tCardTop"><span>${c.name}</span><b class="t2_num" id="t2_tv_${c.id}">—</b></div>
        <canvas class="t2_spark" id="t2_tsp_${c.id}"></canvas>
      </div>`).join("")}
    </div>`;
  d.classList.add("collapsed");                           // spec §2: 遥测抽屉默认收起
  $("t2_tlmCollapse").onclick = () => drawerToggle(d, $("t2_tlmTab"));
  $("t2_tlmCards").addEventListener("click", (ev) => {
    const card = ev.target.closest(".t2_tCard");
    if (card) openExpand(card.dataset.ch);
  });
}

function drawerToggle(drawer, tab) {
  const col = drawer.classList.toggle("collapsed");
  if (tab) tab.hidden = !col;
}

// 点卡展开 ECharts 小图 (v5/v33/load=服务端历史镜像; temp/eff=快照环; 复用 since 语义数据)
async function openExpand(id) {
  const c = TLM_CARDS.find((x) => x.id === id);
  if (!c) return;
  expandId = id;
  const box = $("t2_tlmExpand");
  box.innerHTML = `
    <div class="t2_tCard on">
      <div class="t2_tCardTop"><span>${c.name} · 历史</span>
        <button id="t2_tlmExpClose" class="t2_btn ghost" style="padding:2px 10px">✕</button></div>
      <div id="t2_tlmChart" style="height:150px"></div>
    </div>`;
  box.hidden = false;
  $("t2_tlmExpClose").onclick = closeExpand;
  for (const el of document.querySelectorAll("#t2_tlmCards .t2_tCard"))
    el.classList.toggle("on", el.dataset.ch === id);
  try {
    const echarts = await loadECharts();
    expandChart = echarts.init($("t2_tlmChart"));
    refreshExpand();
  } catch (e) {
    $("t2_tlmChart").innerHTML = `<p style="color:var(--txt2);font-size:12px;padding:12px">${e.message}</p>`;
  }
}
function closeExpand() {
  expandId = null;
  expandChart = null;
  $("t2_tlmExpand").innerHTML = "";
  for (const el of document.querySelectorAll("#t2_tlmCards .t2_tCard")) el.classList.remove("on");
}
function refreshExpand() {
  if (!expandId || !expandChart) return;
  const { t, y } = seriesFull(expandId);
  expandChart.setOption({
    animation: false,
    grid: { left: 46, right: 10, top: 8, bottom: 20 },
    xAxis: { type: "value", axisLabel: { color: "rgba(255,255,255,.4)", fontSize: 10, formatter: (v) => v.toFixed(0) },
             splitLine: { show: false }, axisLine: { lineStyle: { color: "rgba(255,255,255,.15)" } } },
    yAxis: { type: "value", scale: true, splitLine: { show: false },
             axisLabel: { color: "rgba(255,255,255,.4)", fontSize: 10, formatter: (v) => v.toFixed(2) },
             axisLine: { show: false } },
    series: [{ type: "line", showSymbol: false, data: t.map((tv, i) => [tv, y[i]]),
               lineStyle: { color: (TLM_CARDS.find((c) => c.id === expandId) || {}).color, width: 1.5 } }],
  }, true);
}

let lastTelRef = null;              // 遥测引用未变则跳过重绘
function refreshTlm() {
  const tel = store.telemetry;
  for (const c of TLM_CARDS) {
    const el = $("t2_tv_" + c.id);
    const v = tel && tel.rail_5v ? c.get(tel) : undefined;
    el.textContent = (typeof v === "number" && isFinite(v)) ? v.toFixed(c.dec) + " " + c.unit : "—";
  }
  if (tel === lastTelRef) return;                       // pnu 节拍不重绘 spark
  lastTelRef = tel;
  for (const c of TLM_CARDS) drawSpark($("t2_tsp_" + c.id), series(c.id), c.color);
  if (expandId) refreshExpand();
}

/* ══════════ ② 控制抽屉 (左) ══════════ */
const VALVE_NAMES = ["阀1·端口", "阀2·端口", "阀3·端口", "阀4·端口", "阀5·端口",
                     "阀6·进气", "阀7·排气", "阀8·备用"];
const SEGS = [                       // 分段语义 (固件实证): 释=S 确定性关阀 (R 不清 duty); 保=H 诊断保压
  { cmd: "I", label: "充" }, { cmd: "H", label: "保" },
  { cmd: "S", label: "释" }, { cmd: "V", label: "抽" },
];

function initCtrlDrawer() {
  const d = $("t2_ctrlDrawer");
  // 双 PWM 滑条 —— 对齐官方 GUI 参考 (资源/官方参考/flowio-official-gui-reference.png):
  // Vacuum PWM / Inflation PWM 两档泵功率 (官方 setPumpPower 语义: 充气/真空独立设压),
  // I 命令携充气档、V 命令携真空档; 255 制与官方一致 (registry 泵上限 95%≈242,
  // 固件侧钳位, 孪生保持全域可探索)。
  d.innerHTML = `
    <div class="t2_dHead"><h3>控制</h3><button id="t2_ctrlCollapse" class="t2_btn ghost">‹ 收起</button></div>
    <label class="t2_pwmRow">充气 PWM
      <input type="range" id="t2_pwmInfl" min="80" max="255" step="1" value="255"
             title="Inflation PWM —— 充气(I)命令的泵功率档">
      <b id="t2_pwmInflVal" class="t2_num">255</b></label>
    <label class="t2_pwmRow">真空 PWM
      <input type="range" id="t2_pwmVac" min="80" max="255" step="1" value="255"
             title="Vacuum PWM —— 真空(V)命令的泵功率档">
      <b id="t2_pwmVacVal" class="t2_num">255</b></label>
    <div class="t2_vRow">
      <span class="nm">全局 1-5</span>
      <div class="t2_seg" data-port="g">${SEGS.map((s) =>
        `<button data-cmd="${s.cmd}" title="${s.label} → ${s.cmd} (掩码 31)">${s.label}</button>`).join("")}</div>
    </div>
    ${VALVE_NAMES.map((nm, i) => `
    <div class="t2_vRow">
      <span class="nm">${nm}</span><i class="t2_vDot" id="t2_vd_${i}"></i>
      <div class="t2_seg" data-port="${i}">${SEGS.map((s) =>
        `<button data-cmd="${s.cmd}" title="${s.label} → ${s.cmd} ${1 << i}">${s.label}</button>`).join("")}</div>
    </div>`).join("")}
    <div class="t2_ctrlFoot">
      <button class="t2_btn ghost" data-line="T" title="读 16 位状态字">状态字</button>
      <button class="t2_btn ghost" data-line="X" title="闭环状态机复位">闭环复位</button>
      <button class="t2_btn ghost" data-line="F" title="硬件自检（输出在服务端控制台）">自检</button>
    </div>`;
  $("t2_pwmInfl").oninput = (ev) => { $("t2_pwmInflVal").textContent = ev.target.value; };
  $("t2_pwmVac").oninput = (ev) => { $("t2_pwmVacVal").textContent = ev.target.value; };
  $("t2_ctrlCollapse").onclick = () => drawerToggle(d, $("t2_ctrlTab"));

  d.addEventListener("click", (ev) => {
    const line = ev.target.closest("[data-line]");
    if (line) { sendCmd(line.dataset.line); return; }
    const b = ev.target.closest(".t2_seg button");
    if (!b) return;
    const seg = b.closest(".t2_seg");
    const mask = seg.dataset.port === "g" ? 31 : (1 << parseInt(seg.dataset.port, 10));
    const cmd = b.dataset.cmd;
    sendCmd(cmd === "I" ? `${cmd} ${mask} ${$("t2_pwmInfl").value}`       // 充气 → 充气档
         : cmd === "V" ? `${cmd} ${mask} ${$("t2_pwmVac").value}`         // 真空 → 真空档
         : `${cmd} ${mask}`);
    b.classList.add("hit");                              // 点击回执微光
    setTimeout(() => b.classList.remove("hit"), 260);
  });
}

function refreshCtrl() {                                 // 阀位点灯: pnu duty>0 (真机/孪生同构)
  const duties = (store.pnu && store.pnu.valves) || [];
  for (let i = 0; i < 8; i++) {
    const dot = $("t2_vd_" + i);
    if (!dot) continue;
    const pv = duties[i];
    const on = pv !== undefined ? pv > 0
      : !!(store.telemetry && store.telemetry.valves && store.telemetry.valves[i] || {}).on;
    dot.classList.toggle("on", !!on);
  }
}

/* ══════════ ③ 热点卡 ══════════ */
// live 字段 → 归一满量程 (迷你横条宽度)
const FIELD_MAX = [
  [/^valves\[\d+\]\.i_A$/, 0.36], [/^valves\[\d+\]\.p_w$/, 1.6],
  [/^rail_5v\.v$/, 5.5], [/^rail_5v\.load_a$/, 3.0], [/^rail_5v\.p_w$/, 16],
  [/^rail_3v3\.v$/, 3.6], [/^rail_3v3\.load_a$/, 0.5], [/^rail_3v3\.buck_eff$/, 1.0],
  [/^temp_est_c\./, 85], [/^uptime_s$/, 3600],
];
function fieldMax(f) { for (const [re, m] of FIELD_MAX) if (re.test(f)) return m; return 0; }

function resolveField(obj, path) {                       // "valves[0].i_A" → 值
  return String(path).replace(/\[(\d+)\]/g, ".$1").split(".")
    .reduce((o, k) => (o == null ? o : o[k]), obj);
}

let lastHotspot = null;
// 骨架只在切换热点时重建 (200ms live 刷新只改数值/横条, 不动 DOM 结构 → 点击不被重建打断)
export function onPartClick(h) {
  const card = $("t2_hotspotCard");
  const changed = !h || h !== lastHotspot;
  lastHotspot = h || null;
  if (!h) { card.classList.add("hidden"); return; }
  card.classList.remove("hidden");
  if (!changed) { updateHotspotValues(); return; }
  if (h.type === "hotspot") {
    card.innerHTML = `<button class="t2_hsClose" id="t2_hsClose">✕</button>
      <h4>${h.name}</h4><div class="t2_hsRef">${h.ref} · 器件</div>
      ${(h.live || []).map((lv, i) => `
        <div class="t2_hsRow"><span>${lv.label}</span>
          <b class="t2_num" id="t2_hv_${i}">—</b></div>
        <div class="t2_hsBar"><i id="t2_hb_${i}" style="width:0%"></i></div>`).join("")}`;
  } else {
    card.innerHTML = `<button class="t2_hsClose" id="t2_hsClose">✕</button>
      <h4>${h.name}</h4><div class="t2_hsRef">${h.partId} · 部件</div>
      <div class="t2_hsRow"><span>拖动滑杆爆炸查看内部</span></div>`;
  }
  $("t2_hsClose").onclick = () => onPartClick(null);
  updateHotspotValues();
}
function updateHotspotValues() {
  const h = lastHotspot;
  if (!h || h.type !== "hotspot") return;
  (h.live || []).forEach((lv, i) => {
    const raw = resolveField(store.telemetry, lv.field);
    const isEff = lv.field === "rail_3v3.buck_eff";
    const v = typeof raw === "number" ? (isEff ? raw * 100 : raw) : NaN;
    const el = $("t2_hv_" + i), bar = $("t2_hb_" + i);
    if (el) el.textContent = (isFinite(v)
      ? (isEff ? v.toFixed(1) : v.toFixed(3).replace(/\.?0+$/, "")) : "—") + " " + (lv.unit || "");
    if (bar) {
      const m = fieldMax(lv.field);
      bar.style.width = (isFinite(raw) && m ? Math.max(0.02, Math.min(1, raw / m)) * 100 : 0).toFixed(0) + "%";
    }
  });
}

/* ══════════ 运输条 (播放/单步/速度/录制/爆炸) ══════════ */
function initTransport() {
  const tp = $("t2_transport");
  tp.classList.add("t2_glass");
  tp.innerHTML = `
    <button id="t2_playBtn" class="t2_btn ghost" title="暂停 / 继续孪生时间">⏸ 暂停</button>
    <button id="t2_stepBtn" class="t2_btn ghost" title="暂停下单步 50ms">单步</button>
    <label class="t2_explWrap">速度
      <input type="range" id="t2_speedRange" class="t2_speed" min="0.25" max="4" step="0.25" value="1">
      <span id="t2_speedVal" class="t2_num">×1.00</span></label>
    <span class="t2_tpDiv"></span>
    <button id="t2_recBtn" class="t2_btn ghost" title="录制本页发出的全部 CLI 命令 (recordings/ + 浏览器镜像)">⏺ 录制</button>
    <button id="t2_replayBtn" class="t2_btn ghost" hidden title="按墙钟时序回放">▶ <span id="t2_recN" class="t2_num">0</span></button>
    <span class="t2_tpDiv"></span>
    <label class="t2_explWrap">爆炸
      <input type="range" id="t2_explodeRange" class="t2_explode" min="0" max="1" step="0.01" value="0">
      <span id="t2_explodeVal" class="t2_num">0%</span></label>`;

  let paused = false;
  $("t2_playBtn").onclick = async () => {
    paused = !paused;
    $("t2_playBtn").textContent = paused ? "▶ 继续" : "⏸ 暂停";
    const j = await postJSON("/api/time", { paused });
    if (j) setState({ paused: !!j.paused });
  };
  $("t2_stepBtn").onclick = () => postJSON("/api/time", { step_once: true });
  $("t2_speedRange").onchange = async (ev) => {          // change 提交 (拖动不风暴)
    const j = await postJSON("/api/time", { speed: +ev.target.value });
    if (j) $("t2_speedVal").textContent = "×" + (+j.speed).toFixed(2);
  };
  $("t2_explodeRange").oninput = (ev) => {
    const k = parseFloat(ev.target.value);
    const sc = window.__t2 && window.__t2.scene;
    if (sc) sc.setExplode(k);
    setState({ explode: k });
    $("t2_explodeVal").textContent = Math.round(k * 100) + "%";
  };
  $("t2_recBtn").onclick = toggleRec;
  $("t2_replayBtn").onclick = replayRec;
}

async function toggleRec() {
  const on = !store.recording;
  setState({ recording: on });
  if (on) rec.events = [];
  const j = await postJSON("/api/record", { action: on ? "start" : "stop" });
  refreshRecUI();
  if (!on && rec.events.length) $("t2_recN").textContent = rec.events.length;
  return j;
}
async function replayRec() {
  const j = await postJSON("/api/record/replay", { events: rec.events });
  if (j && j.replaying !== undefined) $("t2_replayBtn").title = `回放 ${j.replaying} 条 (后台时序)`;
}
function refreshRecUI() {
  const btn = $("t2_recBtn");
  if (!btn) return;
  const on = !!store.recording;
  btn.textContent = on ? "⏹ 停止" : "⏺ 录制";
  btn.classList.toggle("rec", on);
  $("t2_replayBtn").hidden = on || !rec.events.length;
  $("t2_recN").textContent = rec.events.length;
}

/* ══════════ 状态行 (Task6: stale 红点 / 时间与录制 / 黄徽常驻在 index.html) ══════════ */
const fmtDur = (s) => {
  const m = Math.floor(s / 60), r = Math.round(s % 60);
  return m ? m + "m" + r + "s" : r + "s";
};
function refreshStatus() {
  const el = $("t2_staleBadge");
  if (!el) return;
  const tel = store.telemetry;
  el.hidden = !(!!store.stale || !!(tel && tel.stale));   // 网络断连 或 板级模型冻结
}
function tickTime() {
  const info = $("t2_timeInfo");
  if (!info) return;
  const tel = store.telemetry;
  const parts = [new Date().toLocaleTimeString("zh-CN", { hour12: false })];
  if (store.mode === "real") parts.push("真机 BLE");
  else if (tel && isFinite(tel.uptime_s)) parts.push("孪生 " + fmtDur(tel.uptime_s));
  if (store.recording) parts.push("● 录制中");
  else if (rec.events.length) parts.push("已录 " + rec.events.length + " 条");
  info.textContent = parts.join(" · ");
}
function initStatusbar() {
  setInterval(tickTime, 1000);
  tickTime();
}

/* ══════════ 总装 ══════════ */
export function initPanels() {
  initTlmDrawer();
  initCtrlDrawer();
  initTransport();
  initStatusbar();
  // 收起态浮钮 (抽屉滑出后仍可唤回)
  for (const [id, drawer] of [["t2_ctrlTab", $("t2_ctrlDrawer")], ["t2_tlmTab", $("t2_tlmDrawer")]]) {
    const tab = document.createElement("button");
    tab.id = id;
    tab.className = "t2_btn t2_glass t2_dTab";
    tab.hidden = id !== "t2_tlmTab";                     // 遥测默认收起 → 其浮钮初始可见
    tab.textContent = id === "t2_ctrlTab" ? "⚙" : "📈";
    tab.title = id === "t2_ctrlTab" ? "展开控制抽屉" : "展开遥测抽屉";
    tab.onclick = () => drawerToggle(drawer, tab);
    $("t2_stage").appendChild(tab);
  }
  onState(() => {
    refreshTlm();
    refreshCtrl();
    refreshStatus();
    tickTime();
    if (lastHotspot) onPartClick(lastHotspot);
  });
  refreshTlm();
  refreshCtrl();
  window.__t2 = window.__t2 || {};
  window.__t2.panels = { onPartClick, sendCmd };        // T7 测试调试钩
}
