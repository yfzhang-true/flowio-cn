# -*- coding: utf-8 -*-
# tools/scan_fab.py — 制造前工艺扫描 (只读, T5): via-in-pad 清单 / hole-to-hole 实测 / 最小线宽
# 判据 (任务书 T5-2): 过孔孔中心落在任意 SMD 焊盘 bbox 内 (含 GND 过孔在 EP 上) 即计入;
# 输出 ref/pad/net/坐标; 另附 hole_to_hole 壁距实测 (DRC 15 条 warning 逐条量化) 与
# 全板最小线宽 (布线终态实测值, 供 README-fab 与 JLC 工艺复核表)。
# 用法: cd hardware/flowio-p1 && "E:/Program Files/KiCad/10.0/bin/python.exe" tools/scan_fab.py
# 只读不落盘; SWIG 铁律: 一进程一操作, 本脚本不修改 board。
import json
import math
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
BF = os.path.join(HERE, "..", "flowio-p1.kicad_pcb")
MM = pcbnew.ToMM

b = pcbnew.LoadBoard(BF)
b.BuildConnectivity()

# ── 板外框 (100x80 核对) ─────────────────────────────────────────
bb = b.GetBoardEdgesBoundingBox()
print("BOARD_EDGES %.2f x %.2f mm" % (MM(bb.GetWidth()), MM(bb.GetHeight())))

# ── SMD 焊盘收集 (含 EP: PAD_ATTRIB_SMD / CONN) ─────────────────
def pad_bbox(p):
    """旋转矩形焊盘 bbox -> (cx, cy, hx, hy) (含形状包围, mm)."""
    px, py = MM(p.GetPosition().x), MM(p.GetPosition().y)
    w, h = MM(p.GetSize().x), MM(p.GetSize().y)
    ang = math.radians(p.GetOrientation().AsDegrees())
    ca, sa = abs(math.cos(ang)), abs(math.sin(ang))
    hx = (w * ca + h * sa) / 2.0
    hy = (w * sa + h * ca) / 2.0
    return px, py, hx, hy


SMD_ATTRS = (pcbnew.PAD_ATTRIB_SMD, pcbnew.PAD_ATTRIB_CONN)
smd_pads = []       # (ref, padnum, net, bbox)
pth_pads = []       # (ref, padnum, net, pos, drill)
for fp in b.GetFootprints():
    ref = fp.GetReference()
    for p in fp.Pads():
        attr = p.GetAttribute()
        net = p.GetNetname()
        num = p.GetNumber()
        if attr in SMD_ATTRS:
            smd_pads.append((ref, num, net, pad_bbox(p)))
        elif attr == pcbnew.PAD_ATTRIB_PTH or p.GetDrillSize().x > 0:
            dsz = p.GetDrillSize()
            d = MM(dsz.x) if dsz.x else MM(dsz.y)
            if d > 0:
                pth_pads.append((ref, num, net,
                                 (MM(p.GetPosition().x), MM(p.GetPosition().y)), d))
print("SMD_PADS %d  PTH_PADS %d  FOOTPRINTS %d"
      % (len(smd_pads), len(pth_pads), len(b.GetFootprints())))

# ── 过孔清单 ─────────────────────────────────────────────────────
vias = []           # dict(x,y,drill,width,net,vtype)
VT = {pcbnew.VIATYPE_THROUGH: "TH", pcbnew.VIATYPE_BLIND: "BB",
      pcbnew.VIATYPE_BURIED: "BB", pcbnew.VIATYPE_MICROVIA: "u"}
for t in b.GetTracks():
    if t.Type() == pcbnew.PCB_VIA_T:
        p = t.GetPosition()
        # KiCad10: PCB_VIA::GetWidth() 无层参数会 assert, 逐 via 取其层集首层宽
        try:
            w = MM(t.GetWidth(pcbnew.F_Cu))
        except Exception:
            w = MM(t.GetWidth(pcbnew.B_Cu))
        vias.append({"x": MM(p.x), "y": MM(p.y), "drill": MM(t.GetDrill()),
                     "width": w, "net": t.GetNetname(),
                     "vtype": VT.get(t.GetViaType(), "?")})
print("VIAS %d (%s)" % (len(vias),
      ", ".join("%s:%d" % (k, sum(1 for v in vias if v["vtype"] == k))
                for k in ("TH", "BB", "u"))))
