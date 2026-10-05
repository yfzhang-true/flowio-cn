# -*- coding: utf-8 -*-
"""flowio.geom — 结构域 (spec v2.1 §2: case_geom/device_geom/make_*/pneu_geom)。

M1 自 hardware/flowio-p1/enclosure/ 迁入:
  case_geom.py    装配几何单一真相源 (纯 Python, 无 FreeCAD 依赖 —— 逐字节原样迁移)
  device_geom.py  器件几何核: OBB / 端口射线 / FCL 碰撞管理 (venv-cad)
  pneu_geom.py    气动结构件共享构建器 (FreeCAD; 域归属说明见模块头)
  make_case.py / make_manifold.py / make_pump_module.py  FreeCAD 结构件生成器
  make_meshes.py / make_assembly.py                      孪生网格 / 合并装配体
  diag_l4.py      L4 干涉诊断 (T6 临时工具随迁)

产物落位不变: 生成器经包定位解析输出到 hardware/flowio-p1/enclosure/ 与
firmware/twin/meshes/ (M1 重放对拍 11 产物 sha 全等, 详见 docs/mod-baseline/)。
本 __init__ 刻意零导入: make_*/pneu_geom import 即需 FreeCAD, 包级导入保持惰性。
"""
