# -*- coding: utf-8 -*-
"""flowio.flows — 气路/流拓扑域 (spec v2.1 §2: flows + hotspots).

M1 自 hardware/flowio-p1/enclosure/ 迁入:
  make_flows.py   pos.csv -> firmware/twin/webapp/{flows.json,hotspots.json} (纯 stdlib)
  device_graph.py 器件关系图: 电气边(网表 flowio.hw.netlist) + 空间边(端口->槽)
                  + 21↔21 完美匹配 + flows 交叉校验 (venv-cad, networkx)

气路拓扑单一真值即本包 (spec §2 "flows/hotspots" 落点); 气动**结构件几何**
(阀体/流道管 FreeCAD 实体) 归 flowio.geom.pneu_geom, 见其模块头域归属说明。
"""
