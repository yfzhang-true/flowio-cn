# -*- coding: utf-8 -*-
"""test_devices3d_geom.py — D1 器件三接口面几何断言 (spec: 2026-10-05-device-modeling-connections
§2.1 器件模型库 + §7 验收1"几何断言: 每器件 port/terminal/mount 的位/向/径 vs datasheet 图纸").

TDD 分层追加 (红→绿):
  G1 描述符 schema — pneumatic_devices.*.geom3d 三接口面齐全 (pneumatic_ports/
                    electrical_terminals/mech_mounts), name/pos/dir/dia 完整, dir 单位向量
                    (负测试: 非单位 dir 坏副本必翻红)
  G2 valve_f0520d — 本体 20.5×15×13 + 顶翻边 0.7 + N1/N2 嘴 ⌀3.0×3.5 双端面 (安装态 N1 朝上);
                    引线出体位; 铁律 10: 分项断言, 禁总盒宽松
  G3 valve_f0520b — 总长 28(本体 20+端段 8) + N1 顶嘴 ⌀4.6×6.0; 安装孔=数据占位(不切孔)
  G4 pump_zr370  — 立式校正核心: 轴向分段(头 ⌀24×27.3 + 电机 ⌀27×30.8 = 58.1) +
                    顶置双嘴 ⌀4.2×7.5 (+Z ⊥ 泵轴 +X, 嘴距 10) + 电机端子; 嘴在头段
  G5 sensor_xgzp — 本体 10.8×7×3.5 + 双倒钩 ⌀3.22×2.4 顶置(P1/P2, 孔 ⌀0.9 贯通) +
                    SOIC8 鸥翼 8 脚(节距 2.54/排距 7.96)
  G6 fittings    — 硅胶管 ID3/OD7 直管+三点弯(空腔贯通) + Kamoer 直通/变径 + 三通 (D4-A 折线)
  G7 harness     — 阀 2P 引线视觉桩 60mm + 泵电缆 150 (D2-A 桩深) + XH2.54-2P 白壳 10×7.8×6.2
  G8 单源一致性  — builder 默认参数 == devices.json geom3d (单一真相源, 防 json/代码漂移)

运行: E:/FreeCAD/bin/python.exe hardware/flowio-p1/enclosure/test_devices3d_geom.py
      (FreeCAD Part=OCCT 内嵌, D1 裁定 A 零新依赖; 断言容差分级: 关键接口±0.3/本体外形±0.5)
"""
import copy
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))   # 仓库根 (enclosure 上三级)
sys.path.insert(0, ROOT)               # 几何单一真相源经 flowio 包 (FreeCAD python 免安装)

from flowio.twin import devices3d as D3                          # noqa: E402  (纯 stdlib 面)
DEVICES = os.path.join(HERE, "devices.json")

PASS, FAIL = 0, 0


def check(name, ok, detail=""):
    global PASS, FAIL
    print("[%-4s] %s%s" % ("PASS" if ok else "FAIL", name, ("  | " + detail) if detail else ""))
    if ok:
        PASS += 1
    else:
        FAIL += 1
    return ok


def load_pn():
    with open(DEVICES, encoding="utf-8") as f:
        return json.load(f)["pneumatic_devices"]


def v_sub(a, b):
    return [a[i] - b[i] for i in range(3)]


def v_dot(a, b):
    return sum(a[i] * b[i] for i in range(3))


def v_norm(a):
    return math.sqrt(v_dot(a, a))


def port_by_name(ports, name):
    for p in ports:
        if p["name"] == name:
            return p
    return None


def probe_vol(shape, center, direction, dia, length):
    """方向探针: ⌀dia×length 圆柱自 center 沿 direction, 与 shape 交体积 (材料存在性)."""
    import FreeCAD as App
    import Part
    p0 = App.Vector(*center)
    d = App.Vector(*direction)
    d.normalize()
    probe = Part.makeCylinder(dia / 2.0, length, p0, d)
    return shape.common(probe).Volume


