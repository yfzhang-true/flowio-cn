# -*- coding: utf-8 -*-
"""sim_engine — FLOWIO-CN 孪生平台 S1 参数化仿真引擎.

把 hardware/flowio-p1/tools/sim (已归档 firmware/twin/deprecated/sim-legacy,
真源=本文件) 四电路仿真 (buck / dior / valve / i2c) 重构为
参数化纯函数模块, 供后端重算端点调用: run(circuit, params) 返回
{circuit, params, metrics, waves, notes}, 无文件/全局副作用, 仅 stdlib math.

物理内核与归档 sim-legacy 逐函数对照移植, 数值锚点:
  buck  : VOUT_T = 0.8*(1+10k/3.24k) = 3.269V, 稳态纹波 <50mV @3A,
          闭环 KP=0.3 KI=2500 D0=VOUT_T/vin, dt=TSW/140, ss=0.5ms,
          sim 2.5ms 取 T>2.2ms 稳态段; 效率含 Rsw/DCR/二极管/开关(20ns)/ESR 五项
  dior  : SS34 指数模型 Is=1e-7 n=1.2, 不动点迭代 (vo += 0.05*(ΣI - vo/RL))
  valve : 解析栅极 exp(±dt/τg) + RL 一阶欧拉 dt=2e-5, 3 周期取末周期峰值 ≈0.498A (r_coil=10Ω registry)
  i2c   : 一阶 RC, tr = 2.2·τ, 波形取 8τ
"""
from math import exp

import board_model  # noqa: E402  (M2: r_coil 默认值单源经组合根 BOARD_PARAMS [registry];
                   #  board_model 为薄壳 → flowio.twin.board; 惰性导入避免环: board 不依赖本模块)


class ParamError(ValueError):
    """电路名未知 / 参数名未知 / 类型错误 / 超出允许范围."""


# ---------------------------------------------------------------- 参数域表
# (参数名, 下限, 上限, 默认值) —— 默认值与 BOM/原仿真一致 (buck Cout=100+10+3µF)
# r_coil 默认 = BOARD_PARAMS["r_coil"] (registry F0520D 4.5V/0.45A=10Ω, M2 起
# 经组合根 BoardModel 单源 —— 值不变 10.0, test_sim_engine 锚点 0.498A 不动)
SPEC = {
    "buck": [
        ("vin", 3.8, 5.5, 5.0),        # 输入电压 (DC/USB 双源轨)
        ("iload", 0.1, 3.0, 3.0),      # 负载电流 (TPS54331 额定 3A)
        ("l_uh", 4.7, 10.0, 6.8),      # 电感 (BOM 6.8µH)
        ("cout_uf", 47, 220, 113.0),   # 输出电容 (100+10+3µF)
        ("esr_mohm", 10, 100, 45.0),   # Cout ESR
        ("fsw_khz", 300, 1000, 570.0), # 开关频率 (570kHz 典型)
    ],
    "dior": [
        ("vdc", 4.4, 5.5, 5.0),        # DC-005 座电压
        ("vusb", 4.4, 5.5, 5.1),       # USB-C VBUS (略高模拟最坏)
        ("iload", 0.05, 0.5, 0.5),     # 负载电流
    ],
    "valve": [
        ("pwm_hz", 1, 50, 10.0),       # PWM 频率 (气动阀 10Hz)
        ("duty", 0.05, 0.95, 0.5),     # 占空比
        ("r_coil", 8, 30, board_model.BOARD_PARAMS["r_coil"]),  # [registry] F0520D 4.5V/0.45A=10Ω (原 14Ω 假设废弃, T7 单源同步; M2 经 BOARD_PARAMS 单源)
        ("l_mh", 5, 60, 25.0),         # 阀线圈电感
        ("rg", 47, 330, 100.0),        # 栅极电阻 (AO3400A)
    ],
    "i2c": [
        ("rp_k", 1.0, 10.0, 4.7),      # 上拉电阻 (R8/R9)
        ("cbus_pf", 30, 300, 115.0),   # 总线电容 (TCA+5×传感+走线)
    ],
}


