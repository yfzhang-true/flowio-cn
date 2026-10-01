# -*- coding: utf-8 -*-
"""FLOWIO-CN P1 布线器
阶段1: 平面区 + GND 缝合过孔 + 电源焊盘过孔(带净空搜索)
阶段2: 8 路驱动通道直布
阶段3: 显式曼哈顿信号
用法: kiCad-python route_pcb.py [stage]
"""
import os, sys, math
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
BF = os.path.join(HERE, "..", "flowio-p1.kicad_pcb")
STAGE = int(sys.argv[1]) if len(sys.argv) > 1 else 3
MM = pcbnew.FromMM
board = pcbnew.LoadBoard(BF)

FP = {f.GetReference(): f for f in board.GetFootprints()}

def pad_pos(ref, pad_name):
    p = FP[ref].FindPadByName(str(pad_name))
    pos = p.GetPosition()
    return pcbnew.ToMM(pos.x), pcbnew.ToMM(pos.y), p

def netcode(name):
    ni = board.FindNet(name)
    return ni.GetNetCode() if ni else None

TRACK_PRIO = []
def track(net, pts, width=0.25, layer=pcbnew.F_Cu, prio=1):
    TRACK_PRIO.append(prio)
    t = pcbnew.PCB_TRACK(board)
    t.SetNetCode(netcode(net))
    t.SetWidth(int(MM(width)))
    t.SetLayer(layer)
    for a, b in zip(pts[:-1], pts[1:]):
        seg = pcbnew.PCB_TRACK(board)
        seg.SetNetCode(netcode(net))
        seg.SetWidth(int(MM(width)))
        seg.SetLayer(layer)
        seg.SetStart(pcbnew.VECTOR2I(int(MM(a[0])), int(MM(a[1]))))
        seg.SetEnd(pcbnew.VECTOR2I(int(MM(b[0])), int(MM(b[1]))))
        board.Add(seg)
        TRACK_PRIO.append(prio)
    TRACK_PRIO.pop(0)  # 去掉函数开头多加的一个
    return t

def via(net, x, y):
    v = pcbnew.PCB_VIA(board)
    v.SetNetCode(netcode(net))
    v.SetPosition(pcbnew.VECTOR2I(int(MM(x)), int(MM(y))))
    v.SetViaType(pcbnew.VIATYPE_THROUGH)
    v.SetWidth(int(MM(0.7)))
    v.SetDrill(int(MM(0.35)))
    board.Add(v)
    return v

ALL_PADS = []
def _collect_pads():
    ALL_PADS.clear()
    for r2, fp2 in FP.items():
        for p2 in fp2.Pads():
            ALL_PADS.append((pcbnew.ToMM(p2.GetPosition().x),
                             pcbnew.ToMM(p2.GetPosition().y),
                             p2.GetNetname(), p2.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH))
_collect_pads()

def seg_clear(x1, y1, x2, y2, net):
    """电源引线段不得扫过异网焊盘(采样 0.4mm)"""
    L = math.hypot(x2 - x1, y2 - y1)
    n = max(2, int(L / 0.4))
    for k in range(n + 1):
        f = k / n
        if 0.05 < f < 0.95:          # 起点在源焊盘上, 跳过
            sx, sy = x1 + (x2 - x1) * f, y1 + (y2 - y1) * f
            for qx, qy, qnet, _np in ALL_PADS:
                d = math.hypot(qx - sx, qy - sy)
                if qnet != net and d < 1.3:
                    return False
    return True

def spot_free(vx, vy, net, pad_min=1.7, same_min=0.9, npth_min=2.0):
    if not (1.2 < vx < 88.8 and 1.2 < vy < 73.8):
        return False
    for qx, qy, qnet, is_npth in ALL_PADS:
        d = math.hypot(qx - vx, qy - vy)
        if is_npth and d < npth_min:
            return False
        if qnet == net:
            if d < same_min:
                return False
        elif d < pad_min:
            return False
    return True

def zone(name, layer, pts, min_thickness=0.3):
    z = pcbnew.ZONE(board)
    z.SetLayer(layer)
    z.SetNetCode(netcode(name))
    z.SetMinThickness(int(MM(min_thickness)))
    z.SetZoneName(name)
    ol = z.Outline()
    ol.NewOutline()
    for cx, cy in pts:
        ol.Append(int(MM(cx)), int(MM(cy)))
    board.Add(z)
    return z

