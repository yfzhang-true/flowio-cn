# -*- coding: utf-8 -*-
"""flowio.core.errors — 域异常层次 (spec v2.1 §2 包结构 / §3.3 封装)。

层次: FlowioError(RuntimeError) 为公共根, 四域细分 ——
  TruthError  真值层: devices.json 加载/解析/schema 校验失败 (fail-loud, 禁静默兜底);
  GeomError   结构域: 几何求解/装配干涉/包络失败;
  RouteError  硬件域: 布线/网络求解失败;
  SimError    孪生域: 仿真推进/参数求解失败。

兼容: 全系最终继承 RuntimeError —— 既有 try/except RuntimeError 语义不破坏。
"""


class FlowioError(RuntimeError):
    """flowio 全域异常公共根 (统一捕获入口)。"""


class TruthError(FlowioError):
    """真值层失败: devices.json 缺失/JSON 损坏/两段 schema 校验不过。"""


class GeomError(FlowioError):
    """结构域几何失败 (M1 geom 子包消费)。"""


class RouteError(FlowioError):
    """硬件域布线/网络失败 (M1 hw 子包消费)。"""


class SimError(FlowioError):
    """孪生域仿真失败 (M2 twin 子包消费)。"""
