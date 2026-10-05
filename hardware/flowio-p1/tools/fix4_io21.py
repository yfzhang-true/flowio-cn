# -*- coding: utf-8 -*-
"""fix4b: IO21 东西轨贯通 — In2 微桥·南线终态 (纯增量, 不动任何异网):
  via1 (46.2,55.5) 落 In1 A-竖线 x46.2 (IO21 自身) <-> In2
  In2: (46.2,55.5)->(62.8,51.4) w=0.25 对角微桥 (全板 In2 仅 7 线, 桥窗在 +3V3 平面空旷区)
  via2 (62.8,51.4) 落 In1 B-竖线 x62.8 (IO21 自身)
拓扑死局存档 (35a9628): 弃 In1 硬穿——SE 堡垒(S3/S1 对角阵)/IO11 墙(x46.8,y33-55)/
  BTN_USER 阵 30+ 路径全败(0.02-0.3mm 近失是拓扑死局假象, 微调无解)→ In2 微桥, 最差净距 0.332."""
import sys, math
sys.path.insert(0, "tools")
import pcbnew

b = pcbnew.LoadBoard("flowio-p1.kicad_pcb")
MM, FM, VI = pcbnew.ToMM, pcbnew.FromMM, pcbnew.VECTOR2I
F, B_, I1, I2 = 0, 2, 4, 6
CLR = 0.2
NET = "IO21"

# 南方案参数空间: via1 落 A-竖线 x46.2 (y40.85-57.5), via2 落 B-竖线 x62.8 (y46.05-55.8)
# In2 直连. 预检全障碍后择优.
CANDS1 = [(46.2, round(y, 2)) for y in [52.5 + 0.1*i for i in range(31)]]   # 52.5-55.5
CANDS2 = [(62.8, round(y, 2)) for y in [46.2 + 0.2*i for i in range(48)]]   # 46.2-55.6
TW = 0.25
VIAW, VIADR = 0.6, 0.3

def pt_seg(px, py, ax, ay, bx, by):
    dx, dy = bx-ax, by-ay
    L2 = dx*dx+dy*dy
    if L2 == 0:
        return math.hypot(px-ax, py-ay)
    t = max(0, min(1, ((px-ax)*dx+(py-ay)*dy)/L2))
    return math.hypot(px-(ax+t*dx), py-(ay+t*dy))

def seg_seg(a1, a2, b1, b2):
    ds = []
    for (px, py) in (a1, a2):
        ds.append(pt_seg(px, py, b1[0], b1[1], b2[0], b2[1]))
    for (px, py) in (b1, b2):
        ds.append(pt_seg(px, py, a1[0], a1[1], a2[0], a2[1]))
    for i in range(1, 30):
        t = i/30
        px, py = a1[0]+(a2[0]-a1[0])*t, a1[1]+(a2[1]-a1[1])*t
        ds.append(pt_seg(px, py, b1[0], b1[1], b2[0], b2[1]))
        px, py = b1[0]+(b2[0]-b1[0])*t, b1[1]+(b2[1]-b1[1])*t
        ds.append(pt_seg(px, py, a1[0], a1[1], a2[0], a2[1]))
    return min(ds)

def pad_edge(x, y, pad):
    _n, px, py, hw, hh, c, s = pad[0], pad[1], pad[2], pad[3], pad[4], pad[5], pad[6]
    dx, dy = x-px, y-py
    lx, ly = c*dx+s*dy, -s*dx+c*dy
    qx, qy = abs(lx)-hw, abs(ly)-hh
    return math.hypot(max(qx, 0), max(qy, 0)) if qx > 0 or qy > 0 else max(qx, qy)

# 障碍库
trks = []  # (net, layer, ax, ay, bx, by, hw)
vias = []  # (net, x, y, r)
pads = []  # (net, x, y, hw, hh, cos, sin, drill_r, ref)
for t in b.GetTracks():
    if t.GetClass() == "PCB_VIA":
        q = t.GetPosition()
        vias.append((t.GetNetname(), MM(q.x), MM(q.y), MM(t.GetWidth(0))/2))
    else:
        s, e = t.GetStart(), t.GetEnd()
        trks.append((t.GetNetname(), t.GetLayer(), MM(s.x), MM(s.y), MM(e.x), MM(e.y), MM(t.GetWidth())/2))
