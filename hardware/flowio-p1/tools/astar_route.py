# -*- coding: utf-8 -*-
"""FLOWIO-CN P1 A* 网格路由器
- 网格 0.635mm, F.Cu 单层(信号), 8 方向
- 障碍: 板边/天线禁区/异网焊盘(0.62 膨胀)/异网走线(0.5 膨胀)
- 逐网布线(手动干线已含入障碍), 失败网络列出
用法: kiCad-python astar_route.py
"""
import os, sys, math, heapq
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
BF = os.path.join(HERE, "..", "flowio-p1.kicad_pcb")
MM = pcbnew.FromMM
PITCH = 0.635
X0, Y0, X1, Y1 = 0.9, 0.9, 89.1, 74.1
NX = int((X1 - X0) / PITCH) + 1
NY = int((Y1 - Y0) / PITCH) + 1

board = pcbnew.LoadBoard(BF)
FP = {f.GetReference(): f for f in board.GetFootprints()}

# ---- 障碍栅格 ----
# cell: (padnets frozenset, tracknets frozenset, hard bool)
padnets = [set() for _ in range(NX * NY)]
hard = [False] * (NX * NY)

def idx(gx, gy):
    return gy * NX + gx

def stamp_circle(cx, cy, r, dest, net):
    gx0 = max(0, int((cx - r - X0) / PITCH))
    gx1 = min(NX - 1, int((cx + r - X0) / PITCH) + 1)
    gy0 = max(0, int((cy - r - Y0) / PITCH))
    gy1 = min(NY - 1, int((cy + r - Y0) / PITCH) + 1)
    for gx in range(gx0, gx1 + 1):
        for gy in range(gy0, gy1 + 1):
            px, py = X0 + gx * PITCH, Y0 + gy * PITCH
            if math.hypot(px - cx, py - cy) <= r:
                dest[idx(gx, gy)].add(net)

# 板边/禁区 hard
for gx in range(NX):
    for gy in range(NY):
        px, py = X0 + gx * PITCH, Y0 + gy * PITCH
        if px < 1.0 or px > 89.0 or py < 1.0 or py > 74.0:
            hard[idx(gx, gy)] = True
        if 20.4 <= px <= 35.6 and py <= 6.5:      # 天线净空
            hard[idx(gx, gy)] = True

# 焊盘障碍: 按实际焊盘尺寸膨胀 (max(宽,高)/2 + 0.35)
for ref, fp in FP.items():
    for pad in fp.Pads():
        pos = pad.GetPosition()
        cx, cy = pcbnew.ToMM(pos.x), pcbnew.ToMM(pos.y)
        w, h = pcbnew.ToMM(pad.GetSize().x), pcbnew.ToMM(pad.GetSize().y)
        if w <= 0 or h <= 0:
            w = h = 0.9
        r = max(w, h) / 2 + 0.35
        if pad.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
            r = max(w, h) / 2 + 1.0
        stamp_circle(cx, cy, r, padnets, pad.GetNetname() or "?PAD")

tracknets = [set() for _ in range(NX * NY)]     # F 层走线
padnetsB = [set() for _ in range(NX * NY)]      # B 层: 通孔焊盘
tracknetsB = [set() for _ in range(NX * NY)]
viaAt = [set() for _ in range(NX * NY)]
ZONE5V = [(0.5, 21, 19, 55), (19, 28, 36, 55), (0.5, 53, 89.5, 74.5)]
def in_5v(x, y):
    return any(a <= x <= c and b <= y <= d for a, b, c, d in ZONE5V)

def stamp_track(tr, coll=None, r=None):
    s, e = tr.GetStart(), tr.GetEnd()
    x1, y1 = pcbnew.ToMM(s.x), pcbnew.ToMM(s.y)
    x2, y2 = pcbnew.ToMM(e.x), pcbnew.ToMM(e.y)
    nn = tr.GetNetname() or "?TRK"
    rr = r if r is not None else pcbnew.ToMM(tr.GetWidth()) / 2 + 0.42
    L = math.hypot(x2 - x1, y2 - y1)
    n = max(1, int(L / (PITCH / 2)))
    for k in range(n + 1):
        stamp_circle(x1 + (x2 - x1) * k / n, y1 + (y2 - y1) * k / n, rr,
                     coll if coll is not None else tracknets, nn)

