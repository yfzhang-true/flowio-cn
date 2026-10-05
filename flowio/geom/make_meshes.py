# -*- coding: utf-8 -*-
"""FLOWIO-P1 数字孪生网格 — S3 爆炸视图全套 STL + assembly.json (2026-10-03 装配栈统一).

运行: E:/FreeCAD/bin/python.exe flowio/geom/make_meshes.py
输出: firmware/twin/meshes/{case_bottom,case_top,pcb,parts_f}.stl + assembly.json

坐标系: 壳系 (下壳外角原点, Z-up), 与 scene.js / flows.json 同源, 无任何翻转。
装配栈 (case_geom 单一真相): 板坐铜柱顶 z=Z_BOARD=7.4, 器件基面 z=Z_TOP=9.0。
  旧版错误: 板按"趴腔底 z=2.4"建模 (被铜柱穿透), 19 总高装不下 11mm 端子。
BOM 无底面器件, 故不产出 parts_b.stl, assembly.json 亦不列该件 (旧版列了空件)。
M1 迁移 (2026-10): enclosure/make_meshes.py -> flowio/geom/make_meshes.py (逻辑零改动,
HERE/ROOT 语义经包定位重解析: HERE=enclosure 产物源目录, ROOT=仓库根; 落位不变)。
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

ROOT = Path(__file__).resolve().parents[2]        # flowio/geom -> 仓库根
sys.path.insert(0, str(ROOT))                     # flowio 包 (FreeCAD python 免安装)
from flowio.geom import case_geom as G            # noqa: E402
from flowio.geom.pneu_geom import valve_solids, tube   # T6 共享构建器 (单一实现)

HERE = ROOT / "hardware" / "flowio-p1" / "enclosure"   # 产物源目录 (M1 前=脚本目录)
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


def check_mesh(name, m, min_shells=1, closed_required=True):
    """网格健全: 非空 + 壳数下限 + 逐连通壳闭合 (多件合体 STL 如 pump_module 底+盖 /
    valves 11 只按'逐壳闭合'校验 — 合体件 isSolid 必假是语义不是缺陷).
    closed_required=False: float32 STL 往返会把共面融合件的焊接点拆出 1-ULP 缝
    (pump_module 实测 2 闭壳写盘重载变 3 壳 2 开) — 闭合真值以生成器写时断言
    (make_pump_module write_stl / OCC solid isValid) 为准, 此处退守壳数+面数."""
    facets = m.CountFacets
    comps = m.getSeparateComponents()
    all_closed = all(c.isSolid() for c in comps)
    print("[mesh] %-16s facets=%-6d shells=%-3d closed=%s" % (name, facets, len(comps), all_closed))
    assert facets > 0, "%s: no facets" % name
    assert len(comps) >= min_shells, "%s: shells %d < %d" % (name, len(comps), min_shells)
    if closed_required:
        assert all_closed, "%s: 未闭合壳" % name
    return facets


def main():
    OUT.mkdir(parents=True, exist_ok=True)

    # 1. 壳 STL 复制改名 (make_case.py 产物, 壳系原生)
    shutil.copyfile(HERE / "case-bottom.stl", OUT / "case_bottom.stl")
    shutil.copyfile(HERE / "case-top.stl", OUT / "case_top.stl")

    # 1b. T6 气动结构件 STL 复制 (make_manifold / make_pump_module 产物, 壳系绝对坐标)
    for src, dst in (("manifold.stl", "manifold.stl"), ("pump-module.stl", "pump_module.stl"),
                     ("pump.stl", "pump.stl"), ("brackets.stl", "brackets.stl")):
        shutil.copyfile(HERE / src, OUT / dst)

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

    # 4b. T6 阀阵 11 只 (体+嘴, pneu_geom 单一实现 — 与歧管自检同源)
    m_v = mesh_and_write(Part.makeCompound([vs for *_m, vs in valve_solids()]), OUT / "valves.stl")
    check_mesh("valves.stl", m_v, min_shells=22)      # 11 阀 × (体+嘴) 双壳

    # 4c. T6 视觉气管 ×2 (泵模块面板 ↔ 主壳 S/V 壁孔, ⌀5 管视觉件)
    pmx = G.PMOD_OFF[0] + G.PMOD_L - 1.2      # 管端收 1.2: 斜轴圆柱端面圆盘外缘 x=b.x+r√(1-nx²),
                                               # 实测外伸 0.96 (r=2.5, nx≈0.92), 保 BBOX=壳外廓契约
    pmy, pmz = G.PMOD_OFF[1] + G.PMOD_CY, G.PMOD_OFF[2] + G.PUMP_AXIS_Z
    segs = []
    for k, (y_case, dy) in enumerate(((20.4, -G.PMOD_PORT_DY), (31.4, G.PMOD_PORT_DY))):
        a = App.Vector(G.OW, y_case, G.PORT_Z_LOW)
        mid = App.Vector(G.OW + 44.0, y_case, G.PORT_Z_LOW + 3.0)
        b = App.Vector(pmx, pmy + dy, pmz)
        segs.append(tube(a.x, a.y, a.z, mid.x, mid.y, mid.z, 5.0))
        segs.append(tube(mid.x, mid.y, mid.z, b.x, b.y, b.z, 5.0))
        segs.append(Part.makeSphere(2.6, mid))
    m_t = mesh_and_write(Part.makeCompound(segs), OUT / "tubes.stl")
    check_mesh("tubes.stl", m_t)

    # 5. PCB 网格 + 壳网格校验 (T6 多壳件闭合以生成器写时断言为准, 见 check_mesh)
    check_mesh("pcb.stl", mesh_and_write(pcb_shape, OUT / "pcb.stl"))
    check_mesh("case_bottom.stl", Mesh.Mesh(str(OUT / "case_bottom.stl")))
    check_mesh("case_top.stl", Mesh.Mesh(str(OUT / "case_top.stl")))
    check_mesh("manifold.stl", Mesh.Mesh(str(OUT / "manifold.stl")))
    check_mesh("pump_module.stl", Mesh.Mesh(str(OUT / "pump_module.stl")), min_shells=2,
               closed_required=False)                                              # 底盒+裙盖
    check_mesh("pump.stl", Mesh.Mesh(str(OUT / "pump.stl")), min_shells=3,
               closed_required=False)                                              # 体+双嘴
    check_mesh("brackets.stl", Mesh.Mesh(str(OUT / "brackets.stl")), min_shells=2,
               closed_required=False)                                              # 支架×2

    # 6. 清理旧版遗留的空 parts_b.stl (BOM 无底面器件)
    stale = OUT / "parts_b.stl"
    if stale.exists():
        stale.unlink()
        print("[out] removed stale parts_b.stl (no bottom-side parts)")

    # 7. assembly.json — spec §3.4 契约 + T6 双体 (explode/bbox 全部来自 case_geom)
    #    主模块 6 件 (板+器件+底+盖+阀阵+歧管) + 泵模块 4 件 (壳+泵+支架+气管)
    PARTS = [
        ("manifold",    "歧管 M (1f-β 12 口)",   "/meshes/manifold.stl",     "#6b7fa3"),
        ("valves",      "阀阵 11 只 (1a 竖装)",   "/meshes/valves.stl",       "#4a6da7"),
        ("case_top",    "上壳(通风栅+气口阵列)",  "/meshes/case_top.stl",     "#9e9e9e"),
        ("parts_F",     "器件阵-顶面",            "/meshes/parts_f.stl",      "#c62828"),
        ("pcb",         "P1 主板",                "/meshes/pcb.stl",          "#0d6b3f"),
        ("case_bottom", "下壳(铜柱+泵对接孔)",    "/meshes/case_bottom.stl",  "#757575"),
        ("pump_case",   "泵模块壳 (1h 分装)",     "/meshes/pump_module.stl",  "#8f8f93"),
        ("pump",        "泵 ZR370-03PM",          "/meshes/pump.stl",         "#555b63"),
        ("brackets",    "硅胶支架 ×2",            "/meshes/brackets.stl",     "#c9a06a"),
        ("tubes",       "供压/真空管 (视觉)",     "/meshes/tubes.stl",        "#7ec8e3"),
    ]
    assembly = {
        "parts": [
            {"id": pid, "name": nm, "stl": stl, "color": col,
             "explode": G.EXPLODE[pid], "opacity": 1.0}
            for pid, nm, stl, col in PARTS
        ],
        "bodies": {
            "main": ["manifold", "valves", "case_top", "parts_F", "pcb", "case_bottom"],
            "pump": ["pump_case", "pump", "brackets", "tubes"],
        },
        "bbox_mm": G.BBOX_MM,
        "assembly_note": "T6 双体装配: 主模块 (板+11 阀+歧管 M, 壳盖上气动塔) + "
                         "泵模块 (ZR370+硅胶支架, 分装式); 气管连 S/V 壁孔",
    }
    (OUT / "assembly.json").write_bytes(json.dumps(assembly, ensure_ascii=False, indent=2).encode("utf-8"))
    print("[out] assembly.json written -> %s (bbox %s, 2 bodies x %d+%d parts)"
          % (OUT / "assembly.json", G.BBOX_MM, 6, 4))
    print("MESHES OK: 11 files in", OUT)


main()
