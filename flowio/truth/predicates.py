# -*- coding: utf-8 -*-
"""flowio.truth.predicates — devices.json schema 谓词 (纯函数, 零 IO)。

来源 (M0 收拢, spec v2.1 §2 truth 层 "pneumatic 谓词(T1 断言迁入)"):
hardware/flowio-p1/enclosure/test_device_geom.py T1 十五断言的谓词部分迁此为
可复用函数 —— 断言测试仍留原地 (check 计数不变), 经本模块调用;
TruthSource._validate 亦复用 document_problems 聚合入口 —— 单一校验逻辑,
禁第二份手抄。

语义冻结: 谓词体自 test_device_geom.py 逐字迁移 (去下划线改名), 行为锚点 =
2026-10-05 基线 T1 15 PASS / 0 FAIL @7885c62; 仅取值方式防御化 (缺键=违例,
不抛 KeyError —— 让坏文档稳定产出问题清单供 TruthError 报告)。
"""
import math

# ══════════ devices 段 (PCB 贴装) ══════════
DEVICE_REQUIRED_FIELDS = ("lcsc", "name", "refs", "pkg_keywords",
                          "dims", "placement", "datasheet")
PLACEMENT_LEGAL = frozenset({"EDGE_OUT", "SURFACE", "INTERNAL"})


def missing_bom_refs(entries, bom_refs):
    """BOM 位号是否被 entries 的 refs 全覆盖 → 未覆盖位号排序列表。"""
    covered = set()
    for e in entries:
        covered |= set(e.get("refs") or [])
    return sorted(set(bom_refs) - covered)


def incomplete_entries(entries):
    """缺 7 必需字段 (lcsc/name/refs/pkg_keywords/dims/placement/datasheet) 的条目。"""
    need = set(DEVICE_REQUIRED_FIELDS)
    return [e.get("lcsc", "?") for e in entries if not need <= set(e)]


def bad_dims_entries(entries):
    """dims 三元组出域 (w/d ∈ [0.2,40], h ∈ [0.2,20] mm) 的条目。"""
    bad = []
    for e in entries:
        dm = e.get("dims") or {}
        try:
            ok = (0.2 <= dm["w"] <= 40 and 0.2 <= dm["d"] <= 40
                  and 0.2 <= dm["h"] <= 20)
        except (KeyError, TypeError):
            ok = False
        if not ok:
            bad.append(e.get("lcsc", "?"))
    return bad


def connectors_missing_port(entries, conn_refs):
    """连接器条目缺 port (dir_local/exit_z) 或 dir_local 非单位向量的违例标签。"""
    conn = set(conn_refs)
    bad = []
    for e in entries:
        if not conn & set(e.get("refs") or []):
            continue
        lcsc = e.get("lcsc", "?")
        p = e.get("port")
        if not p or "dir_local" not in p or "exit_z" not in p:
            bad.append(lcsc)
            continue
        try:
            dx, dy = p["dir_local"][:2]
            unit = abs(math.hypot(dx, dy) - 1.0) <= 1e-6
        except (TypeError, ValueError):
            unit = False
        if not unit:
            bad.append(lcsc + "(非单位向量)")
    return bad


def bad_placement_entries(entries):
    """placement 不在合法枚举 (EDGE_OUT/SURFACE/INTERNAL) 的条目。"""
    return [e.get("lcsc", "?") for e in entries
            if e.get("placement") not in PLACEMENT_LEGAL]


# ══════════ pneumatic_devices 段 ══════════
PNEU_GROUPS = ("valves", "valve_vacuum_master", "pump", "sensor")
PNEU_ACTUATORS = ("valves", "valve_vacuum_master", "pump")   # DC4.5V 执行器; sensor 为 5V 轨直供 I2C 件
PNEU_RATED_V = 4.5                                            # P1.1 定案: 全系 DC4.5V 变体
PNEU_RAIL_V = 5.0                                             # _meta.drive_policy.rail_v


def pneu_tag(g, e):
    """违例标签: "组:ref/ref"。"""
    return "%s:%s" % (g, "/".join(e.get("refs") or ["?"]))


def pneu_entries(pn):
    """展平 (group, entry) 对; 组缺失按空处理。"""
    out = []
    for g in PNEU_GROUPS:
        for e in (pn.get(g) or []):
            out.append((g, e))
    return out


def pneu_groups_empty(pn):
    """4 列表组中缺失/空的组名列表 (段完整性)。"""
    return [g for g in PNEU_GROUPS if not (isinstance((pn or {}).get(g), list) and pn[g])]


def pneu_completeness_bad(pn):
    """每条气动 entry 必需字段: refs/model/manufacturer/datasheet/electrical/dims
    + 阀/传感器单口 port + 泵双口 ports。"""
    bad = []
    for g, e in pneu_entries(pn):
        tag = pneu_tag(g, e)
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


