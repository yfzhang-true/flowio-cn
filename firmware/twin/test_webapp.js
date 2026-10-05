#!/usr/bin/env node
/**
 * test_webapp.js — v2 webapp 前端全链测试（playwright 无头，静态回调）
 *
 * M4 组件化语义迁移（2026-10-03, spec D2=B）: webapp 重写为 Custom Elements +
 * shadow DOM（<twin-app> 组件树）后，47 条断言逐一映射到组件 DOM —— 原则:
 *   · 断言语义零弱化（滑条值/命令行/双体装配数/bbox 位移等逐字保持）;
 *   · 仅选择器适配: document.getElementById → window.__t2.dom.byId（影子根深穿
 *     查询, js/dom.js 提供 —— playwright pierce 模式的页内等价物）; 复合后代
 *     选择器去掉跨影前缀（如 '#t2_ctrlDrawer .t2_seg' → '.t2_seg', 唯一性不变）;
 *   · 原 id 全部保留在各组件影子/宿主上（t2_pwmVac/t2_explodeRange/t2_hv_*…）。
 * 新增「组件契约」节 7 条: 定义齐全 / open shadowRoot / 组装树 / 属性反映 /
 * pwm-change / 标签联动 / valve-cmd→cmd-line 组装。合计 47+8=55（迁移 47 零弱化 + 组件契约 8）。
 *
 * 对象: / (webapp 零构建 ES Modules) 的 3D 场景 / 流光粒子 / 抽屉 / 热点卡 / 仿真浮层。
 * 方法: 经 window.__t2={scene,flows,panels,simlab,dom,ble} 调试钩读渲染态（uniforms/粒子
 *       相位/爆炸位移），真实 CLI 命令驱动固件 DLL 后由 200ms 遥测管道回流断言；控制命令用
 *       patch fetch 采集（POST 拦截、GET 透传保持遥测存活）；热点卡用相机投影 U3 中心
 *       真实鼠标点击（raycaster 实证）；/classic 旧版可达性收尾。
 * CLI 语义注意: S=确定性关阀（R 不清 duty，用例避免依赖 R）。
 * 前置: ① server.py 已运行（http://127.0.0.1:8017，bash run_tests.sh 或手动）
 *       ② playwright-core 可 require（NODE_PATH 或就地 node_modules）
 * 用法: node test_webapp.js
 */
'use strict';
let pw;
try { pw = require('playwright-core'); }
catch (e) {
  console.log('SKIP: 需要 playwright-core（npm i playwright-core 或设 NODE_PATH）');
  process.exit(2);
}
const fs = require('fs');
const CHROME = process.env.TWIN_CHROME ||
  'C:\\Users\\yuefe\\AppData\\Local\\ms-playwright\\chromium-1200\\chrome-win64\\chrome.exe';
if (!fs.existsSync(CHROME)) { console.log('SKIP: 未找到 Chromium，可用 TWIN_CHROME 指定路径'); process.exit(2); }

let pass = 0, fail = 0;
function T(name, cond) {
  if (cond) { ++pass; console.log('  ✓ ' + name); }
  else { ++fail; console.log('  ✗ ' + name); }
}
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const cmd = (p, line) => p.evaluate((l) => window.__t2.panels.sendCmd(l), line);

