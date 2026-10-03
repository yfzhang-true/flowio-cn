# Tnkr 主模型升级（合并装配体 STEP）+ Documentation 补全 — 设计规格书

> **[已弃用 2026-10-03]** tnkr.ai 平台已放弃（展示切换 GitHub Pages）。本文仅作工程史留档，执行结论见 docs/archive/tnkr-2026-10/asset-manifest.md。

> **日期**: 2026-10-03 · **状态**: 待用户审查
> **背景**: FLOWIO-CN 已上线 Tnkr（/yuefeizzzs-workspace/flowio-cn）。当前主 STEP 为单一 case-top.step（平台规则"恰好一个主模型"），零件分解观感受限；Documentation 依赖 Leonardo 异步生成，质量待核。
> **用户指令**: 认可"可选后续"①②，要求 using-superpowers + using-git-worktrees 流程。

---

## 1. 范围

| 项 | 内容 | 状态 |
|---|---|---|
| ① 合并装配体 STEP | PCB（含元件）+ case-top + case-bottom 合并为单一装配体，作为 Tnkr 主模型 | **本期核心** |
| ② Documentation 补全 | 核查 Leonardo 生成结果；不足则以 assembly-steps-en.md 内容补齐 | 本期 |
| ③ Kits 套件上架 | 平台 Kits 标签 disabled（条件未解锁），且属商业决策 | **明确出范围** |

## 2. 技术设计

### 2.1 装配体生成流水线（三段）

```
[A] kicad-cli 导出 PCB STEP（含元件 3D 体）
    "E:/Program Files/KiCad/10.0/bin/kicad-cli" pcb export step
      --force -o hardware/flowio-p1/fab/flowio-p1.step
      hardware/flowio-p1/flowio-p1.kicad_pcb

[B] FreeCADCmd 合并装配（新脚本 enclosure/make_assembly.py）
    输入: fab/flowio-p1.step + enclosure/case-top.step + enclosure/case-bottom.step
    定位: 复用 make_case.py 的板尺寸(90×75)与 standoffs.txt 的柱高参数
    输出: enclosure/flowio-p1-assembly.step（多 solid 装配体——Tnkr 拆解视图的原料）

[C] 入库 + 平台同步
    commit → push GitHub → Tnkr Files 区自动跟随仓库 → Manage 更换主 STEP
```

### 2.2 关键风险与对策

| 风险 | 对策 |
|---|---|
| KiCad 元件 3D 模型路径环境变量缺失 → 元件体缺失 | 导出后用 FreeCAD 脚本数 solid 数量；不达标降级 `--board-only`（板+外壳也有分解价值） |
| 装配体文件过大（107 元件 STEP 可达数 MB） | Tnkr 限 100MB，余量充足；GitHub 仓库增量可控 |
| Tnkr Manage 不支持更换主 STEP | 退路：删除项目重建（GitHub 导入路径 5 分钟可复现，已有 runbook）；或主模型维持 case-top、装配体放 Files 区供下载 |
| FreeCAD 合并坐标错位 | 以 standoffs.txt 实测参数为准；生成后脚本化断言（包围盒尺寸≈预期整机尺寸） |

### 2.3 Worktree 约定（using-git-worktrees）

- 目录：`.worktrees/tnkr-assembly`（项目本地隐藏目录）
- 创建前 `git check-ignore .worktrees` 验证，未忽略则先补 .gitignore + 提交
- 分支：`tnkr/assembly-step`；完成后合回 main 并 push（Tnkr Files 同步依赖 GitHub）
- 基线：工作树内跑 `enclosure/check_case.py`（既有几何自检）确认起点干净

## 3. 验收标准

1. `flowio-p1-assembly.step` 生成且含 ≥3 个 solid（顶盖/底壳/PCB 板体；含元件则数十个）
2. 装配体包围盒尺寸与预期整机外形一致（脚本断言，容差 ±2mm）
3. 合并提交推送 GitHub 后，Tnkr 项目 Files 区可见 `flowio-p1-assembly.step`
4. Tnkr 主模型更换为装配体（或按 §2.2 退路记录原因）
5. Documentation 标签有实质内容（Leonardo 生成或手动补齐，含装配步骤）
6. 主仓 main 分支仅新增：make_assembly.py + 2 个 STEP 工件 + 文档回填

## 4. 开放问题（审查时定夺）

1. PCB STEP 若元件体导出不完整：接受"板体+外壳"降级版，还是补齐 KiCad 3D 库路径后重试？（建议：先试完整版，降级版兜底，两版产物都留档）
2. 装配体是否同时导出一份合并 STL 供数字孪生复用？（建议：顺带导出，成本一行命令）
