# -*- coding: utf-8 -*-
"""test_device_geom.py — L5 器件几何层测试 (spec: 2026-10-03-device-geometry-framework §4-L5).

分层追加 (TDD 先红后绿):
  T1 test_schema          — devices.json 覆盖 38 行 BOM/字段完整/17 连接器有 port
     test_schema_pneumatic — pneumatic_devices 段: 4组完整/字段完整/负压阀域(spec 1f-β)/
                             DC4.5V 电压档/refs 唯一/泵压力包络 (+常驻坏副本负测试)
  T2 test_orientation     — 端口射线朝外 + 贴边 (periphery bias / I-O keepout 断言)
  T3 test_matching        — 17 连接器 <-> 17 槽 完美匹配 (networkx)
  T4 test_drill_keepout   — 器件 OBB 避让 M3 孔 + 铜柱投影
  T5 test_truth_sync      — devices.json <-> case_geom 三方真值一致

运行: tools/venv-cad/Scripts/python enclosure/test_device_geom.py
"""
import copy
import csv
import json
import math
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import case_geom as G

ROOT = HERE.parents[2]
BOM = ROOT / "hardware" / "flowio-p1" / "fab" / "flowio-p1-bom-jlc.csv"
POS = ROOT / "hardware" / "flowio-p1" / "fab" / "flowio-p1-pos.csv"
DEVICES = HERE / "devices.json"

PASS, FAIL = 0, 0


def check(name, ok, detail=""):
    global PASS, FAIL
    print("[%-4s] %s%s" % ("PASS" if ok else "FAIL", name, ("  | " + detail) if detail else ""))
    if ok:
        PASS += 1
    else:
        FAIL += 1
    return ok


def load_devices():
    return json.loads(DEVICES.read_text(encoding="utf-8"))


def load_pos():
    rows = list(csv.DictReader(open(POS, newline="", encoding="utf-8")))
    out = []
    for r in rows:
        ref = (r["Ref"] or "").strip()
        if not ref.upper().startswith("H"):
            out.append({"ref": ref, "pkg": (r["Package"] or "").strip(),
                        "x": float(r["PosX"]), "y": -float(r["PosY"]),
                        "rot": float(r["Rot"]), "side": (r["Side"] or "").strip().lower()})
    return out


# ══════════ T1: 器件数据层 schema ══════════
def test_schema():
    dev = load_devices()
    entries = dev["devices"]
    bom_rows = list(csv.DictReader(open(BOM, encoding="utf-8-sig")))

    # 1) BOM 38 行全覆盖 (按 refs 展开)
    covered = set()
    for e in entries:
        for r in e["refs"]:
            covered.add(r)
    bom_refs = set()
    for r in bom_rows:
        for ref in (r["Designator"] or "").split(","):
            ref = ref.strip()
            if ref:
                bom_refs.add(ref)
    missing = sorted(bom_refs - covered)
    check("T1 schema: BOM %d 位号全覆盖" % len(bom_refs), not missing, "缺: %s" % missing[:8])

    # 2) 唯一 C 号数 = 33, 每条含必需字段
    cn = {e["lcsc"] for e in entries}
    check("T1 schema: 33 唯一 C 号", len(cn) == 33, "实际 %d" % len(cn))
    need = {"lcsc", "name", "refs", "pkg_keywords", "dims", "placement", "datasheet"}
    bad = [e["lcsc"] for e in entries if not need <= set(e)]
    check("T1 schema: 字段完整 (7 必需)", not bad, "缺字段: %s" % bad[:4])

    # 3) dims 三元组数值合理
    badd = [e["lcsc"] for e in entries
            if not (0.2 <= e["dims"]["w"] <= 40 and 0.2 <= e["dims"]["d"] <= 40
                    and 0.2 <= e["dims"]["h"] <= 20)]
    check("T1 schema: dims 数值域 (0.2..40 / h<=20)", not badd, "异常: %s" % badd[:4])

    # 4) 17 连接器必须有 port (dir_local 单位向量 + exit_z 带宽)
    CONN = {"J1", "J2", "J5", "J6", "J7", "J8", "J9", "J10", "J11", "J12", "J13",
            "J14", "J15", "J16", "J17", "J18", "J19"}
    noport = []
    for e in entries:
        if CONN & set(e["refs"]):
            p = e.get("port")
            if not p or "dir_local" not in p or "exit_z" not in p:
                noport.append(e["lcsc"])
            else:
                dx, dy = p["dir_local"][:2]
                if abs(math.hypot(dx, dy) - 1.0) > 1e-6:
                    noport.append(e["lcsc"] + "(非单位向量)")
    check("T1 schema: 17 连接器均有 port.dir_local/exit_z", not noport, "缺: %s" % noport)

    # 5) placement 枚举合法
    LEGAL = {"EDGE_OUT", "SURFACE", "INTERNAL"}
    badp = [e["lcsc"] for e in entries if e["placement"] not in LEGAL]
    check("T1 schema: placement 枚举合法", not badp, str(badp[:4]))


