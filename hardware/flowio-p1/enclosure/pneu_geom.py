# -*- coding: utf-8 -*-
"""[弃用 shim · M1 2026-10] 本模块已迁至 flowio/geom/pneu_geom.py, 原位留转发。

(气动结构件几何共享构建器, 域归属说明见 flowio/geom/pneu_geom.py 模块头。)
sys.modules 顶替法转发; 新代码一律 `from flowio.geom import pneu_geom`。
保留一个版本周期, M5 收单后删除。
"""
import sys
from pathlib import Path

_ROOT = str(Path(__file__).resolve().parents[3])   # enclosure -> flowio-p1 -> hardware -> 仓库根
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from flowio.geom import pneu_geom as _real  # noqa: E402

sys.modules[__name__] = _real
