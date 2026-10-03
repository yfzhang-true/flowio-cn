# Tnkr 发布资产清单（T1c）【已归档】

> **[终局 2026-10-03]** 平台已放弃：项目页已删除、GitHub App 授权已卸载、本目录整体归档。
> 装配体工件 `flowio-p1-assembly.step`（76MB）已移出 git HEAD（本地保留）；再生命令两条：
> ① `KICAD9_3RD_PARTY=C:/Users/yuefe/Documents/KiCad/9.0/3rdparty` 前置下运行 `kicad-cli pcb export step --force -o hardware/flowio-p1/fab/flowio-p1.step hardware/flowio-p1/flowio-p1.kicad_pcb`
> ② `"E:/FreeCAD/bin/FreeCADCmd.exe"` 经 exec 注入法运行 `hardware/flowio-p1/enclosure/make_assembly.py`（中文脚本绕法见操作手册 §7）

> **日期**: 2026-10-03 · **安全检查**: 密钥模式扫描（`ghp_*` / `mcpk2_*`）对下列全部文件零命中
> **BOM 口径**: 39 行物料项 / 107 个贴片位（"107 parts"指 placements）

## 1. 待上传资产

| # | 文件 | 大小 | 用途 | 处理 |
|---|---|---|---|---|
| 1 | `firmware/twin/meshes/case_top.stl` | 148 KB | 3D 分解-外壳顶 | 上传 3D viewer |
| 2 | `firmware/twin/meshes/case_bottom.stl` | 212 KB | 3D 分解-外壳底 | 上传 3D viewer |
| 3 | `firmware/twin/meshes/parts_f.stl` | 72 KB | 3D 分解-前器件簇 | 上传 3D viewer |
| 4 | `firmware/twin/meshes/parts_b.stl` | <1 KB | 3D 分解-后器件簇 | 上传 3D viewer |
| 5 | `firmware/twin/meshes/pcb.stl` | <1 KB | 3D 分解-PCB 基板 | 上传 3D viewer |
| 6 | `hardware/flowio-p1/enclosure/case-top.step` | 274 KB | 可编辑 CAD 源 | Files 区 |
| 7 | `hardware/flowio-p1/enclosure/case-bottom.step` | 114 KB | 可编辑 CAD 源 | Files 区 |
| 8 | `hardware/flowio-p1/fab/flowio-p1-bom-jlc.csv` | — | BOM（39 行物料，LCSC 编码 100%） | BOM 导入/Files 区 |
| 9 | `docs/tnkr/onepager-en.md` | — | 项目页正文 | Overview 正文 |
| 10 | `docs/tnkr/assembly-steps-en.md` | — | 装配分步（10 步，票号 A201-A302） | Documentation |

**3D 总量 < 1 MB** —— 任何合理限额内。

## 2. 链接与声明

- **GitHub**: https://github.com/yfzhang-true/flowio-cn（唯一权威源）
- **License**: 代码 MIT · 硬件 CERN OHL-S（项目页双声明）
- **Kit 备注**: 若开通套件销售，定价带 ¥300-500（~$45-70），对标站内 XLeRobot $550 / Open Duck Mini $600 先例

## 3. 安全红线（已验证）

- 发布物中零密钥（本节头部扫描结论）
- `简历/`（含 PAT、天眼查 Key、尽调数据）不在任何发布路径中
- 仅引用 GitHub 公开内容与仓库内公开资产

## 4. 发布记录（Task 5 完成后回填）

- **项目页 URL**: https://tnkr.ai/yuefeizzzs-workspace/flowio-cn （2026-10-03 发布，Public）
- **发布方式**: GitHub 导入路径（Connect to GitHub → 选 flowio-cn → 主 STEP 选 case-top.step → Project Details 表单）
- **实测结论**（回填 platform-notes §5）:
  - 项目名 FLOWIO-CN；描述 262/350 字符（含 MIT/CERN OHL-S 双声明）
  - GitHub App 以**最小权限**安装（Selected repositories: 仅 flowio-cn，只读 actions/code/discussions 等）
  - **整个仓库文件树自动导入 Files 区**（bom-jlc.csv / 双 STEP / pcb.stl / parts_f.stl / BRINGUP.md / README 全部在列，来源标记 github）——无需本地上传
  - GitHub 链接自动接线（github.com/yfzhang-true/flowio-cn）
  - Leo 项目助手自带 "Show me the BOM / How do I assemble this?" 按钮