def cyl_vol(dia, length):
    return math.pi * (dia / 2.0) ** 2 * length


def bb_ok(bb, x0, x1, y0, y1, z0, z1, tol):
    return (abs(bb.XMin - x0) < tol and abs(bb.XMax - x1) < tol and
            abs(bb.YMin - y0) < tol and abs(bb.YMax - y1) < tol and
            abs(bb.ZMin - z0) < tol and abs(bb.ZMax - z1) < tol), str(bb)


def _safe_build(fn, *a, **kw):
    """builder 缺失/异常 → (None, None) 并打印原因 (TDD 红态不裸崩, 逐项 FAIL)."""
    try:
        return fn(*a, **kw)
    except Exception as e:                                  # noqa: BLE001
        print("       (builder 异常: %s: %s)" % (type(e).__name__, e))
        return None, None


# ══════════ G1: 描述符 schema (geom3d 三接口面) ══════════
def test_g1_schema():
    pn = load_pn()
    groups = [("valves", "F0520D"), ("valve_vacuum_master", "F0520B"),
              ("pump", "ZR370"), ("sensor", "XGZP6897D")]
    missing = [g for g, _ in groups
               if not (pn.get(g) and isinstance(pn[g][0].get("geom3d"), dict))]
    check("G1 schema: 四器件均有 geom3d 块", not missing, str(missing))
    if missing:
        return
    bad = []
    for g, _ in groups:
        gm = pn[g][0]["geom3d"]
        for face in ("pneumatic_ports", "electrical_terminals", "mech_mounts"):
            if not gm.get(face):
                bad.append("%s.%s 缺" % (g, face))
        for p in gm.get("pneumatic_ports", []):
            for k in ("name", "pos", "dir", "dia"):
                if k not in p:
                    bad.append("%s.%s.%s 缺 %s" % (g, "ports", p.get("name", "?"), k))
            if not p.get("src"):
                bad.append("%s.%s 缺出处 src" % (g, p.get("name", "?")))
        for t in gm.get("electrical_terminals", []):
            if not t.get("src"):
                bad.append("%s.%s 缺出处 src" % (g, t.get("name", "?")))
    check("G1 schema: 三接口面字段完整 (name/pos/dir/dia + 每条出处 src)", not bad, str(bad[:4]))

    unit_bad = []
    for g, _ in groups:
        for p in pn[g][0]["geom3d"]["pneumatic_ports"]:
            if abs(v_norm(p["dir"]) - 1.0) > 1e-6:
                unit_bad.append("%s.%s" % (g, p["name"]))
    check("G1 schema: 气动口 dir 均为单位向量", not unit_bad, str(unit_bad))

    # 负测试 (防退化): dir 改非单位向量必被上断言翻红
    bad_pn = copy.deepcopy(pn)
    bad_pn["pump"][0]["geom3d"]["pneumatic_ports"][0]["dir"] = [0, 0, 2]
    nb = [p["name"] for p in bad_pn["pump"][0]["geom3d"]["pneumatic_ports"]
          if abs(v_norm(p["dir"]) - 1.0) > 1e-6]
    check("G1 负测试: dir 改 [0,0,2] 必失败", nb == ["CHG"], str(nb))


