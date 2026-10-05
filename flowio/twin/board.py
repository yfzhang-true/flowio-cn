"""flowio.twin.board — 板级组合根 façade (board_model 迁入, spec v2.1 §3.2 M2)。

组合根 (组合优于继承, 三模型正交):
    BoardModel (façade)
      ├─ has-a PneumaticModel   气动执行器负载 (8 阀 RL 电流 + 泵命令)
      ├─ has-a ThermalModel     板级热一阶惯性 (cpu/buck/mos 结温)
      └─ has-a ElectricalModel  准静态母线解/场景矩阵入口 —— 板级 step 不消费
                                (RL 瞬态 vs 准静态场景解正交), 挂载为组合根成员
                                供 server/API 单点直达 (spec §3.2 类图原文)。

对外公共 API 与 firmware/twin/board_model.py 逐签名兼容 (BoardModel.step/
telemetry + 模块常量), 旧调用方 (server.py / test_board_model.py) 经薄壳零改动;
由 server.py 以 ~50ms (TICK=0.1s 对齐) 周期调用 step() 推进。

BOARD_PARAMS 器件参数与 [registry]/[手册]/[实测]/[仿真]/[假设] 溯源注释自
board_model 随迁 (值不动 —— 与 devices.json 的对应关系对齐 M3 codegen 再收;
[registry] 条目语义上即 pneumatic_devices 真值投影, M3 收口为生成常量)。

无文件 IO、无 numpy; telemetry() 从当前 state 以与 step() 相同的式子重算轨值。
"""
import threading
from collections import deque

from flowio.twin.electrical import ElectricalModel
from flowio.twin.pneumatic import N_VALVES, PneumaticModel
from flowio.twin.thermal import ThermalModel

# ESP32 峰值 (~0.24A) + TCA9548A + CH340 等逻辑负载估算
LOGIC_A = 0.43

# 板级参数 (含来源成色注释: [手册]=datasheet, [仿真]=电路仿真, [实测]=上表测量, [假设]=工程假设,
#           [registry]=devices.json pneumatic_devices 真值——T7 2026-10-03 参数单源同步)
BOARD_PARAMS = {
    "r_coil": 10.0,    # [registry] F0520D rated 4.5V/0.45A → 10Ω（原 14Ω 为行业典型假设已废弃；
                       #           5V 全开拉入 ≈0.50A, 90% 保持=4.5V=额定 0.45A, 与 electrical_sim 同式）
    "l_coil": 25e-3,   # [假设] 阀线圈电感 25mH
    "rds": 0.040,      # [手册] AO3400 @ VGS=3.3V 导通电阻 ~40mΩ
    "vbus": 5.0,       # [registry] drive_policy.rail_v 5.0V
    "vf_ss34": 0.31,   # [手册] SS34 肖特基正向压降 (5V 轨串入)
    "r_ss34": 0.05,    # [手册] SS34 导通电阻
    "vf_fw": 0.35,     # [手册] SS14 续流二极管正向压降 (与 sim_engine VF_FW 同源)
    "vout3v3": 3.269,  # [实测] buck 标称输出
    "load_reg": 0.012, # [仿真] buck 负载调整率 (V/A)
    "i_pump": 0.50,    # [registry] ZR370-03PM load_current_a 0.5A（原 0.35 假设已废弃）
    "theta": {         # [手册] 热阻 ℃/W
        "cpu": 35.0,
        "buck": 130.0,
        "mos": 350.0,
    },
}

BUCK_EFF = 0.876          # [仿真] buck 效率
HIST_S = 600              # 历史窗口长度 (s)
TICK = 0.1                # 名义步长 (s); 历史容量 = HIST_S/TICK = 6000 点
TAU_THERMAL = 30.0        # 板级热时间常数 (s)

# 温升一阶惯性目标功率里的固定 cpu 功率 = LOGIC_A * vout3v3
_P_CPU = LOGIC_A * BOARD_PARAMS["vout3v3"]


