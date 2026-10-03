# 基线精读笔记：trimesh+FCL / MacroPlacement-CT / DREAMPlace / OpenPARF / networkx

> 日期: 2026-10-03 · 用途: 支撑 `specs/2026-10-03-device-geometry-framework.md` v2 决策
> 资源根: 2026-10-03 已整合入仓——第三方仓库 `E:/FLOWIO/third_party/repos/`（gitignored）、
> 文献 `E:/FLOWIO/literature/`（PDF 按惯例 gitignored）、几何核环境 `tools/venv-cad`。
> （原 `E:/FLOWIO-3rdparty/` 树外布局经用户指示整合后废弃）

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

**检索通道记录（v2 修正——用户质疑正确，aminer MCP 可用）**：
早前"六连 no data"是**查询姿势问题**：`search_paper` 的 keyword/长短语参数对本主题
恒空，但以下三个通道工作良好——
- `search_paper_by_title`（**短标题片段**）：FlowIO 论文秒中（DOI 10.1145/3411763.3451513，
  **被引 101**，id 60a7892691e0110affd71d5）；"assembly sequence planning" 命中 **650 篇**；
- `search_person`：Shtarbanov（MIT Media Lab，兴趣 Soft Robotics/Pneumatic/Programmable
  Materials，被引 298，id 6380810dfc451b2d602abc55）；
- `recommend_paper`（topics 数组）：推出 8+6 篇高相关论文（见 §7）。
aminer 的 `pdf` 字段是 md5 引用非公开 URL → 全文以元数据+摘要入档；三篇核心基线
的开放 PDF（arXiv/作者站）已在 `papers/` 本地化。

## 7. aminer 新发现（2026-10-03 补充检索）

### 7.1 装配序列规划（ASP，650 篇的领域）
| 论文 | 年份/被引 | 对框架的价值 |
|---|---|---|
| A Novel Geometric Feasibility Method to Perform ASP Through **Oblique Orientations**（JESTCH, DOI 10.1016/j.jestch.2021.04.013） | 2022/46 | **几何可行性(GF)判定从主轴扩展到斜方向**（ODIM 干涉矩阵）——我们"任意 rot 的 OBB/端口射线"正是板级 GF；装配顺序可行性=序列化的无碰撞路径检查 |
| SOS-ACO for ASP（Front. Mech. Eng., DOI 10.1007/s11465-020-0613-3） | 2021/41 | ASP 是 NP-complete；约束+规则建模进装配模型后用元启发式求解——印证"约束图+SA"路线 |
| Pattern Recognition for Knowledge Transfer in Robotic ASP（RA-L 2020） | 11-50 | 知识迁移视角，备查 |

### 7.2 2026 宏布置前沿（recommend_paper 推送，均为最新工作）
| 论文 | 核心思想 | 对框架的映射 |
|---|---|---|
| VeoPlace: Evolving Macro Placements with **Vision-Language Models** | VLM 视觉空间推理引导布局，WL 再降 10.9% | 远期备选：KiCad 截图+VLM 给布局建议（记录不排期） |
| **OrderPlace**: Placement **Sequences** Via Proxy-Guided LLM Evolution | 摆放**顺序**是决定性维度（次优早决策引发多米诺） | L5 可加"装配/摆放顺序检查"：按序放置逐件碰撞（FCL CCD/逐态）|
| Expertise Can Be Helpful for RL-based Macro Placement | 专家知识注入：**periphery bias / I/O keepout constraints** / macro grouping | **periphery bias 与 I/O keepout 正是 EDGE_OUT 的 EDA 学名**——我们的贴边+禁布断言有文献依据 |
| RollPlace（MCTS rollout） / MCTS-RL / LightPlace（轻量连接感知） | 搜索与轻量化范式 | 印证轻量路线；LightPlace"虚拟宏插入"对 P2 阀排预布局有启发 |

### 7.3 软体机器人应用语境（FlowIO 差距文档的相关工作素材）
- **Rehabilitation Hand Exoskeleton（EBPAM+ANFIS，2026）**：康复手套 <100g、自适应模糊神经控制——**正是 FLOWIO-CN 的 B2B 目标场景**，佐证"阀板载化+轻量化"路线的市场侧依据；
- RehapSpine（PMA 背部助力）、BeetleBot（集成多模态软体平台）、Sumbrella（软体服饰 HRI）——
  可穿戴气动平台的当代谱系，FlowIO（101 引）是其中的工具链标杆。

### 7.4 FlowIO 权威画像（aminer 详情）
被引 **101**；关键词 Platforms/Toolkits/Control Systems/Soft Robotics/Programmable
Materials/Wearables/Arduino；一作 Shtarbanov（MIT Media Lab）。

## 8. GitHub 系统检索全景（2026-10-03 补充，api.github.com 经代理）

| 轴向 | 检索词 | 结果 |
|---|---|---|
| KiCad 3D 碰撞/装配 | kicad collision 3D assembly | **0**——KiCad 生态无 3D 装配碰撞工具 → 我们的 L5 填补真空 |
| 电子外壳生成器 | electronic enclosure generator (pcb) / openscad cadquery | **0**——参数化电子外壳无现成轮子 → make_case.py 自研路线无替代品 |
| FCL python 分叉 | python-fcl in:name | 9 个，皆陈旧（benureau 2014 / rxjia-octomap 2024）→ pip `python-fcl` 0.7.0.11 仍是实际最优 |
| KiCad 自动布局 | kicad automatic component placement | 2 个小库 → **KiCad-Autoplace 已克隆**（见下） |
| 装配序列/约束图 | assembly sequence planning python graph | 1 个 → **AOG-Generation 已克隆**（见下） |
| PCB 布局 AI | pcb component placement optimization python | **pcb-designer-ai-agent 已克隆**（★131，LLM 端到端，背景参考） |

