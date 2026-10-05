// firmware/twin/webapp/js/components/styles.js — 共享样式表 (M4)
// 选择说明 (任务 §2 "css 按组件拆分或 :host+::slotted" 的裁定):
//   ① 设计令牌 (:root 自定义属性) 留文档级 css/twin.css —— 自定义属性可继承穿透
//      影子边界, 各影子内 var(--accent) 直接可用, 无需复制;
//   ② 跨组件复用的控件规则 (.t2_btn/.t2_seg/.t2_vRow/…) 收进本共享表 —— 同一
//      CSSStyleSheet 实例被多个影子根 adopt (单份内存), 且只作用于 adopt 它的
//      影子内部, 文档层看不见 (封装不破);
//   ③ 布局/定位归口: 面板自身外观用 :host 规则 (组件文件内), 宿主在父影子里的
//      定位 (absolute/折叠 transform) 写在父组件 (twin-app) 的影子里 —— 影子
//      DOM "宿主样式归父" 的正统分工, 全局 css 不再承载任何面板样式。
const SHARED_CSS = `
/* 复位 (原文档级 * 规则不穿影 —— 影内必须自备, 否则 width+padding 撑破面板) */
*{box-sizing:border-box;margin:0}
.t2_glass{background:var(--glass);backdrop-filter:blur(24px) saturate(180%);-webkit-backdrop-filter:blur(24px) saturate(180%);
  border:1px solid var(--hair);border-radius:20px;box-shadow:0 8px 32px rgba(0,0,0,.35)}
.t2_btn{font:inherit;color:var(--txt);background:var(--glass);border:1px solid var(--hair);border-radius:10px;
  padding:6px 14px;cursor:pointer;transition:all .15s var(--ease)}
.t2_btn:hover{background:rgba(255,255,255,.12)} .t2_btn:disabled{opacity:.4;cursor:default}
.t2_btn.ghost{background:transparent}
.t2_btn.rec{color:#ff8177;border-color:rgba(255,95,87,.5)}
.t2_btn.rec::before{content:"";display:inline-block;width:7px;height:7px;border-radius:50%;
  background:#ff5f57;margin-right:6px;vertical-align:0;animation:t2blink 1.2s infinite}
@keyframes t2blink{50%{opacity:.25}}
.t2_num{font-variant-numeric:tabular-nums}
.t2_badge{font-size:12px;padding:3px 10px;border-radius:99px;border:1px solid var(--hair);color:var(--txt2)}
.t2_badge.warn{color:#ffd479;border-color:rgba(255,212,121,.35)}
.t2_badge.err{color:#ff9d96;border-color:rgba(255,95,87,.45);background:rgba(120,20,20,.35)}
.t2_badge.live{color:#c4b5fd;border-color:rgba(139,92,246,.5)}
.t2_dHead{display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;flex:none}
.t2_dHead h3{font-size:13px;font-weight:600;color:var(--txt2);letter-spacing:.08em}
.t2_dHead .t2_btn{font-size:12px;padding:3px 10px}
/* 控制抽屉/通道行共用的分段控件与行布局 */
.t2_pwmRow{display:flex;align-items:center;gap:8px;font-size:12px;color:var(--txt2);margin-bottom:12px}
.t2_pwmRow input[type=range]{flex:1;accent-color:var(--accent);height:14px}
.t2_pwmRow b{color:var(--txt);min-width:28px;text-align:right}
.t2_vRow{display:flex;align-items:center;gap:8px;margin-bottom:8px}
.t2_vRow .nm{font-size:12px;color:var(--txt2);width:62px;flex:none}
.t2_vDot{width:6px;height:6px;border-radius:50%;background:rgba(255,255,255,.16);flex:none;
  transition:background .25s,box-shadow .25s}
.t2_vDot.on{background:var(--air-p);box-shadow:0 0 6px var(--air-p)}
.t2_seg{display:flex;flex:1;background:rgba(0,0,0,.28);border:1px solid var(--hair);border-radius:9px;
  overflow:hidden}
.t2_seg button{flex:1;font:inherit;font-size:12px;color:var(--txt2);background:transparent;border:none;
  border-right:1px solid var(--hair);padding:5px 0;cursor:pointer;transition:all .12s var(--ease)}
.t2_seg button:last-child{border-right:none}
.t2_seg button:hover{color:var(--txt);background:rgba(255,255,255,.06)}
.t2_seg button.hit{background:rgba(106,169,255,.30);color:var(--txt)}
.t2_ctrlFoot{display:flex;gap:6px;margin-top:10px}
.t2_ctrlFoot .t2_btn{flex:1;font-size:12px;padding:5px 0}
/* 遥测小卡 */
.t2_tCard{border:1px solid var(--hair);border-radius:14px;padding:10px 12px;margin-bottom:8px;
  cursor:pointer;transition:background .15s var(--ease),border-color .15s var(--ease)}
.t2_tCard:hover{background:rgba(255,255,255,.08)}
.t2_tCard.on{border-color:rgba(106,169,255,.55)}
.t2_tCardTop{display:flex;justify-content:space-between;align-items:baseline;font-size:12px;color:var(--txt2);margin-bottom:6px}
.t2_tCardTop b{font-size:13px;font-weight:500;color:var(--txt)}
.t2_spark{width:100%;height:34px;display:block}
#t2_tlmExpand{flex:none}
#t2_tlmExpand .t2_tCard{cursor:default}
/* 热点卡 */
.t2_hsClose{position:absolute;top:10px;right:10px;background:transparent;border:none;color:var(--txt2);
  cursor:pointer;font-size:12px;padding:2px 6px;border-radius:6px}
.t2_hsClose:hover{color:var(--txt);background:rgba(255,255,255,.1)}
.t2_hsRef{font-size:11px;color:var(--txt2);margin-bottom:10px;letter-spacing:.04em}
.t2_hsRow{display:flex;justify-content:space-between;align-items:baseline;font-size:12px;color:var(--txt2);padding:5px 0;border-top:1px solid var(--hair)}
.t2_hsRow b{font-variant-numeric:tabular-nums;color:var(--txt);font-weight:500}
.t2_hsBar{height:3px;border-radius:2px;background:rgba(255,255,255,.10);margin:-1px 0 6px;overflow:hidden}
.t2_hsBar i{display:block;height:100%;background:var(--accent);border-radius:2px;transition:width .3s var(--ease)}
/* 运输条 */
.t2_tpDiv{width:1px;height:18px;background:var(--hair);flex:none}
.t2_speed{width:70px;accent-color:var(--accent);flex:none}
.t2_pill input[type=range].t2_explode{width:180px;flex:none}
input[type=range].t2_explode{width:220px;accent-color:var(--accent)}
.t2_explWrap{display:flex;align-items:center;gap:8px;font-size:13px;color:var(--txt2)}
`;

const cache = new Map();
export function sheet(cssText) {
  if (!cache.has(cssText)) {
    const s = new CSSStyleSheet();
    s.replaceSync(cssText);
    cache.set(cssText, s);
  }
  return cache.get(cssText);
}
export const sharedSheet = sheet(SHARED_CSS);
// 影子根样式装配: [共享表, 组件私有表] (私有表同样缓存复用)
export function adopt(root, cssText) {
  root.adoptedStyleSheets = cssText ? [sharedSheet, sheet(cssText)] : [sharedSheet];
  return root;
}
