# -*- coding: utf-8 -*-
"""electrical_sim — T7 电气驱动仿真层 → M2 薄壳 (shim, spec v2.1 §3.2/§3.4)。

迁移史:
  * T7: 初版 (参数手抄 → devices.json 直读);
  * M0: 参数单源改经 flowio 内核 (TruthSource + flowio.truth 视图);
  * M2 (本形态): 物理内核迁至 flowio 包 ——
      flowio/twin/actuators.py   IActuator 子类族 (ValveF0520D/F0520B/PumpZR370
                                 + build_actuators 工厂; 继承/封装/多态 §3.2-§3.4)
      flowio/twin/electrical.py  ElectricalModel(BaseModel): load_params/simulate
                                 核心 + 固件策略常量 (ADAPTER_A/告警码/工作带)
      flowio/twin/scenarios.py   场景矩阵 (SCENARIOS/run_scenario/run_matrix;
                                 验收语料与物理内核分层)
    本模块仅 re-export —— 对外 API/返回结构与数值位级不变:
      test_electrical_sim.py 零改动全绿 + tools/compare_baseline.py 12 场景
      逐值相等 = 验收门。

模型摘要 (详见 flowio.twin 各模块 docstring):
  * 三态阀驱动 (drive_policy): 吸入 pull_in 100%≤100ms / 全开保持 90%
    (等效4.5V=额定) / 节能保持 55% (有意欠压 2.75V, 35kPa 背压下限 BRINGUP 实测);
  * V_eff = duty × rail_v; I = V_eff / R_coil (r_coil 推导唯一出处 =
    flowio.truth.views.ValveSpec.r_coil: F0520D 10Ω / F0520B 15Ω);
  * 泵: 占空比钳 ≤95% + 软启动互锁 (≥1 通道阀开启才起泵) + 过压停泵 (M>+35kPa)
    / 真空钳位 (M<-40kPa);
  * 母线总电流 = Σ阀 + 泵 (多态求和 §3.4①); 超限 (>ADAPTER_A) → 受限模式告警。

运行: cd firmware/twin && python electrical_sim.py   (打印场景矩阵表)
测试: python test_electrical_sim.py  (TDD 红→绿, 5 断言+冒烟, 零改动)
对拍: python tools/compare_baseline.py  (12 场景 vs docs/mod-baseline/baseline.json)
"""
import sys
from pathlib import Path

# ---- flowio 内核包 (M0 起加载经 TruthSource; 未 pip -e 亦可跑) ----------------
_PKG_ROOT = Path(__file__).resolve().parents[2]          # 仓库根 (flowio 包所在)
if str(_PKG_ROOT) not in sys.path:
    sys.path.insert(0, str(_PKG_ROOT))

from flowio.twin.electrical import (ADAPTER_A, ALARM_NAMES, ALARM_OVERLOAD,   # noqa: E402,F401
                                    ALARM_OVERPRESSURE, ALARM_VACUUM_CLAMP,
                                    VALVE_STATES, VAC_CLAMP_KPA, WORKING_BAND_KPA,
                                    ElectricalModel, REGISTRY, load_params,
                                    simulate)
from flowio.twin.scenarios import (SCENARIOS, run_matrix, run_scenario)       # noqa: E402,F401


if __name__ == "__main__":
    p = load_params()
    print(f"参数单源: {REGISTRY}")
    print(f"  rail={p['rail_v']}V  duties(吸入/全开/节能)="
          f"{p['duties']['pull_in']:.0%}/{p['duties']['full_open']:.0%}/"
          f"{p['duties']['economy']:.0%}  泵≤{p['pump_max_duty']:.0%}"
          f"  R_coil(D)={p['valves']['V1']['r_coil']:.1f}Ω "
          f"R_coil(B)={p['valves']['VV']['r_coil']:.1f}Ω")
    print(f"  适配器档 {ADAPTER_A}A | 工作带 ±{WORKING_BAND_KPA:.0f}kPa | "
          f"真空钳位 {VAC_CLAMP_KPA:.0f}kPa\n")
    print(f"{'场景':<28}{'母线 A':>8}  {'超限':<4}{'告警':<14}说明")
    for row in run_matrix():
        flag = "⚠受限" if row["over_limit"] else "ok"
        al = ",".join(row["alarm_names"]) or "-"
        print(f"{row['name']:<28}{row['i_total_a']:>8.3f}  {flag:<5}{al:<14}{row['desc']}")
        for a in row["advice"]:
            print(f"{'':>40}└ {a}")
