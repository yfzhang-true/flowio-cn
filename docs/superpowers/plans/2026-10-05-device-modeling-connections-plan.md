# Plan: 器件精确建模与连接图谱（R + D1-D4 · spec 批准后执行）

> spec: docs/superpowers/specs/2026-10-05-device-modeling-connections-design.md
> worktree: device-modeling · 每阶段 TDD（几何/连接断言先行）+ 双阶段评审 · 基线=全家桶现有绿

## R1 baseline 研究（先于建模，~半天）
1. aminer/学术：气路集总参数与软体执行器连接建模文献深挖（aminer MCP 接入或 WebSearch 替代；Xavier 在库为起点）；
2. github：KiCad 3D 库/JLC 3D 模型查证（XGZP6897D 现货 STEP？）；CadQuery/build123d 表达范式参考（FreeCAD Part 映射表）；
3. official-3mf 解析：FlowIO 原版主模块/泵模块/管路拓扑几何提取（对照基准）；
4. 产出 docs/research/device-modeling-baseline.md（结论回填 spec §6）。

## D1 器件描述符 + 构建器（核心，~1 天）
1. devices.json pneumatic_devices 各条目增 `geom3d` 块（三接口面，datasheet 图纸直推+出处）；
2. flowio/twin/devices3d/ 五 builder：valve_f0520d / valve_f0520b / pump_zr370（立式校正）/ sensor_xgzp / fittings；
3. 几何断言 TDD：port/terminal/mount 位向径 vs 图纸（红→绿）；校验器（口径/朝向/贯通）。

## D2 连接图谱（~半天）
1. connections.json schema（三类边）+ 校验器（端点存在/口径匹配/六动作路通/悬空=FAIL，TDD）；
2. 主模块内部边（歧管↔阀嘴/测压）+ 模块间 3 边（2 管+1 电缆）+ 通道口 8 边全量落数据。

## D3 模块接口规约（~半天）
docs/module-interface-spec.md：两模块功能/内外三面接口表/模块间 3 边/装配检查项显式（缺管缺缆=功能降级矩阵）。

## D4 集成渲染（~1 天）
1. scene-3d：devices3d 模型替换盒近似；connections.json 驱动管/线渲染（爆炸端跟随）；
2. Web UI：点击器件高亮三类连接；
3. 视觉回归：泵口朝上/引线在位/管路 vs 官方参考图+实物照，截图存证。

## DX 交付（~半天）
1. 全家桶最终绿（L1-L5/flows/graph/check_route/check_fab/test_webapp 55）；
2. BRINGUP 接管指南章节更新（从 connections.json 生成）；
3. 双阶段终审+合并 main+生产重部署。

## 风险
- datasheet 图纸为扫描件（部分尺寸手抄精度 ±0.3）→ 断言容差分级+BRINGUP 卡尺实测关闭；
- FreeCAD 布尔复杂度（多嘴融合）——分件建模+装配体组合（make_pump_module 已证模式）；
- 线束渲染性能（12 引线+2 电缆低面数管即可）。
