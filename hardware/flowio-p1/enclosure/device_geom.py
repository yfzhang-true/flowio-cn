# -*- coding: utf-8 -*-
"""[弃用 shim · M1 2026-10] 本模块已迁至 flowio/geom/device_geom.py, 原位留转发。

sys.modules 顶替法转发 (旧名与新名为同一模块对象, _POS/_BY_KEYWORD 等私有名
与身份均一致); 新代码一律 `from flowio.geom import device_geom`。
保留一个版本周期, M5 收单后删除。
"""
import sys
from pathlib import Path

_ROOT = str(Path(__file__).resolve().parents[3])   # enclosure -> flowio-p1 -> hardware -> 仓库根
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from flowio.geom import device_geom as _real  # noqa: E402

sys.modules[__name__] = _real
