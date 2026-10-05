// firmware/twin/webapp/js/components/sim-lab.js — <sim-lab> 仿真实验室浮层 (M4, 自 simlab.js 整体迁入)
// 宿主即全屏浮层 (hidden 属性 + .open 类, 定位样式在 :host); 影子内为玻璃 sheet。
// 复用 v1.2 端点 /api/board/sim/presets + /api/board/sim: 四电路分段 + 参数表单
// (bounds 限值) + 重算 (禁用态"计算中…") + 波形 canvas 自绘细线 + 指标 ✓/⚠ 徽章;
// 400 越域红条 / 503 忙 / 504 超时; ESC/✕/点击背板回落主场景。
// 方法契约: open()/close()/run()/select(c) — 注册 window.__t2.simlab (T7 调试钩)。
import { adopt } from "./styles.js";

const CIRCUITS = [
  { id: "buck", name: "Buck 电源", desc: "TPS54331 → 3.3V/3A" },
  { id: "dior", name: "双源二极管或", desc: "SS34×2 DC 座 / USB-C" },
  { id: "valve", name: "阀驱动", desc: "AO3400A 低边 + RL" },
  { id: "i2c", name: "I²C 上拉", desc: "TCA9548A 总线 RC" },
];
const WAVE_COLORS = ["#6aa9ff", "#7ee2b8", "#e8b64c", "#6ad4ff"];

class SimLab extends HTMLElement {
  connectedCallback() {
    if (this._booted) return;
    this._booted = true;
    this._presets = null;
    this._circuit = "buck";
    this._built = false;
    this._lastResult = null;
    const root = this.attachShadow({ mode: "open" });
    adopt(root, `
      :host{position:fixed;inset:0;z-index:20;background:rgba(10,10,12,.6);backdrop-filter:blur(8px)}
      :host([hidden]){display:none}
      .t2_simSheet{position:absolute;left:50%;top:50%;transform:translate(-50%,-47%);
        width:min(920px,calc(100vw - 48px));max-height:calc(100vh - 64px);overflow:auto;
        padding:22px 26px;opacity:0;transition:opacity .25s var(--ease),transform .25s var(--ease)}
      :host(.open) .t2_simSheet{opacity:1;transform:translate(-50%,-50%)}
      .t2_simHead{display:flex;justify-content:space-between;align-items:center;margin-bottom:14px}
      .t2_simHead h3{font-size:17px;font-weight:600}
      .t2_simCircuits{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:14px}
      .t2_simCard{font:inherit;text-align:left;color:var(--txt);background:var(--glass);border:1px solid var(--hair);
        border-radius:14px;padding:10px 14px;cursor:pointer;transition:all .15s var(--ease)}
      .t2_simCard:hover{background:rgba(255,255,255,.1)}
      .t2_simCard.on{border-color:var(--accent);background:rgba(106,169,255,.14)}
      .t2_simCard b{display:block;font-weight:600;font-size:13px}
      .t2_simCard span{font-size:11px;color:var(--txt2)}
      .t2_simGrid{display:grid;grid-template-columns:minmax(210px,.7fr) minmax(360px,1.4fr);gap:18px}
      .t2_simLeft h4{font-size:13px;color:var(--txt2);font-weight:600;margin-bottom:8px}
      .t2_simLeft h4 small{font-weight:400;opacity:.7}
      .t2_simForm label{display:flex;justify-content:space-between;align-items:center;gap:8px;margin:7px 0;font-size:12px;color:var(--txt2)}
      .t2_simForm input{width:110px;font:inherit;font-size:12px;color:var(--txt);background:rgba(0,0,0,.3);
        border:1px solid var(--hair);border-radius:8px;padding:5px 8px}
      .t2_simErr{margin-top:10px;padding:8px 12px;border-radius:10px;background:rgba(120,20,20,.5);
        border:1px solid rgba(255,95,87,.5);color:#ff9d96;font-size:12px}
      .t2_simLegend{display:flex;gap:14px;font-size:11px;color:var(--txt2);margin-bottom:6px;flex-wrap:wrap}
      .t2_simLegend i{display:inline-block;width:14px;height:2px;vertical-align:3px;margin-right:5px;border-radius:1px}
      #t2_simWave{width:100%;height:250px;display:block}
      .t2_simMets{width:100%;border-collapse:collapse;font-size:12px;margin-top:10px}
      .t2_simMets th{color:var(--txt2);font-weight:400;text-align:left;padding:4px 8px;border-bottom:1px solid var(--hair)}
      .t2_simMets td{padding:5px 8px;border-bottom:1px solid rgba(255,255,255,.06)}
      .t2_simMets em.ok{font-style:normal;color:#7ee2b8}
      .t2_simMets em.warn{font-style:normal;color:#ffd479}
      .t2_simNotes{font-size:11px;color:var(--txt2);line-height:1.7}`);
    // ESC 在 document 层监听 (浮层语义跨影子仍成立)
    document.addEventListener("keydown", (ev) => {
      if (ev.key === "Escape" && !this.hidden) this.close();
    });
    window.__t2 = window.__t2 || {};
    window.__t2.simlab = { open: () => this.open(), close: () => this.close(),
                           run: () => this.run(), select: (c) => this.select(c) };  // T7 调试钩
  }
  get $() { return this.shadowRoot.getElementById.bind(this.shadowRoot); }

