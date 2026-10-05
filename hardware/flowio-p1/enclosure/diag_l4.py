# -*- coding: utf-8 -*-
"""[弃用 shim · M1 2026-10] 本脚本已迁至 flowio/geom/diag_l4.py, 原位留转发。

(T6 临时诊断工具随 geom 域整体迁入。) 保留一个版本周期 (runpy 直转); 新调用:
    E:/FreeCAD/bin/python.exe flowio/geom/diag_l4.py
M5 收单后删除本文件。
"""
import runpy
import sys
from pathlib import Path

_ROOT = str(Path(__file__).resolve().parents[3])   # enclosure -> flowio-p1 -> hardware -> 仓库根
_TARGET = str(Path(_ROOT) / "flowio" / "geom" / "diag_l4.py")

if __name__ == "__main__":
    if _ROOT not in sys.path:
        sys.path.insert(0, _ROOT)
    runpy.run_path(_TARGET, run_name="__main__")
else:
    raise ImportError("diag_l4 已迁至 flowio.geom.diag_l4 (M1); "
                      "本 shim 仅转发脚本执行 (FreeCAD python 运行形态)")
