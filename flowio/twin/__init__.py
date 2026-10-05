# -*- coding: utf-8 -*-
"""flowio.twin — 孪生域 (OOD 重构核心, spec v2.1 §3.2-§3.4, M2 落地)。

模块图 (继承/组合):
    IActuator (core ABC)
      └─ _DutyActuator ─┬─ _ValveActuator ─┬─ ValveF0520D (10Ω)
                        │                  └─ ValveF0520B (15Ω)
                        └─ PumpZR370 (0.5A 线性)
    BaseModel (core ABC)
      ├─ ElectricalModel   准静态母线解 (electrical_sim 内核迁入)
      ├─ ThermalModel      板级热一阶 (board_model 热段拆出)
      └─ PneumaticModel    气动执行器负载 (board_model 气路段拆出)
    BoardModel = 组合根 façade (has-a 上述三模型; board_model 迁入)

多态落点① (spec §3.4): 场景仿真 total = Σ a.current(state) —— 仿真器零 if-else,
新执行器类型 = 新子类 + 真值条目 + 工厂登记, 零改仿真器 (M5 盲测预演已入
flowio/tests/test_twin.py::test_future_actuator_zero_model_change)。

消费侧: firmware/twin/{electrical_sim,board_model}.py 为薄壳 re-export 本包
(旧调用方 server.py/test_* 零改动); 场景矩阵在 scenarios (验收语料与物理内核分层)。
"""
from flowio.twin.actuators import (PumpZR370, ValveF0520B, ValveF0520D,  # noqa: F401
                                   build_actuators)
from flowio.twin.board import (BOARD_PARAMS, BUCK_EFF, HIST_S, LOGIC_A,  # noqa: F401
                               N_VALVES, TICK, TAU_THERMAL, BoardModel)
from flowio.twin.electrical import (ADAPTER_A, ALARM_NAMES, ALARM_OVERLOAD,  # noqa: F401
                                    ALARM_OVERPRESSURE, ALARM_VACUUM_CLAMP,
                                    VALVE_STATES, VAC_CLAMP_KPA, WORKING_BAND_KPA,
                                    ElectricalModel, load_params, simulate)
from flowio.twin.pneumatic import PneumaticModel                         # noqa: F401
from flowio.twin.scenarios import (SCENARIOS, run_matrix, run_scenario)  # noqa: F401
from flowio.twin.thermal import ThermalModel                             # noqa: F401

__all__ = [
    # actuators (IActuator 子类族)
    "ValveF0520D", "ValveF0520B", "PumpZR370", "build_actuators",
    # electrical (准静态母线解)
    "ElectricalModel", "load_params", "simulate",
    "ADAPTER_A", "WORKING_BAND_KPA", "VAC_CLAMP_KPA",
    "ALARM_OVERLOAD", "ALARM_OVERPRESSURE", "ALARM_VACUUM_CLAMP",
    "ALARM_NAMES", "VALVE_STATES",
    # scenarios (验收语料)
    "SCENARIOS", "run_scenario", "run_matrix",
    # thermal / pneumatic / board (组合根)
    "ThermalModel", "PneumaticModel", "BoardModel",
    "BOARD_PARAMS", "LOGIC_A", "BUCK_EFF", "N_VALVES", "HIST_S", "TICK",
    "TAU_THERMAL",
]
