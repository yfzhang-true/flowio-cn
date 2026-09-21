# PLAN — 数字孪生前端实现（gui.html 完整重写）

> 前置：SPEC.md 已审查通过。本文件描述代码实现的具体步骤和验证方法。
> 原则：每步写完立即验证，通过后再进下一步。不再连续重写。

## 文件

| 文件 | 说明 |
|------|------|
| `twin/gui.html` | 唯一主控制台页面（单文件 HTML，无构建依赖） |
| `twin/check.js` | 前端冒烟检查（已有，复用） |
| `twin/server.py` | 孪生服务（已运行，不改） |

## 技术选型

| 项 | 选择 | 理由 |
|----|------|------|
| 渲染 | SVG（非 Canvas） | 元素级控制（逐活塞变色/位移），无需重绘全帧 |
| 动画 | CSS transition + keyframes | 活塞 fill/translateY 0.2s 过渡，叶轮 rotate 无限循环 |
| 状态驱动 | setInterval 200ms fetch /api/state | 与后端轮询频率匹配 |
| 布局 | CSS Grid 三栏 | 左=示意图+控制，中=Scheduler，右=Log |

## Step 1 — HTML 骨架 + CSS（预计 15 min）

**内容**：
- 顶栏：品牌名 + 状态徽标（state / 闭环 / 错误 / 时钟）
- 三栏 Grid 布局
- 左栏：动画气路 SVG（汇流管腔体 + 7 活塞 + 泵叶轮 + 大气标记 + 端口短管 + 流向箭头 + 压力表）
- 中栏：Scheduler 面板（Add Row / Delete / Reset / Play / Stop 按钮 + 行表格）
- 右栏：Log 面板（绿色等宽字滚动日志）

**验证**：`node check.js gui.html` 语法通过 + 浏览器截图确认布局

## Step 2 — SVG 活塞与叶轮元素精确坐标（预计 15 min）

**内容**：
- 汇流管腔体：圆角矩形，浅蓝底色
- 7 个活塞位：每个 = 活塞矩形（深色）+ 弹簧锯齿 + 阀杆 + 标签
- 泵叶轮：3 叶片 + 中心圆
- 进气/排气短管 + 大气标记
- 压力表圆盘

**验证**：浏览器截图确认所有 SVG 元素在正确位置

## Step 3 — 状态轮询驱动动画（预计 20 min）

**内容**：
- setInterval 200ms fetch /api/state
- 状态变化时更新活塞颜色（ON=绿/OFF=灰）、叶轮旋转（CSS animation 开关）
- 更新压力表数值

**验证**：
- 用 /api/sim 注入压力 → 观察压力表变化
- 手动 POST 命令 → 观察活塞变色

## Step 4 — Scheduler 引擎（预计 20 min）

**内容**：
- rows 数组 + renderSched() 渲染表格
- schedAddRow() / schedDelRow() / schedReset()
- schedPlay()：按 t0 偏移 setTimeout 逐行执行
- schedStopSeq()：清除 timers

**验证**：
- Add 3 行 → Play → 确认按偏移依次执行
- Stop → 确认中止

## Step 5 — 端口控制卡片 ×5（预计 15 min）

**内容**：
- 5 张端口卡片（端口1-5），每张含：
  - 端口名 + 状态标签（阀开/阀关）
  - 压力读数（kPa 大字）
  - 充/保/释/抽 4 按钮
  - 目标压力滑块

**验证**：点各按钮 → 对应阀活塞变色 + 命令发送

## Step 6 — Log 面板 + 全流程截图（预计 10 min）

**内容**：
- devlog 面板（绿色等宽字，最新在上）
- 全流程截图：初始 → 充气 → 释放 → 保压 → 日志记录

**验证**：
- 完整流程截图集
- 刷新后状态恢复

## 风险与缓解

| 风险 | 缓解 |
|------|------|
| 跨域请求被浏览器拦截 | server.py 已设 CORS 头 |
| SVG 元素定位偏移 | 每步截图确认坐标 |
| CSS transition 与 JS 直接设属性冲突 | 统一用 JS 设 attribute，CSS 只做过渡 |
| 多个 setTimeout 竞争 | 用唯一前缀命名，Stop 时全部清除 |

## 时间估算

| 步骤 | 预计 |
|------|------|
| Step 1 骨架 | 15 min |
| Step 2 SVG 元素 | 15 min |
| Step 3 状态轮询 | 20 min |
| Step 4 Scheduler | 20 min |
| Step 5 端口卡片 | 15 min |
| Step 6 Log + 截图 | 10 min |
| **总计** | **~95 min** |
