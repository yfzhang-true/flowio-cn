# -*- coding: utf-8 -*-
"""pneu_geom.py — T6 气动结构件共享构建器 (FreeCAD 依赖; 常量全取 case_geom).

单一实现原则: 11 阀盒体/嘴圆柱 与 两点流道管 在 make_manifold (生成器自检) /
make_meshes (孪生 valves.stl) / make_assembly (双体装配) 三处共用, 禁本地复制.
坐标: 壳系 (case_geom 单一真相源).
"""
import os
import sys

import FreeCAD as App
import Part

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import case_geom as G


def valve_solids():
    """11 阀 (体盒 + 嘴圆柱) 壳系绝对坐标; kind: 'D'=F0520D (体 14.5 + 嘴 ⌀3.0),
    'B'=F0520B (体 22 + 嘴 ⌀4.6). 返回 [(x, y, kind, compound)]."""
    solids = []
    for x, y, kind in G.valve_grid():
        is_b = kind == "B"
        bh = G.VB_BODY_H if is_b else G.VD_BODY_H
        nd = (G._PNEU["vb_noz"]) if is_b else G._PNEU["vd_noz"]
        w, d = (G._PNEU["vb_w"], G._PNEU["vb_d"]) if is_b else (G._PNEU["vd_w"], G._PNEU["vd_d"])
        body = Part.makeBox(w, d, bh, App.Vector(x - w / 2, y - d / 2, G.TOWER_Z0))
        noz = Part.makeCylinder(nd / 2, G.NOZZLE_LEN, App.Vector(x, y, G.TOWER_Z0 + bh))
        solids.append((x, y, kind, Part.makeCompound([body, noz])))
    return solids


def tube(x0, y0, z0, x1, y1, z1, d):
    """两点间 ⌀d 圆柱流道 (axis-aligned 或斜线一律两点放样)."""
    p0, p1 = App.Vector(x0, y0, z0), App.Vector(x1, y1, z1)
    return Part.makeCylinder(d / 2, p0.distanceToPoint(p1), p0, p1.sub(p0).normalize())
