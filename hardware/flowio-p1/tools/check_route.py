# -*- coding: utf-8 -*-
# tools/check_route.py — 布线连通性守门 (只读, 永不落盘; 重放链尾闸门)
# 双绿门: ① ratsnest 未连数 == 0  ② 无布线过孔钻入四铜柱环
# (铜柱环真值同 tools/del_bad_via.py --report / case_geom.py: PD=2.8,
#  BOSS_RING=1.75, ST 四铜柱心; KiCad10 SWIG 无可迭代 GetRatsnest, 故只打印计数)
# 用法: cd hardware/flowio-p1 && "E:/Program Files/KiCad/10.0/bin/python.exe" tools/check_route.py
# 全绿 exit 0, 任一红 exit 1 (挂 rebuild-matrix place_layout / footprint_rules 链尾)
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
BF = os.path.join(HERE, "..", "flowio-p1.kicad_pcb")
MM = pcbnew.ToMM

b = pcbnew.LoadBoard(BF)
b.BuildConnectivity()
n_unc = b.GetConnectivity().GetUnconnectedCount(True)
print("unconnected:", n_unc)
if n_unc:
    print("  (明细用 tools/fix4_status.py 诊断)")

# 铜柱环检查 (逻辑同 del_bad_via.py --report, 只查不删)
BOSS_R = 2.8 / 2 + 1.75          # 3.15 柱外径半径
ST = [(3.4, 3.4), (3.0, 28.0), (83.0, 12.5), (73.5, 55.7)]
bad = []
for t in b.GetTracks():
    if t.Type() == pcbnew.PCB_VIA_T:
        p = t.GetPosition()
        x, y, d = MM(p.x), MM(p.y), MM(t.GetDrill())
        if any((x - sx) ** 2 + (y - sy) ** 2 < (BOSS_R + d / 2 + 0.05) ** 2
               for sx, sy in ST):
            bad.append((x, y, d, t.GetNetname()))
for x, y, d, net in bad:
    print("boss-ring via (%.2f,%.2f) d=%.2f net=%s" % (x, y, d, net))
print("boss-ring vias:", len(bad))

ok = (n_unc == 0) and (not bad)
print("CHECK_ROUTE", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
