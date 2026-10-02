"""S2 板级电气孪生纯模型 (stdlib-only: math + collections).

由 server.py 以 ~50ms (TICK=0.1s 对齐) 周期调用 step() 推进：
  阀线圈 RL 电流(解析式) -> 5V 轨负载/压降 -> 3V3 轨 -> 一阶热惯性 -> 600s 环形历史。

设计笔记 (与 test_board_model.py 锚点对齐):
  * 开通:  i = I_inf + (i0 - I_inf) * exp(-dt/tau_on),  tau_on = L/(r_coil+rds)
           —— 100ms 内电流完全建立 (dt/tau ~ 56)。
  * 关断:  i = i0 * exp(-dt/tau_off),  tau_off = L/rds
           —— 续流电流经低侧回路(仅 rds)再循环缓慢释放, 100ms 后残余 ~85.2%
              (e^(-0.1/0.625)=0.852, 测试锚点 0.85)。若按导通同一 tau(1.78ms)
              计算, 100ms 后电流归零, 与测试 b4 锚点矛盾 —— 故关断取续流回路 tau。
无文件 IO、无 numpy; telemetry() 从当前 state 以与 step() 相同的式子重算轨值。
"""

import math
from collections import deque

# ESP32 峰值 (~0.24A) + TCA9548A + CH340 等逻辑负载估算
LOGIC_A = 0.43

# 板级参数 (含来源成色注释: [手册]=datasheet, [仿真]=电路仿真, [实测]=上表测量, [假设]=工程假设)
BOARD_PARAMS = {
    "r_coil": 14.0,    # [假设-行业典型] 阀线圈电阻 14Ω (5V/14Ω ≈ 0.356A 稳态)
    "l_coil": 25e-3,   # [假设] 阀线圈电感 25mH
    "rds": 0.040,      # [手册] AO3400 @ VGS=3.3V 导通电阻 ~40mΩ
    "vbus": 5.0,       # [标称] USB 5V 总线
    "vf_ss34": 0.31,   # [手册] SS34 肖特基正向压降 (5V 轨串入)
    "r_ss34": 0.05,    # [手册] SS34 导通电阻
    "vout3v3": 3.269,  # [实测] buck 标称输出
    "load_reg": 0.012, # [仿真] buck 负载调整率 (V/A)
    "i_pump": 0.35,    # [假设] 泵电机平均电流
    "theta": {         # [手册] 热阻 ℃/W
        "cpu": 35.0,
        "buck": 130.0,
        "mos": 350.0,
    },
}

BUCK_EFF = 0.876          # [仿真] buck 效率
N_VALVES = 8
HIST_S = 600              # 历史窗口长度 (s)
TICK = 0.1                # 名义步长 (s); 历史容量 = HIST_S/TICK = 6000 点
TAU_THERMAL = 30.0        # 板级热时间常数 (s)

# 温升一阶惯性目标功率里的固定 cpu 功率 = LOGIC_A * vout3v3
_P_CPU = LOGIC_A * BOARD_PARAMS["vout3v3"]


class BoardModel:
    """8 阀 RL + 双轨 + 热状态的确定性板级模型。"""

    def __init__(self):
        self.i = [0.0] * N_VALVES          # 各阀线圈电流 (A)
        self.pump = 0.0                    # 最近一次泵命令 (0/1), telemetry 重算负载用
        self.t = 0.0                       # 累计仿真时间 (s)
        self.stale = False                 # server 超时未收到命令时置 True
        self.temp = {"cpu": 25.0, "buck": 25.0, "mos": 25.0}  # 估计结温 (℃)
        self.hist = deque(maxlen=int(HIST_S / TICK))          # 环形历史

    # ------------------------------------------------------------------ step
    def step(self, dt, valves, pump):
        """推进 dt 秒。valves: 8 元命令列表(真值=开), pump: 泵命令(真值=开)。"""
        p = BOARD_PARAMS
        tau_on = p["l_coil"] / (p["r_coil"] + p["rds"])   # 激励回路: L/(r_coil+rds)
        tau_off = p["l_coil"] / p["rds"]                  # 续流回路: L/rds
        i_inf = p["vbus"] / (p["r_coil"] + p["rds"])      # 稳态电流 (开)
        for k in range(N_VALVES):
            on = bool(valves[k]) if k < len(valves) else False
            i0 = self.i[k]
            if on:
                self.i[k] = i_inf + (i0 - i_inf) * math.exp(-dt / tau_on)
            else:
                self.i[k] = i0 * math.exp(-dt / tau_off)  # I_inf=0

        self.pump = 1.0 if pump else 0.0
        load5 = sum(self.i) + p["i_pump"] * self.pump + LOGIC_A
        v5 = p["vbus"] - (p["vf_ss34"] + p["r_ss34"] * load5)
        v33 = p["vout3v3"] - p["load_reg"] * LOGIC_A

        # 温升一阶惯性: T += (T_target - T) * min(1, dt/30),  T_target = 25 + P*theta
        p_buck = v33 * LOGIC_A * (1.0 / BUCK_EFF - 1.0)
        p_mos = max(x * x for x in self.i) * p["rds"]
        for part, pw in (("cpu", _P_CPU), ("buck", p_buck), ("mos", p_mos)):
            t_target = 25.0 + pw * p["theta"][part]
            self.temp[part] += (t_target - self.temp[part]) * min(1.0, dt / TAU_THERMAL)

        self.t += dt
        self.stale = False  # 刚收到命令即视为新鲜
        self.hist.append({"t": self.t, "v5": v5, "v33": v33,
                          "load": load5, "vi": list(self.i)})

    # ------------------------------------------------------------- telemetry
    def telemetry(self):
        """当前快照; 负载/轨压由当前 state 按与 step() 相同公式重算。"""
        p = BOARD_PARAMS
        load5 = sum(self.i) + p["i_pump"] * self.pump + LOGIC_A
        v5 = p["vbus"] - (p["vf_ss34"] + p["r_ss34"] * load5)
        r_loop = p["r_coil"] + p["rds"]
        valves = [{"on": x > 0.01,
                   "i_A": round(x, 3),
                   "p_w": round(x * x * r_loop, 2)} for x in self.i]
        history = {"t": [], "v5": [], "v33": [], "load": [], "vi": []}
        for rec in self.hist:
            for key in history:
                history[key].append(rec[key])
        return {
            "tick": int(self.t / TICK),
            "uptime_s": round(self.t, 3),
            "stale": self.stale,
            "valves": valves,
            "rail_5v": {"v": round(v5, 4), "load_a": round(load5, 4),
                        "p_w": round(v5 * load5, 3)},
            "rail_3v3": {"v": p["vout3v3"], "load_a": LOGIC_A,
                         "ripple_mv": 3.1, "buck_eff": BUCK_EFF,
                         "loss_mw": {"sw": 706, "dcr": 162, "diode": 436,
                                     "switching": 85}},
            "board_p_w": round(v5 * load5, 3),
            "temp_est_c": {k: round(v, 2) for k, v in self.temp.items()},
            "history": history,
        }
