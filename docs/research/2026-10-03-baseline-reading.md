# 基线精读笔记：trimesh+FCL / MacroPlacement-CT / DREAMPlace / OpenPARF / networkx

> 日期: 2026-10-03 · 用途: 支撑 `specs/2026-10-03-device-geometry-framework.md` v2 决策
> 资源根: `E:/FLOWIO-3rdparty/`（Mimosa 铁律: 第三方源码项目树外）

## 0. 本地资源清单（全部已下载可离线重读）

| 资源 | 路径 | 状态 |
|---|---|---|
| MacroPlacement (TILOS) | `repos/MacroPlacement/` | 克隆 ✓ 含 Docs/ProxyCost、CodeElements/{Clustering,FDPlacement,SimulatedAnnealing,EvalCT} |
| DREAMPlace | `repos/DREAMPlace/` | 克隆 ✓（含 benchmarks/dreamplace 源码） |
| OpenPARF (PKU-IDEA) | `repos/OpenPARF/` | 克隆 ✓ |
| python-fcl | `repos/python-fcl/` | 克隆 ✓（README 含完整 API 说明） |
| trimesh 5.1.1 | `venv-fcl-test/Lib/site-packages/trimesh/`（pip 安装版，源码可读） | ✓（git 克隆被中断损坏，弃；以实际依赖版本源码为准） |
| DREAMPlace 论文 DAC'19 | `papers/dreamplace_dac2019.pdf`（6 页，yibolin.com 预印本） | ✓ 已读 |
| OpenPARF 论文 | `papers/arxiv_2306.16665.pdf`（4 页） | ✓ 已读 |
| UCSD CT 评估（更新版） | `papers/arxiv_2302.11014.pdf`（16 页） | ✓ 已读 |
| 可行性 venv | `venv-fcl-test/`（fcl 0.7.0.11 + trimesh 5.1.1 + networkx 3.7 + scipy） | 冒烟通过 |

**检索通道记录**：aminer MCP 六类查询（英文标题/中文关键词/FlowIO 论文本身）均返回
`no data`（服务侧覆盖问题，非本地故障）；论文改经 arXiv API 按标题精确定位下载（曾用
猜测 ID 下载到 4 篇无关论文，已识别并删除，未引用）；本会话无 github MCP 挂载，git
clone 经代理 7877 替代完成。**无未解决阻塞，无需向用户求助。**

## 1. trimesh + python-fcl（碰撞栈，已实测）

### 1.1 安装可行性（Windows 关键风险，已解除）
- `pip install python-fcl` 直接成功（**0.7.0.11 现成 Windows wheel**）；trimesh 5.1.1、
  networkx 3.7、scipy 依赖链全通。
- "上游仓库归档"（BerkeleyAutomation）对可用性无影响：wheel 自包含 FCL 二进制。

### 1.2 CollisionManager API（`trimesh/collision.py` 源码精读）
- `add_object(name, mesh, transform=None)` — 注册命名碰撞体（mesh 或图元）；
- `set_transform(name, transform)` — **增量更新位姿，无需重建** → 爆炸视图逐层
  扫掠碰撞检查可用它做 O(1) 更新；
- `in_collision_internal(return_names, return_data)` — 集内两两碰撞，可返回
  冲突对名单与接触点（ContactData: normal/point/depth）；
- `in_collision_single(mesh, transform)` — 外来几何 vs 整集（装配体合并检查）；
- `min_distance_internal/other/single` — 最小间距（DistanceData: point/point）→
  "器件间净空 ≥ x mm" 断言直接可用。
- python-fcl 层（README）：`CollisionObject = CollisionGeometry + Transform`；几何含
  Box/Sphere/Cylinder/**Convex**/BVH-Mesh；查询三类：碰撞 / 距离 / **连续碰撞 CCD**
  （运动扫掠）——CCD 留作装配动画碰撞扫掠的阶段 2 选项。

### 1.3 oriented_bounds（OBB，`trimesh/bounds.py` 源码精读 + 实测）
- 3D：对凸包面法向做角度搜索（`angle_digits` 控精度，1 位小数即快且够用），
  返回 `to_origin` 变换 + extents；共面退化有专门路径（qhull QbB + 边投影，
  rotating-calipers 思想）。
