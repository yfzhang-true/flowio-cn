# -*- coding: utf-8 -*-
"""[弃用 shim · M1 2026-10] 本脚本已迁至 flowio/flows/make_flows.py, 原位留转发。

双形态转发: 直接执行 (python make_flows.py) 经 runpy 转发 (sys.argv 透传);
被 import (旧测试取 load_pos/_outward_dir) 经 sys.modules 顶替为同一模块对象。
新代码一律 `from flowio.flows import make_flows`。保留一个版本周期, M5 收单后删。
"""
import sys
from pathlib import Path

_ROOT = str(Path(__file__).resolve().parents[3])   # enclosure -> flowio-p1 -> hardware -> 仓库根
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from flowio.flows import make_flows as _real  # noqa: E402

sys.modules[__name__] = _real

if __name__ == "__main__":   # 旧用法: python make_flows.py
    import runpy
    runpy.run_path(str(Path(_real.__file__)), run_name="__main__")
