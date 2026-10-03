/* demo_api.js — FLOWIO-CN 静态演示站 API 层 (GitHub Pages 无后端版)
 * 拦截 /api/* fetch, 用浏览器内合成模型 + SimDemo 仿真引擎应答; 响应形状与 server.py [API v1.2] 同构.
 * 物理公式移植自 board_model.py (BOARD_PARAMS 常量同源), 遥测为演示级合成 (无真机).
 */
(function (global) {
  "use strict";
  const API_VER = "1.2";
  const realFetch = global.fetch.bind(global);

  // ───────────────────────── 板级常数 (board_model.py 同源)
  const LOGIC_A = 0.43;
  const BP = {
    r_coil: 14.0, rds: 0.040, vbus: 5.0, vf_ss34: 0.31, r_ss34: 0.05,
    vout3v3: 3.269, load_reg: 0.012, i_pump: 0.35,
    theta: { cpu: 35.0, buck: 130.0, mos: 350.0 },
  };
  const I_VALVE = 5.0 / BP.r_coil;          // ≈0.356A 稳态阀电流
  const TAU_TH = 30.0, TICK = 0.1, HIST_N = 6000;
  const CL_NAMES = { 0: "IDLE", 1: "RUNNING", 2: "DONE", 3: "TIMEOUT", 4: "ERR" };

  // ───────────────────────── 合成状态
  const S = {
    duties: new Array(8).fill(0), pump: 0,
    i: new Array(8).fill(0),
    t: 0, acc: 0, paused: false, speed: 1.0,
    state: 0, clT: 0,                      // clT: RUNNING 计时
    ports: new Array(5).fill(0),           // kPa
    sensors: [0, 0], sensorSet: null,      // sensorSet: 手动覆盖值
    temp: { cpu: 25.0, buck: 25.0, mos: 25.0 },
    hist: [],                              // {t,v5,v33,load,vi[]}
  };

  function step(dt) {
    S.t += dt;
    for (let k = 0; k < 8; k++) {
      const target = S.duties[k] > 0 ? I_VALVE * (S.duties[k] / 255) : 0;
      S.i[k] += (target - S.i[k]) * (1 - Math.exp(-dt / 1.78e-3));
    }
    for (let k = 0; k < 5; k++) {
      const drive = k < 4 ? (S.duties[k] / 255) : (S.pump ? 1 : 0);
      const target = 45 * drive;
      S.ports[k] += (target - S.ports[k]) * (1 - Math.exp(-dt / 0.4));
    }
    // 状态机: 命令 → RUNNING → 2s 后 DONE
    if (S.state === 1) { S.clT += dt; if (S.clT > 2.0) S.state = 2; }
    // 热一阶惯性 (目标 = 环境 + P·θ)
    const load5 = S.i.reduce((a, b) => a + b, 0) + BP.i_pump * S.pump + LOGIC_A;
    const v5 = BP.vbus - (BP.vf_ss34 + BP.r_ss34 * load5);
    const p_cpu = LOGIC_A * BP.vout3v3, p_buck = (BP.vout3v3 * LOGIC_A) * (1 / 0.876 - 1);
    const p_mos = S.i.reduce((a, x) => a + x * x * (BP.r_coil + BP.rds), 0);
    for (const [k, P] of [["cpu", p_cpu], ["buck", p_buck], ["mos", p_mos]]) {
      const tgt = 25.0 + P * BP.theta[k];
      S.temp[k] += (tgt - S.temp[k]) * (1 - Math.exp(-dt / TAU_TH));
    }
    // 历史节流 (0.1s 一条, 环形)
    S.acc += dt;
    while (S.acc >= TICK) {
      S.acc -= TICK;
      const v33 = BP.vout3v3 - BP.load_reg * LOGIC_A;
      S.hist.push({ t: Math.round((S.t - S.acc) * 1e6) / 1e6, v5, v33, load: load5, vi: S.i.slice() });
      if (S.hist.length > HIST_N) S.hist.shift();
    }
  }
  // 预热 60s 空闲历史, 图表一打开就有数据
  for (let k = 0; k < 600; k++) step(0.1);

  setInterval(() => {
    if (S.paused) return;
    step(0.05 * S.speed);
  }, 50);

  function command(cmd) {
    cmd = (cmd || "").trim();
    if (!cmd) return;
    let m;
    if ((m = cmd.match(/^V\s*([1-8])\s+(\d+)/i))) {          // V3 80
      S.duties[+m[1] - 1] = Math.min(255, +m[2]);
    } else if ((m = cmd.match(/^P(?:UMP)?\s+([01])/i))) {    // PUMP 1
      S.pump = +m[1];
    } else if ((m = cmd.match(/^P(?:UMP)?\s+OFF/i))) {
      S.pump = 0;
    } else if ((m = cmd.match(/^S\s*([12])\s+([\d.]+)/i))) { // S1 25.0 传感器注入
      S.sensorSet = [+m[1] - 1, +m[2]];
    }
    S.state = 1; S.clT = 0;                                   // 任何命令 → RUNNING
  }

  function telemetry(since) {
    const i = S.i.slice();
    const load5 = i.reduce((a, b) => a + b, 0) + BP.i_pump * S.pump + LOGIC_A;
    const v5 = BP.vbus - (BP.vf_ss34 + BP.r_ss34 * load5);
    const v33 = BP.vout3v3 - BP.load_reg * LOGIC_A;
    const d = BP.vout3v3 / v5;
    const p_sw = LOGIC_A * LOGIC_A * 0.12 * d;
    const p_dcr = LOGIC_A * LOGIC_A * 0.018;
    const p_diode = 0.42 * LOGIC_A * (1.0 - d);
    const p_swp = 0.5 * 5.0 * LOGIC_A * 20e-9 * 570e3;
    const p_out = BP.vout3v3 * LOGIC_A;
    const buck_eff = p_out / (p_out + p_sw + p_dcr + p_diode + p_swp);
    const r_loop = BP.r_coil + BP.rds;
    const valves = i.map((x) => ({ on: x > 0.01, i_A: +x.toFixed(3), p_w: +(x * x * r_loop).toFixed(2) }));
    let hist = S.hist;
    if (since != null && isFinite(since)) {
      let i0 = hist.length;
      for (let k = 0; k < hist.length; k++) if (hist[k].t >= since) { i0 = k; break; }
      hist = hist.slice(i0);
    }
    const history = { t: [], v5: [], v33: [], load: [], vi: [] };
    for (const rec of hist) for (const key of Object.keys(history)) history[key].push(rec[key]);
    return {
      tick: Math.trunc(S.t / TICK), uptime_s: +S.t.toFixed(3), stale: false, valves,
      rail_5v: { v: +v5.toFixed(4), load_a: +load5.toFixed(4), p_w: +(v5 * load5).toFixed(3) },
      rail_3v3: {
        v: +v33.toFixed(4), v_nom: BP.vout3v3, load_a: LOGIC_A, ripple_mv: 1.0,
        buck_eff: +buck_eff.toFixed(4),
        loss_mw: { sw: Math.round(p_sw * 1e3), dcr: Math.round(p_dcr * 1e3), diode: Math.round(p_diode * 1e3), switching: Math.round(p_swp * 1e3) },
      },
      board_p_w: +(v5 * load5).toFixed(3),
      temp_est_c: { cpu: +S.temp.cpu.toFixed(2), buck: +S.temp.buck.toFixed(2), mos: +S.temp.mos.toFixed(2) },
      history,
    };
  }

  function pneuState() {
    const sens = S.sensorSet
      ? S.ports.map((p, k) => (k === S.sensorSet[0] ? S.sensorSet[1] : p)).slice(0, 2)
      : S.ports.slice(0, 2);
    return {
      state: S.state, valves: S.duties.slice(0, 7), pump: S.pump,
      sensors: sens.map((x) => +x.toFixed(2)), ports_p: S.ports.map((x) => +x.toFixed(2)),
      cl: CL_NAMES[S.state] || "?", err: 0, leaks: new Array(7).fill(0),
    };
  }

  function reset() {
    S.duties.fill(0); S.pump = 0; S.i.fill(0); S.state = 0; S.clT = 0;
    S.ports.fill(0); S.sensorSet = null; S.hist = []; S.t = 0; S.acc = 0;
    S.temp = { cpu: 25.0, buck: 25.0, mos: 25.0 };
    for (let k = 0; k < 600; k++) step(0.1);
  }

  // ───────────────────────── fetch 拦截
  const J = (obj) => new Response(JSON.stringify(obj), { status: 200, headers: { "Content-Type": "application/json; charset=utf-8" } });
  const E400 = (msg) => new Response(JSON.stringify({ error: msg }), { status: 400, headers: { "Content-Type": "application/json" } });

  global.fetch = async function (input, init) {
    const url = typeof input === "string" ? input : (input && input.url) || "";
    const path = url.split("?")[0];
    const body = init && init.body;

    try {
      if (path === "/api/board/assembly") {
        const d = await (await realFetch("data/assembly.json", { cache: "no-store" })).json();
        d.api = API_VER;
        return J(d);
      }
      if (path === "/api/board/sim/presets") {
        return J({ api: API_VER, presets: global.SimDemo.presets() });
      }
      if (path === "/api/board/state") {
        const qs = url.split("?")[1] || "";
        let since = null;
        for (const kv of qs.split("&")) if (kv.startsWith("since=")) since = parseFloat(kv.slice(6));
        const tel = telemetry(since);
        tel.api = API_VER;
        return J(tel);
      }
      if (path === "/api/state") return J(pneuState());
      if (path === "/api/board/history/export") {
        const h = telemetry().history;
        const lines = ["t_s,rail5v_v,rail3v3_v,load_a"];
        for (let k = 0; k < h.t.length; k++) lines.push(h.t[k].toFixed(2) + "," + h.v5[k].toFixed(3) + "," + h.v33[k].toFixed(3) + "," + h.load[k].toFixed(3));
        return new Response(lines.join("\n"), { status: 200, headers: { "Content-Type": "text/csv" } });
      }
      if (path === "/api/board/sim" && init && init.method === "POST") {
        let req = {};
        try { req = body ? JSON.parse(body) : {}; } catch (e) { /* 忽略, 同 server */ }
        try {
          const r = global.SimDemo.run(req.circuit, req.params);
          r.api = API_VER;
          return J(r);
        } catch (e) {
          if (e instanceof global.SimDemo.ParamError) return E400(e.message);
          throw e;
        }
      }
      if (path === "/api/cmd" && init && init.method === "POST") {
        command(body);
        return J({ ok: true });
      }
      if (path === "/api/reset" && init && init.method === "POST") { reset(); return J({ ok: true }); }
      if (path === "/api/sim" && init && init.method === "POST") {
        const parts = String(body || "").trim().split(/\s+/);
        if (parts.length === 2 && isFinite(+parts[0]) && isFinite(+parts[1])) {
          S.sensorSet = [Math.min(1, Math.max(0, +parts[0])), +parts[1]];
          return J({ ok: true });
        }
        return J({ ok: false });
      }
      if (path === "/api/time" && init && init.method === "POST") {
        let req = {};
        try { req = body ? JSON.parse(body) : {}; } catch (e) { /* 同 server 容错 */ }
        if ("paused" in req) S.paused = !!req.paused;
        if ("speed" in req && isFinite(+req.speed)) S.speed = Math.min(4.0, Math.max(0.25, +req.speed));
        return J({ api: API_VER, paused: S.paused, speed: S.speed, step_once: false });
      }
      if (path === "/api/record" && init && init.method === "POST") {
        let req = {};
        try { req = body ? JSON.parse(body) : {}; } catch (e) { /* 同 server 容错 */ }
        // 录制事件已由前端 main.js 本地缓存; 这里仅回状态
        return J({ api: API_VER, recording: req.action === "start", n: 0 });
      }
      if (path === "/api/record/replay" && init && init.method === "POST") {
        let req = {};
        try { req = body ? JSON.parse(body) : {}; } catch (e) { /* 同 server 容错 */ }
        const evs = (req.events || []).filter((e) => e && typeof e.cmd === "string");
        let t0 = null;
        for (const ev of evs) {
          const t = isFinite(ev.t) ? ev.t : 0;
          const delay = t0 === null ? 0 : Math.min(Math.max(t - t0, 0) * 1000, 500);
          setTimeout(() => command(ev.cmd), delay);
          t0 = t;
        }
        return J({ api: API_VER, replaying: evs.length });
      }
    } catch (e) {
      return new Response(JSON.stringify({ error: String(e) }), { status: 500, headers: { "Content-Type": "application/json" } });
    }
    return realFetch(input, init);
  };

  // 无 Web Bluetooth 的环境 (Pages 演示): 标注供 CSS/JS 识别
  if (!global.navigator.bluetooth) document.documentElement.classList.add("no-ble");
  global.DemoAPI = { telemetry, pneuState, command, reset };
})(window);
