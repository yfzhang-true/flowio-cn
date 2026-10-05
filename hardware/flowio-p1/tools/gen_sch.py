# -*- coding: utf-8 -*-
"""[弃用 shim · M1 2026-10] 本脚本已迁至 flowio/hw/sch_gen.py, 原位留转发。

保留一个版本周期: 旧 SOP/rebuild-matrix/文档命令不改可继续跑 (runpy 直转,
sys.argv 透传); 新调用一律改为:
    "E:/Program Files/KiCad/10.0/bin/python.exe" flowio/hw/sch_gen.py
注意: make_bom.py 等以 ast 读 gen_sch.py **源码**提取 PARTS 的消费者已改读
flowio/hw/sch_gen.py (本 shim 源码不含 PARTS, 不可作读源)。
M5 收单后删除本文件 (spec 2026-10-05 §2 渐进迁移纪律)。
"""
import os
import runpy
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_TARGET = os.path.join(_ROOT, "flowio", "hw", "sch_gen.py")

if __name__ == "__main__":
    if _ROOT not in sys.path:
        sys.path.insert(0, _ROOT)
    runpy.run_path(_TARGET, run_name="__main__")
else:
    raise ImportError(
        "gen_sch 已迁至 flowio.hw.sch_gen (M1); 本 shim 仅转发脚本执行, "
        "模块导入请改用 flowio.hw.sch_gen")
