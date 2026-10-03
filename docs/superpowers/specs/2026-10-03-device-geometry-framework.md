# Spec: 器件几何与拓扑约束框架（方向感知凸包 + 关系图 + 真实尺寸 + 钻孔避让）

> 日期: 2026-10-03 · 分支: device-geometry · 状态: **v2 — 决策点已由用户定案，待终审**
> v2 变更: ①四决策点按用户指示定案（trimesh+FCL 直引 / 阀板载化上排期 / 解析网表 / 壳高收紧）；
> ②基线资源已下载本地并精读（`docs/research/2026-10-03-baseline-reading.md`），设计按精读结论细化；
> ③壳高收紧数字修正（v1 口算 24.2 有误，正确 26.07，算式见 §5.1）。
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
offset(+3.15, +3.5z) vs 焊盘中心，两说真相只能靠角部 relief 兼容）。本轮 JLC 官方
属性实测三例：**WJ500V-5.08-2P Height Above Board = 14.07mm**（KiCad 模型含 3.5
抬升显示 17.5）；**DC005 Body Height = 10.9mm**（模型显示 15.1）；**XH 4P 板上高
Z-Height = 7mm**（模型显示 10.4）。模型普遍虚高 3~4mm——当前壳按 17.5 设计是
"用错的模型保守地包住了"，不是机制。

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

## 2. 基线研究结论（v2：已下载到本地并精读，笔记见 `docs/research/2026-10-03-baseline-reading.md`）

| 需求 | 基线（本地路径 `E:/FLOWIO-3rdparty/`） | 精读结论 → 落地 |
|---|---|---|
| 碰撞检测 | **python-fcl 0.7.0.11 + trimesh 5.1.1**（venv 实测：pip 直装 Windows wheel ✓） | `CollisionManager`：add_object/set_transform（爆炸态 O(1) 更新）/in_collision_internal(return_names)/min_distance_*（净空断言）；CCD 备用于装配扫掠 |
| 定向包围盒 | trimesh `bounds.oriented_bounds`（源码精读+实测） | 3D 面法向角度搜索（angle_digits 可控）；旋转盒/圆柱实测恢复正确；对 KiCad STEP 实体做姿态校验；首选仍是 JLC 结构化尺寸直接构盒 |
| 图匹配 | networkx 3.7（实测签名） | `minimum_weight_full_matching`：器件↔壁槽最小权完美匹配，权=端口射线到槽中心距离 |
| 布局范式 | MacroPlacement/CT（CCC 协议精读） | proxy cost = W_wl·HPWL + W_den·密度 + W_cong·拥塞 → **板级化三元组**（WL=网表边欧氏和 / 腔密度 / 槽拥塞）；UCSD 结论：优化好的 SA ≥ RL 且 1/4 资源 → 不引 RL/GPU |
| 可微目标思想 | DREAMPlace DAC'19（论文精读） | 把布局质量写成可计算加性评分函数即可，引擎不引 |
| 异构域约束 | OpenPARF（论文精读） | P2 的"阀域/传感域/电源域/气口域"= resource legality + proximity 形式化，图边带域亲和权重 |
| 真实尺寸源 | jlcpcb MCP（实证三例） | **主数据源**：WJ500V 14.07 / DC005 10.9 / XH4P 7.0（均 HAB 类字段）+ datasheet URL |
| 检索通道 | aminer MCP 六类查询均 `no data`（含 FlowIO 论文本身，服务侧覆盖问题，如实入档）；论文经 arXiv API 标题定位下载；github 无 MCP 挂载，git clone 经代理替代 | **无未解决阻塞** |

## 3. 方案（v2 定案：用户已裁定）

**轻量数据/图框架 + trimesh+FCL 碰撞内核**：
`devices.yaml`（JLC 真实尺寸+端口语义）+ `device_geom.py`（OBB/端口射线/凸包，
基于 trimesh）+ FCL `CollisionManager` 碰撞/净空/（阶段 2）CCD + `networkx`
关系图（网表电气边+空间边）+ L5 测试层。
- 不引 RL/GPU 求解器（UCSD 精读结论：优化好的 SA/规则 ≥ RL 且 1/4 资源；33 类
  器件规模更不需要）；
- VLSI 引擎（DREAMPlace/OpenPARF/CT）作为**评分函数与约束形式化**的思想来源，
  不作运行时依赖；
- FCL 归档风险已由 Windows wheel 实测解除（0.7.0.11）。

弃用方案（留档）：纯自实现 OBB-SAT（v1 推荐，被用户否——mesh 级精度与
`min_distance` 净空断言的价值更大）；KiCad 插件生态（只覆盖电气 2D）。

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
- `obb(ref)` → JLC 尺寸直接构盒（首选）或 KiCad STEP 实体经 `trimesh.bounds.
  oriented_bounds`（姿态校验，angle_digits=1）；任意 rot，不再只有 90° 特判；
- `port_ray(ref)` → 端口射线（origin+direction 经 rot 变换到板系/壳系）；
- `hull(ref)` → 非盒件凸包（trimesh convex hull）；
- 碰撞/净空：`trimesh.collision.CollisionManager`——case STL + 器件 OBB/凸包
  全注册；`in_collision_internal(return_names=True)` 出冲突对名单（测试断言）；
  `min_distance_internal` 出净距（"器件间 ≥ x mm" 断言）；`set_transform` 支持
  爆炸态逐层扫掠（爆炸视图每层 k∈[0,1] 无穿模验证）；FCL CCD 留作阶段 2。
- 运行环境：`E:/FLOWIO-3rdparty/venv-fcl-test`（或正式化为本仓 `tools/venv-cad`，
  requirements: python-fcl/trimesh/networkx/scipy；run_tests.sh 探测该解释器跑 L5）。

