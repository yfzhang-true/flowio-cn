# -*- coding: utf-8 -*-
"""FLOWIO-P1 CAD 装配测试 L1/L2/L3 — 纯标准库, 无 FreeCAD 依赖 (对标原理图 DRC/固件单测).

层级 (spec: docs/superpowers/specs/2026-10-03-cad-assembly-truth.md §3):
  L1 单元   — 每个孪生 STL 的几何健全性 (面数/包围盒黄金值/z 带占据/防回归断言)
  L2 接口   — 装配一致性 (钻孔<->铜柱黄金对拍 / 锚点映射 / 越壁器件必落入侧槽)
  L3 功能   — 渲染资产契约 (assembly.json <-> STL <-> bbox <-> 爆炸态 <-> hotspots)

运行: python hardware/flowio-p1/enclosure/test_assembly.py
前置: make_case.py + make_meshes.py + make_flows.py 已生成产物。
历史教训: 旧版装配的两个大错 (上壳带底板与下壳全面穿插; 板趴腔底被铜柱穿透)
都没有任何测试拦截 — 本文件的存在意义就是让它们永远过不了 CI。
"""
import csv
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import case_geom as G

ROOT = HERE.parents[2]
MESH = ROOT / "firmware" / "twin" / "meshes"
WEB = ROOT / "firmware" / "twin" / "webapp"
POSCSV = ROOT / "hardware" / "flowio-p1" / "fab" / "flowio-p1-pos.csv"
DRL = ROOT / "hardware" / "flowio-p1" / "fab" / "flowio-p1.drl"

PASS, FAIL = 0, 0


def check(name, ok, detail=""):
    global PASS, FAIL
    tag = "PASS" if ok else "FAIL"
    if ok:
        PASS += 1
    else:
        FAIL += 1
    print("[%-4s] %s%s" % (tag, name, ("  | " + detail) if detail else ""))
    return ok


def approx(a, b, tol):
    return abs(a - b) <= tol


def load(name):
    cnt, (x0, x1), (y0, y1), (z0, z1) = G.stl_bbox(MESH / name)
    _n, verts = G.parse_stl(MESH / name)
    return cnt, (x0, x1, y0, y1, z0, z1), verts


# ================= L1 单元: STL 几何健全 =================
print("== L1 单元: STL 几何 ==")

for fname in ["pcb.stl", "parts_f.stl", "case_bottom.stl", "case_top.stl"]:
    cnt, bb, verts = load(fname)
    check("L1 %s 可解析 (binary STL, %d facets)" % (fname, cnt), cnt > 0)

# pcb: 精确黄金值 (板坐铜柱顶)
cnt, bb, _ = load("pcb.stl")
_lbl = "L1 pcb bbox 黄金值 (%.1f..%.1f, %.1f..%.1f, %.1f..%.1f)" % (
    G.OX, G.OX + G.BW, G.OX, G.OX + G.BH, G.Z_BOARD, G.Z_TOP)
check(_lbl,
      approx(bb[0], G.OX, 0.05) and approx(bb[1], G.OX + G.BW, 0.05) and
      approx(bb[2], G.OX, 0.05) and approx(bb[3], G.OX + G.BH, 0.05) and
      approx(bb[4], G.Z_BOARD, 0.05) and approx(bb[5], G.Z_TOP, 0.05),
      "实际 x[%.2f..%.2f] y[%.2f..%.2f] z[%.2f..%.2f]" % bb)

# parts_f: 基面=板面, 上界=内腔顶之下, 面数足量
cnt, bb, _ = load("parts_f.stl")
check("L1 parts_f 基面 = Z_TOP", approx(bb[4], G.Z_TOP, 0.05), "zmin=%.2f" % bb[4])
check("L1 parts_f 顶 < Z_CEIL-0.4", bb[5] <= G.Z_CEIL - 0.4, "zmax=%.2f (腔顶 %.1f)" % (bb[5], G.Z_CEIL))
check("L1 parts_f 面数 >= 1000", cnt >= 1000, "facets=%d" % cnt)

