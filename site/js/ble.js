// firmware/twin/webapp/js/ble.js — Web Bluetooth 真机模式 (Task6, 自旧 gui.html 移植)
// 契约 = BLE.md: UUID 基址 f10a5c00-…-1b0fXXXX; 广播名 FLOWIO-P1-*;
// cmd 写 0xA5 帧 [A5 cmd ports pwm crc8] (CRC-8 poly 0x07 init 0x00, 同 pn_core/proto.c),
// 不可帧化的 CLI (H/F/L/G…) 走 ASCII 行 (pn_cmd_feed 双编码兼容);
// state notify 20B LE → 与 /api/state 同构的 pnu 对象 → 同一 store/flows 管道 (p1_renderState 语义)。
// 真机接管时停 HTTP 轮询 (telemetry.beat 检查 store.bleActive); 断连安静降级: 徽章灰、流光回底光。
import { store, setState } from "./main.js";

const $ = (id) => document.getElementById(id);
const UUID = (suf) => "f10a5c00-0000-4b1e-9c2d-8e3a1b0f" + suf;

let ble = { device: null, chCmd: null, chResp: null, chState: null, active: false };
let lastRespLine = "";               // resp 特征最近一行 (调试钩)

/* ── 0xA5 帧编码 (BLE.md §4.1) ── */
function crc8(bytes) {               // MSB-first, 与 pn_core/proto.c 同实现
  let crc = 0;
  for (let i = 0; i < bytes.length; ++i) {
    crc ^= bytes[i];
    for (let b = 0; b < 8; ++b)
      crc = (crc & 0x80) ? ((crc << 1) ^ 0x07) & 0xFF : (crc << 1) & 0xFF;
  }
  return crc;
}
function buildFrame(cmd, ports, pwm) {
  const f = new Uint8Array([0xA5, cmd.charCodeAt(0) & 0xFF, ports & 0xFF, pwm & 0xFF, 0]);
  f[4] = crc8(f.subarray(0, 4));
  return f;
}
// CLI 行 → 0xA5 帧 (§3.2 翻译表逆映射); H 无帧码 → null → ASCII 行直发
function frameForLine(line) {
  const s = String(line).trim();
  const m = /^([IVRSOC])\s+(\d+)(?:\s+(\d+))?$/.exec(s);
  if (m) {
    const cmd = { I: "+", V: "-", R: "^", S: "!", O: "o", C: "c" }[m[1]];
    const needsPwm = m[1] === "I" || m[1] === "V";
    if (!cmd || (needsPwm && m[3] === undefined)) return null;
    return buildFrame(cmd, +m[2] & 0xFF, needsPwm ? (+m[3] & 0xFF) : 0);
  }
  if (s === "T") return buildFrame("S", 0, 0);
  if (s === "X") return buildFrame("R", 0, 0);
  if (s === "P") return buildFrame("?", 0, 0);
  return null;
}

/* ── 20B state 帧解析 (BLE.md §4.2, 校验同 ble_frame.c) ──
   入参 DataView (真机 notify) / ArrayBuffer / TypedArray 均可 */
export function parseState20(buf) {
  const dv = buf instanceof DataView ? buf
    : new DataView(buf instanceof ArrayBuffer ? buf : (buf && buf.buffer) || buf);
  if (dv.byteLength < 20) return null;
  for (let i = 14; i < 20; ++i)
    if (dv.getUint8(i) !== 0) return null;          // 保留字节必须全 0
  const state = dv.getUint16(0, true);
  const pressures = [];
  for (let i = 0; i < 5; ++i) {
    const raw = dv.getInt16(2 + i * 2, true);
    pressures.push(raw === -32768 ? 0 : raw / 10);  // 0x8000=无效 → 0
  }
  return { state, pressures, tick: dv.getUint16(12, true) };
}

// BLE 位 → 与 /api/state 同构的 pnu; 并合成最小 tel (阀电流实值驱动栅极辉光, 轨压留空显 "—")
function bleToStore(f) {
  const valves = [];
  for (let i = 0; i < 7; ++i) valves.push((f.state >> i) & 1 ? 255 : 0);
  const pnu = {
    state: f.state, valves,
    pump: (f.state & 0x80) ? 255 : 0,
    sensors: [f.pressures[0], f.pressures[1]],
    ports_p: f.pressures,
    cl: "BLE",
    err: (f.state & 0x8000) ? 1 : 0,
  };
  const v8 = valves.concat([0]).slice(0, 8);
  const tel = { valves: v8.map((d) => ({ on: d > 0, i_A: d > 0 ? 0.36 : 0, p_w: d > 0 ? 1.51 : 0 })) };
  return { pnu, tel };
}