(async () => {
  const BASE = 'http://127.0.0.1:8017';
  const b = await pw.chromium.launch({ executablePath: CHROME, headless: true });
  const p = await b.newPage({ viewport: { width: 1680, height: 1050 } });
  const errs = [];
  p.on('pageerror', (e) => errs.push(e.message));
  /* 越域仿真 400 会记 "Failed to load resource" 网络日志——预期产物，过滤之 */
  p.on('console', (m) => {
    if (m.type() === 'error' && !m.text().startsWith('Failed to load resource')) errs.push(m.text());
  });
  try {
    await p.goto(BASE + '/', { waitUntil: 'load', timeout: 10000 });
  } catch (e) {
    console.log('SKIP: 测试服务未启动。先运行 bash run_tests.sh（或在 8017 端口启动 server.py）');
    await b.close();
    process.exit(2);
  }
  /* 等场景+流光装配完成 (STL 并行加载), 再等装配叙事 1.5s 收敛 */
  try {
    await p.waitForFunction(() => window.__t2 && window.__t2.scene && window.__t2.flows
      && window.__t2.scene.parts.length > 0, null, { timeout: 20000 });
  } catch (e) {
    console.log('FATAL: 场景装配超时（__t2 不可用）: ' + (await p.evaluate(() => ({
      t2: !!window.__t2, keys: window.__t2 ? Object.keys(window.__t2).join(',') : '-',
      fail: (window.__t2 && window.__t2.dom
        ? window.__t2.dom.q('#t2_stage .t2_glass') : null) || '' }).fail)));
    await b.close();
    process.exit(1);
  }
  await p.evaluate(() => fetch('/api/reset', { method: 'POST' }));
  await sleep(2600);                                     // 装配叙事 1.5s + 首轮遥测

  console.log('─ 加载：场景/流光装配 ─');
  const load = await p.evaluate(() => {
    const D = window.__t2.dom;                           // 影子深穿查询 (M4)
    const sc = window.__t2.scene, fl = window.__t2.flows;
    return {
      parts: sc.parts.length,
      partIds: sc.parts.map((x) => x.id),
      assembled: sc.parts.every((x) => x.mesh.position.length() < 3),   // 叙事收敛回 0
      hotspots: sc.hotspots.length,
      lines: Object.keys(fl.lines).length,
      airs: fl.airs.length,
      particles: fl.airs.every((a) => a.points.geometry.attributes.position.count === 50),
      calBadge: D.byId('t2_calBadge').textContent.includes('未本机标定'),
      staleHidden: D.byId('t2_staleBadge').hidden,
      tlmCollapsed: D.byId('t2_tlmDrawer').classList.contains('collapsed'),
    };
  });
  T('10 部件 STL 装配在场 (T6 双体: 主6+泵4)', load.parts === 10
    && ['manifold', 'pcb', 'pump', 'tubes'].every((id) => load.partIds.includes(id)));
  T('装配叙事收敛 (部件位移<3mm)', load.assembled);
  T('热点器件 6 个 (hotspots.json)', load.hotspots === 6);
  T('电流线 16 条 (4 电源 + 12 栅极: 8通道+S/V/F/泵)', load.lines === 16);
  T('气流端口 12 组 × 50 粒 (β 8通道+S/V/F+测)', load.airs === 12 && load.particles);
  T('状态行: 未标定黄徽常驻 / stale 隐藏', load.calBadge && load.staleHidden);
  T('遥测抽屉默认收起 (spec §2)', load.tlmCollapsed);

  console.log('─ 爆炸滑杆 ─');
  await p.evaluate(() => window.__t2.scene.setExplode(1));
  await sleep(900);
  const expl = await p.evaluate(() => {
    const sc = window.__t2.scene;
    const maxD = Math.max(...sc.parts.map((x) => x.mesh.position.length()));
    const pcb = sc.parts.find((x) => x.id === "pcb").mesh;
    return { maxD, k: sc.explode,
             flowsFollow: window.__t2.flows.group.position.distanceTo(pcb.position) < 0.5 };
  });
  T('setExplode(1) → 部件位移>10mm', expl.maxD > 10);
  T('爆炸系数平滑跟随 (k≈1)', expl.k > 0.9);
  T('流组每帧复制 pcb 位移 (端点绑定不断线)', expl.flowsFollow);
  const slider = await p.evaluate(() => {
    const D = window.__t2.dom;
    const r = D.byId('t2_explodeRange');
    r.value = '0.5';
    r.dispatchEvent(new Event('input', { bubbles: true }));
    return { label: D.byId('t2_explodeVal').textContent };
  });
  T('滑杆 input → 百分比标签联动 (50%)', slider.label === '50%');
  await p.evaluate(() => window.__t2.scene.setExplode(0));
  await sleep(700);

  console.log('─ 气流+电流联动: I 1 255 (充气) ─');
  await cmd(p, 'I 1 255');
  await sleep(1400);                                     // 200ms 交替轮询 + 增益平滑
  /* 首条遥测断言宽限重试: 冷启动后首轮 200ms 遥测偶发未及回流 (增益平滑未爬坡,
     质量审实证过一次 1 红) —— 阈值不放宽, 仅重读 ≤2 次 × 400ms 等遥测管道。 */
  const readFlow = () => {
    const fl = window.__t2.flows;
    const g1 = fl.lines.gate1, a1 = fl.airs[0];
    return {
      live01: g1.live01,
      uGain: g1.uniforms.uGain.value,
      uSpeed: g1.uniforms.uSpeed.value,
      op: a1.op,
      matOp: a1.points.material.opacity,
      col: a1.mat.color.getHex(),
      dir: a1.dir,
      otherOp: fl.airs[1].op,
    };
  };
  let on = await p.evaluate(readFlow);
  for (let i = 0; i < 2 && !(on.live01 > 0.5); i++) {
    await sleep(400);
    on = await p.evaluate(readFlow);
  }
  T('gate1 live01=阀电流归一 (>0.5)', on.live01 > 0.5);
  T('gate1 uGain>0.5 (电流辉光)', on.uGain > 0.5);
  T('gate1 uSpeed>1.5 (行进虚线加速)', on.uSpeed > 1.5);
  T('port1 粒子可见 (op>0.3)', on.op > 0.3 && on.matOp > 0.3);
  T('其余端口静默 (port2 op≈0)', on.otherOp < 0.05);
  T('正压配色 青 0x6ad4ff / 方向 +1', on.col === 0x6ad4ff && on.dir === 1);
  const drift = await p.evaluate(async () => {
    const a1 = window.__t2.flows.airs[0];
    const s0 = a1.points.geometry.attributes.position.array.slice(0, 6);
    await new Promise((r) => setTimeout(r, 300));
    const s1 = a1.points.geometry.attributes.position.array.slice(0, 6);
    let moved = false;
    for (let i = 0; i < 6; i++) if (Math.abs(s1[i] - s0[i]) > 0.05) moved = true;
    return moved;
  });
  T('粒子沿曲线行进 (300ms 内位移)', drift);

  console.log('─ S 1 静默对比 (确定性关阀) ─');
  await cmd(p, 'S 1');
  await sleep(1200);
  const off = await p.evaluate(() => {
    const fl = window.__t2.flows;
    return { uGain: fl.lines.gate1.uniforms.uGain.value, op: fl.airs[0].op };
  });
  T('S 1 → gate1 回落底光 (uGain<0.35)', off.uGain < 0.35);
  T('S 1 → port1 粒子淡出 (op<0.05)', off.op < 0.05);

  console.log('─ 真空: V 1 255 (压力符号→粒子反向) ─');
  await cmd(p, 'V 1 255');
  /* 端口线残余正压需被泵抽穿零点 (≈-33 kPa/s) → 轮询压力符号翻转而非定长等待 */
  try {
    await p.waitForFunction(() => window.__t2.flows.state.pressureSign === -1,
      null, { timeout: 10000 });
  } catch (e) { /* 超时则落入下方断言报 ✗ */ }
  await sleep(600);                                      // 等颜色/方向平滑切换
  const vac = await p.evaluate(async () => {
    const fl = window.__t2.flows;
    const a1 = fl.airs[0];
    const ph0 = a1.phase[0];
    await new Promise((r) => setTimeout(r, 250));
    const d = ((a1.phase[0] - ph0) % 1 + 1) % 1;         // (0,0.5)=正向 (0.5,1)=反向
    return { dir: a1.dir, col: a1.mat.color.getHex(), op: a1.op, d, sign: fl.state.pressureSign };
  });
  T('真空压力符号 → dir=-1', vac.dir === -1 && vac.sign === -1);
  T('真空配色 琥珀 0xffb454', vac.col === 0xffb454);
  T('真空粒子可见 (op>0.3)', vac.op > 0.3);
  T('粒子相位递减 (t 逆向行进)', vac.d > 0.5);
  await cmd(p, 'S 1');
  await sleep(400);

  console.log('─ 抽屉开合 ─');
  const drw = await p.evaluate(() => {
    const D = window.__t2.dom;                           // 影子深穿 (M4 选择器适配)
    const out = {};
    const tlm = D.byId('t2_tlmDrawer');
    const tab = D.byId('t2_tlmTab');
    out.tabVisible = !tab.hidden;
    tab.click();
    out.tlmOpen = !tlm.classList.contains('collapsed') && tab.hidden;
    out.sparks = D.qa('#t2_tlmCards .t2_spark').length;
    D.byId('t2_tlmCollapse').click();
    out.tlmClosed = tlm.classList.contains('collapsed') && !tab.hidden;
    const ctrl = D.byId('t2_ctrlDrawer');
    D.byId('t2_ctrlCollapse').click();
    out.ctrlClosed = ctrl.classList.contains('collapsed');
    D.byId('t2_ctrlTab').click();
    out.ctrlReopen = !ctrl.classList.contains('collapsed');
    return out;
  });
  T('遥测浮钮可见 (默认收起) → 点击展开', drw.tabVisible && drw.tlmOpen);
  T('遥测抽屉 5 张 sparkline 卡', drw.sparks === 5);
  T('遥测/控制抽屉 收起↔展开 往返', drw.tlmClosed && drw.ctrlClosed && drw.ctrlReopen);

  console.log('─ 控制命令通道 (fetch 拦截): 双 PWM 滑条 ─');
  const ctrl = await p.evaluate(async () => {
    const log = [];
    const orig = window.fetch;
    window.fetch = (url, opts) => {
      if (opts && opts.method === 'POST') {
        log.push({ url, body: opts.body });
        return Promise.resolve({ ok: true, json: async () => ({ ok: true }) });
      }
      return orig(url, opts);                            // GET 透传 → 遥测管道存活
    };
    try {
      const D = window.__t2.dom;
      const q = (sel) => D.q(sel);
      // 双 PWM 滑条在场 (对齐官方 GUI 参考: Inflation/Vacuum 两档; M4 迁入 <dual-pump-pwm>)
      const dualSliders = !!(q('#t2_pwmInfl') && q('#t2_pwmVac'));
      // 复合选择器去 '#t2_ctrlDrawer ' 前缀 —— .t2_seg[data-port] 在 <channel-row>
      // (端口行) 或 <control-drawer> (全局行) 影子内, data-port 全局唯一
      q('.t2_seg[data-port="0"] button[data-cmd="I"]').click();        // 阀1 充 (默认 255)
      await new Promise((r) => setTimeout(r, 60));
      q('#t2_pwmVac').value = '200';                                   // 真空档 200
      q('.t2_seg[data-port="g"] button[data-cmd="V"]').click();        // 全局 抽
      await new Promise((r) => setTimeout(r, 60));
      q('#t2_pwmInfl').value = '208';                                  // 充气档 208 (官方参考截图同值)
      q('.t2_seg[data-port="0"] button[data-cmd="I"]').click();        // 阀1 充
      await new Promise((r) => setTimeout(r, 60));
      q('.t2_seg[data-port="2"] button[data-cmd="S"]').click();        // 阀3 释
      await new Promise((r) => setTimeout(r, 60));
      q('.t2_ctrlFoot button[data-line="T"]').click();                 // 状态字
      await new Promise((r) => setTimeout(r, 60));
      // 滑条 input → 数值标签联动 (拖动即时反馈)
      q('#t2_pwmVac').value = '180';
      q('#t2_pwmVac').dispatchEvent(new Event('input', { bubbles: true }));
      const vacLabel = q('#t2_pwmVacVal').textContent;
      return { dualSliders, vacLabel, cmds: log.map((x) => x.url + ' ' + x.body) };
    } finally { window.fetch = orig; }
  });
  const ctrlCmds = ctrl.cmds;
  T('双 PWM 滑条在场 (充气 #t2_pwmInfl / 真空 #t2_pwmVac)', ctrl.dualSliders);
  T('滑条 input → 数值标签联动 (真空 180)', ctrl.vacLabel === '180');
  T('阀1 充(默认充气档) → POST /api/cmd "I 1 255"', ctrlCmds[0] === '/api/cmd I 1 255');
  T('真空滑杆并入 V 命令 (全局抽 → "V 31 200")', ctrlCmds[1] === '/api/cmd V 31 200');
  T('充气滑杆独立调档 (→ "I 1 208")', ctrlCmds[2] === '/api/cmd I 1 208');
  T('阀3 释 → "S 4" (确定性关阀掩码)', ctrlCmds[3] === '/api/cmd S 4');
  T('脚部按钮 状态字 → "T"', ctrlCmds[4] === '/api/cmd T');

  console.log('─ 热点卡: U3 中心真实点击 (raycaster) ─');
  const pt = await p.evaluate(() => {
    const sc = window.__t2.scene;
    const hs = sc.hotspots.find((h) => h.ref === 'U3');
    const cam = sc.camera;
    const V3 = cam.position.constructor;                 // 借 Vector3 构造器做投影
    const v = new V3(hs.center[0], hs.center[1], hs.center[2]);
    v.applyMatrix4(cam.matrixWorldInverse).applyMatrix4(cam.projectionMatrix);  // Vector3 已含透视除法
    const r = window.__t2.dom.byId('t2_canvas').getBoundingClientRect();
    return { x: r.left + ((v.x + 1) / 2) * r.width,
             y: r.top + ((1 - v.y) / 2) * r.height };
  });
  await p.mouse.click(pt.x, pt.y);
  await sleep(700);                                      // 等 200ms live 刷新填充数值
  const card = await p.evaluate(() => {
    const D = window.__t2.dom;
    const c = D.byId('t2_hotspotCard');                  // <hotspot-card> 宿主
    const vals = D.sub(c, '[id^=t2_hv_]').map((e) => e.textContent);   // 穿入其影子根
    return {
      visible: !c.classList.contains('hidden'),
      ref: c.shadowRoot.textContent.includes('U3'),    // 宿主 textContent 不含影子内容 (M4 适配)
      live: vals.length > 0 && vals.every((t) => t && t !== '—'),
      bars: D.qa('.t2_hsBar i').length,
    };
  });
  T('U3 点击 → 热点卡出现 (ref+器件)', card.visible && card.ref);
  T('热点卡 live 值全部填充 (非 —)', card.live);
  T('热点卡迷你横条渲染', card.bars > 0);
  T('热点卡 ✕ 关闭', await p.evaluate(() => {
    const D = window.__t2.dom;
    D.byId('t2_hsClose').click();
    return D.byId('t2_hotspotCard').classList.contains('hidden');
  }));

  console.log('─ 仿真实验室浮层 ─');
  await p.evaluate(() => window.__t2.simlab.open());
  await sleep(1400);                                     // presets + buck 首算
  const sim = await p.evaluate(() => {
    const D = window.__t2.dom;
    return {
      open: !D.byId('t2_simOverlay').hidden,             // <sim-lab> 宿主
      cards: D.qa('.t2_simCard').length,
      inputs: D.qa('#t2_simForm input').length,
      rows: D.qa('#t2_simMets tr').length,
      canvas: !!D.q('#t2_simWave'),
      errHidden: D.byId('t2_simErr').hidden,
    };
  });
  T('浮层升起 (非 hidden)', sim.open);
  T('四电路选择卡', sim.cards === 4);
  T('presets 动态表单 (buck 参数)', sim.inputs >= 6);
  T('自动重算指标表 + 波形 canvas', sim.rows > 0 && sim.canvas && sim.errHidden);
  const sim400 = await p.evaluate(async () => {
    const D = window.__t2.dom;
    const inp = D.q('#t2_simForm input[data-p=vin]');
    inp.value = '9';                                     // 越域 [3.8,5.5]
    await window.__t2.simlab.run();
    const bad = {
      visible: !D.byId('t2_simErr').hidden,
      text: D.byId('t2_simErr').textContent,
      btnOk: !D.byId('t2_simRun').disabled,
    };
    inp.value = '5';
    await window.__t2.simlab.run();
    bad.recovered = D.qa('#t2_simMets tr').length > 0
      && D.byId('t2_simErr').hidden;
    return bad;
  });
  T('参数越域 → 400 红条含 vin', sim400.visible && sim400.text.includes('vin'));
  T('修正参数后指标回归 (红条收敛)', sim400.btnOk && sim400.recovered);
  T('ESC 关闭浮层', await p.evaluate(() => {
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
    return window.__t2.dom.byId('t2_simOverlay').hidden;
  }));

  console.log('─ 组件契约 (M4 新增) ─');
  const CONTRACT_TAGS = ['twin-app', 'top-bar', 'scene-3d', 'control-drawer', 'dual-pump-pwm',
    'channel-row', 'telemetry-panel', 'transport-pill', 'hotspot-card', 'status-bar', 'sim-lab'];
  const contract = await p.evaluate((tags) => {
    const D = window.__t2.dom;
    const app = D.q('twin-app');
    return {
      defined: tags.every((t) => !!customElements.get(t)),
      shadows: tags.every((t) => { const el = D.q(t);
        return el && el.shadowRoot && el.shadowRoot.mode === 'open'; }),
      compose: ['top-bar', 'scene-3d', 'control-drawer', 'transport-pill', 'telemetry-panel',
        'hotspot-card', 'status-bar', 'sim-lab']
        .every((t) => !!(app && app.shadowRoot && app.shadowRoot.querySelector(t))),
      rows8: D.qa('channel-row').length === 8,
      attrReflect: (() => { const r = D.qa('channel-row')[3];
        return !!r && r.getAttribute('port') === '3'
          && r.shadowRoot.querySelector('.nm').textContent === '阀4·端口'
          && !!r.shadowRoot.getElementById('t2_vd_3'); })(),
    };
  }, CONTRACT_TAGS);
  T('11 组件 customElements 定义齐全', contract.defined);
  T('组件均挂 open shadowRoot (样式封装)', contract.shadows);
  T('twin-app 组装 8 子组件 (布局树完整)', contract.compose);
  T('8 通道 <channel-row> 在场', contract.rows8);
  T('channel-row 属性反映 (port/name → 影内 DOM)', contract.attrReflect);
  const pwmEvt = await p.evaluate(() => new Promise((res) => {
    const got = [];
    const h = (ev) => got.push({ kind: ev.detail.kind, value: ev.detail.value });
    document.addEventListener('pwm-change', h);         // composed 事件穿影达 document
    const D = window.__t2.dom;
    const r = D.byId('t2_pwmInfl');
    r.value = '208';
    r.dispatchEvent(new Event('input', { bubbles: true }));
    setTimeout(() => {
      document.removeEventListener('pwm-change', h);
      res({ got, label: D.byId('t2_pwmInflVal').textContent });
    }, 80);
  }));
  T('dual-pump-pwm 发 pwm-change {kind,value} (穿影达 document)',
    pwmEvt.got.length === 1 && pwmEvt.got[0].kind === 'infl' && pwmEvt.got[0].value === 208);
  T('pwm-change 伴标签联动 (充气 208)', pwmEvt.label === '208');
  const cmdEvt = await p.evaluate(() => new Promise((res) => {
    const D = window.__t2.dom;
    D.byId('t2_pwmInfl').value = '255';                 // 复位充气档, 断言默认值路径
    const lines = [];
    const h = (ev) => lines.push(ev.detail.line);
    document.addEventListener('cmd-line', h);
    D.q('.t2_seg[data-port="3"] button[data-cmd="H"]').click();   // 阀4 保
    D.q('.t2_seg[data-port="0"] button[data-cmd="I"]').click();   // 阀1 充
    setTimeout(() => { document.removeEventListener('cmd-line', h); res(lines); }, 80);
  }));
  T('channel-row valve-cmd → control-drawer 组装 cmd-line (掩码+PWM 档)',
    cmdEvt[0] === 'H 8' && cmdEvt[1] === 'I 1 255');

  console.log('─ /classic 旧版可达 ─');
  await p.goto(BASE + '/classic', { waitUntil: 'load', timeout: 8000 });
  await sleep(1000);
  const cls = await p.evaluate(() => ({
    cards: document.getElementById('pcards').childElementCount,
    gui: !!document.getElementById('flowg'),
  }));
  T('/classic 旧 gui 挂载 (5 端口卡片 + 气路 SVG)', cls.cards === 5 && cls.gui);

  T('全程无页面 JS 错误', errs.length === 0);
  if (errs.length) console.log('  错误: ' + errs.join(' | '));
  console.log(`\n${fail ? '✗' : '✓'} v2 webapp 测试 ${pass}/${pass + fail} (47 迁移 + ${pass + fail - 47} 组件契约)`);
  await b.close();
  process.exit(fail ? 1 : 0);
})().catch((e) => { console.error('FATAL', e.message); process.exit(1); });
