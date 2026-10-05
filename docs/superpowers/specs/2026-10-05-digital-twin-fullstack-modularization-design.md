# Spec: 数字孪生产品全流程 SOP 与代码模块化（v2——全栈覆盖 + OOD 设计）

> 日期: 2026-10-05 · worktree: modularization（自 main 90213e6）· 状态: **批准执行（v2.1 三决策全 B + 备份前置）**
> 用户裁定（2026-10-05）：**先备份已跑通版本** → D1=B（types.h 全文件生成替换）/ D2=B（webapp 组件化重写）/
> D3=B（一次性全量重构，不分期）。
> 备份落位：tag `v1.1-pre-modularization` + 分支 `archive/pre-modularization`（均锚 90213e6，
> 含生产在线版本与全套守门绿状态——回滚即 `git reset --hard v1.1-pre-modularization`）。
> 来源: 用户指正——"SOP 的 skill 和代码模块化应覆盖数字孪生**产品研发的全流程**，而不只是布线；
> 代码模块化的目的是提高可维护性，因此引入自顶向下、自底向上、高内聚、低耦合、
> 抽象、继承、封装、多态等技巧。"
> 取代: `2026-10-05-sop-modularization-design.md`（v1：期 B 仅硬件七层、OOD 停留口号——两处缺口如实承认）。

## 0. 现状诚实评估（v1 的两处缺口）

**产品五位一体**：硬件域（sch→pcb→fab）/ 结构域（case/manifold/pump/assembly）/
固件域（pn_core/pn_hal/driver）/ 孪生域（electrical_sim/board_model/sim_engine/twin_api）/
呈现域（webapp/site/部署）。

| 层面 | v1 现状 | 缺口 |
|------|---------|------|
| SOP skill（期 A） | 八节框架名义全流程 | **深度严重不均**：硬件/结构域深（血泪密集），固件/孪生/呈现三域合计不足 10 行（各一行测试命令）；变更矩阵 9 行里 7 行硬件侧 |
| 代码模块化（期 B） | truth/gen/route/geom/flows/netlist/testkit 七层 | **全在硬件侧**——firmware/twin/webapp/site 零覆盖；"高内聚低耦合"无接口/层次/多态实质设计 |

## 1. 设计总纲（自顶向下 × 自底向上双向）

**自顶向下**：从产品愿景分解——数字孪生 = 物理实体（板/结构/气路）与其数字镜像
（参数/模型/仿真/渲染）**共享同一份真值**（devices.json 单源），各域是该真值在不同
介质的投影（铜箔/塑料/C 代码/JS/网页）。架构第一原则：**真值到介质的映射必须是
生成的，不是手抄的**（-58→-60 那次三处手抄事故的根治）。

**自底向上**：从现有资产抽象——P1.1 已绿的全套测试/守门是行为基线，重构=换骨架不换行为
（产物逐字节对拍法，T4/T5 验证过的范式）。

## 2. 目标包结构（全栈，渐进迁移禁 big-bang）

```
flowio/                          # 可安装包（pip -e），全产品共享内核
  core/                          # ★ 抽象层（仅接口与基础类型，零域知识）
    interfaces.py                  # IActuator/ISensor/BaseModel/ITubeNet(ABC)
    truth.py                       # TruthSource：devices.json 封装载载+校验(只读属性)
    errors.py                      # 域异常层次(TruthError/GeomError/RouteError...)
  truth/                         # 真值层：schema/两段解析/pneumatic 谓词(T1 断言迁入)
  hw/                            # 硬件域(自 v1 期B收敛)：sch_gen/pcb_gen/route/(stage1-6,dsn_io,auto6)/netlist/drill
  geom/                          # 结构域：case_geom/device_geom/fcl/manifold/pump_module
  flows/                         # 气路流：flows/hotspots(pneu_geom 并入)
  twin/                          # ★ 孪生域(OOD 重构核心，§3)
  fwgen/                         # ★ 固件域：codegen(params.h 片段/驱动骨架注释块)
  webgen/                        # ★ 呈现域：codegen(params.js)+webapp 组件契约
  testkit/                       # check()/runner/L1-L5+电气仿真分层入口/对拍器(字节级)
  cli.py                         # flowio truth|hw|geom|flows|twin|fwgen|webgen|test|rebuild|codegen <subcmd>
```

