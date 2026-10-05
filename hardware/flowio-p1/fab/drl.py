# -*- coding: utf-8 -*-
"""[弃用 shim · M1 2026-10] 本模块已迁至 flowio/hw/drill.py (drl.py 为旧名), 原位留转发。

保留一个版本周期: 旧脚本 (tools/check_fab.py 等) 经 fab/ 路径 import 不改可
继续跑 —— sys.modules 顶替法转发 (旧名与新名为同一模块对象);
新代码一律 `from flowio.hw import drill`。M5 收单后删除本文件。
"""
import sys
from pathlib import Path

_ROOT = str(Path(__file__).resolve().parents[3])   # fab -> flowio-p1 -> hardware -> 仓库根
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from flowio.hw import drill as _real  # noqa: E402

sys.modules[__name__] = _real         # 旧名 drl = flowio.hw.drill 本体

if __name__ == "__main__":            # 旧用法: python fab/drl.py (统计打印)
    hs = _real._parse()
    print("[drl] 总孔 %d, NPTH %d, 刀径 %s"
          % (len(hs), sum(1 for h in hs if h[3]),
             sorted({round(h[2], 2) for h in hs})))
