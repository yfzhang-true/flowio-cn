// firmware/twin/webapp/js/simlab.js — 仿真实验室浮层 (Task6)
// #t2_simOverlay 全屏玻璃接管: 复用 v1.2 端点 /api/board/sim/presets + /api/board/sim;
// 四电路分段 + 参数表单 (bounds 限值) + 重算 (禁用态"计算中…") + 波形 canvas 自绘细线
// + 指标 ✓/⚠ 徽章; 400 越域红条 / 503 忙 / 504 超时; ESC/✕ 回落主场景。
const $ = (id) => document.getElementById(id);

const CIRCUITS = [
  { id: "buck", name: "Buck 电源", desc: "TPS54331 → 3.3V/3A" },
  { id: "dior", name: "双源二极管或", desc: "SS34×2 DC 座 / USB-C" },
  { id: "valve", name: "阀驱动", desc: "AO3400A 低边 + RL" },
  { id: "i2c", name: "I²C 上拉", desc: "TCA9548A 总线 RC" },
];
const WAVE_COLORS = ["#6aa9ff", "#7ee2b8", "#e8b64c", "#6ad4ff"];

let overlay = null;
let presets = null;
let circuit = "buck";
let built = false;
let lastResult = null;

// 波形 canvas 自绘: 细线多序列 + 细轴线 + 稀疏刻度 (spec §4 曲线图去网格线)
function drawWaves(cv, waves) {
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
  // 细轴线
  g.strokeStyle = "rgba(255,255,255,.18)";
  g.lineWidth = 1;
  g.beginPath();
  g.moveTo(L, T); g.lineTo(L, h - B); g.lineTo(w - R, h - B);
  g.stroke();
  // 稀疏刻度 (y 三档 / x 三档)
  g.fillStyle = "rgba(255,255,255,.42)";
  g.font = "10px ui-monospace,monospace";
  for (let i = 0; i <= 2; i++) {
    const v = y0 + ((y1 - y0) * i) / 2;
    g.fillText(Math.abs(v) >= 1e-3 || v === 0 ? v.toFixed(2) : v.toExponential(1), 2, Y(v) + 3);
    const tx = x0 + ((x1 - x0) * i) / 2;
    g.fillText(tx.toFixed(2), X(tx) - 10, h - 7);
  }
  // 多序列细线
  waves.forEach((s, k) => {
    g.strokeStyle = WAVE_COLORS[k % WAVE_COLORS.length];
    g.lineWidth = 1.5;
    g.lineJoin = "round";
    g.beginPath();
    for (let i = 0; i < s.t.length; i++) (i ? g.lineTo(X(s.t[i]), Y(s.y[i])) : g.moveTo(X(s.t[i]), Y(s.y[i])));
    g.stroke();
  });
}

function buildOverlay() {
  $("t2_simOverlay").innerHTML = `
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
  overlay = $("t2_simOverlay");
  overlay.addEventListener("click", (ev) => { if (ev.target === overlay) close(); });
  $("t2_simClose").onclick = close;
  $("t2_simRun").onclick = run;
  overlay.querySelector(".t2_simCircuits").addEventListener("click", (ev) => {
    const b = ev.target.closest(".t2_simCard");
    if (b) select(b.dataset.c);
  });
  document.addEventListener("keydown", (ev) => {
    if (ev.key === "Escape" && !overlay.hidden) close();
  });
  built = true;
}

function open() {
  if (!built) buildOverlay();
  overlay.hidden = false;
  requestAnimationFrame(() => overlay.classList.add("open"));
  if (!presets) loadPresets();
  else if (lastResult) { drawWaves($("t2_simWave"), lastResult.waves); }   // 重开时重绘 (canvas 尺寸随布局)
}
function close() {
  overlay.classList.remove("open");
  overlay.hidden = true;
}

async function loadPresets() {
  try {
    const j = await (await fetch("/api/board/sim/presets")).json();
    presets = j.presets;
    select("buck");
  } catch (e) {
    simError("presets 加载失败：" + e.message);
  }
}

function select(c) {
  if (!presets || !presets[c]) return;
  circuit = c;
  for (const el of document.querySelectorAll(".t2_simCard"))
    el.classList.toggle("on", el.dataset.c === c);
  const p = presets[c];
  $("t2_simForm").innerHTML = Object.keys(p.default).map((k) => {
    const b = p.bounds[k];
    return `<label><span>${k}</span>
      <input type="number" step="any" min="${b[0]}" max="${b[1]}" value="${p.default[k]}" data-p="${k}"></label>`;
  }).join("");
  $("t2_simErr").hidden = true;
  run();
}

function simError(msg) {
  const el = $("t2_simErr");
  el.textContent = "⚠ " + msg;
  el.hidden = false;
}

async function run() {
  if (!circuit) return;
  const btn = $("t2_simRun");
  btn.disabled = true;
  btn.textContent = "计算中…";                          // 禁用态文案 (忙锁 503 防挂死期间的体感)
  $("t2_simErr").hidden = true;
  const params = {};
  for (const inp of document.querySelectorAll("#t2_simForm input"))
    params[inp.dataset.p] = parseFloat(inp.value);
  try {
    const r = await fetch("/api/board/sim", {
      method: "POST", body: JSON.stringify({ circuit, params }),
    });
    const j = await r.json();
    if (!r.ok) throw new Error(j.error || "HTTP " + r.status);   // 400 参数越域 / 503 忙 / 504 超时
    lastResult = j;
    render(j);
  } catch (e) {
    simError(e.message);
  } finally {
    btn.disabled = false;
    btn.textContent = "⟳ 重算";
  }
}

function render(j) {
  drawWaves($("t2_simWave"), j.waves);
  $("t2_simLegend").innerHTML = j.waves.map((wv, i) =>
    `<span><i style="background:${WAVE_COLORS[i % WAVE_COLORS.length]}"></i>${wv.name}</span>`).join("");
  $("t2_simMets").innerHTML = j.metrics.map((m) => `
    <tr><td>${m.name}</td><td class="t2_num">${m.value} ${m.unit || ""}</td>
    <td><em class="${String(m.verdict).startsWith("✓") ? "ok" : "warn"}">${m.verdict}</em></td></tr>`).join("");
  $("t2_simNotes").innerHTML = (j.notes || []).map((n) => "<div>· " + n + "</div>").join("");
}

export function initSimLab() {
  $("t2_simLabBtn").onclick = open;
  window.__t2 = window.__t2 || {};
  window.__t2.simlab = { open, close, run, select };   // T7 测试调试钩
}
