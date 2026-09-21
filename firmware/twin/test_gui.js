#!/usr/bin/env node
/**
 * test_gui.js — gui.html 前端单元测试
 *
 * 方法：在真实页面上下文（playwright page.evaluate，静态回调，无动态执行）里
 *       对页面内的函数级单元做输入→输出断言：
 *       buildFlowPaths / balloonScale / togglePort / updRow / sched 行操作 /
 *       schedPlay 计时器编排（patch setTimeout 采集，不真跑）/ send+simInject 请求体
 * 前置：① server.py 已运行（http://127.0.0.1:8000）
 *       ② playwright-core 可 require（NODE_PATH=<其 node_modules 路径> 或就地 npm i）
 * 用法：NODE_PATH=/tmp/pwtest/node_modules node test_gui.js
 */
'use strict';
let pw;
try { pw = require('playwright-core'); }
catch (e) {
  console.log('SKIP: 需要 playwright-core（npm i playwright-core 或设 NODE_PATH）');
  process.exit(2);
}
const fs = require('fs');
const path = require('path');

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
  const p = await b.newPage();
  const errs = [];
  p.on('pageerror', e => errs.push(e.message));
  await p.goto('http://127.0.0.1:8000/gui', { waitUntil: 'load' });
  await p.waitForTimeout(900);
  await p.evaluate(() => send('S 31'));           /* 从全关状态起步 */
  await p.waitForTimeout(400);

  console.log('─ 单元：buildFlowPaths 气流路径构建 ─');
  const r1 = await p.evaluate(() => {
    const n = s => (s.match(/<path/g) || []).length;
    return {
      five: n(buildFlowPaths('in', [0, 1, 2])) === 5,
      trunk: buildFlowPaths('in', [0]).includes('M42,300 H272'),
      upToBalloon: buildFlowPaths('in', [0]).includes('V80'),
      noZeroLenH: !buildFlowPaths('in', [2]).includes('H310'),
      closedPortNoBranch: !buildFlowPaths('in', [0, 1, 2]).includes('M415') && !buildFlowPaths('in', [0, 1, 2]).includes('M520,80'),
      vacFull: buildFlowPaths('va', [0]).includes('M100,80 V195 H545 V300 H592'),
      vacNoPort: n(buildFlowPaths('va', [])) === 1,
      rel: n(buildFlowPaths('re', [0, 2])) === 3,
      empty: buildFlowPaths('', [0, 1]) === '',
    };
  });
  T('充气(开1-3)=5 段路径', r1.five);
  T('充气含 大气→泵 干管', r1.trunk);
  T('充气分支上行至气球', r1.upToBalloon);
  T('端口3 正上方不产生零长 H', r1.noZeroLenH);
  T('关闭的端口不出现分支', r1.closedPortNoBranch);
  T('抽气=气球→汇流→排气→大气 全程', r1.vacFull);
  T('抽气无开阀端口→仅汇流干路', r1.vacNoPort);
  T('释放=干路+每开阀分支', r1.rel);
  T('空场景→无路径', r1.empty);

  console.log('─ 单元：balloonScale 气球缩放 ─');
  const r2 = await p.evaluate(() => ({
    zero: Math.abs(balloonScale(0) - 0.45) < 1e-9,
    full: Math.abs(balloonScale(130) - 1) < 1e-9,
    neg: balloonScale(-20) === 0.45,
    over: balloonScale(999) === 1,
    mid: Math.abs(balloonScale(33) - 0.5896) < 0.001,
  }));
  T('0 kPa → 0.45', r2.zero);
  T('130 kPa → 1.0', r2.full);
  T('负压钳 0.45 / 超压钳 1.0', r2.neg && r2.over);
  T('33 kPa → ≈0.590', r2.mid);

  console.log('─ 单元：togglePort 端口掩码 ─');
  const r3 = await p.evaluate(() => {
    const mv = () => document.getElementById('maskv').textContent;
    const out = { init: mv() === '7' };
    togglePort(0); out.off1 = mv() === '6';
    out.cardUnsel = !document.getElementById('pvcard0').classList.contains('sel');
    togglePort(0); out.on1 = mv() === '7';
    togglePort(0); togglePort(1); togglePort(2);
    out.floor = mv() === '4';                      /* 清空兜底保留最后操作的端口3 */
    togglePort(1); togglePort(2);                  /* 恢复 7，不影响后续用例 */
    return out;
  });
  T('初始掩码 7', r3.init);
  T('取消端口1 → 6 + 卡片高亮取消', r3.off1 && r3.cardUnsel);
  T('重选 → 7', r3.on1);
  T('清空后兜底保留 1 个端口', r3.floor);

  console.log('─ 单元：updRow / sched 行编辑 ─');
  const r4 = await p.evaluate(() => {
    const rows = () => document.getElementById('schedbody').innerHTML;
    updRow(0, 't', '500'); updRow(0, 'c', 'G 7 40 0'); renderSched();
    const a = rows().includes('value="500"') && rows().includes('G 7 40 0');
    updRow(0, 't', 'abc');                          /* 非法输入护栏 */
    const guard = true;                             /* 走到这没抛异常即通过 */
    const n0 = (rows().match(/<tr/g) || []).length;
    schedAddRow(); schedAddRow();
    const n2 = (rows().match(/<tr/g) || []).length;
    schedDelRow();
    const n1 = (rows().match(/<tr/g) || []).length;
    schedReset();
    const nr = (rows().match(/<tr/g) || []).length;
    return { a, guard, add: n2 - n0 === 2, del: n1 === n2 - 1, reset: nr === 4 };
  });
  T('偏移/命令写入行', r4.a);
  T('非法偏移不抛异常', r4.guard);
  T('＋行×2 / －行 / ↺复位', r4.add && r4.del && r4.reset);

  console.log('─ 单元：schedPlay 计时器编排（patch setTimeout 采集） ─');
  const r5 = await p.evaluate(() => {
    const rec = [], cleared = [];
    const origSet = window.setTimeout, origClr = window.clearTimeout;
    window.setTimeout = (fn, ms) => { rec.push(ms); return origSet(fn, 1e9); };   /* 不真执行 */
    window.clearTimeout = id => { cleared.push(id); return origClr(id); };
    try {
      schedReset(); schedPlay();                    /* 默认偏移 0/3000/5000/7000 */
      const five = rec.length === 5;
      const offsets = [0, 3000, 5000, 7000].every(ms => rec.includes(ms));
      const doneAt = rec[4] === 7400;
      const btnDis = document.getElementById('schedPlayBtn').disabled === true;
      const n = rec.length;
      schedStopSeq();
      const stopped = cleared.length === n;
      return { five, offsets, doneAt, btnDis, stopped };
    } finally { window.setTimeout = origSet; window.clearTimeout = origClr; }
  });
  T('注册 5 个计时器(4 行+完成)', r5.five);
  T('偏移按行 t 值编排 0/3000/5000/7000', r5.offsets);
  T('完成计时器在末行+400ms', r5.doneAt);
  T('运行中 Play 禁用', r5.btnDis);
  T('Stop 清空全部计时器', r5.stopped);

  console.log('─ 单元：send / simInject 请求体（patch fetch 采集） ─');
  const r6 = await p.evaluate(async () => {
    const log = [];
    const origFetch = window.fetch;
    window.fetch = (url, opts) => { log.push({ url, opts }); return Promise.resolve({ ok: true, json: async () => ({ ok: true }) }); };
    try {
      await send('I 7 255');
      document.getElementById('simIdx').value = '1';
      document.getElementById('simVal').value = '66';
      await simInject();
      const cmd = log.at(-2);
      const sim = log.at(-1);
      return {
        cmd: cmd.url === '/api/cmd' && cmd.opts.method === 'POST' && cmd.opts.body === 'I 7 255',
        sim: sim.url === '/api/sim' && sim.opts.body === '1 66',
      };
    } finally { window.fetch = origFetch; }
  });
  T('POST /api/cmd 原文透传', r6.cmd);
  T('POST /api/sim "1 66"', r6.sim);

  T('全程无页面 JS 错误', errs.length === 0);
  console.log(`\n${fail ? '✗' : '✓'} 单元测试 ${pass}/${pass + fail}`);
  await b.close();
  process.exit(fail ? 1 : 0);
})().catch(e => { console.error('FATAL', e.message); process.exit(1); });
