// firmware/twin/webapp/js/store.js — 应用状态 + 命令通道 (M4: 自 main.js 抽出的数据层)
// 组件与内核 (telemetry/scene/flows/ble) 共用的单一状态源; 组件树不 import main.js,
// 依赖图无环: store.js 是叶子, main.js 是组装根。
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