def _check(circuit, params):
    """校验电路名与参数域, 返回 默认值+覆盖 合并后的完整参数 dict."""
    if circuit not in SPEC:
        raise ParamError("未知电路 %r, 可选: %s" % (circuit, "/".join(sorted(SPEC))))
    if params is None:
        params = {}
    if not isinstance(params, dict):
        raise ParamError("params 必须为 dict {参数名: 数值}")
    table = {s[0]: s for s in SPEC[circuit]}
    for k, v in params.items():
        if k not in table:
            raise ParamError("电路 %r 不存在参数 %r, 可调: %s"
                             % (circuit, k, list(table)))
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise ParamError("参数 %s=%r 必须为数值" % (k, v))
        _n, lo, hi, _d = table[k]
        if not (lo <= v <= hi):
            raise ParamError("参数 %s=%s 超出允许范围 [%s, %s]" % (k, v, lo, hi))
    merged = {name: float(dflt) for name, _lo, _hi, dflt in SPEC[circuit]}
    for k, v in params.items():
        merged[k] = float(v)
    return merged


def run(circuit, params=None):
    """运行一个电路仿真 (纯函数). 返回
    {circuit, params, metrics:[{name,value,unit,verdict}],
     waves:[{name,t[],y[],unit}], notes:[str]}"""
    p = _check(circuit, params)
    metrics, waves, notes = _IMPL[circuit](p)
    return {"circuit": circuit, "params": p,
            "metrics": metrics, "waves": waves, "notes": notes}


# ---------------------------------------------------------------- 公共小工具
def _dec(t, y, n=1500):
    """等距降采样到 ≤n 点, 数值 round (JSON 友好). 返回 (list, list).
    t 跨度 ≥1ms 时取 6 位小数 (µs 分辨率, 覆盖 buck/valve/dior);
    µs 级波形 (i2c, 8τ≈数 µs) 加严到 9 位, 避免 x 轴量化成阶梯."""
    m = len(t)
    if m <= n:
        idx = list(range(m))
    else:
        step = (m - 1) / float(n - 1)
        idx, last = [], -1
        for k in range(n):
            j = min(m - 1, int(k * step + 0.5))
            if j != last:
                idx.append(j)
                last = j
    nd = 6 if abs(float(t[-1])) >= 1e-3 else 9
    return ([round(float(t[j]), nd) for j in idx],
            [round(float(y[j]), 6) for j in idx])


def _wave(name, t, y, unit, n=1500):
    tt, yy = _dec(t, y, n)
    return {"name": name, "t": tt, "y": yy, "unit": unit}


def _metric(name, value, unit, verdict):
    return {"name": name, "value": round(float(value), 9), "unit": unit,
            "verdict": verdict}


def _diode_i(v, Is=1e-7, n=1.2, vt=0.02585):
    """SS34 指数模型 (与 simlib.diode_i 标量路径一致, >40V 线性外推防溢出)."""
    x = v / (n * vt)
    if x > 40:
        return Is * exp(40.0) * (1.0 + (x - 40.0))
    return Is * (exp(min(max(x, 0.0), 40.0)) - 1.0)


