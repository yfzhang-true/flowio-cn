"""S2 板级电气孪生纯模型 (stdlib-only: math + collections).

由 server.py 以 ~50ms (TICK=0.1s 对齐) 周期调用 step() 推进：
  阀线圈 RL 电流(解析式) -> 5V 轨负载/压降 -> 3V3 轨 -> 一阶热惯性 -> 600s 环形历史。

设计笔记 (与 test_board_model.py 锚点对齐):
  * 开通:  i = I_inf + (i0 - I_inf) * exp(-dt/tau_on),  tau_on = L/(r_coil+rds) ≈ 1.78ms
           —— 100ms 内电流完全建立 (dt/tau ~ 56)。
  * 关断:  MOS 已断开, 线圈经 SS14 续流回路释放: vcoil = -vf_fw,
           i = max(0, I_off + (i0 - I_off) * exp(-dt/tau_off)),
           tau_off = L/r_coil ≈ 1.79ms,  I_off = -vf_fw/r_coil (负稳态,
           电流过零即被二极管反向截止钳位) —— 与 sim_engine._valve 的
           续流 ODE (VF_FW=0.35, 钳 i>=0) 同一物理量, 防双源漂移。
无文件 IO、无 numpy; telemetry() 从当前 state 以与 step() 相同的式子重算轨值。
"""

import math
import threading
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
    "vf_fw": 0.35,     # [手册] SS14 续流二极管正向压降 (与 sim_engine VF_FW 同源)
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
        self._lock = threading.Lock()      # tick 线程 step() 与 HTTP 线程 telemetry() 互斥
        self._acc = 0.0                    # 历史节流累加器 (满 TICK=0.1s 落一条)

    # ------------------------------------------------------------------ step
    def step(self, dt, valves, pump):
        """推进 dt 秒。valves: 8 元命令列表(真值=开), pump: 泵命令(真值=开)。"""
        with self._lock:                   # 全程持锁: 状态写入与 telemetry 快照互斥
            self._step_locked(dt, valves, pump)

    def _step_locked(self, dt, valves, pump):
        p = BOARD_PARAMS
        tau_on = p["l_coil"] / (p["r_coil"] + p["rds"])   # 激励回路: L/(r_coil+rds)
        tau_off = p["l_coil"] / p["r_coil"]               # 续流回路: L/r_coil (SS14 钳位)
        i_inf = p["vbus"] / (p["r_coil"] + p["rds"])      # 稳态电流 (开)
        i_inf_off = -p["vf_fw"] / p["r_coil"]             # 续流负稳态 (过零截止)
        for k in range(N_VALVES):
            on = bool(valves[k]) if k < len(valves) else False
            i0 = self.i[k]
            if on:
                self.i[k] = i_inf + (i0 - i_inf) * math.exp(-dt / tau_on)
            else:
                i = i_inf_off + (i0 - i_inf_off) * math.exp(-dt / tau_off)
                self.i[k] = i if i > 0.0 else 0.0         # 二极管反向截止钳位

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
        # 历史节流: step 周期 (50ms) < TICK=0.1s, 每步都 append 则 6000 条仅覆盖
        # 300s; 累计满 TICK 才落一条 → 6000 条 = 600s 仿真时间。dt 可达 0.2s
        # (speed=4), while 保证一步补齐 2 条; 时间戳取 0.1s 边界穿越时刻,
        # uptime/tick 语义不变 (仍按真实累计时间)。
        self._acc += dt
        while self._acc >= TICK:
            self._acc -= TICK
            self.hist.append({"t": round(self.t - self._acc, 6), "v5": v5,
                              "v33": v33, "load": load5, "vi": list(self.i)})

    # ------------------------------------------------------------- telemetry
    def telemetry(self):
        """当前快照; 负载/轨压由当前 state 按与 step() 相同公式重算。
        历史快照段持锁拷贝——tick 线程并发 append 会使裸迭代 deque 抛
        'deque mutated during iteration'; dict 组装在锁外做纯计算。"""
        with self._lock:
            i = list(self.i)
            pump = self.pump
            t = self.t
            stale = self.stale
            temp = dict(self.temp)
            hist = list(self.hist)          # 落库后的 rec 不再被改, 浅拷贝即可
        p = BOARD_PARAMS
        load5 = sum(i) + p["i_pump"] * pump + LOGIC_A
        v5 = p["vbus"] - (p["vf_ss34"] + p["r_ss34"] * load5)
        v33 = p["vout3v3"] - p["load_reg"] * LOGIC_A   # 与 step() history v33 同式
        r_loop = p["r_coil"] + p["rds"]
        valves = [{"on": x > 0.01,
                   "i_A": round(x, 3),
                   "p_w": round(x * x * r_loop, 2)} for x in i]
        history = {"t": [], "v5": [], "v33": [], "load": [], "vi": []}
        for rec in hist:
            for key in history:
                history[key].append(rec[key])
        return {
            "tick": int(t / TICK),
            "uptime_s": round(t, 3),
            "stale": stale,
            "valves": valves,
            "rail_5v": {"v": round(v5, 4), "load_a": round(load5, 4),
                        "p_w": round(v5 * load5, 3)},
            # v 与 step()/history 的 v33 同式同值 (vout3v3 - load_reg*LOGIC_A),
            # 消除 telemetry 3.269 vs history 3.2638 的双源漂移; v_nom 保留标称。
            "rail_3v3": {"v": round(v33, 4), "v_nom": p["vout3v3"],
                         "load_a": LOGIC_A,
                         "ripple_mv": 1.0,  # 与 sim_engine buck 默认工况实测一致（@3A）
                         "buck_eff": BUCK_EFF,
                         "loss_mw": {"sw": 706, "dcr": 162, "diode": 436,
                                     "switching": 85}},
            "board_p_w": round(v5 * load5, 3),
            "temp_est_c": {k: round(v, 2) for k, v in temp.items()},
            "history": history,
        }