## 3. OOD 实质设计（v1 缺失的技巧，逐一落点）

### 3.1 抽象（Abstract）——`core/interfaces.py`
```python
class IActuator(ABC):
    @abstractmethod
    def current(self, state: str) -> float: ...        # state ∈ pull_in/hold/economy/off
    @abstractmethod
    def effective_v(self, duty: float) -> float: ...    # duty×rail
class ISensor(ABC):
    @abstractmethod
    def read(self) -> "Sample": ...                     # +protocol 对象注入(I2CProtocol)
class BaseModel(ABC):
    @abstractmethod
    def params(self) -> "TruthView": ...                # 参数单源视图
    @abstractmethod
    def step(self, dt: float, inputs: dict) -> dict: ...
    @abstractmethod
    def reset(self) -> None: ...
```

### 3.2 继承（Inheritance）——参数化子类
```
IActuator ─┬─ Valve ─┬─ ValveF0520D(10Ω/±45kPa)      # 差异只在 TruthView 参数
           │         └─ ValveF0520B(15Ω/-45kPa)
           └─ PumpZR370(load 0.5A/±120-60kPa)
BaseModel ─┬─ ElectricalModel(准静态母线解=electrical_sim 重构)
           ├─ ThermalModel(板级热一阶=board_model 热段拆出)
           └─ PneumaticModel(p 板模型=board_model 气路段拆出)
BoardModel = 组合根(has-a 三模型, façade 对外)          # 组合优于继承(三模型正交)
```

### 3.3 封装（Encapsulation）
- `TruthSource`：私有 `_load/_validate`，公共只读属性；直接摸 dict 的旧代码一律经视图；
- 各域生成器私有几何常量构建过程，公共只暴露 `generate(out)`+`verify()`。

### 3.4 多态（Polymorphism）——三处消灭 if-else 链
1. 场景仿真：`total = sum(a.current(s) for a in actuators)`——**新增执行器类型零改仿真器**
   （未来无刷泵/比例阀接入=新增子类+真值条目）；
2. 测试 runner：`for m in board.models: m.step(dt)`——模型增减不动 runner；
3. 守门：`for g in gates: g.check(ctx)`——L1-L5/check_route/check_fab/电气仿真统一门协议。

### 3.5 三语参数生成（单一真值的终极形态，v1 完全没有）
```
devices.json ──flowio codegen──┬─ pn_core/params_gen.h    # C：#define 生成片段(DO NOT EDIT 头)
                               ├─ webapp/js/params_gen.js # TS/ES module
                               └─ twin/_params_gen.py     # py(直接 import truth 可省)
```
CI 守门：重生成后 `git diff --exit-code`——**手编生成物立即红**（-58→-60 漏改事故的机器级根治）。
固件 types.h 现有手写常量逐个迁入生成片段（合并策略：生成文件被 types.h include）。

## 4. SOP skill v2（期 A 深化——全流程十二节）

| 节 | v1 状态 | v2 动作 |
|----|---------|---------|
| 0-1 愿景/真值链 | 真值链已有 | 增§0 产品五位一体与真值-介质映射图；真值链扩展固件/呈现（codegen 路径） |
| 2 变更矩阵 | 9 行(7 硬件) | **增 6 行**：固件常量改(走 codegen 勿手编)/孪生模型改(锚点钉值流程)/webapp 改(ES ./+47 测)/传感换型/执行器加型(IActuator 子类三步)/参数改(三语重生成+CI 门) |
| 3 五层测试 | 已全 | 增电气仿真层/守门统一门协议说明 |
| 4 环境铁律 | 16 条 | 保持，增 codegen 手编禁令 |
| 5 硬件流程 | 深 | 收敛为 hw+geom 两节（内容不减） |
| **6 固件开发流程** | 无 | **新**：driver-spec(唯一规格源)→组件实现→selftest→烧录；参数一律 params_gen.h |
| **7 孪生开发流程** | 一行 | **新**：BaseModel 子类开发模板(params/step/reset+锚点钉值测试)+场景矩阵扩展法 |
| **8 呈现域流程** | 无 | **新**：webapp 模块图/importmap/ES ./ 铁律/build_site/gh-pages/生产终验清单 |
| 9-12 评审/选型/部署/盲测 | 已有 | 保持 |
部署脚本 deploy_sop_skill.py 与 rebuild-matrix.json 随之扩（矩阵 +6 行、skill 十二节）。

