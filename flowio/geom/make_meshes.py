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

D4 (2026-10-05, spec 2026-10-05 §5 device-modeling): 三件升级为 devices3d 精确模型
(盒近似退役 —— 阀阵/泵/传感的 datasheet 几何直推, 单一真相 devices.json geom3d):
  valves.stl   11 只 = 10×F0520D (底面坐盖顶, install 1a) + 1×F0520B/VV (⌀4.6 嘴充满
               ⌀4.8 承口带 44..50 锚定, origin z=16.0) + C 架引线出体段在模;
  pump.stl     ZR370 立式校正 (头⌀24 + 电机⌀27 + 顶置双嘴⌀4.2 ⊥轴), 装配位 =
               make_pump_module 同式 (轴沿 X @z18.4, 头端面 x=140.2);
  parts_f.stl  顶面盒阵剔除 U6 (XGZP) + 精确传感器 (焊盘中心贴板, 航向 -90°)。
另产: webapp/connections_scene.json (connections.json → 渲染折线, D4-A/D2-A,
      connections_render 单源) + webapp/connections.json (真值原文副本);
      assembly.json tubes 件标记 kind=connections (scene-3d 运行时由图谱驱动,
      tubes.stl 保留为加载失败回退件)。
幂等: 网格化参数固定 (LinearDeflection 0.4/Angular 0.5), 重跑输出逐字节稳定。
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
from flowio.geom.pneu_geom import tube             # T6 共享构建器 (tubes.stl 回退件仍用)
from flowio.twin import connections_render as CR  # noqa: E402  D4 渲染 payload (纯 stdlib)
from flowio.twin.devices3d import (               # noqa: E402  D4 精确器件构建器
    valve_f0520d, valve_f0520b, pump_zr370, sensor_xgzp)

HERE = ROOT / "hardware" / "flowio-p1" / "enclosure"   # 产物源目录 (M1 前=脚本目录)
POSCSV = ROOT / "hardware" / "flowio-p1" / "fab" / "flowio-p1-pos.csv"
OUT = ROOT / "firmware" / "twin" / "meshes"
WEB = ROOT / "firmware" / "twin" / "webapp"
SENSOR_REF = "U6"                                 # XGZP6897D 位号 (pos.csv; connections=S1)


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


def mesh_compound_write(shape, path):
    """D4: 逐 solid 细分 + addMesh 合并 (make_pump_module.write_stl 同模式) ——
    meshFromShape 直接吃复合体会产生破壳 (FreeCAD 1.1.4 实测: 阀复合体 5952 facets
    碎成 2258 开壳), 逐体细分各闭合。"""
    out = None
    for s in shape.Solids:
        m = MeshPart.meshFromShape(Shape=s, LinearDeflection=0.4, AngularDeflection=0.5)
        if out is None:
            out = Mesh.Mesh(m)                   # addMesh 原位变更返回 None (pump_module 同坑)
        else:
            out.addMesh(m)
    out.write(str(path))
    return out


