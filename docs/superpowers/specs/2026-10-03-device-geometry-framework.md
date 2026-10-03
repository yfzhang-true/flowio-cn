# Spec: 器件几何与拓扑约束框架（方向感知凸包 + 关系图 + 真实尺寸 + 钻孔避让）

> 日期: 2026-10-03 · 分支: device-geometry · 状态: **待用户审查**
> 触发: 用户指出——充电口/电磁阀等集成器件不能只看凸包，还要**方向、3D 空间位置、相对关系（图算法）、真实尺寸、PCB 打孔**；且不能忘记对标 FlowIO 的功能与集成度。
> 上游: 2026-10-03 CAD 装配大修（spec: 2026-10-03-cad-assembly-truth.md）建立了 z 栈位真相；本框架把"凸包"升级为**带语义的定向几何**。

## 1. 现状审计（本轮程序取证）

### 1.1 朝向正确性没有机器可读来源
P1 的 15 个对外连接器（J1 DC005 / J2 USB-C / J5-J8 4P×4 / J9,J18,J19 4P×3 / J10-J17 2P×8）
物理上全部朝外（由侧槽吻合反推证实），但这是**手工布局的巧合正确**：
- pos.csv 只有 (x, y, rot)，无端口法向语义；
- 本轮审计脚本试算朝向时，基准方向只能靠猜（猜错 5/11）——**没有权威数据源**；
- 没有任何测试能拦截"USB-C 被旋转 180° 朝内"这类错误。

### 1.2 尺寸是估计值，不是器件真值
`case_geom.H` 表的器件尺寸来自人工估值；KiCad 3D 模型又自带噪声（WJ500V 封装
offset(+3.15, +3.5z) vs 焊盘中心，两说真相只能靠角部 relief 兼容）。本轮实测 **JLC
官方属性：WJ500V-5.08-2P Height Above Board = 14.07mm**（KiCad 模型含 3.5 抬升
显示 17.5；当前壳按 17.5 保守设计仍安全，但这是运气不是机制）。

### 1.3 对标 FlowIO（CHI'21, Shtarbanov, MIT Media Lab）的集成差距
论文提取的主模块集成清单 vs FLOWIO-CN P1：

| 能力 | FlowIO 主模块 | FLOWIO-CN P1 | 差距 |
|---|---|---|---|
| 阀 | **7× 常闭电磁阀板载歧管**（2 进/出 + 5 通道） | 8 路外部阀驱动端子（MOSFET+端子） | 阀不板载、无歧管 |
| 压力传感 | 1× 直连歧管（分时复用） | 无 | 全缺 |
| 气路端口 | 5× 气口（充/抽/泄/保持/测） | 无气路 | 全缺 |
| 电源 | 500mAh LiPo **藏于阀下** + USB 充电 | DC005+USB-C 供电输入（SS34 或门） | 无电池/无充电 |
| 传感 | 9-DoF IMU/气压计/光敏 | 无 | 全缺 |
| 扩展 | 14-pin 磁吸 (I2C/SPI/UART/GPIO) | TCA9548A I2C 扩展（板内） | 无模块化接口 |
| 泵模块 | S/M/L 三档（37/90/251g，磁吸+双硅胶管） | 无 | 全缺 |

**结论**：P1 是"驱动器"，FlowIO 是"集成气动平台"。差距不只是器件清单——阀排必须
**边缘布置+气口朝外**、电池必须**低矮置于阀下**（高度栈约束）、歧管必须**与阀同域**
（拓扑约束）。这些正是"方向+3D位置+关系图"要形式化的东西。

## 2. 基线研究结论（本轮检索）

| 需求 | 基线 | 结论 |
|---|---|---|
| 凸包/定向包围盒 | scipy.spatial.ConvexHull；trimesh(`oriented_bounds`) | 板级 33 类器件用 OBB 足够，凸包留作非盒件（WROOM 天线、电感） |
| 碰撞检测 | python-fcl (BerkeleyAutomation, **已归档**→fix-jie fork)；trimesh.CollisionManager | 阶段 1 自实现 OBB-SAT（~100 行零依赖）；阶段 2 再评估 FCL（mesh 级精确） |
| 图算法/布局 | **DREAMPlace/AutoDMP**（GPU 解析式）、**OpenPARF**（FPGA GNN）、**Circuit Training**（RL）；TILOS/MacroPlacement 基准仓 | 面向百万单元 VLSI，杀鸡牛刀；借鉴**连接度驱动+约束求解**思想，用 networkx（二部匹配/力导向）落地板级规模 |
| 装配约束图 | OpenCASCADE/FreeCAD Assembly 约束体系 | 思想对齐：我们的图边=几何约束（port→槽、贴边、避让） |
| 真实尺寸源 | jlcpcb MCP（本轮实证：C8465→HAB 14.07mm、C456012→"Right Angle" 朝向语义、datasheet URL） | **主数据源**，bom-jlc.csv 33 行 C 号全量摄取可行 |
| 检索说明 | aminer MCP 四查询（component placement / convex hull assembly / DREAMPlace / assembly sequence planning）均返回 no data | 本轮以 WebSearch+GitHub 检索替代（aminer 库覆盖面所致，如实记录） |

## 3. 方案对比

**方案 A（推荐）：轻量自建框架，挂接现有单一真相源体系**
`devices.yaml`（真实尺寸+端口语义）+ `device_geom.py`（OBB/端口射线/SAT 碰撞）+
`networkx` 关系图（电气边+空间边）+ L5 测试层；不引入 FCL/求解器。
- 优点：零重依赖；直接替换 case_geom.H 双源；33 器件规模下 force-directed+规则足够；
  测试可入 run_tests.sh 常跑。
