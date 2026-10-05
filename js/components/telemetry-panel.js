// firmware/twin/webapp/js/components/telemetry-panel.js — <telemetry-panel> 遥测抽屉 (M4, 自 panels.js ① 迁移)
// 5 张 sparkline 玻璃小卡 (canvas 2D 手绘 60 点折线) + 点卡展开 ECharts 小图
// (v5/v33/load=服务端历史镜像 seriesFull; temp/eff=快照环)。
// 数据经 properties: 订阅 store (onState) 刷新; series/seriesFull 来自 telemetry.js 内核。
// 抽屉契约: 默认收起 (spec §2, 宿主 .collapsed); toggle() 发 `drawer-toggle` {collapsed}。
import { store, onState } from "../store.js";
import { series, seriesFull } from "../telemetry.js";
import { FLOWIO_PARAMS } from "../params_gen.js";     // M3: 参数真值 (devices.json 生成物)
import { adopt } from "./styles.js";

const RAIL_LABEL = FLOWIO_PARAMS.rail_v.toFixed(0) + "V";   // 5V 轨名取真值 (rail_v=5.0)
const TLM_CARDS = [
  { id: "v5", name: RAIL_LABEL + " 轨", unit: "V", dec: 3, color: "#e8b64c", get: (t) => t.rail_5v.v },
  { id: "v33", name: "3.3V 轨", unit: "V", dec: 3, color: "#7ee2b8", get: (t) => t.rail_3v3.v },
  { id: "load", name: RAIL_LABEL + " 负载", unit: "A", dec: 2, color: "#6aa9ff", get: (t) => t.rail_5v.load_a },
  { id: "temp", name: "结温峰值", unit: "℃", dec: 1, color: "#ffb454", get: (t) => {
      const x = t.temp_est_c || {}; return Math.max(x.cpu || 0, x.buck || 0, x.mos || 0); } },
  { id: "eff", name: "Buck 效率", unit: "%", dec: 1, color: "#6ad4ff", get: (t) => t.rail_3v3.buck_eff * 100 },
];

let echartsLoading = null;          // 按需加载 /lib/echarts.min.js (仅展开小图用)
function loadECharts() {
  if (window.echarts) return Promise.resolve(window.echarts);
  if (!echartsLoading) echartsLoading = new Promise((res, rej) => {
    const s = document.createElement("script");
    s.src = "/lib/echarts.min.js";
    s.onload = () => res(window.echarts);
    s.onerror = () => { echartsLoading = null; rej(new Error("echarts 加载失败")); };
    document.head.appendChild(s);
  });
  return echartsLoading;
}

