# -*- coding: utf-8 -*-
"""connections_render — connections.json → webapp 渲染 payload (D4, spec 2026-10-05 §5)。

把连接图谱三类边解析为 scene-3d 可直接渲染的**世界坐标折线** (壳系 Z-up, 与 meshes/*.stl
同源), 连同端点锚定部件 (爆炸端跟随) 与器件级三类连接计数 (点击高亮/UI 提示消费):

    build_render_payload() -> {
      "meta":   {coord, source, placement_note, generated_by},
      "devices": {ref: {"name": ...}},                      # 位号 → 显示名
      "edges":  [{i, cls, kind, from, to, render, path, radius, follow, fit_pending, desc}],
      "counts": {ref: {"pneumatic": n, "electrical": n, "mechanical": n}},
    }

设计裁定落地点 (全为数据消费, 不改 connections.json 本体):
  · D4-A 折线路径: tube 边渲染 = 端点世界位 + 最小几何弯折点折线 (数据 tube.bend 为
    采购下料名义值 2, 实际折线弯折 2~4 点 —— 壁孔过越/障碍让位必须的诚实差, meta 声明);
  · D2-A 引线桩: 阀 2P 引线/泵电缆 = 视觉桩折线 (阀阵引线按 case_geom "软引线, 物理自由"
    注记拱越塔顶, 落入 B 壁 J 带插座; 泵电缆经 R 壁 J23 槽 → 泵模块出线孔 → 电机端子);
  · socket/ambient 边 (tube=null) 无几何渲染 —— 插接接触已由器件精确模型表达;
  · mech 边无几何 (翻边夹持/螺丝/回流焊 = 接触关系), 仅计入 counts 供 UI 提示。

纯 stdlib (case_geom 同为纯 Python); devices3d.__init__ 的 stdlib 面供 geom3d 读取。
放置真值来源 (逐器件, 与 export 管线 make_meshes D4 段同源):
  · 阀阵 11 只   case_geom.valve_grid() (x, y, kind) + 装配锚: D=底面坐盖顶 TOWER_Z0
                 (devices.json install "13×15 底面着板方向"); VV(F0520B) 按 ⌀4.6 嘴充满
                 ⌀4.8 承口带锚定 (origin z=SOCK_D_B 面, 见 _VALVE_ORIGIN_Z 推导);
  · 泵 ZR370     geom/make_pump_module 装配位 (轴沿 X, z=PUMP_AXIS_Z-本地轴高);
  · 传感 XGZP    pos.csv U6 焊盘中心 board_to_case + 航向 -90° (封装跨距 7.96 沿壳系 X,
                 本体长轴沿 Y —— 与 parts_f 盒 7.96×10.6 一致; P1 落天花过孔 (48.5,27) 邻位);
  · J10-J23      pos.csv 焊盘中心 board_to_case, 插座顶 z=Z_TOP+6.2 (XH-2P h)。
"""
import csv
import json
import os
import sys
from pathlib import Path

_ROOT = str(Path(__file__).resolve().parents[2])
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
from flowio.geom import case_geom as G                      # noqa: E402  纯 Python 装配常量
from flowio.twin.devices3d import DEVICES_JSON              # noqa: E402  真值文件定位

CONNECTIONS_JSON = Path(_ROOT) / "hardware" / "flowio-p1" / "enclosure" / "connections.json"
POSCSV = Path(_ROOT) / "hardware" / "flowio-p1" / "fab" / "flowio-p1-pos.csv"

# ---- 阀放置锚 (与 make_meshes D4 段逐字同源 —— 单一实现, 改一处两处同步) ----
# F0520D (kind D): 安装态 = N2 端面坐壳盖顶 (origin z = TOWER_Z0);
#   N1 嘴 (本地 20.5..23.5) → 世界 42.0..45.0, 落歧管承口带 (36.5..46) ✓
# F0520B (kind B, VV): N2 端面 z 使 N1 嘴 (本地 28..34) 充满承口带 (44..50):
#   origin z = 44.0 - 28.0 = 16.0 (体顶 44.0 贴块底, 0 隙面接触; N2 嘴尖 13.0 隐入腔内)
VALVE_ORIGIN_Z_D = G.TOWER_Z0                                # 21.5
VALVE_ORIGIN_Z_B = G.MAN_Z0 - G._PNEU["vb_h"]                # 16.0 (44 - 28)

