// firmware/twin/webapp/js/components/transport-pill.js — <transport-pill> 运输条 (M4, 自 panels.js 迁移)
// 播放/单步/速度/录制/回放 + 爆炸滑杆。孪生时间与录制走 postJSON (/api/time,
// /api/record…); 爆炸经 window.__t2.scene.setExplode (场景内核句柄) + setState。
import { store, setState, postJSON, rec } from "../store.js";
import { adopt } from "./styles.js";

class TransportPill extends HTMLElement {
  connectedCallback() {
    if (this._booted) return;
    this._booted = true;
    this._paused = false;
    const root = this.attachShadow({ mode: "open" });
    adopt(root, `
      :host{display:flex;gap:10px;align-items:center;padding:10px 18px}
      :host(.t2_pill), .t2_pill>*{flex:none;white-space:nowrap}`);
    root.innerHTML = `
      <button id="t2_playBtn" class="t2_btn ghost" title="暂停 / 继续孪生时间">⏸ 暂停</button>
      <button id="t2_stepBtn" class="t2_btn ghost" title="暂停下单步 50ms">单步</button>
      <label class="t2_explWrap">速度
        <input type="range" id="t2_speedRange" class="t2_speed" min="0.25" max="4" step="0.25" value="1">
        <span id="t2_speedVal" class="t2_num">×1.00</span></label>
      <span class="t2_tpDiv"></span>
      <button id="t2_recBtn" class="t2_btn ghost" title="录制本页发出的全部 CLI 命令 (recordings/ + 浏览器镜像)">⏺ 录制</button>
      <button id="t2_replayBtn" class="t2_btn ghost" hidden title="按墙钟时序回放">▶ <span id="t2_recN" class="t2_num">0</span></button>
      <span class="t2_tpDiv"></span>
      <label class="t2_explWrap">爆炸
        <input type="range" id="t2_explodeRange" class="t2_explode" min="0" max="1" step="0.01" value="0">
        <span id="t2_explodeVal" class="t2_num">0%</span></label>`;
    const $ = root.getElementById.bind(root);
    $("t2_playBtn").onclick = async () => {
      this._paused = !this._paused;
      $("t2_playBtn").textContent = this._paused ? "▶ 继续" : "⏸ 暂停";
      const j = await postJSON("/api/time", { paused: this._paused });
      if (j) setState({ paused: !!j.paused });
    };
    $("t2_stepBtn").onclick = () => postJSON("/api/time", { step_once: true });
    $("t2_speedRange").onchange = async (ev) => {       // change 提交 (拖动不风暴)
      const j = await postJSON("/api/time", { speed: +ev.target.value });
      if (j) $("t2_speedVal").textContent = "×" + (+j.speed).toFixed(2);
    };
    $("t2_explodeRange").oninput = (ev) => {
      const k = parseFloat(ev.target.value);
      const sc = window.__t2 && window.__t2.scene;
      if (sc) sc.setExplode(k);
      setState({ explode: k });
      $("t2_explodeVal").textContent = Math.round(k * 100) + "%";
    };
    $("t2_recBtn").onclick = () => this._toggleRec();
    $("t2_replayBtn").onclick = () => this._replayRec();
  }
  async _toggleRec() {
    const on = !store.recording;
    setState({ recording: on });
    if (on) rec.events = [];
    await postJSON("/api/record", { action: on ? "start" : "stop" });
    this._refreshRecUI();
    if (!on && rec.events.length)
      this.shadowRoot.getElementById("t2_recN").textContent = rec.events.length;
  }
  async _replayRec() {
    const j = await postJSON("/api/record/replay", { events: rec.events });
    if (j && j.replaying !== undefined)
      this.shadowRoot.getElementById("t2_replayBtn").title = `回放 ${j.replaying} 条 (后台时序)`;
  }
  _refreshRecUI() {
    const $ = this.shadowRoot.getElementById.bind(this.shadowRoot);
    const btn = $("t2_recBtn");
    if (!btn) return;
    const on = !!store.recording;
    btn.textContent = on ? "⏹ 停止" : "⏺ 录制";
    btn.classList.toggle("rec", on);
    $("t2_replayBtn").hidden = on || !rec.events.length;
    $("t2_recN").textContent = rec.events.length;
  }
}
customElements.define("transport-pill", TransportPill);
