# -*- coding: utf-8 -*-
"""力导向布局精修(正确版)
- 锚定件(连接器/IC/开关/L1)只施力不受力
- 可动件带阻尼速度 + 原位弱弹簧 + 边界约束
- 步长退火 0.4 -> 0.05
排除: 端子链 J10-J17 相互接触(设计意图)
用法: kiCad-python fd_solve.py [board.kicad_pcb]
"""
import os, sys, math
import pcbnew

BF = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "flowio-p1.kicad_pcb")
board = pcbnew.LoadBoard(BF)

TERM = {f"J{n}" for n in range(10, 18)}          # 端子链: 相互接触按设计
def anchored(ref):
    return (ref[0] in "HU" or ref.startswith("SW") or ref.startswith("J")
            or ref == "L1")

P = {}
for fp in board.GetFootprints():
    ref = fp.GetReference()
    if ref.startswith("H"):
        continue
    bb = fp.GetBoundingBox()
    P[ref] = dict(
        fp=fp, anc=anchored(ref),
        w=pcbnew.ToMM(bb.GetWidth()), h=pcbnew.ToMM(bb.GetHeight()),
        cx=pcbnew.ToMM(bb.GetX() + bb.GetWidth() / 2),
        cy=pcbnew.ToMM(bb.GetY() + bb.GetHeight() / 2),
        vx=0.0, vy=0.0)
    P[ref]["ox"], P[ref]["oy"] = P[ref]["cx"], P[ref]["cy"]

# 板边界(从 Edge_Cuts 估算)
minx = miny = 1e9; maxx = maxy = -1e9
for d in board.GetDrawings():
    if d.GetLayer() == pcbnew.Edge_Cuts and d.GetShape() == pcbnew.SHAPE_T_SEGMENT:
        s, e = d.GetStart(), d.GetEnd()
        for pt in (s, e):
            minx = min(minx, pcbnew.ToMM(pt.x)); maxx = max(maxx, pcbnew.ToMM(pt.x))
            miny = min(miny, pcbnew.ToMM(pt.y)); maxy = max(maxy, pcbnew.ToMM(pt.y))
print(f"board: {minx:.0f}..{maxx:.0f} x {miny:.0f}..{maxy:.0f}")

refs = list(P)
ITER, DAMP = 400, 0.55
for it in range(ITER):
    step = 0.4 * (1 - it / ITER) + 0.05
    fx = {r: 0.0 for r in refs}; fy = {r: 0.0 for r in refs}
    for i in range(len(refs)):
        for j in range(i + 1, len(refs)):
            a, b = P[refs[i]], P[refs[j]]
            if refs[i] in TERM and refs[j] in TERM:
                continue
            ox = (a["w"] + b["w"]) / 2 - abs(a["cx"] - b["cx"])
            oy = (a["h"] + b["h"]) / 2 - abs(a["cy"] - b["cy"])
            if ox > 0.3 and oy > 0.3:
                if ox <= oy:
                    s = 1.0 if a["cx"] < b["cx"] else -1.0
                    f = min(ox + 0.4, 2.5)
                    if not a["anc"]: fx[refs[i]] += s * f
                    if not b["anc"]: fx[refs[j]] -= s * f
                else:
                    s = 1.0 if a["cy"] < b["cy"] else -1.0
                    f = min(oy + 0.4, 2.5)
                    if not a["anc"]: fy[refs[i]] += s * f
                    if not b["anc"]: fy[refs[j]] -= s * f
    for r in refs:
        g = P[r]
        if g["anc"]:
            g["vx"] = g["vy"] = 0.0
            continue
        fx[r] += (g["ox"] - g["cx"]) * 0.03
        fy[r] += (g["oy"] - g["cy"]) * 0.03
        g["vx"] = g["vx"] * DAMP + fx[r]
        g["vy"] = g["vy"] * DAMP + fy[r]
        g["cx"] += max(-step, min(step, g["vx"]))
        g["cy"] += max(-step, min(step, g["vy"]))
        m = 0.9
        g["cx"] = min(maxx - m - g["w"] / 2, max(minx + m + g["w"] / 2, g["cx"]))
        g["cy"] = min(maxy - m - g["h"] / 2, max(miny + m + g["h"] / 2, g["cy"]))

n = 0
for r, g in P.items():
    g["fp"].SetPosition(pcbnew.VECTOR2I(int(pcbnew.FromMM(g["cx"])),
                                        int(pcbnew.FromMM(g["cy"]))))
for i in range(len(refs)):
    for j in range(i + 1, len(refs)):
        if refs[i] in TERM and refs[j] in TERM:
            continue
        a, b = P[refs[i]], P[refs[j]]
        ox = (a["w"] + b["w"]) / 2 - abs(a["cx"] - b["cx"])
        oy = (a["h"] + b["h"]) / 2 - abs(a["cy"] - b["cy"])
        if ox > 0.3 and oy > 0.3:
            n += 1
            if n <= 15:
                print(f"  {refs[i]} x {refs[j]}: {ox:.1f}x{oy:.1f}")
pcbnew.SaveBoard(BF, board)
print("剩余冲突(不含端子链):", n)
