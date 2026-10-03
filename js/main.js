// firmware/twin/webapp/js/main.js — v2 应用壳 (Task5: 命令通道抽象 + panels/telemetry 挂载;
//                                             Task6: simlab 浮层 + BLE 真机模式 + debug 浮层扩展)
import { initPanels, onPartClick } from "./panels.js";
import { startTelemetry, latencyMs } from "./telemetry.js";
import { initSimLab } from "./simlab.js";
import { initBLE } from "./ble.js";

const $ = (id) => document.getElementById(id);
export const store = { mode: "twin", explode: 0, telemetry: null, pnu: null,
                       paused: false, recording: false, stale: false, bleActive: false };
const subs = new Set();
export function onState(fn) { subs.add(fn); return () => subs.delete(fn); }
export function setState(patch) { Object.assign(store, patch); subs.forEach((f) => f(store)); }

export const rec = { events: [] };                   // 命令录制客户端镜像 (回放用)

// ═══ 命令通道抽象: 孪生=POST /api/cmd (body=裸 CLI 文本) · 真机=BLE (ble.js 经 __t2.ble 接管) ═══
export async function sendCmd(line) {
  if (store.recording) rec.events.push({ t: Date.now() / 1000, cmd: line });
  if (store.bleActive && window.__t2 && window.__t2.ble) return window.__t2.ble.sendLine(line);
  try {
    const r = await fetch("/api/cmd", { method: "POST", body: line });
    if (!r.ok) throw new Error("HTTP " + r.status);
  } catch (e) { /* 断连由轮询侧呈现 (stale), 不弹窗 */ }
}

export async function postJSON(url, body) {
  try {
    const r = await fetch(url, { method: "POST", body: JSON.stringify(body) });
    return await r.json();
  } catch (e) { return null; }
}

// ?debug: fps/粒子/延迟浮层 (spec §6 性能预算观测; 读 __t2 + telemetry.latencyMs)
function initDebug() {
  if (!location.search.includes("debug")) return;
  const el = document.createElement("div");
  el.id = "t2_debug";
  el.style.cssText = "position:absolute;top:56px;left:16px;z-index:9;font:12px/1.6 ui-monospace,monospace;" +
    "color:#9fe08c;text-shadow:0 1px 2px #000;pointer-events:none;white-space:pre";
  $("t2_stage").appendChild(el);
  setInterval(() => {
    const sc = window.__t2 && window.__t2.scene;
    const fl = window.__t2 && window.__t2.flows;
    const airOn = fl ? fl.airs.filter((a) => a.op > 0.01).length : 0;
    el.textContent =
      "fps " + (sc ? sc.fps.toFixed(0) : "—") +
      "\nparts " + (sc ? sc.parts.length : 0) +
      "\nair " + airOn + "/" + (fl ? fl.airs.length : 8) +
      "\nlat " + latencyMs.toFixed(0) + " ms";
  }, 500);
}

function initChrome() {
  for (const id of ["t2_ctrlDrawer", "t2_tlmDrawer", "t2_hotspotCard"]) $(id).classList.add("t2_glass");
  $("t2_hotspotCard").classList.add("hidden");
  initPanels();                                       // 抽屉/运输条/热点卡/状态行 (panels.js)
  initSimLab();                                       // 仿真实验室浮层 (simlab.js)
  initBLE();                                          // Web Bluetooth 真机模式 (ble.js)
  initDebug();
  startTelemetry();                                   // 200ms 交替轮询双源 (telemetry.js)
  createSceneGate();
}

// 场景挂载 (Task3 语义保持): WebGL/装配失败 → 优雅降级卡, 其余抽屉仍可用 (spec §6)
function createSceneGate() {
  import("js/scene.js")
    .then(({ createScene }) => createScene($("t2_canvas"), onPartClick))
    .catch((e) => {
      const d = document.createElement("div");
      d.className = "t2_glass";
      d.style.cssText = "position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);padding:24px;z-index:8";
      d.textContent = "3D 场景不可用：" + e.message;
      $("t2_stage").appendChild(d);
    });
}
initChrome();