class TelemetryPanel extends HTMLElement {
  connectedCallback() {
    if (this._booted) return;
    this._booted = true;
    this._expandId = null;
    this._expandChart = null;
    this._lastTelRef = null;
    const root = this.attachShadow({ mode: "open" });
    adopt(root, `
      :host{display:flex;flex-direction:column;padding:14px 16px;overflow:hidden auto;
        scrollbar-width:thin;scrollbar-color:rgba(255,255,255,.15) transparent}`);
    root.innerHTML = `
      <div class="t2_dHead"><h3>遥测</h3><button id="t2_tlmCollapse" class="t2_btn ghost">收起 ›</button></div>
      <div id="t2_tlmExpand"></div>
      <div id="t2_tlmCards">${TLM_CARDS.map((c) => `
        <div class="t2_tCard" data-ch="${c.id}">
          <div class="t2_tCardTop"><span>${c.name}</span><b class="t2_num" id="t2_tv_${c.id}">—</b></div>
          <canvas class="t2_spark" id="t2_tsp_${c.id}"></canvas>
        </div>`).join("")}
      </div>`;
    root.getElementById("t2_tlmCollapse").onclick = () => this.toggle();
    root.getElementById("t2_tlmCards").addEventListener("click", (ev) => {
      const card = ev.target.closest(".t2_tCard");
      if (card) this.openExpand(card.dataset.ch);
    });
    this.classList.add("collapsed");                   // spec §2: 遥测抽屉默认收起
    onState(() => this.refresh());
    this.refresh();
  }
  toggle() {
    const collapsed = this.classList.toggle("collapsed");
    this.dispatchEvent(new CustomEvent("drawer-toggle",
      { detail: { collapsed }, bubbles: true, composed: true }));
  }
  get $() { return this.shadowRoot.getElementById.bind(this.shadowRoot); }
  // 点卡展开 ECharts 小图 (复用 since 语义数据)
  async openExpand(id) {
    const c = TLM_CARDS.find((x) => x.id === id);
    if (!c) return;
    this._expandId = id;
    const box = this.$("t2_tlmExpand");
    box.innerHTML = `
      <div class="t2_tCard on">
        <div class="t2_tCardTop"><span>${c.name} · 历史</span>
          <button id="t2_tlmExpClose" class="t2_btn ghost" style="padding:2px 10px">✕</button></div>
        <div id="t2_tlmChart" style="height:150px"></div>
      </div>`;
    box.hidden = false;
    this.$("t2_tlmExpClose").onclick = () => this.closeExpand();
    for (const el of this.shadowRoot.querySelectorAll("#t2_tlmCards .t2_tCard"))
      el.classList.toggle("on", el.dataset.ch === id);
    try {
      const echarts = await loadECharts();
      this._expandChart = echarts.init(this.$("t2_tlmChart"));
      this.refreshExpand();
    } catch (e) {
      this.$("t2_tlmChart").innerHTML =
        `<p style="color:var(--txt2);font-size:12px;padding:12px">${e.message}</p>`;
    }
  }
  closeExpand() {
    this._expandId = null;
    this._expandChart = null;
    this.$("t2_tlmExpand").innerHTML = "";
    for (const el of this.shadowRoot.querySelectorAll("#t2_tlmCards .t2_tCard"))
      el.classList.remove("on");
  }
  refreshExpand() {
    if (!this._expandId || !this._expandChart) return;
    const { t, y } = seriesFull(this._expandId);
    this._expandChart.setOption({
      animation: false,
      grid: { left: 46, right: 10, top: 8, bottom: 20 },
      xAxis: { type: "value", axisLabel: { color: "rgba(255,255,255,.4)", fontSize: 10, formatter: (v) => v.toFixed(0) },
               splitLine: { show: false }, axisLine: { lineStyle: { color: "rgba(255,255,255,.15)" } } },
      yAxis: { type: "value", scale: true, splitLine: { show: false },
               axisLabel: { color: "rgba(255,255,255,.4)", fontSize: 10, formatter: (v) => v.toFixed(2) },
               axisLine: { show: false } },
      series: [{ type: "line", showSymbol: false, data: t.map((tv, i) => [tv, y[i]]),
                 lineStyle: { color: (TLM_CARDS.find((c) => c.id === this._expandId) || {}).color, width: 1.5 } }],
    }, true);
  }
  refresh() {
    const tel = store.telemetry;
    for (const c of TLM_CARDS) {
      const el = this.$("t2_tv_" + c.id);
      if (!el) continue;
      const v = tel && tel.rail_5v ? c.get(tel) : undefined;
      el.textContent = (typeof v === "number" && isFinite(v)) ? v.toFixed(c.dec) + " " + c.unit : "—";
    }
    if (tel === this._lastTelRef) return;              // pnu 节拍不重绘 spark
    this._lastTelRef = tel;
    for (const c of TLM_CARDS) this._drawSpark(this.$("t2_tsp_" + c.id), series(c.id), c.color);
    if (this._expandId) this.refreshExpand();
  }
  // canvas 2D 手绘 sparkline: 60 点折线, 无网格, 细线+末端点 (spec §4 克制红线)
  _drawSpark(cv, data, color) {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const w = cv.clientWidth || 216, h = cv.clientHeight || 34;
    if (cv.width !== w * dpr || cv.height !== h * dpr) { cv.width = w * dpr; cv.height = h * dpr; }
    const g = cv.getContext("2d");
    g.setTransform(dpr, 0, 0, dpr, 0, 0);
    g.clearRect(0, 0, w, h);
    if (!data || data.length < 2) return;
    let lo = Math.min(...data), hi = Math.max(...data);
    const span = (hi - lo) || Math.abs(hi) * 0.08 || 1;   // 防零跨度
    lo -= span * 0.18; hi += span * 0.18;
    const X = (i) => 2 + (i / (data.length - 1)) * (w - 8);
    const Y = (v) => h - 3 - ((v - lo) / (hi - lo)) * (h - 6);
    g.strokeStyle = color;
    g.lineWidth = 1.25;
    g.lineJoin = "round";
    g.lineCap = "round";
    g.beginPath();
    data.forEach((v, i) => (i ? g.lineTo(X(i), Y(v)) : g.moveTo(X(i), Y(v))));
    g.stroke();
    g.fillStyle = color;                                   // 末端亮点
    g.beginPath();
    g.arc(w - 4, Y(data[data.length - 1]), 2, 0, Math.PI * 2);
    g.fill();
  }
}
customElements.define("telemetry-panel", TelemetryPanel);