# 阀引线拱越高度: 阀阵最高点 (VV 嘴尖 49.75 落承口带; 体顶 43.75) 与歧管块底 (44.0)
# 之间的净空带 —— 跨越段 z=43.5 自阀顶上方 1.5mm 处越过, 距块底 0.5mm (视觉无碰),
# 出壁段沿壳外壁面下落, 经 B/R 壁 TERM 槽带 (z 8.8..15.4) 插入 J 插座 (真实插装方向)。
LEAD_ARC_Z = G.MAN_Z0 - 0.5                                  # 43.5
J_TOP_DZ = 6.2                                               # XH-2P 座高 (devices C7429671)

_DEVICE_NAMES = {
    "V1": "通道阀 V1 (F0520D)", "V2": "通道阀 V2 (F0520D)", "V3": "通道阀 V3 (F0520D)",
    "V4": "通道阀 V4 (F0520D)", "V5": "通道阀 V5 (F0520D)", "V6": "通道阀 V6 (F0520D)",
    "V7": "通道阀 V7 (F0520D)", "V8": "通道阀 V8 (F0520D)",
    "VS": "充气主阀 VS (F0520D)", "VV": "真空主阀 VV (F0520B)", "VF": "排气主阀 VF (F0520D)",
    "P1": "微型真空泵 ZR370-03PM", "S1": "微差压传感 XGZP6897D (U6)",
    "Main": "主模块", "PMod": "泵模块", "ATM": "大气",
}


