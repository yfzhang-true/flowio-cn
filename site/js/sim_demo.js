/* sim_demo.js — FLOWIO-CN S1 参数化仿真引擎 (浏览器移植版)
 * 源: firmware/twin/sim_engine.py (356 行, 纯数学) — 逐函数 1:1 移植, 数值锚点见原文件头注释.
 * 输出结构与 Python 版同构: {circuit, params, metrics, waves, notes} + api:"1.2" (由 demo_api 注入).
 * 一致性: site/js/sim_test_data.json 存 Python 版默认工况输出, 页面加载时 console.assert 对拍.
 */
(function (global) {
  "use strict";

  class ParamError extends Error {}

  // ------------------------------------------------ 参数域表 (参数名, 下限, 上限, 默认值)
  const SPEC = {
    buck: [
      ["vin", 3.8, 5.5, 5.0],
      ["iload", 0.1, 3.0, 3.0],
      ["l_uh", 4.7, 10.0, 6.8],
      ["cout_uf", 47, 220, 113.0],
      ["esr_mohm", 10, 100, 45.0],
      ["fsw_khz", 300, 1000, 570.0],
    ],
    dior: [
      ["vdc", 4.4, 5.5, 5.0],
      ["vusb", 4.4, 5.5, 5.1],
      ["iload", 0.05, 0.5, 0.5],
    ],
    valve: [
      ["pwm_hz", 1, 50, 10.0],
      ["duty", 0.05, 0.95, 0.5],
      ["r_coil", 8, 30, 14.0],
      ["l_mh", 5, 60, 25.0],
      ["rg", 47, 330, 100.0],
    ],
    i2c: [
      ["rp_k", 1.0, 10.0, 4.7],
      ["cbus_pf", 30, 300, 115.0],
    ],
  };

  function isNum(v) {
    return typeof v === "number" && isFinite(v);
  }

  function _check(circuit, params) {
    if (!Object.prototype.hasOwnProperty.call(SPEC, circuit)) {
      throw new ParamError("未知电路 " + circuit + ", 可选: " + Object.keys(SPEC).sort().join("/"));
    }
    params = params || {};
    if (typeof params !== "object" || Array.isArray(params)) {
      throw new ParamError("params 必须为对象 {参数名: 数值}");
    }
    const table = {};
    for (const s of SPEC[circuit]) table[s[0]] = s;
    for (const k of Object.keys(params)) {
      if (!table[k]) throw new ParamError("电路 " + circuit + " 不存在参数 " + k);
      const v = params[k];
      if (typeof v === "boolean" || !isNum(v)) throw new ParamError("参数 " + k + "=" + v + " 必须为数值");
      const [, lo, hi] = table[k];
      if (!(lo <= v && v <= hi)) throw new ParamError("参数 " + k + "=" + v + " 超出允许范围 [" + lo + ", " + hi + "]");
    }
    const merged = {};
    for (const [name, , , dflt] of SPEC[circuit]) merged[name] = dflt;
    for (const k of Object.keys(params)) merged[k] = params[k];
    return merged;
  }

  // ------------------------------------------------ 公共小工具
  const R6 = (x) => Math.round(x * 1e6) / 1e6;

  function _dec(t, y, n) {
    n = n || 1500;
    const m = t.length;
    let idx;
    if (m <= n) {
      idx = Array.from({ length: m }, (_, j) => j);
    } else {
      const step = (m - 1) / (n - 1);
      idx = [];
      let last = -1;
      for (let k = 0; k < n; k++) {
        const j = Math.min(m - 1, Math.round(k * step));
        if (j !== last) { idx.push(j); last = j; }
      }
    }
    const nd = Math.abs(t[t.length - 1]) >= 1e-3 ? 6 : 9;
    const rd = (x) => Math.round(x * Math.pow(10, nd)) / Math.pow(10, nd);
    return [idx.map((j) => rd(t[j])), idx.map((j) => R6(y[j]))];
  }

  function _wave(name, t, y, unit, n) {
    const [tt, yy] = _dec(t, y, n);
    return { name, t: tt, y: yy, unit };
  }

  function _metric(name, value, unit, verdict) {
    return { name, value: Math.round(value * 1e9) / 1e9, unit, verdict };
  }

  function _diode_i(v, Is, n, vt) {
    Is = Is || 1e-7; n = n || 1.2; vt = vt || 0.02585;
    const x = v / (n * vt);
    if (x > 40) return Is * Math.exp(40.0) * (1.0 + (x - 40.0));
    return Is * (Math.exp(Math.min(Math.max(x, 0.0), 40.0)) - 1.0);
  }

  // ------------------------------------------------ 1) buck
  function _buck(p) {
    const vin = p.vin, iload = p.iload;
    const L = p.l_uh * 1e-6, COUT = p.cout_uf * 1e-6, ESR = p.esr_mohm * 1e-3, FSW = p.fsw_khz * 1e3;

    const VREF = 0.8, RDIV = 1.0 + 10e3 / 3.24e3;
    const VOUT_T = VREF * RDIV;
    const TSW = 1.0 / FSW;
    const RSW = 0.12, DCR = 0.018, VF = 0.42, RD = 0.035;
    const KP = 0.3, KI = 2500.0;
    const D0 = VOUT_T / vin;
    const dt = 1.0 / (FSW * 140);
    const total = 2.5e-3, ss = 0.5e-3;

    const n = Math.trunc(total / dt);
    let t = 0, iL = 0, vC = 0, integ = 0;
    const T = [0], IL = [0], VO = [0];
    for (let k = 0; k < n; k++) {
      t += dt;
      const vref_eff = Math.min(1.0, t / ss) * VOUT_T;
      const vout = vC + ESR * (iL - iload);
      const err = vref_eff - vout;
      integ = Math.min(1e-3, Math.max(-1e-3, integ + err * dt));
      const d = Math.min(0.92, Math.max(0.05, D0 + KP * err + KI * integ));
      const on = ((k * dt) % TSW) < d * TSW;
      const vsw = on ? (vin - iL * RSW) : (-VF - iL * RD);
      iL += (vsw - vout - iL * DCR) / L * dt;
      if (iL < 0 && !on) iL = 0.0;
      vC += (iL - iload) / COUT * dt;
      T.push(t); IL.push(iL); VO.push(vC);
    }

    const vo_w = [], il_w = [];
    for (let j = 0; j < T.length; j++) if (T[j] > 2.2e-3) { vo_w.push(VO[j]); il_w.push(IL[j]); }
    let v_avg = 0; for (const v of vo_w) v_avg += v; v_avg /= vo_w.length;
    const ripple_mV = (Math.max(...vo_w) - Math.min(...vo_w)) * 1000.0;
    const ilpp = Math.max(...il_w) - Math.min(...il_w);
    const ilpk = Math.max(...il_w);

    const D = VOUT_T / vin;
    const P_rsw = iload * iload * RSW * D;
    const P_dcr = iload * iload * DCR;
    const P_d = VF * iload * (1.0 - D);
    const P_sw = 0.5 * vin * iload * 20e-9 * FSW;
    const P_esr = (ilpp * ilpp / 12.0) * ESR;
    const eff = (VOUT_T * iload) / (VOUT_T * iload + P_rsw + P_dcr + P_d + P_sw + P_esr);

    const metrics = [
      _metric("输出电压", v_avg, "V",
        Math.abs(v_avg - 3.3) <= 0.033 ? "✓ 3.3V±1% 设计目标" : "⚠ 偏离 3.3V±1% 设计窗口"),
      _metric("稳态纹波", ripple_mV, "mVpp",
        ripple_mV < 50 ? "✓ <50mV 预算" : "⚠ 超 50mV 预算 (ESR 主导)"),
      _metric("电感电流纹波", ilpp, "App",
        ilpk < 3.9 ? "✓ 峰值 " + ilpk.toFixed(2) + "A < 3.9A (3A+30% 裕量)" : "⚠ 峰值 " + ilpk.toFixed(2) + "A 超 3.9A 裕量"),
      _metric("满载效率", eff, "", eff > 0.8 ? "✓ >80%" : "⚠ ≤80%, 见损耗分解"),
    ];
    const waves = [_wave("Vout", T, VO, "V"), _wave("iL", T, IL, "A")];
    const notes = [
      "VOUT_T=0.8×(1+10k/3.24k)=" + VOUT_T.toFixed(3) + "V; 闭环 KP=0.3 KI=2500, 软启动 " + (ss * 1e3).toFixed(1) + "ms, dt=TSW/140=" + (dt * 1e9).toFixed(1) + "ns",
      "损耗分解: 开关管 " + (P_rsw * 1e3).toFixed(0) + "mW + DCR " + (P_dcr * 1e3).toFixed(0) + "mW + 二极管 " + (P_d * 1e3).toFixed(0) + "mW + 开关(20ns) " + (P_sw * 1e3).toFixed(0) + "mW + ESR " + (P_esr * 1e3).toFixed(1) + "mW",
      "稳态窗口 T>2.2ms (" + vo_w.length + " 点), 含软启动波形",
    ];
    return { metrics, waves, notes };
  }

  // ------------------------------------------------ 2) dior
  function _dior(p) {
    const vdc = p.vdc, vusb = p.vusb, iload = p.iload;
    const RL = 5.0 / iload;

    let vo = 4.5;
    for (let k = 0; k < 200; k++) {
      const i1 = _diode_i(vdc - vo), i2 = _diode_i(vusb - vo);
      vo += 0.05 * ((i1 + i2) - vo / RL);
    }
    const i1 = _diode_i(vdc - vo), i2 = _diode_i(vusb - vo);

    const vds = [], dc_mA = [], usb_mA = [];
    for (let k = 0; k < 60; k++) vds.push(4.4 + (5.5 - 4.4) * k / 59.0);
    for (const v of vds) {
      let vo2 = 4.4;
      const vcap = Math.max(v, vusb);
      for (let k = 0; k < 150; k++) {
        const a = _diode_i(v - vo2), b = _diode_i(vusb - vo2);
        vo2 = Math.min(vo2 + 0.05 * ((a + b) - vo2 / RL), vcap);
      }
      dc_mA.push(_diode_i(v - vo2) * 1000.0);
      usb_mA.push(_diode_i(vusb - vo2) * 1000.0);
    }
    let j = 0, best = Infinity;
    for (let k = 0; k < 60; k++) { const d = Math.abs(vds[k] - 5.0); if (d < best) { best = d; j = k; } }
    const reverse_mA = usb_mA[j];

    const metrics = [
      _metric("轨电压", vo, "V", 4.3 < vo && vo < 5.0 ? "✓ 5V-单二极管压降(~0.3V)" : "⚠ 轨电压异常"),
      _metric("DC侧电流", i1, "A", "✓ SS34 正向导通"),
      _metric("USB侧电流", i2, "A", i2 < iload ? "✓ 双源分流" : "⚠ USB 超供"),
      _metric("USB分流@DC5V", reverse_mA / 1000.0, "A",
        reverse_mA < 500 ? "✓ 两管分流, 无反偏倒灌路径" : "⚠ 分流异常"),
    ];
    const waves = [_wave("DC侧电流", vds, dc_mA, "mA"), _wave("USB侧电流", vds, usb_mA, "mA")];
    const notes = [
      "SS34 指数模型 Is=1e-7 n=1.2; 工作点: vdc=" + vdc.toFixed(1) + "V vusb=" + vusb.toFixed(1) + "V 负载 " + iload.toFixed(2) + "A (RL=" + RL.toFixed(1) + "Ω)",
      "扫描 x 轴为 V_DC (4.4→5.5V, 60 点); USB 倒灌取 V_DC≈5.0V 处",
    ];
    return { metrics, waves, notes };
  }

  // ------------------------------------------------ 3) valve
  function _valve(p) {
    const f_pwm = p.pwm_hz, duty = p.duty, R_COIL = p.r_coil, L = p.l_mh * 1e-3, RG = p.rg;
    const RDS = 0.040, CISS = 1.0e-9, VF_FW = 0.35;

    const T_per = 1.0 / f_pwm;
    const dt = 2e-5;
    const n = Math.trunc(3.0 * T_per / dt);
    const tau_g = RG * CISS;
    let i = 0, vg = 0;
    const T = [0], I = [0], VG = [0];
    for (let k = 0; k < n; k++) {
      const t = k * dt;
      const pwm = ((t * f_pwm) % 1.0) < duty;
      vg = pwm ? 3.3 + (vg - 3.3) * Math.exp(-dt / tau_g) : vg * Math.exp(-dt / tau_g);
      const on = vg > 1.2;
      const vcoil = on ? (5.0 - i * RDS) : -VF_FW;
      const i_new = i + (vcoil - i * R_COIL) / L * dt;
      i = i_new > 0 ? i_new : 0.0;
      T.push(t); I.push(i); VG.push(vg);
    }

    let peak = 0;
    for (let j = 0; j < T.length; j++) if (T[j] > 2.0 * T_per) peak = Math.max(peak, I[j]);
    const tau = L / R_COIL;
    const P_coil = 0.5 * peak * peak * R_COIL * duty;
    const P_mos = 0.5 * peak * peak * RDS * duty;
    const P_fw = VF_FW * peak * duty * (2.0 * tau / T_per);

    const metrics = [
      _metric("稳态阀电流", peak, "A", peak < 0.45 ? "✓ 阀额定 0.35A" : "⚠ 超 0.45A, 检查线圈/占空比"),
      _metric("电流时间常数", tau * 1e3, "ms", tau < 10e-3 ? "✓ <10ms, 不拖阀机械响应后腿" : "⚠ ≥10ms"),
      _metric("MOS导通损耗", P_mos * 1e3, "mW", "✓ SOT-23 无需散热"),
      _metric("续流二极管损耗", P_fw * 1e3, "mW", P_fw < 0.2 ? "✓ SS14 0.5A 额定" : "⚠ 续流损耗偏大"),
    ];
    const T2 = [], I2 = [], VG2 = [];
    for (let j = 0; j < T.length; j++) if (T[j] > T_per) { T2.push(T[j]); I2.push(I[j]); VG2.push(VG[j]); }
    const waves = [_wave("阀电流", T2, I2, "A"), _wave("Vgs", T2, VG2, "V")];
    const notes = [
      "PWM " + f_pwm.toFixed(0) + "Hz/" + (duty * 100).toFixed(0) + "%; τ=L/R=" + (tau * 1e3).toFixed(1) + "ms; 关断由 SS14 钳位至 -0.35V, 无高压尖峰",
      "稳态线圈功耗 " + (P_coil * 1e3).toFixed(0) + "mW; 8 路全开总线电流约 " + (peak * 8).toFixed(1) + "A (5V/3A 输入下禁全开)",
    ];
    return { metrics, waves, notes };
  }

  // ------------------------------------------------ 4) i2c
  function _i2c(p) {
    const RP = p.rp_k * 1e3, CBUS = p.cbus_pf * 1e-12;
    const tau = RP * CBUS;
    const tr = 2.2 * tau;

    const npts = 400;
    const t_end = 8.0 * tau;
    const T = [], V = [];
    for (let k = 0; k < npts; k++) {
      const tv = t_end * k / (npts - 1.0);
      T.push(tv);
      V.push(3.3 * (1.0 - Math.exp(-tv / tau)));
    }

    const metrics = [
      _metric("上升时间", tr, "s",
        tr < 0.6e-6 ? "✓ ≤0.6µs, 400kHz 快速模式可用" : "⚠ 超 0.6µs → 降 100kHz 或上拉减弱(改 2.2k)"),
      _metric("RC时间常数", tau, "s", tr < 1e-6 ? "✓ 100kHz 预算 1µs 内" : "⚠ 超 100kHz 预算"),
    ];
    const waves = [_wave("SDA/SCL", T, V, "V", npts)];
    const notes = [
      "τ=Rp×Cbus=" + (tau * 1e6).toFixed(2) + "µs; tr=2.2τ=" + (tr * 1e6).toFixed(2) + "µs; 波形为释放后 8τ (" + (t_end * 1e6).toFixed(1) + "µs)",
      "高电平噪声裕量: 3.3V 摆幅, VIH=0.7×3.3=2.31V",
    ];
    return { metrics, waves, notes };
  }

  const IMPL = { buck: _buck, dior: _dior, valve: _valve, i2c: _i2c };

  function presets() {
    const out = {};
    for (const circuit of Object.keys(SPEC)) {
      const def = {}, bounds = {};
      for (const [name, lo, hi, dflt] of SPEC[circuit]) { def[name] = dflt; bounds[name] = [lo, hi]; }
      out[circuit] = { default: def, bounds };
    }
    return out;
  }

  function run(circuit, params) {
    const p = _check(circuit, params);
    const r = IMPL[circuit](p);
    return { circuit, params: p, metrics: r.metrics, waves: r.waves, notes: r.notes };
  }

  global.SimDemo = { run, presets, SPEC, ParamError };
})(window);
