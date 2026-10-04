# -*- coding: utf-8 -*-
"""FLOWIO-CN P1 布线器
阶段1: 平面区 + GND 缝合过孔 + 电源焊盘过孔(带净空搜索)
阶段1.5: 电源引出线事后验证(触碰异网即删)
阶段2+3: 通用网表驱动直布——收集全部非电源 SMD 焊盘按最近邻链式 L 形布线,
         无写死通道数 (P1.0 的 8 路 MANUAL 干线表已随 90x75 布局废弃,
         P1.1 12 路 J10-J23/J20-J23 驱动栅网由网表自动覆盖)
阶段4: SES 导入后电源收尾——J1 +5V 入口三通道 + In2 Z5a↔Z5b 颈桥
用法: kiCad-python route_pcb.py [stage]   (stage 累积, 3=布线, 4=SES后收尾)
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
        if math.hypot(b[0] - a[0], b[1] - a[1]) < 0.05:
            continue
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

def _pd_seg(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    L2 = dx * dx + dy * dy
    tp = 0 if L2 == 0 else max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / L2))
    return math.hypot(px - (x1 + tp * dx), py - (y1 + tp * dy))

def seg_clear(x1, y1, x2, y2, net, extra=0.75, layer=pcbnew.F_Cu):
    """电源/逃逸引线段 (默认 F.Cu) 不得扫过异网焊盘/同层走线/过孔(穿层, 采样 0.4mm)
    extra = 线半宽 + 铜间距 (0.8mm 线→0.75 / 1.0mm 线→0.85 / 1.5mm 线→1.1)
    (round5 后: freerouting 信号铜是真实障碍, T4-r4 曾因无视它把 +5V 过孔
    压上 P5_CC1 拐线出 shorting; ⚠ 走线仅查同层 —— 异层从下方穿过无害,
    全层检查会把密集内层布线区判成全堵, T4-r5 实测 6.5mm 环搜零落点)"""
    L = math.hypot(x2 - x1, y2 - y1)
    n = max(2, int(L / 0.4))
    bx0, bx1 = min(x1, x2) - 1.2, max(x1, x2) + 1.2
    by0, by1 = min(y1, y2) - 1.2, max(y1, y2) + 1.2
    for k in range(n + 1):
        f = k / n
        if 0.05 < f < 0.95:          # 起点在源焊盘上, 跳过
            sx, sy = x1 + (x2 - x1) * f, y1 + (y2 - y1) * f
            for qx, qy, qnet, _np, qr, _hw, _hh in ALL_PADS:
                d = math.hypot(qx - sx, qy - sy)
                if qnet != net and d < qr + extra:
                    return False
    for tr in board.GetTracks():
        tn = tr.GetNetname()
        if tn == net or not tn:
            continue
        if tr.GetClass() == "PCB_VIA":
            q = tr.GetPosition()
            if bx0 < pcbnew.ToMM(q.x) < bx1 and by0 < pcbnew.ToMM(q.y) < by1:
                if _pd_seg(pcbnew.ToMM(q.x), pcbnew.ToMM(q.y), x1, y1, x2, y2) < 0.35 + extra + 0.2:
                    return False
        elif tr.GetClass() == "PCB_TRACK" and tr.GetLayer() == layer:
            s, e = tr.GetStart(), tr.GetEnd()
            tsx, tsy = pcbnew.ToMM(s.x), pcbnew.ToMM(s.y)
            tex, tey = pcbnew.ToMM(e.x), pcbnew.ToMM(e.y)
            if max(tsx, tex) < bx0 or min(tsx, tex) > bx1 or max(tsy, tey) < by0 or min(tsy, tey) > by1:
                continue
            hw = pcbnew.ToMM(tr.GetWidth()) / 2
            for k in range(n + 1):
                f = k / n
                sx, sy = x1 + (x2 - x1) * f, y1 + (y2 - y1) * f
                if _pd_seg(sx, sy, tsx, tsy, tex, tey) < hw + extra + 0.2:
                    return False
    return True

def spot_free(vx, vy, net, pad_gap=0.65, same_min=0.9, npth_min=3.7, own=None, via_r=0.35):
    # own=(x,y): via-in-pad 场景跳过源焊盘自身 (否则 same_min 必拒)
    # via_r: 过孔环半径 (0.7 孔=0.35 默认; 0.6 孔 VIP 传 0.3 —— T4-r5 实测
    #   R4.1 距 B.Cu S2_SCL 线 0.6497, 0.35 模型差 0.0003 误拒)
    # pad_gap=0.65: 0.5 板级铜间距 + 0.15 双模型误差裕量 (T4-r5 实测 0.55 时
    #   +3V3 逃逸线端头距 R9.2 0.18 出 clearance; 模型半径 vs 真焊盘圆角差);
    # npth_min=3.7: M3 安装孔=铜柱心; 净空 = npth_min - 柱外径半径3.15 - 过孔半径0.35
    # = 0.2 真裕量 (3.5 时仅相切 0 裕量, T3 缺陷4 复审修正)
    # ⚠ 异网焊盘必须按真实半径 qr 判距: XH pad r=1.9 时固定 1.7 会让过孔物理
    #   压上焊盘, KiCad BOARD::Add 连通性会把异网名静默传播给过孔 (T4 实测:
    #   GND 缝合过孔压 DRV1/DRV2/+5V pad 后存盘即变网)
    VIA_R = via_r
    if not (1.2 < vx < 98.8 and 1.2 < vy < 78.8):
        return False
    for qx, qy, qnet, is_npth, qr, _hwx, _hhx in ALL_PADS:
        if own is not None and abs(qx - own[0]) < 0.05 and abs(qy - own[1]) < 0.05:
            continue
        d = math.hypot(qx - vx, qy - vy)
        if is_npth and d < npth_min:
            return False
        if qnet == net:
            if d < same_min:
                return False
        elif d < qr + VIA_R + pad_gap:
            return False
    # freerouting 信号铜 (过孔穿全层, track 任意层) 也是障碍 (T4-r4 shorting 教训)
    for tr in board.GetTracks():
        tn = tr.GetNetname()
        if tn == net or not tn:
            continue
        if tr.GetClass() == "PCB_VIA":
            q = tr.GetPosition()
            if math.hypot(pcbnew.ToMM(q.x) - vx, pcbnew.ToMM(q.y) - vy) < VIA_R + 0.35 + 0.2:
                return False
        elif tr.GetClass() == "PCB_TRACK":
            s, e = tr.GetStart(), tr.GetEnd()
            tsx, tsy = pcbnew.ToMM(s.x), pcbnew.ToMM(s.y)
            tex, tey = pcbnew.ToMM(e.x), pcbnew.ToMM(e.y)
            if max(tsx, tex) < vx - 1.2 or min(tsx, tex) > vx + 1.2 or max(tsy, tey) < vy - 1.2 or min(tsy, tey) > vy + 1.2:
                continue
            hw = pcbnew.ToMM(tr.GetWidth()) / 2
            if _pd_seg(vx, vy, tsx, tsy, tex, tey) < hw + VIA_R + 0.2:
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

# ---- 公共收尾: 重合铜去重 + 平面填充 + 存盘 ----
def _run_tail():
    # 重合铜去重 (幂等硬化): 累积 stage 重跑时, 阶段1 电源过孔守卫
    # (_via_exists r=1.3 < 候选最小 dist 1.5) 拦不住同位重放 (T4 实测一次
    # 重跑翻出 68 枚同位同网过孔)。同网同位铜本就冗余, 存盘前统一归一:
    # 过孔按 (网,坐标) 去重; 走线按 (网,层,端点无向) 去重留最宽。
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

# ================= 阶段 4: SES 导入后电源收尾 (独立路径, 提前退出) =================
# freerouting 只布 0.2mm 信号线, 电源容量必须脚本补; 且障碍模型只认焊盘/自家
# 走线, 不能在已布板上重跑阶段 1-3 (会重复布线/压线出短路) —— 故 stage 4
# 做完自己的事直接 _run_tail + exit, 不落入后续阶段。
if STAGE == 4:
    import math as _m4

    def _in2_clear(pts, net, half_w):
        """In2 中心线净空: 过孔(全层穿孔) + In2 走线 + NPTH 钻孔。
        need = half_w + 障碍半径 + 0.25"""
        for s, e in zip(pts[:-1], pts[1:]):
            L = _m4.hypot(e[0] - s[0], e[1] - s[1])
            n = max(2, int(L / 0.3))
            for k in range(n + 1):
                f = k / n
                px, py = s[0] + (e[0] - s[0]) * f, s[1] + (e[1] - s[1]) * f
                for tr in board.GetTracks():
                    if tr.GetNetname() == net or not tr.GetNetname():
                        continue
                    if tr.GetClass() == "PCB_VIA":
                        q = tr.GetPosition()
                        if _m4.hypot(pcbnew.ToMM(q.x) - px, pcbnew.ToMM(q.y) - py) < half_w + 0.35 + 0.25:
                            return False
                    elif tr.GetLayer() == pcbnew.In2_Cu:
                        st, en = tr.GetStart(), tr.GetEnd()
                        hw2 = pcbnew.ToMM(tr.GetWidth()) / 2
                        if _pd_seg(px, py, pcbnew.ToMM(st.x), pcbnew.ToMM(st.y),
                                   pcbnew.ToMM(en.x), pcbnew.ToMM(en.y)) < half_w + hw2 + 0.25:
                            return False
                for qx, qy, qnet, is_np, _qr, qhw, qhh in ALL_PADS:
                    if is_np:  # 钻孔穿 In2 (J1 固定孔等, 半径按孔径)
                        if _pd_seg(qx, qy, s[0], s[1], e[0], e[1]) < qhw + half_w + 0.25:
                            return False
        return True

    # (a) J1 +5V 入口 (0.5mm 单列 USB-C: 焊盘间隙 0.2mm, F.Cu 正面
    #     全宽逃逸几何不可行; 左缘 0.5mm 边带总线 + A4B9 右狗骨入 In2):
    #       ch1: 左缘总线 0.5mm (x0.7 边带) ≈1.2A@10°C + Z5a 锚过孔
    #       ch2: A4B9 右狗骨 0.2 → via 0.7/0.35 → In2 1.0mm ≈0.9A@10°C
    #     合计 ≈2.1A@10°C / 3.2A@20°C; 分发主体 = In2 平面 (区宽数十 mm)。
    #     ⚠ 过孔落点必须过 spot_free: freerouting 会在 J1 周边布信号
    #     (T4-r5 实测其 P5_CC2 扇出过孔恰落 (4.4,16.9), 盲放 +5V 孔即短路)。
    _J1_VIAS = [(4.40, 21.25)]
    for _vx, _vy in _J1_VIAS:
        if not _via_exists(_vx, _vy, "+5V", r=0.6) and spot_free(_vx, _vy, "+5V"):
            v = pcbnew.PCB_VIA(board)
            v.SetNetCode(netcode("+5V"))
            v.SetPosition(pcbnew.VECTOR2I(int(MM(_vx)), int(MM(_vy))))
            v.SetViaType(pcbnew.VIATYPE_THROUGH)
            v.SetWidth(int(MM(0.7)))
            v.SetDrill(int(MM(0.35)))
            board.Add(v)
            print(f"[stage4] J1 +5V 过孔 @({_vx},{_vy})")
    _S4_FCU = [
        (0.2, [(1.90, 21.25), (4.40, 21.25)]),                 # A4B9 右狗骨
        (0.5, [(1.90, 16.60), (0.70, 16.60), (0.70, 25.50), (4.50, 25.50)]),  # 左缘总线
        (0.5, [(1.90, 21.45), (0.70, 21.45)]),                 # A4B9 并入左总线
    ]
    for _w, _pts in _S4_FCU:
        track("+5V", _pts, width=_w, layer=pcbnew.F_Cu)
    # 左总线的 Z5a 锚过孔 (总线是 F.Cu, 必须过孔才挨到 In2 平面; T4-r5 曾整条悬空)
    for _vx, _vy in [(4.20, 25.50), (3.45, 25.50)]:
        if not _via_exists(_vx, _vy, "+5V", r=0.6) and spot_free(_vx, _vy, "+5V"):
            via("+5V", _vx, _vy)
            print(f"[stage4] 左总线 Z5a 锚孔 @({_vx},{_vy})")
    _S4_IN2 = [
        [(4.40, 21.25), (4.40, 20.40), (7.20, 20.40)],   # y20.4: 避 P5_CC2 In2 线 (y19.2)
    ]
    for _pts in _S4_IN2:
        if _via_exists(_pts[0][0], _pts[0][1], "+5V", r=0.6) and _in2_clear(_pts, "+5V", 0.5):
            track("+5V", _pts, width=1.0, layer=pcbnew.In2_Cu)
        else:
            print(f"[stage4] In2 引入段 {_pts[0]} 无锚孔或被阻, 跳过")

    # (b) In2 Z5a↔Z5b 颈桥: 两区共边仅 x14/y33.5-36 = 2.5mm (内层 ~1.2A@10°C),
    #     且 freerouting 在该带布了 S4_SDA(y36.1)/+3V3(y34.2) 两条 In2 信号线,
    #     任何粗走线桥都穿不过剩余窗口 → 新增一块跨颈 +5V 平面 (填充自动在
    #     信号线周 carve 0.2 净空, 颈下带 y33.5-34 + 信号线间岛连通), 等效颈宽
    #     2.5→~4.5mm ≈ 3A 内层档。矩形 x≤17 让开 +3V3 Z3b (x≥18)。
    #     幂等: In2 层 +5V 区恰 4 块 (Z5a-d) 时才建, 建后变 5。
    _n_5v_in2 = sum(1 for z in board.Zones()
                    if (not z.GetIsRuleArea()) and z.GetNetname() == "+5V"
                    and z.GetLayer() == pcbnew.In2_Cu)
    if _n_5v_in2 == 4:
        zone("+5V", pcbnew.In2_Cu,
             [(6.0, 32.5), (17.0, 32.5), (17.0, 38.0), (6.0, 38.0)], prio=6)
        print("[stage4] 颈桥平面 Z5NECK (6-17, 32.5-38) prio6 已建")
    else:
        print(f"[stage4] In2 +5V 区已有 {_n_5v_in2} 块 (≠4=颈桥已建), 跳过")

    # (c) freerouting 扇出短桩加宽 0.15 → 0.2 (netclass 最小线宽)。
    #     ⚠ 本进程不做任何 board.Remove (SWIG 堆毒化, T4 实测 Remove 后
    #     GetTracks 返回不可迭代 SwigPyObject) —— 退化短段一并加宽即可
    #     (0.006mm 段加宽后即同网铜点, 无害); 真要删另起进程。
    _nwid = 0
    for tr in board.GetTracks():
        if tr.GetClass() == "PCB_TRACK" and pcbnew.ToMM(tr.GetWidth()) < 0.199:
            tr.SetWidth(int(MM(0.2)))
            _nwid += 1
    print(f"[stage4] 扇出短桩加宽 {_nwid}")

    # (d) GND 孤立焊盘修复: 自定义形状 PTH 屏蔽腿 (J1.1-4/J2.7, 热辐条算不出)
    #     + 被 freerouting 走线围死的 GND 腿 → FULL 实连 + via-in-pad (0.6/0.3
    #     恰容于 0.6 宽焊盘内, 零外溢) 系锚到 In1/B 平面。
    _FULL_S4 = [("J1", "1"), ("J1", "2"), ("J1", "3"), ("J1", "4"), ("J1", "A1B12"), ("J1", "B1A12"),
                ("J2", "7"),   # 4 枚同名屏蔽腿, 循环内全量命中
                ("U2", "1"), ("U2", "2"), ("U2", "12"), ("U2", "21"),
                ("Q12", "2"), ("U4", "3"), ("R64", "2"), ("R24", "2"), ("R23", "2"),
                ("Q11", "2"), ("U5", "2"), ("R47", "2"), ("U7", "2"), ("Q13", "2"), ("Q14", "2"),
                ("Q8", "2"), ("R54", "2"), ("U1", "40"), ("C2", "2")]
    _VIP_S4 = [r for r in _FULL_S4 if r[0] not in ("J1",)]
    _nf = 0
    for _ref, _pn in _FULL_S4:
        if _ref not in FP:
            continue
        for _p in FP[_ref].Pads():
            if str(_p.GetPadName()) == _pn and _p.GetNetname() == "GND":
                _p.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
                _nf += 1
    _nv = 0
    _nesc = 0
    for _ref, _pn in _VIP_S4:
        if _ref not in FP:
            continue
        _p = FP[_ref].FindPadByNumber(_pn)
        if _p is None or _p.GetNetname() != "GND":
            continue
        _q = _p.GetPosition()
        _x, _y = pcbnew.ToMM(_q.x), pcbnew.ToMM(_q.y)
        if _via_exists(_x, _y, "GND", r=0.3):
            continue
        if spot_free(_x, _y, "GND", same_min=0.45):
            v = pcbnew.PCB_VIA(board)
            v.SetNetCode(netcode("GND"))
            v.SetPosition(pcbnew.VECTOR2I(int(MM(_x)), int(MM(_y))))
            v.SetViaType(pcbnew.VIATYPE_THROUGH)
            v.SetWidth(int(MM(0.6)))
            v.SetDrill(int(MM(0.3)))
            board.Add(v)
            _nv += 1
            continue
        # 焊盘中心不净空 (freerouting 内层信号骑上 GND 焊盘 / SOP-6 0.65 节距
        # 邻腿太近): 环搜就近落点 + F.Cu 0.3mm 短逃逸线
        done = False
        for _rr in (0.8, 1.2, 1.6, 2.0, 2.6, 3.2, 4.0, 4.8, 5.6, 6.5):
            for _a2 in range(0, 360, 15):
                _vx = _x + _rr * _m4.cos(_m4.radians(_a2))
                _vy = _y + _rr * _m4.sin(_m4.radians(_a2))
                if spot_free(_vx, _vy, "GND", same_min=0.45) and                        seg_clear(_x, _y, _vx, _vy, "GND", 0.45):
                    via("GND", _vx, _vy)
                    track("GND", [(_x, _y), (_vx, _vy)], width=0.3, layer=pcbnew.F_Cu)
                    _nesc += 1
                    done = True
                    break
            if done:
                break
        if not done:
            print(f"[stage4] GND 焊盘 {_ref}.{_pn} 无净空落点!")
    print(f"[stage4] GND FULL {_nf}, via-in-pad {_nv}, 逃逸系锚 {_nesc}")

    _run_tail()
    sys.exit(0)

# ================= 阶段 5: 散件收尾 (round5 后残余, 独立路径提前退出) =================
if STAGE == 5:
    import math as _m5

    # (a) 失败电源焊盘窄线重试: 焊盘无同网 F.Cu 逃逸线触达 (端点距焊盘心 <0.3)
    #     → 以 0.6/0.4 两档线宽重搜 (轻载 pull-up/LED/去耦焊盘 0.4mm ≈1A 足够)
    _5V_RECTS = [(3, 14, 13, 36), (14, 36, 33.5, 55), (0.5, 99.5, 53, 79.5),
                 (79.5, 99.5, 14, 79.5)]
    _3V3_RECTS = [(14, 99.5, 0.5, 20), (18, 30, 20, 33.5), (30, 79, 20, 58)]

    def _in_r(rects, x, y):
        return any(x1 <= x <= x2 and y1 <= y <= y2 for x1, x2, y1, y2 in rects)

    _placed5 = 0
    for ref5, fp5 in FP.items():
        for pad5 in fp5.Pads():
            nn5 = pad5.GetNetname()
            if nn5 not in ("+3V3", "+5V") or pad5.GetAttribute() != pcbnew.PAD_ATTRIB_SMD:
                continue
            px5, py5 = pcbnew.ToMM(pad5.GetPosition().x), pcbnew.ToMM(pad5.GetPosition().y)
            has_esc = False
            for tr5 in board.GetTracks():
                if tr5.GetNetname() == nn5 and tr5.GetClass() == "PCB_TRACK" and tr5.GetLayer() == pcbnew.F_Cu:
                    s5, e5 = tr5.GetStart(), tr5.GetEnd()
                    if (abs(pcbnew.ToMM(s5.x) - px5) < 0.3 and abs(pcbnew.ToMM(s5.y) - py5) < 0.3) or \
                       (abs(pcbnew.ToMM(e5.x) - px5) < 0.3 and abs(pcbnew.ToMM(e5.y) - py5) < 0.3):
                        has_esc = True
                        break
            if has_esc:
                continue
            done5 = False
            for w5 in (0.6, 0.4):
                ex5 = w5 / 2 + 0.4
                for ang5 in range(0, 360, 10):
                    for d5 in (1.5, 2.1, 2.7, 3.3, 4.2, 5.5, 6.5, 8.0):
                        vx5 = px5 + d5 * _m5.cos(_m5.radians(ang5))
                        vy5 = py5 + d5 * _m5.sin(_m5.radians(ang5))
                        inz5 = _in_r(_3V3_RECTS if nn5 == "+3V3" else _5V_RECTS, vx5, vy5)
                        if inz5 and spot_free(vx5, vy5, nn5) and                                seg_clear(px5, py5, vx5, vy5, nn5, ex5):
                            track(nn5, [(px5, py5), (vx5, vy5)], width=w5, layer=pcbnew.F_Cu)
                            via(nn5, vx5, vy5)
                            _placed5 += 1
                            done5 = True
                            break
                    if done5:
                        break
                if done5:
                    break
            if not done5:
                # 终极兜底: via-in-pad (T4-r5 实测 R4.1 被 FB 走线三面围死,
                # 0.4mm 逃逸走廊不存在; 0.6/0.3 孔在 0.81x0.86 焊盘内恰好净空)。
                # 仅当焊盘位于本网 In2 平面矩形内 (孔穿 In2 即挨平面)。
                if _in_r(_3V3_RECTS if nn5 == "+3V3" else _5V_RECTS, px5, py5) and                        spot_free(px5, py5, nn5, pad_gap=0.28, same_min=0.4, own=(px5, py5), via_r=0.3):
                    v5 = pcbnew.PCB_VIA(board)
                    v5.SetNetCode(netcode(nn5))
                    v5.SetPosition(pcbnew.VECTOR2I(int(MM(px5)), int(MM(py5))))
                    v5.SetViaType(pcbnew.VIATYPE_THROUGH)
                    v5.SetWidth(int(MM(0.6)))
                    v5.SetDrill(int(MM(0.3)))
                    board.Add(v5)
                    _placed5 += 1
                    done5 = True
            if not done5:
                print(f"[stage5] 电源焊盘 {ref5}.{pad5.GetPadName()} {nn5} 窄线重试仍失败")
    print(f"[stage5] 窄线重试逃逸: {_placed5}")

    # (b) GND F.Cu 填充孤岛系锚: 无过孔的岛内放孔 (F 填充与 In1/B 平面失联根因)
    def _pip(x, y, xs, ys):
        n_, inside = len(xs), False
        j_ = n_ - 1
        for i_ in range(n_):
            if (ys[i_] > y) != (ys[j_] > y) and \
               x < (xs[j_] - xs[i_]) * (y - ys[i_]) / (ys[j_] - ys[i_] + 1e-12) + xs[i_]:
                inside = not inside
            j_ = i_
        return inside

    _gnd_vias5 = []
    for tr5 in board.GetTracks():
        if tr5.GetClass() == "PCB_VIA" and tr5.GetNetname() == "GND":
            q5 = tr5.GetPosition()
            _gnd_vias5.append((pcbnew.ToMM(q5.x), pcbnew.ToMM(q5.y)))
    _stitch5 = 0
    for z5 in board.Zones():
        if z5.GetIsRuleArea() or z5.GetNetname() != "GND" or z5.GetLayer() != pcbnew.F_Cu:
            continue
        try:
            polys5 = z5.GetFilledPolysList(pcbnew.F_Cu)
        except Exception:
            continue
        for i5 in range(polys5.OutlineCount()):
            ch5 = polys5.Outline(i5)
            xs5 = [pcbnew.ToMM(ch5.CPoint(k5).x) for k5 in range(ch5.PointCount())]
            ys5 = [pcbnew.ToMM(ch5.CPoint(k5).y) for k5 in range(ch5.PointCount())]
            bw5, bh5 = max(xs5) - min(xs5), max(ys5) - min(ys5)
            if bw5 * bh5 < 2.0:
                continue  # 碎屑岛
            if any(_pip(vx5, vy5, xs5, ys5) for vx5, vy5 in _gnd_vias5):
                continue
            hit5 = False
            for kx5 in range(2, 8):
                for ky5 in range(2, 8):
                    gx5 = min(xs5) + bw5 * kx5 / 8.0
                    gy5 = min(ys5) + bh5 * ky5 / 8.0
                    if not _pip(gx5, gy5, xs5, ys5):
                        continue
                    pt5 = pcbnew.VECTOR2I(int(MM(gx5)), int(MM(gy5)))
                    if not z5.HitTestFilledArea(pcbnew.F_Cu, pt5):
                        continue
                    if spot_free(gx5, gy5, "GND", same_min=0.45):
                        via("GND", gx5, gy5)
                        _gnd_vias5.append((gx5, gy5))
                        _stitch5 += 1
                        hit5 = True
                        break
                if hit5:
                    break
    print(f"[stage5] GND 孤岛系锚: {_stitch5}")

    # (c) 断层补孔: F.Cu 走线端点 ↔ In1/B 同网走线端点距 <0.6 且近旁无过孔
    #     (freerouting 优化器留下的层切换残缺, GATE5/7/8/S1_*/S3_* 根因)
    _f_ends, _ib_ends = [], []
    for tr5 in board.GetTracks():
        if tr5.GetClass() != "PCB_TRACK" or not tr5.GetNetname():
            continue
        s5, e5 = tr5.GetStart(), tr5.GetEnd()
        if tr5.GetLayer() == pcbnew.F_Cu:
            _f_ends.append((tr5.GetNetname(), pcbnew.ToMM(s5.x), pcbnew.ToMM(s5.y)))
            _f_ends.append((tr5.GetNetname(), pcbnew.ToMM(e5.x), pcbnew.ToMM(e5.y)))
        elif tr5.GetLayer() in (pcbnew.In1_Cu, pcbnew.B_Cu):
            _ib_ends.append((tr5.GetNetname(), pcbnew.ToMM(s5.x), pcbnew.ToMM(s5.y)))
            _ib_ends.append((tr5.GetNetname(), pcbnew.ToMM(e5.x), pcbnew.ToMM(e5.y)))
    _via_pts5 = []
    for tr5 in board.GetTracks():
        if tr5.GetClass() == "PCB_VIA":
            q5 = tr5.GetPosition()
            _via_pts5.append((pcbnew.ToMM(q5.x), pcbnew.ToMM(q5.y)))
    _j5 = 0
    for nn5, fx5, fy5 in _f_ends:
        for bn5, bx5, by5 in _ib_ends:
            if bn5 != nn5:
                continue
            if _m5.hypot(fx5 - bx5, fy5 - by5) > 0.6:
                continue
            mx5, my5 = (fx5 + bx5) / 2, (fy5 + by5) / 2
            if any(_m5.hypot(mx5 - ux5, my5 - uy5) < 0.7 for ux5, uy5 in _via_pts5):
                continue
            if not spot_free(mx5, my5, nn5, same_min=0.45):
                continue
            v5 = pcbnew.PCB_VIA(board)
            v5.SetNetCode(netcode(nn5))
            v5.SetPosition(pcbnew.VECTOR2I(int(MM(mx5)), int(MM(my5))))
            v5.SetViaType(pcbnew.VIATYPE_THROUGH)
            v5.SetWidth(int(MM(0.6)))
            v5.SetDrill(int(MM(0.3)))
            board.Add(v5)
            _via_pts5.append((mx5, my5))
            _j5 += 1
    print(f"[stage5] 断层补孔: {_j5}")

    # (e) L 型补线: 滞留电源焊盘 / 断链信号端点 → 最近同网"平面锚过孔/链端点"。
    #     平面锚 = 位于本网 In2 平面矩形内的过孔 (孔穿 In2 即与平面连通)。
    def _lay_clear(net, pts, layer, w):
        """L 补线净空: 异网焊盘(矩形) + 同层走线 + 过孔(全层) + 板界"""
        hw6 = w / 2
        for x6, y6 in pts:
            if not (0.55 < x6 < 99.45 and 0.55 < y6 < 79.45):
                return False
        for s6, e6 in zip(pts[:-1], pts[1:]):
            L6 = _m5.hypot(e6[0] - s6[0], e6[1] - s6[1])
            n6 = max(2, int(L6 / 0.25))
            for k6 in range(n6 + 1):
                f6 = k6 / n6
                if 0.02 < f6 < 0.98:
                    px6, py6 = s6[0] + (e6[0] - s6[0]) * f6, s6[1] + (e6[1] - s6[1]) * f6
                    for qx6, qy6, qn6, _np6, _qr6, qhw6, qhh6 in ALL_PADS:
                        if qn6 == net:
                            continue
                        if _pt_r6(px6, py6, qx6, qy6, qhw6, qhh6) < hw6 + 0.22:
                            return False
            for tr6 in board.GetTracks():
                tn6 = tr6.GetNetname()
                if tn6 == net or not tn6:
                    continue
                if tr6.GetClass() == "PCB_VIA":
                    q6 = tr6.GetPosition()
                    if _pd_seg(pcbnew.ToMM(q6.x), pcbnew.ToMM(q6.y), s6[0], s6[1], e6[0], e6[1]) < 0.35 + hw6 + 0.2:
                        return False
        # 同层走线检查用采样
        for s6, e6 in zip(pts[:-1], pts[1:]):
            L6 = _m5.hypot(e6[0] - s6[0], e6[1] - s6[1])
            n6 = max(2, int(L6 / 0.25))
            for tr6 in board.GetTracks():
                tn6 = tr6.GetNetname()
                if tn6 == net or not tn6 or tr6.GetClass() != "PCB_TRACK" or tr6.GetLayer() != layer:
                    continue
                st6, en6 = tr6.GetStart(), tr6.GetEnd()
                tx6, ty6, ux6, uy6 = pcbnew.ToMM(st6.x), pcbnew.ToMM(st6.y), pcbnew.ToMM(en6.x), pcbnew.ToMM(en6.y)
                if max(s6[0], e6[0]) + 1.0 < min(tx6, ux6) or min(s6[0], e6[0]) - 1.0 > max(tx6, ux6):
                    continue
                if max(s6[1], e6[1]) + 1.0 < min(ty6, uy6) or min(s6[1], e6[1]) - 1.0 > max(ty6, uy6):
                    continue
                hwT6 = pcbnew.ToMM(tr6.GetWidth()) / 2
                for k6 in range(n6 + 1):
                    f6 = k6 / n6
                    px6, py6 = s6[0] + (e6[0] - s6[0]) * f6, s6[1] + (e6[1] - s6[1]) * f6
                    if _pd_seg(px6, py6, tx6, ty6, ux6, uy6) < hwT6 + hw6 + 0.22:
                        return False
                for k6 in range(2):
                    px6, py6 = (tx6, ty6) if k6 == 0 else (ux6, uy6)
                    if _pd_seg(px6, py6, s6[0], s6[1], e6[0], e6[1]) < hwT6 + hw6 + 0.22:
                        return False
        return True

    def _pt_r6(px, py, qx, qy, hw, hh):
        dx = max(abs(px - qx) - hw, 0.0)
        dy = max(abs(py - qy) - hh, 0.0)
        return _m5.hypot(dx, dy)

    def _L_try(net, src, dst, layer, w=0.25):
        mx6, my6 = (src[0] + dst[0]) / 2, (src[1] + dst[1]) / 2
        cands = [[src, dst],
                 [src, (dst[0], src[1]), dst],
                 [src, (src[0], dst[1]), dst],
                 [src, (dst[0], src[1] + 0.6), dst],
                 [src, (src[0] + 0.6, dst[1]), dst],
                 [src, (dst[0], src[1] - 0.6), dst],
                 [src, (src[0] - 0.6, dst[1]), dst],
                 # 阶梯: 中点偏移的 4 弯绕行 (正面 L 被阻时的旁路)
                 [src, (mx6, src[1]), (mx6, dst[1]), dst],
                 [src, (src[0], my6), (dst[0], my6), dst],
                 [src, (mx6, src[1] + 1.0), (mx6, dst[1]), dst],
                 [src, (mx6, src[1] - 1.0), (mx6, dst[1]), dst],
                 [src, (src[0] + 1.0, my6), (dst[0], my6), dst],
                 [src, (src[0] - 1.0, my6), (dst[0], my6), dst]]
        for pts in cands:
            pp = [pts[0]]
            for q6 in pts[1:]:
                if _m5.hypot(q6[0] - pp[-1][0], q6[1] - pp[-1][1]) > 0.05:
                    pp.append(q6)
            if len(pp) < 2:
                continue
            if _lay_clear(net, pp, layer, w):
                track(net, pp, width=w, layer=layer)
                return True
        return False

    # 平面锚过孔表
    _anchors = {"+3V3": [], "+5V": []}
    for tr6 in board.GetTracks():
        if tr6.GetClass() == "PCB_VIA" and tr6.GetNetname() in _anchors:
            q6 = tr6.GetPosition()
            x6, y6 = pcbnew.ToMM(q6.x), pcbnew.ToMM(q6.y)
            rr6 = _3V3_RECTS if tr6.GetNetname() == "+3V3" else _5V_RECTS
            if _in_r(rr6, x6, y6):
                _anchors[tr6.GetNetname()].append((x6, y6))
    # (e1) 滞留电源焊盘 → 15mm 内最近平面锚 (F.Cu 0.3mm L)
    # (只补"无任何同网铜触达"的焊盘 — 与 (a) 判据一致)
    _fail_pads = []
    for ref5, fp5 in FP.items():
        for pad5 in fp5.Pads():
            nn5 = pad5.GetNetname()
            if nn5 in ("+3V3", "+5V") and pad5.GetAttribute() == pcbnew.PAD_ATTRIB_SMD:
                _fail_pads.append((ref5, str(pad5.GetPadName()), nn5,
                                   pcbnew.ToMM(pad5.GetPosition().x), pcbnew.ToMM(pad5.GetPosition().y)))
    _patched = 0
    for _pass5 in range(3):
        # 目标 = 平面锚 + 已触达铜的电源焊盘 (迭代: 新补通的焊盘成为下一轮目标)
        _targets = {n5: list(v5) for n5, v5 in _anchors.items()}
        for ref5, pn5, nn5, px5, py5 in _fail_pads:
            touched = False
            for tr5 in board.GetTracks():
                if tr5.GetNetname() != nn5:
                    continue
                if tr5.GetClass() == "PCB_VIA":
                    q5 = tr5.GetPosition()
                    if _m5.hypot(pcbnew.ToMM(q5.x) - px5, pcbnew.ToMM(q5.y) - py5) < 0.6:
                        touched = True
                        break
                elif tr5.GetLayer() == pcbnew.F_Cu:
                    s5, e5 = tr5.GetStart(), tr5.GetEnd()
                    if _pd_seg(px5, py5, pcbnew.ToMM(s5.x), pcbnew.ToMM(s5.y),
                               pcbnew.ToMM(e5.x), pcbnew.ToMM(e5.y)) < 0.45:
                        touched = True
                        break
            if touched:
                _targets.setdefault(nn5, []).append((px5, py5))
        _added = 0
        for ref5, pn5, nn5, px5, py5 in _fail_pads:
            touched = False
            for tr5 in board.GetTracks():
                if tr5.GetNetname() != nn5:
                    continue
                if tr5.GetClass() == "PCB_VIA":
                    q5 = tr5.GetPosition()
                    if _m5.hypot(pcbnew.ToMM(q5.x) - px5, pcbnew.ToMM(q5.y) - py5) < 0.6:
                        touched = True
                        break
                elif tr5.GetLayer() == pcbnew.F_Cu:
                    s5, e5 = tr5.GetStart(), tr5.GetEnd()
                    if _pd_seg(px5, py5, pcbnew.ToMM(s5.x), pcbnew.ToMM(s5.y),
                               pcbnew.ToMM(e5.x), pcbnew.ToMM(e5.y)) < 0.45:
                        touched = True
                        break
            if touched:
                continue
            best = None
            for ax, ay in _targets.get(nn5, []):
                d = _m5.hypot(ax - px5, ay - py5)
                if d < 22 and d > 0.5 and (best is None or d < best[0]):
                    best = (d, ax, ay)
            if best and _L_try(nn5, (px5, py5), (best[1], best[2]), pcbnew.F_Cu):
                _patched += 1
                _added += 1
        if not _added:
            break
    for ref5, pn5, nn5, px5, py5 in _fail_pads:
        touched = any(False for _ in ())
        for tr5 in board.GetTracks():
            if tr5.GetNetname() == nn5 and tr5.GetClass() == "PCB_VIA":
                q5 = tr5.GetPosition()
                if _m5.hypot(pcbnew.ToMM(q5.x) - px5, pcbnew.ToMM(q5.y) - py5) < 0.6:
                    touched = True
                    break
            if touched:
                break
        if not touched:
            for tr5 in board.GetTracks():
                if tr5.GetNetname() == nn5 and tr5.GetClass() == "PCB_TRACK" and tr5.GetLayer() == pcbnew.F_Cu:
                    s5, e5 = tr5.GetStart(), tr5.GetEnd()
                    if _pd_seg(px5, py5, pcbnew.ToMM(s5.x), pcbnew.ToMM(s5.y),
                               pcbnew.ToMM(e5.x), pcbnew.ToMM(e5.y)) < 0.45:
                        touched = True
                        break
            if not touched:
                print(f"[stage5] {ref5}.{pn5} {nn5} 补线失败 (无锚/L 无净空)")
    print(f"[stage5] 电源补线: {_patched}")

    # (e2) 跨层断头缝合: F 端 ↔ In1/B 端距 0.4-2.0 → 孔@F端 + 内层 jog
    _f_ends2, _ib_ends2 = [], []
    for tr5 in board.GetTracks():
        if tr5.GetClass() != "PCB_TRACK" or not tr5.GetNetname() or tr5.GetNetname() in ("GND", "+3V3", "+5V"):
            continue
        s5, e5 = tr5.GetStart(), tr5.GetEnd()
        for ptx, pty in ((pcbnew.ToMM(s5.x), pcbnew.ToMM(s5.y)), (pcbnew.ToMM(e5.x), pcbnew.ToMM(e5.y))):
            if tr5.GetLayer() == pcbnew.F_Cu:
                _f_ends2.append((tr5.GetNetname(), ptx, pty))
            else:
                _ib_ends2.append((tr5.GetNetname(), ptx, pty, tr5.GetLayer()))
    _st2 = 0
    for nn5, fx5, fy5 in _f_ends2:
        for bn5, bx5, by5, bl5 in _ib_ends2:
            if bn5 != nn5:
                continue
            d5 = _m5.hypot(fx5 - bx5, fy5 - by5)
            if not (0.4 < d5 < 2.0):
                continue
            if any(_m5.hypot(fx5 - ux5, fy5 - uy5) < 0.55 for ux5, uy5 in _via_pts5):
                continue
            if not spot_free(fx5, fy5, nn5, same_min=0.4):
                continue
            if not _lay_clear(nn5, [(fx5, fy5), (bx5, by5)], bl5, 0.3):
                continue  # jog 必须过同层净空 (T4-r5 实测盲 jog 短路 S2_SDA/压 IO6)
            v5 = pcbnew.PCB_VIA(board)
            v5.SetNetCode(netcode(nn5))
            v5.SetPosition(pcbnew.VECTOR2I(int(MM(fx5)), int(MM(fy5))))
            v5.SetViaType(pcbnew.VIATYPE_THROUGH)
            v5.SetWidth(int(MM(0.6)))
            v5.SetDrill(int(MM(0.3)))
            board.Add(v5)
            _via_pts5.append((fx5, fy5))
            track(nn5, [(fx5, fy5), (bx5, by5)], width=0.3, layer=bl5)
            _st2 += 1
            break
    print(f"[stage5] 跨层断头缝合: {_st2}")

    # (e3) 同层断段 L 补线: 仅补"真悬空端"(触接图度=1, 即只被自身段触碰的端点),
    #      且两端点分属不同连通分量 —— 否则会给已连通链布冗余平行线 (T4-r5
    #      实测无差别配对炸出 5830 段补线 + 63 条 clearance)
    _lay_ends = {}
    for tr5 in board.GetTracks():
        if tr5.GetClass() != "PCB_TRACK" or not tr5.GetNetname() or tr5.GetNetname() in ("GND", "+3V3", "+5V"):
            continue
        s5, e5 = tr5.GetStart(), tr5.GetEnd()
        for ptx, pty in ((pcbnew.ToMM(s5.x), pcbnew.ToMM(s5.y)), (pcbnew.ToMM(e5.x), pcbnew.ToMM(e5.y))):
            _lay_ends.setdefault((tr5.GetNetname(), tr5.GetLayer()), []).append((ptx, pty))
    _st3 = 0
    for (nn5, ll5), ends5 in _lay_ends.items():
        if len(ends5) < 2:
            continue
        m5 = len(ends5)
        # union-find: 端点距 <0.45 视为相触 (段自身两端除外由距离自然排除)
        par5 = list(range(m5))
        def _find5(i_):
            while par5[i_] != i_:
                par5[i_] = par5[par5[i_]]
                i_ = par5[i_]
            return i_
        for i5 in range(m5):
            for j5 in range(i5 + 1, m5):
                if _m5.hypot(ends5[i5][0] - ends5[j5][0], ends5[i5][1] - ends5[j5][1]) < 0.45:
                    ri5, rj5 = _find5(i5), _find5(j5)
                    if ri5 != rj5:
                        par5[ri5] = rj5
        # 度: 与该端点相触的其他端点数
        deg5 = [sum(1 for j5 in range(m5) if j5 != i5 and
                    _m5.hypot(ends5[i5][0] - ends5[j5][0], ends5[i5][1] - ends5[j5][1]) < 0.45)
                for i5 in range(m5)]
        dangle5 = [i5 for i5 in range(m5) if deg5[i5] == 0]
        for _i5 in range(len(dangle5)):
            for _j5 in range(_i5 + 1, len(dangle5)):
                i5, j5 = dangle5[_i5], dangle5[_j5]
                if _find5(i5) == _find5(j5):
                    continue
                ax5, ay5 = ends5[i5]
                bx5, by5 = ends5[j5]
                d5 = _m5.hypot(ax5 - bx5, ay5 - by5)
                if not (0.4 < d5 < 9.0):
                    continue
                if _L_try(nn5, (ax5, ay5), (bx5, by5), ll5, w=0.2):
                    _st3 += 1
                    ri5, rj5 = _find5(i5), _find5(j5)
                    if ri5 != rj5:
                        par5[ri5] = rj5
    print(f"[stage5] 同层断段补线: {_st3}")

    # (d) 追加 FULL: C11.2 (GND 花焊盘单辐条)
    if "C11" in FP:
        _p5 = FP["C11"].FindPadByNumber("2")
        if _p5 is not None and _p5.GetNetname() == "GND":
            _p5.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)

    _run_tail()
    sys.exit(0)

# ================= 阶段 6: 定点收尾 (显式坐标, 全部运行时核验) =================
if STAGE == 6:
    import math as _m6
    X0c, Y0c = 0.55, 0.55

    def _ok_via(x, y, net):
        """0.6/0.3 孔落点核验: 异网焊盘/过孔/任意层走线"""
        for qx, qy, qnet, _np6, qr, _hw, _hh in ALL_PADS:
            if qnet == net or not qnet:
                continue
            if _m6.hypot(qx - x, qy - y) < qr + 0.3 + 0.203:
                return False
        for tr in board.GetTracks():
            tn = tr.GetNetname()
            if tn == net or not tn:
                continue
            if tr.GetClass() == "PCB_VIA":
                q = tr.GetPosition()
                if _m6.hypot(pcbnew.ToMM(q.x) - x, pcbnew.ToMM(q.y) - y) < 0.3 + 0.35 + 0.203:
                    return False
            elif tr.GetClass() == "PCB_TRACK":
                s, e = tr.GetStart(), tr.GetEnd()
                if _pd_seg(x, y, pcbnew.ToMM(s.x), pcbnew.ToMM(s.y),
                           pcbnew.ToMM(e.x), pcbnew.ToMM(e.y)) < pcbnew.ToMM(tr.GetWidth()) / 2 + 0.3 + 0.203:
                    return False
        return 0.55 < x < 99.45 and 0.55 < y < 79.45

    def _add_via6(x, y, net):
        v = pcbnew.PCB_VIA(board)
        v.SetNetCode(netcode(net))
        v.SetPosition(pcbnew.VECTOR2I(int(MM(x)), int(MM(y))))
        v.SetViaType(pcbnew.VIATYPE_THROUGH)
        v.SetWidth(int(MM(0.6)))
        v.SetDrill(int(MM(0.3)))
        board.Add(v)

    def _ok_route(net, pts, layer, w=0.25):
        """折线核验: 板界 + 异网焊盘(矩形) + 同层走线 + 全层孔; 同网铜不算障"""
        hw = w / 2
        for x, y in pts:
            if not (0.55 < x < 99.45 and 0.55 < y < 79.45):
                return False
        for s, e in zip(pts[:-1], pts[1:]):
            L = _m6.hypot(e[0] - s[0], e[1] - s[1])
            n = max(2, int(L / 0.2))
            for k in range(n + 1):
                f = k / n
                if 0.02 < f < 0.98:
                    px, py = s[0] + (e[0] - s[0]) * f, s[1] + (e[1] - s[1]) * f
                    for qx, qy, qnet, _np6, _qr, qhw, qhh in ALL_PADS:
                        if qnet == net:
                            continue
                        dx = max(abs(px - qx) - qhw, 0.0)
                        dy = max(abs(py - qy) - qhh, 0.0)
                        if _m6.hypot(dx, dy) < hw + 0.203:
                            return False
            for tr in board.GetTracks():
                tn = tr.GetNetname()
                if tn == net or not tn:
                    continue
                if tr.GetClass() == "PCB_VIA":
                    q = tr.GetPosition()
                    if _pd_seg(pcbnew.ToMM(q.x), pcbnew.ToMM(q.y), s[0], s[1], e[0], e[1]) < 0.35 + hw + 0.203:
                        return False
                elif tr.GetLayer() == layer and tr.GetClass() == "PCB_TRACK":
                    st, en = tr.GetStart(), tr.GetEnd()
                    tx, ty, ux, uy = pcbnew.ToMM(st.x), pcbnew.ToMM(st.y), pcbnew.ToMM(en.x), pcbnew.ToMM(en.y)
                    if max(s[0], e[0]) + 1.0 < min(tx, ux) or min(s[0], e[0]) - 1.0 > max(tx, ux):
                        continue
                    if max(s[1], e[1]) + 1.0 < min(ty, uy) or min(s[1], e[1]) - 1.0 > max(ty, uy):
                        continue
                    hwT = pcbnew.ToMM(tr.GetWidth()) / 2
                    for k in range(n + 1):
                        f = k / n
                        px, py = s[0] + (e[0] - s[0]) * f, s[1] + (e[1] - s[1]) * f
                        if _pd_seg(px, py, tx, ty, ux, uy) < hwT + hw + 0.203:
                            return False
                    for px, py in ((tx, ty), (ux, uy)):
                        if _pd_seg(px, py, s[0], s[1], e[0], e[1]) < hwT + hw + 0.203:
                            return False
        return True

    def _apply(net, pts, layer, w=0.25, tag=""):
        if _ok_route(net, pts, layer, w):
            track(net, pts, width=w, layer=layer)
            return True
        print(f"[stage6] 路由受阻 {net} {tag} {pts[:2]}...")
        # 诊断: 报出首个命中障碍
        hw = w / 2
        for s, e in zip(pts[:-1], pts[1:]):
            for tr in board.GetTracks():
                tn = tr.GetNetname()
                if tn == net or not tn:
                    continue
                if tr.GetClass() == "PCB_VIA":
                    q = tr.GetPosition()
                    if _pd_seg(pcbnew.ToMM(q.x), pcbnew.ToMM(q.y), s[0], s[1], e[0], e[1]) < 0.35 + hw + 0.203:
                        print(f"         障碍: via {tn} ({pcbnew.ToMM(q.x):.2f},{pcbnew.ToMM(q.y):.2f})")
                        return False
                elif tr.GetLayer() == layer and tr.GetClass() == "PCB_TRACK":
                    st, en = tr.GetStart(), tr.GetEnd()
                    tx, ty, ux, uy = pcbnew.ToMM(st.x), pcbnew.ToMM(st.y), pcbnew.ToMM(en.x), pcbnew.ToMM(en.y)
                    if max(s[0], e[0]) + 1.0 < min(tx, ux) or min(s[0], e[0]) - 1.0 > max(tx, ux):
                        continue
                    if max(s[1], e[1]) + 1.0 < min(ty, uy) or min(s[1], e[1]) - 1.0 > max(ty, uy):
                        continue
                    hwT = pcbnew.ToMM(tr.GetWidth()) / 2
                    L = _m6.hypot(e[0] - s[0], e[1] - s[1])
                    n = max(2, int(L / 0.2))
                    for k in range(n + 1):
                        f = k / n
                        px, py = s[0] + (e[0] - s[0]) * f, s[1] + (e[1] - s[1]) * f
                        if _pd_seg(px, py, tx, ty, ux, uy) < hwT + hw + 0.203:
                            print(f"         障碍: trk {tn} L{layer} ({tx:.1f},{ty:.1f})-({ux:.1f},{uy:.1f}) w={hwT*2:.2f} @({px:.1f},{py:.1f})")
                            return False
        for qx, qy, qnet, _np6, _qr, qhw, qhh in ALL_PADS:
            if qnet == net:
                continue
            for s, e in zip(pts[:-1], pts[1:]):
                L = _m6.hypot(e[0] - s[0], e[1] - s[1])
                n = max(2, int(L / 0.2))
                for k in range(n + 1):
                    f = k / n
                    if 0.02 < f < 0.98:
                        px, py = s[0] + (e[0] - s[0]) * f, s[1] + (e[1] - s[1]) * f
                        dx = max(abs(px - qx) - qhw, 0.0)
                        dy = max(abs(py - qy) - qhh, 0.0)
                        if _m6.hypot(dx, dy) < hw + 0.203:
                            print(f"         障碍: pad {qnet} ({qx:.1f},{qy:.1f}) @({px:.1f},{py:.1f})")
                            return False
        return False


    import heapq as _hq

    def _obst6(net, x0_, y0_, x1_, y1_, layer):
        """区域障碍表: 异网孔(全层)/同层异网走线/异网焊盘矩形 (bbox 外弃);
        margin 随路径长放大 (绕行空间, T4-r6 实测 m=3 时 A* 借道无障碍区被终检拒)"""
        m = max(3.0, 0.7 * _m6.hypot(x1_ - x0_, y1_ - y0_))
        obs = []
        for qx, qy, qnet, _np6, _qr, qhw, qhh in ALL_PADS:
            if qnet == net or not qnet:
                continue
            if x0_ - m - qhw <= qx <= x1_ + m + qhw and y0_ - m - qhh <= qy <= y1_ + m + qhh:
                obs.append(("P", qx, qy, qhw, qhh))
        for tr in board.GetTracks():
            tn = tr.GetNetname()
            if tn == net or not tn:
                continue
            if tr.GetClass() == "PCB_VIA":
                q = tr.GetPosition()
                vx_, vy_ = pcbnew.ToMM(q.x), pcbnew.ToMM(q.y)
                if x0_ - m <= vx_ <= x1_ + m and y0_ - m <= vy_ <= y1_ + m:
                    obs.append(("V", vx_, vy_))
            elif tr.GetLayer() == layer and tr.GetClass() == "PCB_TRACK":
                s, e = tr.GetStart(), tr.GetEnd()
                tx, ty, ux, uy = pcbnew.ToMM(s.x), pcbnew.ToMM(s.y), pcbnew.ToMM(e.x), pcbnew.ToMM(e.y)
                if max(tx, ux) < x0_ - m or min(tx, ux) > x1_ + m or max(ty, uy) < y0_ - m or min(ty, uy) > y1_ + m:
                    continue
                obs.append(("T", tx, ty, ux, uy, pcbnew.ToMM(tr.GetWidth()) / 2))
        return obs

    def _cell_ok6(px, py, qx, qy, obs, hw):
        """微线段 (px,py)-(qx,qy) vs 障碍表"""
        for o in obs:
            if o[0] == "V":
                if _pd_seg(o[1], o[2], px, py, qx, qy) < 0.35 + hw + 0.2:
                    return False
            elif o[0] == "P":
                dx = max(abs((px + qx) / 2 - o[1]) - o[3], 0.0)
                dy = max(abs((py + qy) / 2 - o[2]) - o[4], 0.0)
                if _m6.hypot(dx, dy) < hw + 0.21:
                    return False
                for sx_, sy_ in ((px, py), (qx, qy)):
                    dx = max(abs(sx_ - o[1]) - o[3], 0.0)
                    dy = max(abs(sy_ - o[2]) - o[4], 0.0)
                    if _m6.hypot(dx, dy) < hw + 0.21:
                        return False
            else:
                for sx_, sy_ in ((px, py), (qx, qy), ((px + qx) / 2, (py + qy) / 2)):
                    if _pd_seg(sx_, sy_, o[1], o[2], o[3], o[4]) < o[5] + hw + 0.21:
                        return False
        return True

    def _astar6(net, src, dst, layer, w=0.25):
        """0.25mm 栅格 A*: 障碍=区域障碍表; 返回折线或 None"""
        P = 0.25
        obs = _obst6(net, min(src[0], dst[0]), min(src[1], dst[1]),
                     max(src[0], dst[0]), max(src[1], dst[1]), layer)
        hw = w / 2
        def cell(x, y):
            return (round((x - 0.55) / P), round((y - 0.55) / P))
        sc, dc = cell(*src), cell(*dst)
        if sc == dc:
            return [src, dst]
        open_ = [(0.0, sc)]
        came = {}
        gsc = {sc: 0.0}
        def h(c):
            return (abs(c[0] - dc[0]) + abs(c[1] - dc[1])) * P
        while open_:
            _, cur = _hq.heappop(open_)
            if cur == dc:
                path = [cur]
                while path[-1] in came:
                    path.append(came[path[-1]])
                path.reverse()
                pts = [(0.55 + c[0] * P, 0.55 + c[1] * P) for c in path]
                pts[0], pts[-1] = src, dst
                simp = [pts[0]]
                for i in range(1, len(pts) - 1):
                    a, b, c = simp[-1], pts[i], pts[i + 1]
                    if (b[0] - a[0]) * (c[1] - b[1]) != (b[1] - a[1]) * (c[0] - b[0]):
                        simp.append(b)
                simp.append(pts[-1])
                return simp
            cx, cy = cur
            for nb in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                if nb in gsc and gsc[nb] <= gsc[cur] + P:
                    continue
                px, py = 0.55 + nb[0] * P, 0.55 + nb[1] * P
                if not (0.55 <= px <= 99.45 and 0.55 <= py <= 79.45):
                    continue
                ppx, ppy = 0.55 + cx * P, 0.55 + cy * P
                if not _cell_ok6(ppx, ppy, px, py, obs, hw):
                    continue
                ng = gsc[cur] + P
                if ng < gsc.get(nb, 1e9):
                    gsc[nb] = ng
                    came[nb] = cur
                    _hq.heappush(open_, (ng + h(nb), nb))
        return None

    def _auto6(net, via_from, via_to, layer, w=0.25, tag="", src=None, dst=None):
        """双孔 + A* 寻路 (孔/端点均可传 None; src/dst 缺省取孔位)"""
        s6 = src or via_from
        d6 = dst or via_to
        if not s6 or not d6:
            print(f"[stage6] {tag} 缺端点")
            return False
        if via_from and not _ok_via(*via_from, net):
            print(f"[stage6] {tag} 起点孔受阻")
            return False
        if via_to and not _ok_via(*via_to, net):
            print(f"[stage6] {tag} 终点孔受阻")
            return False
        if via_from:
            _add_via6(*via_from, net)
        if via_to:
            _add_via6(*via_to, net)
        p = _astar6(net, s6, d6, layer, w)
        if p and _ok_route(net, p, layer, w):
            track(net, p, width=w, layer=layer)
            return True
        print(f"[stage6] {tag} A* 未果")
        return False

    # ---- (a) 同点异层补孔 (F 端与 In1/B 端坐标重合, 只差一颗孔) ----
    _CO_INC = [("S1_SCL", 62.72, 31.78),
               ("S3_SCL", 77.15, 48.85), ("GATE8", 81.16, 58.12),
               ("BOOT", 21.70, 45.40)]
    _nv6 = 0
    for _n6, _x6, _y6 in _CO_INC:
        if _ok_via(_x6, _y6, _n6):
            _add_via6(_x6, _y6, _n6)
            _nv6 += 1
        else:
            print(f"[stage6] 同点孔受阻 {_n6}@({_x6},{_y6})")
    print(f"[stage6] 同点补孔 {_nv6}")

    # S1_SDA 补: 孔@F 西端 (60,29.25) + In1 绕到同网竖线 (62.11,34.90 链)
    if _ok_via(60.00, 29.25, "S1_SDA"):
        _add_via6(60.00, 29.25, "S1_SDA")
        _auto6("S1_SDA", (60.00, 29.25), None, pcbnew.In1_Cu, 0.25, "S1_SDA-west", dst=(62.11, 33.00))
    # BOOT 补: 孔@F 簇枢纽 (23.09,46.43) + B.Cu 绕 S2_SCL 竖带到既有孔 (22.80,28.92)
    if _ok_via(23.09, 46.43, "BOOT"):
        _add_via6(23.09, 46.43, "BOOT")
        _apply("BOOT", [(23.09, 46.43), (24.70, 45.30), (24.70, 29.40), (22.80, 28.92)], pcbnew.In1_Cu, 0.25, "BOOT-I1")

    # ---- (b) BTN_USER: 孔@F端(46.82,33.16) + In1 jog 至 (48.75,33.16) ----
    if _ok_via(46.82, 33.16, "BTN_USER"):
        _add_via6(46.82, 33.16, "BTN_USER")
        _apply("BTN_USER", [(46.82, 33.16), (48.75, 33.16)], pcbnew.In1_Cu, 0.25, "jog")

    # ---- (c) S3_SCL A→B: 孔@A端 + In1 L 到 (76.46,48.15) 孔 ----
    if _ok_via(64.95, 38.63, "S3_SCL"):
        _add_via6(64.95, 38.63, "S3_SCL")
        if _ok_via(76.46, 48.15, "S3_SCL"):
            _add_via6(76.46, 48.15, "S3_SCL")
            _apply("S3_SCL", [(64.95, 38.63), (76.46, 38.63), (76.46, 48.15)], pcbnew.In1_Cu, 0.25, "A-B")

    # ---- (d) I2C_SDA U2 侧 → R8/R9 侧: 双孔 + In1 斜线 (与 SCL In1 斜线平行 ~2mm) ----
    if _ok_via(70.58, 39.80, "I2C_SDA") and _ok_via(54.42, 25.07, "I2C_SDA"):
        _add_via6(70.58, 39.80, "I2C_SDA")
        _add_via6(54.42, 25.07, "I2C_SDA")
        _apply("I2C_SDA", [(70.58, 39.80), (54.42, 25.07)], pcbnew.In1_Cu, 0.25, "U2-pullup")

    # ---- (e) I2C_SCL 两段: U1.20→北簇 B.Cu; TP8 簇→R9.2 B.Cu ----
    if _ok_via(24.10, 26.84, "I2C_SCL") and _ok_via(47.98, 20.73, "I2C_SCL"):
        _add_via6(24.10, 26.84, "I2C_SCL")
        _add_via6(47.98, 20.73, "I2C_SCL")
        _apply("I2C_SCL", [(24.10, 26.84), (24.10, 21.00), (47.98, 21.00), (47.98, 20.73)], pcbnew.B_Cu, 0.25, "U1-north")
    if _ok_via(47.00, 31.50, "I2C_SCL") and _ok_via(57.25, 27.00, "I2C_SCL"):
        _add_via6(47.00, 31.50, "I2C_SCL")
        _add_via6(57.25, 27.00, "I2C_SCL")
        _apply("I2C_SCL", [(47.00, 31.50), (52.00, 31.50), (52.00, 27.00), (57.25, 27.00)], pcbnew.B_Cu, 0.25, "TP8-R9")

    # ---- (f) LED_USER: B.Cu 直连两簇 (32.13,26.67)→(48.41,26.67) ----
    _auto6("LED_USER", None, None, pcbnew.B_Cu, 0.25, "LED_USER-span", src=(32.13, 26.67), dst=(48.41, 28.52))

    # ---- (g) EN 三段 B.Cu ----
    if _ok_via(7.27, 10.62, "EN") and _ok_via(17.02, 16.00, "EN"):
        _add_via6(7.27, 10.62, "EN")
        _add_via6(17.02, 16.00, "EN")
        _auto6("EN", (7.27, 10.62), (17.02, 16.00), pcbnew.B_Cu, 0.25, "EN-SW2")
    if _ok_via(20.30, 9.99, "EN"):
        _add_via6(20.30, 9.99, "EN")
        _auto6("EN", (17.02, 16.00), (20.30, 9.99), pcbnew.B_Cu, 0.25, "EN-U1")
    if _ok_via(22.00, 10.30, "EN") and _ok_via(69.16, 28.12, "EN"):
        _add_via6(22.00, 10.30, "EN")
        _add_via6(69.16, 28.12, "EN")
        _apply("EN", [(22.00, 10.30), (22.00, 7.50), (66.50, 7.50), (66.50, 28.12), (69.16, 28.12)],
               pcbnew.B_Cu, 0.25, "U1-east")

    # ---- (h) IO21: 孔@In1 端 + 孔@F 端 + In1 绕行 (y53.1 让 S1_SCL In1 y52.53) ----
    if _ok_via(39.97, 52.91, "IO21") and _ok_via(75.98, 61.62, "IO21"):
        _add_via6(39.97, 52.91, "IO21")
        _add_via6(75.98, 61.62, "IO21")
        _apply("IO21", [(39.97, 52.91), (39.97, 53.10), (74.50, 53.10), (74.50, 61.62), (75.98, 61.62)],
               pcbnew.In1_Cu, 0.25, "span")

    # ---- (i) J5/J6/J8 3V3 THT: B.Cu 长线 + 入平面孔 ----
    if _ok_via(19.00, 32.00, "+3V3"):
        _add_via6(19.00, 32.00, "+3V3")
        _apply("+3V3", [(5.00, 42.30), (3.20, 42.30), (3.20, 32.00), (19.00, 32.00)], pcbnew.B_Cu, 0.4, "J8")
    if _ok_via(32.00, 55.80, "+3V3"):
        _add_via6(32.00, 55.80, "+3V3")
        _apply("+3V3", [(5.00, 55.80), (32.00, 55.80)], pcbnew.B_Cu, 0.4, "J6")
    if _ok_via(77.20, 51.50, "+3V3"):
        _add_via6(77.20, 51.50, "+3V3")
        _apply("+3V3", [(98.30, 74.00), (98.30, 72.60), (96.00, 72.60), (96.00, 68.00), (77.20, 68.00), (77.20, 51.50)], pcbnew.B_Cu, 0.3, "J5")

    # ---- (j) 电源滞留焊盘: 孔@焊盘近旁 + B.Cu 汇流到最近平面锚孔 ----
    _3R = [(14, 99.5, 0.5, 20), (18, 30, 20, 33.5), (30, 79, 20, 58)]
    _5R = [(3, 14, 13, 36), (14, 36, 33.5, 55), (0.5, 99.5, 53, 79.5), (79.5, 99.5, 14, 79.5)]
    _pw_anch = {"+3V3": [], "+5V": []}
    for z6a in board.Zones():
        if z6a.GetIsRuleArea() or z6a.GetNetname() not in _pw_anch or z6a.GetLayer() != pcbnew.In2_Cu:
            continue
        for tr in board.GetTracks():
            if tr.GetClass() == "PCB_VIA" and tr.GetNetname() == z6a.GetNetname():
                q = tr.GetPosition()
                x, y = pcbnew.ToMM(q.x), pcbnew.ToMM(q.y)
                if z6a.HitTestFilledArea(pcbnew.In2_Cu, pcbnew.VECTOR2I(int(MM(x)), int(MM(y)))):
                    _pw_anch[tr.GetNetname()].append((x, y))
    _STRANDS = [("R31", "1", "+3V3"), ("R36", "1", "+3V3"), ("LED4", "1", "+3V3"),
                ("LED5", "1", "+3V3"), ("C9", "1", "+3V3"), ("U2", "24", "+3V3"),
                ("U3", "2", "+5V"), ("U7", "5", "+5V")]
    _npw = 0
    for _ref6, _pn6, _nn6 in _STRANDS:
        if _ref6 not in FP:
            continue
        _p6 = FP[_ref6].FindPadByNumber(_pn6)
        if _p6 is None or _p6.GetNetname() != _nn6:
            continue
        _q6 = _p6.GetPosition()
        _px6, _py6 = pcbnew.ToMM(_q6.x), pcbnew.ToMM(_q6.y)
        _spot6 = None
        if _ok_via(_px6, _py6, _nn6):
            _spot6 = (_px6, _py6)
        else:
            for _rr6 in (0.9, 1.3, 1.8, 2.4, 3.0):
                for _a6 in range(0, 360, 15):
                    _vx6 = _px6 + _rr6 * _m6.cos(_m6.radians(_a6))
                    _vy6 = _py6 + _rr6 * _m6.sin(_m6.radians(_a6))
                    if _ok_via(_vx6, _vy6, _nn6):
                        _spot6 = (_vx6, _vy6)
                        break
                if _spot6:
                    break
        if not _spot6:
            print(f"[stage6] {_ref6}.{_pn6} 无孔位")
            continue
        _best6 = None
        for _ax6, _ay6 in _pw_anch.get(_nn6, []):
            _d6 = _m6.hypot(_ax6 - _spot6[0], _ay6 - _spot6[1])
            if _best6 is None or _d6 < _best6[0]:
                _best6 = (_d6, _ax6, _ay6)
        if _best6 is None:
            print(f"[stage6] {_nn6} 无平面锚")
            continue
        _add_via6(_spot6[0], _spot6[1], _nn6)
        if _spot6[0] == _best6[1] or _spot6[1] == _best6[2]:
            _pts6 = [_spot6, (_best6[1], _best6[2])]
        else:
            _pts6 = [_spot6, (_spot6[0], _best6[2]), (_best6[1], _best6[2])]
        if _auto6(_nn6, None, None, pcbnew.B_Cu, 0.25, _ref6, src=_spot6, dst=_best6[1:3]):
            _apply(_nn6, [(_px6, _py6), _spot6], pcbnew.F_Cu, 0.3, _ref6 + "-esc")
            _npw += 1
    print(f"[stage6] 电源滞留 B.Cu 汇流 {_npw}")

    # U4.7 专用: 北向孔 (RTS 走线东/南包围) + B.Cu 汇流
    if _ok_via(75.50, 17.30, "+3V3"):
        _add_via6(75.50, 17.30, "+3V3")
        _apply("+3V3", [(75.50, 18.75), (75.50, 17.30)], pcbnew.F_Cu, 0.3, "U4-esc")
        _best6 = min(_pw_anch["+3V3"], key=lambda a6: _m6.hypot(a6[0] - 75.5, a6[1] - 17.3)) if _pw_anch["+3V3"] else None
        if _best6:
            _apply("+3V3", [(75.50, 17.30), (75.50, _best6[1]), _best6], pcbnew.B_Cu, 0.3, "U4-bus")

    # ---- (k) GND F.Cu 孤岛系锚 ----
    def _pip6(x, y, xs, ys):
        n_, ins = len(xs), False
        j_ = n_ - 1
        for i_ in range(n_):
            if (ys[i_] > y) != (ys[j_] > y) and x < (xs[j_] - xs[i_]) * (y - ys[i_]) / (ys[j_] - ys[i_] + 1e-12) + xs[i_]:
                ins = not ins
            j_ = i_
        return ins

    _gpts6 = []
    for t6 in board.GetTracks():
        if t6.GetClass() == "PCB_VIA" and t6.GetNetname() == "GND":
            q6 = t6.GetPosition()
            _gpts6.append((pcbnew.ToMM(q6.x), pcbnew.ToMM(q6.y)))
    _nis6 = 0
    for z6 in board.Zones():
        if z6.GetIsRuleArea() or z6.GetNetname() != "GND" or z6.GetLayer() != pcbnew.F_Cu:
            continue
        try:
            polys6 = z6.GetFilledPolysList(pcbnew.F_Cu)
        except Exception:
            continue
        for i6 in range(polys6.OutlineCount()):
            ch6 = polys6.Outline(i6)
            xs6 = [pcbnew.ToMM(ch6.CPoint(k).x) for k in range(ch6.PointCount())]
            ys6 = [pcbnew.ToMM(ch6.CPoint(k).y) for k in range(ch6.PointCount())]
            if (max(xs6) - min(xs6)) * (max(ys6) - min(ys6)) < 1.0:
                continue
            if any(_pip6(x, y, xs6, ys6) for x, y in _gpts6):
                continue
            done6 = False
            for kx6 in range(2, 9):
                for ky6 in range(2, 9):
                    gx6 = min(xs6) + (max(xs6) - min(xs6)) * kx6 / 9.0
                    gy6 = min(ys6) + (max(ys6) - min(ys6)) * ky6 / 9.0
                    if not _pip6(gx6, gy6, xs6, ys6):
                        continue
                    pt6 = pcbnew.VECTOR2I(int(MM(gx6)), int(MM(gy6)))
                    if not z6.HitTestFilledArea(pcbnew.F_Cu, pt6):
                        continue
                    if _ok_via(gx6, gy6, "GND"):
                        _add_via6(gx6, gy6, "GND")
                        _gpts6.append((gx6, gy6))
                        _nis6 += 1
                        done6 = True
                        break
                if done6:
                    break
    print(f"[stage6] GND 孤岛系锚 {_nis6}")

    # ---- (l) 微缺口补跳: 同网同层端点对距 0.28-0.55 (段端头差一线之隔) ----
    _mg = 0
    _ends6 = {}
    for tr in board.GetTracks():
        if tr.GetClass() != "PCB_TRACK" or not tr.GetNetname() or tr.GetNetname() in ("GND", "+3V3", "+5V"):
            continue
        s, e = tr.GetStart(), tr.GetEnd()
        for ptx, pty in ((pcbnew.ToMM(s.x), pcbnew.ToMM(s.y)), (pcbnew.ToMM(e.x), pcbnew.ToMM(e.y))):
            _ends6.setdefault((tr.GetNetname(), tr.GetLayer()), []).append((ptx, pty))
    for (nn6, ll6), ends6 in _ends6.items():
        seen6 = set()
        for i6 in range(len(ends6)):
            for j6 in range(i6 + 1, len(ends6)):
                ax6, ay6 = ends6[i6]
                bx6, by6 = ends6[j6]
                d6 = _m6.hypot(ax6 - bx6, ay6 - by6)
                if not (0.05 < d6 < 0.52):
                    continue
                key6 = (round((ax6 + bx6) / 2, 1), round((ay6 + by6) / 2, 1))
                if key6 in seen6:
                    continue
                seen6.add(key6)
                track(nn6, [(ax6, ay6), (bx6, by6)], width=0.2, layer=ll6)
                _mg += 1
    print(f"[stage6] 微缺口跳线 {_mg}")

    # ---- (m) U2.21 GND 逃逸: A* F.Cu 到最近 GND 平面孔 ----
    _ganch6 = []
    for tr in board.GetTracks():
        if tr.GetClass() == "PCB_VIA" and tr.GetNetname() == "GND":
            q = tr.GetPosition()
            _ganch6.append((pcbnew.ToMM(q.x), pcbnew.ToMM(q.y)))
    if _ganch6:
        _b6 = min(_ganch6, key=lambda a6: _m6.hypot(a6[0] - 71.9, a6[1] - 41.0))
        if _m6.hypot(_b6[0] - 71.9, _b6[1] - 41.0) < 12:
            _auto6("GND", None, None, pcbnew.F_Cu, 0.25, "U2.21-esc", src=(71.9, 41.0), dst=_b6)

    # ---- (n) 跨层同网端点重合/近失补孔 (F↔In1/B 差 0-0.6mm) ----
    _cn = 0
    _fe6, _ibe6 = [], []
    for tr in board.GetTracks():
        if tr.GetClass() != "PCB_TRACK" or not tr.GetNetname() or tr.GetNetname() in ("GND", "+3V3", "+5V"):
            continue
        s, e = tr.GetStart(), tr.GetEnd()
        for ptx, pty in ((pcbnew.ToMM(s.x), pcbnew.ToMM(s.y)), (pcbnew.ToMM(e.x), pcbnew.ToMM(e.y))):
            if tr.GetLayer() == pcbnew.F_Cu:
                _fe6.append((tr.GetNetname(), ptx, pty))
            elif tr.GetLayer() != pcbnew.In2_Cu:
                _ibe6.append((tr.GetNetname(), ptx, pty, tr.GetLayer()))
    _vp6 = []
    for tr in board.GetTracks():
        if tr.GetClass() == "PCB_VIA":
            q = tr.GetPosition()
            _vp6.append((pcbnew.ToMM(q.x), pcbnew.ToMM(q.y)))
    for nn6, fx6, fy6 in _fe6:
        for bn6, bx6, by6, bl6 in _ibe6:
            if bn6 != nn6:
                continue
            d6 = _m6.hypot(fx6 - bx6, fy6 - by6)
            if d6 > 0.6 or any(_m6.hypot(fx6 - ux6, fy6 - uy6) < 0.55 for ux6, uy6 in _vp6):
                continue
            if not _ok_via(fx6, fy6, nn6):
                continue
            _add_via6(fx6, fy6, nn6)
            _vp6.append((fx6, fy6))
            if d6 > 0.4:
                track(nn6, [(fx6, fy6), (bx6, by6)], width=0.2, layer=bl6)
            _cn += 1
            break
    print(f"[stage6] 跨层端点补孔 {_cn}")

    _run_tail()
    sys.exit(0)

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

    # GND 缝合过孔网格 (避开天线净空 x20.5-35.5/y<6.4)。
    # round5 后 freerouting 信号线常压住整格点 → 网格点被阻时环形搜附近净空
    # (T4-r5 实测不搜索时缝合=0, F 填充与 In1/B 平面失联)
    n_st = 0
    for gx in range(4, 99, 12):
        for gy in range(4, 79, 12):
            if 20 <= gx <= 36 and gy <= 7:
                continue
            spot = None
            if spot_free(gx, gy, "GND"):
                spot = (gx, gy)
            else:
                for rr in (0.9, 1.7, 2.5):
                    for a2 in range(0, 360, 30):
                        cx2 = gx + rr * math.cos(math.radians(a2))
                        cy2 = gy + rr * math.sin(math.radians(a2))
                        if spot_free(cx2, cy2, "GND") and not _via_exists(cx2, cy2, "GND", r=0.8):
                            spot = (cx2, cy2)
                            break
                    if spot:
                        break
            if spot and not _via_exists(spot[0], spot[1], "GND", r=0.5):
                via("GND", *spot)
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
            extra = w / 2 + 0.4
            want2 = ref == "J1" and nname == "+5V"   # VBUS 双过孔分摊
            if _via_exists(px, py, nname, r=1.3):
                continue  # 幂等: 该焊盘已打过孔
            spots = []
            used = []
            for _try in range(2 if want2 else 1):
                best = None
                for ang in range(0, 360, 10):
                    for dist in (1.5, 2.1, 2.7, 3.3, 4.2, 5.5, 6.5, 8.0, 9.5, 11.0):
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

_run_tail()
