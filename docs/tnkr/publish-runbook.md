# Tnkr 发布操作手册（Publish Runbook）

> **日期**: 2026-10-03 · **前提**: 你已在自己的浏览器登录 tnkr.ai（GitHub OAuth, yfzhang-true）
> **预计耗时**: ~10 分钟 · **全部素材路径**: 见 `docs/tnkr/asset-manifest.md`

## 安全红线

- 全程不需要向任何页面输入 GitHub 密码；若弹出 GitHub 重新授权，只点 "Authorize"
- 若被要求输入密码且页面 URL 不是 github.com，立即停止（钓鱼）

## 步骤

### 1. 创建项目

- 进入 tnkr.ai，找 **Create Project / New Project** 入口（通常在右上角或 dashboard）
- 项目名：`FLOWIO-CN — Open Pneumatic Soft-Robotics Control Platform`
- 简称/slug（如要求）：`flowio-cn`
- 可见性：**Public**

### 2. 填 Overview 正文

- 打开 `docs/tnkr/onepager-en.md`，全文复制粘贴到项目简介/Overview 富文本框
- 若编辑器支持 Markdown，直接贴源码；若纯文本，保留标题层级手调

### 3. 上传文件（Files 标签）

按 `asset-manifest.md` §1 清单上传 8 个文件：

```
firmware/twin/meshes/case_top.stl        （3D）
firmware/twin/meshes/case_bottom.stl     （3D）
firmware/twin/meshes/parts_f.stl         （3D）
firmware/twin/meshes/parts_b.stl         （3D）
firmware/twin/meshes/pcb.stl             （3D）
hardware/flowio-p1/enclosure/case-top.step    （CAD 源）
hardware/flowio-p1/enclosure/case-bottom.step （CAD 源）
hardware/flowio-p1/fab/flowio-p1-bom-jlc.csv  （BOM，39 行物料）
```

### 4. Documentation 标签

- 粘贴 `docs/tnkr/assembly-steps-en.md` 内容（10 步装配/bring-up）
- 若平台支持分步结构，按其 step 格式拆分，票号 A201-A302 保留

### 5. 链接与 License

- GitHub: `https://github.com/yfzhang-true/flowio-cn`
- License 声明（若无专用字段，加在 Overview 末尾）：
  `Code: MIT · Hardware: CERN OHL-S`

### 6. 发布 + 回填

- Publish 后复制项目页 URL
- 顺手核实 6 项（platform-notes §5）：3D 是否自动出分解视图 / BOM 的 LCSC 编码是否变成可点链接 / free tier 有无弹限制 / license 字段位置 / 有无 kit 上架入口 / GitHub repo 是否可关联同步
- 把 URL + 6 项观察告诉我，我回填 `asset-manifest.md §4` 与 `platform-notes.md §5` 并提交

## 备选：Agent 代驾（不需要密码）

若想让我操作：说一声，我用 browser-use 打开 tnkr.ai——**登录墙出现时把窗口交给你**，你在那个窗口里完成 GitHub OAuth（密码只经你手），登录成功后我接管完成 2-5 步。
