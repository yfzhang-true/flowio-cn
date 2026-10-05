# Plan: SOP 沉淀（期 A 流程 Skill 化先行 · 期 B 模块化随 P1.1 收尾后）

> spec: docs/superpowers/specs/2026-10-05-sop-modularization-design.md
> 前提: 用户裁定 S1/S2/S3；期 A 不依赖任何代码状态可立即执行；期 B 等 P1.1 T8。

## 期 A: SOP Skill 化（A1-A5，纯文档，~半天量）

### A1 素材回溯与矩阵补全
从 git 历史（P1→P1.1 全部 commit）+ HANDOFF 铁律 12 条 + 本轮 T1-T4 实战，
穷举"变更→重走"场景，核对 spec §2.2.3 矩阵覆盖度（目标 ≥13 类，含 5 次
真实返工案例：壳高链漂移/端子换型/双带出线/POS_P11 过渡/DSN 电源清除事故）。

### A2 SKILL.md 撰写（仓库源）
`docs/sop/SKILL.md` 八节 checklist 化（每节: 触发条件→步骤→命令→验收→反例引用）。
铁律区含 hooksPath 绕行的"理由模板"（Mimosa venv 误报场景）与 max_passes=3 等
血泪参数。语言: 中文，命令可复制即跑（三环境路径表齐备）。

### A3 变更重走矩阵机读化
`docs/sop/rebuild-matrix.json`（改什么→[重跑链]→[更新面]），SKILL.md 引用人读表，
脚本可消费（期 B cli 的 `flowio rebuild --after <change>` 直接用此数据源——一份真相）。

### A4 部署与盲测
- 同步脚本 `tools/deploy_sop_skill.py`（仓库 docs/sop/ → C:\Users\yuefe\.agents\skills\flowio-sop\，幂等）；
- 盲测: fresh 子代理只加载 skill，完成两个推演任务（改 PLACE 重走链推演/新器件端到端
  数据面清单），无卡点=通过；不通过回 A2 修。

### A5 归档提交
commit（含矩阵 json+skill 镜像+部署脚本+盲测记录 docs/sop/blind-test-1.md）。

## 期 B: 模块化重构（B1-B7，P1.1 交付后，独立 worktree）

### B1 冻结基线
`flowio all` 快照: 全测试输出+全部生成物 sha256 清单（DRC 差分基线）。
### B2 骨架与 truth 层
包骨架+truth/（devices 加载/schema/pneumatic 谓词迁移，T1 断言改引 testkit/check）。
### B3 gen 层
gen_sch/gen_pcb 迁移为 sch_gen/pcb_gen（AST 共享真值源机制原样保留）；旧路径 shim。
### B4 route 层
route_pcb 六阶段拆 stage1-6 + dsn_io + auto6 + **drc_rules（硬线/美观线两档，S1-A 落地）**；
布线重放对拍 B1 基线（产物逐字节一致）。
### B5 geom/flows/netlist/testkit 层 + cli
### B6 run_tests.sh 切 cli 双跑对拍（退出码一致）后删双跑
### B7 盲测+收尾
假想器件端到端零代码改动走通（spec §3.3）；shim 标记废弃周期；HANDOFF 增"flowio cli"章节。

## 风险
- 期 B 与未来 P2 改动争窗口 → B 排期由用户点单启动，不自动开工；
- 迁移期产物确定性破坏（uuid/时间戳）→ B1 基线含归一化对比脚本（uuid 折叠）；
- skill 双源漂移 → A4 部署脚本单向同步+CI 可选校验（仅提示不阻断）。
