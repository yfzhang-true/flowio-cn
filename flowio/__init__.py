# -*- coding: utf-8 -*-
"""flowio — FLOWIO-CN 数字孪生全栈内核包 (spec v2.1 §2 目标包结构)。

单一真值 devices.json 到五域介质 (硬件/结构/固件/孪生/呈现) 的共享抽象;
M0 落地 core 抽象层 + truth 真值层, M1-M5 渐进迁入 hw/geom/flows/twin/fwgen/webgen。

用法 (免安装, 任意 python3):
    import sys, pathlib; sys.path.insert(0, str(pathlib.Path("<repo>/").resolve()))
    from flowio import TruthSource, IActuator, TruthError
或: pip install -e <repo>   (pyproject.toml 位于仓库根)
"""
from flowio.core.errors import (FlowioError, GeomError, RouteError, SimError,  # noqa: F401
                                TruthError)
from flowio.core.interfaces import BaseModel, IActuator, ISensor  # noqa: F401

__version__ = "0.1.0"

__all__ = ["FlowioError", "TruthError", "GeomError", "RouteError", "SimError",
           "IActuator", "ISensor", "BaseModel", "__version__"]
