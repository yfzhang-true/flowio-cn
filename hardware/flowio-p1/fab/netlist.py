# -*- coding: utf-8 -*-
"""netlist.py — KiCad S-expr 网表解析 -> 电气边集合 (plan T3, 决策④: 网表为权威源).

输入: fab/flowio-p1.net (kicad-cli sch export netlist --format kicadsexpr)
输出 API:
  nets()            -> [(net_name, [refs...])]
  power_nets()      -> 电源/地网络名集合 (按名称约定)
  electrical_edges()-> {frozenset({a,b}), ...} 剔除电源地后的共网器件对
纯标准库; 解析用逐括号扫描而非正则嵌套, 抗格式微变.
"""
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
NETFILE = HERE / "flowio-p1.net" if (HERE / "flowio-p1.net").exists() \
    else HERE.parents[1] / "fab" / "flowio-p1.net"

POWER_HINTS = ("GND", "+3V3", "+5V", "+BATT", "VBUS", "VIN", "+12V", "+VA",
               "VDD", "VSS", "/power/", "Earth", "PWR")


def _parse_nets(text):
    """扫描 (net (code "..") (name "..") (node (ref "..") ...) ...) 顶层段."""
    nets = []
    for m in re.finditer(r'\(net\s+\(code\s+"[^"]*"\)\s+\(name\s+"([^"]*)"\)', text):
        name = m.group(1)
        seg = text[m.end(): text.find("\n\t(net ", m.end()) if text.find("\n\t(net ", m.end()) > 0 else len(text)]
        refs = re.findall(r'\(node\s+\(ref\s+"([^"]+)"\)', seg)
        if refs:
            nets.append((name, refs))
    return nets


def _is_power(name):
    n = name.upper()
    return any(h.upper() in n for h in POWER_HINTS)


def nets():
    return _parse_nets(Path(NETFILE).read_text(encoding="utf-8", errors="replace"))


def power_nets():
    return {n for n, refs in nets() if _is_power(n)}


def electrical_edges():
    edges = set()
    for name, refs in nets():
        if _is_power(name):
            continue
        uniq = sorted(set(refs))
        for i in range(len(uniq)):
            for j in range(i + 1, len(uniq)):
                edges.add(frozenset((uniq[i], uniq[j])))
    return edges


if __name__ == "__main__":
    ns = nets()
    print("[netlist] nets=%d (power %d) elec_edges=%d refs=%d"
          % (len(ns), len(power_nets()), len(electrical_edges()),
             len({r for _, rs in ns for r in rs})))
