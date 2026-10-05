// firmware/twin/webapp/js/components/twin-app.js — <twin-app> 根组件 (M4)
// 布局 (48px 顶栏 / 舞台 / 36px 状态行) + 子组件组装 + 跨组件事件路由:
//   · scene-3d 拾取 (onPartClick 属性) → hotspot-card.show
//   · `drawer-toggle` {collapsed} → 抽屉浮钮 (t2_ctrlTab/t2_tlmTab) 显隐
//   · `sim-open` → sim-lab.open
// 宿主定位契约: 抽屉/运输条/热点卡的 absolute 定位与折叠 transform 写在本组件
// 影子内 ("宿主样式归父" —— 子组件自身外观才归子组件的 :host)。
import { adopt } from "./styles.js";
import "./top-bar.js";
import "./scene-3d.js";
import "./control-drawer.js";
import "./telemetry-panel.js";
import "./transport-pill.js";
import "./hotspot-card.js";
import "./status-bar.js";
import "./sim-lab.js";

class TwinApp extends HTMLElement {
  connectedCallback() {
    if (this._booted) return;
    this._booted = true;
    const root = this.attachShadow({ mode: "open" });
    adopt(root, `
      :host{display:grid;grid-template-rows:48px 1fr 36px;height:100%}
      #t2_stage{position:relative;overflow:hidden;
        background:radial-gradient(120% 100% at 50% 20%,var(--bg0),var(--bg1))}
      /* 抽屉/浮层宿主定位 (父影子职责) */
      control-drawer.t2_drawer,telemetry-panel.t2_drawer{position:absolute;top:60px;bottom:52px;width:264px;
        transition:transform .2s var(--ease);z-index:5}
      control-drawer.left{left:12px} telemetry-panel.right{right:12px}
      control-drawer.collapsed{transform:translateX(calc(-100% - 24px))}
      telemetry-panel.right.collapsed{transform:translateX(calc(100% + 24px))}
      /* 控制面材质略加浓 (玻璃 6% 白透出中带亮机身影响可读性 → 44% 深底仍保 blur 通透) */
      control-drawer.t2_glass,telemetry-panel.t2_glass{background:rgba(14,14,18,.44)}
      transport-pill.t2_pill{position:absolute;left:50%;bottom:44px;transform:translateX(-50%);
        display:flex;z-index:5;font-size:13px;max-width:calc(100vw - 32px)}
      hotspot-card.t2_card{position:absolute;right:292px;bottom:52px;width:240px;z-index:6;
        transition:opacity .2s var(--ease),transform .2s var(--ease)}
      hotspot-card.t2_card.hidden{opacity:0;transform:translateY(8px);pointer-events:none}
      /* 收起态浮钮 (抽屉滑出后仍可唤回) */
      .t2_dTab{position:absolute;top:64px;width:34px;height:34px;border-radius:50%;padding:0;
        display:grid;place-items:center;font-size:14px;line-height:1;z-index:5}
      #t2_ctrlTab{left:12px} #t2_tlmTab{right:12px}`);
    root.innerHTML = `
      <top-bar id="t2_topbar"></top-bar>
      <main id="t2_stage">
        <scene-3d id="t2_scene"></scene-3d>
        <control-drawer id="t2_ctrlDrawer" class="t2_drawer left t2_glass"></control-drawer>
        <transport-pill id="t2_transport" class="t2_pill t2_glass"></transport-pill>
        <telemetry-panel id="t2_tlmDrawer" class="t2_drawer right t2_glass"></telemetry-panel>
        <hotspot-card id="t2_hotspotCard" class="t2_card t2_glass hidden"></hotspot-card>
      </main>
      <status-bar id="t2_statusbar"></status-bar>
      <sim-lab id="t2_simOverlay" hidden></sim-lab>`;
    const $ = root.getElementById.bind(root);
    this.stage = $("t2_stage");
    this.sceneEl = $("t2_scene");
    this.hotspotCard = $("t2_hotspotCard");
    this.simLab = $("t2_simOverlay");
    // 场景拾取 → 热点卡 (属性注入, scene-3d 内核回调)
    this.sceneEl.onPartClick = (h) => this.hotspotCard.show(h);
    // 抽屉浮钮 + drawer-toggle 路由
    const drawerOf = { t2_ctrlTab: $("t2_ctrlDrawer"), t2_tlmTab: $("t2_tlmDrawer") };
    for (const [id, drawer] of Object.entries(drawerOf)) {
      const tab = document.createElement("button");
      tab.id = id;
      tab.className = "t2_btn t2_glass t2_dTab";
      tab.hidden = id !== "t2_tlmTab";                 // 遥测默认收起 → 其浮钮初始可见
      tab.textContent = id === "t2_ctrlTab" ? "⚙" : "📈";
      tab.title = id === "t2_ctrlTab" ? "展开控制抽屉" : "展开遥测抽屉";
      tab.onclick = () => drawer.toggle();
      this.stage.appendChild(tab);
    }
    root.addEventListener("drawer-toggle", (ev) => {
      const tab = ev.target === drawerOf.t2_ctrlTab ? $("t2_ctrlTab")
                : ev.target === drawerOf.t2_tlmTab ? $("t2_tlmTab") : null;
      if (tab) tab.hidden = !ev.detail.collapsed;      // 浮钮可见 ⟺ 抽屉收起
    });
    // 状态行 → 仿真实验室
    root.addEventListener("sim-open", () => this.simLab.open());
  }
}
customElements.define("twin-app", TwinApp);
