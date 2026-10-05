// firmware/twin/webapp/js/components/hotspot-card.js — <hotspot-card> 热点卡 (M4, 自 panels.js ③ 迁移)
// 器件热点 live 字段 → 中文名+实时值+迷你横条 (归一满量程 FIELD_MAX, rail_v 取 M3 生成真值);
// 部件级点击 → 提示行。骨架只在切换热点时重建 (200ms live 刷新只改数值/横条,
// 不动 DOM 结构 → 点击不被重建打断)。宿主 .hidden 类控制显隐 (twin-app 影子内定位置)。
// 方法契约: show(h) — h=null 关卡; h.type="hotspot"|"part" (scene.js 拾取返回形状)。
import { store, onState } from "../store.js";
import { FLOWIO_PARAMS } from "../params_gen.js";     // M3: rail_v 等真值 (devices.json 生成物)
import { adopt } from "./styles.js";

// live 字段 → 归一满量程 (迷你横条宽度)
const FIELD_MAX = [
  [/^valves\[\d+\]\.i_A$/, 0.36], [/^valves\[\d+\]\.p_w$/, 1.6],
  [/^rail_5v\.v$/, FLOWIO_PARAMS.rail_v * 1.1], [/^rail_5v\.load_a$/, 3.0], [/^rail_5v\.p_w$/, 16],
  [/^rail_3v3\.v$/, 3.6], [/^rail_3v3\.load_a$/, 0.5], [/^rail_3v3\.buck_eff$/, 1.0],
  [/^temp_est_c\./, 85], [/^uptime_s$/, 3600],
];
function fieldMax(f) { for (const [re, m] of FIELD_MAX) if (re.test(f)) return m; return 0; }
function resolveField(obj, path) {                     // "valves[0].i_A" → 值
  return String(path).replace(/\[(\d+)\]/g, ".$1").split(".")
    .reduce((o, k) => (o == null ? o : o[k]), obj);
}

class HotspotCard extends HTMLElement {
  connectedCallback() {
    if (this._booted) return;
    this._booted = true;
    this._hotspot = null;
    const root = this.attachShadow({ mode: "open" });
    adopt(root, `:host{padding:16px}
      :host h4{font-weight:600;font-size:14px;margin-bottom:2px}`);
    onState(() => { if (this._hotspot) this._updateValues(); });
  }
  show(h) {
    const root = this.shadowRoot;
    const changed = !h || h !== this._hotspot;
    this._hotspot = h || null;
    if (!h) { this.classList.add("hidden"); return; }
    this.classList.remove("hidden");
    if (!changed) { this._updateValues(); return; }    // 200ms 刷新不重建骨架
    if (h.type === "hotspot") {
      root.innerHTML = `<button class="t2_hsClose" id="t2_hsClose">✕</button>
        <h4>${h.name}</h4><div class="t2_hsRef">${h.ref} · 器件</div>
        ${(h.live || []).map((lv, i) => `
          <div class="t2_hsRow"><span>${lv.label}</span>
            <b class="t2_num" id="t2_hv_${i}">—</b></div>
          <div class="t2_hsBar"><i id="t2_hb_${i}" style="width:0%"></i></div>`).join("")}`;
    } else {
      root.innerHTML = `<button class="t2_hsClose" id="t2_hsClose">✕</button>
        <h4>${h.name}</h4><div class="t2_hsRef">${h.partId} · 部件</div>
        <div class="t2_hsRow"><span>拖动滑杆爆炸查看内部</span></div>`;
    }
    root.getElementById("t2_hsClose").onclick = () => this.show(null);
    this._updateValues();
  }
  _updateValues() {
    const h = this._hotspot;
    if (!h || h.type !== "hotspot") return;
    const root = this.shadowRoot;
    (h.live || []).forEach((lv, i) => {
      const raw = resolveField(store.telemetry, lv.field);
      const isEff = lv.field === "rail_3v3.buck_eff";
      const v = typeof raw === "number" ? (isEff ? raw * 100 : raw) : NaN;
      const el = root.getElementById("t2_hv_" + i), bar = root.getElementById("t2_hb_" + i);
      if (el) el.textContent = (isFinite(v)
        ? (isEff ? v.toFixed(1) : v.toFixed(3).replace(/\.?0+$/, "")) : "—") + " " + (lv.unit || "");
      if (bar) {
        const m = fieldMax(lv.field);
        bar.style.width = (isFinite(raw) && m ? Math.max(0.02, Math.min(1, raw / m)) * 100 : 0).toFixed(0) + "%";
      }
    });
  }
}
customElements.define("hotspot-card", HotspotCard);
