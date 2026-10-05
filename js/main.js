// firmware/twin/webapp/js/main.js — M4 组装根 (瘦身后 ~50 行)
// 职责只剩四件: ① import 组件树 (<twin-app> 在 index.html 声明, import 即升级)
// ② `cmd-line` CustomEvent → store.sendCmd 路由 (组件不直接依赖网络层)
// ③ BLE 真机模式接线 ④ 遥测管道启动 + ?debug 浮层。
// 数据层在 ./store.js; three 场景/流光/遥测内核 (scene/flows/telemetry) 不变。
import "./components/twin-app.js";
import { sendCmd } from "./store.js";
import { startTelemetry, latencyMs } from "./telemetry.js";
import { initBLE } from "./ble.js";
import * as dom from "./dom.js";

window.__t2 = window.__t2 || {};
window.__t2.dom = dom;                                // 深穿查询 (shadow DOM 调试/测试钩)
window.__t2.panels = { sendCmd };                     // T7 测试调试钩 (语义保持)

// 组件命令事件 → 命令通道 (control-drawer 发 `cmd-line` {line})
document.addEventListener("cmd-line", (ev) => sendCmd(ev.detail.line));

initBLE();                                            // Web Bluetooth 真机模式 (ble.js)
startTelemetry();                                     // 200ms 交替轮询双源 (telemetry.js)
initDebug();

// ?debug: fps/粒子/延迟浮层 (spec §6 性能预算观测; 读 __t2 + telemetry.latencyMs)
function initDebug() {
  if (!location.search.includes("debug")) return;
  const el = document.createElement("div");
  el.id = "t2_debug";
  el.style.cssText = "position:absolute;top:56px;left:16px;z-index:9;font:12px/1.6 ui-monospace,monospace;" +
    "color:#9fe08c;text-shadow:0 1px 2px #000;pointer-events:none;white-space:pre";
  const app = document.querySelector("twin-app");
  if (app && app.stage) app.stage.appendChild(el);
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