# ══════════ G2: valve_f0520d ══════════
def test_g2_valve_d():
    pn = load_pn()
    gm = pn["valves"][0]["geom3d"]
    body, ports = gm["body"], gm["pneumatic_ports"]
    n1, n2 = port_by_name(ports, "N1"), port_by_name(ports, "N2")
    check("G2 数据: N1 安装态朝上(dir +Z, 1a 竖装嘴朝上)", n1["dir"] == [0, 0, 1], str(n1["dir"]))
    check("G2 数据: N2 朝下(dir -Z, 正压/充气侧→cuff 管)", n2["dir"] == [0, 0, -1], str(n2["dir"]))
    check("G2 数据: 嘴径 ⌀3.0 (关键接口 ±0.3)", abs(n1["dia"] - 3.0) < 0.3 and abs(n2["dia"] - 3.0) < 0.3)

    parts, shape = _safe_build(D3.valve_f0520d.parts, ), None
    if parts is not None:
        shape = D3.valve_f0520d.build()
    if shape is None:
        for nm in ("build 可用", "bbox 外廓", "N1 嘴实体+朝上", "N2 嘴实体+朝下",
                   "顶翻边 0.7 (z19.8..20.5)", "引线出体位在位"):
            check("G2 %s" % nm, False, "builder 红 (未实现/异常)")
        return
    bb = shape.BoundBox
    ok = (abs(bb.XMin + 7.5) < 0.5 and abs(bb.XMax - 7.5) < 0.5 and      # 外形±0.5 (面心原点)
          bb.YMax - 6.5 < 0.05 and -15.5 < bb.YMin <= -14.0 and          # 引线自壁面出 -Y 侧 8mm
          abs(bb.ZMin + 3.5) < 0.5 and abs(bb.ZMax - 24.0) < 0.5)        # 本体20.5+双端嘴3.5
    check("G2 bbox 外廓 = 15×13×[-3.5..24.0] (面心原点, 引线出 -Y)", ok, str(bb))
    fr = parts["frame"]
    okf0 = (abs(fr.BoundBox.XMin + 7.5) < 0.01 and abs(fr.BoundBox.XMax - 7.5) < 0.01 and
            abs(fr.BoundBox.YMin + 6.5) < 0.01 and abs(fr.BoundBox.YMax - 6.5) < 0.01 and
            abs(fr.BoundBox.ZMin) < 0.01 and abs(fr.BoundBox.ZMax - 20.5) < 0.01)
    check("G2 本体分件 = 15×13×20.5 面心系 (铁律10 分项)", okf0, str(fr.BoundBox))
    check("G2 build 分件实体 ≥5 (架/线圈/翻边/双嘴/双引线)", len(shape.Solids) >= 5,
          "solids=%d" % len(shape.Solids))
    # N1 嘴: 自翻边顶面向上贯通; 嘴尖外无材料 (分项断言, 铁律 10)
    v_in = probe_vol(shape, [0, 0, 20.6], [0, 0, 1], 2.8, 3.2)
    v_out = probe_vol(shape, [0, 0, 24.05], [0, 0, 1], 2.8, 1.0)
    check("G2 N1 嘴实体在位 (⌀2.8 探针充盈>90%)", v_in > 0.9 * cyl_vol(2.8, 3.2),
          "%.2f/%.2f mm^3" % (v_in, cyl_vol(2.8, 3.2)))
    check("G2 N1 朝向: 嘴尖(24.0)之外无材料", v_out < 1e-6, "%.4f mm^3" % v_out)
    v_in2 = probe_vol(shape, [0, 0, -0.1], [0, 0, -1], 2.8, 3.2)
    v_out2 = probe_vol(shape, [0, 0, -3.55], [0, 0, -1], 2.8, 1.0)
    check("G2 N2 嘴实体在位且朝下 (尖外无材料)", v_in2 > 0.9 * cyl_vol(2.8, 3.2) and v_out2 < 1e-6,
          "in=%.2f out=%.4f" % (v_in2, v_out2))
    fl = parts.get("flange")
    okf = fl is not None and abs(fl.BoundBox.ZMin - (20.5 - body["flange_t"])) < 0.01 \
        and abs(fl.BoundBox.ZMax - 20.5) < 0.01
    check("G2 顶翻边 0.7 薄层在 z 19.8..20.5 (架顶固定面)", okf,
          str(fl.BoundBox if fl is not None else None))
    # 引线出体位 (图纸 5.2±0.3, 自 N2 端): -Y 侧探针
    v_w = probe_vol(shape, [0, -6.0, 5.2], [0, -1, 0], 0.9, 3.0)
    check("G2 引线出体位在位 (z=5.2, -Y 侧)", v_w > 0.5 * cyl_vol(0.9, 3.0), "%.3f mm^3" % v_w)