# ================= 阶段 1: 平面 + 过孔 =================
if STAGE >= 1:
    # 删除旧 zones (gen_pcb 外部脚本加的, 若有)
    for z in list(board.Zones()):
        board.Remove(z)
    # 层叠: F=信号+GND填充 / In1=GND面 / In2=+5V L形区 / B=+3V3面
    zone("GND", pcbnew.In1_Cu, [(0.5, 0.5), (89.5, 0.5), (89.5, 74.5), (0.5, 74.5)])
    # In2: 5V L形区(同网多块) + 3V3 补充区(避开5V区)
    zone("+5V", pcbnew.In2_Cu, [(0.5, 21), (19, 21), (19, 55), (0.5, 55)])
    zone("+5V", pcbnew.In2_Cu, [(19, 28), (36, 28), (36, 55), (19, 55)])
    zone("+5V", pcbnew.In2_Cu, [(0.5, 53), (89.5, 53), (89.5, 74.5), (0.5, 74.5)])
    zone("+3V3", pcbnew.In2_Cu, [(0.5, 0.5), (89.5, 0.5), (89.5, 20.8), (0.5, 20.8)])
    zone("+3V3", pcbnew.In2_Cu, [(19.2, 20.8), (89.5, 20.8), (89.5, 52.8), (36.2, 52.8),
                                 (36.2, 27.8), (19.2, 27.8)])
    zone("GND", pcbnew.F_Cu, [(0.5, 0.5), (89.5, 0.5), (89.5, 74.5), (0.5, 74.5)])
    zone("GND", pcbnew.B_Cu, [(0.5, 0.5), (89.5, 0.5), (89.5, 74.5), (0.5, 74.5)])

    def in_5v_zone(vx, vy):
        return (vy >= 53) or (vx <= 19 and vy >= 21) or (19 <= vx <= 36 and vy >= 28)

    # GND 缝合过孔网格 (避开天线净空 x20.5-35.5/y<6.4)
    n_st = 0
    for gx in range(4, 89, 12):
        for gy in range(4, 74, 12):
            if 20 <= gx <= 36 and gy <= 7:
                continue
            if spot_free(gx, gy, "GND"):
                via("GND", gx, gy)
                n_st += 1
    print(f"[stage1] GND 缝合过孔: {n_st}")

    # 电源焊盘过孔: 对每个 +3V3/+5V SMD 焊盘, 在附近净空点打过孔+短粗线
    PWR = {"+3V3": 1.0, "+5V": 1.0}
    placed = 0
    for ref, fp in FP.items():
        for pad in fp.Pads():
            nname = pad.GetNetname()
            if nname not in PWR or pad.GetAttribute() != pcbnew.PAD_ATTRIB_SMD:
                continue
            px, py = pcbnew.ToMM(pad.GetPosition().x), pcbnew.ToMM(pad.GetPosition().y)
            # In2 分割线附近归就近平面; 3V3 在左半/5V 在右半, 平面本身会处理连通
            w = PWR[nname]
            best = None
            for ang in range(0, 360, 30):
                for dist in (1.5, 2.1, 2.7, 3.3, 4.2, 5.5):
                    vx = px + dist * math.cos(math.radians(ang))
                    vy = py + dist * math.sin(math.radians(ang))
                    in_zone = True if nname == "+3V3" else in_5v_zone(vx, vy)
                    if in_zone and spot_free(vx, vy, nname) and                        seg_clear(px, py, vx, vy, nname):
                        best = (vx, vy); break
                if best:
                    break
            if best:
                track(nname, [(px, py), best], width=0.8)
                via(nname, *best)
                placed += 1
    print(f"[stage1] 电源焊盘过孔: {placed}")

# ---- 阶段1.5: 电源引出线事后验证, 触碰异网者删除 ----
import math as _m2
def _pd_seg(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    L2 = dx * dx + dy * dy
    tp = 0 if L2 == 0 else max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / L2))
    return _m2.hypot(px - (x1 + tp * dx), py - (y1 + tp * dy))

_pwr_items = []
for tr in board.GetTracks():
    if tr.GetNetname() in ("+3V3", "+5V"):
        if tr.GetClass() == "PCB_TRACK":
            s, e = tr.GetStart(), tr.GetEnd()
            _pwr_items.append((tr, "T", pcbnew.ToMM(s.x), pcbnew.ToMM(s.y),
                               pcbnew.ToMM(e.x), pcbnew.ToMM(e.y),
                               pcbnew.ToMM(tr.GetWidth()) / 2))
        elif tr.GetClass() == "PCB_VIA":
            q = tr.GetPosition()
            _pwr_items.append((tr, "V", pcbnew.ToMM(q.x), pcbnew.ToMM(q.y), 0, 0, 0.35))