for f in b.GetFootprints():
    for p in f.Pads():
        c, sz = p.GetPosition(), p.GetSize()
        rot = math.radians(p.GetOrientation().AsDegrees())
        dr = MM(p.GetDrillSizeX())/2 if p.GetAttribute() != pcbnew.PAD_ATTRIB_SMD else 0.0
        pads.append((p.GetNetname(), MM(c.x), MM(c.y), MM(sz.x)/2, MM(sz.y)/2,
                     math.cos(rot), math.sin(rot), dr, f.GetReference()+"."+p.GetPadName()))

def check_vialoc(x, y):
    """via 全层核验, 返回最差间隙 (与描述). IO21 自身不算."""
    worst, witem = 99, None
    for (n, ly, ax, ay, bx, by, hw) in trks:
        if n == NET:
            continue
        d = pt_seg(x, y, ax, ay, bx, by) - hw - VIAW/2
        if d < worst:
            worst, witem = d, f"trk {n} L{ly}"
    for (n, vx, vy, vr) in vias:
        if n == NET:
            continue
        d = math.hypot(vx-x, vy-y) - vr - VIAW/2
        if d < worst:
            worst, witem = d, f"via {n}@({vx:.2f},{vy:.2f})"
    for pad in pads:
        n, px, py = pad[0], pad[1], pad[2]
        if n == NET:
            continue
        d = pad_edge(x, y, pad) - VIAW/2
        if d < worst:
            worst, witem = d, f"pad {pad[8]}"
        if pad[7] > 0:  # TH 钻
            dh = math.hypot(px-x, py-y) - VIADR/2 - pad[7]
            if dh < 0.25:
                print(f"  [hole-clr] via({x},{y}) vs {pad[8]} drill gap {dh:.3f}")
    return worst, witem

def check_in2_seg(a1, a2):
    worst, witem = 99, None
    for (n, ly, ax, ay, bx, by, hw) in trks:
        if n == NET or ly != I2:
            continue
        d = seg_seg(a1, a2, (ax, ay), (bx, by)) - hw - TW/2
        if d < worst:
            worst, witem = d, f"In2 trk {n}"
    for (n, vx, vy, vr) in vias:
        if n == NET:
            continue
        d = pt_seg(vx, vy, a1[0], a1[1], a2[0], a2[1]) - vr - TW/2
        if d < worst:
            worst, witem = d, f"via {n}@({vx:.2f},{vy:.2f})"
    for kx in range(0, 60):
        px = a1[0] + (a2[0]-a1[0])*kx/59.0
        py = a1[1] + (a2[1]-a1[1])*kx/59.0
        for pad in pads:
            if pad[0] == NET:
                continue
            if abs(pad[1]-px) < 3.0 and abs(pad[2]-py) < 3.0:
                d = pad_edge(px, py, pad) - TW/2
                if d < worst:
                    worst, witem = d, f"pad {pad[8]}"
    return worst, witem

print("=== 预检: 搜索最优 (via1, via2) 组合 ===")
def in2_seg_clear(a1, a2):
    return check_in2_seg(a1, a2)[0]

best = None
for c1 in CANDS1:
    w1, i1 = check_vialoc(*c1)
    if w1 < CLR:
        continue
    for c2 in CANDS2:
        w2, i2 = check_vialoc(*c2)
        if w2 < CLR:
            continue
        ws, is_ = check_in2_seg(c1, c2)
        if ws < CLR:
            continue
        score = min(w1, w2, ws)
        if best is None or score > best[0]:
            best = (score, c1, c2, min(w1, w2), ws)