class BoardModel:
    """8 阀 RL + 双轨 + 热状态的确定性板级模型 (组合根 façade)。

    子模型 step 由 façade 持锁串行推进 (子模型自身不保证线程安全 ——
    tick 线程 step() 与 HTTP 线程 telemetry() 的互斥是 façade 职责)。
    """

    def __init__(self):
        # ---- 组合根: 三模型装配 (参数注入自 BOARD_PARAMS 单源) ----------------
        self.pneumatic = PneumaticModel(
            r_coil=BOARD_PARAMS["r_coil"], l_coil=BOARD_PARAMS["l_coil"],
            rds=BOARD_PARAMS["rds"], vf_fw=BOARD_PARAMS["vf_fw"],
            i_pump=BOARD_PARAMS["i_pump"], vbus=BOARD_PARAMS["vbus"],
            n_valves=N_VALVES)
        self.thermal = ThermalModel(theta=BOARD_PARAMS["theta"],
                                    tau_s=TAU_THERMAL)
        self.electrical = ElectricalModel()       # 准静态场景入口 (懒加载真值)
        self.t = 0.0                       # 累计仿真时间 (s)
        self.stale = False                 # server 超时未收到命令时置 True
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
        # ---- 气动负载模型 (阀 RL + 泵命令) → 5V 轨负载 -------------------------
        pn = self.pneumatic.step(dt, {"valves": valves, "pump": pump})
        i = pn["i_valves"]
        load5 = sum(i) + pn["i_pump_a"] + LOGIC_A
        v5 = p["vbus"] - (p["vf_ss34"] + p["r_ss34"] * load5)
        v33 = p["vout3v3"] - p["load_reg"] * LOGIC_A

        # ---- 热模型: T_target = 25 + P·θ (buck 损耗恒载 / mos 取最大阀流平方) --
        p_buck = v33 * LOGIC_A * (1.0 / BUCK_EFF - 1.0)
        p_mos = max(x * x for x in i) * p["rds"]
        self.thermal.step(dt, {"powers": {"cpu": _P_CPU, "buck": p_buck,
                                          "mos": p_mos}})

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
                              "v33": v33, "load": load5, "vi": list(i)})

    # ------------------------------------------------------------- telemetry
    def telemetry(self):
        """当前快照; 负载/轨压由当前 state 按与 step() 相同公式重算。
        历史快照段持锁拷贝——tick 线程并发 append 会使裸迭代 deque 抛
        'deque mutated during iteration'; dict 组装在锁外做纯计算。"""
        with self._lock:
            i = list(self.pneumatic.i)
            pump = self.pneumatic.pump
            t = self.t
            stale = self.stale
            temp = dict(self.thermal.temp)
            hist = list(self.hist)          # 落库后的 rec 不再被改, 浅拷贝即可
        p = BOARD_PARAMS
        load5 = sum(i) + p["i_pump"] * pump + LOGIC_A
        v5 = p["vbus"] - (p["vf_ss34"] + p["r_ss34"] * load5)
        v33 = p["vout3v3"] - p["load_reg"] * LOGIC_A   # 与 step() history v33 同式
        # buck 损耗随负载动态 (load5↑ → v5↓ → D↑), 公式与 sim_engine._buck 同源
        # (CCM 损耗分解: Rsw=0.12Ω, DCR=18mΩ, VF=0.42V, vin=5V, FSW=570kHz):
        #   P_sw=I²·0.12·D, P_dcr=I²·0.018, P_diode=0.42·I·(1-D),
        #   P_switching=0.5·5.0·I·20ns·570kHz, D=vout3v3/v5 ≈ 3.269/4.67。
        d = p["vout3v3"] / v5
        i33 = LOGIC_A                                  # 3V3 轨负载 = 逻辑电流
        p_sw = i33 ** 2 * 0.12 * d
        p_dcr = i33 ** 2 * 0.018
        p_diode = 0.42 * i33 * (1.0 - d)
        p_swp = 0.5 * 5.0 * i33 * 20e-9 * 570e3
        p_out = p["vout3v3"] * i33
        buck_eff = p_out / (p_out + p_sw + p_dcr + p_diode + p_swp)
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
                         # 损耗/效率随负载动态（@LOGIC_A 工况, 非旧 @3A 常量快照
                         # {706,162,436,85}），公式与 sim_engine._buck 同源。
                         "buck_eff": round(buck_eff, 4),
                         "loss_mw": {"sw": round(p_sw * 1e3), "dcr": round(p_dcr * 1e3),
                                     "diode": round(p_diode * 1e3),
                                     "switching": round(p_swp * 1e3)}},
            "board_p_w": round(v5 * load5, 3),
            "temp_est_c": {k: round(v, 2) for k, v in temp.items()},
            "history": history,
        }