# case_bottom: 底板带/壁带/铜柱簇/无超腔顶材料
cnt, bb, verts = load("case_bottom.stl")
check("L1 bottom z 0..Z_CEIL", approx(bb[4], 0, 0.05) and approx(bb[5], G.Z_CEIL, 0.05),
      "z[%.2f..%.2f]" % (bb[4], bb[5]))
check("L1 bottom 底板带占据 (z<2.3 有顶点)", any(v[2] < 2.3 for v in verts))
check("L1 bottom 壁顶带占据 (z>Z_CEIL-1)", any(v[2] > G.Z_CEIL - 1.0 for v in verts))
boss_r = G.PD / 2 + G.BOSS_RING
boss_ok = 0
for sx, sy in G.ST:
    cx, cy = sx + G.OX, sy + G.OX
    # 柱壁为竖直面, STL 顶点仅存于上下环 (z=7.4 顶环); 窗口取环带
    if any((abs(v[0] - cx) < boss_r + 0.6 and abs(v[1] - cy) < boss_r + 0.6
            and abs(v[2] - G.Z_BOARD) < 0.25) for v in verts):
        boss_ok += 1
check("L1 bottom 铜柱簇 x4 (ST 处有柱顶环)", boss_ok == 4, "%d/4" % boss_ok)

# case_top: 裙边下端以上才有材料 (防"带底板方盒"回归), 天花板/通风栅/螺丝孔
cnt, bb, verts = load("case_top.stl")
check("L1 top zmin >= SKIRT_Z0 (盖子不得有底板!)",
      bb[4] >= G.SKIRT_Z0 - 0.05, "zmin=%.2f (SKIRT_Z0=%.1f)" % (bb[4], G.SKIRT_Z0))
check("L1 top zmax = OUTER_H", approx(bb[5], G.OUTER_H, 0.05), "zmax=%.2f" % bb[5])
ceil_band = [v for v in verts if v[2] > G.Z_CEIL - 0.1]
check("L1 top 天花板带占据", len(ceil_band) > 50, "verts=%d" % len(ceil_band))
vent_ok = 0
for i in (0, 4, 7):
    for j in (0, 3, 5):
        gx, gy = G.OX + 12 + i * 9, G.OX + 18 + j * 8
        if any(gx - 0.4 < v[0] < gx + 5.4 and gy - 0.4 < v[1] < gy + 4.4
               and abs(v[2] - G.OUTER_H) < 0.25 for v in ceil_band):
            vent_ok += 1
check("L1 top 通风栅孔环 9/9 抽样", vent_ok == 9, "%d/9" % vent_ok)
screw_ok = sum(
    1 for sx, sy in G.ST
    if any(abs(v[0] - (sx + G.OX)) < G.SCREW_D / 2 + 0.5 and abs(v[1] - (sy + G.OX)) < G.SCREW_D / 2 + 0.5
           and abs(v[2] - G.OUTER_H) < 0.25 for v in ceil_band))
check("L1 top M3 过孔 x4", screw_ok == 4, "%d/4" % screw_ok)

# ================= L2 接口: 装配一致性 =================
print("== L2 接口: 装配一致性 ==")

# 钻孔 NPTH Ø3.2 <-> 铜柱 ST 黄金对拍 (fab 数据 <-> CAD)
# P1.1 T3: M3 孔工具号从 T9 变为 T5 (XH-2P 无 TH 孔, 工具集变化) -> 按
# 直径检索工具而非硬编码序号, 对拍语义不变 (仍 4 孔 Δ<0.2)
drl_txt = open(DRL, encoding="utf-8", errors="replace").read()
dia, cur, t32 = {}, None, []
for ln in drl_txt.splitlines():
    s = ln.strip()
    m = re.match(r"^T(\d+)C([\d.]+)$", s)
    if m:
        dia[m.group(1)] = float(m.group(2))
        continue
    m = re.match(r"^T(\d+)$", s)
    if m:
        cur = m.group(1)
        continue
    m = re.match(r"^X(-?[\d.]+)Y(-?[\d.]+)$", s)
    if m and cur and abs(dia.get(cur, 0) - 3.2) < 0.01:
        t32.append((float(m.group(1)), -float(m.group(2))))
