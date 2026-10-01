# -*- coding: utf-8 -*-
"""boardgeom: 全障碍感知的过孔/走线落点工具 (KiCad 10 pcbnew).
教训编码: 阶段1.5手工过孔只查焊盘引发14条违规——本库必须查全障碍."""
import math, pcbnew

BF = "flowio-p1.kicad_pcb"
MM, FM, VI = pcbnew.ToMM, pcbnew.FromMM, pcbnew.VECTOR2I
KEEPOUT = (19.5, 36.5, 0.2, 6.4)          # 天线禁布区 x0,x1,y0,y1
EDGE = (1.2, 88.8, 1.2, 73.8)             # 板边净空
CLR, HOLE_CLR = 0.21, 0.26                # 铜间距(规则0.2+裕量) / 孔边距(0.25+裕量)

def load():
    b = pcbnew.LoadBoard(BF)
    pads, trks, vias = [], [], []
    for f in b.GetFootprints():
        for p in f.Pads():
            c = p.GetPosition()
            sz = p.GetSize()
            pads.append(dict(x=MM(c.x), y=MM(c.y), r=max(MM(sz.x), MM(sz.y)) / 2,
                             rc=math.hypot(MM(sz.x), MM(sz.y)) / 2,   # 外接圆(保守, 走线用)
                             w=MM(sz.x), h=MM(sz.y),
                             rot=math.radians(p.GetOrientation().AsDegrees()),
                             net=p.GetNetname(),
                             drill=(MM(p.GetDrillSizeX()) if p.GetAttribute() != pcbnew.PAD_ATTRIB_SMD else 0.0),
                             npth=p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH,
                             ref=f.GetReference() + "." + str(p.GetPadName())))
    for t in b.GetTracks():
        if t.Type() == pcbnew.PCB_VIA_T:
            c = t.GetPosition(); vias.append((MM(c.x), MM(c.y), t.GetNetname(), MM(t.GetWidth(pcbnew.F_Cu))))
        else:
            s, e = t.GetStart(), t.GetEnd()
            trks.append((t.GetNetname(), t.GetLayer(), MM(s.x), MM(s.y), MM(e.x), MM(e.y), MM(t.GetWidth())))
    return b, pads, trks, vias

def pad_pt_dist(x, y, p):
    """点到焊盘(旋转矩形)铜边缘距离的精确近似: 负值=侵入."""
    dx, dy = x - p["x"], y - p["y"]
    c, s = math.cos(p["rot"]), math.sin(p["rot"])
    lx, ly = c * dx + s * dy, -s * dx + c * dy        # 逆旋转到焊盘局部系
    qx, qy = abs(lx) - p["w"] / 2, abs(ly) - p["h"] / 2
    d = math.hypot(max(qx, 0), max(qy, 0))
    return d if qx > 0 or qy > 0 else max(qx, qy)      # 内部时返回负穿透深度

def netcode(b, name):
    return b.FindNet(name).GetNetCode()

def seg_dist(px, py, ax, ay, bx, by):
    abx, aby = bx - ax, by - ay
    L2 = abx * abx + aby * aby
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px - ax) * abx + (py - ay) * aby) / L2))
    return math.hypot(px - ax - t * abx, py - ay - t * aby)

def seg_seg_dist(p1, p2, p3, p4):
    def orient(a, b, c):
        v = (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])
        return 0 if abs(v) < 1e-9 else (1 if v > 0 else -1)
    def onseg(a, b, c):
        return min(a[0],b[0])-1e-9 <= c[0] <= max(a[0],b[0])+1e-9 and min(a[1],b[1])-1e-9 <= c[1] <= max(a[1],b[1])+1e-9
    if orient(p1,p2,p3) != orient(p1,p2,p4) and orient(p3,p4,p1) != orient(p3,p4,p2):
        return 0.0  # 相交
    return min(seg_dist(*p3, *p1, *p2), seg_dist(*p4, *p1, *p2),
               seg_dist(*p1, *p3, *p4), seg_dist(*p2, *p3, *p4))

def _obs_ok(x, y, net, od, drill, pads, vias):
    for p in pads:
        d = pad_pt_dist(x, y, p)                        # 点到矩形边缘(精确)
        if p["npth"] or p["net"] != net:                # 空网络焊盘(如 TCA NC 脚)同为障碍
            if d - od / 2 < CLR: return False
        if p["drill"] > 0 and p["net"] != net:
            if math.hypot(p["x"] - x, p["y"] - y) < (p["drill"] + drill) / 2 + HOLE_CLR: return False
        if p["npth"] and math.hypot(p["x"] - x, p["y"] - y) < (p["drill"] + drill) / 2 + HOLE_CLR: return False
    for vx, vy, vnet, vw in vias:
        d = math.hypot(vx - x, vy - y)
        if vnet != net and d - (vw + od) / 2 < CLR: return False
        # 孔距规则不分网 (含同网叠孔)
        if d < (0.3 + drill) / 2 + HOLE_CLR: return False
    return True

