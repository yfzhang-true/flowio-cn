# -*- coding: utf-8 -*-
"""[弃用 shim · M1 2026-10] 本脚本已迁至 flowio/geom/make_pump_module.py, 原位留转发。

保留一个版本周期 (runpy 直转, sys.argv 透传, 产物仍落位本目录); 新调用:
    E:/FreeCAD/bin/FreeCADCmd.exe flowio/geom/make_pump_module.py
M5 收单后删除本文件。
"""
import runpy
import sys
from pathlib import Path

_ROOT = str(Path(__file__).resolve().parents[3])   # enclosure -> flowio-p1 -> hardware -> 仓库根
_TARGET = str(Path(_ROOT) / "flowio" / "geom" / "make_pump_module.py")

if __name__ == "__main__":
    if _ROOT not in sys.path:
        sys.path.insert(0, _ROOT)
    runpy.run_path(_TARGET, run_name="__main__")
else:
    raise ImportError("make_pump_module 已迁至 flowio.geom.make_pump_module (M1); "
                      "本 shim 仅转发脚本执行 (FreeCADCmd 运行形态)")