_bad = 0
for tr, kind, x1, y1, x2, y2, r in _pwr_items:
    hit = False
    for ref2, fp2 in FP.items():
        for p2 in fp2.Pads():
            if p2.GetNetname() in ("+3V3", "+5V", ""):
                continue
            q = p2.GetPosition()
            qx, qy = pcbnew.ToMM(q.x), pcbnew.ToMM(q.y)
            w2, h2 = pcbnew.ToMM(p2.GetSize().x), pcbnew.ToMM(p2.GetSize().y)
            if w2 <= 0: w2 = 0.9
            rr = max(w2, h2) / 2
            if kind == "V":
                if _m2.hypot(qx - x1, qy - y1) < rr + r + 0.2:
                    hit = True; break
            else:
                if _pd_seg(qx, qy, x1, y1, x2, y2) < rr + r + 0.2:
                    hit = True; break
        if hit: break
    if hit:
        board.Remove(tr)
        _bad += 1
print(f"[stage1.5] 删除触碰异网的电源引线: {_bad}")
# 同网成对删除: 孤立的过孔/引线也清掉
_orphan = 0
for tr in list(board.GetTracks()):
    if tr.GetNetname() in ("+3V3", "+5V") and tr.GetClass() == "PCB_VIA":
        q = tr.GetPosition()
        vx, vy = pcbnew.ToMM(q.x), pcbnew.ToMM(q.y)
        has_pad = any(
            _m2.hypot(pcbnew.ToMM(p.GetPosition().x) - vx,
                      pcbnew.ToMM(p.GetPosition().y) - vy) < 1.1
            for f3 in FP.values() for p in f3.Pads()
            if p.GetNetname() == tr.GetNetname())
        has_trk = any(
            tr2 is not tr and tr2.GetNetname() == tr.GetNetname()
            and tr2.GetClass() == "PCB_TRACK"
            and _pd_seg(vx, vy, pcbnew.ToMM(tr2.GetStart().x), pcbnew.ToMM(tr2.GetStart().y),
                        pcbnew.ToMM(tr2.GetEnd().x), pcbnew.ToMM(tr2.GetEnd().y)) < 0.5
            for tr2 in board.GetTracks())
        if not has_pad and not has_trk:
            board.Remove(tr)
            _orphan += 1
print(f"[stage1.5] 清除孤立电源过孔: {_orphan}")

