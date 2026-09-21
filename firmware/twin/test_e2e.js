#!/usr/bin/env node
/**
 * test_e2e.js — gui.html 功能测试（端到端，真实浏览器）
 *
 * 场景：页面加载(面板齐全+0 JS 错误) → 充气(活塞/叶轮/气流/气球/曲线) → 保压(密封定格)
 *       → 释放 → 抽气 → 端口卡片单口动作 → Scheduler 播放/停止 → 刷新恢复。
 * 前置：① server.py 已运行  ② playwright-core 可 require（NODE_PATH 或就地 npm i）
 * 用法：NODE_PATH=/tmp/pwtest/node_modules node test_e2e.js
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

(async () => {
  const b = await pw.chromium.launch({ executablePath: CHROME, headless: true });
  const p = await b.newPage({ viewport: { width: 1680, height: 1050 } });
  const errs = [];
  p.on('pageerror', e => errs.push(e.message));
  p.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });

  const snap = () => p.evaluate(() => ({
    flows: document.querySelectorAll('#flowg path').length,
    bal: [0, 1, 2].map(i => document.getElementById('bal' + i).style.transform),
    pistons: [1, 2, 3, 6].map(i => document.getElementById('pn' + i).classList.contains('on')),
    imp: document.getElementById('imp').classList.contains('on'),
    gauge: document.getElementById('gval').textContent,
    cl: document.getElementById('tbcl').textContent,
  }));

  console.log('─ 功能：页面加载 ─');
  await p.goto('http://127.0.0.1:8000/gui', { waitUntil: 'load' });
  await p.waitForTimeout(1200);
  const load = await p.evaluate(() => ({
    cards: document.getElementById('pcards').childElementCount,
    rows: document.getElementById('schedbody').childElementCount,
    log: document.getElementById('devlog').childElementCount,
    chart: !!document.querySelector('#chart canvas'),
    pistons: [1, 7].every(i => document.getElementById('pn' + i) !== null),
    gaugeOk: document.getElementById('gval') !== null,
  }));
  T('5 张端口卡片', load.cards === 5);
  T('Scheduler 默认 4 行', load.rows === 4);
  T('日志已启动(≥2 行)', load.log >= 2);
  T('ECharts 已渲染 canvas', load.chart);
  T('SVG 7 活塞+压力表就位', load.pistons && load.gaugeOk);
  T('加载无 JS 错误', errs.length === 0);

  console.log('─ 功能：充气 ─');
  await p.evaluate(() => send('S 31'));
  await p.waitForTimeout(300);
  await p.click('text=▶ 充气');
  await p.waitForTimeout(1400);
  let s = await snap();
  T('端口阀1-3+进气阀 导通', s.pistons.every(Boolean));
  T('泵叶轮旋转', s.imp);
  T('全路径气流(干管+泵+3分支=5)', s.flows === 5);
  T('气球长大(>0.5)', parseFloat(s.bal[0].match(/[\d.]+/)[0]) > 0.5);
  const g1 = parseFloat(s.gauge);
  T('压力上升 >20 kPa', g1 > 20);

  console.log('─ 功能：保压 ─');
  await p.click('text=■ 保压');
  await p.waitForTimeout(600);
  s = await snap();
  T('气流消失', s.flows === 0);
  T('泵停', !s.imp);
  const balHold = s.bal[0];
  T('气球密封定格(不回落)', balHold !== 'scale(0.450)');

  console.log('─ 功能：释放 ─');
  await p.click('text=↗ 释放');
  await p.waitForTimeout(900);
  s = await snap();
  T('释放气流(干路+3分支=4)', s.flows === 4);
  T('泵保持停转', !s.imp);
  const g2 = parseFloat(s.gauge);
  T('压力下降', g2 < g1);

  console.log('─ 功能：抽气 ─');
  await p.click('text=▼ 抽气');
  await p.waitForTimeout(700);
  s = await snap();
  T('抽气全程气流(3 分支)', s.flows === 3);
  T('泵运转', s.imp);

  console.log('─ 功能：端口卡片单口动作 ─');
  await p.evaluate(() => send('S 31'));
  await p.waitForTimeout(300);
  await p.click('#pvcard1 .pbtns button:first-child');   /* 端口2 充 */
  await p.waitForTimeout(600);
  const card = await p.evaluate(() => ({
    tag: document.getElementById('pvs1').textContent,
    pn2: document.getElementById('pn2').classList.contains('on'),
    pn1: document.getElementById('pn1').classList.contains('on'),
  }));
  T('端口2 标签→阀开', card.tag === '阀开');
  T('仅 V2 活塞导通(单口掩码)', card.pn2 && !card.pn1);

  console.log('─ 功能：Scheduler 播放/停止 ─');
  await p.evaluate(() => send('S 31'));
  await p.evaluate(() => schedReset());
  await p.click('#schedPlayBtn');
  await p.waitForTimeout(1100);                           /* 行1 @0ms 已执行 */
  const sched = await p.evaluate(() => ({
    r1: document.getElementById('strs0').textContent,
    r2: document.getElementById('strs1').textContent,
    run: document.getElementById('str0').className === 'run',
    flow: document.querySelectorAll('#flowg path').length > 0,
  }));
  T('行1(偏移0)已执行+高亮', sched.r1 === '已执行' && sched.run);
  T('行2(偏移3000)未到点仍待机', sched.r2 === '待机');
  T('序列命令真实驱动气路', sched.flow);
  await p.click('text=■ 停止');
  await p.waitForTimeout(300);
  T('停止后行状态复位', await p.evaluate(() =>
    document.getElementById('strs1').textContent === '待机'));

  console.log('─ 功能：刷新恢复 ─');
  await p.reload({ waitUntil: 'load' });
  await p.waitForTimeout(1000);
  const rl = await p.evaluate(() => ({
    cards: document.getElementById('pcards').childElementCount,
    rows: document.getElementById('schedbody').childElementCount,
    bal: !!document.getElementById('bal0'),
  }));
  T('刷新后布局完整(卡片/行/气球)', rl.cards === 5 && rl.rows === 4 && rl.bal);
  T('全流程无 JS 错误', errs.length === 0);

  await p.evaluate(() => send('S 31'));
  console.log(`\n${fail ? '✗' : '✓'} 功能测试 ${pass}/${pass + fail}`);
  await b.close();
  process.exit(fail ? 1 : 0);
})().catch(e => { console.error('FATAL', e.message); process.exit(1); });
