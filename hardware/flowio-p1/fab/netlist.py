# -*- coding: utf-8 -*-
"""netlist.py — KiCad S-expr 网表解析 -> 电气边集合 (plan T3, 决策④: 网表为权威源).

输入: fab/flowio-p1.net (kicad-cli sch export netlist --format kicadsexpr)
输出 API:
  nets()            -> [(net_name, [refs...])]
  power_nets()      -> 电源/地网络名集合 (按名称约定)
  electrical_edges()-> {frozenset({a,b}), ...} 剔除电源地后的共网器件对
纯标准库; 逐 (net ...) 节点括号深度扫描切块后取字段, 而非行 split —
KiCad10 网表为多行缩进 s-expr (net / code / name / node 各占一行), 旧版
行分割对齐不到块边界会把"后续全部 node"误并进当前网 (T2 遗留 known-issue, T5 修复)。
"""
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
NETFILE = HERE / "flowio-p1.net" if (HERE / "flowio-p1.net").exists() \
    else HERE.parents[1] / "fab" / "flowio-p1.net"

POWER_HINTS = ("GND", "+3V3", "+5V", "+BATT", "VBUS", "VIN", "+12V", "+VA",
               "VDD", "VSS", "/power/", "Earth", "PWR")


def _find_block(text, start):
    """text[start] == '(' 处的 s-expr 块结尾下标 (闭括号后一位); 括号深度扫描."""
    depth = 0
    for i in range(start, len(text)):
        c = text[i]
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return i + 1
    return len(text)


def _parse_nets(text):
    """顶层 (nets ...) 内逐 (net ...) 节点切块: 取 (name "..") 与全部 (node (ref ".."))."""
    m = re.search(r"\(nets\b", text)
    nets_body_start = m.end() if m else 0
    nets = []
    pos = nets_body_start
    pat = re.compile(r"\(net\b")
    while True:
        m = pat.search(text, pos)
        if not m:
            break
        end = _find_block(text, m.start())
        seg = text[m.start():end]
        nm = re.search(r'\(name\s+"([^"]*)"\)', seg)
        if nm:
            refs = re.findall(r'\(node\s+\(ref\s+"([^"]+)"\)', seg)
            if refs:
                nets.append((nm.group(1), refs))
        pos = end
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