  open() {
    if (!this._built) this._build();
    this.hidden = false;
    requestAnimationFrame(() => this.classList.add("open"));
    if (!this._presets) this._loadPresets();
    else if (this._lastResult) this._drawWaves(this.$("t2_simWave"), this._lastResult.waves); // 重开重绘 (canvas 尺寸随布局)
  }
  close() {
    this.classList.remove("open");
    this.hidden = true;
  }
  _build() {
    const root = this.shadowRoot;
    root.innerHTML = `
      <div class="t2_simSheet t2_glass">
        <header class="t2_simHead"><h3>仿真实验室</h3>
          <button id="t2_simClose" class="t2_btn ghost" title="ESC 关闭">✕ 关闭</button></header>
        <div class="t2_simCircuits">${CIRCUITS.map((c) => `
          <button class="t2_simCard" data-c="${c.id}">
            <b>${c.name}</b><span>${c.desc}</span></button>`).join("")}
        </div>
        <div class="t2_simGrid">
          <section class="t2_simLeft">
            <h4>参数 <small>(域约束来自 presets)</small></h4>
            <div class="t2_simForm" id="t2_simForm"></div>
            <button id="t2_simRun" class="t2_btn" style="width:100%">⟳ 重算</button>
            <div class="t2_simErr" id="t2_simErr" hidden></div>
          </section>
          <section class="t2_simRight">
            <div class="t2_simLegend" id="t2_simLegend"></div>
            <canvas id="t2_simWave"></canvas>
            <table class="t2_simMets"><thead>
              <tr><th>指标</th><th>数值</th><th>判定</th></tr></thead><tbody id="t2_simMets"></tbody></table>
            <div class="t2_simNotes" id="t2_simNotes"></div>
          </section>
        </div>
      </div>`;
    this.addEventListener("click", (ev) => { if (ev.target === this) this.close(); });  // 点击背板
    this.$("t2_simClose").onclick = () => this.close();
    this.$("t2_simRun").onclick = () => this.run();
    root.querySelector(".t2_simCircuits").addEventListener("click", (ev) => {
      const b = ev.target.closest(".t2_simCard");
      if (b) this.select(b.dataset.c);
    });
    this._built = true;
  }
  async _loadPresets() {
    try {
      const j = await (await fetch("/api/board/sim/presets")).json();
      this._presets = j.presets;
      this.select("buck");
    } catch (e) {
      this._simError("presets 加载失败：" + e.message);
    }
  }
  select(c) {
    if (!this._presets || !this._presets[c]) return;
    this._circuit = c;
    for (const el of this.shadowRoot.querySelectorAll(".t2_simCard"))
      el.classList.toggle("on", el.dataset.c === c);
    const p = this._presets[c];
    this.$("t2_simForm").innerHTML = Object.keys(p.default).map((k) => {
      const b = p.bounds[k];
      return `<label><span>${k}</span>
        <input type="number" step="any" min="${b[0]}" max="${b[1]}" value="${p.default[k]}" data-p="${k}"></label>`;
    }).join("");
    this.$("t2_simErr").hidden = true;
    this.run();
  }
  _simError(msg) {
    const el = this.$("t2_simErr");
    el.textContent = "⚠ " + msg;
    el.hidden = false;
  }
  async run() {
    if (!this._circuit) return;
    const btn = this.$("t2_simRun");
    btn.disabled = true;
    btn.textContent = "计算中…";                      // 禁用态文案 (忙锁 503 防挂死期间的体感)
    this.$("t2_simErr").hidden = true;
    const params = {};
    for (const inp of this.shadowRoot.querySelectorAll("#t2_simForm input"))
      params[inp.dataset.p] = parseFloat(inp.value);
    try {
      const r = await fetch("/api/board/sim", {
        method: "POST", body: JSON.stringify({ circuit: this._circuit, params }),
      });
      const j = await r.json();
      if (!r.ok) throw new Error(j.error || "HTTP " + r.status);   // 400 参数越域 / 503 忙 / 504 超时
      this._lastResult = j;
      this._render(j);
    } catch (e) {
      this._simError(e.message);
    } finally {
      btn.disabled = false;
      btn.textContent = "⟳ 重算";
    }
  }
  _render(j) {
    this._drawWaves(this.$("t2_simWave"), j.waves);
    this.$("t2_simLegend").innerHTML = j.waves.map((wv, i) =>
      `<span><i style="background:${WAVE_COLORS[i % WAVE_COLORS.length]}"></i>${wv.name}</span>`).join("");
    this.$("t2_simMets").innerHTML = j.metrics.map((m) => `
      <tr><td>${m.name}</td><td class="t2_num">${m.value} ${m.unit || ""}</td>
      <td><em class="${String(m.verdict).startsWith("✓") ? "ok" : "warn"}">${m.verdict}</em></td></tr>`).join("");
    this.$("t2_simNotes").innerHTML = (j.notes || []).map((n) => "<div>· " + n + "</div>").join("");
  }
  // 波形 canvas 自绘: 细线多序列 + 细轴线 + 稀疏刻度 (spec §4 曲线图去网格线)
  _drawWaves(cv, waves) {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const w = cv.clientWidth || 640, h = cv.clientHeight || 260;
    if (cv.width !== w * dpr || cv.height !== h * dpr) { cv.width = w * dpr; cv.height = h * dpr; }
    const g = cv.getContext("2d");
    g.setTransform(dpr, 0, 0, dpr, 0, 0);
    g.clearRect(0, 0, w, h);
    const L = 44, R = 8, T = 8, B = 22;
    if (!waves || !waves.length) return;
    let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
    for (const s of waves) for (let i = 0; i < s.t.length; i++) {
      x0 = Math.min(x0, s.t[i]); x1 = Math.max(x1, s.t[i]);
      y0 = Math.min(y0, s.y[i]); y1 = Math.max(y1, s.y[i]);
    }
    const xs = (x1 - x0) || 1, ys = (y1 - y0) || 1;
    y0 -= ys * 0.08; y1 += ys * 0.08;
    const X = (v) => L + ((v - x0) / xs) * (w - L - R);
    const Y = (v) => h - B - ((v - y0) / (y1 - y0)) * (h - T - B);
    g.strokeStyle = "rgba(255,255,255,.18)";
    g.lineWidth = 1;
    g.beginPath();
    g.moveTo(L, T); g.lineTo(L, h - B); g.lineTo(w - R, h - B);
    g.stroke();
    g.fillStyle = "rgba(255,255,255,.42)";
    g.font = "10px ui-monospace,monospace";
    for (let i = 0; i <= 2; i++) {
      const v = y0 + ((y1 - y0) * i) / 2;
      g.fillText(Math.abs(v) >= 1e-3 || v === 0 ? v.toFixed(2) : v.toExponential(1), 2, Y(v) + 3);
      const tx = x0 + ((x1 - x0) * i) / 2;
      g.fillText(tx.toFixed(2), X(tx) - 10, h - 7);
    }
    waves.forEach((s, k) => {
      g.strokeStyle = WAVE_COLORS[k % WAVE_COLORS.length];
      g.lineWidth = 1.5;
      g.lineJoin = "round";
      g.beginPath();
      for (let i = 0; i < s.t.length; i++)
        (i ? g.lineTo(X(s.t[i]), Y(s.y[i])) : g.moveTo(X(s.t[i]), Y(s.y[i])));
      g.stroke();
    });
  }
}
customElements.define("sim-lab", SimLab);