def load_pos():
    """pos.csv → {ref: {x, y, rot, side}} (KiCad 板系; 与 make_meshes.load_pos 同口径)."""
    out = {}
    with open(POSCSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            ref = (row["Ref"] or "").strip()
            if not ref or ref.upper().startswith("H"):
                continue
            out[ref] = {"x": float(row["PosX"]), "y": float(row["PosY"]),
                        "rot": float(row["Rot"]), "side": (row["Side"] or "").strip().lower()}
    return out


def valve_places():
    """11 阀壳系放置 [{ref, x, y, kind, oz}] (序 = connections/位号序 V1..VF)."""
    order = ["V1", "V2", "V3", "V4", "V5", "V6", "V7", "V8", "VS", "VV", "VF"]
    grid = G.valve_grid()                                    # (x, y, kind) 位号序同上
    out = []
    for ref, (x, y, kind) in zip(order, grid):
        out.append({"ref": ref, "x": x, "y": y, "kind": kind,
                    "oz": VALVE_ORIGIN_Z_B if kind == "B" else VALVE_ORIGIN_Z_D})
    return out


def pump_place():
    """泵 ZR370 器件原点 (壳系): 泵头端面轴心 @最低体点 —— 与 make_pump_module 装配位同式."""
    pl = G._PNEU["pump_l"]                                   # 58.1
    return (G.PMOD_OFF[0] + G.PMOD_CX - pl / 2.0,            # 140.2 (头端面贴内腔 x0=T+CLR)
            G.PMOD_OFF[1] + G.PMOD_CY,                       # 42.9
            G.PUMP_AXIS_Z - 12.0)                            # 6.4 (本地轴高 12 → 壳系轴 18.4)


def sensor_place(pos):
    """XGZP (U6) 器件原点 (壳系): 焊盘中心贴板面 + 航向 -90° (体长轴 → 壳系 +Y)."""
    u6 = pos["U6"]
    cx, cy = G.board_to_case(u6["x"], u6["y"])               # (46.9, 24.9)
    assert int(u6["rot"]) % 360 == 0, "U6 rot 非 0: 放置航向需复核"
    return (cx, cy, G.Z_TOP)


def _port_tip(device, port, places, pplace, splace):
    """气动口**口端**世界坐标 (geom3d pos 沿 dir 外推 len)."""
    gm = _geom3d_of(device)
    q = next(p for p in gm["pneumatic_ports"] if p["name"] == port)
    if device.startswith(("V", )) and device != "VF" or device in ("VS", "VV", "VF"):
        pl = next(v for v in places if v["ref"] == device)
        base = (pl["x"], pl["y"], pl["oz"])
    elif device == "P1":
        base = pplace
    elif device == "S1":
        base = splace
        # 体长轴航向 -90°: 本地 (x,y,z) → 壳系 (cx + y, cy + x, cz + z)?? —— 本地 X(长轴)
        # 旋至 -Y: case = R(-90°)·local, R: (lx,ly)→(ly,-lx)
        lx, ly, lz = q["pos"]
        tip = (base[0] + ly + q["dir"][1] * q["len"],
               base[1] - lx - q["dir"][0] * q["len"],
               base[2] + lz + q["dir"][2] * q["len"])
        return list(tip)
    else:
        raise KeyError("气动口器件 %s 无放置" % device)
    return [base[0] + q["pos"][0] + q["dir"][0] * q["len"],
            base[1] + q["pos"][1] + q["dir"][1] * q["len"],
            base[2] + q["pos"][2] + q["dir"][2] * q["len"]]


_GM_CACHE = {}


def _geom3d_of(device):
    if device not in _GM_CACHE:
        from flowio.twin.devices3d import load_geom3d
        gm = load_geom3d()
        if device == "P1":
            _GM_CACHE[device] = gm["pump"]
        elif device == "S1":
            _GM_CACHE[device] = gm["sensor"]
        else:
            vv = device == "VV"
            _GM_CACHE[device] = gm["valve_vacuum_master" if vv else "valves"]
    return _GM_CACHE[device]


def _anchor_index(places, pplace, splace, pos):
    """端点 → (世界坐标, 锚定部件 id) 字典 (边端点解析单源)."""
    a = {}
    for v in places:
        gm = _geom3d_of(v["ref"])
        for p in gm["pneumatic_ports"]:
            tip = _port_tip(v["ref"], p["name"], places, pplace, splace)
            a["%s.%s" % (v["ref"], p["name"])] = (tip, "valves")
        for t in gm["electrical_terminals"]:
            if t["kind"] == "wire":                          # 引线出体端 (桩起点)
                a["%s.ESCAPE" % v["ref"]] = (
                    [v["x"] + t["pos"][0], v["y"] + t["pos"][1] - G._PNEU["vd_d"] / 2 - 8.0,
                     v["oz"] + t["pos"][2]], "valves")
    p_gm = _geom3d_of("P1")
    for p in p_gm["pneumatic_ports"]:
        a["P1.%s" % p["name"]] = (_port_tip("P1", p["name"], places, pplace, splace), "pump")
    for t in p_gm["electrical_terminals"]:
        a["P1.%s" % t["name"]] = ([pplace[0] + t["pos"][0], pplace[1] + t["pos"][1],
                                   pplace[2] + t["pos"][2]], "pump")
    s_gm = _geom3d_of("S1")
    for p in s_gm["pneumatic_ports"]:
        a["S1.%s" % p["name"]] = (_port_tip("S1", p["name"], places, pplace, splace), "pcb")
    # 模块面 (case_geom 单源)
    for i, x in enumerate(G.CH_PORT_X):
        a["Main.CH%d" % (i + 1)] = ([x, G.OH, G.PORT_Z_CH], "case_bottom")
    a["Main.S_wall"] = ([G.OW, 20.4, G.PORT_Z_LOW], "case_bottom")
    a["Main.V_wall"] = ([G.OW, 31.4, G.PORT_Z_LOW], "case_bottom")
    a["Main.F_wall"] = ([G.OW, 42.4, G.PORT_Z_LOW], "case_bottom")
    a["Main.M_tap"] = ([G.SENS_TAP[0] + 5.0, G.SENS_TAP[1], G.SENS_TAP[2]], "manifold")
    a["Main.M"] = a["Main.M_tap"]                            # 测压支路自公共腔测压嘴引出
    # J 插座 (pos.csv 焊盘中心, 插座顶面)
    for j in ("J10", "J11", "J12", "J13", "J14", "J15", "J16", "J17",
              "J20", "J21", "J22", "J23"):
        p = pos[j]
        a["Main.%s" % j] = ([G.board_to_case(p["x"], p["y"])[0],
                             G.board_to_case(p["x"], p["y"])[1],
                             G.Z_TOP + J_TOP_DZ], "pcb")
    # 泵模块面板 (make_pump_module 面板孔位: S=y c-8 / V=y c+8, z=轴; 出线孔 z=6)
    px = G.PMOD_OFF[0] + G.PMOD_L
    py = G.PMOD_OFF[1] + G.PMOD_CY
    a["PMod.S_panel"] = ([px, py - G.PMOD_PORT_DY, G.PUMP_AXIS_Z], "pump_case")
    a["PMod.V_panel"] = ([px, py + G.PMOD_PORT_DY, G.PUMP_AXIS_Z], "pump_case")
    a["PMod.cable_2p"] = ([px, py, G.PMOD_WIRE_Z], "pump_case")
    return a


def _dedupe(pts):
    out = [pts[0]]
    for p in pts[1:]:
        if abs(p[0] - out[-1][0]) > 1e-6 or abs(p[1] - out[-1][1]) > 1e-6 \
           or abs(p[2] - out[-1][2]) > 1e-6:
            out.append(p)
    return out


def _tube_path(key, pa, pb, places, pplace, splace):
    """tube 边最小弯折点折线 (D4-A; 端点顺序 = from→to). key = (from, to)."""
    f_dev, t_dev = key[0].split(".")[0], key[1].split(".")[0]
    # 1) 主阀 N2 ↔ R 壁 S/V/F 孔: 竖落到低带 z → 沿 y 横行 → 入壁孔
    if f_dev in ("VS", "VV", "VF") or t_dev in ("VS", "VV", "VF"):
        v = next(v for v in places if v["ref"] in (f_dev, t_dev))
        wall = pa if t_dev in ("VS", "VV", "VF") else pb
        tip = pb if t_dev in ("VS", "VV", "VF") else pa
        return _dedupe([tip, [tip[0], tip[1], wall[2]], wall])
    # 2) 通道阀 N2 ↔ B 壁 CH 孔: 落到过孔 z → 对齐孔 x → 穿墙
    if "Main.CH" in key[0] or "Main.CH" in key[1]:
        ch = pa if key[0].startswith("Main.CH") else pb
        tip = pb if key[0].startswith("Main.CH") else pa
        return _dedupe([tip, [tip[0], tip[1], ch[2]], [ch[0], tip[1], ch[2]], ch])
    # 3) 泵顶嘴 ↔ 泵模块面板快插 (模块内跳管): 嘴旁肘部让开盖板 → 斜入面板口
    if f_dev == "P1" or t_dev == "P1":
        noz = pa if f_dev == "P1" else pb
        pan = pb if f_dev == "P1" else pa
        elbow = [noz[0] + 12.0, noz[1], noz[2] - 4.0]
        return _dedupe([noz, elbow, pan])
    # 4) 泵模块面板 ↔ 主壳 S/V 壁孔 (模块间干管): 中间垂弯点 (旧 tubes.stl 同式)
    if "PMod" in key[0] or "PMod" in key[1]:
        wall = pa if "PMod" in key[1] else pb
        pan = pb if "PMod" in key[1] else pa
        mid = [G.OW + 44.0, wall[1], G.PORT_Z_LOW + 3.0]
        return _dedupe([pan, mid, wall])
    # 5) 歧管测压嘴 ↔ XGZP P1 (测压支路): 嘴上翻 → 越歧管顶横渡 → 天花过孔垂直下行 → 倒钩
    if "Main.M" in key[0]:
        p1 = pb
        ceil_hole = [G.CEIL_SENS[0], G.CEIL_SENS[1], G.Z_CEIL - 2.0]
        over_z = G.MAN_Z1 + 3.0
        return _dedupe([pa, [pa[0], pa[1], over_z],
                        [ceil_hole[0], ceil_hole[1], over_z], ceil_hole, p1])
    raise KeyError("tube 边 %s 无路由规则" % (key,))


def _lead_path(a, from_key, to_key):
    """阀引线桩 (D2-A "诚实的不精确"): 出体位 → 爬升 → 沿阀阵顶/歧管块底净空带 (43.5)
    横渡 → 沿壳**外壁**下落 → 穿 B/R 壁 TERM 槽插入 J 插座顶 (真实插装方向)。
    折线 5 点; 柔顺垂感由渲染层 CatmullRom 平滑 (flows 同视觉语言)。"""
    esc_key = from_key.replace(".CONN_2P", ".ESCAPE")        # 桩起点 = 引线出体端
    esc = a[esc_key][0]
    jtop = a[to_key][0]
    jface = to_key.split(".")[1]
    if jface in ("J20", "J21", "J22", "J23"):                # R 壁插座: 从 +X 外侧插入
        approach = [G.OW + 3.0, jtop[1], 0.0]
    else:                                                    # B 壁 TERM 带: 从 +Y 外侧插入
        approach = [jtop[0], G.OH + 3.0, 0.0]
    approach[2] = jtop[2]
    return _dedupe([esc, [esc[0], esc[1], LEAD_ARC_Z],
                    [approach[0], approach[1], LEAD_ARC_Z],
                    approach, jtop])


def _cable_path(a, key_from, key_to):
    """泵电缆桩: J23 插座顶 → R 壁 J23 槽外折点 → 泵模块出线孔."""
    j = a[key_from][0]
    w = a[key_to][0]
    return _dedupe([j, [G.OW + 8.0, j[1], (j[2] + w[2]) / 2.0], w])


def _motor_wire(a, end):
    """出线孔 → 电机端子 (模块腔内短桩)."""
    w = a["PMod.cable_2p"][0]
    mid = [(w[0] + end[0]) / 2.0 + 1.0, (w[1] + end[1]) / 2.0, (w[2] + end[2]) / 2.0]
    return _dedupe([w, mid, end])


def build_render_payload(path=None):
    """connections.json → 渲染 payload (见模块 docstring)."""
    path = Path(path) if path else CONNECTIONS_JSON
    conn = json.loads(path.read_text(encoding="utf-8"))
    places = valve_places()
    pos = load_pos()
    pplace = pump_place()
    splace = sensor_place(pos)
    a = _anchor_index(places, pplace, splace, pos)

    edges = []
    counts = {}
    for dev in _DEVICE_NAMES:
        counts[dev] = {"pneumatic": 0, "electrical": 0, "mechanical": 0}

    def dev_of(endpoint):
        return endpoint.split(".")[0]

    def face_of(endpoint):
        return endpoint.split(".", 1)[1]

    def note(dev):
        if dev in counts:
            return
        counts[dev] = {"pneumatic": 0, "electrical": 0, "mechanical": 0}

    for cls, arr in (("pneumatic", conn["pneumatic_edges"]),
                     ("electrical", conn["electrical_edges"]),
                     ("mechanical", conn["mechanical_edges"])):
        for e in arr:
            d0, d1 = dev_of(e["from"]), dev_of(e["to"])
            note(d0)
            note(d1)
            counts[d0][cls] += 1
            if d1 != d0:
                counts[d1][cls] += 1

    def add(cls, e, render, pth=None, radius=None, follow=None):
        # 锚定部件序列 (逐点): 首点=from 侧部件, 末点=to 侧部件, 内点对半归属 ——
        # scene-3d 爆炸端跟随按点取锚 (spec §5 "连接边随爆炸端点跟随, 管/线拉伸可视")
        anchors = None
        if pth:
            f, t = follow
            n = len(pth)
            anchors = [f] + [f if i < (n - 2) / 2 else t for i in range(n - 2)] + [t]
        edges.append({
            "i": len(edges), "cls": cls, "kind": e.get("kind"),
            "from": e["from"], "to": e["to"],
            "render": render if pth else "none",
            "path": pth, "anchors": anchors, "radius": radius,
            "follow": follow or [dev_of(e["from"]), dev_of(e["to"])],
            "fit_pending": bool(e.get("fit_pending")) or bool(e.get("inferred")),
            "desc": e.get("desc", ""),
        })

    for e in conn["pneumatic_edges"]:
        tube = e.get("tube")
        if not tube:
            add("pneumatic", e, "none")                      # socket/ambient: 插接无几何
            continue
        pth = _tube_path((e["from"], e["to"]), a[e["from"]][0], a[e["to"]][0],
                         places, pplace, splace)
        add("pneumatic", e, "tube", pth, radius=tube["od"] / 2.0,
            follow=[a[e["from"]][1], a[e["to"]][1]])
    for e in conn["electrical_edges"]:
        if e["kind"] == "lead_2p":
            add("electrical", e, "wire", _lead_path(a, e["from"], e["to"]), radius=0.55,
                follow=["valves", a[e["to"]][1]])
        elif e["kind"] == "cable_2p":
            add("electrical", e, "wire", _cable_path(a, e["from"], e["to"]), radius=0.9,
                follow=[a[e["from"]][1], a[e["to"]][1]])
        elif e["kind"] == "wire":
            add("electrical", e, "wire", _motor_wire(a, a[e["to"]][0]), radius=0.75,
                follow=[a[e["from"]][1], a[e["to"]][1]])
        else:
            add("electrical", e, "none")
    for e in conn["mechanical_edges"]:
        add("mechanical", e, "none")

    return {
        "meta": {
            "coord": "shell: 壳系 Z-up, 下壳外角原点 (与 meshes/*.stl 同源, 无翻转)",
            "source": "hardware/flowio-p1/enclosure/connections.json (真值, 只读) + "
                      "devices.json geom3d 端点 + case_geom 放置常量 + pos.csv 焊盘中心",
            "generated_by": "flowio/twin/connections_render.build_render_payload()",
            "placement_note": {
                "valves": "D 阀 origin z=TOWER_Z0 (底面坐盖顶, devices.json install 1a); "
                          "VV origin z=MAN_Z0-28=16.0 (N1 ⌀4.6 充满 ⌀4.8 承口带 44..50)",
                "pump": "make_pump_module 装配位 (轴沿 X @z18.4, 头端面 x=140.2)",
                "sensor": "pos.csv U6 焊盘中心 board_to_case(44,-22) 航向 -90°",
                "lead_arc_z": LEAD_ARC_Z,
                "bend_note": "tube.bend=2 为采购下料名义值; 渲染折线按最小几何弯折 (2~4 点, "
                             "壁孔过越/障碍让位) —— 段长和仍可核算下料",
            },
        },
        "devices": {k: {"name": v} for k, v in _DEVICE_NAMES.items()},
        "edges": edges,
        "counts": counts,
    }


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    d = build_render_payload()
    n_render = sum(1 for e in d["edges"] if e["render"] != "none")
    print("[connections_render] edges=%d rendered=%d (tube=%d wire=%d) devices=%d"
          % (len(d["edges"]), n_render,
             sum(1 for e in d["edges"] if e["render"] == "tube"),
             sum(1 for e in d["edges"] if e["render"] == "wire"),
             len(d["devices"])))
    for e in d["edges"]:
        if e["render"] != "none":
            print("  [%2d] %-10s %-22s -> %-22s pts=%d r=%.2f%s"
                  % (e["i"], e["render"], e["from"], e["to"], len(e["path"]),
                     e["radius"] or 0, "  ~fit_pending" if e["fit_pending"] else ""))
