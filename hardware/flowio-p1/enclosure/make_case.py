# -*- coding: utf-8 -*-
"""[弃用 shim · M1 2026-10] 本脚本已迁至 flowio/geom/make_case.py, 原位留转发。

保留一个版本周期: 旧命令 (SOP/rebuild-matrix) 不改可继续跑 —— runpy 直转,
sys.argv 透传, 产物仍落位本目录; 新调用一律改为:
    E:/FreeCAD/bin/FreeCADCmd.exe flowio/geom/make_case.py
M5 收单后删除本文件 (spec 2026-10-05 §2 渐进迁移纪律)。
"""
import runpy
import sys
from pathlib import Path

_ROOT = str(Path(__file__).resolve().parents[3])   # enclosure -> flowio-p1 -> hardware -> 仓库根
_TARGET = str(Path(_ROOT) / "flowio" / "geom" / "make_case.py")

if __name__ == "__main__":
    if _ROOT not in sys.path:
        sys.path.insert(0, _ROOT)
    runpy.run_path(_TARGET, run_name="__main__")
else:
    raise ImportError("make_case 已迁至 flowio.geom.make_case (M1); "
                      "本 shim 仅转发脚本执行 (FreeCADCmd 运行形态)")