# ---------------------------------------------------------------- 1) buck
def _buck(p):
    """TPS54331 异步 buck 行为级闭环 (移植 sim_buck.run, ss=0.5ms 单次 2.5ms)."""
    vin, iload = p["vin"], p["iload"]
    L = p["l_uh"] * 1e-6
    COUT = p["cout_uf"] * 1e-6
    ESR = p["esr_mohm"] * 1e-3
    FSW = p["fsw_khz"] * 1e3

    VREF, RDIV = 0.8, 1.0 + 10e3 / 3.24e3
    VOUT_T = VREF * RDIV                       # = 3.269V
    TSW = 1.0 / FSW
    RSW, DCR = 0.12, 0.018                     # 内部高边开关 / 电感绕线
    VF, RD = 0.42, 0.035                       # SS34 续流
    KP, KI = 0.3, 2500.0
    D0 = VOUT_T / vin
    dt = 1.0 / (FSW * 140)                     # = TSW/140 ≈ 12.5ns
    total, ss = 2.5e-3, 0.5e-3                 # 软启动 0.5ms, 仿真 2.5ms

    n = int(total / dt)
    t = iL = vC = integ = 0.0
    T, IL, VO = [0.0], [0.0], [0.0]
    for k in range(n):
        t += dt
        vref_eff = min(1.0, t / ss) * VOUT_T
        vout = vC + ESR * (iL - iload)
        err = vref_eff - vout                  # 直接以 Vout 尺度调环 (同原版)
        integ = min(1e-3, max(-1e-3, integ + err * dt))
        d = min(0.92, max(0.05, D0 + KP * err + KI * integ))
        on = ((k * dt) % TSW) < d * TSW
        vsw = vin - iL * RSW if on else (-VF - iL * RD)
        iL += (vsw - vout - iL * DCR) / L * dt
        if iL < 0 and not on:                  # 断续模式钳位
            iL = 0.0
        vC += (iL - iload) / COUT * dt
        T.append(t); IL.append(iL); VO.append(vC)

    # 稳态段: T>2.2ms
    w = [j for j, tv in enumerate(T) if tv > 2.2e-3]
    vo_w = [VO[j] for j in w]
    il_w = [IL[j] for j in w]
    v_avg = sum(vo_w) / len(vo_w)
    ripple_mV = (max(vo_w) - min(vo_w)) * 1000.0
    ilpp = max(il_w) - min(il_w)
    ilpk = max(il_w)

    # 效率 (CCM): 导通 + 绕线 + 二极管 + 开关(20ns/沿) + ESR
    D = VOUT_T / vin
    P_rsw = iload ** 2 * RSW * D
    P_dcr = iload ** 2 * DCR
    P_d = VF * iload * (1.0 - D)
    P_sw = 0.5 * vin * iload * 20e-9 * FSW
    P_esr = (ilpp ** 2 / 12.0) * ESR
    eff = VOUT_T * iload / (VOUT_T * iload + P_rsw + P_dcr + P_d + P_sw + P_esr)

    metrics = [
        _metric("输出电压", v_avg, "V",
                "✓ 3.3V±1% 设计目标" if abs(v_avg - 3.3) <= 0.033
                else "⚠ 偏离 3.3V±1% 设计窗口"),
        _metric("稳态纹波", ripple_mV, "mVpp",
                "✓ <50mV 预算" if ripple_mV < 50 else "⚠ 超 50mV 预算 (ESR 主导)"),
        _metric("电感电流纹波", ilpp, "App",
                "✓ 峰值 %.2fA < 3.9A (3A+30%% 裕量)" % ilpk if ilpk < 3.9
                else "⚠ 峰值 %.2fA 超 3.9A 裕量" % ilpk),
        _metric("满载效率", eff, "",
                "✓ >80%" if eff > 0.8 else "⚠ ≤80%, 见损耗分解"),
    ]
    waves = [_wave("Vout", T, VO, "V"), _wave("iL", T, IL, "A")]
    notes = [
        "VOUT_T=0.8×(1+10k/3.24k)=%.3fV; 闭环 KP=0.3 KI=2500, 软启动 %.1fms, dt=TSW/140=%.1fns"
        % (VOUT_T, ss * 1e3, dt * 1e9),
        "损耗分解: 开关管 %.0fmW + DCR %.0fmW + 二极管 %.0fmW + 开关(20ns) %.0fmW + ESR %.1fmW"
        % (P_rsw * 1e3, P_dcr * 1e3, P_d * 1e3, P_sw * 1e3, P_esr * 1e3),
        "稳态窗口 T>2.2ms (%d 点), 含软启动波形" % len(w),
    ]
    return metrics, waves, notes