def pneu_domain_ok(pn):
    """spec 1f-β 负压专用阀域: pressure_kpa 上限<=0 的阀 (F0520B) 只允许出现在
    valve_vacuum_master 组; valves 组 (V1-V8/VS/VF 正压通用阀位) 不允许混入;
    反向: valve_vacuum_master 组内必须全为负压域条目。"""
    for e in (pn.get("valves") or []):
        pk = e.get("pressure_kpa")
        if not pk or pk[1] <= 0:
            return False
    for e in (pn.get("valve_vacuum_master") or []):
        pk = e.get("pressure_kpa")
        if not pk or pk[1] > 0:
            return False
    return True


def pneu_voltage_bad(pn):
    """电压档一致性 (P1.1 定案全系 DC4.5V): 执行器 (阀/泵) electrical.rated_v 必须为 4.5;
    无 rated_v 的直供件 (sensor) 其 v_range 必须覆盖 5V 轨。"""
    rail = ((pn.get("_meta") or {}).get("drive_policy") or {}).get("rail_v")
    bad = []
    for g, e in pneu_entries(pn):
        el = e.get("electrical") or {}
        tag = pneu_tag(g, e)
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


def pneu_rail_variant_ok(pn):
    """drive_policy.rail_v=5.0 且 voltage_variant 含 DC4.5V (5V 轨 + PWM 调制前提)。"""
    meta = pn.get("_meta") or {}
    rail = (meta.get("drive_policy") or {}).get("rail_v")
    variant = meta.get("voltage_variant") or ""
    return rail == PNEU_RAIL_V and "DC4.5V" in variant


def pneu_refs_dup(pn, pcb_refs):
    """四组合计 refs 不得重复, 且不得与 devices 段 (PCB 贴装) refs 冲突。"""
    seen, dups = set(), set()
    for g, e in pneu_entries(pn):
        for r in (e.get("refs") or []):
            if r in seen or r in pcb_refs:
                dups.add(r)
            seen.add(r)
    return sorted(dups)


def pneu_envelope_bad(pn):
    """泵压力窗必须严格包络两类阀压力窗 (valve ⊂ pump, 余量>0)。
    返回 (违例列表, 全局最小余量 kPa; 无有效阀-泵对时为 None)。"""
    pumps = [e for e in (pn.get("pump") or []) if e.get("pressure_kpa")]
    bad, margins = [], []
    for g in ("valves", "valve_vacuum_master"):
        for e in (pn.get(g) or []):
            pk = e.get("pressure_kpa")
            if not pk:
                bad.append(pneu_tag(g, e) + "(缺pressure_kpa)")
                continue
            m = [min(pk[0] - p["pressure_kpa"][0], p["pressure_kpa"][1] - pk[1])
                 for p in pumps]
            margins += m
            if not m or max(m) <= 0:
                bad.append("%s %s" % (pneu_tag(g, e), pk))
    return bad, (min(margins) if margins else None)


# ══════════ 聚合: 全文档结构校验 (TruthSource._validate 消费) ══════════
def document_problems(doc):
    """devices + pneumatic_devices 两段结构校验 → 问题清单 (空 = 通过)。

    覆盖 T1 十五断言中纯文档可判的谓词 (不含需外部文件的 BOM csv 覆盖与
    21 连接器位号清单 —— 那两项仍由 test_device_geom.py 持有清单侧调用)。
    """
    problems = []
    devices = doc.get("devices")
    if not (isinstance(devices, list) and devices):
        problems.append("devices 段缺失或为空")
        devices = []
    else:
        problems += ["devices 字段缺失: %s" % x for x in incomplete_entries(devices)]
        problems += ["devices dims 出域: %s" % x for x in bad_dims_entries(devices)]
        problems += ["devices placement 非法: %s" % x for x in bad_placement_entries(devices)]

    pn = doc.get("pneumatic_devices")
    if not isinstance(pn, dict):
        problems.append("pneumatic_devices 段缺失")
        return problems
    empty = pneu_groups_empty(pn)
    if empty:
        problems.append("pneumatic 组缺失/空: %s" % empty)
        return problems          # 段残缺早退 (与 T1 同策略: 空结构下后续谓词无意义)
    problems += ["pneumatic 字段缺失: %s" % x for x in pneu_completeness_bad(pn)]
    if not pneu_domain_ok(pn):
        problems.append("pneumatic 负压阀域违例 (上限≤0 仅 valve_vacuum_master)")
    problems += ["pneumatic 电压档违例: %s" % x for x in pneu_voltage_bad(pn)]
    if not pneu_rail_variant_ok(pn):
        problems.append("pneumatic rail_v/variant 违例 (期望 rail=5.0 + DC4.5V)")
    pcb_refs = set()
    for e in devices:
        pcb_refs |= set(e.get("refs") or [])
    dups = pneu_refs_dup(pn, pcb_refs)
    if dups:
        problems.append("pneumatic refs 重复/冲突: %s" % dups)
    ebad, _margin = pneu_envelope_bad(pn)
    problems += ["pneumatic 压力包络违例: %s" % x for x in ebad]
    return problems
