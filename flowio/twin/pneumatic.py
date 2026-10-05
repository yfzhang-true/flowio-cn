# -*- coding: utf-8 -*-
"""flowio.twin.pneumatic — 板级气动负载模型 (board_model 气路/执行器负载段拆出, M2)。

8 通道阀线圈 RL 电流解析式 + 泵命令负载 (与 firmware/twin/board_model 原实现
逐式同构, 位级不变):
  * 开通:  i = I_inf + (i0 - I_inf)·exp(-dt/τ_on),  τ_on = L/(r_coil+rds) ≈ 2.49ms
           —— 100ms 吸入窗内电流完全建立 (dt/τ ~ 40);
  * 关断:  MOS 已断开, 线圈经 SS14 续流回路释放: i = max(0, I_off + (i0-I_off)·
           exp(-dt/τ_off)), τ_off = L/r_coil ≈ 2.5ms, I_off = -vf_fw/r_coil (负稳态,
           电流过零即被二极管反向截止钳位) —— 与 sim_engine._valve 的续流 ODE
           (VF_FW=0.35, 钳 i>=0) 同一物理量, 防双源漂移。

封装 (spec §3.3): 参数注入 (r_coil/l_coil/rds/vf_fw/i_pump/vbus) —— 本模块
零器件常量 (单源在 flowio.twin.board.BOARD_PARAMS, [registry]/[手册]/[假设]
溯源注释随迁于彼); 可变状态 = 各阀线圈电流 self.i + 泵命令 self.pump。
"""
import math

from flowio.core.interfaces import BaseModel

N_VALVES = 8    # 通道阀拓扑数 (板拓扑常量 V1-V8, 非 devices.json 器件参数)


class PneumaticModel(BaseModel):
    """8 通道阀 RL + 泵命令的气动负载模型 (板级 5V 轨的执行器负载源)。"""

    def __init__(self, r_coil, l_coil, rds, vf_fw, i_pump, vbus,
                 n_valves=N_VALVES):
        self._r_coil = float(r_coil)      # [registry] 阀线圈电阻 (值单源: board)
        self._l_coil = float(l_coil)      # [假设]   阀线圈电感
        self._rds = float(rds)            # [手册]   MOS 导通电阻
        self._vf_fw = float(vf_fw)        # [手册]   续流二极管正向压降
        self._i_pump = float(i_pump)      # [registry] 泵负载电流
        self._vbus = float(vbus)          # [registry] 5V 轨压
        self._n = int(n_valves)
        self.i = [0.0] * self._n          # 各阀线圈电流 (A)
        self.pump = 0.0                   # 最近一次泵命令 (0/1)

    def params(self) -> dict:
        """参数单源视图 (注入快照; 器件值单源在 board.BOARD_PARAMS)。"""
        return {"r_coil": self._r_coil, "l_coil": self._l_coil, "rds": self._rds,
                "vf_fw": self._vf_fw, "i_pump": self._i_pump, "vbus": self._vbus,
                "n_valves": self._n}

    def step(self, dt: float, inputs: dict) -> dict:
        """推进 dt 秒; inputs = {"valves": 8 元命令列表(真值=开), "pump": 命令}。

        返回 {"i_valves": [...], "pump": 0/1, "i_pump_a": 泵负载电流}。
        """
        valves = (inputs or {}).get("valves") or []
        pump_cmd = bool((inputs or {}).get("pump"))
        tau_on = self._l_coil / (self._r_coil + self._rds)   # 激励回路 L/(r_coil+rds)
        tau_off = self._l_coil / self._r_coil                # 续流回路 L/r_coil (SS14 钳位)
        i_inf = self._vbus / (self._r_coil + self._rds)      # 稳态电流 (开)
        i_inf_off = -self._vf_fw / self._r_coil              # 续流负稳态 (过零截止)
        for k in range(self._n):
            on = bool(valves[k]) if k < len(valves) else False
            i0 = self.i[k]
            if on:
                self.i[k] = i_inf + (i0 - i_inf) * math.exp(-dt / tau_on)
            else:
                i = i_inf_off + (i0 - i_inf_off) * math.exp(-dt / tau_off)
                self.i[k] = i if i > 0.0 else 0.0            # 二极管反向截止钳位
        self.pump = 1.0 if pump_cmd else 0.0
        return {"i_valves": list(self.i), "pump": self.pump,
                "i_pump_a": self._i_pump * self.pump}

    def reset(self) -> None:
        """归零 (线圈电流 0, 泵命令 0)。"""
        self.i = [0.0] * self._n
        self.pump = 0.0
