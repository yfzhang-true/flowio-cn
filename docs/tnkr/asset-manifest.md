# Tnkr 发布资产清单（T1c）

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
- **后续可选**: ① 生成合并装配体 STEP（顶+底+PCB）替换单一 case-top 主模型 ② 补 assembly-steps-en.md 到 Documentation ③ Kits 标签当前 disabled，满足条件后可探索套件上架
