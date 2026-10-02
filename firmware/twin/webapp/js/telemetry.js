// firmware/twin/webapp/js/telemetry.js — 双源轮询管道 (Task5)
// 200ms 交替: /api/board/state?since= (电气遥测+增量历史) ↔ /api/state (阀 duty/压力/状态字)
// 结果 → setState (panels 消费) + flows.update (流光/粒子消费) 双管道。
// 停轮询: document.hidden / 孪生时间暂停 (store.paused) / BLE 真机接管 (store.bleActive);
// 连续失败 → setState({stale:true}) + 流光回底光 (spec §6 安静降级, 不弹窗)。
import { store, setState } from "/webapp/js/main.js";

const SPARK_N = 60;                 // sparkline 窗口 (≈24s @400ms/点)
const LONG_N = 600;                 // 展开小图窗口 (≈4min, 与服务端 600s 历史同量级)

// 两级缓冲: hist=服务端权威历史镜像 (since 增量, v5/v33/load); snap=快照环 (temp/eff 无服务端历史)
export const hist = { t: [], v5: [], v33: [], load: [] };
export const snap = { t: [], temp: [], eff: [] };

export let latencyMs = 0;           // 最近一次成功请求往返 (?debug 浮层消费)

let turn = 0;                       // 交替节拍: 偶=board / 奇=pnu
let histLast = -Infinity;           // since 增量游标 (v1.2 语义, 去重边界点)
let failN = 0;

const trim = (a) => { while (a.length > LONG_N) a.shift(); };

// 服务端历史增量入镜像 (与 v1.2 p1_pollBoard 同款游标逻辑)
function ingestHistory(tel) {
  const h = tel && tel.history;
  if (!h || !Array.isArray(h.t)) return;
  for (let i = 0; i < h.t.length; i++) {
    if (h.t[i] <= histLast) continue;
    histLast = h.t[i];
    hist.t.push(h.t[i]);
    hist.v5.push(h.v5[i]);
    hist.v33.push(h.v33[i]);
    hist.load.push(h.load[i]);
  }
  trim(hist.t); trim(hist.v5); trim(hist.v33); trim(hist.load);
}

// 快照通道入环: 温度取三结温最大 (最坏结温), 效率=%
function pushSnap(tel) {
  if (!tel || !tel.rail_5v) return;
  const tmp = tel.temp_est_c || {};
  snap.t.push(tel.uptime_s);
  snap.temp.push(Math.max(tmp.cpu || 0, tmp.buck || 0, tmp.mos || 0));
  snap.eff.push((tel.rail_3v3 || {}).buck_eff * 100);
  trim(snap.t); trim(snap.temp); trim(snap.eff);
}

// 通道表: sparkline/展开图取数统一入口 (src=hist|snap)
const CHAN = {
  v5: { src: hist, key: "v5" }, v33: { src: hist, key: "v33" }, load: { src: hist, key: "load" },
  temp: { src: snap, key: "temp" }, eff: { src: snap, key: "eff" },
};
export function series(id, n = SPARK_N) {          // 末 n 点值数组 (sparkline)
  const c = CHAN[id];
  return c ? c.src[c.key].slice(-n) : [];
}
export function seriesFull(id) {                    // {t,y} 完整窗口 (展开小图)
  const c = CHAN[id];
  return c ? { t: c.src.t.slice(), y: c.src[c.key].slice() } : { t: [], y: [] };
}

function flowsUpdate(d) {
  const f = window.__t2 && window.__t2.flows;
  if (f) f.update(d);
}

async function beat() {
  if (document.hidden || store.paused || store.bleActive) return;
  const t0 = performance.now();
  try {
    if (turn++ % 2 === 0) {                        // 电气遥测 (增量历史)
      const url = isFinite(histLast) ? "/api/board/state?since=" + (histLast + 0.001)
                                    : "/api/board/state";
      const tel = await (await fetch(url, { cache: "no-store" })).json();
      latencyMs = performance.now() - t0;
      failN = 0;
      ingestHistory(tel);
      pushSnap(tel);
      setState({ telemetry: tel, stale: false });
      flowsUpdate({ tel, pnu: store.pnu, connected: true });
    } else {                                       // 气动状态 (阀 duty/压力/状态字)
      const pnu = await (await fetch("/api/state", { cache: "no-store" })).json();
      latencyMs = performance.now() - t0;
      failN = 0;
      setState({ pnu, stale: false });
      flowsUpdate({ tel: store.telemetry, pnu, connected: true });
    }
  } catch (e) {
    if (++failN >= 2) {                            // 单次抖动不算 stale
      setState({ stale: true });
      flowsUpdate({ connected: false });
    }
  }
}

export function startTelemetry() {
  beat();
  setInterval(beat, 200);
}
