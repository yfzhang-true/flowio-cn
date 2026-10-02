# -*- coding: utf-8 -*-
"""FLOWIO-P1 数字孪生网格 — S3 爆炸视图全套 STL + assembly.json.

运行: E:/FreeCAD/bin/FreeCADCmd.exe hardware/flowio-p1/enclosure/make_meshes.py
输出: firmware/twin/meshes/{case_bottom,case_top,pcb,parts_f,parts_b}.stl + assembly.json

坐标系: 壳坐标系(底壳原点)。板原点在壳内 (OX, OX)=(2.9,2.9), 板底面 z=WALL=2.4。
器件坐标映射 (KiCad pos -> 板坐标, 板外沿 X:0-90 Y:0-75):
    x = PosX,  y = -PosY
经 J10 端子 (6.5,-68.5)->(6.5,68.5) 与 J2 USB-C (86,-6)->(86,6) 验证;
"-PosY+75" 翻转假设被证伪 (会给 143.5/81), 故弃用。
"""
import csv
import json
import shutil
import struct
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import FreeCAD as App
import Mesh
import MeshPart
import Part

ROOT = Path(__file__).resolve().parents[3]
ENCL = ROOT / "hardware" / "flowio-p1" / "enclosure"
POSCSV = ROOT / "hardware" / "flowio-p1" / "fab" / "flowio-p1-pos.csv"
OUT = ROOT / "firmware" / "twin" / "meshes"

# ---------- 装配常量 (与 make_case.py 一致) ----------
BOARD_W, BOARD_D, BOARD_T = 90.0, 75.0, 1.6   # P1 板
WALL = 2.4                                     # 壁厚 = 板底面 z
OX = 2.9                                       # WALL+CLR: 板原点在壳内偏移

# Package 关键字 -> (w, d, h) mm
H = {
    "CONN-TH_2P": (11.6, 11.0, 11.0),
    "TYPE-C":     (8.0, 10.3, 3.2),
    "WROOM":      (18.0, 25.5, 3.1),
    "XH":         (6.5, 13.3, 8.5),
    "CONN-TH_4P": (13.3, 6.5, 8.5),
    "SOT-23":     (2.9, 2.4, 1.2),
    "C_0603":     (1.6, 0.8, 0.9),
    "C1206":      (3.2, 1.6, 0.8),
    "C_1206":     (3.2, 1.6, 6.5),
    "SOP":        (4.9, 3.9, 1.75),
    "MSOP":       (3.0, 5.0, 1.1),
    "CDRH":       (10.0, 10.0, 4.0),
    "DC005":      (10.9, 15.6, 7.0),
    "TestPoint":  (1.0, 1.0, 0.5),
    "R0603":      (1.6, 0.8, 0.6),
    "SMA":        (4.3, 2.6, 1.1),
    "SW-SMD":     (6.1, 3.8, 2.0),
}
# BOM 实际封装的别名 -> H 条目 (L1 电感 10.2x10 / U3 SOIC-8)
ALIAS = {"IND-SMD": "CDRH", "SOIC": "SOP"}
KEYWORDS = [(k, H[k]) for k in H] + [(a, H[b]) for a, b in ALIAS.items()]
DEFAULT = (2.2, 2.2, 1.5)


def dims_for(pkg):
    for k, d in KEYWORDS:
        if k in pkg:
            return d
    return DEFAULT