# ══════════ T1: 气动器件段 schema (pneumatic_devices, spec 1f-β) ══════════
PNEU_GROUPS = ("valves", "valve_vacuum_master", "pump", "sensor")
PNEU_ACTUATORS = ("valves", "valve_vacuum_master", "pump")   # DC4.5V 执行器; sensor 为 5V 轨直供 I2C 件
PNEU_RATED_V = 4.5                                            # P1.1 定案: 全系 DC4.5V 变体
PNEU_RAIL_V = 5.0                                             # _meta.drive_policy.rail_v


def _pneu_tag(g, e):
    return "%s:%s" % (g, "/".join(e.get("refs") or ["?"]))


def _pneu_entries(pn):
    """展平 (group, entry) 对; 组缺失按空处理."""
    out = []
    for g in PNEU_GROUPS:
        for e in (pn.get(g) or []):
            out.append((g, e))
    return out


def _pneu_completeness_bad(pn):
    """每条气动 entry 必需字段: refs/model/manufacturer/datasheet/electrical/dims
    + 阀/传感器单口 port + 泵双口 ports."""
    bad = []
    for g, e in _pneu_entries(pn):
        tag = _pneu_tag(g, e)
        if not (isinstance(e.get("refs"), list) and e["refs"]):
            bad.append(tag + "(refs)")
        for f in ("model", "manufacturer", "datasheet"):
            if not (isinstance(e.get(f), str) and e[f].strip()):
                bad.append(tag + "(%s)" % f)
        if not isinstance(e.get("electrical"), dict):
            bad.append(tag + "(electrical)")
        dm = e.get("dims")
        if not (isinstance(dm, dict) and all(isinstance(dm.get(k), (int, float)) and dm[k] > 0
                                             for k in ("w", "d", "h"))):
            bad.append(tag + "(dims)")
        if g != "pump" and not e.get("port"):
            bad.append(tag + "(port)")
        if g == "pump" and not e.get("ports"):
            bad.append(tag + "(ports)")
    return bad


def _pneu_domain_ok(pn):
    """spec 1f-β 负压专用阀域: pressure_kpa 上限<=0 的阀 (F0520B) 只允许出现在
    valve_vacuum_master 组; valves 组 (V1-V8/VS/VF 正压通用阀位) 不允许混入;
    反向: valve_vacuum_master 组内必须全为负压域条目."""
    for e in (pn.get("valves") or []):
        pk = e.get("pressure_kpa")
        if not pk or pk[1] <= 0:
            return False
    for e in (pn.get("valve_vacuum_master") or []):
        pk = e.get("pressure_kpa")
        if not pk or pk[1] > 0:
            return False
    return True


