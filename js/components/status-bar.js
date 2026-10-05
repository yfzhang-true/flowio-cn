// firmware/twin/webapp/js/components/status-bar.js — <status-bar> 状态行 (M4, 自 index.html 骨架+panels.js 迁移)
// stale 红点 (网络断连或板级模型冻结) / 未标定黄徽常驻 / 时间与录制信息 / 仿真实验室入口。
// 事件契约: #t2_simLabBtn 点击 → `sim-open` (composed 上冒, twin-app 开 <sim-lab>)。
import { store, onState } from "../store.js";
import { rec } from "../store.js";
import { adopt } from "./styles.js";

const fmtDur = (s) => {
  const m = Math.floor(s / 60), r = Math.round(s % 60);
  return m ? m + "m" + r + "s" : r + "s";
};

class StatusBar extends HTMLElement {
  connectedCallback() {
    if (this._booted) return;
    this._booted = true;
    const root = this.attachShadow({ mode: "open" });
    adopt(root, `
      :host{display:flex;align-items:center;gap:16px;padding:0 20px;border-top:1px solid var(--hair);
        font-size:12px;color:var(--txt2);background:rgba(10,10,12,.55);backdrop-filter:blur(24px)}
      #t2_timeInfo{flex:1}`);
    root.innerHTML = `
      <span id="t2_staleBadge" class="t2_badge err" hidden>● 遥测冻结</span>
      <span id="t2_calBadge" class="t2_badge warn">模型参数：理论值（未本机标定）</span>
      <span id="t2_timeInfo"></span>
      <button id="t2_simLabBtn" class="t2_btn ghost">仿真实验室</button>`;
    root.getElementById("t2_simLabBtn").addEventListener("click", () => {
      this.dispatchEvent(new CustomEvent("sim-open", { bubbles: true, composed: true }));
    });
    onState(() => { this._refreshStatus(); this._tickTime(); });
    this._timer = setInterval(() => this._tickTime(), 1000);
    this._refreshStatus();
    this._tickTime();
  }
  disconnectedCallback() { if (this._timer) clearInterval(this._timer); }
  _refreshStatus() {
    const el = this.shadowRoot.getElementById("t2_staleBadge");
    if (!el) return;
    const tel = store.telemetry;
    el.hidden = !(!!store.stale || !!(tel && tel.stale));   // 网络断连 或 板级模型冻结
  }
  _tickTime() {
    const info = this.shadowRoot.getElementById("t2_timeInfo");
    if (!info) return;
    const tel = store.telemetry;
    const parts = [new Date().toLocaleTimeString("zh-CN", { hour12: false })];
    if (store.mode === "real") parts.push("真机 BLE");
    else if (tel && isFinite(tel.uptime_s)) parts.push("孪生 " + fmtDur(tel.uptime_s));
    if (store.recording) parts.push("● 录制中");
    else if (rec.events.length) parts.push("已录 " + rec.events.length + " 条");
    info.textContent = parts.join(" · ");
  }
}
customElements.define("status-bar", StatusBar);
