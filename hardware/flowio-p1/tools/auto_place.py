# -*- coding: utf-8 -*-
"""布局自动微调 v2: 直接读 flowio-p1.kicad_pcb 的封装几何,
锚定连接器/IC, 小器件在重叠时沿较小重叠轴退让, 收敛后回写板文件 + JSON。
用法: kiCad-python auto_place.py
"""
import os, json
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
BOARD_FILE = "flowio-p1.kicad_pcb"       # 相对当前目录 (用法: 在 flowio-p1/ 下运行)
board = pcbnew.LoadBoard(BOARD_FILE)

def anchored(ref):
    if ref[0] in "HU" or ref.startswith("SW") or ref.startswith("J") or ref == "L1":
        return True
    if ref.startswith("TP"):
        return False
    return False

geom = {}
for fp in board.GetFootprints():
    if fp.GetReference().startswith("H"):  # 安装孔
        continue
    bb = fp.GetBoundingBox()
    pos = fp.GetPosition()
    geom[fp.GetReference()] = dict(
        fp=fp,
        x1=pcbnew.ToMM(bb.GetX()), y1=pcbnew.ToMM(bb.GetY()),
        x2=pcbnew.ToMM(bb.GetX() + bb.GetWidth()),
        y2=pcbnew.ToMM(bb.GetY() + bb.GetHeight()))

def overlap(a, b):
    return (min(a["x2"], b["x2"]) - max(a["x1"], b["x1"]),
            min(a["y2"], b["y2"]) - max(a["y1"], b["y1"]))

moved_any, rounds = True, 0
while moved_any and rounds < 80:
    rounds += 1
    moved_any = False
    refs = list(geom)
    for i in range(len(refs)):
        for j in range(i + 1, len(refs)):
            a, b = geom[refs[i]], geom[refs[j]]
            ox, oy = overlap(a, b)
            if ox > 0.5 and oy > 0.5:
                if anchored(refs[i]) and anchored(refs[j]):
                    continue
                mv, other = (a, b) if not anchored(refs[i]) else (b, a)
                ox, oy = overlap(mv, other)
                if ox <= oy:
                    d = 0.7 if (mv["x1"] + mv["x2"]) < (other["x1"] + other["x2"]) else -0.7
                    mv["x1"] += d; mv["x2"] += d
                else:
                    d = 0.7 if (mv["y1"] + mv["y2"]) < (other["y1"] + other["y2"]) else -0.7
                    mv["y1"] += d; mv["y2"] += d
                moved_any = True
    for g in geom.values():
        if g["x1"] < 0.7:
            d = 0.7 - g["x1"]; g["x1"] += d; g["x2"] += d
        if g["y1"] < 0.7:
            d = 0.7 - g["y1"]; g["y1"] += d; g["y2"] += d
        if g["x2"] > 79.3:
            d = g["x2"] - 79.3; g["x1"] -= d; g["x2"] -= d
        if g["y2"] > 69.3:
            d = g["y2"] - 69.3; g["y1"] -= d; g["y2"] -= d

left = []
refs = list(geom)
for i in range(len(refs)):
    for j in range(i + 1, len(refs)):
        ox, oy = overlap(geom[refs[i]], geom[refs[j]])
        if ox > 0.5 and oy > 0.5:
            left.append((refs[i], refs[j], round(ox, 1), round(oy, 1)))
print("剩余冲突:", left if left else "无", f"({rounds} 轮)")

# 应用回板文件
solved = {}
for ref, g in geom.items():
    cx = (g["x1"] + g["x2"]) / 2
    cy = (g["y1"] + g["y2"]) / 2
    # 位移 = 新中心 - 旧中心(旧中心按当前 fp bbox)
    bb = g["fp"].GetBoundingBox()
    ocx = pcbnew.ToMM(bb.GetX() + bb.GetWidth() / 2)
    ocy = pcbnew.ToMM(bb.GetY() + bb.GetHeight() / 2)
    g["fp"].Move(pcbnew.VECTOR2I(int(pcbnew.FromMM(cx - ocx)),
                                 int(pcbnew.FromMM(cy - ocy))))
    solved[ref] = [round(cx, 2), round(cy, 2)]
pcbnew.SaveBoard(BOARD_FILE, board)
from pathlib import Path as _P
_P("place_solved.json").write_bytes(json.dumps(solved, ensure_ascii=False, indent=1).encode("utf-8"))
print("已回写板文件 + place_solved.json")