# ================= 阶段 2+3: 通用自动布线 =================
if STAGE >= 2:
    import math as _m

    def seg_pad_clear(x1, y1, x2, y2, net, clearance=0.88):
        """线段到异网焊盘中心距离检查"""
        dx, dy = x2 - x1, y2 - y1
        L2 = dx * dx + dy * dy
        for qx, qy, qnet, _np in ALL_PADS:
            if qnet == net or qnet == "":
                continue
            t_par = 0 if L2 == 0 else max(0, min(1, ((qx - x1) * dx + (qy - y1) * dy) / L2))
            px_, py_ = x1 + t_par * dx, y1 + t_par * dy
            if _m.hypot(qx - px_, qy - py_) < clearance:
                return False
        return True

    def pad_exit(ref, padname):
        """焊盘朝外的逃逸方向(单位向量)"""
        pad = FP[ref].FindPadByName(str(padname))
        ang = pad.GetOrientation()
        a = pcbnew.ToDegrees(ang.AsRadians()) if hasattr(ang, "AsRadians") else float(ang) / 10
        a = a % 360
        return (_m.cos(_m.radians(a)), _m.sin(_m.radians(a)))

    def _existing_tracks():
        out = []
        for tr in board.GetTracks():
            if tr.GetClass() == "PCB_TRACK" and tr.GetLayer() == pcbnew.F_Cu:
                s, e = tr.GetStart(), tr.GetEnd()
                out.append((pcbnew.ToMM(s.x), pcbnew.ToMM(s.y),
                            pcbnew.ToMM(e.x), pcbnew.ToMM(e.y), tr.GetNetname()))
        return out

    def _pt_seg_dist(px, py, x1, y1, x2, y2):
        dx, dy = x2 - x1, y2 - y1
        L2 = dx * dx + dy * dy
        tp = 0 if L2 == 0 else max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / L2))
        return _m.hypot(px - (x1 + tp * dx), py - (y1 + tp * dy))

    def seg_track_clear(x1, y1, x2, y2, net, clearance=0.5):
        for tx1, ty1, tx2, ty2, tnet in _existing_tracks():
            if tnet == net or not tnet:
                continue
            # 粗包围盒预筛
            if max(x1, x2) + clearance < min(tx1, tx2) or min(x1, x2) - clearance > max(tx1, tx2):
                continue
            if max(y1, y2) + clearance < min(ty1, ty2) or min(y1, y2) - clearance > max(ty1, ty2):
                continue
            for px_, py_ in ((x1, y1), (x2, y2), ((x1+x2)/2, (y1+y2)/2)):
                if _pt_seg_dist(px_, py_, tx1, ty1, tx2, ty2) < clearance:
                    return False
            for px_, py_ in ((tx1, ty1), (tx2, ty2)):
                if _pt_seg_dist(px_, py_, x1, y1, x2, y2) < clearance:
                    return False
        return True

    def seg_ok(pts, net, clearance=0.88):
        for s, e in zip(pts[:-1], pts[1:]):
            if not seg_pad_clear(s[0], s[1], e[0], e[1], net, clearance):
                return False
            if not seg_track_clear(s[0], s[1], e[0], e[1], net):
                return False
        return True

    def route_L(a, b, net, width=0.25):
        """多候选: 直接 L / 轴向逃逸 L / 平行通道绕行"""
        (ax, ay, aref, apad), (bx, by, bref, bpad) = a, b
        cands = []
        # 1) 直接 L + 偏移拐角
        for off in (0, 1.27, -1.27, 2.54, -2.54):
            cands.append([(ax, ay), (bx, ay + off if off else ay), (bx, by)])
            cands.append([(ax, ay), (ax + off if off else ax, by), (bx, by)])
        # 2) 引脚轴向逃逸后 L
        try:
            ex, ey = pad_exit(aref, apad)
            for d in (2.0, 2.6):
                exx, eyy = ax + ex * d, ay + ey * d
                cands.append([(ax, ay), (exx, eyy), (bx, eyy), (bx, by)])
                cands.append([(ax, ay), (exx, eyy), (exx, by), (bx, by)])
        except Exception:
            pass
        try:
            fx, fy = pad_exit(bref, bpad)
            for d in (2.0, 2.6):
                fxx, fyy = bx + fx * d, by + fy * d
                cands.append([(ax, ay), (fxx, ay), (fxx, fyy), (bx, by)])
        except Exception:
            pass
        # 3) 平行通道绕行(垂直于 a-b 轴)
        dx, dy = bx - ax, by - ay
        L = _m.hypot(dx, dy)
        if L > 0.1:
            nx_, ny_ = -dy / L, dx / L
            for off in (1.9, -1.9, 3.2, -3.2):
                mx, my = (ax + bx) / 2 + nx_ * off, (ay + by) / 2 + ny_ * off
                cands.append([(ax, ay), (mx, ay), (mx, by), (bx, by)])
                cands.append([(ax, ay), (ax, my), (bx, my), (bx, by)])
        for pts in cands:
            # 去除零长段
            pp = [pts[0]]
            for q in pts[1:]:
                if _m.hypot(q[0] - pp[-1][0], q[1] - pp[-1][1]) > 0.05:
                    pp.append(q)
            if len(pp) < 2:
                continue
            if seg_ok(pp, net):
                track(net, pp, width=width)
                return pp
        return None

    # 收集每个网络的 SMD 焊盘(排除电源/GND——它们由平面负责)
    SKIP_NETS = {"GND", "+3V3", "+5V"}
    netpads = {}
    for ref, fp in FP.items():
        for pad in fp.Pads():
            nn = pad.GetNetname()
            if not nn or nn in SKIP_NETS:
                continue
            pos = pad.GetPosition()
            netpads.setdefault(nn, []).append(
                (pcbnew.ToMM(pos.x), pcbnew.ToMM(pos.y), ref, pad.GetPadName()))

    done, failed = [], []
    for net, pads in sorted(netpads.items()):
        # 最近邻链式连接
        remaining = pads[:]
        cur = remaining.pop(0)
        ok_all = True
        while remaining:
            remaining.sort(key=lambda p: _m.hypot(p[0] - cur[0], p[1] - cur[1]))
            nxt = remaining.pop(0)
            r = route_L(cur, nxt, net)
            if r is None:
                ok_all = False
                failed.append((net, cur, nxt))
            else:
                pass
            cur = nxt
        if ok_all:
            done.append(net)
    # ---- 显式干线: 长距离网络(走廊布线) ----
    MANUAL = {
        # GPIO 总线: U1 -> 各通道栅极电阻 (走廊 + y52.4 分发道)
        "IO4":  [(19.2, 11.3), (17.5, 11.3), (17.5, 16.5), (13.5, 16.5), (13.5, 52.5), (4.1, 52.5), (4.1, 54.4)],
        "IO5":  [(19.2, 13.8), (17.8, 13.8), (17.8, 16.8), (16.4, 16.8), (16.4, 51.8), (15.1, 51.8), (15.1, 54.4)],
        "IO6":  [(19.2, 16.3), (19.2, 28.5), (26.35, 28.5), (26.35, 54.4), (26.1, 54.4)],
        "IO7":  [(19.2, 18.8), (19.2, 27.8), (33.2, 27.8), (33.2, 53.8), (37.1, 53.8), (37.1, 54.4)],
        "IO10": [(24.8, 25.2), (24.8, 28.0), (45.2, 28.0), (45.2, 53.9), (48.1, 53.9), (48.1, 54.4)],
        "IO11": [(26.1, 25.2), (26.1, 29.0), (50.0, 29.0), (50.0, 53.8), (59.1, 53.8), (59.1, 54.4)],
        "IO12": [(27.4, 25.2), (27.4, 29.6), (52.0, 29.6), (52.0, 52.4), (70.1, 52.4), (70.1, 54.4)],
        "IO21": [(31.2, 25.2), (31.2, 29.0), (53.4, 29.0), (53.4, 51.9), (81.1, 51.9), (81.1, 54.4)],
        # EN / BOOT 顶边横道 y=8
        "EN":   [(72.04, 18.42), (72.04, 8.0), (17.84, 8.0), (17.84, 10.15), (6.46, 10.15), (6.46, 8.5)],
        "BOOT": [(36.8, 24.0), (40.5, 20.5), (40.5, 9.5), (10.96, 9.5), (10.96, 12.5)],
        # I2C: U1 -> 上拉 -> U2 (F 直连)
        "I2C_SDA": [(19.2, 21.4), (50.8, 21.4) if False else (19.2, 21.4)],
    }
    for net, pts in MANUAL.items():
        if net in ("I2C_SDA",):
            continue
        track(net, pts, width=0.25, prio=0)
    done2 = [n for n in MANUAL if n != "I2C_SDA"]
    print(f"[manual] 干线 {len(done2)} 网")

    print(f"[route] 成功 {len(done)} 网, 失败 {len(failed)}:")
    for net, a, b in failed[:20]:
        print(f"   {net}: ({a[0]:.1f},{a[1]:.1f}){a[2]}.{a[3]} -> ({b[0]:.1f},{b[1]:.1f}){b[2]}.{b[3]}")

