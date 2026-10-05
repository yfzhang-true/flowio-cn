# -*- coding: utf-8 -*-
"""flowio.twin.thermal — 板级热模型 (board_model 热段拆出, spec v2.1 §3.2 M2)。

一阶热惯性 (与 firmware/twin/board_model 原实现逐式同构, 位级不变):
    T_target = t_amb + P × θ          (θ = 结-环境热阻 ℃/W, [手册] 溯源见 board)
    T += (T_target - T) × min(1, dt/τ)  (τ = 板级热时间常数 30s)

封装 (spec §3.3): 参数注入 (theta/tau_s/t_amb) —— 本模块零器件常量
(单源在 flowio.twin.board.BOARD_PARAMS, [手册]/[registry] 溯源注释随迁于彼),
满足 BaseModel.params() "参数单源视图" 契约; 临时结温 self.temp 为唯一可变状态。
"""
from flowio.core.interfaces import BaseModel


class ThermalModel(BaseModel):
    """板级一阶热模型 (cpu/buck/mos 三点结温估计)。"""

    def __init__(self, theta, tau_s, t_amb=25.0):
        self._theta = dict(theta)                 # {part: θ ℃/W}
        self._tau = float(tau_s)                  # 热时间常数 (s)
        self._t_amb = float(t_amb)                # 环境温度 (℃)
        self.temp = {k: float(t_amb) for k in self._theta}

    def params(self) -> dict:
        """参数单源视图 (注入快照; 器件值单源在 board.BOARD_PARAMS)。"""
        return {"theta_c_per_w": dict(self._theta), "tau_s": self._tau,
                "t_amb_c": self._t_amb}

    def step(self, dt: float, inputs: dict) -> dict:
        """推进 dt 秒; inputs = {"powers": {part: W}} → 返回 {"temp_c": {...}}。

        未列出的 part 温度不动 (空输入 = 纯保持); min(1, dt/τ) 钳位防大步过冲。
        """
        powers = (inputs or {}).get("powers") or {}
        for part, pw in powers.items():
            t_target = self._t_amb + pw * self._theta[part]
            self.temp[part] += (t_target - self.temp[part]) * min(1.0, dt / self._tau)
        return {"temp_c": dict(self.temp)}

    def reset(self) -> None:
        """归零到环温 (场景重放/测试复位)。"""
        self.temp = {k: self._t_amb for k in self._theta}