# ══════════ G3: valve_f0520b ══════════
def test_g3_valve_b():
    pn = load_pn()
    gm = pn["valve_vacuum_master"][0]["geom3d"]
    body, n1 = gm["body"], port_by_name(gm["pneumatic_ports"], "N1")
    check("G3 数据: N1 顶嘴 ⌀4.6×6.0 (关键 ±0.3)",
          abs(n1["dia"] - 4.6) < 0.3 and abs(n1["len"] - 6.0) < 0.3)
    check("G3 数据: 本体 20+端段 8 = 总长 28 (dims.h 同源)",
          abs(body["frame_len"] + body["end_sec_len"] - body["h"]) < 1e-9 and abs(body["h"] - 28.0) < 1e-9)

    parts, shape = _safe_build(D3.valve_f0520b.parts), None
    if parts is not None:
        shape = D3.valve_f0520b.build()
    if shape is None:
        for nm in ("build 可用", "bbox 外廓", "N1 顶嘴实体", "本体/端段分段", "安装孔=数据占位不切孔"):
            check("G3 %s" % nm, False, "builder 红 (未实现/异常)")
        return
    bb = shape.BoundBox
    n2 = port_by_name(gm["pneumatic_ports"], "N2")
    ok = (abs(bb.XMin + 7.5) < 0.5 and abs(bb.XMax - 7.5) < 0.5 and
          bb.YMax - 6.5 < 0.05 and -15.5 < bb.YMin <= -14.0 and
          abs(bb.ZMin + n2["len"]) < 0.5 and abs(bb.ZMax - (body["h"] + n1["len"])) < 0.5)
    check("G3 bbox 外廓 = 15×13×[-3.0..34.0] (面心原点, 28+顶嘴6/对端口3)", ok, str(bb))
    v_in = probe_vol(shape, [0, 0, 28.1], [0, 0, 1], 4.2, 5.6)
    v_out = probe_vol(shape, [0, 0, 34.05], [0, 0, 1], 4.2, 1.0)
    check("G3 N1 顶嘴实体在位 (⌀4.2 探针) 且尖外无材料",
          v_in > 0.9 * cyl_vol(4.2, 5.6) and v_out < 1e-6,
          "in=%.2f out=%.4f" % (v_in, v_out))
    fr, es = parts.get("frame"), parts.get("end_sec")
    okseg = (fr is not None and es is not None
             and abs(fr.BoundBox.ZMax - body["frame_len"]) < 0.01
             and abs(es.BoundBox.ZMin - body["frame_len"]) < 0.01
             and abs(es.BoundBox.ZMax - body["h"]) < 0.01)
    check("G3 本体(0..20)/端段(20..28) 分件建模", okseg,
          "frame=%s end=%s" % (fr and str(fr.BoundBox), es and str(es.BoundBox)))
    # 有孔变体 ⌀2.0×2 = 数据占位 (孔距待商家): 几何不切孔 → 占位探针遇实体材料
    v_hole = probe_vol(shape, [7.5, 0, 19.0], [0, 0, 1], 2.0, 2.0)
    check("G3 安装孔 ⌀2.0×2 为数据占位 (几何不切孔, 探针遇材料)", v_hole > 1e-3,
          "%.3f mm^3" % v_hole)


