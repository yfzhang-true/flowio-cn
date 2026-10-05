# -*- coding: utf-8 -*-
"""flowio.hw.route — 布线器域 (M1 整迁自 tools/route_pcb.py)。

route_pcb.py 保持脚本形态 (KiCad python + pcbnew SWIG 铁律: 运行目录与解释器
约束见模块头), 本 __init__ 刻意不 re-export —— import route_pcb 即触发
LoadBoard+布线副作用, 包级导入必须保持惰性。

别名导出 (import 路径稳定性): `flowio.hw.route.route_pcb` 即唯一正名;
旧 tools/route_pcb.py 为 runpy 转发 shim (一个版本周期后删)。
"""
