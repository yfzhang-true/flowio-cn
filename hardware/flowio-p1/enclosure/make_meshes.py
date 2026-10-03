# -*- coding: utf-8 -*-
"""FLOWIO-P1 数字孪生网格 — S3 爆炸视图全套 STL + assembly.json (2026-10-03 装配栈统一).

运行: E:/FreeCAD/bin/python.exe hardware/flowio-p1/enclosure/make_meshes.py
输出: firmware/twin/meshes/{case_bottom,case_top,pcb,parts_f}.stl + assembly.json

坐标系: 壳系 (下壳外角原点, Z-up), 与 scene.js / flows.json 同源, 无任何翻转。
装配栈 (case_geom 单一真相): 板坐铜柱顶 z=Z_BOARD=7.4, 器件基面 z=Z_TOP=9.0。
  旧版错误: 板按"趴腔底 z=2.4"建模 (被铜柱穿透), 19 总高装不下 11mm 端子。
BOM 无底面器件, 故不产出 parts_b.stl, assembly.json 亦不列该件 (旧版列了空件)。
"""
import csv
import json
import shutil
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

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import case_geom as G

ROOT = HERE.parents[2]
POSCSV = ROOT / "hardware" / "flowio-p1" / "fab" / "flowio-p1-pos.csv"
OUT = ROOT / "firmware" / "twin" / "meshes"


def load_pos():
    parts = []
    with open(POSCSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            ref = (row["Ref"] or "").strip()
            if ref.upper().startswith("H"):   # 安装孔不建模 (pos 导出无 H 位, 防御保留)
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
    """锚点校验 pos.csv -> 壳系映射 (case_geom.ANCHORS 黄金值)."""
    refs = {p["ref"]: p for p in parts}
    for ref, px, py, ex, ey in G.ANCHORS:
        p = refs[ref]
        x, y = G.board_to_case(p["x"], p["y"])
        ok = abs(x - ex) < 0.01 and abs(y - ey) < 0.01
        print("[map] %s pos=(%.1f,%.1f) -> case=(%.1f,%.1f) expect=(%.1f,%.1f) %s"
              % (ref, p["x"], p["y"], x, y, ex, ey, "OK" if ok else "FAIL"))
        assert ok, "Y mapping verification failed for %s" % ref
    print("[map] mapping OK: x=PosX+OX, y=-PosY+OX (%d anchors)" % len(G.ANCHORS))


def part_box(p):
    """单器件盒体, 已变换到壳坐标系 (z 基准 = case_geom 装配栈)."""
    w, d, h = G.dims_for(p["pkg"])
    if int(round(p["rot"])) % 180 == 90:   # 90 度旋转交换 w/d
        w, d = d, w
    cx, cy = G.board_to_case(p["x"], p["y"])
    if p["side"] == "top":
        z = G.Z_TOP                        # 9.0 板面起向上
    else:
        z = G.Z_BOARD - h                  # 自板底面向下 (当前 BOM 无底面件)
    return Part.makeBox(w, d, h, App.Vector(cx - w / 2.0, cy - d / 2.0, z))


def mesh_and_write(shape, path):
    m = MeshPart.meshFromShape(Shape=shape, LinearDeflection=0.4, AngularDeflection=0.5)
    m.write(str(path))
    return m


def check_mesh(name, m):
    facets = m.CountFacets
    solid = m.isSolid()
    print("[mesh] %-16s facets=%-6d isSolid=%s" % (name, facets, solid))
    assert facets > 0, "%s: no facets" % name
    assert solid, "%s: mesh not solid" % name
    return facets


def main():
    OUT.mkdir(parents=True, exist_ok=True)

    # 1. 壳 STL 复制改名 (make_case.py 产物, 壳系原生)
    shutil.copyfile(HERE / "case-bottom.stl", OUT / "case_bottom.stl")
    shutil.copyfile(HERE / "case-top.stl", OUT / "case_top.stl")

    # 2. 坐标映射锚点校验
    parts = load_pos()
    verify_mapping(parts)
    tops = [p for p in parts if p["side"] == "top"]
    bots = [p for p in parts if p["side"] != "top"]
    print("[pos] %d components (%d top / %d bottom), mounting holes skipped"
          % (len(parts), len(tops), len(bots)))
    assert not bots, "出现底面器件: 需恢复 parts_b 通道并补 z 语义"

    # 3. PCB (板底 = 铜柱顶 Z_BOARD, 旧版误用 Z_FLOOR=2.4)
    pcb_shape = Part.makeBox(G.BW, G.BH, G.PCB_T, App.Vector(G.OX, G.OX, G.Z_BOARD))

    # 4. 顶面器件阵 (基面 Z_TOP)
    m_f = mesh_and_write(Part.makeCompound([part_box(p) for p in tops]), OUT / "parts_f.stl")
    check_mesh("parts_f.stl", m_f)

    # 5. PCB 网格 + 壳网格校验
    check_mesh("pcb.stl", mesh_and_write(pcb_shape, OUT / "pcb.stl"))
    check_mesh("case_bottom.stl", Mesh.Mesh(str(OUT / "case_bottom.stl")))
    check_mesh("case_top.stl", Mesh.Mesh(str(OUT / "case_top.stl")))

    # 6. 清理旧版遗留的空 parts_b.stl (BOM 无底面器件)
    stale = OUT / "parts_b.stl"
    if stale.exists():
        stale.unlink()
        print("[out] removed stale parts_b.stl (no bottom-side parts)")

    # 7. assembly.json — spec §3.4 契约 (explode/bbox 全部来自 case_geom)
    assembly = {
        "parts": [
            {"id": "case_top",    "name": "上壳(通风栅)",  "stl": "/meshes/case_top.stl",    "color": "#9e9e9e",
             "explode": G.EXPLODE["case_top"],    "opacity": 1.0},
            {"id": "parts_F",     "name": "器件阵-顶面",   "stl": "/meshes/parts_f.stl",     "color": "#c62828",
             "explode": G.EXPLODE["parts_F"],     "opacity": 0.95},
            {"id": "pcb",         "name": "P1 主板",       "stl": "/meshes/pcb.stl",         "color": "#0d6b3f",
             "explode": G.EXPLODE["pcb"],         "opacity": 1.0},
            {"id": "case_bottom", "name": "下壳(铜柱)",   "stl": "/meshes/case_bottom.stl", "color": "#757575",
             "explode": G.EXPLODE["case_bottom"], "opacity": 1.0},
        ],
        "bbox_mm": G.BBOX_MM,
        "assembly_note": "M3 螺丝穿板自攻入下壳铜柱 (板坐铜柱顶 z=7.4)",
    }
    (OUT / "assembly.json").write_bytes(json.dumps(assembly, ensure_ascii=False, indent=2).encode("utf-8"))
    print("[out] assembly.json written -> %s (bbox %s)" % (OUT / "assembly.json", G.BBOX_MM))
    print("MESHES OK: 5 files in", OUT)


main()