function onStateNotify(ev) {
  const f = parseState20(ev.target.value);
  if (!f) return;                                   // 校验失败静默丢帧
  const { pnu, tel } = bleToStore(f);
  setState({ pnu, telemetry: tel, stale: false });
  const fl = window.__t2 && window.__t2.flows;
  if (fl) fl.update({ tel, pnu, connected: true });
}

/* ── 连接管理 (自 gui.html p1_bleConnect 移植) ── */
async function connect() {
  if (!navigator.bluetooth || ble.active) return;
  try {
    const device = await navigator.bluetooth.requestDevice({
      filters: [{ namePrefix: "FLOWIO-P1" }],
      optionalServices: [UUID("0001"), UUID("0004"), UUID("0007")],
    });
    ble.device = device;
    device.addEventListener("gattserverdisconnected", onDisconnect);
    const server = await device.gatt.connect();
    const [svcCmd, svcTel] = await Promise.all([
      server.getPrimaryService(UUID("0001")),
      server.getPrimaryService(UUID("0004")),
    ]);
    ble.chCmd = await svcCmd.getCharacteristic(UUID("0002"));
    ble.chResp = await svcCmd.getCharacteristic(UUID("0003"));
    ble.chState = await svcTel.getCharacteristic(UUID("0005"));
    const chEn = await svcTel.getCharacteristic(UUID("0006"));
    await chEn.writeValue(new Uint8Array([1]));    // 应用级遥测开关
    await ble.chState.startNotifications();
    ble.chState.addEventListener("characteristicvaluechanged", onStateNotify);
    await ble.chResp.startNotifications();
    ble.chResp.addEventListener("characteristicvaluechanged", (ev) => {
      lastRespLine = new TextDecoder().decode(ev.target.value);
    });
    ble.active = true;
    setState({ bleActive: true, mode: "real", stale: false });   // 停 HTTP 轮询
    updateBadge();
  } catch (e) {
    if (!e || e.name !== "NotFoundError") console.warn("BLE 连接失败:", e && e.message || e);
    cleanup();                                      // 取消扫描/失败 → 安静回落孪生
  }
}
function disconnect() {
  if (ble.device && ble.device.gatt && ble.device.gatt.connected)
    ble.device.gatt.disconnect();                   // → gattserverdisconnected → cleanup
  else cleanup();
}
function onDisconnect() { cleanup(); }              // 断连安静降级: 徽章灰、流光回底光
function cleanup() {
  ble = { device: null, chCmd: null, chResp: null, chState: null, active: false };
  setState({ bleActive: false, mode: "twin" });    // HTTP 轮询自动恢复
  updateBadge();
}

// 命令通道 (main.sendCmd 真机分支): 优先 0xA5 帧, 不可帧化走 ASCII 行
async function sendLine(line) {
  if (!ble.active || !ble.chCmd) return null;
  const frame = frameForLine(line);
  try {
    await ble.chCmd.writeValue(frame || new TextEncoder().encode(line + "\n"));
    return frame ? "frame" : "ascii";
  } catch (e) {
    console.warn("BLE 写失败 [" + line + "]", e.message || e);
    return null;
  }
}

function updateBadge() {
  const on = ble.active;
  const badge = $("t2_modeBadge"), btn = $("t2_bleBtn");
  if (!badge || !btn) return;
  badge.textContent = on ? "真机 BLE" : "孪生";
  badge.classList.toggle("live", on);
  btn.textContent = on ? "断开真机" : "连接真机";
}

export function initBLE() {
  const btn = $("t2_bleBtn");
  if (!navigator.bluetooth) {
    btn.disabled = true;
    btn.title = "此环境不支持 Web Bluetooth（需 Chrome/Edge 蓝牙 + localhost/HTTPS）";
    return;
  }
  btn.onclick = () => (ble.active ? disconnect() : connect());
  window.__t2 = window.__t2 || {};
  window.__t2.ble = {                                 // T7 测试调试钩 + main.sendCmd 真机分支
    sendLine, connect, disconnect,
    frameForLine, parseState20, buildFrame, crc8,
    get active() { return ble.active; },
    get lastResp() { return lastRespLine; },
  };
}
