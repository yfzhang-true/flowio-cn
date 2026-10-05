# Plan: 数字孪生全流程 SOP 与模块化（M0-M5 + A2 · spec 批准后执行）

> spec: docs/superpowers/specs/2026-10-05-digital-twin-fullstack-modularization-design.md
> worktree: modularization · 每期独立交付可中断 · 基线冻结+字节对拍 · 双阶段评审每期必走

## M0 核心抽象层（先行，~半天）
1. `flowio/core/interfaces.py`：IActuator/ISensor/BaseModel(+TubeNet 预留)+errors 层次（纯 ABC 零依赖）；
2. `flowio/core/truth.py`：TruthSource 封装（devices.json 两段只读装载+schema 校验委托 truth/）；
3. `flowio/truth/`：v1 期 B 的 truth 迁入+T1 pneumatic 谓词迁入（断言语义不变）；
4. electrical_sim.py 改经 TruthSource 取参（行为锚点：12 场景数值逐一不变）。
**验收**：L5 15/0、electrical_sim 6fn、场景数值快照相等。

## M1 硬件/结构/气路域挂载（~1 天）
1. `flowio/hw/`（sch_gen/pcb_gen/route 六阶段+dsn_io+auto6/drc_rules 预留）；
2. `flowio/geom/`（case/device_geom/fcl/manifold/pump_module）、`flowio/flows/`（pneu_geom 并入 flows）；
3. 旧路径 shim（tools/gen_sch.py→from flowio.hw.sch_gen import…，废弃标记+一个版本周期）；
4. 生成器重放对拍：gen_sch/gen_pcb/make_case/make_manifold/make_pump_module/make_meshes/make_assembly
   产物与迁移前 uuid 归一化逐字节一致。
**验收**：全家桶全绿+对拍报告。

## M2 孪生域 OOD 重构（~1 天）
1. ElectricalModel(BaseModel)：electrical_sim 迁入，IActuator 子类化
   （ValveF0520D/F0520B/PumpZR370——current/effective_v 多态实现）；
2. board_model 拆 ThermalModel+PneumaticModel；BoardModel 组合根 façade
   （对外 API 兼容旧 board_model 调用方）；
3. sim_engine 改经 BoardModel；twin_api.c 不动（C 侧在 M3）。
**验收**：场景矩阵 12 数值相等、run_tests 0、接口 50/50。

## M3 三语参数 codegen（~半天）
1. `flowio/fwgen/`：devices.json→pn_core/params_gen.h（D1 形态：片段被 types.h include，
   DO NOT EDIT 头）；现有手写常量逐个迁移（-60/230/100ms 等）；
2. `flowio/webgen/`：→webapp/js/params_gen.js（ES module）；
3. CI 门：`flowio codegen --all && git diff --exit-code`（手编即红）；
4. 负测试：手改 params_gen.h 一处→CI 红→还原。
**验收**：三语常量对拍=devices.json；负测试红绿证据。

## M4 webapp 模块化（~半天，D2=A 浅度）
1. js 七件按组件契约归位（importmap+ES ./ 铁律保持）；
2. params_gen.js 接入（面板/仿真读生成参数）。
**验收**：test_webapp 47/47、site 重建字节对拍（params_gen 除外）。

## M5 cli+全回归+盲测（~半天）
1. `flowio/cli.py`：truth/hw/geom/flows/twin/fwgen/webgen/test/rebuild/codegen；
2. run_tests.sh 切 cli 双跑对拍（退出码一致）后收单跑；
3. 盲测（skill A2 版同步更新）：fresh 代理完成"新执行器类型接入"三步
   （devices.json 条目+IActuator 子类+场景）零改仿真器走通。
**验收**：盲测通过+全回归 0。

## A2 SOP skill v2（与 M0 并行，~半天）
1. SKILL.md 八节→十二节（§0 愿景/§6 固件/§7 孪生/§8 呈现新增，内容按 spec §4 表）；
2. rebuild-matrix.json +6 行（固件常量/孪生模型/webapp/传感换型/执行器加型/参数三语）；
3. 盲测二轮（新三节各一任务）+ deploy_sop_skill.py 重部署。
**验收**：盲测通过+IN-SYNC。

## 风险
- M1 对拍若遇生成器隐式时序（dict 序/随机 uuid）——uuid 归一化器已有先例，dict 序用 sort_keys；
- M3 迁 types.h 逐常量须逐个溯源注释搬运（禁丢事故出处）；
- 与 P2 板到货 BRINGUP 争窗口——各期独立可暂停，BRINGUP 优先。

## 依赖与顺序
M0→M1→M2→M3→M4→M5 主线；A2 随 M0 并行启动；D1/D2/D3 裁定后开工。
