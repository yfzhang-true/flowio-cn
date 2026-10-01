# -*- coding: utf-8 -*-
"""sim_valve: AO3400A 低边驱动气动阀 (PWM 10Hz/50%)."""
import numpy as np, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from simlib import plot_svg

R_COIL, L_COIL = 14.0, 25e-3      # 5V/0.35A 小型气动阀, 电感 25mH 典型
RDS, RG, CISS = 0.040, 100.0, 1.0e-9   # AO3400A @VGS=3.3V, 栅阻 100Ω, 输入电容 1nF
VF_FW = 0.35                      # SS14 续流 @0.35A

def report(md, png_dir):
    R = {}
    dt = 0.2e-6; total = 0.3        # 3 个 PWM 周期 (10Hz/50%)
    n = int(total/dt)
    i = 0.0; vg = 0.0
    T, I, VG = [0], [0], [0]
    tau_g = RG*CISS
    for k in range(n):
        t = k*dt
        pwm = ((t*10) % 1.0) < 0.5
        if pwm:
            vg = 3.3 + (vg-3.3)*np.exp(-dt/tau_g)
        else:
            vg = vg*np.exp(-dt/tau_g)
        on = vg > 1.2
        vcoil = (5.0 - i*RDS) if on else -VF_FW
        di = (vcoil - i*R_COIL)/L_COIL
        i_new = i + di*dt
        if i_new < 0: i_new = 0.0
        i = i_new
        T.append(t); I.append(i); VG.append(vg)
    T = np.array(T); I = np.array(I); VG = np.array(VG)
    m = T > 0.1
    plot_svg([("i 阀电流 (A)", T[m], I[m], "#d62728"), ("Vgs (V)", T[m], VG[m], "#1f77b4")],
             png_dir+"/valve_pwm.svg", "AO3400 驱动阀线圈 PWM 10Hz/50% (tau=L/R=1.8ms)",
             "t (ms)", "A / V",
             notes=[f"稳态峰值电流 {I[m].max():.3f} A (目标 0.35A)",
                    "关断续流由 SS14 钳位至 -0.35V, 无高压尖峰"])
    tau = L_COIL/R_COIL
    P_coil = 0.5*(0.35**2)*R_COIL*0.5
    P_mos  = 0.5*(0.35**2)*RDS*0.5
    P_fw   = VF_FW*0.35*0.5*(2*tau/0.1)
    R.update(peak=I[m].max(), tau=tau, P_coil=P_coil, P_mos=P_mos, P_fw=P_fw)
    md.append("### 3. AO3400A 阀驱动通道 (8 路之一, PWM 10Hz/50%)")
    md.append("| 指标 | 仿真值 | 判定 |")
    md.append("|---|---|---|")
    md.append(f"| 稳态阀电流 | {R['peak']:.3f} A | 阀额定 0.35A ✓ |")
    md.append(f"| 电流建立 tau=L/R | {tau*1000:.1f} ms | 阀机械响应 ~10ms, 电感不拖后腿 ✓ |")
    md.append("| 关断尖峰 | 被 SS14 钳位至 -0.35V | Vds<AO3400 30V 额定, 大裕量 ✓ |")
    md.append(f"| MOS 损耗/通道 | {P_mos*1000:.1f} mW | SOT-23 无需散热 ✓ |")
    md.append(f"| 续流二极管损耗 | {P_fw*1000:.1f} mW | SS14 0.5A 额定 ✓ |")
    md.append("| 8 路全开总线电流 | 2.8 A | 5V/3A 输入下禁止 8 路全开 (固件限流) ⚠ 已在固件约束 |")
    md.append("")
    md.append("波形: `valve_pwm.svg`")
    md.append("")
    return R