def load_pos():
    parts = []
    with open(POSCSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            ref = (row["Ref"] or "").strip()
            if ref.upper().startswith("H"):   # 安装孔 HA..HD 不建模
                continue
            parts.append({
                "ref": ref,
                "pkg": (row["Package"] or "").strip(),
                "x": float(row["PosX"]),
                "y": float(row["PosY"]),
                "rot": float(row["Rot"]),
                "side": (row["Side"] or "").strip().lower(),
            })
    return parts


def verify_mapping(parts):
    """已知器件校验 pos.csv -> 板坐标映射, 定稿后供建模使用."""
    refs = {p["ref"]: p for p in parts}
    checks = [("J10", 6.5, 68.5), ("J2", 86.0, 6.0), ("J1", 5.5, 27.0)]
    for ref, ex, ey in checks:
        p = refs[ref]
        x, y = p["x"], -p["y"]
        ok = abs(x - ex) < 0.01 and abs(y - ey) < 0.01
        print("[map] %s %-28s pos=(%.1f,%.1f) -> board=(%.1f,%.1f) expect=(%.1f,%.1f) %s"
              % (ref, p["pkg"][:28], p["x"], p["y"], x, y, ex, ey, "OK" if ok else "FAIL"))
        assert ok, "Y mapping verification failed for %s" % ref
    print("[map] mapping FIXED: x=PosX, y=-PosY ('-PosY+75' rejected by J10/J2 checks)")


def part_box(p):
    """单器件盒体, 已变换到壳坐标系."""
    w, d, h = dims_for(p["pkg"])
    if int(round(p["rot"])) % 180 == 90:   # 90 度旋转交换 w/d
        w, d = d, w
    cx, cy = p["x"] + OX, -p["y"] + OX     # 板坐标 + 壳偏移
    if p["side"] == "top":
        z = WALL + BOARD_T                 # 底 z = 4.0 向上
    else:
        z = WALL - h                        # 自板底面向下
    return Part.makeBox(w, d, h, App.Vector(cx - w / 2.0, cy - d / 2.0, z))


def mesh_and_write(shape, path):
    m = MeshPart.meshFromShape(Shape=shape, LinearDeflection=0.4, AngularDeflection=0.5)
    m.write(str(path))
    return m


def check_mesh(name, m, require_facets=True):
    facets = m.CountFacets
    solid = m.isSolid()
    print("[mesh] %-16s facets=%-6d isSolid=%s" % (name, facets, solid))
    assert facets > 0 or not require_facets, "%s: no facets" % name
    if facets > 0:
        assert solid, "%s: mesh not solid" % name
    return facets


def write_empty_stl(path):
    """空二进制 STL (84 字节): BOM 无底面器件时的 parts_b 占位."""
    path.write_bytes(b"FLOWIO empty parts_b (no bottom-side components)".ljust(80, b"\0")[:80]
                     + struct.pack("<I", 0))


def main():
    OUT.mkdir(parents=True, exist_ok=True)

    # 1. 壳 STL 复制改名 (壳本身已是壳坐标系)
    shutil.copyfile(ENCL / "case-bottom.stl", OUT / "case_bottom.stl")
    shutil.copyfile(ENCL / "case-top.stl", OUT / "case_top.stl")

    # 2. 坐标映射校验
    parts = load_pos()
    verify_mapping(parts)
    tops = [p for p in parts if p["side"] == "top"]
    bots = [p for p in parts if p["side"] != "top"]
    print("[pos] %d components (%d top / %d bottom), mounting holes skipped"
          % (len(parts), len(tops), len(bots)))

    # 3. PCB (壳坐标系: 原点 (2.9,2.9), 底面 z=2.4, 厚 1.6)
    pcb_shape = Part.makeBox(BOARD_W, BOARD_D, BOARD_T, App.Vector(OX, OX, WALL))

    # 4. 器件阵
    if tops:
        m_f = mesh_and_write(Part.makeCompound([part_box(p) for p in tops]), OUT / "parts_f.stl")
        check_mesh("parts_f.stl", m_f)
    else:
        write_empty_stl(OUT / "parts_f.stl")
        print("[mesh] parts_f.stl         empty (no top-side parts)")
    if bots:
        m_b = mesh_and_write(Part.makeCompound([part_box(p) for p in bots]), OUT / "parts_b.stl")
        check_mesh("parts_b.stl", m_b)
    else:
        write_empty_stl(OUT / "parts_b.stl")
        print("[mesh] parts_b.stl         empty (no bottom-side parts in BOM)")

    # 5. PCB 网格 + 壳网格校验
    m_pcb = mesh_and_write(pcb_shape, OUT / "pcb.stl")
    check_mesh("pcb.stl", m_pcb)
    check_mesh("case_bottom.stl", Mesh.Mesh(str(OUT / "case_bottom.stl")))
    check_mesh("case_top.stl", Mesh.Mesh(str(OUT / "case_top.stl")))

    # 6. assembly.json (爆炸向量/颜色/包围盒)
    assembly = {
        "units": "mm",
        "frame": "case (bottom shell at origin; board inset 2.9 XY, board underside z=2.4)",
        "bbox": [95.8, 80.8, 19.0],
        "note": "M3×2 自攻入下壳铜柱; via-in-pad 已塞孔(见 fab README)",
        "parts": [
            {"name": "case_top",    "file": "case_top.stl",    "explode": [0, 0, 28],  "color": "#9e9e9e"},
            {"name": "parts_f",     "file": "parts_f.stl",     "explode": [0, 0, 12],  "color": "#c62828"},
            {"name": "pcb",         "file": "pcb.stl",         "explode": [0, 0, 0],   "color": "#0d6b3f"},
            {"name": "parts_b",     "file": "parts_b.stl",     "explode": [0, 0, -8],  "color": "#1565c0"},
            {"name": "case_bottom", "file": "case_bottom.stl", "explode": [0, 0, -16], "color": "#757575"},
        ],
    }
    (OUT / "assembly.json").write_bytes(json.dumps(assembly, ensure_ascii=False, indent=2).encode("utf-8"))
    print("[out] assembly.json written ->", OUT / "assembly.json")
    print("MESHES OK: 6 files in", OUT)


main()