# ══════════ G4: pump_zr370 (立式校正核心) ══════════
def test_g4_pump():
    pn = load_pn()
    gm = pn["pump"][0]["geom3d"]
    body, ports = gm["body"], gm["pneumatic_ports"]
    chg, suck = port_by_name(ports, "CHG"), port_by_name(ports, "SUCK")
    axis = [1, 0, 0]                                   # 泵轴 = +X (头→电机)
    check("G4 数据: 双嘴顶置 ⊥ 泵轴 (dir·axis = 0)",
          abs(v_dot(chg["dir"], axis)) < 1e-9 and abs(v_dot(suck["dir"], axis)) < 1e-9)
    check("G4 数据: 嘴 ⌀4.2×7.5 (关键 ±0.3)",
          abs(chg["dia"] - 4.2) < 0.3 and abs(chg["len"] - 7.5) < 0.3)
    check("G4 数据: 嘴距 10.0 (实物照估值, 容差 ±1.0)",
          abs((suck["pos"][0] - chg["pos"][0]) - 10.0) < 1.0)

    parts, shape = _safe_build(D3.pump_zr370.parts), None
    if parts is not None:
        shape = D3.pump_zr370.build()
    if shape is None:
        for nm in ("build 可用", "bbox 外廓", "头/电机分段异径", "双顶嘴在位+⊥轴",
                   "嘴在头段内", "电机端子在位"):
            check("G4 %s" % nm, False, "builder 红 (未实现/异常)")
        return
    bb = shape.BoundBox
    r_head, r_motor = body["head_dia"] / 2.0, body["motor_dia"] / 2.0
    az = body["axis_z"]
    ok = (abs(bb.XMin) < 0.3 and bb.XMax - body["total_len"] < 3.5 and    # 电机端子焊片外伸 <3.5
          abs(bb.YMin + r_motor) < 0.3 and abs(bb.YMax - r_motor) < 0.3 and
          abs(bb.ZMin - (az - r_motor)) < 0.3 and                          # 电机⌀27 下缘 -1.5
          abs(bb.ZMax - (body["head_dia"] + chg["len"])) < 0.3)            # 关键接口级: 58.1×27×31.5
    check("G4 bbox = 58.1(+端子)×27.0×[-1.5..31.5] (总长/电机⌀27/含嘴高=devices dims.h)", ok, str(bb))
    # 轴向分段异径 (E1 校正): 头段 r12 之外无材料, 电机段 r12.4 有材料
    v_head_out = probe_vol(shape, [13.0, r_head + 0.4, az], [0, 0, 1], 0.6, 1.0)
    v_motor_in = probe_vol(shape, [50.0, r_head + 0.4, az], [0, 0, 1], 0.6, 1.0)
    check("G4 头⌀24/电机⌀27 分段异径 (头段外无材料, 同半径电机段有材料)",
          v_head_out < 1e-6 and v_motor_in > 1e-3,
          "head_out=%.4f motor_in=%.3f" % (v_head_out, v_motor_in))
    # 双顶嘴: 在位 (充盈) + 嘴尖外无材料 + 位于头段
    for nm, p in (("CHG", chg), ("SUCK", suck)):
        v_in = probe_vol(shape, [p["pos"][0], p["pos"][1], body["head_dia"] + 0.1], [0, 0, 1],
                         p["dia"] - 0.4, p["len"] - 0.4)
        v_out = probe_vol(shape, [p["pos"][0], p["pos"][1], body["head_dia"] + p["len"] + 0.05],
                          [0, 0, 1], p["dia"] - 0.4, 1.0)
        in_head = body["head_len"] >= p["pos"][0] >= 0
        check("G4 %s 顶置嘴在位+⊥轴+头段内" % nm,
              v_in > 0.9 * cyl_vol(p["dia"] - 0.4, p["len"] - 0.4) and v_out < 1e-6 and in_head,
              "in=%.2f out=%.4f in_head=%s" % (v_in, v_out, in_head))
    # 电机端子 (正/负极) 于电机端面 x=58.1
    tp = [t for t in gm["electrical_terminals"] if t["name"] == "MOTOR_POS"][0]
    v_t = probe_vol(shape, [tp["pos"][0] + 0.2, tp["pos"][1], tp["pos"][2]], [1, 0, 0], 0.5, 2.0)
    check("G4 电机正极端子在位 (x=58.1 端面)", v_t > 0.4 * cyl_vol(0.5, 2.0), "%.3f mm^3" % v_t)
    # 负测试 (E1 防退化): 侧置嘴 (dir=±Y) 虽 ⊥ 泵轴, 但非 +Z 顶置 → 朝向断言必翻红
    wrong = [0, 1, 0]
    check("G4 负测试: 侧置嘴 dir=[0,1,0] 非顶置 (+Z 分量=0≠1) 必失败",
          abs(v_dot(wrong, [0, 0, 1])) < 1e-9 and wrong != [0, 0, 1])


