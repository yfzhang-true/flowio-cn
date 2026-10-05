# D4 视觉回归存证 — 孪生 3D 器件精确建模 + connections 驱动渲染 (2026-10-05)

> spec: docs/superpowers/specs/2026-10-05-device-modeling-connections-design.md §5/§7(验收 4)
> 截图: 本目录 `d4-*.png` (1680×1050, playwright 无头; 脚本 `firmware/twin/shots_d4.js`,
> 需 8017 孪生服务: `bash firmware/twin/run_tests.sh` 或手动起 `server.py`)。
> 重生成: `cd firmware/twin && node shots_d4.js [输出目录]` (默认落本目录)。

## 截图清单与判定点

| 截图 | 视角/态 | 判定点 (spec E1/E2 校正) |
|---|---|---|
| `d4-pump-top.png` | 泵模块装配位 + **隐壳透视** (截图工具临时 `pump_case.visible=false`, 非场景功能; 泵在封闭腔内, 唯一诚实观查法) | **顶置双嘴 ⌀4.2 垂直于泵轴** (E1: 旧版误建侧嘴); 泵头⌀24/电机⌀27 两段式; 硅胶支架环×2 抱头段/电机段; 电机端面红黑引线; 模块内跳管 (fit_pending 半透明) 自双嘴下行至面板快插 |
| `d4-valve-leads.png` | B 壁 (+Y) 正视塔层 | 11 阀 C 架本体 (devices3d 精确模型, 非盒近似); **红黑引线自阀 -Y 侧出体 → 拱越 (z43.5, 阀顶与歧管块底净空带) → 沿壳外壁下落 → 穿 B 壁 TERM 槽 → 2P 白壳插入 J10-J17** (E2: 旧版引线缺失); 白壳视觉件在插座位; 测压支路自歧管顶过天花过孔垂直下行 |
| `d4-tube-routing.png` | 全局 3/4 (装配态) | **connections.json 驱动管路** (16 管, D4-A 折线): 模块间干管×2 (面板快插→R 壁 S/V 孔), 壳内 S/V/F 竖落管, 通道管 V×N2→CH 过孔, 测压支路 (歧管测压嘴→越歧管顶→天花过孔→XGZP P1); 泵电缆 J23→R 壁槽→模块出线孔→电机端子 |
| `d4-explode-follow.png` | 爆炸 k=1 | 连接边**端点随部件跟随拉伸** (spec §5): 测压支路自歧管层拉至 pcb 层, 模块干管拉伸跨主/泵模块间隙 —— 分装式教学价值可视 |
| `d4-click-highlight.png` | 点击 J10 热点 (raycaster 真点击) | 三类连接**高亮分色** (电气琥珀, 其余压暗); 提示 chip (左下): 器件名 + 气动/电气/机械计数; 热点卡照常弹出 (55 测试契约不破) |

## 与官方参考照/实物照对照

参考照在主仓库 (worktree 外, 绝对路径):

| 孪生截图 | 参照 | 对照结论 |
|---|---|---|
| d4-pump-top.png | `E:/FLOWIO/literature/ZR370-03PM.pdf` p2 图纸 (顶置 2-⌀4.2 出气/进气口标注) + `E:/FLOWIO/资源/实物图/1.png`-`4.png` (整机实物) | 嘴位/朝向/头-电机两段比例一致; 充(S)/吸(V) 固定不可反接 (图纸标注同) |
| d4-valve-leads.png | `E:/FLOWIO/literature/F0520D.pdf` p2 图纸 + 实物照 `E:/FLOWIO/literature/extract/散件/` (p0-p8, 红黑引线+2P 白壳) + `E:/FLOWIO/资源/实物图/电磁阀052/` | C 架比例 (20.5×15×13 + 翻边)、红黑并排引线、白壳插接方向一致; F0520B/VV 总长 28+⌀4.6 顶嘴承插悬置态 (图纸直推) |
| d4-tube-routing.png | `E:/FLOWIO/资源/官方参考/flowio-official-gui-reference.png` (官方 GUI 整机) + `docs/pneumatic-diagram.md` §1-§5 (图谱拓扑真值) | 管路拓扑按 connections.json (机器真值) 而非目测; 官方为集成式单壳, 本机为分装双模块 (1h 决策), 干管跨接为设计意图非偏差 |
| d4-click-highlight.png | — (交互新增, 无官方对应) | spec §5 "点击器件→高亮其三类连接" 落地存证 |

## 已知视觉限制 (诚实记录, 非缺陷遮掩)

1. **引线/管与结构件的过越穿模**: 壳盖 (case_top) 无阀 N2 过孔/引线过孔 (盖开孔属
   enclosure 域待 1a 支架定型), 渲染折线穿过盖板处阅读为"过孔"; VS/VF 竖落管与
   J20/J22 插座体量轻微交叠 (真实走线在插座旁, 折线未让位)。
2. **tube.bend=2 为采购下料名义值**, 渲染折线按最小几何弯折 (2~4 点, 壁孔过越/障碍
   让位必须) —— 段长和仍可核算下料 (D4-A), 逐边路径见
   `firmware/twin/webapp/connections_scene.json` (flowio/twin/connections_render 生成)。
3. **引线桩深** = D2-A "诚实的不精确" (~60mm 视觉桩语义, 端点接真值插座位);
   精确线长/壳内走线属机械冻结后阶段 (spec §8 D2)。
4. V2-V8 N2→CH 的 **x 向让位折线** 按 connections.json 字面映射渲染 (V2→CH2@29.5 等
   与阀列 x 不对齐处出现横行段) —— 图谱映射与壁孔序号的对应关系建议 D2 侧复核
   (见 D4 报告"数据发现")。