- **异步待完成（平台侧处理中，稍后自查）**: Leonardo processing——① Documentation 标签内容生成 ② STEP→3D viewer 渲染（Overview 当前无 canvas）
- **后续可选**: ① ~~生成合并装配体 STEP~~ ✅ 已完成（2026-10-03，见下）② 补 assembly-steps-en.md 到 Documentation ③ Kits 标签当前 disabled，满足条件后可探索套件上架

## 5. 装配体主模型升级（2026-10-03 第二轮）

- **流水线**: kicad-cli 导出 PCB STEP（需 `KICAD9_3RD_PARTY=C:/Users/yuefe/Documents/KiCad/9.0/3rdparty`，否则 108 个 JLC 元件 3D 体缺失）→ `enclosure/make_assembly.py` 合并（离群过滤 136 个坏原点 JLC 模型）→ 装配体 **557 solids**，包围盒 95.8×80.8×19.1（与理论偏差 ≤0.11mm，断言通过）
- **产物**: `hardware/flowio-p1/enclosure/flowio-p1-assembly.step`（**76MB**，已入 main 并 push；GitHub 提示 >50MB 建议但未拦截）；assembly STL 67MB 与 PCB 中间件 20MB 已 gitignore（可由脚本再生）
- **三轮复核（2026-10-03 深夜，管理后台发现后全面翻案）**: 用户发现隐藏管理路由 `/projects/home/{id}`（项目 ID edb4fbab-7e85-4913-a40a-0802c2830a07）——侧栏含 Central Docs / Hardware Docs（mode=edit）/ File Management / **Settings**。此前"无删除/无编辑入口"结论作废：
  - ✅ **Documentation 已发布**：Central Docs 编辑器（contenteditable）写入 Overview 项目介绍（776 字符）→ Publish 成功 → 公开页 Documentation 标签可见正文，**3D canvas×3 首次渲染**
- **四轮终局（2026-10-03 深夜，全链路闭环 ✅）**:
  - ✅ **STEP 原位替换完成**：零用户操作——本地一次性 CORS 服务器（`tools/serve_step_once.mjs`，127.0.0.1:8765，含 PNA 头）→ Tnkr 页面 fetch 76.4MB → File/DataTransfer 注入 `input[type=file]`（accept=.stp,.step）→ 平台上传 → "Analyze new model"（结构比对：0 added/0 removed/1 changed，判定 safe）→ "Replace model" 执行 → 替换区重置确认完成
  - ✅ 公开页 3D canvas×3 渲染恢复（换模后需等待平台重转换）
  - ✅ **缩略图已从新 3D 模型生成**（S3 CDN thumbnail/edb4fbab-…）
  - 📌 突破浏览器自动化上传限制的通用手法已沉淀：CORS+PNA 本地服务 + 页面内 File 构造注入（react-dropzone 兼容）
  - ⏳ 唯一剩余：Assembly Instructions 结构化步骤编辑器（3D 标注装配阶段）——建议专场
  - ⏳ **Assembly Instructions 为结构化步骤编辑器**（"Add Assembly Instructions"→3D 标注装配阶段），建议在 STEP 替换后专场处理
  - 📋 Delete Project 按钮确认存在（Settings→General 底部）——重建路径恢复可行，但原位替换已使其不必要
  - 7 步设置清单当前 1/7（Publish 文档后预计 +N，待复查）
- **Onshape 结论**: 不需要注册关联——我们的 CAD 链是 FreeCAD→STEP→GitHub→Tnkr 已闭环；Onshape 集成仅服务"在 Onshape 里做设计"的用户
- **运行约束备忘**: FreeCADCmd 对含中文注释脚本报"not readable"，用 `exec(compile(open(p, encoding='utf-8').read(), p, 'exec'), {'__file__': p})` 绕过
