# -*- coding: utf-8 -*-
"""[弃用 shim · M1 2026-10] 本模块已迁至 flowio/hw/netlist.py, 原位留转发。

保留一个版本周期: 旧脚本/测试经 fab/ 路径 import 不改可继续跑 —— 本 shim 以
sys.modules 顶替法转发 (旧名与新名为**同一模块对象**, 私有名/身份均一致);
新代码一律 `from flowio.hw import netlist`。M5 收单后删除本文件。
"""
import sys
from pathlib import Path

_ROOT = str(Path(__file__).resolve().parents[3])   # fab -> flowio-p1 -> hardware -> 仓库根
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from flowio.hw import netlist as _real  # noqa: E402

sys.modules[__name__] = _real           # 旧名 = 新模块本体 (含私有名, 身份同一)

if __name__ == "__main__":              # 旧用法: python fab/netlist.py (统计打印)
    ns = _real.nets()
    print("[netlist] nets=%d (power %d) elec_edges=%d refs=%d"
          % (len(ns), len(_real.power_nets()), len(_real.electrical_edges()),
             len({r for _, rs in ns for r in rs})))
