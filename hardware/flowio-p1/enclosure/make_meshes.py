# -*- coding: utf-8 -*-
"""[弃用 shim · M1 2026-10] 本脚本已迁至 flowio/geom/make_meshes.py, 原位留转发。

保留一个版本周期 (runpy 直转, sys.argv 透传); 新调用:
    E:/FreeCAD/bin/python.exe flowio/geom/make_meshes.py
M5 收单后删除本文件。
"""
import runpy
import sys
from pathlib import Path

_ROOT = str(Path(__file__).resolve().parents[3])   # enclosure -> flowio-p1 -> hardware -> 仓库根
_TARGET = str(Path(_ROOT) / "flowio" / "geom" / "make_meshes.py")

if __name__ == "__main__":
    if _ROOT not in sys.path:
        sys.path.insert(0, _ROOT)
    runpy.run_path(_TARGET, run_name="__main__")
else:
    raise ImportError("make_meshes 已迁至 flowio.geom.make_meshes (M1); "
                      "本 shim 仅转发脚本执行 (FreeCAD python 运行形态)")
