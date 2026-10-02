// firmware/twin/webapp/js/main.js — v2 应用壳 (Task3: 场景挂载 + 运输条/爆炸滑杆)
import { createScene } from "/webapp/js/scene.js";

const $ = (id) => document.getElementById(id);
export const store = { mode: "twin", explode: 0, telemetry: null, pnu: null };
const subs = new Set();
export function onState(fn) { subs.add(fn); return () => subs.delete(fn); }
export function setState(patch) { Object.assign(store, patch); subs.forEach((f) => f(store)); }

let scene = null;                                 // createScene 句柄

// 遥测字段路径解析: "valves[0].i_A" / "rail_5v.load_a" / "temp_est_c.cpu"
function resolveField(obj, path) {
  return String(path).replace(/\[(\d+)\]/g, ".$1").split(".")
    .reduce((o, k) => (o == null ? o : o[k]), obj);
}

// 热点卡 (Task5 将扩展为完整 live 横条; 此处先给 名称+实时值 最小闭环)
let lastHotspot = null;
function fillHotspotCard(h) {
  const card = $("t2_hotspotCard");
  lastHotspot = h;
  if (!h) { card.classList.add("hidden"); return; }
  card.classList.remove("hidden");
  if (h.type === "hotspot") {
    const rows = (h.live || []).map((lv) => {
      const v = resolveField(store.telemetry, lv.field);
      const txt = (typeof v === "number") ? v.toFixed(3).replace(/\.?0+$/, "") : "—";
      return `<div class="t2_hsRow"><span>${lv.label}</span><b class="t2_num">${txt} ${lv.unit || ""}</b></div>`;
    }).join("");
    card.innerHTML = `<h4>${h.name}</h4><div class="t2_hsRef">${h.ref}</div>${rows}`;
  } else {
    card.innerHTML = `<h4>${h.name}</h4><div class="t2_hsRef">部件 · ${h.partId}</div>`;
  }
}
const onPartClick = (h) => fillHotspotCard(h);

async function postJSON(url, body) {
  try { await fetch(url, { method: "POST", body: JSON.stringify(body) }); } catch (e) { /* 断连由轮询侧呈现 */ }
}

// 运输条: 播放/暂停/单步 (POST /api/time) + 爆炸滑杆 → scene.setExplode
function initTransport() {
  const tp = $("t2_transport");
  tp.classList.add("t2_glass");
  tp.innerHTML = `
    <button id="t2_playBtn" class="t2_btn ghost" title="暂停 / 继续孪生时间">⏸ 暂停</button>
    <button id="t2_stepBtn" class="t2_btn ghost" title="暂停下单步 50ms">单步</button>
    <label class="t2_explWrap">爆炸
      <input type="range" id="t2_explodeRange" class="t2_explode" min="0" max="1" step="0.01" value="0">
      <span id="t2_explodeVal" class="t2_num">0%</span></label>`;
  let paused = false;
  $("t2_playBtn").onclick = () => {
    paused = !paused;
    $("t2_playBtn").textContent = paused ? "▶ 继续" : "⏸ 暂停";
    postJSON("/api/time", { paused });
  };
  $("t2_stepBtn").onclick = () => postJSON("/api/time", { step_once: true });
  $("t2_explodeRange").oninput = (ev) => {
    const k = parseFloat(ev.target.value);
    if (scene) scene.setExplode(k);
    setState({ explode: k });
    $("t2_explodeVal").textContent = Math.round(k * 100) + "%";
  };
}

// ?debug: fps 浮层 (Task6 将扩为 fps/粒子/延迟)
function initDebug() {
  if (!location.search.includes("debug")) return;
  const el = document.createElement("div");
  el.id = "t2_debug";
  el.style.cssText = "position:absolute;top:56px;left:16px;z-index:9;font:12px/1.6 ui-monospace,monospace;" +
    "color:#9fe08c;text-shadow:0 1px 2px #000;pointer-events:none;white-space:pre";
  $("t2_stage").appendChild(el);
  setInterval(() => { el.textContent = "fps " + (scene ? scene.fps.toFixed(0) : "—") + "\nparts " + (scene ? scene.parts.length : 0); }, 500);
}

// 数据管道 (Task6 将演进为 telemetry.js 200ms 交替轮询): 双源 → flows.update + setState
// 断连 → 流光降底光 0.08 / 粒子淡出 (spec §6 安静降级, 不弹窗)
async function pollData() {
  if (document.hidden || !scene) return;
  try {
    const [tel, pnu] = await Promise.all([
      fetch("/api/board/state").then((r) => r.json()),
      fetch("/api/state").then((r) => r.json()),
    ]);
    setState({ telemetry: tel, pnu, stale: false });
    if (scene.flows) scene.flows.update({ tel, pnu, connected: true });
  } catch (e) {
    setState({ stale: true });
    if (scene.flows) scene.flows.update({ connected: false });
  }
}

function initChrome() {
  for (const id of ["t2_ctrlDrawer", "t2_tlmDrawer", "t2_hotspotCard"]) $(id).classList.add("t2_glass");
  $("t2_ctrlDrawer").innerHTML = '<h3>控制</h3><p style="color:var(--txt2)">待 Task 6 填充</p>';
  $("t2_tlmDrawer").innerHTML = '<h3>遥测</h3><p style="color:var(--txt2)">待 Task 6 填充</p>';
  $("t2_hotspotCard").classList.add("hidden");
  initTransport();
  initDebug();
  createScene($("t2_canvas"), onPartClick)
    .then((h) => {
      scene = h;
      pollData();
      setInterval(pollData, 250);
      onState(() => { if (lastHotspot) fillHotspotCard(lastHotspot); });   // 卡内 live 值随遥测刷新
    })
    .catch((e) => {                                 // WebGL/装配失败 → 优雅降级卡 (spec §6)
      const d = document.createElement("div");
      d.className = "t2_glass";
      d.style.cssText = "position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);padding:24px;z-index:8";
      d.textContent = "3D 场景不可用：" + e.message;
      $("t2_stage").appendChild(d);
    });
}
initChrome();
