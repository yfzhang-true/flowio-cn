# -*- coding: utf-8 -*-
"""FLOWIO-CN P1 布线器
阶段1: 平面区 + GND 缝合过孔 + 电源焊盘过孔(带净空搜索)
阶段1.5: 电源引出线事后验证(触碰异网即删)
阶段2+3: 通用网表驱动直布——收集全部非电源 SMD 焊盘按最近邻链式 L 形布线,
         无写死通道数 (P1.0 的 8 路 MANUAL 干线表已随 90x75 布局废弃,
         P1.1 12 路 J10-J23/J20-J23 驱动栅网由网表自动覆盖)
用法: kiCad-python route_pcb.py [stage]   (stage 累积, 3=全流程)
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
    p = FP[ref].FindPadByNumber(str(pad_name))
    pos = p.GetPosition()
    return pcbnew.ToMM(pos.x), pcbnew.ToMM(pos.y), p

# 网号预缓存: 载入后立即抓取, 之后不再调 FindNet (board.Remove 系列操作后
# SWIG FindNet 偶发返回坏对象 — T4 实测 zone 删除后 GetNetCode AttributeError)
_NET_CACHE = {}
for _ni in board.GetNetInfo().NetsByName().values():
    _NET_CACHE[_ni.GetNetname()] = _ni.GetNetCode()

def netcode(name):
    return _NET_CACHE.get(name)

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

def _via_exists(x, y, net, r=0.5):
    """幂等守卫: 同网点位已有过孔则跳过(累积 stage 重跑防翻倍)"""
    for tr in board.GetTracks():
        if tr.GetClass() == "PCB_VIA" and tr.GetNetname() == net:
            q = tr.GetPosition()
            if math.hypot(pcbnew.ToMM(q.x) - x, pcbnew.ToMM(q.y) - y) < r:
                return True
    return False

ALL_PADS = []
def _collect_pads():
    # 焊盘障碍模型两条真值 (T4 二轮 DRC 教训):
    # 1) r = 外接圆半径 (XH 卧贴 pad 1.5x3.5 → r=1.75) — 供圆模型消费者
    #    (seg_clear/spot_free); 2) hw/hh = 朝向半边长 — 供 stage2 矩形模型
    #    (seg_pad_clear)。⚠ 自定义形状 pad (J2.7 屏蔽腿 x4) 的 GetSize 撒谎
    #    (0.01x0.01), 必须回落 GetBoundingBox (真实 1.9x1.1, 否则走线穿屏蔽焊盘)。
    ALL_PADS.clear()
    for r2, fp2 in FP.items():
        try:
            _ang = fp2.GetOrientation()
            _deg = _ang.AsDegrees() if hasattr(_ang, "AsDegrees") else float(_ang) / 10
        except Exception:
            _deg = 0
        _odd = int(round(_deg)) % 180 == 90
        for p2 in fp2.Pads():
            w2, h2 = pcbnew.ToMM(p2.GetSize().x), pcbnew.ToMM(p2.GetSize().y)
            if max(w2, h2) < 0.2:  # 自定义形状: 尺寸退化, 用 bbox 真值
                bb = p2.GetBoundingBox()
                hw = pcbnew.ToMM(bb.GetWidth()) / 2
                hh = pcbnew.ToMM(bb.GetHeight()) / 2
            else:
                hw, hh = (h2 / 2, w2 / 2) if _odd else (w2 / 2, h2 / 2)
            ALL_PADS.append((pcbnew.ToMM(p2.GetPosition().x),
                             pcbnew.ToMM(p2.GetPosition().y),
                             p2.GetNetname(), p2.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH,
                             max(hw, hh), hw, hh))
_collect_pads()

def seg_clear(x1, y1, x2, y2, net, extra=0.75):
    """电源引线段不得扫过异网焊盘(采样 0.4mm)
    extra = 线半宽 + 铜间距 (0.8mm 线→0.75 / 1.0mm 线→0.85 / 1.5mm 线→1.1)"""
    L = math.hypot(x2 - x1, y2 - y1)
    n = max(2, int(L / 0.4))
    for k in range(n + 1):
        f = k / n
        if 0.05 < f < 0.95:          # 起点在源焊盘上, 跳过
            sx, sy = x1 + (x2 - x1) * f, y1 + (y2 - y1) * f
            for qx, qy, qnet, _np, qr, _hwx, _hhx in ALL_PADS:
                d = math.hypot(qx - sx, qy - sy)
                if qnet != net and d < qr + extra:
                    return False
    return True

def spot_free(vx, vy, net, pad_gap=0.55, same_min=0.9, npth_min=3.7):
    # pad_gap=0.55: 0.5 板级铜间距 + 0.05 余量; 过孔半径 0.35 计入
    # npth_min=3.7: M3 安装孔=铜柱心; 净空 = npth_min - 柱外径半径3.15 - 过孔半径0.35
    # = 0.2 真裕量 (3.5 时仅相切 0 裕量, T3 缺陷4 复审修正)
    # ⚠ 异网焊盘必须按真实半径 qr 判距: XH pad r=1.9 时固定 1.7 会让过孔物理
    #   压上焊盘, KiCad BOARD::Add 连通性会把异网名静默传播给过孔 (T4 实测:
    #   GND 缝合过孔压 DRV1/DRV2/+5V pad 后存盘即变网)
    VIA_R = 0.35
    if not (1.2 < vx < 98.8 and 1.2 < vy < 78.8):
        return False
    for qx, qy, qnet, is_npth, qr, _hwx, _hhx in ALL_PADS:
        d = math.hypot(qx - vx, qy - vy)
        if is_npth and d < npth_min:
            return False
        if qnet == net:
            if d < same_min:
                return False
        elif d < qr + VIA_R + pad_gap:
            return False
    return True

def zone(name, layer, pts, min_thickness=0.3, prio=0):
    z = pcbnew.ZONE(board)
    z.SetLayer(layer)
    z.SetNetCode(netcode(name))
    z.SetMinThickness(int(MM(min_thickness)))
    z.SetZoneName(name)
    z.SetAssignedPriority(prio)  # 同网共边/重叠区必须异优先级, 否则 DRC zones_intersect
    ol = z.Outline()
    ol.NewOutline()
    for cx, cy in pts:
        ol.Append(int(MM(cx)), int(MM(cy)))
    board.Add(z)
    return z

# ================= 阶段 1: 平面 + 过孔 =================
if STAGE >= 1:
    # 幂等守卫: 阶段1跑过后(>1 块 zone)不再重建。判据用 COUNT 而非
    # SWIG getter——KiCad 10 python 的 ZONE.GetLayerName/GetIsRuleArea 在
    # 载入已填充板时会撒谎 (T4 实测: 新建 zone GetLayer()=4 正确而
    # GetLayerName() 报 F.Cu; 载入含填充板时 GetIsRuleArea 全真致幂等
    # 判空失效→zone 翻倍)。T3 新板恰好只有 keepout 一块。
    # board.Remove(zone) 亦会毒化 SWIG 堆, 本项目永远无需删除重建。
    # ⚠ guard 必须真的跳过: 只 print 不跳会让每次累积重跑把 9 块平面
    #   全部重建一遍 → 同网同优先级重叠 → 10 条 zones_intersect (T4 实测)
    _n_zones = len(list(board.Zones()))
    if _n_zones > 1:
        print(f"[stage1] zone 共 {_n_zones} 块 (>1=阶段1已跑), 跳过重建 (幂等)")
    else:
        # 层叠: F=信号+GND填充 / In1=GND面 / In2=电源分区 / B=+3V3面外的GND面
        # In2 分区按 T3b 100x80 布局重推导 (P1.0 L 形区不覆盖右带 J20-J23/D12-D15):
        #   +5V: Z5a 左上(J1/U7/C17/TP2) + Z5b buck 输入带(R3/C1/C2/D2/U3/C15)
        #        + Z5c 底带全宽(D4-D11/J10-J17) + Z5d 右带(J20-J23/D12-D15/C16)
        #        — 四块两两共边连通 (a-b 共 x14 边, b-c 共 y53-55, c-d 大面积重叠)
        #   +3V3: Z3a 顶带(x≥14, U1/R7/J7/J9/J18/J19/U4) + Z3b R13/R14 颈
        #        + Z3c 中心大块(30-79/20-58, U2/U6/上拉阵/LED) — 共边连通
        #   边界 x14 切在 U7.5(+5V,12.5) 与 R7.1(+3V3,15.7) 之间;
        #   遗留 J5(98.3,74)/J6(5,55.8)/J8(5,42.3) 三枚 3V3 THT 无同网区, 归 freerouting F/B 收尾
        zone("GND", pcbnew.In1_Cu, [(0.5, 0.5), (99.5, 0.5), (99.5, 79.5), (0.5, 79.5)], prio=1)
        zone("+5V", pcbnew.In2_Cu, [(3, 13), (14, 13), (14, 36), (3, 36)], prio=2)          # Z5a
        zone("+5V", pcbnew.In2_Cu, [(14, 33.5), (36, 33.5), (36, 55), (14, 55)], prio=3)    # Z5b
        zone("+5V", pcbnew.In2_Cu, [(0.5, 53), (99.5, 53), (99.5, 79.5), (0.5, 79.5)], prio=4)  # Z5c
        zone("+5V", pcbnew.In2_Cu, [(79.5, 14), (99.5, 14), (99.5, 79.5), (79.5, 79.5)], prio=5)  # Z5d
        zone("+3V3", pcbnew.In2_Cu, [(14, 0.5), (99.5, 0.5), (99.5, 20), (14, 20)], prio=2)     # Z3a
        zone("+3V3", pcbnew.In2_Cu, [(18, 20), (30, 20), (30, 33.5), (18, 33.5)], prio=3)   # Z3b
        zone("+3V3", pcbnew.In2_Cu, [(30, 20), (79, 20), (79, 58), (30, 58)], prio=4)       # Z3c
        zone("GND", pcbnew.F_Cu, [(0.5, 0.5), (99.5, 0.5), (99.5, 79.5), (0.5, 79.5)], prio=1)
        zone("GND", pcbnew.B_Cu, [(0.5, 0.5), (99.5, 0.5), (99.5, 79.5), (0.5, 79.5)], prio=1)

    _5V_RECTS = [(3, 14, 13, 36), (14, 36, 33.5, 55), (0.5, 99.5, 53, 79.5),
                 (79.5, 99.5, 14, 79.5)]
    _3V3_RECTS = [(14, 99.5, 0.5, 20), (18, 30, 20, 33.5), (30, 79, 20, 58)]

    def _in_rects(rects, vx, vy):
        return any(x1 <= vx <= x2 and y1 <= vy <= y2 for x1, x2, y1, y2 in rects)

    def in_5v_zone(vx, vy):
        return _in_rects(_5V_RECTS, vx, vy)

    def in_3v3_zone(vx, vy):
        return _in_rects(_3V3_RECTS, vx, vy)

    # GND 缝合过孔网格 (避开天线净空 x20.5-35.5/y<6.4)
    n_st = 0
    for gx in range(4, 99, 12):
        for gy in range(4, 79, 12):
            if 20 <= gx <= 36 and gy <= 7:
                continue
            if spot_free(gx, gy, "GND") and not _via_exists(gx, gy, "GND"):
                via("GND", gx, gy)
                n_st += 1
    print(f"[stage1] GND 缝合过孔: {n_st}")

    # 电源焊盘过孔: 对每个 +3V3/+5V SMD 焊盘, 在附近净空点打过孔+短粗线
    # 5V 主干 3A 设计 (450mA×9 保持+泵 0.5=2.75A, 瞬态错峰→3A 档):
    #   - 分发主体=In2 +5V 平面 (区宽数十 mm, 内层 3A 远超需求)
    #   - J1 VBUS 段=F.Cu 逃逸 1.5mm+双过孔分摊 (IPC-2221 1oz 外层 10°C:
    #     1.5mm≈3.4A; 0.35 孔单 via≈1A, 双 via 分摊 2×0.75A)
    #   - 插座分支 ≤0.5A 取 1.0mm (≈2.4A); 3V3 轻载 0.8mm (≈2A)
    PWR_W = {"+3V3": 0.8, "+5V": 1.0}
    placed = 0
    for ref, fp in FP.items():
        for pad in fp.Pads():
            nname = pad.GetNetname()
            if nname not in PWR_W or pad.GetAttribute() != pcbnew.PAD_ATTRIB_SMD:
                continue
            px, py = pcbnew.ToMM(pad.GetPosition().x), pcbnew.ToMM(pad.GetPosition().y)
            # In2 分割线附近归就近平面; 3V3 在左半/5V 在右半, 平面本身会处理连通
            w = 1.5 if ref == "J1" else PWR_W[nname]
            extra = w / 2 + 0.3
            want2 = ref == "J1" and nname == "+5V"   # VBUS 双过孔分摊
            if _via_exists(px, py, nname, r=1.3):
                continue  # 幂等: 该焊盘已打过孔
            spots = []
            used = []
            for _try in range(2 if want2 else 1):
                best = None
                for ang in range(0, 360, 15):
                    for dist in (1.5, 2.1, 2.7, 3.3, 4.2, 5.5):
                        vx = px + dist * math.cos(math.radians(ang))
                        vy = py + dist * math.sin(math.radians(ang))
                        if any(math.hypot(vx - ux, vy - uy) < 1.1 for ux, uy in used):
                            continue
                        in_zone = in_3v3_zone(vx, vy) if nname == "+3V3" else in_5v_zone(vx, vy)
                        if in_zone and spot_free(vx, vy, nname) and                                seg_clear(px, py, vx, vy, nname, extra):
                            best = (vx, vy); break
                    if best:
                        break
                if best:
                    spots.append(best); used.append(best)
            for sp in spots:
                track(nname, [(px, py), sp], width=w)
                via(nname, *sp)
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

# ---- 阶段1.8: 饥饿热焊盘修复——单辐条 GND 花焊盘改 FULL 实连 ----
# 布局把 6 枚 SMD GND 焊盘挤进铜口袋(四向仅 1 辐条 < DRC 最少 2), 改实连
# 既消 starved_thermal 又利功率件散热 (U5 buck/T2 传感 GND 实连是常规做法)。
# 幂等: 重复设置同值无害。
# 第二批 (T4 stage2 后): stage2 走线把 F.Cu GND 填充切出单辐条口袋 —
# R59/Q15/R23/Q16 的 GND 腿 (布局态本有 2+ 辐条, 被新走线割走)。
_STARVED = [("J2", "A12"), ("J2", "B12"), ("U5", "2"), ("U2", "2"), ("U2", "12"), ("U7", "2"),
            ("R59", "2"), ("Q15", "2"), ("R23", "2"), ("Q16", "2")]
_nfull = 0
for _ref, _pn in _STARVED:
    if _ref not in FP:
        continue
    _p = FP[_ref].FindPadByNumber(str(_pn))
    if _p is not None and _p.GetNetname() == "GND":
        _p.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
        _nfull += 1
print(f"[stage1.8] GND 花焊盘改实连: {_nfull}")

# ================= 阶段 2+3: 通用自动布线 =================
if STAGE >= 2:
    import math as _m

    # 板界 (100x80): 信号线中心线不得越 [0.55,99.45]x[0.55,79.45]
    # (0.3 板边间距 + 0.125 半宽 + 0.125 余量; T4 实测无界检查把 J1 逃逸
    #  拐角布到 x=100.45 板外 → copper_edge_clearance)
    BX0, BX1, BY0, BY1 = 0.55, 99.45, 0.55, 79.45
    # DRC 网络类铜间距 0.2; 检查模型一律留 0.05 余量
    CLR_NET = 0.25

    def _pt_rect_dist(px, py, qx, qy, hw, hh):
        """点到轴对齐矩形 (中心 qx,qy 半边 hw,hh) 的距离, 入内为 0"""
        dx = max(abs(px - qx) - hw, 0.0)
        dy = max(abs(py - qy) - hh, 0.0)
        return _m.hypot(dx, dy)

    def seg_pad_clear(x1, y1, x2, y2, net, gap=CLR_NET):
        """线段到异网焊盘距离检查 (矩形模型: 外接圆在长条 pad 角区欠保守,
        XH 3.5x1.5 角区 0.5mm 死区曾放进 0.14 间距走线; 采样 0.15mm)"""
        half_w = 0.125  # 0.25mm 信号线半宽
        L = _m.hypot(x2 - x1, y2 - y1)
        n = max(2, int(L / 0.15))
        for k in range(n + 1):
            f = k / n
            if 0.02 < f < 0.98:  # 端点落在源/目标焊盘上, 跳过
                sx, sy = x1 + (x2 - x1) * f, y1 + (y2 - y1) * f
                for qx, qy, qnet, _np, _qr, qhw, qhh in ALL_PADS:
                    if qnet == net:
                        continue
                    # ⚠ 无网焊盘(M3 安装孔/插座定位柱)也是障碍: 跳过会压孔短路
                    # (T4 实测 stage2 走线压 J23.4/U1.38 no-net pad 出 shorting_items)
                    if _pt_rect_dist(sx, sy, qx, qy, qhw, qhh) < half_w + gap:
                        return False
        return True

    def pad_exit(ref, padname):
        """焊盘朝外的逃逸方向(单位向量)"""
        pad = FP[ref].FindPadByNumber(str(padname))
        ang = pad.GetOrientation()
        a = pcbnew.ToDegrees(ang.AsRadians()) if hasattr(ang, "AsRadians") else float(ang) / 10
        a = a % 360
        return (_m.cos(_m.radians(a)), _m.sin(_m.radians(a)))

    def _existing_obstacles():
        """F.Cu 既有铜: (线段, 半宽, 网) + (过孔点, 半径, 网) — 宽度感知
        (T4 实测 0.8mm 电源逃逸线旁仅按中心线 0.5 判距放进 0.073 间距)。
        每次调用重建: stage2 自身新布的线对后续网络也是障碍。"""
        out = []
        for tr in board.GetTracks():
            _nm = tr.GetNetname()
            if tr.GetClass() == "PCB_TRACK" and tr.GetLayer() == pcbnew.F_Cu:
                s, e = tr.GetStart(), tr.GetEnd()
                out.append(("T", pcbnew.ToMM(s.x), pcbnew.ToMM(s.y),
                            pcbnew.ToMM(e.x), pcbnew.ToMM(e.y),
                            pcbnew.ToMM(tr.GetWidth()) / 2, _nm))
            elif tr.GetClass() == "PCB_VIA":
                q = tr.GetPosition()
                out.append(("V", pcbnew.ToMM(q.x), pcbnew.ToMM(q.y), 0, 0, 0.35, _nm))
        return out

    def _pt_seg_dist(px, py, x1, y1, x2, y2):
        dx, dy = x2 - x1, y2 - y1
        L2 = dx * dx + dy * dy
        tp = 0 if L2 == 0 else max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / L2))
        return _m.hypot(px - (x1 + tp * dx), py - (y1 + tp * dy))

    def seg_track_clear(x1, y1, x2, y2, net, new_half_w=0.125):
        """与既有 F.Cu 铜的间距: 需要 = 新半宽 + 既有半宽 + 0.2 网络类间距;
        双向密采样 0.3mm (T4 实测仅端点+中点采样漏检平行斜交)"""
        L = _m.hypot(x2 - x1, y2 - y1)
        n = max(2, int(L / 0.3))
        for kind, tx1, ty1, tx2, ty2, hw, tnet in _existing_obstacles():
            if tnet == net or not tnet:
                continue
            need = new_half_w + hw + CLR_NET
            # 粗包围盒预筛
            if max(x1, x2) + need < min(tx1, tx2) or min(x1, x2) - need > max(tx1, tx2):
                continue
            if max(y1, y2) + need < min(ty1, ty2) or min(y1, y2) - need > max(ty1, ty2):
                continue
            hit = False
            for k in range(n + 1):
                f = k / n
                if _pt_seg_dist(x1 + (x2 - x1) * f, y1 + (y2 - y1) * f,
                                tx1, ty1, tx2, ty2) < need:
                    hit = True
                    break
            if not hit:
                # 反向: 既有铜采样点到新线段
                m = max(2, int(_m.hypot(tx2 - tx1, ty2 - ty1) / 0.3))
                for k in range(m + 1):
                    f = k / m
                    if _pt_seg_dist(tx1 + (tx2 - tx1) * f, ty1 + (ty2 - ty1) * f,
                                    x1, y1, x2, y2) < need:
                        hit = True
                        break
            if hit:
                return False
        return True

    def seg_ok(pts, net, gap=CLR_NET):
        for a in pts:
            if not (BX0 <= a[0] <= BX1 and BY0 <= a[1] <= BY1):
                return False
        for s, e in zip(pts[:-1], pts[1:]):
            if not seg_pad_clear(s[0], s[1], e[0], e[1], net, gap):
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
    # ---- 显式干线: 已废弃 ----
    # P1.0 (90x75 板) 的走廊坐标随 T3b 100x80 重布局全部失效, 布出去只会产生
    # 浮空错位走线+挤占真线通道(贪心冲突消解还会误删好线)。P1.1 改由上方
    # 通用最近邻 route_L 全网表覆盖; freerouting round4 收尾剩余。
    MANUAL = {
        # "IO4": [ ... P1.0 坐标, 仅存 git 历史: git show d4ee812:tools/route_pcb.py ]
    }
    for net, pts in MANUAL.items():
        track(net, pts, width=0.25, prio=0)
    done2 = list(MANUAL)
    print(f"[manual] 干线 {len(done2)} 网 (P1.0 表已废弃=0)")

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

# ---- 网名完整性后验: 过孔若物理压上异网焊盘铜, BOARD::Add 会把异网名静默 ----
# ---- 传播给它 (T4 实测 GND 缝合过孔变 DRV1/DRV2/+5V) —— 逐孔复核, 违者删 ----
_net_bad = 0
for tr in list(board.GetTracks()):
    if tr.GetClass() != "PCB_VIA":
        continue
    q = tr.GetPosition()
    vx, vy = pcbnew.ToMM(q.x), pcbnew.ToMM(q.y)
    vnet = tr.GetNetname()
    for qx, qy, qnet, _np, qr, _hwx, _hhx in ALL_PADS:
        if qnet and qnet != vnet and math.hypot(qx - vx, qy - vy) < qr + 0.30:
            print(f"[netfix] 删异网传播过孔 {vnet}@({vx:.1f},{vy:.1f}) 压 {qnet} pad")
            board.Remove(tr)
            _net_bad += 1
            break
print(f"[netfix] 删除异网传播过孔: {_net_bad}")

# ---- 重合铜去重 (幂等硬化) ----
# 累积 stage 重跑时, 阶段1 电源过孔守卫 (_via_exists r=1.3 < 候选最小 dist 1.5)
# 拦不住同位重放 (T4 实测一次重跑翻出 68 枚同位同网过孔)。同网同位铜本就冗余,
# 存盘前统一归一: 过孔按 (网,坐标) 去重; 走线按 (网,层,端点无向) 去重留最宽。
_via_seen = {}
_nvd = 0
for tr in list(board.GetTracks()):
    if tr.GetClass() != "PCB_VIA":
        continue
    q = tr.GetPosition()
    k = (tr.GetNetname(), round(q.x), round(q.y))
    if k in _via_seen:
        board.Remove(tr)
        _nvd += 1
    else:
        _via_seen[k] = tr
_trk_seen = {}
_ntd = 0
for tr in list(board.GetTracks()):
    if tr.GetClass() != "PCB_TRACK":
        continue
    s, e = tr.GetStart(), tr.GetEnd()
    # 端点无向键: 水平/垂直线用排序端点; 斜线 (不该出现) 保守按有向
    k2 = (tr.GetNetname(), tr.GetLayer(),
          min(s.x, e.x), min(s.y, e.y), max(s.x, e.x), max(s.y, e.y)) \
         if (s.x == e.x or s.y == e.y) else \
         (tr.GetNetname(), tr.GetLayer(), s.x, s.y, e.x, e.y)
    if k2 in _trk_seen:
        if tr.GetWidth() > _trk_seen[k2].GetWidth():
            board.Remove(_trk_seen[k2])
            _trk_seen[k2] = tr
        else:
            board.Remove(tr)
        _ntd += 1
    else:
        _trk_seen[k2] = tr
print(f"[dedup] 同位过孔 -{_nvd}, 同位走线 -{_ntd}")

# 填充所有平面
try:
    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(list(board.Zones()))
except Exception as e:
    print("zone fill:", e)
pcbnew.SaveBoard(BF, board)
print(f"[route] stage {STAGE} 完成")