if best is None:
    # 打印每个 via1 的最差障碍帮助诊断
    for c1 in CANDS1[:40:5]:
        w1, i1 = check_vialoc(*c1)
        print(f"  via1 {c1}: {w1:.3f} ({i1})")
    for c2 in CANDS2[:48:6]:
        w2, i2 = check_vialoc(*c2)
        print(f"  via2 {c2}: {w2:.3f} ({i2})")
    print("[ABORT] 无可行组合")
    sys.exit(1)

score, VIA1, VIA2, wmin, wseg = best
SEGS = [(VIA1, VIA2)]
print(f"选定 via1={VIA1} via2={VIA2} 组合最差={score:.3f}")
w1, i1 = check_vialoc(*VIA1)
w2, i2 = check_vialoc(*VIA2)
print(f"via1 最差 {w1:.3f} ({i1}); via2 最差 {w2:.3f} ({i2})")
for idx, (a1, a2) in enumerate(SEGS):
    ws, is_ = check_in2_seg(a1, a2)
    print(f"In2 seg{idx}: 最差 {ws:.3f} ({is_})")

# 落点核验: via1 在 A-横线上, via2 在 B-竖线上 (IO21 自身 In1)
def on_track(x, y):
    best = None
    for (n, ly, ax, ay, bx, by, hw) in trks:
        if n == NET and ly == I1:
            d = pt_seg(x, y, ax, ay, bx, by)
            if d <= VIAW/2:
                if best is None or d < best[0]:
                    best = (d, f"L{ly} ({ax:.2f},{ay:.2f})->({bx:.2f},{by:.2f})")
    return best
print(f"via1 落点: {on_track(*VIA1)}")
print(f"via2 落点: {on_track(*VIA2)}")
assert on_track(*VIA1) and on_track(*VIA2), "落点不在 IO21 In1 走线上!"

# === 幂等重放守卫 (模式同 route_pcb._via_exists): 桥已在板则 no-op 退出,
#     消除重跑 double-via 静默累积 —— 候选搜索对同网增量不敏感(同网不算障碍),
#     重跑必然复选同一 (VIA1,VIA2), 守卫必命中; exit 0 前不触碰板文件。 ===
def _via_exists(x, y, net, r=0.5):
    for tr in b.GetTracks():
        if tr.GetClass() == "PCB_VIA" and tr.GetNetname() == net:
            q = tr.GetPosition()
            if math.hypot(MM(q.x) - x, MM(q.y) - y) < r:
                return True
    return False

if _via_exists(*VIA1, NET) or _via_exists(*VIA2, NET):
    print(f"[SKIP] IO21 In2 桥已在板 (via@{VIA1}/{VIA2} 已存在) — 重放守卫生效, 不落盘")
    sys.exit(0)

# === 放置 ===
netcode = None
for t in b.GetTracks():
    if t.GetNetname() == NET:
        netcode = t.GetNetCode()
        break
assert netcode is not None

for (x, y) in (VIA1, VIA2):
    v = pcbnew.PCB_VIA(b)
    v.SetNetCode(netcode)
    v.SetPosition(VI(int(FM(x)), int(FM(y))))
    v.SetViaType(pcbnew.VIATYPE_THROUGH)
    v.SetWidth(int(FM(VIAW)))
    v.SetDrill(int(FM(VIADR)))
    b.Add(v)
    print(f"+via ({x},{y})")

for (a1, a2) in SEGS:
    t = pcbnew.PCB_TRACK(b)
    t.SetNetCode(netcode)
    t.SetLayer(I2)
    t.SetWidth(int(FM(TW)))
    t.SetStart(VI(int(FM(a1[0])), int(FM(a1[1]))))
    t.SetEnd(VI(int(FM(a2[0])), int(FM(a2[1]))))
    b.Add(t)
    print(f"+In2 {a1}->{a2}")

try:
    pcbnew.ZONE_FILLER(b).Fill(list(b.Zones()))
    print("zone refill OK")
except Exception as e:
    print("zone fill:", e)

b.BuildConnectivity()
print("unconnected now:", b.GetConnectivity().GetUnconnectedCount(True))
pcbnew.SaveBoard("flowio-p1.kicad_pcb", b)
print("已保存")