- 实测：旋转 0.6rad 的 20×4×4 盒正确恢复（4,4,20 主轴序）；圆柱 → (9.95,9.95,10)。
- 用法：KiCad STEP 单实体 → trimesh mesh → `oriented_bounds` 得"真实姿态包围盒"，
  替代我们手工 H 表估值；或直接用 JLC 结构化尺寸构盒（更快，作首选，OBB 作校验）。

## 2. MacroPlacement / Circuit Training（CCC 协议，`Docs/ProxyCost` + Clustering README 精读）
- **CCC** = Clustering（hMETIS 超图聚类标准单元→千级 soft macro）→ Constraints
  （canvas 划网格 + 宏放置顺序）→ Cost（**proxy cost = W_wl·HPWL + W_den·密度 +
  W_cong·拥塞** 加权和）；宏放完后 **力导向（FD）** 摆 cluster；RL 只做宏的顺序决策。
- UCSD 更新版评估核心结论：**精心优化的模拟退火（SA）与 CT 相当或更优，且同时间
  预算下仅用 1/4 资源**；"经典启发式在组合优化上依然有效"。
- **对我们的映射**：① 板级 33 类器件 → RL/GPU 求解器无必要，规则+SA+匹配足够
  （与决策 2 的轻量路线互相印证，但碰撞内核升级为 FCL）；② proxy cost 三元组
  **直接板级化**：WL=网表边欧氏长度和（网表解析后可得）、密度=壳腔 OBB 占用率、
  拥塞=壁槽/逃逸通道冲突数 → L5 的 placement_advice 评分函数。

## 3. DREAMPlace（DAC'19 预印本精读）
- 核心：把解析式布局（min WL s.t. 无重叠）**等价改写为神经网络训练**（可微的
  WL/density 核），PyTorch 反向传播即梯度流，30× 加速、质量不降。
- 对我们：思想可借（**把布局目标写成可计算的加性评分函数**，供 SA/FD 迭代），
  引擎不引（GPU/PyTorch 对 33 器件是屠龙刀）。

## 4. OpenPARF（arXiv 2306.16665 精读）
- FPGA 异构布局：目标 = min WL **同时** 满足 SLICEL/SLICEM 资源异构、可布通性、
  时钟可行性——即"**器件有类型域，放置必须落在合法域且与电气邻近对象靠近**"。
- 对我们的映射：P2 集成后器件分域（阀域/传感域/电源域/气路口域），图边带"域亲和"
  权重——OpenPARF 的异构约束形式化正是"电磁阀必须在边缘+气口朝外"这类约束的
  学术表述（resource legality + proximity）。

## 5. networkx 3.7（装好实测）
- `networkx.algorithms.bipartite.hopcroft_karp_matching(G, top_nodes)`（最大匹配）；
- `minimum_weight_full_matching(G, top_nodes, weight)`（**最小权完美匹配**）→
  器件↔壁槽匹配用它：边权 = 器件端口射线到槽中心的距离（偏好编码进权重）。
- FD 布局建议用 `spring_layout` 的经典弹簧模型改造（连接边=弹簧、同域=吸引、
  壁=边界势）。

## 6. 精读 → 框架的落地决策（写入 spec v2）
| 框架部件 | 采用 | 来源依据 |
|---|---|---|
| D2 碰撞内核 | `trimesh.collision.CollisionManager`（吃 case STL+器件 OBB/凸包 mesh；`set_transform` 支持爆炸态扫掠；`min_distance_*` 作净空断言） | §1.2 实测 |
| D2 包围体 | JLC 结构化尺寸构盒（首选）+ `oriented_bounds` 对 KiCad STEP 实体校验（次选） | §1.3 |
| D3 匹配 | `minimum_weight_full_matching`（端口射线→槽中心距离为权） | §5 |
| D3 评分 | proxy cost 板级化三元组（WL/腔密度/槽拥塞） | §2 |
| D3 布局建议 | FD（弹簧-势场），SA 微调；不引 RL/GPU | §2 UCSD 结论 |
| P2 约束形式化 | 异构资源域 + 域亲和边（OpenPARF 式） | §4 |
| 装配动画扫掠 | FCL CCD（阶段 2 可选） | §1.2 |
