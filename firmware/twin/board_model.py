"""board_model — S2 板级电气孪生纯模型 → M2 薄壳 (shim, spec v2.1 §3.2)。

迁移史:
  * S2: 初版 (8 阀 RL + 双轨 + 热一体式模型, BOARD_PARAMS 手写常量);
  * T7: BOARD_PARAMS [registry] 条目与 devices.json 参数单源同步
    (r_coil 10Ω / i_pump 0.5A / vbus 5.0V);
  * M2 (本形态): 拆分迁至 flowio 包 ——
      flowio/twin/pneumatic.py  PneumaticModel (8 阀 RL 电流 + 泵命令负载)
      flowio/twin/thermal.py    ThermalModel   (cpu/buck/mos 一阶热惯性)
      flowio/twin/board.py      BoardModel = 组合根 façade (has-a 三模型:
                                 pneumatic/thermal/electrical; BOARD_PARAMS 与
                                 [registry]/[手册]/[实测] 溯源注释随迁于彼, 值不动)
    本模块仅 re-export —— 对外公共 API (BoardModel.step/telemetry + 模块常量)
    逐签名兼容, 旧调用方 (server.py / test_board_model.py) 零改动。

设计笔记 (与 test_board_model.py 锚点对齐; 详见 flowio.twin 各模块 docstring):
  * 开通:  i = I_inf + (i0 - I_inf) * exp(-dt/tau_on),  tau_on = L/(r_coil+rds) ≈ 2.49ms
  * 关断:  线圈经 SS14 续流回路释放, 电流过零即被二极管反向截止钳位
          (与 sim_engine._valve 的续流 ODE 同一物理量, 防双源漂移)。
无文件 IO、无 numpy; telemetry() 从当前 state 以与 step() 相同的式子重算轨值。
"""
import sys
from pathlib import Path

_PKG_ROOT = Path(__file__).resolve().parents[2]          # 仓库根 (flowio 包所在)
if str(_PKG_ROOT) not in sys.path:
    sys.path.insert(0, str(_PKG_ROOT))

from flowio.twin.board import (BOARD_PARAMS, BUCK_EFF, HIST_S, LOGIC_A,        # noqa: E402,F401
                               N_VALVES, TICK, TAU_THERMAL, BoardModel)
