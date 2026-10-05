# -*- coding: utf-8 -*-
"""[弃用 shim · M1 2026-10] 本脚本已迁至 flowio/hw/route/route_pcb.py, 原位留转发。

⛔⛔⛔ 本脚本直接改写 flowio-p1.kicad_pcb (板内含 T4 全部布线成果, fab 产物
已下单就绪)。除"明确决定重建整板"外绝对禁止执行 (spec 2026-10-05 M1 禁令)。

保留一个版本周期 (旧命令不改可继续跑, runpy 直转, sys.argv 含 stage 透传);
新调用一律改为:
    kiCad-python flowio/hw/route/route_pcb.py [stage]
M5 收单后删除本文件。
"""
import os
import runpy
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_TARGET = os.path.join(_ROOT, "flowio", "hw", "route", "route_pcb.py")

if __name__ == "__main__":
    if _ROOT not in sys.path:
        sys.path.insert(0, _ROOT)
    runpy.run_path(_TARGET, run_name="__main__")
else:
    raise ImportError(
        "route_pcb 已迁至 flowio.hw.route.route_pcb (M1); 本 shim 仅转发脚本执行, "
        "模块导入请改用新路径 (并遵守重跑禁令)")
