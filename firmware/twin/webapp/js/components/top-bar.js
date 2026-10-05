// firmware/twin/webapp/js/components/top-bar.js — <top-bar> 顶栏 (M4, 自 index.html/index 模板迁移)
// 职责: 品牌 + 模式徽章 (#t2_modeBadge, ble.js 经 store 订阅切字) + 真机按钮
// (#t2_bleBtn → 发 `ble-toggle` composed 事件, ble.js 在 document 层接管)。
import { adopt } from "./styles.js";

class TopBar extends HTMLElement {
  connectedCallback() {
    if (this._booted) return;
    this._booted = true;
    const root = this.attachShadow({ mode: "open" });
    adopt(root, `
      :host{display:flex;align-items:center;gap:16px;padding:0 20px;border-bottom:1px solid var(--hair);
        background:rgba(10,10,12,.55);backdrop-filter:blur(24px);z-index:10}
      .t2_brand{font-weight:600;letter-spacing:.02em}`);
    root.innerHTML = `
      <span class="t2_brand">FLOWIO-CN</span>
      <span id="t2_modeBadge" class="t2_badge">孪生</span>
      <button id="t2_bleBtn" class="t2_btn ghost">连接真机</button>`;
    root.getElementById("t2_bleBtn").addEventListener("click", () => {
      this.dispatchEvent(new CustomEvent("ble-toggle", { bubbles: true, composed: true }));
    });
  }
}
customElements.define("top-bar", TopBar);