# ---------------------------------------------------------------- 2) dior
def _dior(p):
    """SS34×2 二极管-或 (DC 座 vs USB-C VBUS) 不动点工作点 + vdc 扫描."""
    vdc, vusb, iload = p["vdc"], p["vusb"], p["iload"]
    RL = 5.0 / iload                           # 0.5A → 10Ω, 同原版

    vo = 4.5
    for _ in range(200):
        i1 = _diode_i(vdc - vo)
        i2 = _diode_i(vusb - vo)
        vo += 0.05 * ((i1 + i2) - vo / RL)
    i1, i2 = _diode_i(vdc - vo), _diode_i(vusb - vo)

    # DC 扫描 4.4→5.5V (60 点), 观察双源分流
    # 注: 原版 vo2 初值 4.4 使迭代发散 (首步指数电流≈数百 A 跳出), sweep 恒 0;
    #     此处加 vo2≤max(源) 物理钳位使其收敛, 不动点结构与收敛根不变.
    vds = [4.4 + (5.5 - 4.4) * k / 59.0 for k in range(60)]
    dc_mA, usb_mA = [], []
    for v in vds:
        vo2 = 4.4
        vcap = max(v, vusb)                    # 轨电压不可能高于最高源
        for _ in range(150):
            a = _diode_i(v - vo2)
            b = _diode_i(vusb - vo2)
            vo2 = min(vo2 + 0.05 * ((a + b) - vo2 / RL), vcap)
        dc_mA.append(_diode_i(v - vo2) * 1000.0)
        usb_mA.append(_diode_i(vusb - vo2) * 1000.0)
    j = min(range(60), key=lambda k: abs(vds[k] - 5.0))   # 最接近 5.0V 的点
    reverse_mA = usb_mA[j]

    metrics = [
        _metric("轨电压", vo, "V",
                "✓ 5V-单二极管压降(~0.3V)" if 4.3 < vo < 5.0 else "⚠ 轨电压异常"),
        _metric("DC侧电流", i1, "A", "✓ SS34 正向导通"),
        _metric("USB侧电流", i2, "A",
                "✓ 双源分流" if i2 < iload else "⚠ USB 超供"),
        _metric("USB分流@DC5V", reverse_mA / 1000.0, "A",
                "✓ 两管分流, 无反偏倒灌路径" if reverse_mA < 500 else "⚠ 分流异常"),
    ]
    waves = [_wave("DC侧电流", vds, dc_mA, "mA"),
             _wave("USB侧电流", vds, usb_mA, "mA")]
    notes = [
        "SS34 指数模型 Is=1e-7 n=1.2; 工作点: vdc=%.1fV vusb=%.1fV 负载 %.2fA (RL=%.1fΩ)"
        % (vdc, vusb, iload, RL),
        "扫描 x 轴为 V_DC (4.4→5.5V, 60 点); USB 倒灌取 V_DC≈5.0V 处",
    ]
    return metrics, waves, notes


