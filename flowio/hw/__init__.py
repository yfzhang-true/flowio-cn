# -*- coding: utf-8 -*-
"""flowio.hw — 硬件域 (spec v2.1 §2: sch_gen/pcb_gen/route/netlist/drill)。

M1 自 hardware/flowio-p1/{tools,fab}/ 迁入:
  sch_gen.py   原理图生成器 (PARTS 单一真值源, tools/gen_sch.py)
  pcb_gen.py   PCB 骨架生成器 (tools/gen_pcb.py; ⛔ 禁令: 重跑=裸板毁布线)
  netlist.py   网表解析器 (fab/netlist.py)
  drill.py     Excellon 钻孔解析器 (fab/drl.py)
  route/       布线器 (tools/route_pcb.py 整迁; ⛔ 同禁令)

本 __init__ 刻意零导入: 生成器模块 import 即执行 (脚本形态, pcbnew/FreeCAD
运行约束), 包级导入必须保持惰性 —— 需要时显式 `from flowio.hw import netlist`。

⛔ 板产物禁令 (M1 起): flowio-p1.kicad_pcb 内含 T4 全部布线成果且 fab 产物
已下单就绪, pcb_gen/route 与旧 fix*.py 一律禁止重跑 (详见各模块头注释)。
"""
