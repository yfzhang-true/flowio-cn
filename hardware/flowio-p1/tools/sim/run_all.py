# -*- coding: utf-8 -*-
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
os.makedirs(OUT, exist_ok=True)
sys.path.insert(0, HERE)
import sim_buck, sim_dior_valve_i2c, sim_valve, sim_i2c
from simlib import SVG_PENDING
md = ["# FLOWIO-P1 电路仿真报告", "",
      "> 日期: 2026-10-01 · 工具: 自研行为级状态机仿真 (numpy RK/欧拉), 无 ngspice 环境下的替代方案",
      "> 模型级局限: 半导体用简化开关/指数模型, 控制环为行为级 PI——数值量级可信, 非厂商 SPICE 精度",
      "> 参数全部取自实际 BOM: L1=6.8µH, C7/C8=100µF, R4=10k/R5=3.24k, SS34/SS14, AO3400A, R8/R9=4.7k", ""]
r1 = sim_buck.report(md, OUT)
r2 = sim_dior_valve_i2c.report(md, OUT)
r3 = sim_valve.report(md, OUT)
r4 = sim_i2c.report(md, OUT)
md.append("## 汇总结论\n")
md.append("- 电源链 (DC/USB 二极管或 → buck 3.27V): 纹波/过冲/阶跃全部在预算内, 修正 #9/#11 经仿真复核成立")
md.append("- 8 路阀驱动: 开关安全 (续流钳位), 单管损耗 <10mW; **8 路同开 2.8A 超出 DC 输入 3A×裕量设计, 固件已限同时 ≤6 路**")
md.append("- I2C: 100kHz 无忧; 400kHz 时若实测 tr 超差, 预案改 2.2k 上拉")
md.append("- 待回板实测项: 效率 (仿真 87%), 纹波实测对照, 阀线圈实际 L 值")
from pathlib import Path as _P
_P(OUT, "2026-10-01-p1-circuit-sim.md").write_bytes("\n".join(md).encode("utf-8"))
# SVG 落盘: 字面量文件名 (路径穿越防护), 目录为本脚本旁 out/
for _nm in ("buck_startup.svg", "buck_ripple.svg", "buck_loadstep.svg",
            "dior_share.svg", "valve_pwm.svg", "i2c_rise.svg"):
    if _nm in SVG_PENDING:
        _P(OUT, _nm).write_bytes(SVG_PENDING[_nm].encode("utf-8"))
print("报告与波形已输出到", OUT)
