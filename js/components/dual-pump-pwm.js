// firmware/twin/webapp/js/components/dual-pump-pwm.js — <dual-pump-pwm> 双泵 PWM 滑条 (M4)
// 自 panels.js 控制抽屉头部迁出 —— 对齐官方 GUI 参考 (资源/官方参考/flowio-official-gui-reference.png):
// Vacuum PWM / Inflation PWM 两档泵功率 (官方 setPumpPower 语义: 充气/真空独立设压),
// I 命令携充气档、V 命令携真空档; 255 制与官方一致 (registry 泵上限 95%≈242,
// 固件侧钳位, 孪生保持全域可探索)。
// 事件契约: input → `pwm-change` {kind:"infl"|"vac", value:Number} (composed 上冒)。
// 属性契约: infl/vac getter 读底层滑条活值 (点击组装命令时现读 —— 程序化设 .value
//           不发 input 也能被后续 I/V 命令取到, 与旧版行为逐位一致)。
import { adopt } from "./styles.js";

class DualPumpPwm extends HTMLElement {
  connectedCallback() {
    if (this._booted) return;
    this._booted = true;
    const root = this.attachShadow({ mode: "open" });
    adopt(root, ":host{display:block;flex:none}");
    root.innerHTML = `
      <label class="t2_pwmRow">充气 PWM
        <input type="range" id="t2_pwmInfl" min="80" max="255" step="1" value="255"
               title="Inflation PWM —— 充气(I)命令的泵功率档">
        <b id="t2_pwmInflVal" class="t2_num">255</b></label>
      <label class="t2_pwmRow">真空 PWM
        <input type="range" id="t2_pwmVac" min="80" max="255" step="1" value="255"
               title="Vacuum PWM —— 真空(V)命令的泵功率档">
        <b id="t2_pwmVacVal" class="t2_num">255</b></label>`;
    this._infl = root.getElementById("t2_pwmInfl");
    this._vac = root.getElementById("t2_pwmVac");
    this._inflVal = root.getElementById("t2_pwmInflVal");
    this._vacVal = root.getElementById("t2_pwmVacVal");
    this._infl.oninput = (ev) => this._emit("infl", ev.target.value);
    this._vac.oninput = (ev) => this._emit("vac", ev.target.value);
  }
  _emit(kind, value) {
    (kind === "infl" ? this._inflVal : this._vacVal).textContent = value;
    this.dispatchEvent(new CustomEvent("pwm-change",
      { detail: { kind, value: +value }, bubbles: true, composed: true }));
  }
  get infl() { return this._infl ? +this._infl.value : 255; }
  get vac() { return this._vac ? +this._vac.value : 255; }
}
customElements.define("dual-pump-pwm", DualPumpPwm);
