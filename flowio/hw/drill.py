# -*- coding: utf-8 -*-
"""drill.py — Excellon 钻孔文件解析 (plan T4; M1 前名 drl.py).

输入: hardware/flowio-p1/fab/flowio-p1.drl (KiCad 导出, 公制小数, MixedPlating)
输出 API:
  holes()       -> [(x板, y板(=-Y 取负), dia)] 全部孔 (含 PTH)
  npth_holes()  -> 仅 NPTH 段 (非金属化, M3 安装孔在此段)
M1 迁移 (2026-10): fab/drl.py -> flowio/hw/drill.py (逻辑零改动,
仅 DRL 路径解析改经包定位)。
"""
import re
from pathlib import Path

DRL = Path(__file__).resolve().parents[2] / "hardware" / "flowio-p1" \
    / "fab" / "flowio-p1.drl"


def _parse():
    text = DRL.read_text(encoding="utf-8", errors="replace")
    tools = {}          # T号 -> (dia, is_npth)
    cur_np = False
    for m in re.finditer(r"; #@! TA\.AperFunction,(\w+)[^\n]*\nT(\d+)C([\d.]+)", text):
        func, tn, dia = m.group(1), m.group(2), float(m.group(3))
        tools[tn] = (dia, func == "NonPlated")
    out = []
    cur = None
    for ln in text.splitlines():
        s = ln.strip()
        m = re.match(r"^T(\d+)$", s)
        if m:
            cur = m.group(1)
            continue
        m = re.match(r"^X(-?[\d.]+)Y(-?[\d.]+)$", s)
        if m and cur in tools:
            x, y = float(m.group(1)), float(m.group(2))
            out.append((x, -y, tools[cur][0], tools[cur][1]))
    return out


def holes():
    return [(x, y, d) for x, y, d, _ in _parse()]


def npth_holes():
    return [(x, y, d) for x, y, d, np in _parse() if np]


if __name__ == "__main__":
    hs = _parse()
    print("[drl] 总孔 %d, NPTH %d, 刀径 %s"
          % (len(hs), sum(1 for h in hs if h[3]),
             sorted({round(h[2], 2) for h in hs})))
