# -*- coding: utf-8 -*-
"""flowio.core.interfaces — 纯抽象层 (spec v2.1 §3.1/§3.4, 零域知识)。

仅接口与基础类型: 不 import 任何域模块, 不含器件/单位/文件路径知识。
OOD 落点:
  * 抽象 —— IActuator/ISensor/BaseModel 三族 ABC, 差异下沉到子类 (M2 参数化子类);
  * 多态 —— 三处 if-else 链的消灭入口 (spec §3.4):
      ① 场景仿真: total = sum(a.current(s) for a in actuators)  新执行器零改仿真器;
      ② 测试 runner: for m in board.models: m.step(dt)           模型增减不动 runner;
      ③ 守门: for g in gates: g.check(ctx)                       统一门协议 (M5)。

M0 契约 (实现者必读):
  * IActuator.current 的 state ∈ {"pull_in", "hold", "economy", "off"}
    (吸入瞬态 / 全开保持 / 节能保持 / 关断; 孪生域现行 "full_open" 即 "hold");
  * IActuator.duty 为具体报告钩子 (非抽象, M2-R①): 覆写后与 current 同源,
    未覆写调用即 fail-loud;
  * ISensor.read 返回 Sample (= dict, 键由具体传感协议定义), protocol 为
    协议对象注入位 (如 I2C 协议), M0 占位 None, M2 绑定;
  * BaseModel.params 返回参数单源视图 (dict), step 推进一个时间步, reset 归零。
"""
from abc import ABC, abstractmethod


class IActuator(ABC):
    """执行器抽象 (阀/泵/未来无刷泵/比例阀……)。"""

    @property
    @abstractmethod
    def ref(self) -> str:
        """位号 (如 "V1"/"VS"/"P1"), 真值 refs 的单条展开。"""

    @abstractmethod
    def current(self, state: str) -> float:
        """给定状态返回稳/瞬态电流 (A)。state ∈ pull_in/hold/economy/off。"""

    @abstractmethod
    def effective_v(self, duty: float) -> float:
        """有效电压 = duty × 母线轨压 (PWM 调制)。"""

    def duty(self, state: str) -> float:
        """报告钩子 (M2-R①): 状态 → 该执行器实际驱动占空比。

        仿真报告的 duty/eff_v 必须与 current(state) 同源 (执行器侧申报),
        而非调用方的策略表 —— 注入异构执行器时两者才会分叉。具体执行器
        覆写本钩子 (阀族 = 四态策略表, 泵 = off/95%/100%); 基类默认
        fail-loud: 未申报驱动量的执行器一进报告层即暴露。
        """
        raise NotImplementedError(
            "%s 未覆写 duty(state) —— 报告层需要与 current 同源的实际占空比"
            % type(self).__name__)


class ISensor(ABC):
    """传感器抽象 (压力/温度/未来电流计……)。

    protocol: 协议对象注入位 (构造或绑定后 read 经它取数), M0 占位。
    """

    protocol = None

    @abstractmethod
    def read(self) -> dict:
        """读取一次 → Sample (dict; 键由具体传感协议定义)。"""


class BaseModel(ABC):
    """孪生模型抽象 (ElectricalModel/ThermalModel/PneumaticModel 的公共根, M2)。"""

    @abstractmethod
    def params(self) -> dict:
        """参数单源视图 (devices.json 投影, 禁手抄)。"""

    @abstractmethod
    def step(self, dt: float, inputs: dict) -> dict:
        """推进 dt 秒, 消费 inputs (上级模型输出/外部激励), 返回本步输出。"""

    @abstractmethod
    def reset(self) -> None:
        """归零到初始状态 (场景重放/测试复位)。"""
