# -*- coding: utf-8 -*-
"""[弃用 shim · M1 2026-10] 本模块已迁至 flowio/flows/device_graph.py, 原位留转发。

sys.modules 顶替法转发 (旧名与新名为同一模块对象); 旧 __main__ 统计入口经
runpy 转发。新代码一律 `from flowio.flows import device_graph`。
保留一个版本周期, M5 收单后删除。
"""
import sys
from pathlib import Path

_ROOT = str(Path(__file__).resolve().parents[3])   # enclosure -> flowio-p1 -> hardware -> 仓库根
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from flowio.flows import device_graph as _real  # noqa: E402

sys.modules[__name__] = _real

if __name__ == "__main__":   # 旧用法: venv-cad enclosure/device_graph.py
    import runpy
    runpy.run_path(str(Path(_real.__file__)), run_name="__main__")
