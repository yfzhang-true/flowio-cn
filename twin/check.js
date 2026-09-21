#!/usr/bin/env node
/**
 * check.js — 前端冒烟检查（无需浏览器）
 *   1. 内联 <script> 语法检查（能抓住"多余括号导致整页 JS 失效"这类事故）
 *   2. onclick/oninput 处理函数存在性检查
 *   3. $('id') 引用与 id="..." 定义交叉核对（跳过 JS 动态生成的已知前缀）
 * 用法: node check.js <page.html> [more.html ...]
 */
const fs = require('fs');
const vm = require('vm');

let fail = 0;
const DYNAMIC_ID = /^(bal|pv|tl|st|pp|pt|pf|seq|ps|pc|pn)/;   // JS 动态生成的前缀
const JS_KEYWORD = new Set(['if', 'for', 'while', 'switch', 'return']);

for (const file of process.argv.slice(2)) {
  const html = fs.readFileSync(file, 'utf8');
  const blocks = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);

  // 1) 语法检查
  blocks.forEach((code, bi) => {
    try {
      new vm.Script(code, { filename: `${file}#inline-${bi}` });
    } catch (e) {
      console.log(`✗ [语法] ${file} script#${bi}: ${e.message.split('\n')[0]}`);
      ++fail;
    }
  });

  // 2) 事件处理函数存在性
  const handlers = new Set();
  for (const m of html.matchAll(/on(?:click|input|change|keydown)="([A-Za-z_$][\w$]*)\(/g))
    if (!JS_KEYWORD.has(m[1])) handlers.add(m[1]);
  for (const h of handlers) {
    if (!new RegExp(`function\\s+${h}\\b|(?:const|let|var)\\s+${h}\\s*=`).test(html)) {
      console.log(`✗ [缺失] ${file}: 处理函数 ${h}() 未定义`);
      ++fail;
    }
  }

  // 3) $('id') 静态引用 vs id="..." 定义
  const ids = new Set([...html.matchAll(/id="([^"]+)"/g)].map(m => m[1]));
  const refs = new Set();
  for (const m of html.matchAll(/\$\('([A-Za-z][\w-]*)'\)/g)) refs.add(m[1]);
  for (const r of refs) {
    if (DYNAMIC_ID.test(r)) continue;
    if (!ids.has(r)) { console.log(`✗ [缺失] ${file}: #${r} 不存在`); ++fail; }
  }

  console.log(`• ${file}: ${blocks.length} 个脚本块, ${handlers.size} 个处理函数, 语法 ${fail ? '有问题' : 'OK'}`);
}
process.exit(fail ? 1 : 0);