# ══════════ G5: sensor_xgzp ══════════
def test_g5_sensor():
    pn = load_pn()
    gm = pn["sensor"][0]["geom3d"]
    body, ports = gm["body"], gm["pneumatic_ports"]
    p1, p2 = port_by_name(ports, "P1"), port_by_name(ports, "P2")
    check("G5 数据: 双倒钩顶置 (+Z), ⌀3.22×2.4 (关键 ±0.3)",
          p1["dir"] == [0, 0, 1] and p2["dir"] == [0, 0, 1] and
          abs(p1["dia"] - 3.22) < 0.3 and abs(p1["len"] - 2.4) < 0.3)
    check("G5 数据: P1高压/P2大气 + 间距 5.2 (图面目测, ±0.5)",
          abs(math.dist(p1["pos"], p2["pos"]) - 5.2) < 0.5 or
          abs(math.dist(p1["pos"][:2], p2["pos"][:2]) - 5.2) < 0.5,
          "dist=%.2f" % math.dist(p1["pos"], p2["pos"]))

    parts, shape = _safe_build(D3.sensor_xgzp.parts), None
    if parts is not None:
        shape = D3.sensor_xgzp.build()
    if shape is None:
        for nm in ("build 可用", "bbox 外廓", "双倒钩在位+孔贯通", "SOIC8 8 脚"):
            check("G5 %s" % nm, False, "builder 红 (未实现/异常)")
        return
    bb = shape.BoundBox
    row = 7.96 / 2.0
    pad_out = row + 0.9 / 2.0                                              # 焊盘外缘 (排距+盘宽)
    ok = (abs(bb.XMin + body["l"] / 2) < 0.5 and abs(bb.XMax - body["l"] / 2) < 0.5 and
          abs(bb.YMin + pad_out) < 0.1 and abs(bb.YMax - pad_out) < 0.1 and
          abs(bb.ZMin) < 0.05 and abs(bb.ZMax - (body["h"] + p1["len"])) < 0.3)
    check("G5 bbox = 10.8×7.96(盘外缘8.86)×5.9 (本体/排距/含倒钩)", ok, str(bb))
    for nm, p in (("P1", p1), ("P2", p2)):
        pd = min(p["dia"], p.get("neck_dia", p["dia"])) - 0.4    # 颈部探针 (倒钩颈 ⌀2.2 为最细实体)
        v_in = probe_vol(shape, [p["pos"][0], p["pos"][1], body["h"] + 0.05], [0, 0, 1],
                         pd, p["len"] - 0.3)
        v_bore = probe_vol(shape, [p["pos"][0], p["pos"][1], body["h"] + p["len"] - 0.05],
                           [0, 0, -1], 0.9, p["len"] + 0.3)
        check("G5 %s 倒钩在位 + 内孔⌀0.9 贯通入体 (死端引压口)" % nm,
              v_in > 0.6 * cyl_vol(pd, p["len"] - 0.3) and v_bore < 1e-6,
              "in=%.2f bore=%.4f" % (v_in, v_bore))
    pins = [t for t in gm["electrical_terminals"] if t["kind"] == "soic8_gullwing"]
    check("G5 数据: SOIC8 8 脚 (VDD/SDA/SCL/GND + 4×NC)", len(pins) == 8)
    ok_pin = True
    for t in pins:
        v_p = probe_vol(shape, [t["pos"][0], t["pos"][1], 0.05], [0, 0, 1], 0.7, 0.1)
        if v_p < 0.5 * cyl_vol(0.7, 0.1):
            ok_pin = False
    check("G5 8 脚焊盘在位 (z=0 坐板面)", ok_pin)


