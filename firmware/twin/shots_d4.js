#!/usr/bin/env node
/**
 * shots_d4.js — D4 视觉回归截图 (spec 2026-10-05 §7 验收 4 "渲染目视")
 *
 * 三视角 + 两态存证 → docs/device-modeling/*.png:
 *   1 d4-pump-top.png      泵特写: 立式校正 —— 顶置双嘴 ⌀4.2 垂直于泵轴 (旧版错误=侧嘴)
 *   2 d4-valve-leads.png   阵特写: F0520D C 架 + 引线出体 + 红黑桩拱越落 J 带 + 2P 白壳
 *   3 d4-tube-routing.png  全局 3/4: connections.json 驱动管路走线 (16 管) + 模块间干管
 *   4 d4-explode-follow.png 爆炸态: 连接边端点跟随部件拉伸 (分装式教学价值)
 *   5 d4-click-highlight.png 点击 J10: 三类连接高亮分色 + 提示 chip (器件名+计数)
 *
 * 用法: ① 起 server (TWIN_URL 或 http://127.0.0.1:8017)  ② node shots_d4.js [输出目录]
 * 前置: playwright-core 可 require (NODE_PATH 或 firmware/twin/node_modules); Chromium 路径同 test_webapp。
 */
'use strict';
let pw;
try { pw = require('playwright-core'); }
catch (e) { console.log('SKIP: 需要 playwright-core（npm i playwright-core 或设 NODE_PATH）'); process.exit(2); }
const fs = require('fs');
const path = require('path');
const CHROME = process.env.TWIN_CHROME ||
  'C:\\Users\\yuefe\\AppData\\Local\\ms-playwright\\chromium-1200\\chrome-win64\\chrome.exe';
if (!fs.existsSync(CHROME)) { console.log('SKIP: 未找到 Chromium，可用 TWIN_CHROME 指定'); process.exit(2); }

const BASE = process.env.TWIN_URL || 'http://127.0.0.1:8017';
const OUT = process.argv[2] || path.join('..', '..', 'docs', 'device-modeling');
fs.mkdirSync(OUT, { recursive: true });

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

(async () => {
  const b = await pw.chromium.launch({ executablePath: CHROME, headless: true });
  const p = await b.newPage({ viewport: { width: 1680, height: 1050 } });
  try { await p.goto(BASE + '/', { waitUntil: 'load', timeout: 10000 }); }
  catch (e) { console.log('SKIP: 测试服务未启动（先 bash run_tests.sh 或起 server.py）'); await b.close(); process.exit(2); }
  await p.waitForFunction(() => window.__t2 && window.__t2.scene
    && window.__t2.scene.parts.length > 0 && window.__t2.scene.connections, null, { timeout: 30000 });
  await p.evaluate(() => fetch('/api/reset', { method: 'POST' }));
  await sleep(2800);                                     // 装配叙事收敛

  // 视角: 相机/target 设定 + 关闭呼吸悬浮的取景抖动 (不改内核, 仅设位)
  const view = (cam, tgt) => p.evaluate(([c, t]) => {
    const sc = window.__t2.scene;
    sc.camera.position.set(...c);
    sc.controls.target.set(...t);
    sc.controls.update();
  }, [cam, tgt]);

  async function shot(name) {
    await sleep(350);                                    // 等阻尼收敛 + 一帧渲染
    await p.screenshot({ path: path.join(OUT, name), clip: { x: 0, y: 0, width: 1680, height: 1050 } });
    console.log('  ✓ ' + name);
  }

  console.log('─ D4 视觉回归三视角 + 两态 ─');
  // 1. 泵特写 (泵模块 @x135.8..202.7, 泵轴 z18.4, 顶置双嘴 z24..31.5)
  //    装配位 + 隐壳透视 (仅截图工具临时 visible=false, 非场景功能) ——
  //    验证 "顶置双嘴 ⌀4.2 垂直泵轴" (E1 校正核心) 与模块内跳管
  await p.evaluate(() => {
    window.__t2.scene.parts.find((x) => x.id === 'pump_case').mesh.visible = false;
  });
  await sleep(400);
  await view([120, -95, 105], [163, 43, 24]);
  await shot('d4-pump-top.png');
  await p.evaluate(() => {
    window.__t2.scene.parts.find((x) => x.id === 'pump_case').mesh.visible = true;
  });
  await sleep(300);
  // 2. 阀阵特写 (塔 @y45..70 z21.5..50, 引线拱越落 B 壁 J 带)
  await view([75, 285, 115], [55, 52, 27]);
  await shot('d4-valve-leads.png');
  // 3. 全局 3/4 管路走线 (双体: 主模块 + 泵模块, 模块间干管 ×2 + 电缆)
  await view([-90, -330, 190], [100, 45, 20]);
  await shot('d4-tube-routing.png');

  // 4. 爆炸态: 连接边端跟随拉伸
  await p.evaluate(() => window.__t2.scene.setExplode(1));
  await sleep(1400);
  await view([-90, -330, 220], [100, 45, 35]);
  await shot('d4-explode-follow.png');
  await p.evaluate(() => window.__t2.scene.setExplode(0));
  await sleep(900);

  // 5. 点击 J10 热点 (raycaster 真点击): 高亮 + chip
  const pt = await p.evaluate(() => {
    const sc = window.__t2.scene;
    const hs = sc.hotspots.find((h) => h.ref === 'J10');
    const cam = sc.camera;
    const V3 = cam.position.constructor;
    const v = new V3(hs.center[0], hs.center[1], hs.center[2]);
    v.applyMatrix4(cam.matrixWorldInverse).applyMatrix4(cam.projectionMatrix);
    return { x: (v.x + 1) / 2 * 1680, y: (1 - v.y) / 2 * 1050 };
  });
  await p.mouse.click(pt.x, pt.y);
  await sleep(600);
  await view([75, 285, 115], [55, 52, 27]);
  await sleep(300);
  await shot('d4-click-highlight.png');

  await b.close();
  console.log('SHOTS OK -> ' + path.resolve(OUT));
})().catch((e) => { console.error('FATAL', e.message); process.exit(1); });
