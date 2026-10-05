// firmware/twin/webapp/js/components/channel-row.js — <channel-row> 通道行 (M4)
// 自 panels.js 控制抽屉行迁出: 名称 + 阀位点灯 (t2_vd_N) + Apple 分段控件 (充/保/释/抽)。
// 分段语义 (固件实证): 释=S 确定性关阀 (R 不清 duty); 保=H 诊断保压。
// 属性契约: port (0-7, observed) / name —— 属性驱动渲染; setOn(on) 点灯。
// 事件契约: 按钮点击 → `valve-cmd` {cmd:"I"|"H"|"S"|"V", port:Number} (composed 上冒,
//           由 <control-drawer> 组装掩码与 PWM 档)。
import { adopt } from "./styles.js";

export const SEGS = [
  { cmd: "I", label: "充" }, { cmd: "H", label: "保" },
  { cmd: "S", label: "释" }, { cmd: "V", label: "抽" },
];

class ChannelRow extends HTMLElement {
  static get observedAttributes() { return ["port", "name"]; }
  connectedCallback() {
    if (this._booted) return;
    this._booted = true;
    const root = this.attachShadow({ mode: "open" });
    adopt(root, ":host{display:block;flex:none}");
    this._render(root);
    root.addEventListener("click", (ev) => {
      const b = ev.target.closest(".t2_seg button");
      if (!b) return;
      b.classList.add("hit");                          // 点击回执微光
      setTimeout(() => b.classList.remove("hit"), 260);
      this.dispatchEvent(new CustomEvent("valve-cmd",
        { detail: { cmd: b.dataset.cmd, port: this.port }, bubbles: true, composed: true }));
    });
  }
  attributeChangedCallback() {
    if (this._booted) this._render(this.shadowRoot);  // 属性变化 → 重渲染 (反映契约)
  }
  _render(root) {
    const port = this.getAttribute("port") || "0";
    const name = this.getAttribute("name") || "";
    root.innerHTML = `
      <div class="t2_vRow"><span class="nm">${name}</span><i class="t2_vDot" id="t2_vd_${port}"></i>
        <div class="t2_seg" data-port="${port}">${SEGS.map((s) =>
          `<button data-cmd="${s.cmd}" title="${s.label} → ${s.cmd} ${1 << port}">${s.label}</button>`).join("")}
        </div></div>`;
  }
  get port() { return parseInt(this.getAttribute("port"), 10) || 0; }
  setOn(on) {                                          // 阀位点灯: pnu duty>0 (真机/孪生同构)
    const dot = this.shadowRoot && this.shadowRoot.querySelector(".t2_vDot");
    if (dot) dot.classList.toggle("on", !!on);
  }
}
customElements.define("channel-row", ChannelRow);
