#!/usr/bin/env node
/**
 * test_gui_p1.js — gui.html「P1 板级」前端测试（遥测/仿真/结构 + Web BLE 纯逻辑）
 *
 * 方法：与 test_gui.js 同款 playwright 无头实例（静态回调，无动态执行）：
 *   ① 顶层标签切换与三子面板 DOM/懒加载
 *   ② 遥测：电源树实时值 / 8 阀电流条 / 双轴历史图
 *   ③ 仿真：四电路卡 + presets 动态表单 + 自动重算指标表 + 400 越域红条
 *   ④ 结构：assembly→STL 五部件加载 + 爆炸滑杆位移动画
 *   ⑤ BLE 纯逻辑：CRC-8/0x07、0xA5 帧构造（BLE.md §4.1 向量）、20B state 解析
 *      （§4.2 向量）、双模命令路径 p1_sendCmd（孪生分支截 fetch）、双模渲染入口
 *   ⑥ 无 navigator.bluetooth 环境按钮置灰 + 模式徽章
 * 前置：① server.py 已在 8017 端口运行（bash run_tests.sh 或手动）
 *       ② playwright-core 可 require（NODE_PATH 或就地 npm i）
 * 用法：NODE_PATH=/tmp/pwtest/node_modules node test_gui_p1.js
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
  const BASE = 'http://127.0.0.1:8017';
  const b = await pw.chromium.launch({ executablePath: CHROME, headless: true });
  const p = await b.newPage({ viewport: { width: 1680, height: 1050 } });
  const errs = [];
  p.on('pageerror', e => errs.push(e.message));
  /* 越域仿真用例会得到预期的 400 → 浏览器记 "Failed to load resource" 网络日志，过滤之 */
  p.on('console', m => {
    if (m.type() === 'error' && !m.text().startsWith('Failed to load resource')) errs.push(m.text());
  });
  try {
    await p.goto(BASE + '/classic', { waitUntil: 'load', timeout: 8000 });
  } catch (e) {
    console.log('SKIP: 测试服务未启动。先在 8017 端口启动 server.py（bash run_tests.sh）');
    await b.close();
    process.exit(2);
  }
  await p.waitForTimeout(900);

  console.log('─ 加载：顶层标签与静态结构 ─');
  const load = await p.evaluate(() => ({
    libScripts: document.querySelectorAll('script[src^="/lib/"]').length,
    pneuVisible: document.getElementById('p1_tabpneu').style.display !== 'none',
    p1Hidden: document.getElementById('p1_tabp1').style.display === 'none',
    tabs: ['p1_tabbtnPneu', 'p1_tabbtnP1', 'p1_subbtntel', 'p1_subbtnsim', 'p1_subbtn3d']
      .every(id => document.getElementById(id) !== null),
    panes: ['p1_panetel', 'p1_panesim', 'p1_pane3d', 'p1_histchart', 'p1_valves', 'p1_simcards',
            'p1_simform', 'p1_simchart', 'p1_simmets', 'p1_c3d', 'p1_explodeI', 'p1_bleBtn',
            'p1_modeBadge', 'p1_stale'].every(id => document.getElementById(id) !== null),
    csv: !!document.querySelector('a[href="/api/board/history/export"]'),
    calbadge: document.body.textContent.includes('模型参数：理论值（未本机标定）'),
    oldCards: document.getElementById('pcards').childElementCount === 5,   /* 气动台无回归 */
  }));
  T('4 个 vendor script 引用(echarts+three+OrbitControls+STLLoader)', load.libScripts === 4);
  T('默认气动台可见 / P1 隐藏', load.pneuVisible && load.p1Hidden);
  T('顶层 2 标签 + 3 子标签按钮', load.tabs);
  T('P1 三子面板关键 DOM 齐全', load.panes);
  T('CSV 导出链接 + 未标定黄徽章文案', load.csv && load.calbadge);
  T('气动台 5 端口卡片仍在（无回归）', load.oldCards);

  console.log('─ 标签切换：P1 遥测子面板 ─');
  await p.click('#p1_tabbtnP1');
  await p.waitForTimeout(900);                       /* 首轮 /api/board/state */
  const tel = await p.evaluate(() => ({
    pneuHidden: document.getElementById('p1_tabpneu').style.display === 'none',
    p1Visible: document.getElementById('p1_tabp1').style.display === 'block',
    chartCanvas: !!document.querySelector('#p1_histchart canvas'),
    v5: document.getElementById('p1_ptV5').textContent,
    i5: document.getElementById('p1_ptI5').textContent,
    eff: document.getElementById('p1_ptEff').textContent,
    tcpu: document.getElementById('p1_tcpu').textContent,
    bars: document.querySelectorAll('#p1_valves .vbar').length,
    histN: p1_hist.t.length,
    staleHidden: document.getElementById('p1_stale').style.display === 'none',
  }));
  T('切换后气动台隐藏 / P1 显示', tel.pneuHidden && tel.p1Visible);
  T('双轴历史 ECharts 已渲染 canvas', tel.chartCanvas);
  T('电源树 5V 实时值已填充', /^[\d.]+ V$/.test(tel.v5) && /^[\d.]+ A$/.test(tel.i5));
  T('buck 效率与结温已填充', /%$/.test(tel.eff) && /^[\d.]+$/.test(tel.tcpu));
  T('8 阀电流条构建', tel.bars === 8);
  T('历史增量入图 (>0 点)', tel.histN > 0);
  T('stale=false 时冻结徽章隐藏', tel.staleHidden);

  console.log('─ 仿真子面板：presets 表单 + 自动重算 ─');
  await p.click('#p1_subbtnsim');
  await p.waitForTimeout(1200);                      /* presets fetch + buck 首算 */
  const sim = await p.evaluate(() => ({
    cards: document.querySelectorAll('#p1_simcards .p1simcard').length,
    sel: document.getElementById('p1_simc-buck').classList.contains('sel'),
    inputs: document.querySelectorAll('#p1_simform input').length,
    rows: document.querySelectorAll('#p1_simmets tbody tr').length,
    canvas: !!document.querySelector('#p1_simchart canvas'),
    notes: document.getElementById('p1_simnotes').textContent.length > 0,
    errHidden: document.getElementById('p1_simerr').style.display === 'none',
  }));
  T('四电路选择卡', sim.cards === 4);
  T('buck 默认选中', sim.sel);
  T('presets 动态参数表单(buck 6 参数)', sim.inputs === 6);
  T('自动重算出指标表 4 行 + 波形 canvas + notes', sim.rows === 4 && sim.canvas && sim.notes);
  T('无错误时红条隐藏', sim.errHidden);

  const sim400 = await p.evaluate(async () => {
    document.getElementById('p1_sp_vin').value = '9';          /* 越域 [3.8,5.5] */
    await p1_simRun();
    const bad = {
      visible: document.getElementById('p1_simerr').style.display === 'block',
      text: document.getElementById('p1_simerr').textContent,
      btnOk: document.getElementById('p1_simRunBtn').textContent === '⟳ 重算'
             && !document.getElementById('p1_simRunBtn').disabled,
    };
    document.getElementById('p1_sp_vin').value = '5';          /* 恢复并重算 */
    await p1_simRun();
    bad.recovered = document.querySelectorAll('#p1_simmets tbody tr').length === 4
                    && document.getElementById('p1_simerr').style.display === 'none';
    return bad;
  });
  T('参数越域 → 400 红条显示 error 文本', sim400.visible && sim400.text.includes('vin'));
  T('重算按钮恢复可用 / 修正参数后指标回归', sim400.btnOk && sim400.recovered);

  console.log('─ 结构子面板：3D 装配 ─');
  await p.click('#p1_subbtn3d');
  await p.waitForTimeout(1800);                      /* assembly + 5×STL 加载 */
  const st3d = await p.evaluate(() => ({
    init: !!p1_3d,
    parts: p1_3d ? p1_3d.parts.length : 0,
    failHidden: document.getElementById('p1_3dfail').style.display === 'none',
    bufW: p1_3d ? p1_3d.renderer.domElement.width : 0,
    loopLive: p1_3d ? p1_3d.raf !== 0 : false,
    note: document.getElementById('p1_3dnote').textContent,
  }));
  T('three.js 场景初始化', st3d.init);
  T('assembly 五部件 STL 全部加载', st3d.parts === 5);
  T('WebGL 渲染 buffer 已分配 (>0 px)', st3d.bufW > 0);
  T('装配备注写入 (铜柱螺丝)', st3d.note.includes('铜柱'));
  T('rAF 循环存活(结构页可见)', st3d.loopLive);
  await p.evaluate(() => p1_explodeSet(1));
  await p.waitForTimeout(700);
  const exp = await p.evaluate(() => ({
    z: p1_3d.parts[0].mesh.position.z,               /* case_top explode z=28 */
    label: document.getElementById('p1_explodeV').textContent,
  }));
  T('爆炸滑杆 → 上壳沿 +Z 位移 (≈28mm)', exp.z > 20);
  T('爆炸百分比标签联动', exp.label === '100%');

  console.log('─ BLE 纯逻辑：CRC / 帧 / 20B 解析（BLE.md 向量） ─');
  const ble = await p.evaluate(() => {
    const crc = p1_crc8(new Uint8Array([0xA5, 0x2B, 0x01, 0xFF]));
    const frame = Array.from(p1_buildFrame('+', 1, 255));
    const dv = new DataView(new Uint8Array(
      [0x21, 0x02, 0x7B, 0x00, 0xEB, 0xFD, 0, 0, 0, 0, 0, 0, 0xF4, 0x01,
       0, 0, 0, 0, 0, 0]).buffer);
    const f = p1_bleParseState(dv);
    const bad = p1_bleParseState(new DataView(new Uint8Array(
      [0x21, 0x02, 0x7B, 0x00, 0xEB, 0xFD, 0, 0, 0, 0, 0, 0, 0xF4, 0x01,
       1, 0, 0, 0, 0, 0]).buffer));                  /* 保留字节非 0 → 拒收 */
    return {
      crc: crc === 0xF8,
      frame: frame[0] === 0xA5 && frame[1] === 0x2B && frame[2] === 0x01 &&
             frame[3] === 0xFF && frame[4] === 0xF8,
      st: f && f.state === 0x0221,
      p: f && Math.abs(f.pressures[0] - 12.3) < 1e-9 && Math.abs(f.pressures[1] + 53.3) < 1e-9,
      tick: f && f.tick === 0x01F4,
      bad: bad === null,
    };
  });
  T('CRC-8(0x07/0x00): A5 2B 01 FF → F8', ble.crc);
  T('0xA5 帧构造 充气/端口1/PWM255 → A5 2B 01 FF F8', ble.frame);
  T('20B state 解析: 状态字/压力×10 含负压/tick', ble.st && ble.p && ble.tick);
  T('保留字节非 0 → 帧拒收 (ble_frame.c 同校验)', ble.bad);

  console.log('─ 双模命令路径 p1_sendCmd / 双模渲染入口 ─');
  const dual = await p.evaluate(async () => {
    const log = [];
    const orig = window.fetch;
    window.fetch = (url, opts) => {
      log.push({ url, opts });
      return Promise.resolve({ ok: true, json: async () => ({ ok: true }) });
    };
    try {
      await p1_sendCmd('+', 3, 200);                 /* 孪生模式 → CLI 行 */
      await p1_sendCmd('R');                         /* 帧码 'R' → CLI 'X' */
      p1_renderState({ state: 0x0021, valves: [255, 0, 0, 0, 0, 255, 0], pump: 255,
                       sensors: [12.3, -53.3], ports_p: [12.3, 0, 0, 0, 0],
                       cl: 'BLE', err: 0 });         /* 真机 notify 同入口 */
      return {
        inflate: log[0] && log[0].url === '/api/cmd' && log[0].opts.body === 'I 3 200',
        reset: log[1] && log[1].opts.body === 'X',
        st: document.getElementById('tbstate').textContent === '0x0021',
        gauge: document.getElementById('gval').textContent === '12.3',
        cl: document.getElementById('tbcl').textContent === 'BLE',
      };
    } finally { window.fetch = orig; }
  });
  T('孪生模式: p1_sendCmd(+,3,200) → POST /api/cmd "I 3 200"', dual.inflate);
  T('帧码映射: p1_sendCmd(R) → CLI "X" (闭环复位)', dual.reset);
  T('双模渲染: BLE 形状对象喂 p1_renderState → 状态字/压力表/闭环域', dual.st && dual.gauge && dual.cl);

  console.log('─ BLE 按钮态 / 时间控制 / 录制 ─');
  const misc = await p.evaluate(async () => {
    const out = {
      /* 按钮态与能力一致：有 navigator.bluetooth → 可点；无 → 置灰（本 chromium 有，CI 无头可能无） */
      bleConsistent: document.getElementById('p1_bleBtn').disabled === !navigator.bluetooth,
      badge: document.getElementById('p1_modeBadge').textContent.includes('孪生(HTTP)'),
    };
    await p1_timePost({ paused: true });
    out.pauseBtn = document.getElementById('p1_pauseBtn').textContent.includes('继续');
    await p1_timePost({ paused: false });
    out.resumeBtn = document.getElementById('p1_pauseBtn').textContent.includes('暂停');
    p1_recToggle();                                   /* start */
    await send('S 1');
    await p1_sendCmd('!', 1);
    out.recN = p1_recEvents.length === 2;
    p1_recToggle();                                   /* stop */
    out.replayVisible = document.getElementById('p1_replayBtn').style.display !== 'none'
                        && document.getElementById('p1_recN').textContent === '2';
    return out;
  });
  T('BLE 按钮态与环境能力一致 (无bt置灰) + 孪生徽章', misc.bleConsistent && misc.badge);
  T('时间控制: 暂停→继续按钮文案翻转', misc.pauseBtn && misc.resumeBtn);
  T('录制镜像 send+p1_sendCmd 两条 → 回放按钮出现', misc.recN && misc.replayVisible);

  console.log('─ 回气动台无回归 ─');
  await p.click('#p1_tabbtnPneu');
  const back = await p.evaluate(() => ({
    visible: document.getElementById('p1_tabpneu').style.display !== 'none',
    loopDead: p1_3d.raf === 0,                       /* 离开 P1 → 3D 循环停 */
    chart: !!document.querySelector('#chart canvas'),
  }));
  T('气动台恢复显示 + 压力曲线仍在', back.visible && back.chart);
  T('离开 P1 标签 → 3D rAF 循环停止', back.loopDead);

  T('全程无页面 JS 错误', errs.length === 0);
  if (errs.length) console.log('  错误: ' + errs.join(' | '));
  console.log(`\n${fail ? '✗' : '✓'} P1 前端测试 ${pass}/${pass + fail}`);
  await b.close();
  process.exit(fail ? 1 : 0);
})().catch(e => { console.error('FATAL', e.message); process.exit(1); });