# ---------------------------------------------------------------- 3) valve
def _valve(p):
    """AO3400A 低边驱动气动阀: 解析栅极 exp + RL 一阶欧拉, 3 周期取末周期."""
    f_pwm, duty = p["pwm_hz"], p["duty"]
    R_COIL = p["r_coil"]
    L = p["l_mh"] * 1e-3
    RG = p["rg"]
    RDS, CISS, VF_FW = 0.040, 1.0e-9, 0.35     # AO3400A @VGS=3.3V / SS14 续流

    T_per = 1.0 / f_pwm
    dt = 2e-5
    n = int(3.0 * T_per / dt)
    tau_g = RG * CISS
    i = vg = 0.0
    T, I, VG = [0.0], [0.0], [0.0]
    for k in range(n):
        t = k * dt
        pwm = ((t * f_pwm) % 1.0) < duty
        if pwm:
            vg = 3.3 + (vg - 3.3) * exp(-dt / tau_g)
        else:
            vg = vg * exp(-dt / tau_g)
        on = vg > 1.2
        vcoil = (5.0 - i * RDS) if on else -VF_FW
        i_new = i + (vcoil - i * R_COIL) / L * dt
        i = i_new if i_new > 0 else 0.0         # 续流钳位, 无高压尖峰
        T.append(t); I.append(i); VG.append(vg)

    w = [j for j, tv in enumerate(T) if tv > 2.0 * T_per]      # 末周期
    peak = max(I[j] for j in w)
    tau = L / R_COIL
    P_coil = 0.5 * peak ** 2 * R_COIL * duty
    P_mos = 0.5 * peak ** 2 * RDS * duty
    P_fw = VF_FW * peak * duty * (2.0 * tau / T_per)

    metrics = [
        _metric("稳态阀电流", peak, "A",
                "✓ 拉入≈0.5A@5V (registry 额定 0.45A@4.5V, 保持90%=额定)" if peak <= 0.52 else "⚠ >0.52A, 检查线圈/占空比"),
        _metric("电流时间常数", tau * 1e3, "ms",
                "✓ <10ms, 不拖阀机械响应后腿" if tau < 10e-3 else "⚠ ≥10ms"),
        _metric("MOS导通损耗", P_mos * 1e3, "mW", "✓ SOT-23 无需散热"),
        _metric("续流二极管损耗", P_fw * 1e3, "mW",
                "✓ SS14 0.5A 额定" if P_fw < 0.2 else "⚠ 续流损耗偏大"),
    ]
    w2 = [j for j, tv in enumerate(T) if tv > T_per]           # 末 2 周期波形
    waves = [_wave("阀电流", [T[j] for j in w2], [I[j] for j in w2], "A"),
             _wave("Vgs", [T[j] for j in w2], [VG[j] for j in w2], "V")]
    notes = [
        "PWM %.0fHz/%.0f%%; τ=L/R=%.1fms; 关断由 SS14 钳位至 -0.35V, 无高压尖峰"
        % (f_pwm, duty * 100, tau * 1e3),
        "稳态线圈功耗 %.0fmW; 8 路全开总线电流约 %.1fA (5V/3A 输入下禁全开)"
        % (P_coil * 1e3, peak * 8),
    ]
    return metrics, waves, notes


# ---------------------------------------------------------------- 4) i2c
def _i2c(p):
    """I2C 总线一阶 RC 上升沿: tr=2.2τ, 波形取释放后 8τ."""
    RP = p["rp_k"] * 1e3
    CBUS = p["cbus_pf"] * 1e-12
    tau = RP * CBUS
    tr = 2.2 * tau

    npts = 400
    t_end = 8.0 * tau
    T = [t_end * k / (npts - 1.0) for k in range(npts)]
    V = [3.3 * (1.0 - exp(-tv / tau)) for tv in T]

    metrics = [
        _metric("上升时间", tr, "s",
                "✓ ≤0.6µs, 400kHz 快速模式可用" if tr < 0.6e-6
                else "⚠ 超 0.6µs → 降 100kHz 或上拉减弱(改 2.2k)"),
        _metric("RC时间常数", tau, "s",
                "✓ 100kHz 预算 1µs 内" if tr < 1e-6 else "⚠ 超 100kHz 预算"),
    ]
    waves = [_wave("SDA/SCL", T, V, "V", n=npts)]
    notes = [
        "τ=Rp×Cbus=%.2fµs; tr=2.2τ=%.2fµs; 波形为释放后 8τ (%.1fµs)"
        % (tau * 1e6, tr * 1e6, t_end * 1e6),
        "高电平噪声裕量: 3.3V 摆幅, VIH=0.7×3.3=2.31V",
    ]
    return metrics, waves, notes


_IMPL = {"buck": _buck, "dior": _dior, "valve": _valve, "i2c": _i2c}


if __name__ == "__main__":
    import sys
    argv = sys.argv[1:]
    if argv[:1] == ["--export"]:              # 离线导出: 5 SVG + sim-report.md
        import sim_export
        for f in sim_export.export_all(argv[1] if len(argv) > 1 else None):
            print("写出", f)
    elif argv:                                # 未知参数: 提示用法
        print("用法: python sim_engine.py [--export [输出目录]]")
        raise SystemExit(2)
    else:                                     # 无参: 冒烟打印各电路首指标
        for c in ("buck", "dior", "valve", "i2c"):
            r = run(c, {})
            m = r["metrics"][0]
            print("%-5s %-8s = %s %s  %s" % (c, m["name"], m["value"], m["unit"], m["verdict"]))