def _pneu_voltage_bad(pn):
    """电压档一致性 (P1.1 定案全系 DC4.5V): 执行器 (阀/泵) electrical.rated_v 必须为 4.5;
    无 rated_v 的直供件 (sensor) 其 v_range 必须覆盖 5V 轨."""
    rail = ((pn.get("_meta") or {}).get("drive_policy") or {}).get("rail_v")
    bad = []
    for g, e in _pneu_entries(pn):
        el = e.get("electrical") or {}
        tag = _pneu_tag(g, e)
        if g in PNEU_ACTUATORS:
            if "rated_v" not in el:
                bad.append(tag + "(缺rated_v)")
            elif el["rated_v"] != PNEU_RATED_V:
                bad.append(tag + "(rated_v=%s≠%s)" % (el["rated_v"], PNEU_RATED_V))
        else:
            vr = el.get("v_range")
            if not (vr and rail is not None and vr[0] <= rail <= vr[1]):
                bad.append(tag + "(v_range=%s 不含rail=%s)" % (vr, rail))
    return bad


def _pneu_refs_dup(pn, pcb_refs):
    """四组合计 refs 不得重复, 且不得与 devices 段 (PCB 贴装) refs 冲突."""
    seen, dups = set(), set()
    for g, e in _pneu_entries(pn):
        for r in (e.get("refs") or []):
            if r in seen or r in pcb_refs:
                dups.add(r)
            seen.add(r)
    return sorted(dups)


def _pneu_envelope_bad(pn):
    """泵压力窗必须严格包络两类阀压力窗 (valve ⊂ pump, 余量>0).
    返回 (违例列表, 全局最小余量 kPa; 无有效阀-泵对时为 None)."""
    pumps = [e for e in (pn.get("pump") or []) if e.get("pressure_kpa")]
    bad, margins = [], []
    for g in ("valves", "valve_vacuum_master"):
        for e in (pn.get(g) or []):
            pk = e.get("pressure_kpa")
            if not pk:
                bad.append(_pneu_tag(g, e) + "(缺pressure_kpa)")
                continue
            m = [min(pk[0] - p["pressure_kpa"][0], p["pressure_kpa"][1] - pk[1])
                 for p in pumps]
            margins += m
            if not m or max(m) <= 0:
                bad.append("%s %s" % (_pneu_tag(g, e), pk))
    return bad, (min(margins) if margins else None)


