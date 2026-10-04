# -*- coding: utf-8 -*-
"""device_graph.py — 器件关系图 (plan T3): 电气边(网表) + 空间边(端口->槽) + 匹配.

  build_graph()      -> networkx.Graph (节点=ref; 边带 kind=elec/spatial)
  slot_nodes()       -> 21 槽节点 (case_geom CUTS 13 + TERM 8; 角部 relief 为附属几何)
  slots_satisfied()  -> minimum_weight_full_matching (权=端口面中心到槽中心距离)
  flows_crosscheck() -> flows.json 电气拓扑 vs 网表权威源 交叉校验 (plan T3.3)
运行: tools/venv-cad (networkx).
"""
import json
import math
from pathlib import Path

import networkx as nx

HERE = Path(__file__).resolve().parent
import sys
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[0] / "fab"))   # enclosure 上一级 = flowio-p1
import case_geom as G
import netlist as NL

ROOT = HERE.parents[2]
FLOWS = ROOT / "firmware" / "twin" / "webapp" / "flows.json"


def slot_nodes():
    """17 槽: dict(slot_id -> {face, center3(壳系), z_lo, z_hi}).

    槽中心取壁厚中点 + 槽带宽中点; TERM 8 槽在 B 面, 侧槽按 CUTS.
    """
    slots = {}
    for face, pos, w, lo, hi in G.CUTS:
        sid = "%s@%.1f" % (face, pos)
        a = pos + G.OX
        if face == "L":
            c = (G.WALL / 2, a)
        elif face == "R":
            c = (G.OW - G.WALL / 2, a)
        elif face == "T":
            c = (a, G.WALL / 2)
        else:
            c = (a, G.OH - G.WALL / 2)
        slots[sid] = {"face": face, "center3": (c[0], c[1], (lo + hi) / 2),
                      "z_lo": lo, "z_hi": hi}
    tw, lo, hi = G.TERM_SLOT
    for i, x in enumerate(G.TERM_X):
        sid = "B@term%d" % i
        slots[sid] = {"face": "B", "center3": (x + G.OX, G.OH - G.WALL / 2, (lo + hi) / 2),
                      "z_lo": lo, "z_hi": hi}
    return slots


def build_graph():
    import device_geom as DG
    g = nx.Graph()
    for e in NL.electrical_edges():
        a, b = sorted(e)
        if a in DG._POS and b in DG._POS:
            g.add_edge(a, b, kind="elec")
    for ref in DG._POS:
        if not g.has_node(ref):
            g.add_node(ref)
    return g


def slots_satisfied(conn_refs=None, drop_slots=()):
    """器件<->槽 最小权完美匹配; 返回 (ok, matching, diag)."""
    import device_geom as DG
    conns = conn_refs or [r for r in DG._POS
                          if "port" in DG.entry_for_ref(r)]
    slots = {k: v for k, v in slot_nodes().items() if k not in drop_slots}
    B = nx.Graph()
    for ref in conns:
        ray = DG.port_ray(ref)
        for sid, s in slots.items():
            # 权 = 端口面中心到槽中心的欧氏距离 (mm); 仅当端口指向该面时才是低权
            ox, oy, oz = ray["origin"]
            sx, sy, sz = s["center3"]
            wdist = math.dist((ox, oy, oz), (sx, sy, sz))
            B.add_edge(("D", ref), ("S", sid), weight=wdist)
    try:
        m = nx.bipartite.minimum_weight_full_matching(B)
    except ValueError:
        return False, None, "完美匹配不存在 (槽或器件孤点)"
    pairs = {(d[1], s[1]) for d, s in m.items() if d[0] == "D"}
    return len(pairs) == len(conns) == len(slots), pairs, "ok"


def flows_crosscheck():
    """flows.json 的 ELEC 拓扑每对相邻 ref 必须在网表电气边上 (权威源校验)."""
    edges = NL.electrical_edges()
    bad = []
    data = json.loads(FLOWS.read_text(encoding="utf-8"))
    for fl in data.get("elec", []):
        refs = fl.get("refs", [])
        for a, b in zip(refs, refs[1:]):
            if frozenset((a, b)) not in edges:
                bad.append("%s: %s-%s" % (fl.get("id"), a, b))
    return bad


if __name__ == "__main__":
    g = build_graph()
    ok, pairs, diag = slots_satisfied()
    bad = flows_crosscheck()
    print("[graph] nodes=%d elec_edges=%d" % (g.number_of_nodes(), g.number_of_edges()))
    print("[match] 21<->21 %s (%s); 示例 %s" % (ok, diag, list(pairs)[:3] if pairs else "-"))
    print("[flows] 交叉校验违例 %d: %s" % (len(bad), bad[:5]))
