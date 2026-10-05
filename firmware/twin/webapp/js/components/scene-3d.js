// firmware/twin/webapp/js/components/scene-3d.js — <scene-3d> 3D 舞台容器 (M4)
// 组件只是 canvas 壳: 内核 three 场景/装配/热点/流光全在 ../scene.js (动态 import,
// 惰性加载语义保持)。WebGL/装配失败 → 优雅降级卡, 其余抽屉仍可用 (spec §6)。
// 属性契约: onPartClick(h) —— 拾取回调 (twin-app 注入, 转发 <hotspot-card>)。
// 注: canvas 包一层 <div id="t2_sceneView"> —— scene.js resize 用 canvas.parentElement
// 量尺寸, 影子根的直接子元素 parentElement 为 null, 包壳后内核零改动。
// D4: 连接提示 chip —— 点击器件/部件后 scene.js 派发 "t2-conn" {name, counts},
// 此处显示器件名 + 三类连接计数 (气动青/电气琥珀/机械铜, spec §5 点击高亮语义)。
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
        padding:24px;z-index:8}
      #t2_connChip{position:absolute;left:14px;bottom:14px;z-index:7;padding:8px 12px;
        border-radius:10px;font:12px/1.5 system-ui;color:#e8ecf4;
        background:rgba(20,26,38,.72);backdrop-filter:blur(14px);
        border:1px solid rgba(255,255,255,.14);max-width:340px;
        opacity:0;transform:translateY(6px);transition:opacity .18s,transform .18s;
        pointer-events:none}
      #t2_connChip.on{opacity:1;transform:none}
      #t2_connChip .t2_connName{font-weight:600;letter-spacing:.02em}
      #t2_connChip .t2_connCnt{margin-right:10px;white-space:nowrap}
      #t2_connChip i{display:inline-block;width:8px;height:8px;border-radius:50%;
        margin-right:5px}
    `);
    root.innerHTML = `<div id="t2_sceneView"><canvas id="t2_canvas"></canvas></div>
      <div id="t2_connChip" hidden></div>`;
    window.addEventListener("t2-conn", (ev) => {
      const chip = root.getElementById("t2_connChip");
      const d = ev.detail || {};
      if (!d.counts) {                            // 空白/板内器件: 复位隐藏
        chip.classList.remove("on");
        chip.hidden = true;
        return;
      }
      chip.innerHTML = `<span class="t2_connName">${d.name || d.query}</span><br>`
        + `<span class="t2_connCnt"><i style="background:#6ad4ff"></i>气动 ${d.counts.pneumatic || 0}</span>`
        + `<span class="t2_connCnt"><i style="background:#ffd27a"></i>电气 ${d.counts.electrical || 0}</span>`
        + `<span class="t2_connCnt"><i style="background:#c9a06a"></i>机械 ${d.counts.mechanical || 0}</span>`
        + (d.hit ? `<span style="opacity:.65">(渲染 ${d.hit} 条)</span>` : "");
      chip.hidden = false;
      requestAnimationFrame(() => chip.classList.add("on"));
    });
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