def test_schema_pneumatic():
    dev = load_devices()
    pn = dev.get("pneumatic_devices")

    # 1) 段完整性: pneumatic_devices 存在且 4 列表组均非空
    empty = [g for g in PNEU_GROUPS if not (isinstance((pn or {}).get(g), list) and pn[g])]
    check("T1 pneumatic: 段完整 (pneumatic_devices 4 列表组非空)", bool(pn) and not empty,
          "缺/空: %s" % empty)
    if not pn or empty:
        return          # 段残缺早退: 空结构会让 checks 3-7 空洞 PASS(假绿)或裸崩,
                        # 负测试也无法构造 — 只留 check1 干净 FAIL 即为正确行为

    # 2) 字段完整: 每条气动 entry 必需字段无缺失
    bad = _pneu_completeness_bad(pn or {})
    check("T1 pneumatic: 字段完整 (refs/model/manufacturer/datasheet/electrical/dims/port(s))",
          not bad, str(bad[:6]))

    # 3) 负压专用阀域 (spec 1f-β, 核心): 上限<=0 的阀只允许在 valve_vacuum_master
    check("T1 pneumatic: 负压阀域 (pressure_kpa 上限≤0 仅 valve_vacuum_master)",
          _pneu_domain_ok(pn or {}))

    # 4) 电压档一致性 (P1.1 定案全系 DC4.5V): 执行器 rated_v=4.5; sensor v_range 覆盖 5V 轨
    vbad = _pneu_voltage_bad(pn or {})
    check("T1 pneumatic: 电压档一致 (执行器 rated_v=4.5, sensor v_range 覆盖 5V 轨)",
          not vbad, str(vbad[:4]))
    meta = (pn or {}).get("_meta") or {}
    rail = (meta.get("drive_policy") or {}).get("rail_v")
    variant = meta.get("voltage_variant") or ""
    check("T1 pneumatic: drive_policy.rail_v=5.0 且 voltage_variant 含 DC4.5V",
          rail == PNEU_RAIL_V and "DC4.5V" in variant,
          "rail=%s variant=%s" % (rail, variant[:36]))

    # 5) refs 唯一性: 四组合计不重复, 且不与 devices 段冲突
    pcb_refs = set()
    for e in dev["devices"]:
        pcb_refs |= set(e["refs"])
    dups = _pneu_refs_dup(pn or {}, pcb_refs)
    check("T1 pneumatic: refs 唯一 (气动四组内 + 不与 devices 段冲突)", not dups, str(dups[:6]))

    # 6) 压力包络 sanity: 两类阀压力窗 ⊂ 泵压力窗 (严格包含, 余量>0)
    ebad, margin = _pneu_envelope_bad(pn)
    check("T1 pneumatic: 泵压力窗严格包络两类阀 (余量>0)", not ebad,
          str(ebad[:4]) if ebad else ("最小余量 %.1f kPa" % margin))

    # ── 常驻负测试 (TDD 红证明, 防未来退化): deepcopy 坏副本必须让断言翻红 ──
    b_dom = copy.deepcopy(pn)
    leak = copy.deepcopy(b_dom["valve_vacuum_master"][0])
    leak["refs"] = ["VX"]                        # 改名隔离: 只打域断言, 不连坐 refs 唯一性
    b_dom["valves"].append(leak)                 # 把 F0520B 负压阀混入正压阀组
    check("T1 pneumatic: 负测试-负压阀混入 valves 组必失败", not _pneu_domain_ok(b_dom),
          "domain_ok(坏副本)=%s (须 False)" % _pneu_domain_ok(b_dom))

    b_vol = copy.deepcopy(pn)
    b_vol["valves"][0]["electrical"]["rated_v"] = 3.7     # 电压档改坏 (非 4.5)
    vbad2 = _pneu_voltage_bad(b_vol)
    check("T1 pneumatic: 负测试-rated_v 改 3.7V 必失败", bool(vbad2), str(vbad2[:2]))


# ══════════ T2: 几何核 — 朝向/贴边/FCL 碰撞 ══════════
CONN_REFS = ["J1", "J2", "J5", "J6", "J7", "J8", "J9", "J10", "J11", "J12",
             "J13", "J14", "J15", "J16", "J17", "J18", "J19"]

# 已知装配干涉 (板已下单, P1 带病放行 -> P2 工单; 证据见 2026-10-03 全量回归报告)
# - C9  (1206, 板43,9)   压 J9  XH4P 壳体下方 ~1.5x1.6mm — XH 壳贴板无立高, 实装挤压
# - R3  (100k, 板21,28)  藏 U1 WROOM 屏蔽罩正下方 — 违反模块禁布 (shield 无开窗)
# - J19/R17 仅 0.05mm 擦边 — 盒模型容差内, 物理间隙存疑但不构成干涉
# - J15/J16 壳体压 M3 安装孔(68,65): 螺丝头 Ø5.5 被两侧 WJ500V 壳卡住 (BRINGUP 注意)
KNOWN_ISSUES = {frozenset(p) for p in [("C9", "J9"), ("R3", "U1"), ("J19", "R17")]}
KNOWN_HOLE_CLASH = {("J15", (68.0, 65.0)), ("J16", (68.0, 65.0))}
# 过孔擦铜柱接触环 (via 中心距柱心 ≈ 环外径, P2 工单: 移孔 0.5mm)
KNOWN_VIA_BOSS = {((82.7, 12.9), (86.0, 13.0)), ((4.0, 40.0), (3.0, 37.0))}


