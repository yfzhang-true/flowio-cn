# -*- coding: utf-8 -*-
"""netgraph: 铜连通性分析 (cleanup_pipeline 思路: sweep_dead_ends 前的侦察).
输出每网的连通分量; 含焊盘的分量=活, 纯走线悬桩=死."""
import sys, math
sys.path.insert(0, "tools")
import pcbnew, boardgeom as G

TOL = 0.05          # 触碰判定容差 mm

def analyze():
    b = pcbnew.LoadBoard(G.BF)
    items = []   # (kind, id, net, layer, geom, has_pad_ref)
    pads_by_net = {}
    for f in b.GetFootprints():
        for p in f.Pads():
            c = p.GetPosition()
            e = dict(kind="pad", net=p.GetNetname(), layer=None, ref=f.GetReference()+"."+str(p.GetPadName()),
                     x=G.MM(c.x), y=G.MM(c.y), r=max(G.MM(p.GetSize().x), G.MM(p.GetSize().y))/2, obj=p)
            items.append(e)
    for t in b.GetTracks():
        if t.Type() == pcbnew.PCB_VIA_T:
            c = t.GetPosition()
            items.append(dict(kind="via", net=t.GetNetname(), layer=None, ref="via",
                              x=G.MM(c.x), y=G.MM(c.y), r=G.MM(t.GetWidth(pcbnew.F_Cu))/2, obj=t))
        else:
            s, e = t.GetStart(), t.GetEnd()
            items.append(dict(kind="trk", net=t.GetNetname(), layer=t.GetLayer(), ref="trk",
                              ax=G.MM(s.x), ay=G.MM(s.y), bx=G.MM(e.x), by=G.MM(e.y),
                              w=G.MM(t.GetWidth()), obj=t))
    # union-find
    parent = list(range(len(items)))
    def find(i):
        while parent[i] != i: parent[i] = parent[parent[i]]; i = parent[i]
        return i
    def union(i, j):
        ri, rj = find(i), find(j)
        if ri != rj: parent[ri] = rj
    def pt_on_item(x, y, it):
        if it["kind"] == "trk":
            return G.seg_dist(x, y, it["ax"], it["ay"], it["bx"], it["by"]) <= it["w"]/2 + TOL
        return math.hypot(x-it["x"], y-it["y"]) <= it["r"] + TOL
    # 空间桶加速
    by_net = {}
    for i, it in enumerate(items): by_net.setdefault(it["net"], []).append(i)
    for net, idxs in by_net.items():
        for a in range(len(idxs)):
            for bidx in range(a+1, len(idxs)):
                ia, ib = idxs[a], idxs[bidx]
                A, B = items[ia], items[ib]
                if A["kind"] == "trk" and B["kind"] == "trk" and A["layer"] != B["layer"]: continue
                # 端点/圆心 触碰对方
                ptsA = [(A["ax"],A["ay"]),(A["bx"],A["by"])] if A["kind"]=="trk" else [(A["x"],A["y"])]
                ptsB = [(B["ax"],B["ay"]),(B["bx"],B["by"])] if B["kind"]=="trk" else [(B["x"],B["y"])]
                touch = any(pt_on_item(px,py,B) for px,py in ptsA) or any(pt_on_item(px,py,A) for px,py in ptsB)
                if touch: union(ia, ib)
    # 分量归类 (zone 填充接触的项视为活: 近似——与 zone 同网的 via/pad 若落在 zone 层范围即算;
    # 更准: 用 HitTestFilledArea; 这里先报告, 活死判定保守——含 pad 即活)
    from collections import defaultdict
    comps = defaultdict(list)
    for i in range(len(items)): comps[find(i)].append(i)
    dead, live = [], []
    for root, members in comps.items():
        nets = {items[m]["net"] for m in members}
        if len(nets) > 1: print("!! 跨网分量(短路?):", nets)
        has_pad = any(items[m]["kind"] == "pad" for m in members)
        (live if has_pad else dead).append(members)
    return b, items, live, dead

if __name__ == "__main__":
    b, items, live, dead = analyze()
    print(f"分量: 活(含焊盘) {len(live)}, 死(无焊盘) {len(dead)}")
    for members in dead:
        for m in members:
            it = items[m]
            if it["kind"] == "trk":
                print(f"  DEAD trk [{it['net']}] L{b.GetLayerName(it['layer'])} ({it['ax']:.2f},{it['ay']:.2f})-({it['bx']:.2f},{it['by']:.2f}) w{it['w']}")
            else:
                print(f"  DEAD {it['kind']} [{it['net']}] @({it['x']:.2f},{it['y']:.2f})")
        print("  ---")