for ref, fp in FP.items():
    for pad in fp.Pads():
        if pad.GetAttribute() == pcbnew.PAD_ATTRIB_PTH:
            pos = pad.GetPosition()
            w2, h2 = pcbnew.ToMM(pad.GetSize().x), pcbnew.ToMM(pad.GetSize().y)
            if w2 <= 0 or h2 <= 0:
                w2 = h2 = 0.9
            stamp_circle(pcbnew.ToMM(pos.x), pcbnew.ToMM(pos.y),
                         max(w2, h2) / 2 + 0.35, padnetsB,
                         pad.GetNetname() or "?PAD")
for tr in board.GetTracks():
    if tr.GetClass() == "PCB_TRACK" and tr.GetLayer() == pcbnew.F_Cu:
        stamp_track(tr)
    elif tr.GetClass() == "PCB_TRACK" and tr.GetLayer() == pcbnew.B_Cu:
        stamp_track(tr, tracknetsB)
    elif tr.GetClass() == "PCB_VIA":
        pos = tr.GetPosition()
        stamp_circle(pcbnew.ToMM(pos.x), pcbnew.ToMM(pos.y), 0.95, viaAt,
                     tr.GetNetname() or "?VIA")

def blocked(gx, gy, net, layer=0):
    i = idx(gx, gy)
    if hard[i]:
        return True
    pn, tn = (padnets[i], tracknets[i]) if layer == 0 else (padnetsB[i], tracknetsB[i])
    if pn and (len(pn) > 1 or net not in pn):
        return True
    if tn and (len(tn) > 1 or net not in tn):
        return True
    v = viaAt[i]
    if v and net not in v:
        return True
    if layer == 1 and net != "+5V":
        x, y = to_mm(gx, gy)
        if in_5v(x, y):
            return True
    return False

def to_grid(x, y):
    return round((x - X0) / PITCH), round((y - Y0) / PITCH)

def to_mm(gx, gy):
    return X0 + gx * PITCH, Y0 + gy * PITCH

DIRS = [(1,0,1.0),(-1,0,1.0),(0,1,1.0),(0,-1,1.0),
        (1,1,1.414),(1,-1,1.414),(-1,1,1.414),(-1,-1,1.414)]

VIA_COST = 4.0

def astar(start, goal, net, limit=250000):
    sx, sy = to_grid(*start); gx_, gy_ = to_grid(*goal)
    if (sx, sy) == (gx_, gy_):
        return [(start[0], start[1], 0), (goal[0], goal[1], 0)]
    # 起点/终点若被自身网络占据则允许
    openq = [(0.0, sx, sy, 0)]
    came = {(sx, sy, 0): None}
    gsc = {(sx, sy, 0): 0.0}
    pops = 0
    while openq:
        f, cx, cy, cl = heapq.heappop(openq)
        pops += 1
        if pops > limit:
            return None
        if (cx, cy) == (gx_, gy_):
            path = []
            cur = (cx, cy, cl)
            while cur:
                path.append(cur)
                cur = came[cur]
            out = [(X0 + q[0] * PITCH, Y0 + q[1] * PITCH, q[2]) for q in reversed(path)]
            out[0] = (start[0], start[1], out[0][2])
            out[-1] = (goal[0], goal[1], out[-1][2])
            return out
        for dx, dy, w in DIRS:
            nx_, ny_ = cx + dx, cy + dy
            if not (0 <= nx_ < NX and 0 <= ny_ < NY):
                continue
            if blocked(nx_, ny_, net, cl) and (nx_, ny_) != (gx_, gy_):
                continue
            if dx and dy and (blocked(cx + dx, cy, net, cl) or blocked(cx, cy + dy, net, cl)):
                continue
            nc = gsc[(cx, cy, cl)] + w
            st = (nx_, ny_, cl)
            if st not in gsc or nc < gsc[st]:
                gsc[st] = nc
                came[st] = (cx, cy, cl)
                heapq.heappush(openq, (nc + math.hypot(gx_ - nx_, gy_ - ny_), nx_, ny_, cl))
        nl = 1 - cl
        st = (cx, cy, nl)
        both_clear = ((not blocked(cx, cy, net, cl) or (cx, cy) == (gx_, gy_)) and
                      (not blocked(cx, cy, net, nl) or (cx, cy) == (gx_, gy_)))
        if both_clear and st not in gsc:
            gsc[st] = gsc[(cx, cy, cl)] + VIA_COST
            came[st] = (cx, cy, cl)
            heapq.heappush(openq, (gsc[st] + math.hypot(gx_ - cx, gy_ - cy), cx, cy, nl))
    return None

