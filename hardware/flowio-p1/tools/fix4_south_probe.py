# -*- coding: utf-8 -*-
"""fix4b: 南走廊探测 — In1 水平线 (46.2,y)->(62.8,y) 障碍核验, y 扫描找净距>=0.205 的窗口."""
import sys, math
sys.path.insert(0, "tools")
import pcbnew

b = pcbnew.LoadBoard("flowio-p1.kicad_pcb")
MM = pcbnew.ToMM
I1 = 4
CLR = 0.205  # 板上沿用的净距 (fix3 同款)

def pt_seg(px, py, ax, ay, bx, by):
    dx, dy = bx-ax, by-ay
    L2 = dx*dx+dy*dy
    if L2 == 0:
        return math.hypot(px-ax, py-ay)
    t = max(0, min(1, ((px-ax)*dx+(py-ay)*dy)/L2))
    return math.hypot(px-(ax+t*dx), py-(ay+t*dy))

def seg_seg(a1, a2, b1, b2):
    # 两线段最小距离 (粗: 采样 + 端点到线段)
    ds = []
    for (px, py) in (a1, a2):
        ds.append(pt_seg(px, py, b1[0], b1[1], b2[0], b2[1]))
    for (px, py) in (b1, b2):
        ds.append(pt_seg(px, py, a1[0], a1[1], a2[0], a2[1]))
    # 采样中间
    for i in range(1, 20):
        t = i/20
        px, py = a1[0]+(a2[0]-a1[0])*t, a1[1]+(a2[1]-a1[1])*t
        ds.append(pt_seg(px, py, b1[0], b1[1], b2[0], b2[1]))
        px, py = b1[0]+(b2[0]-b1[0])*t, b1[1]+(b2[1]-b1[1])*t
        ds.append(pt_seg(px, py, a1[0], a1[1], a2[0], a2[1]))
    return min(ds)

# 障碍: In1 非 IO21 走线 + 所有非 IO21 via (通孔全层) + 通孔焊盘
obs_tracks = []
for t in b.GetTracks():
    if t.GetClass() == "PCB_VIA":
        if t.GetNetname() == "IO21":
            continue
        q = t.GetPosition()
        obs_tracks.append(("via", t.GetNetname(), MM(q.x), MM(q.y), MM(q.x), MM(q.y), MM(t.GetWidth(0))/2))
    else:
        if t.GetNetname() == "IO21" or t.GetLayer() != I1:
            continue
        s, e = t.GetStart(), t.GetEnd()
        obs_tracks.append(("trk", t.GetNetname(), MM(s.x), MM(s.y), MM(e.x), MM(e.y), MM(t.GetWidth())/2))

obs_pads = []
for f in b.GetFootprints():
    for p in f.Pads():
        if p.GetNetname() == "IO21":
            continue
        if p.GetAttribute() == pcbnew.PAD_ATTRIB_SMD:
            if p.GetLayer() != I1:  # SMD 只在自身层
                continue
        c, sz = p.GetPosition(), p.GetSize()
        rot = math.radians(p.GetOrientation().AsDegrees())
        obs_pads.append((f.GetReference()+"."+p.GetPadName(), p.GetNetname(), MM(c.x), MM(c.y),
                         MM(sz.x)/2, MM(sz.y)/2, math.cos(rot), math.sin(rot)))

def pad_edge(x, y, pad):
    _r, _n, px, py, hw, hh, c, s = pad
    dx, dy = x-px, y-py
    lx, ly = c*dx+s*dy, -s*dx+c*dy
    qx, qy = abs(lx)-hw, abs(ly)-hh
    return math.hypot(max(qx, 0), max(qy, 0)) if qx > 0 or qy > 0 else max(qx, qy)

print(f"障碍: {len(obs_tracks)} 走线/孔, {len(obs_pads)} 焊盘")
W = 0.25
best = []
for yi in range(500, 581):  # y 50.0 - 58.0 步 0.1
    y = yi/10.0
    worst = 999
    witem = None
    a1, a2 = (46.2, y), (62.8, y)
    for kind, n, ax, ay, bx, by, hw in obs_tracks:
        d = seg_seg(a1, a2, (ax, ay), (bx, by)) - hw - W/2
        if d < worst:
            worst, witem = d, (kind, n, ax, ay, bx, by)
    # pads: 采样沿线
    for kx in range(0, 167):
        x = 46.2 + kx*0.1
        for pad in obs_pads:
            if abs(pad[2]-x) < 2.5 and abs(pad[3]-y) < 2.5:
                d = pad_edge(x, y, pad) - W/2
                if d < worst:
                    worst, witem = d, ("pad", pad[0], pad[2], pad[3])
    best.append((y, worst, witem))

ok = [(y, w, i) for y, w, i in best if w >= CLR]
print(f"可行 y 窗口 (净距>={CLR}): {[(y, round(w,3)) for y, w, _ in ok]}")
if not ok:
    for y, w, i in sorted(best, key=lambda z: -z[1])[:8]:
        print(f"  y={y} 最差净距={w:.3f} 障碍={i}")
