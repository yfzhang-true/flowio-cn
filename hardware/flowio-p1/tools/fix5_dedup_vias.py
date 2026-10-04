# -*- coding: utf-8 -*-
# tools/fix5_dedup_vias.py — hole_to_hole 重叠过孔去重 (T5, SWIG 一进程一操作)
# 背景: 布线终态 15 条 hole_to_hole DRC warning = 14 对物理重叠孔 (wall<0,
# freerouting/stitch 撞孔伪影) + 1 对 wall=0.064 — 超 JLC 0.25mm 孔距限值, 且重叠孔
# 会被钻孔 DFM 拒收。处置: 逐对判定"冗余可删"后删除一员 (同网缝合/换层过孔), 不动
# 轨道拓扑不动 PLACE; 被删孔中心的终止端点统一吸附到保留孔中心 (零长轨道随之清除)。
# 判据 (线段+宽度模型): 轨道段到保留孔中心的中心线距离集是区间 [dmin, dmax]
# (连续函数达到最值), 铜径向区间 ≈ [max(0,dmin-w/2), dmax+w/2] (含端帽/侧缘),
# 与环带 [drill/2, w/2] 铜交叠 ≥0.01mm 即保持连接 (同网连通判据, 任意重叠即连通); 整段落在保留孔钻 void 内的
# 碎轨视为钻孔废料不判连通 (物理钻孔后无铜, 本就非连通承担者)。
# 用法: fix5_dedup_vias.py [--report]   (--report 只查不删)
# 守门: 删后另进程跑 check_route (未连须 0) + kicad-cli drc (warning 净减不增)。
import sys

import pcbnew

BF = "flowio-p1.kicad_pcb"
REPORT_ONLY = "--report" in sys.argv
WALL_LIMIT = 0.10          # 处置阈值: 壁距 < 0.10 的对 (远超 JLC 0.25 限)
MM = pcbnew.ToMM

b = pcbnew.LoadBoard(BF)

vias = []      # dict(obj, x, y, drill, w, layers:set, net)
tracks = []    # dict(obj, layer, p1, p2, w)
for t in b.GetTracks():
    tt = t.Type()
    if tt == pcbnew.PCB_VIA_T:
        p = t.GetPosition()
        try:
            w = MM(t.GetWidth(pcbnew.F_Cu))
        except Exception:
            w = MM(t.GetWidth(pcbnew.B_Cu))
        vias.append({"obj": t, "x": MM(p.x), "y": MM(p.y),
                     "drill": MM(t.GetDrill()), "w": w,
                     "layers": set(t.GetLayerSet().Seq()), "net": t.GetNetname()})
    elif tt in (pcbnew.PCB_TRACE_T, pcbnew.PCB_ARC_T):
        s, e = t.GetStart(), t.GetEnd()
        tracks.append({"obj": t, "layer": t.GetLayer(),
                       "p1": (MM(s.x), MM(s.y)), "p2": (MM(e.x), MM(e.y)),
                       "w": MM(t.GetWidth())})


def _d(px, py, v):
    return ((px - v["x"]) ** 2 + (py - v["y"]) ** 2) ** 0.5


def seg_contact(tr, v, m=0.01):
    """轨道段 (p1->p2, 宽 w) 与过孔 v 环带的铜交叠 ≥ m.
    铜径向区间 ≈ [max(0, dmin-w/2), dmax+w/2] (中心线距离集 [dmin,dmax] 外扩半宽,
    端帽/侧缘均覆盖), 与环带 [drill/2, w/2] 交叠长度判定."""
    x1, y1 = tr["p1"]
    x2, y2 = tr["p2"]
    vx, vy = v["x"], v["y"]
    dx, dy = x2 - x1, y2 - y1
    seg2 = dx * dx + dy * dy
    if seg2 < 1e-12:
        dmin = dmax = _d(x1, y1, v)
    else:
        tt = max(0.0, min(1.0, ((vx - x1) * dx + (vy - y1) * dy) / seg2))
        dmin = _d(x1 + tt * dx, y1 + tt * dy, v)
        dmax = max(_d(x1, y1, v), _d(x2, y2, v))
    rc = tr["w"] / 2
    ri, ro = v["drill"] / 2, v["w"] / 2
    return min(dmax + rc, ro) - max(max(0.0, dmin - rc), ri) >= m


def via_terms(v):
    """终止在过孔 v 环缘上的轨道 (端点圆与孔外缘圆交叠)."""
    out = []
    for tr in tracks:
        if tr["layer"] not in v["layers"]:
            continue
        for ex, ey in (tr["p1"], tr["p2"]):
            if _d(ex, ey, v) <= v["w"] / 2 + tr["w"] / 2 + 0.02:
                out.append(tr)
                break
    return out