def netcode(name):
    ni = board.FindNet(name)
    return ni.GetNetCode() if ni else None

def _mk_track(a, b, net, layer, width=0.25):
    tr = pcbnew.PCB_TRACK(board)
    tr.SetNetCode(netcode(net))
    tr.SetWidth(int(MM(width)))
    tr.SetLayer(pcbnew.B_Cu if layer else pcbnew.F_Cu)
    tr.SetStart(pcbnew.VECTOR2I(int(MM(a[0])), int(MM(a[1]))))
    tr.SetEnd(pcbnew.VECTOR2I(int(MM(b[0])), int(MM(b[1]))))
    board.Add(tr)
    stamp_track(tr, tracknetsB if layer else tracknets)

def _mk_via(x, y, net):
    v = pcbnew.PCB_VIA(board)
    v.SetNetCode(netcode(net))
    v.SetPosition(pcbnew.VECTOR2I(int(MM(x)), int(MM(y))))
    v.SetViaType(pcbnew.VIATYPE_THROUGH)
    v.SetWidth(int(MM(0.7)))
    v.SetDrill(int(MM(0.35)))
    board.Add(v)
    stamp_circle(x, y, 0.95, viaAt, net)


def _pt_seg_d(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    L2 = dx * dx + dy * dy
    tp = 0 if L2 == 0 else max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / L2))
    return math.hypot(px - (x1 + tp * dx), py - (y1 + tp * dy))

GEO_PADS = []
GEO_VIAS = []
GEO_TRK = []
for _ref, _fp in FP.items():
    for _pd in _fp.Pads():
        _pos = _pd.GetPosition()
        _w, _h = pcbnew.ToMM(_pd.GetSize().x), pcbnew.ToMM(_pd.GetSize().y)
        if _w <= 0: _w = 0.9
        if _h <= 0: _h = 0.9
        GEO_PADS.append((pcbnew.ToMM(_pos.x), pcbnew.ToMM(_pos.y),
                         max(_w, _h) / 2, _pd.GetNetname() or "?"))
for _tr in board.GetTracks():
    if _tr.GetClass() == "PCB_VIA":
        _pos = _tr.GetPosition()
        GEO_VIAS.append((pcbnew.ToMM(_pos.x), pcbnew.ToMM(_pos.y), 0.35,
                         _tr.GetNetname() or "?"))
    elif _tr.GetClass() == "PCB_TRACK":
        _s, _e = _tr.GetStart(), _tr.GetEnd()
        GEO_TRK.append((pcbnew.ToMM(_s.x), pcbnew.ToMM(_s.y),
                        pcbnew.ToMM(_e.x), pcbnew.ToMM(_e.y),
                        pcbnew.ToMM(_tr.GetWidth()) / 2,
                        _tr.GetNetname() or "?", _tr.GetLayer()))

def anchor_clear(x1, y1, x2, y2, net):
    for px, py, r, n2 in GEO_PADS + GEO_VIAS:
        if n2 == net:
            continue
        if _pt_seg_d(px, py, x1, y1, x2, y2) < r + 0.35:
            return False
    for tx1, ty1, tx2, ty2, r2, n2, ly in GEO_TRK:
        if n2 == net:
            continue
        if _pt_seg_d(tx1, ty1, x1, y1, x2, y2) < r2 + 0.35 or            _pt_seg_d(tx2, ty2, x1, y1, x2, y2) < r2 + 0.35 or            _pt_seg_d(x1, y1, tx1, ty1, tx2, ty2) < r2 + 0.35 or            _pt_seg_d(x2, y2, tx1, ty1, tx2, ty2) < r2 + 0.35:
            return False
    return True