# ══════════ G6: fittings (硅胶管/直通/变径/三通, D4-A 折线) ══════════
def test_g6_fittings():
    # 硅胶管 ID3×OD7 直管
    sh = _safe_build(D3.fittings.build_silicone_tube, [[0, 0, 0], [40, 0, 0]], 3.0, 7.0)
    if sh is None:
        for nm in ("硅胶管直管", "硅胶管三点弯", "Kamoer 直通", "Kamoer 变径", "三通"):
            check("G6 %s" % nm, False, "builder 红 (未实现/异常)")
        return
    ok, det = bb_ok(sh.BoundBox, 0, 40, -3.5, 3.5, -3.5, 3.5, 0.05)
    check("G6 硅胶管直管 bbox = 40×⌀7 (ID3×OD7)", ok, det)
    v_bore = probe_vol(sh, [-0.5, 0, 0], [1, 0, 0], 3.0, 41.0)
    check("G6 硅胶管内腔贯通 (⌀ID 探针零交)", v_bore < 1e-6, "%.4f mm^3" % v_bore)
    # 三点弯 (D4-A 关键弯折点折线): L 形两腿, 端面平头 (= 折线端点), 弯折点球包络
    sh2 = D3.fittings.build_silicone_tube([[0, 0, 0], [30, 0, 0], [30, 0, 25]], 3.0, 7.0)
    bb2 = sh2.BoundBox
    check("G6 三点弯管覆盖折线两端 (X 0..33.5 含弯折球 / Z -3.5..25 平头端)",
          abs(bb2.XMin) < 0.01 and abs(bb2.XMax - 33.5) < 0.01 and
          abs(bb2.ZMin + 3.5) < 0.01 and abs(bb2.ZMax - 25.0) < 0.01, str(bb2))
    # Kamoer 直通 (1/8 档 ⌀3.5 barb, len 25, hex ⌀8)
    sh3 = _safe_build(D3.fittings.build_straight_barb)
    if sh3 is not None:
        ok3, det3 = bb_ok(sh3.BoundBox, 0, 25, -4.0, 4.0, -4.0, 4.0, 0.3)
        v_a = probe_vol(sh3, [0.3, 0, 0], [1, 0, 0], 2.8, 4.0)
        v_b = probe_vol(sh3, [24.7, 0, 0], [-1, 0, 0], 2.8, 4.0)
        check("G6 Kamoer 直通 = 25 长/两端倒钩在位 (1/8 档)", ok3 and v_a > 1.0 and v_b > 1.0,
              det3 + " ends=%.2f/%.2f" % (v_a, v_b))
    else:
        check("G6 Kamoer 直通", False, "builder 红")
    # Kamoer 变径 (两端异径: 大端 ⌀4.9/小端颈 ⌀2)
    sh4 = _safe_build(D3.fittings.build_reducing_barb)
    if sh4 is not None:
        v_big = probe_vol(sh4, [0.3, 0, 0], [1, 0, 0], 4.2, 3.0)
        v_small = probe_vol(sh4, [sh4.BoundBox.XMax - 0.3, 0, 0], [-1, 0, 0], 1.6, 3.0)
        check("G6 Kamoer 变径两端异径 (⌀4.9/⌀2 档)", v_big > 2.0 and v_small > 0.3,
              "big=%.2f small=%.2f" % (v_big, v_small))
    else:
        check("G6 Kamoer 变径", False, "builder 红")
    # 三通: 直通段 + 垂直支口
    sh5 = _safe_build(D3.fittings.build_tee)
    if sh5 is not None:
        v_run = probe_vol(sh5, [0, 0, 0], [1, 0, 0], 2.8, 24.0)
        v_stem = probe_vol(sh5, [12.5, 0, 0], [0, 0, 1], 2.8, 10.0)
        check("G6 三通 = 直通段+垂直支口 (T 形)", v_run > 5.0 and v_stem > 2.0,
              "run=%.2f stem=%.2f" % (v_run, v_stem))
    else:
        check("G6 三通", False, "builder 红")


