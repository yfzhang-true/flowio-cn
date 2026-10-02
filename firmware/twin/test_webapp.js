#!/usr/bin/env node
/**
 * test_webapp.js — v2 webapp 前端全链测试（playwright 无头，静态回调）
 *
 * 对象: / (webapp 零构建 ES Modules) 的 3D 场景 / 流光粒子 / 抽屉 / 热点卡 / 仿真浮层。
 * 方法: 经 window.__t2={scene,flows,panels,simlab} 调试钩读渲染态（uniforms/粒子相位/爆炸
 *       位移），真实 CLI 命令驱动固件 DLL 后由 200ms 遥测管道回流断言；控制命令用
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
      fail: (document.querySelector('#t2_stage .t2_glass') || {}).textContent || '' })).fail));
    await b.close();
    process.exit(1);
  }
  await p.evaluate(() => fetch('/api/reset', { method: 'POST' }));
  await sleep(2600);                                     // 装配叙事 1.5s + 首轮遥测

  console.log('─ 加载：场景/流光装配 ─');
  const load = await p.evaluate(() => {
    const sc = window.__t2.scene, fl = window.__t2.flows;
    return {
      parts: sc.parts.length,
      assembled: sc.parts.every((x) => x.mesh.position.length() < 3),   // 叙事收敛回 0
      hotspots: sc.hotspots.length,
      lines: Object.keys(fl.lines).length,
      airs: fl.airs.length,
      particles: fl.airs.every((a) => a.points.geometry.attributes.position.count === 50),
      calBadge: document.getElementById('t2_calBadge').textContent.includes('未本机标定'),
      staleHidden: document.getElementById('t2_staleBadge').hidden,
      tlmCollapsed: document.getElementById('t2_tlmDrawer').classList.contains('collapsed'),
    };
  });
  T('5 部件 STL 装配在场 (__t2.scene.parts)', load.parts === 5);
  T('装配叙事收敛 (部件位移<3mm)', load.assembled);
  T('热点器件 6 个 (hotspots.json)', load.hotspots === 6);
  T('电流线 12 条 (4 电源 + 8 栅极)', load.lines === 12);
  T('气流端口 8 组 × 50 粒', load.airs === 8 && load.particles);
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
    const r = document.getElementById('t2_explodeRange');
    r.value = '0.5';
    r.dispatchEvent(new Event('input', { bubbles: true }));
    return { label: document.getElementById('t2_explodeVal').textContent };
  });
  T('滑杆 input → 百分比标签联动 (50%)', slider.label === '50%');
  await p.evaluate(() => window.__t2.scene.setExplode(0));
  await sleep(700);

  console.log('─ 气流+电流联动: I 1 255 (充气) ─');
  await cmd(p, 'I 1 255');
  await sleep(1400);                                     // 200ms 交替轮询 + 增益平滑
  const on = await p.evaluate(() => {
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
  });
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
    const out = {};
    const tlm = document.getElementById('t2_tlmDrawer');
    const tab = document.getElementById('t2_tlmTab');
    out.tabVisible = !tab.hidden;
    tab.click();
    out.tlmOpen = !tlm.classList.contains('collapsed') && tab.hidden;
    out.sparks = document.querySelectorAll('#t2_tlmCards .t2_spark').length;
    document.getElementById('t2_tlmCollapse').click();
    out.tlmClosed = tlm.classList.contains('collapsed') && !tab.hidden;
    const ctrl = document.getElementById('t2_ctrlDrawer');
    document.getElementById('t2_ctrlCollapse').click();
    out.ctrlClosed = ctrl.classList.contains('collapsed');
    document.getElementById('t2_ctrlTab').click();
    out.ctrlReopen = !ctrl.classList.contains('collapsed');
    return out;
  });
  T('遥测浮钮可见 (默认收起) → 点击展开', drw.tabVisible && drw.tlmOpen);
  T('遥测抽屉 5 张 sparkline 卡', drw.sparks === 5);
  T('遥测/控制抽屉 收起↔展开 往返', drw.tlmClosed && drw.ctrlClosed && drw.ctrlReopen);

  console.log('─ 控制命令通道 (fetch 拦截) ─');
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
      const q = (sel) => document.querySelector(sel);
      q('#t2_ctrlDrawer .t2_seg[data-port="0"] button[data-cmd="I"]').click();   // 阀1 充
      await new Promise((r) => setTimeout(r, 60));
      q('#t2_pwmRange').value = '200';
      q('#t2_ctrlDrawer .t2_seg[data-port="g"] button[data-cmd="V"]').click();   // 全局 抽
      await new Promise((r) => setTimeout(r, 60));
      q('#t2_pwmRange').value = '255';
      q('#t2_ctrlDrawer .t2_seg[data-port="2"] button[data-cmd="S"]').click();   // 阀3 释
      await new Promise((r) => setTimeout(r, 60));
      q('#t2_ctrlDrawer .t2_ctrlFoot button[data-line="T"]').click();           // 状态字
      await new Promise((r) => setTimeout(r, 60));
      return log.map((x) => x.url + ' ' + x.body);
    } finally { window.fetch = orig; }
  });
  T('阀1 充 → POST /api/cmd "I 1 255"', ctrl[0] === '/api/cmd I 1 255');
  T('PWM 滑杆并入命令 (全局抽 → "V 31 200")', ctrl[1] === '/api/cmd V 31 200');
  T('阀3 释 → "S 4" (确定性关阀掩码)', ctrl[2] === '/api/cmd S 4');
  T('脚部按钮 状态字 → "T"', ctrl[3] === '/api/cmd T');

  console.log('─ 热点卡: U3 中心真实点击 (raycaster) ─');
  const pt = await p.evaluate(() => {
    const sc = window.__t2.scene;
    const hs = sc.hotspots.find((h) => h.ref === 'U3');
    const cam = sc.camera;
    const V3 = cam.position.constructor;                 // 借 Vector3 构造器做投影
    const v = new V3(hs.center[0], hs.center[1], hs.center[2]);
    v.applyMatrix4(cam.matrixWorldInverse).applyMatrix4(cam.projectionMatrix);  // Vector3 已含透视除法
    const r = document.getElementById('t2_canvas').getBoundingClientRect();
    return { x: r.left + ((v.x + 1) / 2) * r.width,
             y: r.top + ((1 - v.y) / 2) * r.height };
  });
  await p.mouse.click(pt.x, pt.y);
  await sleep(700);                                      // 等 200ms live 刷新填充数值
  const card = await p.evaluate(() => {
    const c = document.getElementById('t2_hotspotCard');
    const vals = [...c.querySelectorAll('[id^=t2_hv_]')].map((e) => e.textContent);
    return {
      visible: !c.classList.contains('hidden'),
      ref: c.textContent.includes('U3'),
      live: vals.length > 0 && vals.every((t) => t && t !== '—'),
      bars: c.querySelectorAll('#t2_hotspotCard .t2_hsBar i').length,
    };
  });
  T('U3 点击 → 热点卡出现 (ref+器件)', card.visible && card.ref);
  T('热点卡 live 值全部填充 (非 —)', card.live);
  T('热点卡迷你横条渲染', card.bars > 0);
  T('热点卡 ✕ 关闭', await p.evaluate(() => {
    document.getElementById('t2_hsClose').click();
    return document.getElementById('t2_hotspotCard').classList.contains('hidden');
  }));

  console.log('─ 仿真实验室浮层 ─');
  await p.evaluate(() => window.__t2.simlab.open());
  await sleep(1400);                                     // presets + buck 首算
  const sim = await p.evaluate(() => ({
    open: !document.getElementById('t2_simOverlay').hidden,
    cards: document.querySelectorAll('.t2_simCard').length,
    inputs: document.querySelectorAll('#t2_simForm input').length,
    rows: document.querySelectorAll('#t2_simMets tr').length,
    canvas: !!document.querySelector('#t2_simWave'),
    errHidden: document.getElementById('t2_simErr').hidden,
  }));
  T('浮层升起 (非 hidden)', sim.open);
  T('四电路选择卡', sim.cards === 4);
  T('presets 动态表单 (buck 参数)', sim.inputs >= 6);
  T('自动重算指标表 + 波形 canvas', sim.rows > 0 && sim.canvas && sim.errHidden);
  const sim400 = await p.evaluate(async () => {
    const inp = document.querySelector('#t2_simForm input[data-p=vin]');
    inp.value = '9';                                     // 越域 [3.8,5.5]
    await window.__t2.simlab.run();
    const bad = {
      visible: !document.getElementById('t2_simErr').hidden,
      text: document.getElementById('t2_simErr').textContent,
      btnOk: !document.getElementById('t2_simRun').disabled,
    };
    inp.value = '5';
    await window.__t2.simlab.run();
    bad.recovered = document.querySelectorAll('#t2_simMets tr').length > 0
      && document.getElementById('t2_simErr').hidden;
    return bad;
  });
  T('参数越域 → 400 红条含 vin', sim400.visible && sim400.text.includes('vin'));
  T('修正参数后指标回归 (红条收敛)', sim400.btnOk && sim400.recovered);
  T('ESC 关闭浮层', await p.evaluate(() => {
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
    return document.getElementById('t2_simOverlay').hidden;
  }));

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
  console.log(`\n${fail ? '✗' : '✓'} v2 webapp 测试 ${pass}/${pass + fail}`);
  await b.close();
  process.exit(fail ? 1 : 0);
})().catch((e) => { console.error('FATAL', e.message); process.exit(1); });
