# -*- coding: utf-8 -*-
"""device_geom.py — 器件几何核 (plan T2): OBB / 端口射线 / FCL 碰撞管理.

数据源: devices.json (T1 器件数据层) + flowio-p1-pos.csv (位姿) + case_geom (装配栈).
坐标系: 壳系 (case frame, Z-up); KiCad rot 为 y-down 系 CCW -> 板系( y-up )取 -rot.
运行: tools/venv-cad (需 trimesh/python-fcl); 纯几何部分 (obb/port_ray) 无第三方依赖.
M1 迁移 (2026-10): enclosure/device_geom.py -> flowio/geom/device_geom.py (逻辑零改动,
HERE/ROOT 重解析: ROOT=仓库根, 真值 devices.json 固定读 hardware/flowio-p1/enclosure/)。
"""
import csv
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]        # flowio/geom -> 仓库根
import sys
sys.path.insert(0, str(ROOT))                     # flowio 包 (venv-cad python 免安装)
from flowio.geom import case_geom as G            # noqa: E402

HERE = ROOT / "hardware" / "flowio-p1" / "enclosure"   # 真值/产物目录 (M1 前=脚本目录)
POS = ROOT / "hardware" / "flowio-p1" / "fab" / "flowio-p1-pos.csv"

_DEV = json.loads((HERE / "devices.json").read_text(encoding="utf-8"))["devices"]
_BY_KEYWORD = []            # (keyword, entry); T6 起按关键词长度降序 (最具体优先,
# 与 case_geom._load_device_dims 同策略 — J2 "TYPE-C-6P" 须先于泛词 "TYPE-C" 命中)
for _e in _DEV:
    for _k in _e["pkg_keywords"]:
        _BY_KEYWORD.append((_k, _e))
_BY_KEYWORD.sort(key=lambda t: -len(t[0]))

_POS = {}
for _r in csv.DictReader(open(POS, newline="", encoding="utf-8")):
    _ref = (_r["Ref"] or "").strip()
    if _ref and not _ref.upper().startswith("H"):
        _POS[_ref] = {"pkg": (_r["Package"] or "").strip(), "x": float(_r["PosX"]),
                      "y": -float(_r["PosY"]), "rot": float(_r["Rot"]),
                      "side": (_r["Side"] or "").strip().lower()}


def entry_for_ref(ref):
    for k, e in _BY_KEYWORD:
        if k in _POS[ref]["pkg"]:
            return e
    raise KeyError("devices.json 无匹配条目: %s (%s)" % (ref, _POS[ref]["pkg"]))


def _rot_board(ref):
    """板系(y-up)旋转角(rad) = -KiCad rot."""
    return -math.radians(_POS[ref]["rot"])


def obb(ref):
    """器件定向包围盒 (壳系): dict(center2, axis0, axis1, w, d, z0, z1, h).

    axis0/axis1 为板面内单位正交轴 (任意角, 非 90 度特判); w/d 沿轴长度.
    注: _POS 的 y 已是板系 y-up (-PosY), 进壳系只加 OX, 勿再取负.
    """
    e = entry_for_ref(ref)
    p = _POS[ref]
    th = _rot_board(ref)
    c, s = math.cos(th), math.sin(th)
    cx, cy = p["x"] + G.OX, p["y"] + G.OX
    w, d, h = e["dims"]["w"], e["dims"]["d"], e["dims"]["h"]
    z0 = G.Z_TOP if p["side"] == "top" else G.Z_BOARD - h
    return {"ref": ref, "center": (cx, cy),
            "axis0": (c, s), "axis1": (-s, c),
            "w": w, "d": d, "h": h, "z0": z0, "z1": z0 + h}