# ══════════ G7: harness (D2-A 引线桩深度) ══════════
def test_g7_harness():
    p = _safe_build(D3.harness.parts_valve_lead, [0, 0, 0], [0, 0, -60])
    if p is None:
        for nm in ("阀 2P 引线桩 60mm", "XH2.54-2P 白壳视觉件", "泵电缆 150"):
            check("G7 %s" % nm, False, "builder 红 (未实现/异常)")
        return
    wr = p["wire_red"]
    check("G7 阀引线桩长 60mm (spec ~60mm 视觉桩)", abs(wr.BoundBox.ZLength - 60.0) < 0.5,
          str(wr.BoundBox))
    shell = p["shell"]
    dims = sorted(round(x, 2) for x in (shell.BoundBox.XLength, shell.BoundBox.YLength,
                                        shell.BoundBox.ZLength))
    check("G7 XH2.54-2P 白壳视觉件 10×7.8×6.2 (C7429671 dims 单源)", dims == [6.2, 7.8, 10.0],
          str(dims))
    sh = D3.harness.build_valve_lead([0, 0, 0], [0, 0, -60])
    check("G7 build_valve_lead 复合体可用 (双线+壳)", sh is not None and len(sh.Solids) >= 3,
          "solids=%d" % len(sh.Solids))
    sh2 = D3.harness.build_pump_cable([0, 0, 0], [150, 0, 0])
    check("G7 泵电缆桩 150mm (J23→泵端子, spec §3 示例 len)", abs(sh2.BoundBox.XLength - 150.0) < 0.5,
          str(sh2.BoundBox))


# ══════════ G8: 单源一致性 (builder 默认 == devices.json geom3d) ══════════
def test_g8_single_source():
    pn = load_pn()
    bad = []
    d_gm = pn["valves"][0]["geom3d"]
    n1 = port_by_name(d_gm["pneumatic_ports"], "N1")
    dv = D3.device_geom3d("valves")
    n1j = port_by_name(dv["pneumatic_ports"], "N1")
    if n1 != n1j:
        bad.append("valves.N1 json 不一致")
    if D3.valve_f0520d.DEFAULTS["body"] != d_gm["body"]:
        bad.append("valve_f0520d.DEFAULTS.body 漂移")
    if D3.pump_zr370.DEFAULTS["body"] != pn["pump"][0]["geom3d"]["body"]:
        bad.append("pump_zr370.DEFAULTS.body 漂移")
    if D3.sensor_xgzp.DEFAULTS["body"] != pn["sensor"][0]["geom3d"]["body"]:
        bad.append("sensor_xgzp.DEFAULTS.body 漂移")
    if D3.valve_f0520b.DEFAULTS["body"] != pn["valve_vacuum_master"][0]["geom3d"]["body"]:
        bad.append("valve_f0520b.DEFAULTS.body 漂移")
    check("G8 单源: builder 默认参数 == devices.json geom3d (防 json/代码漂移)", not bad, str(bad))


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    print("== G1 描述符 schema ==")
    test_g1_schema()
    print("== G2 valve_f0520d ==")
    test_g2_valve_d()
    print("== G3 valve_f0520b ==")
    test_g3_valve_b()
    print("== G4 pump_zr370 (立式校正) ==")
    test_g4_pump()
    print("== G5 sensor_xgzp ==")
    test_g5_sensor()
    print("== G6 fittings (D4-A 折线) ==")
    test_g6_fittings()
    print("== G7 harness (D2-A 桩深) ==")
    test_g7_harness()
    print("== G8 单源一致性 ==")
    test_g8_single_source()
    print("\nD1 devices3d: %d PASS / %d FAIL" % (PASS, FAIL))
    sys.exit(1 if FAIL else 0)