- 缺点：mesh 级精确碰撞仍靠 L4 FreeCAD 布尔（保留现状即可）。

**方案 B：trimesh+python-fcl 全 mesh 级 + VLSI 求解器**
- 优点：最精确；自动布局能力强。
- 缺点：FCL 仓库已归档（维护风险）；DREAMPlace/OpenPARF 需 PyTorch/CUDA 环境；
  对 33 器件是过度工程；与 Mimosa"第三方源码树外"约束摩擦大。

**方案 C：KiCad 插件生态（courtyard 检查+freerouting）**
- 只覆盖电气侧 2D，不覆盖 3D 装配/气路方向/外壳联动——不满足需求，弃。

## 4. 方案 A 设计

### D1 器件数据层 `enclosure/devices.yaml`
每器件（33 唯一行 × 字段）：
```yaml
- ref: J10                    # 或 ref_group: [J10..J17]
  lcsc: C8465                 # bom-jlc.csv 键
  dims: {w: 10.16, d: 10.0, hab: 14.07}   # JLC MCP 摄取 (mm)
  port:                        # 端口语义 (datasheet 人工钉一次)
    type: pneumatic_wire       # electrical | barrel | usb | pneumatic_wire
    dir_local: [0, 1, 0]      # rot=0 时端口法向 (KiCad 板系, +Y=上边)
    exit_z: [9.0, 20.0]       # 端口开口的 z 带 (壳系)
  placement: EDGE_OUT          # EDGE_OUT | SURFACE | INTERNAL | KEEPOUT_CENTER
  datasheet: https://www.lcsc.com/datasheet/...C8465.pdf
```
摄取脚本 `tools/ingest_device_dims.py`：读 bom-jlc.csv C 号 → jlcpcb MCP →
属性映射（Height Above Board/尺寸/朝向类）→ 写 yaml（人工只补 port.dir_local）。

### D2 几何核 `enclosure/device_geom.py`（import case_geom，不复制常量）
- `obb(ref)` → 中心/半轴/旋转角（任意 rot，不再只有 90° 特判）；
- `port_ray(ref)` → 端口射线（origin+direction 经 rot 变换到板系/壳系）；
- `hull(ref)` → 非盒件凸包顶点（scipy ConvexHull，可选）；
- `sat_overlap(a, b)` → OBB 分离轴碰撞测试（自实现，零依赖）。

### D3 关系图 `enclosure/device_graph.py`（networkx）
- 电气边：从 flows/网表拓扑（U1→R→Q→J*已存在）；
- 空间边：port→wall slot 绑定（含 B 面 8 槽↔J10-17）、贴边约束、K1 远离热源类；
- 查询：`slots_satisfied()`（二部匹配：每个 EDGE_OUT 器件必须命中一个槽）、
  `placement_advice()`（力导向预布局建议，供人工/KiCad 推挤参考，非强制）。

### D4 钻孔/禁布层
- drl 解析（T9 经验已有）→ NPTH/PTH 孔位+孔径；
- courtyard（F/B_Courtyard.gbr）→ 禁布多边形；
- 断言：器件 OBB ∩ 安装孔区 = ∅；TH 焊盘不落外壳铜柱/槽投影区。

### L5 测试层 `test_device_geom.py`（入 run_tests.sh 第 2c 层）
1. 朝向断言：EDGE_OUT 器件 port_dir·所属壁外法向 > cos45°，且端口射线在 3mm 内
   穿出板边；
2. 贴边断言：EDGE_OUT 中心距最近边 < 该类阈值（连接器 8mm）；
3. 碰撞断言：顶面器件 OBB 两两无交（SAT）；KERPOUT_CENTER 类不落中心区；
4. 图闭环：每个对外 port 有槽、每槽有器件（双向匹配）；
5. 钻孔避让：D4 两断言；
6. 真值一致性：devices.yaml.dims vs case_geom.H vs JLC 属性三方对拍（消除双源）。

### 与 FlowIO 差距的落地方式（本框架如何服务 P2）
框架就绪后，P2 集成路线（阀排/歧管/压力传感/LiPo 充电）的每一步都是**加数据+加断言**：
- 阀排：placement=EDGE_OUT + port.type=pneumatic + 与歧管器件加 SPATIAL_SAME_DOMAIN 边；
- 电池：dims.hab 精确参与 z 栈（FlowIO 把 LiPo 藏在阀下=负 z 空间利用）；
- 泵模块接口：磁吸 4-pin + 双气口 = 新 port 类型，槽位匹配直接复用。
差距表与 P2 候选清单写入 `docs/flowio-parity-gap.md`（本期只出文档不实施）。

## 5. 决策点（请审查时裁定）
1. **WJ500V 高度真值**：JLC 14.07 vs KiCad 模型 17.5。建议壳 TALLEST 收紧至
   14.07+0.6=14.7（总高 29.5→24.2，更紧凑）？还是维持 17.5 保守？→ **建议收紧，
   以 JLC 为准**（板到货实测二次校验）。
2. **碰撞实现**：阶段 1 OBB-SAT 自实现（推荐）vs 直接引 trimesh+FCL。
3. **P2 集成范围**：本期只出差距文档（推荐），还是把"8 路阀板载化"提上 P2 排期？
4. 网表电气边数据源：直接解析 .kicad_sch 网表（准确但解析重）vs 复用 flows 拓扑
   表（轻但仅覆盖主干）？→ 建议阶段 1 用 flows 拓扑，P2 前再上网表解析。

## 6. 不做的事（YAGNI）
- 不引入 GPU 布局求解器/FCL/全 mesh 库（阶段 2 再评估）；
- 不自动改 KiCad 布局（框架输出建议+断言，人工推挤保留决策权）；
- 不在本期实施任何 P2 硬件集成。
