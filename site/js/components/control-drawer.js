// firmware/twin/webapp/js/components/control-drawer.js — <control-drawer> 控制抽屉 (M4, 自 panels.js ② 迁移)
// 组装: <dual-pump-pwm> 双滑条 + 全局 1-5 分段行 (掩码 31) + <channel-row>×8 + 脚部 T/X/F。
// 命令流 (事件契约): channel-row `valve-cmd` / 全局行点击 → 本组件组装 CLI 行
//   (I 携充气档 pwm.infl、V 携真空档 pwm.vac —— 活值现读) → 发 `cmd-line`
//   {line:"I 1 255"} (composed 上冒) → main.js 在 document 层路由到 store.sendCmd。
// 抽屉契约: .collapsed 类挂宿主; toggle() 发 `drawer-toggle` {collapsed} (twin-app 显隐浮钮)。
import { store, onState } from "../store.js";
import { adopt } from "./styles.js";
import "./dual-pump-pwm.js";
import { SEGS } from "./channel-row.js";

const VALVE_NAMES = ["阀1·端口", "阀2·端口", "阀3·端口", "阀4·端口", "阀5·端口",
                     "阀6·进气", "阀7·排气", "阀8·备用"];

class ControlDrawer extends HTMLElement {
  connectedCallback() {
    if (this._booted) return;
    this._booted = true;
    const root = this.attachShadow({ mode: "open" });
    adopt(root, `
      :host{display:flex;flex-direction:column;padding:14px 16px;overflow:hidden auto;
        scrollbar-width:thin;scrollbar-color:rgba(255,255,255,.15) transparent}`);
    root.innerHTML = `
      <div class="t2_dHead"><h3>控制</h3><button id="t2_ctrlCollapse" class="t2_btn ghost">‹ 收起</button></div>
      <dual-pump-pwm id="t2_pwm"></dual-pump-pwm>
      <div class="t2_vRow"><span class="nm">全局 1-5</span>
        <div class="t2_seg" data-port="g">${SEGS.map((s) =>
          `<button data-cmd="${s.cmd}" title="${s.label} → ${s.cmd} (掩码 31)">${s.label}</button>`).join("")}
        </div></div>
      ${VALVE_NAMES.map((nm, i) =>
        `<channel-row port="${i}" name="${nm}"></channel-row>`).join("")}
      <div class="t2_ctrlFoot">
        <button class="t2_btn ghost" data-line="T" title="读 16 位状态字">状态字</button>
        <button class="t2_btn ghost" data-line="X" title="闭环状态机复位">闭环复位</button>
        <button class="t2_btn ghost" data-line="F" title="硬件自检（输出在服务端控制台）">自检</button>
      </div>`;
    this._pwm = root.getElementById("t2_pwm");
    this._rows = [...root.querySelectorAll("channel-row")];
    root.getElementById("t2_ctrlCollapse").onclick = () => this.toggle();
    // 通道行 → 组装 CLI (I/V 携双泵滑条活值)
    root.addEventListener("valve-cmd", (ev) => this._sendValve(ev.detail.cmd, ev.detail.port));
    // 全局行 + 脚部按钮 (本组件影子内的直属 DOM)
    root.addEventListener("click", (ev) => {
      const foot = ev.target.closest("[data-line]");
      if (foot) { this._dispatchLine(foot.dataset.line); return; }
      const b = ev.target.closest(".t2_seg button");
      if (!b) return;
      const seg = b.closest(".t2_seg");
      if (seg.dataset.port !== "g") return;            // 通道行走 valve-cmd 事件
      this._sendValve(b.dataset.cmd, "g");
      b.classList.add("hit");
      setTimeout(() => b.classList.remove("hit"), 260);
    });
    onState(() => this.refresh());                     // 阀位点灯
    this.refresh();
  }
  _sendValve(cmd, port) {
    const mask = port === "g" ? 31 : (1 << port);
    this._dispatchLine(cmd === "I" ? `I ${mask} ${this._pwm.infl}`      // 充气 → 充气档
         : cmd === "V" ? `V ${mask} ${this._pwm.vac}`                   // 真空 → 真空档
         : `${cmd} ${mask}`);
  }
  _dispatchLine(line) {
    this.dispatchEvent(new CustomEvent("cmd-line", { detail: { line }, bubbles: true, composed: true }));
  }
  toggle() {
    const collapsed = this.classList.toggle("collapsed");
    this.dispatchEvent(new CustomEvent("drawer-toggle",
      { detail: { collapsed }, bubbles: true, composed: true }));
  }
  refresh() {
    const duties = (store.pnu && store.pnu.valves) || [];
    for (let i = 0; i < 8; i++) {
      const pv = duties[i];
      const on = pv !== undefined ? pv > 0
        : !!(store.telemetry && store.telemetry.valves && store.telemetry.valves[i] || {}).on;
      this._rows[i].setOn(!!on);
    }
  }
}
customElements.define("control-drawer", ControlDrawer);