def emit(path, net, width=0.25):
    # 锚定段净空验证: 失败则从相邻格重锚
    for endi in (0, -1):
        anchor = path[endi]
        node = path[1] if endi == 0 else path[-2]
        if not anchor_clear(anchor[0], anchor[1], node[0], node[1], net):
            gx_, gy_ = to_grid(anchor[0], anchor[1])
            best = None
            for dx in (-2, -1, 0, 1, 2):
                for dy in (-2, -1, 0, 1, 2):
                    if dx == 0 and dy == 0:
                        continue
                    cx, cy = X0 + (gx_ + dx) * PITCH, Y0 + (gy_ + dy) * PITCH
                    if not (1 < cx < 89 and 1 < cy < 74):
                        continue
                    if anchor_clear(anchor[0], anchor[1], cx, cy, net):
                        d = math.hypot(cx - node[0], cy - node[1])
                        if best is None or d < best[0]:
                            best = (d, cx, cy)
            if best:
                if endi == 0:
                    path = [(best[1], best[2], node[2])] + path[1:]
                else:
                    path = path[:-1] + [(best[1], best[2], node[2])]
    pts = [path[0]]
    for k in range(1, len(path) - 1):
        ax, ay, al = pts[-1]; bx, by, bl = path[k]; cx, cy, cl2 = path[k+1]
        if al != bl or bl != cl2:
            pts.append(path[k]); continue
        cross = (bx - ax) * (cy - by) - (by - ay) * (cx - bx)
        if abs(cross) > 1e-6:
            pts.append(path[k])
    pts.append(path[-1])
    seg_a, prev_layer = None, None
    for p in pts:
        x, y, ly = p
        if prev_layer is None:
            seg_a, prev_layer = (x, y), ly
            continue
        if ly != prev_layer:
            _mk_track(seg_a, (x, y), net, prev_layer)
            _mk_via(x, y, net)
            seg_a, prev_layer = (x, y), ly
    if seg_a:
        _mk_track(seg_a, (pts[-1][0], pts[-1][1]), net, prev_layer)
    # 增量更新几何表
    for p, q in zip(pts[:-1], pts[1:]):
        if p[2] == q[2]:
            GEO_TRK.append((p[0], p[1], q[0], q[1], 0.125, net,
                            pcbnew.B_Cu if p[2] else pcbnew.F_Cu))

# ---- 网络列表: 未完成信号网 ----
SKIP = {"GND", "+3V3", "+5V"}
netpads = {}
for ref, fp in FP.items():
    for pad in fp.Pads():
        nn = pad.GetNetname()
        if not nn or nn in SKIP:
            continue
        pos = pad.GetPosition()
        netpads.setdefault(nn, []).append(
            (pcbnew.ToMM(pos.x), pcbnew.ToMM(pos.y)))

# 连通性检查(同网走线+焊盘的并查集) —— 简化: 用 DRC 前的粗检省略, 全部重布太慢;
# 只布线"尚未由现有走线连通"的网络: 以现有走线端点判断
def existing_conn(net):
    pts = []
    for tr in board.GetTracks():
        if tr.GetClass() == "PCB_TRACK" and tr.GetNetname() == net:
            s, e = tr.GetStart(), tr.GetEnd()
            pts.append((pcbnew.ToMM(s.x), pcbnew.ToMM(s.y)))
            pts.append((pcbnew.ToMM(e.x), pcbnew.ToMM(e.y)))
    return pts

done, failed = [], []
for net, pads in sorted(netpads.items(), key=lambda kv: len(kv[1])):
    # 起点=第一个焊盘, 逐点连通(航路点包含该网现有走线端点, 借助既有干线)
    targets = pads + existing_conn(net)
    cur = targets[0]
    rem = targets[1:]
    ok = True
    while rem:
        rem.sort(key=lambda p: math.hypot(p[0] - cur[0], p[1] - cur[1]))
        nxt = rem.pop(0)
        if math.hypot(nxt[0] - cur[0], nxt[1] - cur[1]) < 0.4:
            cur = nxt
            continue
        # 若两点已在既有走线附近(被干线覆盖)则跳过
        path = astar(cur, nxt, net)
        if path is None:
            ok = False
            failed.append((net, cur, nxt))
        else:
            emit(path, net)
        cur = nxt
    if ok:
        done.append(net)

print(f"[astar] 完成 {len(done)} 网, 失败 {len(failed)}")
for net, a, b in failed[:25]:
    print(f"   {net}: ({a[0]:.1f},{a[1]:.1f})->({b[0]:.1f},{b[1]:.1f})")

# 重填平面
try:
    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(list(board.Zones()))
except Exception as e:
    print("fill:", e)
pcbnew.SaveBoard(BF, board)
print("[astar] saved")
