# -*- coding: utf-8 -*-
"""[弃用 shim · M1 2026-10] 本模块已迁至 flowio/geom/case_geom.py, 原位留转发。

case_geom 保持"装配几何单一真相源"角色不变 —— 正名 = flowio.geom.case_geom,
测试/生成器一律经 flowio.geom 取常量; 本 shim 以 sys.modules 顶替法转发
(旧名与新名为**同一模块对象**, _PNEU/_KW_DIMS 等私有名与身份均一致),
旧脚本不改可继续跑。保留一个版本周期, M5 收单后删除 (spec 2026-10-05 §2)。
"""
import sys
from pathlib import Path

_ROOT = str(Path(__file__).resolve().parents[3])   # enclosure -> flowio-p1 -> hardware -> 仓库根
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from flowio.geom import case_geom as _real  # noqa: E402

sys.modules[__name__] = _real               # 旧名 = 新模块本体 (含私有名, 身份同一)