## 5. 迁移分期（每期独立交付可中断，基线冻结+字节对拍）

| 期 | 内容 | 验收 |
|----|------|------|
| **M0 核心抽象** | core/(interfaces/truth/errors)+truth/ 迁入；electrical_sim 改经 TruthSource | L5/electrical_sim 全绿+行为锚点不变 |
| **M1 hw+geom+flows 挂载** | v1 期 B 七层收敛为子包；旧路径 shim | 全生成产物逐字节一致(uuid 归一化) |
| **M2 孪生域 OOD** | electrical_sim→ElectricalModel；board_model 拆 Thermal/Pneumatic；BoardModel 组合根 | 场景矩阵 12 数值逐一相等+run_tests 0 |
| **M3 三语 codegen** | fwgen/webgen；types.h/js 常量迁移；CI diff 门 | 手编实验翻红；三语常量三方对拍=devices.json |
| **M4 webapp 模块化** | js 七件按组件契约归位(importmap) | test_webapp 47/47+site 字节对拍 |
| **M5 cli+全回归+盲测** | flowio cli 全域；run_tests.sh 切 cli 双跑对拍后收；假想器件/模型全栈走通 | 盲测：新执行器类型三步接入零改仿真器 |
| **A2 SOP skill v2** | §4 十二节扩写+矩阵+6 行+重部署 | 与 M0 并行；盲测二轮 |

## 6. 不做的事（YAGNI）
- 不做微服务/进程隔离/插件市场——单包单进程够用；
- 不做 C 侧 OO（C 用 codegen+注释块，不硬上 C++）；
- webapp 不引入框架（原生 ES module+importmap 即可）；
- 不重写已绿的测试语义（只搬不改断言）。

## 7. 决策记录（2026-10-05 用户裁定：全 B）
- **D1=B 全文件替换**：`pn_core/types.h` 整体成为生成文件——`flowio fwgen` 产出
  （模板段：类型/枚举定义 + 参数段：devices.json 映射 #define），文件头 DO NOT EDIT；
  原手写常量的溯源注释逐条迁入生成器模板（事故出处不丢）。风险与对策：生成器自身
  bug 会波及类型定义 → M3 验收加"生成 types.h 与备份版 diff 逐行为等价语义（类型段
  字节一致+参数段仅值域受控变化）"对拍门。
- **D2=B 组件化重写**：webapp 以 Custom Elements + shadow DOM 重写（每面板一组件：
  DualPumpPWM/ChannelRow/FlowCanvas/TwinScene/TelemetryPanel…），importmap 管依赖；
  ES ./ 铁律保持。行为基线：test_webapp 47 条语义迁移（选择器适配组件 DOM），
  最终 47/47 等价覆盖+新增组件契约单测。
- **D3=B 一次性全量**：M0→M5 工程依赖顺序不变（抽象→挂载→孪生→codegen→web→cli），
  但**交付节奏合一**——一个 worktree 一次走完，末端一次双阶段评审+对拍+合并。
  内部检查点不省略：每步 commit+相关测试绿（守门是纪律不是阶段）；中断恢复靠
  worktree 内 commit 序列（铁律 16 范式）。
- **回滚线**：备份 tag/archive 如上；重构若最终验收不过且无法修复，主树 reset 备份即恢复生产。
