// firmware/twin/webapp/js/dom.js — shadow DOM 深穿查询 (M4)
// 组件化后 document.getElementById 不再穿透影子根 → 本模块递归遍历 document +
// 所有 open shadowRoot。仅调试钩 (window.__t2.dom) 与 test_webapp 使用;
// 组件内部一律用 this.shadowRoot 就地查询, 不走这条慢路径。
export function allRoots(root = document, out = []) {
  out.push(root);
  for (const el of root.querySelectorAll("*")) if (el.shadowRoot) allRoots(el.shadowRoot, out);
  return out;
}
export function byId(id) {
  for (const r of allRoots()) {
    const el = r.getElementById(id);
    if (el) return el;
  }
  return null;
}
// 联合查询: 对每个 root 独立求值后合并 (选择器不得跨影子边界组合后代,
// 如 "#a .b" 中 a 与 b 分属两层影子 → 改用单层内选择器或 byId+sub)。
export function qa(sel) {
  const out = [];
  for (const r of allRoots()) out.push(...r.querySelectorAll(sel));
  return out;
}
export function q(sel) { return qa(sel)[0] || null; }
// 元素子树查询: 优先穿入其影子根 (host → shadow 内部)
export function sub(el, sel) {
  if (!el) return [];
  return [...(el.shadowRoot || el).querySelectorAll(sel)];
}