# ---- 贪心冲突消解: 同层异网络走线相交, 删低优先者 ----
def _seg_int(p1, p2, p3, p4):
    d1 = (p4[0]-p3[0])*(p1[1]-p3[1]) - (p4[1]-p3[1])*(p1[0]-p3[0])
    d2 = (p4[0]-p3[0])*(p2[1]-p3[1]) - (p4[1]-p3[1])*(p2[0]-p3[0])
    d3 = (p2[0]-p1[0])*(p3[1]-p1[1]) - (p2[1]-p1[1])*(p3[0]-p1[0])
    d4 = (p2[0]-p1[0])*(p4[1]-p1[1]) - (p2[1]-p1[1])*(p4[0]-p1[0])
    return d1*d2 < 0 and d3*d4 < 0

segs = []
for tr in board.GetTracks():
    if tr.GetClass() == "PCB_TRACK" and tr.GetLayer() == pcbnew.F_Cu:
        s, e = tr.GetStart(), tr.GetEnd()
        segs.append((pcbnew.ToMM(s.x), pcbnew.ToMM(s.y), pcbnew.ToMM(e.x), pcbnew.ToMM(e.y),
                     tr.GetNetname(), tr))
print(f"[conflict] F.Cu 走线段: {len(segs)}")
removed = set()
for i in range(len(segs)):
    if i in removed: continue
    a = segs[i]
    for j in range(i+1, len(segs)):
        if j in removed: continue
        b = segs[j]
        if a[4] == b[4] or not a[4] or not b[4]:
            continue
        if _seg_int(a[:2], a[2:4], b[:2], b[2:4]):
            # 删 j (后布的)
            board.Remove(b[5])
            removed.add(j)
print(f"[conflict] 删除冲突段: {len(removed)}")

# 填充所有平面
try:
    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(list(board.Zones()))
except Exception as e:
    print("zone fill:", e)
pcbnew.SaveBoard(BF, board)
print(f"[route] stage {STAGE} 完成")