def removable(a, keeper):
    """删 a 后, a 的每条终止轨道仍与 keeper 保持铜连接 (线段+宽度模型);
    整段落在 keeper 钻孔 void 内的碎轨 (dmax+w/2 < drill/2) 视为钻孔废料不判连通."""
    terms = via_terms(a)
    ri = keeper["drill"] / 2
    for tr in terms:
        dmax = max(_d(*tr["p1"], keeper), _d(*tr["p2"], keeper))
        if dmax + tr["w"] / 2 < ri:
            continue        # 钻孔 void 内碎轨: 物理钻孔后无铜, 不承担连通
        if not seg_contact(tr, keeper):
            return False, terms
    return True, terms

# ── 找 wall < WALL_LIMIT 的对 ─────────────────────────────────────
pairs = []
for i in range(len(vias)):
    for j in range(i + 1, len(vias)):
        a, c = vias[i], vias[j]
        d = _d(a["x"], a["y"], c)
        wall = d - (a["drill"] + c["drill"]) / 2
        if wall < WALL_LIMIT:
            pairs.append((wall, d, a, c))
print("candidate pairs (wall<%.2f): %d" % (WALL_LIMIT, len(pairs)))

dead = set()
keepers = set()
plan = []       # (victim, keep, wall, n_terms)
skipped = []
for wall, d, a, c in sorted(pairs, key=lambda p: p[0]):
    if id(a["obj"]) in dead or id(c["obj"]) in dead:
        continue
    a_ok, a_terms = removable(a, c)
    c_ok, c_terms = removable(c, a)
    # 吸附目标 (keeper) 不得是前对已删孔: 双角色冲突时换向, 都冲突则跳过
    a_bad = id(a["obj"]) in keepers
    c_bad = id(c["obj"]) in keepers
    if a_ok and not a_bad:
        victim, keep, terms = a, c, a_terms
    elif c_ok and not c_bad:
        victim, keep, terms = c, a, c_terms
    else:
        skipped.append((wall, a, c))
        continue
    dead.add(id(victim["obj"]))
    keepers.add(id(keep["obj"]))
    plan.append((victim, keep, wall, len(terms)))

for v, k, wall, n in plan:
    print("DEL (%.3f,%.3f) %s drill=%.2f wall=%+.3f (kept (%.3f,%.3f) terms=%d)"
          % (v["x"], v["y"], v["net"], v["drill"], wall, k["x"], k["y"], n))
for wall, a, c in skipped:
    print("SKIP pair wall=%+.3f (%.3f,%.3f)%s <-> (%.3f,%.3f)%s — 线段模型仍不满足, 需人工"
          % (wall, a["x"], a["y"], a["net"], c["x"], c["y"], c["net"]))

if not REPORT_ONLY and plan:
    kpos = {id(v["obj"]): k for v, k, _, _ in plan}
    snapped = set()
    n_snap = 0
    for tr in tracks:
        for attr in ("p1", "p2"):
            ex, ey = tr[attr]
            for v in vias:
                if id(v["obj"]) not in dead:
                    continue
                if _d(ex, ey, v) <= 0.05:
                    k = kpos[id(v["obj"])]
                    iu = pcbnew.VECTOR2I(pcbnew.FromMM(k["x"]), pcbnew.FromMM(k["y"]))
                    if attr == "p1":
                        tr["obj"].SetStart(iu)
                        tr["p1"] = (k["x"], k["y"])
                    else:
                        tr["obj"].SetEnd(iu)
                        tr["p2"] = (k["x"], k["y"])
                    n_snap += 1
                    snapped.add(id(tr["obj"]))
    # 吸附后零长轨道 (原 A<->B 短接环) 一并清除
    zero_len = []
    for tr in tracks:
        if id(tr["obj"]) in snapped:
            s, e = tr["obj"].GetStart(), tr["obj"].GetEnd()
            if (s.x, s.y) == (e.x, e.y):
                zero_len.append(tr["obj"])
    for tr_obj in zero_len:
        b.Remove(tr_obj)
    for v in vias:
        if id(v["obj"]) in dead:
            b.Remove(v["obj"])
    pcbnew.SaveBoard(BF, b)
    print("SAVED removed_vias=%d snapped_ends=%d zero_len_tracks=%d"
          % (len(plan), n_snap, len(zero_len)))
else:
    print(("REPORT-ONLY" if REPORT_ONLY else "NO-OP") + " del=%d skip=%d"
          % (len(plan), len(skipped)))
