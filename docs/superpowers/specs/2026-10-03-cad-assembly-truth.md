# Spec: CAD 装配逻辑统一 + CAD 测试体系（用户报障：爆炸视图装配结果错误）

> 日期: 2026-10-03 · 分支: fix-cad-assembly · 状态: 已执行
> 触发: 用户在生产站 (gh-pages) 发现爆炸视图装配结果错误，并指出"原理图/PCB/固件/孪生有单元/接口/功能测试，CAD 没有"。

## 1. 诊断结论（程序取证，非目测）

### 1.1 四个生成源 z 基准互相矛盾（核心病根）

机械真相只有一个：**M3 螺丝穿 PCB 孔自攻入铜柱 → 板必须坐在铜柱顶 z = WALL+PH = 7.4**。

| 文件 | 板底 z | 判定 |
|---|---|---|
| make_case.py | 注释"Z0=2.4 板底面所在"，但铜柱物理顶到 7.4；内腔高/侧槽带全按 2.4 设计 | **自相矛盾** |
| make_meshes.py（孪生 STL/assembly.json 数据源） | 2.4（板趴腔底，被铜柱穿透） | 错 |
| make_flows.py（hotspots/flows） | Z_TOP=4.0 | 错 |
| make_assembly.py（557 实体 STEP） | 7.4 | z 对，但断言过松（±2.5） |

### 1.2 上壳根本不是盖子（第二病根）

`top_cavity` 从 z=2.8 才起挖 → "顶盖"保留了 z 0..2.8 的**完整底板** + 全高四壁 = 一个带底的方盒：
- case_top.stl 3020 个三角形中 2996 个堆在 z<5（程序直方图取证）；
- 与 case_bottom 同占 z 0..19、几乎完全互相穿插（装配视图双底板/同位墙壁）；
- 通风栅刻在"底板"上 = 盖子做反了。

### 1.3 连锁错误

- 外壳总高 19.0 装不下真实装配栈：板顶 9.0 + 端子 11.0 = 20.0 > 内腔顶 19.0（盖不上盖）。
- parts_b.stl 为 84 字节空文件，但 assembly.json 仍列"器件阵-底面"（BOM 无底面器件）。
- hotspots.json z 全按旧板顶 4.0 计算。
- make_assembly.py `Y_FLIP` 双分支从未验证（注释自承"预览若端子排未贴底边改 False 重跑"）。

### 1.4 已验证的黄金事实（修复的地基）

- 坐标映射 `x=PosX, y=−PosY(+OX)`：J10(6.5,68.5)/J2(86,6)/J1(5.5,27) 三锚点断言通过（make_meshes.verify_mapping）。
- 铜柱 ST 与钻孔文件 T9（NPTH 3.2）四孔 **Δ=0.00**。
- 底边端子 J10..J17 = 8×2P 恰对应 TERM_X 8 槽；J1(DC005,板边外伸2.3mm)⊂L@27 槽、J2(TYPE-C,外伸1.15)⊂R@6 槽、4P 端子 J5-J9/J18/J19 ⊂ L/R/T 槽——**槽位 XY 全部吻合，只有 Z 带需重定基准**。
- KiCad PCB STEP：Y∈[−75,0]，555 实体（过滤 136 离群后）。

## 2. 统一装配栈（唯一真相，case_geom.py 单一来源）

```
WALL=2.4 CLR=0.5 OX=2.9 · 板 90×75×1.6 · OW×OH=95.8×80.8
Z_FLOOR=2.4（腔底） → 铜柱 2.4..7.4（PD=2.8 M3自攻底孔, OD=6.3） → 板 7.4..9.0
→ 器件基面 Z_TOP=9.0 → 最高件端子 11.0 → 内腔顶 Z_CEIL=20.6 → 总高 OUTER_H=23.0
顶盖 = 裙边环(内缩0.4, z 13.6..20.6) + 天花板(20.6..23.0, 通风栅8×6, M3过孔)
侧槽统一 z 带: z_lo=Z_TOP−0.2=8.8, z_hi=Z_TOP+组件高+0.2（端子带 8.8..20.2）
下壳 = 底板 0..2.4 + 四壁 2.4..20.6 + 铜柱（外壁到 20.6 止, 与顶盖天花板面接触）
PD 由 4.2 修正为 2.8（M3 自攻底孔 4.2 无咬丝, 属装配逻辑错误）
爆炸向量: case_top +34 / parts_F +16 / pcb 0 / case_bottom −18（爆炸态无重叠, 见 L3 测试）
```

## 3. CAD 测试体系（对标原理图 DRC / 固件单测的范式）

| 层 | 文件 | 手段 | 代表断言 |
|---|---|---|---|
| L1 单元（每网格几何健全） | test_assembly.py（纯 Python, 无 FreeCAD 依赖） | 二进制 STL struct 解析 | pcb bbox == (2.9..92.9, 2.9..77.9, 7.4..9.0) 精确黄金值; **case_top 在 SKIRT_Z0 以下零三角形**（永远拦住"带底板方盒"回归）; 天花板带/底板带/四壁带占据; 铜柱簇 ≈ ST 四点 |
| L2 接口（装配一致性, 事解析何） | 同上 | pos.csv+钻孔+槽位解析 | **钻孔 T9 ↔ ST Δ<0.2（fab⇄CAD 黄金对拍）**; 板 zmin==Z_BOARD（拦"趴底"回归）; 每个越出板边的器件盒必须落入某侧槽矩形（否则 FAIL, 拦穿壁）; 三锚点映射 |
| L3 功能（渲染资产契约） | 同上 | assembly.json+hotspots+scene.js | 清单↔STL 文件一致非空; bbox_mm ↔ 实测并集 ±0.5; 爆炸单调 + 爆炸态包围盒两两不交; hotspots z∈[Z_TOP, 20.0]; scene.js 回退 bbox 同源 |
| L4 干涉（OCC 布尔, FreeCADCmd） | test_assembly_freecad.py | STEP 布尔交集 | top∩bottom 体积 <1mm³; bottom∩PCB(实装位) <5mm³; 装配体 bbox == 黄金 ±0.3; solids ≥500 |

接入 `firmware/twin/run_tests.sh` 为第五层 CAD 套件（L1-L3 恒跑, L4 探测到 FreeCADCmd 才跑）。

## 4. 交付清单

1. `enclosure/case_geom.py`（新）: 常量+映射+锚点, 四个 make_* 全部 import, 杜绝再次分叉。
2. `make_case.py` 重写: 统一栈 + 真顶盖 + 槽带重基准 + PD 修正。
3. `make_meshes.py`/`make_flows.py`: z 改引 case_geom; 去空 parts_B; explode/bbox 更新。
4. `make_assembly.py`: 删 Y_FLIP 双分支（保留经锚点验证的映射）, 断言收紧 ±0.3。
5. 双测试文件 + run_tests.sh 第五层。
6. 重生成全部 CAD/孪生资产, 全量回归, 重建站点, 目视截图（装配+爆炸）交付用户。
