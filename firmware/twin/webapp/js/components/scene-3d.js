// firmware/twin/webapp/js/components/scene-3d.js — <scene-3d> 3D 舞台容器 (M4)
// 组件只是 canvas 壳: 内核 three 场景/装配/热点/流光全在 ../scene.js (动态 import,
// 惰性加载语义保持)。WebGL/装配失败 → 优雅降级卡, 其余抽屉仍可用 (spec §6)。
// 属性契约: onPartClick(h) —— 拾取回调 (twin-app 注入, 转发 <hotspot-card>)。
// 注: canvas 包一层 <div id="t2_sceneView"> —— scene.js resize 用 canvas.parentElement
// 量尺寸, 影子根的直接子元素 parentElement 为 null, 包壳后内核零改动。
import { adopt } from "./styles.js";

class Scene3D extends HTMLElement {
  constructor() { super(); this.onPartClick = () => {}; }
  connectedCallback() {
    if (this._booted) return;
    this._booted = true;
    const root = this.attachShadow({ mode: "open" });
    adopt(root, `
      :host{position:absolute;inset:0;display:block}
      #t2_sceneView{position:absolute;inset:0}
      #t2_canvas{width:100%;height:100%;display:block}
      .t2_glass{position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);
        padding:24px;z-index:8}`);
    root.innerHTML = `<div id="t2_sceneView"><canvas id="t2_canvas"></canvas></div>`;
    import("../scene.js")
      .then(({ createScene }) =>
        createScene(root.getElementById("t2_canvas"), (h) => this.onPartClick(h)))
      .catch((e) => {
        const d = document.createElement("div");
        d.className = "t2_glass";
        d.textContent = "3D 场景不可用：" + e.message;
        root.appendChild(d);
      });
  }
}
customElements.define("scene-3d", Scene3D);
