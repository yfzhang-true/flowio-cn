# -*- coding: utf-8 -*-
"""[弃用 shim · M1 2026-10] 本脚本已迁至 flowio/hw/pcb_gen.py, 原位留转发。

⛔⛔⛔ 重跑本脚本 (经 shim 或新路径) = 重写裸板骨架 —— flowio-p1.kicad_pcb
内含 T4 全部布线成果 (338 缺陷清零) + fab 产物已下单就绪。除"明确决定重建
整板"外绝对禁止执行 (spec 2026-10-05 M1 禁令)。

保留一个版本周期 (旧命令不改可继续跑, runpy 直转, sys.argv 透传);
新调用一律改为: "E:/Program Files/KiCad/10.0/bin/python.exe" flowio/hw/pcb_gen.py
M5 收单后删除本文件。
"""
import runpy
import sys
from pathlib import Path

_ROOT = str(Path(__file__).resolve().parents[3])   # tools -> flowio-p1 -> hardware -> 仓库根
_TARGET = str(Path(_ROOT) / "flowio" / "hw" / "pcb_gen.py")

if __name__ == "__main__":
    if _ROOT not in sys.path:
        sys.path.insert(0, _ROOT)
    runpy.run_path(_TARGET, run_name="__main__")
else:
    raise ImportError(
        "gen_pcb 已迁至 flowio.hw.pcb_gen (M1); 本 shim 仅转发脚本执行, "
        "模块导入请改用 flowio.hw.pcb_gen (并遵守重跑禁令)")
