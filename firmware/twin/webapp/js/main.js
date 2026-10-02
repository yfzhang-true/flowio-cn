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