def _in_keepout(x, y):
    return KEEPOUT[0] <= x <= KEEPOUT[1] and KEEPOUT[2] <= y <= KEEPOUT[3]

def spot_ok(x, y, net, pads, trks, vias, od=0.8, drill=0.4):
    if not (EDGE[0] < x < EDGE[1] and EDGE[2] < y < EDGE[3]) or _in_keepout(x, y):
        return False
    if not _obs_ok(x, y, net, od, drill, pads, vias): return False
    for tn, _ly, ax, ay, bx, by, w in trks:
        if tn == net: continue
        if seg_dist(x, y, ax, ay, bx, by) - w / 2 - od / 2 < CLR: return False
    return True

def track_ok(p1, p2, net, w, pads, trks, vias, layer=None):
    """走线铜冲突检查; layer=None 时查所有层(过孔语义), 否则只查同层走线.
    过孔为全层圆形障碍(铜+孔规则); 焊盘用沿段采样精确矩形距离."""
    L = math.hypot(p2[0]-p1[0], p2[1]-p1[1])
    n = max(2, min(400, int(L / 0.1)))
    samples = [(p1[0] + (p2[0]-p1[0]) * k / (n-1), p1[1] + (p2[1]-p1[1]) * k / (n-1)) for k in range(n)]
    for p in pads:
        if p["net"] == net and not p["npth"]: continue
        if min(pad_pt_dist(sx, sy, p) for sx, sy in samples) - w / 2 < CLR: return False
    for vx, vy, vnet, vw in vias:
        d = min(math.hypot(sx - vx, sy - vy) for sx, sy in samples)
        if vnet != net and d - vw / 2 - w / 2 < CLR: return False
        # 同网: 铜重叠合法, 走线无孔故无孔距问题
    for tn, tly, ax, ay, bx, by, tw in trks:
        if tn == net: continue
        if layer is not None and tly != layer: continue
        if seg_seg_dist(p1, p2, (ax, ay), (bx, by)) - tw / 2 - w / 2 < CLR: return False
    return True

def plan_route(anchor, spot, net, w, pads, trks, vias, layer=None):
    """直线或 L 形两腿 (先x后y / 先y后x) 任一可通行; 返回路径点列或 None."""
    if track_ok(anchor, spot, net, w, pads, trks, vias, layer): return [anchor, spot]
    c1 = (spot[0], anchor[1])
    if track_ok(anchor, c1, net, w, pads, trks, vias, layer) and track_ok(c1, spot, net, w, pads, trks, vias, layer):
        return [anchor, c1, spot]
    c2 = (anchor[0], spot[1])
    if track_ok(anchor, c2, net, w, pads, trks, vias, layer) and track_ok(c2, spot, net, w, pads, trks, vias, layer):
        return [anchor, c2, spot]
    return None

def find_spot(cx, cy, net, pads, trks, vias, anchor=None, rmax=3.5, od=0.8, drill=0.4, w=0.3, route_layer=None):
    """从 (cx,cy) 环形搜索: 过孔落点(全层) + (anchor→落点) 同层走线双净空."""
    r = 0.3
    while r <= rmax:
        n = max(8, int(2 * math.pi * r / 0.3))
        for i in range(n):
            a = 2 * math.pi * i / n
            x, y = cx + r * math.cos(a), cy + r * math.sin(a)
            if not spot_ok(x, y, net, pads, trks, vias, od, drill): continue
            sp = (round(x, 3), round(y, 3))
            if anchor and plan_route(anchor, sp, net, w, pads, trks, vias, route_layer) is None: continue
            return sp
        r += 0.2
    return None

def add_route(b, path, layer, net, w=0.3):
    """布 plan_route 返回的路径. 返回段数."""
    for p1, p2 in zip(path, path[1:]):
        add_seg(b, p1, p2, layer, net, w)
    return len(path) - 1

def add_via(b, x, y, net, od=0.8, drill=0.4):
    v = pcbnew.PCB_VIA(b); v.SetNetCode(netcode(b, net)); v.SetPosition(VI(int(FM(x)), int(FM(y))))
    v.SetWidth(int(FM(od))); v.SetDrill(int(FM(drill))); v.SetViaType(pcbnew.VIATYPE_THROUGH)
    b.Add(v); return v

def add_seg(b, p1, p2, layer, net, w=0.3):
    t = pcbnew.PCB_TRACK(b); t.SetNetCode(netcode(b, net)); t.SetLayer(layer)
    t.SetStart(VI(int(FM(p1[0])), int(FM(p1[1])))); t.SetEnd(VI(int(FM(p2[0])), int(FM(p2[1]))))
    t.SetWidth(int(FM(w))); b.Add(t); return t

def refill_save(b):
    pcbnew.ZONE_FILLER(b).Fill(list(b.Zones())); pcbnew.SaveBoard(BF, b)