check("L2 钻孔 Ø3.2 共 4 孔 (按直径检索工具)", len(t32) == 4, str(t32))
dmax = 0.0
for hx, hy in t32:
    dmin_st = min(((sx - hx) ** 2 + (sy - hy) ** 2) ** 0.5 for sx, sy in G.ST)
    dmax = max(dmax, dmin_st)
check("L2 铜柱 ST <-> 钻孔 Δ<0.2", len(t32) == 4 and dmax < 0.2, "max Δ=%.3f" % dmax)

# pos.csv 锚点
parts = []
with open(POSCSV, newline="", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        ref = (row["Ref"] or "").strip()
        if not ref.upper().startswith("H"):
            parts.append({"ref": ref, "pkg": (row["Package"] or "").strip(),
                          "x": float(row["PosX"]), "y": float(row["PosY"]),
                          "rot": float(row["Rot"]),
                          "side": (row["Side"] or "").strip().lower()})
refs = {p["ref"] for p in parts}
anchor_ok = all(r in refs for r, *_ in G.ANCHORS) and all(
    approx(G.board_to_case(px, py)[0], ex, 0.01) and approx(G.board_to_case(px, py)[1], ey, 0.01)
    for r, px, py, ex, ey in G.ANCHORS)
check("L2 锚点映射 x3 (J10/J2/J1)", anchor_ok)

# 顶面器件基面 + 无底面器件
sides = {p["side"] for p in parts}
check("L2 全部顶面器件 (parts_B 通道应关闭)", sides == {"top"}, str(sides))


# 越壁器件必须落入侧槽 (CAD 版 DRC)
def slot_rects():
    """返回 [(face, u_lo, u_hi, z_lo, z_hi)] — u 沿板边方向; 含后壁两端角部 relief."""
    out = []
    for face, pos, w, lo, hi in G.CUTS:
        out.append((face, pos + G.OX - w / 2, pos + G.OX + w / 2, lo, hi))
    tw, lo, hi = G.TERM_SLOT
    for x in G.TERM_X:
        out.append(("B", x + G.OX - tw / 2, x + G.OX + tw / 2, lo, hi))
    rx, ry0, ry1 = G.TERM_RELIEF
    out.append(("L", ry0, ry1, lo, hi))          # 角 relief 在 L/R 壁的贯穿范围
    out.append(("R", ry0, ry1, lo, hi))
    return out


SLOTS = slot_rects()


def covered(x0, x1, y0, y1, z0, z1):
    """器件盒与壁带相交的部分, 必须被该面某侧槽完整覆盖 (u 向 + z 带覆盖).
    穿透深度阈值: 低带=壁厚 WALL, 高带(触及裙环 z>SKIRT_Z0)=裙带深 SKIRT_INSET+SKIRT_T.
    返回 (ok, 未覆盖面)."""
    deep = G.SKIRT_INSET + G.SKIRT_T
    lo_d = deep if z1 > G.SKIRT_Z0 else G.WALL
    crossings = []
    if x0 < lo_d:
        crossings.append(("L", (y0, y1)))
    if x1 > G.OW - lo_d:
        crossings.append(("R", (y0, y1)))
    if y0 < G.WALL:
        crossings.append(("T", (x0, x1)))
    if y1 > G.OH - G.WALL:
        crossings.append(("B", (x0, x1)))
    for face, (a0, a1) in crossings:
        for sf, u0, u1, zlo, zhi in SLOTS:
            if sf == face and u0 - 0.05 <= a0 and a1 <= u1 + 0.05 \
               and zlo - 0.1 <= z0 and z1 <= zhi + 0.1:
                break
        else:
            return False, face
    return True, None


violators = []
for p in parts:
    w, d, h = G.dims_for(p["pkg"])
    if int(round(p["rot"])) % 180 == 90:
        w, d = d, w
    cx, cy = G.board_to_case(p["x"], p["y"])
    okc, face = covered(cx - w / 2, cx + w / 2, cy - d / 2, cy + d / 2, G.Z_TOP, G.Z_TOP + h)
    if not okc:
        violators.append("%s(%s,%s)" % (p["ref"], p["pkg"][:12], face))
check("L2 越壁器件全部落于侧槽", not violators, "violators: %s" % violators)

# ================= L3 功能: 渲染资产契约 =================
print("== L3 功能: 渲染资产契约 ==")

man = json.loads((MESH / "assembly.json").read_text(encoding="utf-8"))
ids = [p["id"] for p in man["parts"]]
check("L3 装配清单 = 4 件 (无空 parts_B)", set(ids) == {"case_top", "parts_F", "pcb", "case_bottom"}, str(ids))
stl_ok = True
for p in man["parts"]:
    cnt, _x, _y, _z = G.stl_bbox(MESH / Path(p["stl"]).name)
    if cnt <= 0:
        stl_ok = False
check("L3 清单 STL 全部非空", stl_ok)
exp_ok = all(list(p["explode"]) == G.EXPLODE[p["id"]] for p in man["parts"])
check("L3 爆炸向量 = case_geom 契约", exp_ok)

# bbox_mm <-> 实测并集
meas = [0.0, 0.0, 0.0]
for p in man["parts"]:
    cnt, (x0, x1), (y0, y1), (z0, z1) = G.stl_bbox(MESH / Path(p["stl"]).name)
    meas = [max(meas[0], x1), max(meas[1], y1), max(meas[2], z1)]
bbox_ok = all(approx(man["bbox_mm"][i], meas[i], 0.6) for i in range(3))
check("L3 bbox_mm <-> 实测并集 ±0.6", bbox_ok,
      "json=%s meas=%s" % (man["bbox_mm"], [round(m, 2) for m in meas]))

# 爆炸态两两不交 (z 区间)
def zrange(pid):
    _n, _x, _y, zz = G.stl_bbox(MESH / (pid + ".stl"))
    return zz[0] + G.EXPLODE[pid][2], zz[1] + G.EXPLODE[pid][2]


order = ["case_top", "parts_F", "pcb", "case_bottom"]
bands = {pid: zrange(pid) for pid in order}
pairs = [(a, b) for i, a in enumerate(order) for b in order[i + 1:]]
disjoint = all(bands[a][1] <= bands[b][0] or bands[b][1] <= bands[a][0] for a, b in pairs)
check("L3 爆炸态层叠两两分离", disjoint,
      " ".join("%s[%.1f..%.1f]" % (pid, *bands[pid]) for pid in order))

# hotspots z 域
hs = json.loads((WEB / "hotspots.json").read_text(encoding="utf-8"))["hotspots"]
hs_ok = all(G.Z_TOP - 0.1 <= h["center"][2] <= G.Z_CEIL - 0.5 for h in hs)
check("L3 hotspots z ∈ [Z_TOP, Z_CEIL-0.5]", hs_ok,
      "z: %s" % [round(h["center"][2], 1) for h in hs])

# scene.js 回退 bbox 同源
scene_txt = (ROOT / "firmware" / "twin" / "webapp" / "js" / "scene.js").read_text(encoding="utf-8")
fb = "%.1f, %.1f, %.1f" % tuple(G.BBOX_MM)
check("L3 scene.js 回退 bbox 同源", fb in scene_txt, "expect '%s'" % fb)

print("\nCAD L1/L2/L3: %d PASS / %d FAIL" % (PASS, FAIL))
sys.exit(1 if FAIL else 0)