### D3 关系图 `enclosure/device_graph.py`（networkx）
- 电气边（**决策 ④：解析网表**）：`kicad-cli sch export netlist` 导出 → S-expr
  解析器 → 网络名→refs 边（剔除电源/地）；网表是权威源（flows 拓扑表仅覆盖主干）；
- 空间边：port→wall slot 绑定（槽清单 import case_geom）、贴边约束、域亲和
  （P2：阀域/传感域/电源域，OpenPARF 异构资源式）；
- 查询：`slots_satisfied()`（`minimum_weight_full_matching`，权=端口射线到槽中心
  距离）；`placement_advice()`（FD 弹簧-势场 + SA 微调 + proxy cost 板级三元组
  评分：WL=网表边欧氏和 / 腔密度 / 槽拥塞）；输出建议与评分，不直接改布局。

### D4 钻孔/禁布层
- drl 解析（T9 经验已有）→ NPTH/PTH 孔位+孔径；
- courtyard（F/B_Courtyard.gbr）→ 禁布多边形；
- 断言：器件 OBB ∩ 安装孔区 = ∅；TH 焊盘不落外壳铜柱/槽投影区。

### L5 测试层 `test_device_geom.py`（入 run_tests.sh，用 venv-cad 解释器）
1. 朝向断言：EDGE_OUT 器件 port_dir·所属壁外法向 > cos45°，且端口射线在 3mm 内
   穿出板边；
2. 贴边断言：EDGE_OUT 中心距最近边 < 该类阈值（连接器 8mm）；
3. 碰撞断言（FCL）：装配态 `in_collision_internal` 无冲突（return_names 空表）；
   爆炸态沿 k∈{0,0.25,0.5,0.75,1} 逐层 `set_transform` 扫掠无穿模；
   `min_distance_internal` ≥ 关键对净距（如 U1↔L1 散热间隙）；
4. 图闭环：`minimum_weight_full_matching` 完美匹配（器件↔唯一槽，双向无孤点）；
5. 钻孔避让：D4 两断言；
6. 真值一致性：devices.yaml.dims vs case_geom.H vs JLC 属性三方对拍（消除双源）。

### 与 FlowIO 差距的落地方式（本框架如何服务 P2）
框架就绪后，P2 集成路线（阀排/歧管/压力传感/LiPo 充电）的每一步都是**加数据+加断言**：
- 阀排：placement=EDGE_OUT + port.type=pneumatic + 与歧管器件加 SPATIAL_SAME_DOMAIN 边；
- 电池：dims.hab 精确参与 z 栈（FlowIO 把 LiPo 藏在阀下=负 z 空间利用）；
- 泵模块接口：磁吸 4-pin + 双气口 = 新 port 类型，槽位匹配直接复用。
差距表与 P2 候选清单写入 `docs/flowio-parity-gap.md`（本期只出文档不实施）。

## 5. 决策点（v2：已由用户定案，2026-10-03）
1. **壳高收紧 ✓**：以 JLC 真值为准。TALLEST = max(器件真高) = WJ500V **14.07**
   （DC005 10.9 / XH4P 7.0 均低于它）。高度链：Z_CEIL = 9.0+14.07+0.6 = **23.67**，
   OUTER_H = 23.67+2.4 = **26.07**（v1 口算"24.2"有误，以本算式为准）；端子槽
   z_hi = 23.27；板到货实测二次校验后如需再调，只改 case_geom 常量全链重生成。
2. **碰撞实现 ✓：直接引 trimesh+FCL**（pip 0.7.0.11 Windows wheel 实测可装；
   依赖 scipy；venv 已建于 E:/FLOWIO-3rdparty/venv-fcl-test，实施时正式化为
   tools/venv-cad 并提交 requirements）。
3. **P2 范围 ✓：先出 FlowIO 差距文档，"8 路阀板载化"提上排期**（M2 里程碑，
   见 §7）。
4. **电气边数据源 ✓：解析网表**（kicad-cli sch export netlist → S-expr 解析；
   权威且覆盖全连接，flows 拓扑表降级为交叉校验）。

## 6. 不做的事（YAGNI）
- 不引入 RL/GPU 布局求解器（UCSD 精读结论：优化好的 SA/规则 ≥ RL；板级规模更不需要）；
- 不自动改 KiCad 布局（框架输出建议+评分+断言，人工推挤保留决策权）；
- 本期不实施 P2 硬件集成（阀板载化按 §7 里程碑排期，前置依赖=本框架 + P1 到货验证）。

## 7. P2 里程碑：8 路阀板载化（决策 ③，提上排期）
- **M2-0 前置**：本框架（T1-T7）交付 + P1 板到货 BRINGUP 通过（供电/8 路驱动实测带载）。
- **M2-1 选型**（JLC MCP 取真值入 devices.yaml）：12V 微型电磁阀（如 JUKA/SMC
  微型，Ø2 快插口，EDGE_OUT+pneumatic 端口）；歧管（3D 打印集成流道或采购 8 联）；
  压力传感（MPRLS 系 I2C，SURFACE 域）；
- **M2-2 布局约束**（框架直接服务）：阀排在边缘带、气口朝外同侧；驱动 MOS（已有
  Q3-Q10）与阀同列就近（域亲和边）；压力传感近歧管（SPATIAL_SAME_DOMAIN 边）；
- **M2-3 交付**：P2 原理图增量 + 布局（placement_advice 评分迭代）+ 外壳重生成
  （阀口槽→气口阵列）+ 孪生/装配全链 + L1-L5 全绿。
- 排期建议：M2 启动于 P1 板验证后（用户 JLC 下单→到货周期内完成 T1-T7）。