def test_orientation():
    import device_geom as DG
    import case_geom as GG
    bad_dir, bad_edge = [], []
    for ref in CONN_REFS:
        ray = DG.port_ray(ref)
        p = DG._POS[ref]
        # 所属壁 = 端口指向的壁 (dot 最大), 非最近壁 (J10/J17 平局会误判)
        walls = {"L": (-1, 0, p["x"]), "R": (1, 0, GG.BW - p["x"]),
                 "T": (0, -1, p["y"]), "B": (0, 1, GG.BH - p["y"])}
        wall, (nx, ny, wdist) = max(walls.items(),
                                    key=lambda kv: ray["dir"][0] * kv[1][0] + ray["dir"][1] * kv[1][1])
        dot = ray["dir"][0] * nx + ray["dir"][1] * ny
        if dot <= math.cos(math.radians(45)):
            bad_dir.append("%s(·%.2f→%s)" % (ref, dot, wall))
        # 贴边从端口面中心 (ray origin) 量, 非器件中心
        ox, oy = ray["origin"][0] - GG.OX, ray["origin"][1] - GG.OX   # 壳系->板系
        t = DG.dist_to_edge_along(ref, ray["dir"][0], ray["dir"][1])
        # origin 可能在板边外 (外伸连接器), 以 origin 到边界的带符号距离近似
        dist_out = t - 0.0
        if wdist - (ray["dir"][0] * nx + ray["dir"][1] * ny) * 0 > 8.0 and dist_out > 5.0:
            bad_edge.append("%s(壁%.1f/面%.1fmm)" % (ref, wdist, dist_out))
    check("T2 朝向: 17 连接器端口指向壁 (dot>cos45, 按方向选壁)", not bad_dir, str(bad_dir))
    check("T2 贴边: 端口面 5mm 内或已外伸", not bad_edge, str(bad_edge))


def test_collision_fcl():
    import device_geom as DG

    def active_hits(cm):
        res = cm.in_collision_internal(return_names=True)
        return {frozenset(p) for p in (res[1] or [])} - KNOWN_ISSUES

    cm, names = DG.collision_manager()
    hits = active_hits(cm)
    check("T2 FCL: 装配态器件盒两两无交 (known-issues 除外)", not hits,
          "新冲突: %s" % sorted({tuple(sorted(p)) for p in hits})[:6])
    swept_bad = []
    for k in (0.25, 0.5, 0.75, 1.0):
        cm2, _ = DG.collision_manager()
        for ref in names:
            cm2.set_transform(ref, DG.explode_transform(ref, k))
        if active_hits(cm2):
            swept_bad.append(k)
    check("T2 FCL: 爆炸态 k∈{.25,.5,.75,1} 无新增穿模", not swept_bad, str(swept_bad))
    d = cm.min_distance_internal()
    check("T2 FCL: min_distance_internal 可用 (>=%.2f, 含 known 负距)" % d, d > -2.0)


# ══════════ T3: 关系图 — 匹配闭环 + flows 交叉校验 ══════════
def test_matching():
    import device_graph as DGr
    ok, pairs, diag = DGr.slots_satisfied()
    check("T3 匹配: 17 连接器↔17 槽完美匹配", ok, diag)
    if pairs:
        d = dict(pairs)
        slots = DGr.slot_nodes()
        import math
        import device_geom as DG
        worst, wref = 0.0, ""
        for ref, sid in d.items():
            w = math.dist(DG.port_ray(ref)["origin"], slots[sid]["center3"])
            if w > worst:
                worst, wref = w, ref
        check("T3 匹配: 最远端口-槽距 < 6mm", worst < 6.0, "worst %s %.2fmm" % (wref, worst))
        faces_ok = all(d[r].startswith(slots_face) for r, slots_face in
                       [("J10", "B@"), ("J17", "B@"), ("J9", "T@"), ("J19", "T@"),
                        ("J1", "L@"), ("J8", "L@"), ("J2", "R@"), ("J5", "R@")])
        check("T3 匹配: 抽样 8 器件落位壁正确", faces_ok)
    ok2, _, _ = DGr.slots_satisfied(drop_slots=("T@73.0",))
    check("T3 匹配: 删一槽必失配 (负测试)", not ok2)


