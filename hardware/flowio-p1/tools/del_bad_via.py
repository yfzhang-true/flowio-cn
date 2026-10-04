# -*- coding: utf-8 -*-
# tools/del_bad_via.py — 过孔-铜柱守门清扫 (SWIG 一进程一操作)
# T4 布线后运行: 删除钻入铜柱环的布线过孔 (freerouting 只认 DSN 焊盘净空
# ~2.1mm, 铜柱环要求 ≥ boss_r+drill/2+0.05; stage1 过孔已被 npth_min=3.7
# 守住, 这里兜底 SES 导入的外来过孔)。
# 用法: del_bad_via.py [--report]   (--report 只查不删)
import sys
import pcbnew

BF = "flowio-p1.kicad_pcb"
REPORT_ONLY = "--report" in sys.argv

# case_geom.py 真值: PD=2.8, BOSS_RING=1.75, ST=四铜柱心 (与 M3 孔同心)
BOSS_R = 2.8 / 2 + 1.75          # 3.15 柱外径半径
ST = [(3.4, 3.4), (3.0, 28.0), (83.0, 12.5), (73.5, 55.7)]

b = pcbnew.LoadBoard(BF)
n = 0
bad = []
for t in list(b.GetTracks()):
    if t.Type() == pcbnew.PCB_VIA_T:
        p = t.GetPosition()
        x, y = pcbnew.ToMM(p.x), pcbnew.ToMM(p.y)
        drill = pcbnew.ToMM(t.GetDrill())
        for sx, sy in ST:
            if (x - sx) ** 2 + (y - sy) ** 2 < (BOSS_R + drill / 2 + 0.05) ** 2:
                bad.append((x, y, drill, t.GetNetname()))
                if not REPORT_ONLY:
                    b.Remove(t)
                n += 1
                break
if not REPORT_ONLY and n:
    pcbnew.SaveBoard(BF, b)
for x, y, d, net in bad:
    print("boss-ring via (%.2f,%.2f) d=%.2f net=%s" % (x, y, d, net))
print(("REPORT " if REPORT_ONLY else "removed ") + str(n))