### 8.1 新克隆三库精读要点
- **DTU-EKB/KiCad-Autoplace**（★2，活跃 2026-09）：连接感知自动布局+布线桌面应用。
  **"Connectors on edges"（点选连接器→自动贴边布置）正是我们 EDGE_OUT 的现成实现**；
  多种子布局画廊、FreeRouting 联动、路由驱动再退火。规模小（教学向）但验证了
  "连接度+贴边"路线可落地；其布局评分/退火实现可作 D3 placement_advice 的工程参考。
- **wzl-muenker/AOG-Generation**（★8，2021）：从 CAD 提取 **liaison（连接图）+
  moving wedge（可移除方向楔）** 约束 → AND/OR 图（自顶向下/自底向上两种生成法），
  表征产品全部可行装配序列。**moving wedge 概念与我们 port_ray/装配方向语义同构**；
  AOG 是 L5"装配顺序检查"的成熟数据结构（论文级实现，py3.7，含离心泵/离合器案例）。
- **assalas/pcb-designer-ai-agent**（★131，活跃 2026-10）：LLM 自然语言→网表→IPC
  封装→.kicad_pcb 端到端。无几何严谨性（无碰撞/朝向检查）——恰反衬我们框架的
  价值定位：**AI 生成布局可以快，但"对不对"要靠几何约束测试层守门**。

## 9. 付费墙论文全文精读（用户 2026-10-03 下载 8 篇至 papers/）

### 9.1 逐篇要点
| 论文（出处） | 方法核心 | 结果 | → 框架映射 |
|---|---|---|---|
| **ODIM 斜方向几何可行性**（JESTCH 2022, 16p） | 几何可行性 GF 是装配前置谓词（无碰撞路径）；自动化 GF 此前仅限主轴、斜方向需人工；提出斜方向干涉矩阵 ODIM 扩展到任意方向，接入既有装配规划器 | 真实产品验证 | **我们的 FCL 方向查询/CCD = 板级任意方向 GF 的现代实现**（比矩阵法直接）；L5 第 7 项 = GF 序列化 |
| **SOS-ACO**（Front. Mech. Eng. 2021, 17p） | ASP 为 NP-complete；装配约束+规则建模进装配模型保证合理序列；SOS 自适应调 ACO 参数 | 迭代次数少于纯 ACO，鲁棒 | 约束图→元启发式的范式印证；33 器件用规则+SA 足矣 |
| **AlphaChip**（Nature 2021, 23p，正主一手） | RL 顺序放宏到网格；状态=网表边 GCN 嵌入+当前宏嵌入+**可行性掩码（密度掩码定义合法放置）**；动作=网格单元；奖励=终态 −proxy cost；预训练 48h×20 worker（每人 1 Volta GPU+10 CPU），微调 16 worker≤6h | TPU 块（预训/测试宏数 107/131，生产>500） | CCC 一手确认；**可行性掩码=硬约束先于优化**（我们 L5 断言层即掩码）；其算力门槛反证"板级不引 RL" |
| **AlphaChip Addendum**（Nature 2024, 2p） | 官方澄清：宏数更正、补充引文、共同一作说明 | — | 与 UCSD 评估（arXiv 2302.11014）构成争议两面，均已本地 |
| **Expertise-RL**（**ICLR 2026**, 24p） | (1) 专家知识注入：dataflow guidance / **periphery bias** / macro grouping / **I/O keepout constraints**；(2) 专家工作流模仿（后端 PPA 反馈+偏好优化） | ICCAD2015+OpenROAD：TNS −32.53% / WNS −7.74% | **EDGE_OUT 的 EDA 学名实锤（periphery bias + I/O keepout）**；macro grouping ↔ 域亲和边（阀域/传感域） |
| **OrderPlace**（ICML'26 投稿, 35p） | 摆放顺序=被静态启发式统治的"时间维"，次优早决策→**不可逆多米诺**；LLM 进化 code 级排序策略（静态打分→物理启发动态）；**greedy probe 代理评估**降序列评估成本 | ISPD2005：WL −34.04%/−14.08% vs WireMask-EA/EGPlace | L5 第 7 项（装配顺序逐态无碰撞）文献依据；greedy probe 思想可用于 placement_advice 的廉价评分 |
| **RollPlace**（**IEEE TCAD 45(7) 2026**, 14p） | 两阶段：ML/启发式出初始布局→只精调特定宏；MCTS 平衡探索/利用+rollout 局部搜索，绕开 RL 顺序生成的约束传播 | ISPD2005 SOTA + OpenROAD 19 基准 e2e | "先粗后精+局部调整"与我们的 FD+SA 微调同构 |
| **VeoPlace**（See It to Place It, 29p） | VLM 空间推理把基础策略约束到画布子区域；VLM 提案经进化搜索按布局质量迭代 | 7 基准中 4 个 SOTA（WL −10.9% 均值） | 远期备选（KiCad 截图+VLM 布局建议）已入档不排期 |

### 9.2 全文精读后的增量结论
1. **"可行性掩码先于优化"是一手方法论**（AlphaChip 的 density mask、Expertise-RL 的
   I/O keepout、ODIM 的 GF 谓词三处同构）：我们的 L5 断言层本质就是板级可行性掩码，
   placement_advice 只在掩码内搜索——设计定位获得三重文献背书。
2. **EDGE_OUT 有了 ICLR 级定名的学术对应**（periphery bias + I/O keepout），
   spec 与笔记中的术语表述可对外引用。
3. **摆放/装配顺序是独立优化维**（OrderPlace 多米诺效应 + ODIM 的序列化 GF）：
   L5 第 7 项从"可选"升为"应有"（spec v2.1 已含）。

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