def port_ray(ref):
    """端口射线 (壳系): dict(origin=(x,y,z), dir=(dx,dy,0)) — 开口面中心 + 朝向."""
    e = entry_for_ref(ref)
    p = _POS[ref]
    if "port" not in e:
        raise KeyError("%s 无端口语义" % ref)
    th = _rot_board(ref)
    c, s = math.cos(th), math.sin(th)
    lx, ly = e["port"]["dir_local"]
    dx, dy = c * lx - s * ly, s * lx + c * ly          # R(th)·dir_local
    cx, cy = p["x"] + G.OX, p["y"] + G.OX               # 板系 y-up -> 壳系仅加 OX
    lo, hi = e["port"]["exit_z"]
    ex, ey = cx + dx * e["dims"]["d"] / 2.0, cy + dy * e["dims"]["d"] / 2.0
    return {"ref": ref, "origin": (ex, ey, G.Z_TOP + (lo + hi) / 2.0), "dir": (dx, dy, 0.0)}


def nearest_wall(ref):
    """器件中心最近壁: ('L'|'R'|'T'|'B', 外法向(板系), 中心到该壁边距 mm)."""
    p = _POS[ref]
    cands = [("L", (-1, 0), p["x"]), ("R", (1, 0), G.BW - p["x"]),
             ("T", (0, -1), p["y"]), ("B", (0, 1), G.BH - p["y"])]
    return min(cands, key=lambda t: t[2])


def dist_to_edge_along(ref, dx, dy):
    """从 (cx,cy) 沿 (dx,dy) 到板矩形边界的距离 (板系, 射线必指向外)."""
    p = _POS[ref]
    x, y = p["x"], p["y"]
    t = float("inf")
    if dx > 1e-9:
        t = min(t, (G.BW - x) / dx)
    if dx < -1e-9:
        t = min(t, (0 - x) / dx)
    if dy > 1e-9:
        t = min(t, (G.BH - y) / dy)
    if dy < -1e-9:
        t = min(t, (0 - y) / dy)
    return t


# ── FCL 碰撞管理 (需 venv-cad) ─────────────────────────────────
def collision_manager(parts=None, with_case=False):
    """装配态 CollisionManager: 全部(或指定)器件盒 + 可选壳 mesh.

    返回 (manager, names); 器件名 = ref, 壳名 = case_bottom/case_top.
    """
    import trimesh
    import numpy as np

    cm = trimesh.collision.CollisionManager()
    names = []
    for ref in (parts if parts is not None else sorted(_POS)):
        try:
            b = obb(ref)
        except KeyError:
            continue
        if b["z0"] < G.Z_FLOOR - 0.01:               # 底面件暂不注册 (BOM 无)
            continue
        box = trimesh.creation.box(extents=[b["w"], b["d"], b["h"]])
        th = _rot_board(ref)
        c, s = math.cos(th), math.sin(th)
        T = trimesh.transformations.rotation_matrix(th, [0, 0, 1])
        T[:3, 3] = [b["center"][0], b["center"][1], b["z0"] + b["h"] / 2.0]
        cm.add_object(ref, box, transform=T)
        names.append(ref)
    if with_case:
        mesh_dir = ROOT / "firmware" / "twin" / "meshes"
        for nm in ("case_bottom", "case_top"):
            m = trimesh.load_mesh(str(mesh_dir / (nm + ".stl")))
            cm.add_object(nm, m)
            names.append(nm)
    return cm, names


def explode_transform(ref, k):
    """爆炸态位姿: 装配位 + k*explode 向量 (case_geom.EXPLODE, 仅部件级)."""
    import trimesh
    b = obb(ref)
    th = _rot_board(ref)
    T = trimesh.transformations.rotation_matrix(th, [0, 0, 1])
    ex = (0.0, 0.0, 0.0)
    for pid, vec in G.EXPLODE.items():
        if ref.startswith(pid.rstrip("_F")) or pid == ref:
            ex = tuple(vec)
            break
    T[:3, 3] = [b["center"][0] + k * ex[0], b["center"][1] + k * ex[1],
                b["z0"] + b["h"] / 2.0 + k * ex[2]]
    return T


PART_GROUPS = {"case_top": [], "parts_F": [r for r in _POS], "pcb": [], "case_bottom": []}
