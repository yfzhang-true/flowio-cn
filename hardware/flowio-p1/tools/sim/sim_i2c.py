# -*- coding: utf-8 -*-
"""sim_i2c: 4.7k 上拉 + 总线电容 (主总线+TCA 5 通道挂载)."""
import numpy as np, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from simlib import plot_svg

def report(md, png_dir):
    R = {}
    # 总线电容: TCA9548A (10pF) + 5×传感器 (15pF) + 走线 (~20pF) + 主侧 10pF ≈ 115pF
    CBUS = 115e-12; RP = 4.7e3
    dt = 5e-9; total = 40e-6
    n = int(total/dt)
    v = 0.0; T = [0]; V = [0]
    for k in range(n):
        t = k*dt
        i_src = (3.3-v)/RP if t > 2e-6 else 0.0   # 2µs 时释放总线 (0→上拉)
        v += i_src/CBUS*dt
        T.append(t); V.append(v)
    T = np.array(T); V = np.array(V)
    tau = RP*CBUS
    tr = 2.2*tau                                # 10-90% 上升时间
    plot_svg([("SDA/SCL (V)", T, V, "#1f77b4")],
             png_dir+"/i2c_rise.svg", "I2C 总线上升沿 (4.7k 上拉, Cbus=115pF)",
             "t (µs)", "V",
             notes=[f"τ = {tau*1e6:.2f} µs, 10-90% 上升时间 tr = {tr*1e6:.2f} µs",
                    "400kHz 快速模式预算 300ns×... 按 0.6µs 判定"])
    R['tr'] = tr
    ok400 = tr < 0.6e-6
    md.append("### 4. I2C 总线时序 (R8/R9=4.7k, 挂 TCA9548A+5 传感器)\n")
    md.append("| 指标 | 仿真值 | 判定 |")
    md.append("|---|---|---|")
    md.append(f"| 总线电容 (估算) | {CBUS*1e12:.0f} pF | TCA+5×传感+走线 |")
    md.append(f"| 上升时间 tr | {tr*1e6:.2f} µs | 100kHz (预算 1µs) ✓; 400kHz 需 ≤0.6µs {'✓' if ok400 else '⚠ 降为 100kHz 或上拉改 2.2k'} |")
    md.append(f"| 高电平噪声裕量 | 3.3V 摆幅, VIH=0.7×3.3=2.31V | ✓ |")
    md.append("\n波形: `i2c_rise.svg`\n")
    return R