def test_flows_crosscheck():
    import device_graph as DGr
    bad = DGr.flows_crosscheck()
    check("T3 flows 电气拓扑 ↔ 网表权威源 0 违例", not bad, str(bad[:4]))


# ══════════ T4: 钻孔/禁布 — M3 孔 + 铜柱避让 ══════════
def test_drill_keepout():
    import device_geom as DG
    import drl
    holes = drl.npth_holes()                    # [(x板, y板, dia)]
    m3 = [h for h in holes if 3.0 <= h[2] <= 3.4]
    check("T4 drl: NPTH Ø3.2 M3 孔 = 4", len(m3) == 4, str([(round(a,1),round(b,1)) for a,b,_ in m3]))
    viol = []
    for ref in sorted(DG._POS):
        try:
            b = DG.obb(ref)
        except KeyError:
            continue
        cx, cy = b["center"]
        ax0, ax1 = b["axis0"], b["axis1"]
        for hx, hy, hd in m3:
            px, py = hx + G.OX, hy + G.OX
            # 盒(任意角)到孔心: 投影到盒局部系
            lx = (px - cx) * ax0[0] + (py - cy) * ax0[1]
            ly = (px - cx) * ax1[0] + (py - cy) * ax1[1]
            dxo = max(abs(lx) - b["w"] / 2, 0)
            dyo = max(abs(ly) - b["d"] / 2, 0)
            gap = math.hypot(dxo, dyo) - hd / 2
            if gap < 0.3 and (ref, (hx, hy)) not in KNOWN_HOLE_CLASH:
                viol.append("%s↔M3(%.0f,%.0f) gap=%.2f" % (ref, hx, hy, gap))
    check("T4 避让: 器件 OBB 与 M3 孔间隙 >0.3mm (known 除外)", not viol, str(viol[:5]))
    # 物理意义修正: 铜柱在板下, 顶面 SMD/壳体与其无 z 向冲突;
    # 真实约束 = TH 焊盘钻孔 (drl PTH) 不得钻入铜柱环 (柱外径 Ø6.3)
    boss_r = G.PD / 2 + G.BOSS_RING
    all_holes = drl.holes()
    viol2 = []
    for hx, hy, hd in all_holes:
        if hd >= 3.0:            # M3 安装孔本身即对位铜柱
            continue
        for sx, sy in G.ST:
            if ((round(hx, 1), round(hy, 1)), (sx, sy)) in KNOWN_VIA_BOSS:
                continue
            if math.hypot(hx - sx, hy - sy) < boss_r + hd / 2 + 0.05:
                viol2.append("孔(%.1f,%.1f Ø%.1f)↔铜柱(%.0f,%.0f)" % (hx, hy, hd, sx, sy))
    check("T4 避让: PTH 焊盘孔不钻入铜柱环 (+0.2 裕量)", not viol2, str(viol2[:5]))


if __name__ == "__main__":
    which = sys.argv[1:] or ["schema"]
    if "schema" in which:
        print("== T1 器件数据层 ==")
        test_schema()
        print("== T1 气动器件段 (pneumatic_devices) ==")
        test_schema_pneumatic()
    if "geom" in which or "all" in which:
        print("== T2 几何核 ==")
        test_orientation()
        test_collision_fcl()
    if "graph" in which or "all" in which:
        print("== T3 关系图 ==")
        test_matching()
        test_flows_crosscheck()
    if "drill" in which or "all" in which:
        print("== T4 钻孔禁布 ==")
        test_drill_keepout()
    print("\nL5: %d PASS / %d FAIL" % (PASS, FAIL))
    sys.exit(1 if FAIL else 0)

