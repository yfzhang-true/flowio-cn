# -*- coding: utf-8 -*-
"""flowio.twin.devices3d — 孪生器件参数化 3D 构建器 (D1, spec 2026-10-05 §2.1)。

器件 = 三接口面实体 (气动/电气/机械) + 参数化几何 (datasheet 图纸直推):
    valve_f0520d.py   F0520D C 架阀 (本体 20.5×15×13 + 顶翻边 0.7 + N1/N2 双端嘴 ⌀3.0×3.5)
    valve_f0520b.py   F0520B 真空主阀 (总长 28 = 本体 20 + 端段 8, N1 顶嘴 ⌀4.6×6.0)
    pump_zr370.py     ZR370-03PM 立式校正 (头 ⌀24×27.3 + 电机 ⌀27×30.8 + 顶置双嘴 ⌀4.2×7.5 ⊥轴)
    sensor_xgzp.py    XGZP6897D (本体 10.8×7×3.5 + 双倒钩 ⌀3.22×2.4 顶置 + SOIC8 鸥翼)
    fittings.py       硅胶管 (ID3/ID5, 关键弯折点折线 = D4 裁定 A) + Kamoer 直通/变径 + 三通
    harness.py        电气线束视觉桩 (阀 2P 引线 60mm / 泵电缆 150, D2 裁定 A 桩深)

设计纪律 (对齐 geom 包既有模式):
- 建模内核 = FreeCAD Part (OCCT 内嵌, D1 裁定 A **零新依赖**; build123d/CadQuery 不引入);
- 单一真相源: 四器件 builder 默认参数一律读 devices.json pneumatic_devices.*.geom3d
  (device_geom3d()/load_geom3d(), 同 case_geom._load_pneu 模式), 禁本地复制尺寸;
- 分件建模 + 装配组合 (Compound), 不做复杂布尔融合 (make_pump_module 已证模式);
  每模块 build() -> Part.Shape(Compound) + parts() -> {分件名: Part.Shape};
- 本包 __init__ 保持纯 stdlib (devices.json 读取不依赖 FreeCAD), builder 模块惰性导入
  —— flowio.twin 主包在无 FreeCAD 环境 (flowio/tests 双轨) 可照常导入。

接口面数据 (D2 连接图谱消费): device_geom3d(group)["pneumatic_ports" /
"electrical_terminals" / "mech_mounts"], pos 为器件自身原点系 mm 坐标, dir 单位向量。
"""
import json
import os
import sys
from pathlib import Path

_ROOT = str(Path(__file__).resolve().parents[3])             # flowio/twin/devices3d -> 仓库根
if _ROOT not in sys.path:                                    # FreeCAD python 免安装导入
    sys.path.insert(0, _ROOT)

DEVICES_JSON = os.path.join(_ROOT, "hardware", "flowio-p1", "enclosure", "devices.json")

_GROUPS = ("valves", "valve_vacuum_master", "pump", "sensor")

# builder 模块名 -> pneumatic_devices 组 (builder 默认参数的 json 源)
_BUILDERS = {
    "valve_f0520d": "valves",
    "valve_f0520b": "valve_vacuum_master",
    "pump_zr370": "pump",
    "sensor_xgzp": "sensor",
    # fittings / harness 为通用连接件 (非器件实例): 参数即模块 DEFAULTS, 无 json 条目
    "fittings": None,
    "harness": None,
}

__all__ = [
    "load_geom3d", "device_geom3d", "DEVICES_JSON",
    "valve_f0520d", "valve_f0520b", "pump_zr370", "sensor_xgzp", "fittings", "harness",
]


def load_geom3d(path=None):
    """devices.json -> {组名: 该组首条目的 geom3d 块} (纯 stdlib; 失败抛异常, 真值缺失即红)。"""
    with open(path or DEVICES_JSON, encoding="utf-8") as f:
        pn = json.load(f)["pneumatic_devices"]
    return {g: pn[g][0]["geom3d"] for g in _GROUPS}


def device_geom3d(group, path=None):
    """单组 geom3d 块 (builder 默认参数 + D2 连接图谱接口面消费入口)。"""
    return load_geom3d(path)[group]


def __getattr__(name):
    """惰性 builder 导入: FreeCAD (Part/OCCT) 仅在真正建模时加载 ——
    本包 stdlib 面 (load_geom3d/device_geom3d) 在无 FreeCAD 环境零负担可用。"""
    if name in _BUILDERS:
        import importlib
        mod = importlib.import_module("flowio.twin.devices3d." + name)
        globals()[name] = mod
        return mod
    raise AttributeError("module %r has no attribute %r" % (__name__, name))