dh = {}
for v in vias:
    dh[round(v["drill"], 2)] = dh.get(round(v["drill"], 2), 0) + 1
print("VIA_DRILL_HIST %s" % json.dumps(dh, sort_keys=True))

# ── via-in-pad: 孔中心 ∈ SMD bbox ──────────────────────────────
vip = []
for v in vias:
    for ref, num, net, (cx, cy, hx, hy) in smd_pads:
        if abs(v["x"] - cx) <= hx and abs(v["y"] - cy) <= hy:
            vip.append((ref, num, v["net"], v["x"], v["y"], v["drill"],
                        v["width"], net))
print("--- VIA_IN_PAD (%d) ---" % len(vip))
for ref, num, vnet, x, y, d, w, pnet in vip:
    print("VIP %s.%s pad_net=%s via_net=%s @(%.3f,%.3f) drill=%.2f annular=%.2f"
          % (ref, num, pnet, vnet, x, y, d, w))

# PTH 焊盘与过孔同位 (holes_co_located 复核, 不入塞孔清单)
print("--- VIA_ON_PTH_PAD ---")
for v in vias:
    for ref, num, net, (px, py), d in pth_pads:
        if abs(v["x"] - px) < 0.05 and abs(v["y"] - py) < 0.05:
            print("VPTH %s.%s net=%s via_drill=%.2f pad_drill=%.2f @(%.3f,%.3f)"
                  % (ref, num, net, v["drill"], d, v["x"], v["y"]))

# ── hole-to-hole 壁距实测 (过孔↔过孔, 含盲埋) ────────────────────
print("--- HOLE_TO_HOLE (wall < 0.30mm) ---")
n_h2h = 0
for i in range(len(vias)):
    for j in range(i + 1, len(vias)):
        a, c = vias[i], vias[j]
        dist = math.hypot(a["x"] - c["x"], a["y"] - c["y"])
        wall = dist - (a["drill"] + c["drill"]) / 2.0
        if wall < 0.30:
            n_h2h += 1
            print("H2H %s[%.2f]@(%.3f,%.3f) <-> %s[%.2f]@(%.3f,%.3f) "
                  "center=%.3f wall=%.3f"
                  % (a["net"], a["drill"], a["x"], a["y"],
                     c["net"], c["drill"], c["x"], c["y"], dist, wall))
print("H2H_COUNT %d" % n_h2h)

# 过孔↔PTH 焊盘孔壁距 (补充: 过孔钻入插件孔净空)
print("--- VIA_TO_PTH_HOLE (wall < 0.30mm) ---")
for v in vias:
    for ref, num, net, (px, py), d in pth_pads:
        dist = math.hypot(v["x"] - px, v["y"] - py)
        wall = dist - (v["drill"] + d) / 2.0
        if 0 < wall < 0.30:
            print("V2P %s.%s pad_drill=%.2f via[%.2f] center=%.3f wall=%.3f"
                  % (ref, num, d, v["drill"], dist, wall))

# ── 最小线宽实测 ────────────────────────────────────────────────
wmin, wmin_net = 1e9, ""
whist = {}
n_tr = 0
for t in b.GetTracks():
    if t.Type() in (pcbnew.PCB_TRACE_T, pcbnew.PCB_ARC_T):
        w = MM(t.GetWidth())
        n_tr += 1
        whist[round(w, 3)] = whist.get(round(w, 3), 0) + 1
        if w < wmin:
            wmin, wmin_net = w, t.GetNetname()
print("TRACKS %d  MIN_WIDTH %.3f (net=%s)" % (n_tr, wmin, wmin_net))
print("WIDTH_HIST %s" % json.dumps(whist, sort_keys=True))

# ── 设计规则真值 (净空/孔净空) ──────────────────────────────────
ds = b.GetDesignSettings()
try:
    print("RULES min_clearance=%.3f hole_clearance=%.3f hole_to_hole=%.3f "
          "copper_edge=%.3f silk_clearance=%.3f mask_to_copper=%.3f"
          % (MM(ds.m_MinClearance), MM(ds.m_HoleClearance), MM(ds.m_HoleToHoleMin),
             MM(ds.m_CopperEdgeClearance), MM(ds.m_SilkClearance),
             MM(ds.m_SolderMaskToCopperClearance)))
except Exception as ex:
    print("ds probe fail:", ex)