def check_mesh(name, m, min_shells=1, closed_required=True):
    """网格健全: 非空 + 壳数下限 + 逐连通壳闭合 (多件合体 STL 如 pump_module 底+盖 /
    valves 11 只按'逐壳闭合'校验 — 合体件 isSolid 必假是语义不是缺陷).
    closed_required=False: float32 STL 往返会把共面融合件的焊接点拆出 1-ULP 缝
    (pump_module 实测 2 闭壳写盘重载变 3 壳 2 开; parts_f 实测 3 开壳全落传感器域,
    见 4/4b 取证断言) — 闭合真值以生成器写时断言
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


def valve_solids_precise():
    """D4: 11 阀 devices3d 精确模型, 壳系绝对坐标 (放锚同 connections_render 单源).

    F0520D (10 只): 器件原点 (N2 端面面心) 坐壳盖顶 TOWER_Z0 —— install "13×15 底面
      着板方向, 长轴 20.5 立起, 嘴朝上"; N1 嘴 (世界 42.0..45.0) 入歧管承口带 36.5..46。
    F0520B (VV, 1 只): 器件原点 z = MAN_Z0 - 28.0 = 16.0 —— N1 ⌀4.6×6 嘴 (44..50)
      充满 ⌀4.8 承口带 (装配态=歧管承插悬置, case_geom "阀吊装于歧管"; 体底 16.0
      隐入腔内, 视觉于盖顶起浮 5.5mm 属真实悬置态)。
    """
    out = []
    for v in CR.valve_places():
        b = valve_f0520b.build() if v["kind"] == "B" else valve_f0520d.build()
        b.translate(App.Vector(v["x"], v["y"], v["oz"]))
        out.append((v["x"], v["y"], v["kind"], b))
    return out


def pump_precise():
    """D4: ZR370 精确泵 (立式校正: 顶置双嘴 ⊥ 轴), 装配位 = make_pump_module 同式
    (器件本地轴高 12 → 壳系 PUMP_AXIS_Z; 头端面贴内腔 x0 = T+CLR)。"""
    sh = pump_zr370.build()
    px, py, pz = CR.pump_place()
    sh.translate(App.Vector(px, py, pz))
    return sh


def sensor_precise():
    """D4: XGZP6897D 精确传感器 (双倒钩 + SOIC8 鸥翼), 焊盘中心贴板面 + 航向 -90°
    (封装跨距 7.96 沿壳系 X / 体长轴沿 Y —— 与 parts_f 旧盒 7.96×10.6 同朝向;
    P1 高压倒钩落天花过孔 (48.5,27) 邻位, 与测压支路对接)。"""
    sh = sensor_xgzp.build()
    sh.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), -90.0)
    cx, cy, cz = CR.sensor_place(CR.load_pos())
    sh.translate(App.Vector(cx, cy, cz))
    return sh


def main():
    OUT.mkdir(parents=True, exist_ok=True)

    # 1. 壳 STL 复制改名 (make_case.py 产物, 壳系原生)
    shutil.copyfile(HERE / "case-bottom.stl", OUT / "case_bottom.stl")
    shutil.copyfile(HERE / "case-top.stl", OUT / "case_top.stl")

    # 1b. T6 气动结构件 STL 复制 (make_manifold / make_pump_module 产物, 壳系绝对坐标)
    #     D4: pump.stl 不再取 enclosure 哑泵 —— devices3d 精确泵重建 (见 1c)
    for src, dst in (("manifold.stl", "manifold.stl"), ("pump-module.stl", "pump_module.stl"),
                     ("brackets.stl", "brackets.stl")):
        shutil.copyfile(HERE / src, OUT / dst)

    # 1c. D4 精确泵 (立式校正: 头⌀24×27.3 + 电机⌀27×30.8 + 顶置双嘴 ⌀4.2×7.5 ⊥轴)
    check_mesh("pump.stl", mesh_compound_write(pump_precise(), OUT / "pump.stl"), min_shells=6)

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

    # 4. 顶面器件阵 (基面 Z_TOP) — D4: U6 (XGZP) 剔盒, 由精确传感器入阵
    #    closed_required=False (D4 规格审遗留复核 2026-10-05 收口, 取证属实):
    #    写前 OCC 157 体 isValid 且全闭合、逐体网格全闭合; float32 STL 往返把传感器
    #    fuse/cut 共面点拆 1-ULP 缝, 稳定复现 3 开壳 = 本体(含引压孔 cut)+双倒钩
    #    (stub.fuse(flare).cut(bore)), 全部落在传感器 bbox 域, 盒阵 148 体全闭合,
    #    网格/OCC 体积相对差 2e-5 (float32 量化级) —— 缝隙为格式量化非几何破损,
    #    不能收紧 closed_required=True (见 4b 重载定位断言)。写时断言双保险:
    #    OCC isValid (此处) + 重载后开壳域检查 (4b)。
    sensor_shape = sensor_precise()
    pf_shape = Part.makeCompound(
        [part_box(p) for p in tops if p["ref"] != SENSOR_REF] + [sensor_shape])
    assert pf_shape.isValid() and all(s.isClosed() for s in pf_shape.Solids), \
        "parts_f: 写前 OCC solid 无效/开壳 —— 几何构建破损, 非格式量化"
    m_f = mesh_compound_write(pf_shape, OUT / "parts_f.stl")
    check_mesh("parts_f.stl", m_f, closed_required=False)

    # 4b. parts_f 写盘重载复核 (float32 往返): 开壳仅允许出现在传感器 bbox 域内
    #     (1-ULP 缝位置取证 2026-10-05); 盒阵/他处开壳 = 真破损, 必红。
    pf_reload = Mesh.Mesh(str(OUT / "parts_f.stl"))
    pf_comps = pf_reload.getSeparateComponents()
    pf_opens = [c for c in pf_comps if not c.isSolid()]
    sbb = sensor_shape.BoundBox
    _pad = 0.5

    def _in_sensor(c):
        b = c.BoundBox
        return (b.XMin >= sbb.XMin - _pad and b.XMax <= sbb.XMax + _pad and
                b.YMin >= sbb.YMin - _pad and b.YMax <= sbb.YMax + _pad and
                b.ZMin >= sbb.ZMin - _pad and b.ZMax <= sbb.ZMax + _pad)

    print("[mesh] parts_f.stl  reload shells=%d open=%d all-in-sensor=%s"
          % (len(pf_comps), len(pf_opens), all(_in_sensor(c) for c in pf_opens)))
    assert all(_in_sensor(c) for c in pf_opens), \
        "parts_f: 传感器域外开壳 —— 非 float32 ULP 缝, 需排查几何"

    # 4b. T6→D4 阀阵 11 只 (devices3d 精确模型: C 架+翻边+双端嘴+引线出体段)
    m_v = mesh_compound_write(Part.makeCompound([vs for *_m, vs in valve_solids_precise()]),
                              OUT / "valves.stl")
    check_mesh("valves.stl", m_v, min_shells=66)      # 11 阀 × 6 分件 (D: frame/flange/N1/N2/线×2; B: frame/端段/N1/N2/线×2)

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
    check_mesh("pump.stl", Mesh.Mesh(str(OUT / "pump.stl")), min_shells=6,
               closed_required=False)                                              # 头+电机+双嘴+双焊片
    check_mesh("brackets.stl", Mesh.Mesh(str(OUT / "brackets.stl")), min_shells=2,
               closed_required=False)                                              # 支架×2

    # 6. 清理旧版遗留的空 parts_b.stl (BOM 无底面器件)
    stale = OUT / "parts_b.stl"
    if stale.exists():
        stale.unlink()
        print("[out] removed stale parts_b.stl (no bottom-side parts)")

    # 7. assembly.json — spec §3.4 契约 + T6 双体 (explode/bbox 全部来自 case_geom)
    #    主模块 6 件 (板+器件+底+盖+阀阵+歧管) + 泵模块 4 件 (壳+泵+支架+气管)
    #    D4: tubes 件标记 kind=connections —— scene-3d 运行时由 connections 图谱驱动
    #    折线渲染 (爆炸端跟随), tubes.stl 保留为数据加载失败的回退件。
    PARTS = [
        ("manifold",    "歧管 M (1f-β 12 口)",   "/meshes/manifold.stl",     "#6b7fa3", None),
        ("valves",      "阀阵 11 只 (devices3d 精确)", "/meshes/valves.stl",   "#4a6da7", None),
        ("case_top",    "上壳(通风栅+气口阵列)",  "/meshes/case_top.stl",     "#9e9e9e", None),
        ("parts_F",     "器件阵-顶面",            "/meshes/parts_f.stl",      "#c62828", None),
        ("pcb",         "P1 主板",                "/meshes/pcb.stl",          "#0d6b3f", None),
        ("case_bottom", "下壳(铜柱+泵对接孔)",    "/meshes/case_bottom.stl",  "#757575", None),
        ("pump_case",   "泵模块壳 (1h 分装)",     "/meshes/pump_module.stl",  "#8f8f93", None),
        ("pump",        "泵 ZR370-03PM (精确)",   "/meshes/pump.stl",         "#555b63", None),
        ("brackets",    "硅胶支架 ×2",            "/meshes/brackets.stl",     "#c9a06a", None),
        ("tubes",       "管路/线束 (connections)", "/meshes/tubes.stl",       "#7ec8e3", "connections"),
    ]
    assembly = {
        "parts": [
            {"id": pid, "name": nm, "stl": stl, "color": col,
             "explode": G.EXPLODE[pid], "opacity": 1.0, **({"kind": kd} if kd else {})}
            for pid, nm, stl, col, kd in PARTS
        ],
        "bodies": {
            "main": ["manifold", "valves", "case_top", "parts_F", "pcb", "case_bottom"],
            "pump": ["pump_case", "pump", "brackets", "tubes"],
        },
        "bbox_mm": G.BBOX_MM,
        "assembly_note": "T6 双体装配: 主模块 (板+11 阀+歧管 M, 壳盖上气动塔) + "
                         "泵模块 (ZR370+硅胶支架, 分装式); 气管连 S/V 壁孔; "
                         "D4: 阀/泵/传感=devices3d 精确模型, 管路线束=connections.json 驱动",
    }
    (OUT / "assembly.json").write_bytes(json.dumps(assembly, ensure_ascii=False, indent=2).encode("utf-8"))
    print("[out] assembly.json written -> %s (bbox %s, 2 bodies x %d+%d parts)"
          % (OUT / "assembly.json", G.BBOX_MM, 6, 4))

    # 8. D4 数据管线: connections 图谱 → webapp (渲染折线 payload + 真值原文副本)
    WEB.mkdir(parents=True, exist_ok=True)
    payload = CR.build_render_payload()
    (WEB / "connections_scene.json").write_bytes(
        json.dumps(payload, ensure_ascii=False, indent=1).encode("utf-8"))
    shutil.copyfile(CR.CONNECTIONS_JSON, WEB / "connections.json")
    n_render = sum(1 for e in payload["edges"] if e["render"] != "none")
    print("[out] connections_scene.json (%d edges, %d rendered) + connections.json (真值副本) -> %s"
          % (len(payload["edges"]), n_render, WEB))
    print("MESHES OK: 11 files in", OUT)


if __name__ == "__main__":
    main()
