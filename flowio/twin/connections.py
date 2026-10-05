# -*- coding: utf-8 -*-
"""flowio.twin.connections — D2 连接图谱机器校验器 (spec 2026-10-05 §3/§4, plan D2)。

连接 = 三类边图谱 (pneumatic/electrical/mechanical), 端点语法 "<位号>.<接口面>" /
"<模块>.<face>": 器件接口面单源 = devices.json pneumatic_devices.*.geom3d (D1 落地),
模块对外/对内接口面 = connections.json modules 块 (spec §4 两模块三面接口表的机器化)。

四条校验 (spec §3, 全部落地):
  R1 端点存在  — 每边 from/to 解析到器件 geom3d 接口面或模块 face, 且边类=端点类
                (气动边插电气面=FAIL); 附轻量 schema (自环/管边须 tube/线缆须 len);
  R2 口径匹配  — 管边 tube.id (及异径段 id_to) ≤ 端点嘴径 (引用 geom3d 的 dia;
                tube.id > 嘴径 = FAIL); 承插边 socket_dia ≥ 器件嘴径 (插入配合);
                fit_pending 边 (registry §6 到货试装条款) 倒挂降级 WARN;
  R3 六动作语义路通 — 充/吸/排/测 按场景阀态 (flowio.twin.scenarios SCENARIOS 同源:
                充=VS+Vi / 吸=VV+Vi / 排=VF+Vi / 测=Vi) 在气动图上 BFS 可达, 8 通道逐一;
                保 = 阀关断割集: 全部 NC 阀关断后, 通道口与 大气/泵双口/传感 隔离;
                (搬气=S+V 同开+泵内换向, 泵内气路不建边, 不在判据 —— spec §3 括号
                同只列五类);
  R4 悬空端点  — 器件气动口 + {2P 白壳, 电机焊片} 端子 + 全部模块面 必须有边连接
                或显式 reserved 标注 (预留语义; COIL_* 引线端子被 CONN_2P 视觉桩
                组件包含, SOIC8 板载脚归网表域 —— 见 _meta conventions.elec_scope)。

WARN 清单 (不 FAIL, 机器可读): 端点/边引用 inferred 接口面 (D1 占位: VV.N2 /
VV.mount_hole, BRINGUP 实测校正); fit_pending 口径倒挂 (泵 ⌀4.2 嘴 × ID5 管)。

纯 stdlib (json + 集合 BFS, 零新依赖); tube 只记 len_mm/bend 数 (D2-A 裁定:
逐点坐标属 D4 渲染层)。CLI: python -m flowio connections --check
(rc 0=绿 / 1=数据违例 / 2=文件缺失或坏 JSON, 对齐 cli rc 约定)。
"""
import json
import os
from collections import deque

from flowio.twin.devices3d import DEVICES_JSON            # 纯 stdlib 面常量单源

CONNECTIONS_JSON = os.path.join(os.path.dirname(DEVICES_JSON), "connections.json")

# NC 电磁阀组 = 可关断器件 (保压割集判据; devices.json 两阀组全系 NC, diagram §4 "全 NC 阀")
_NC_GROUPS = ("valves", "valve_vacuum_master")
# R4 电气端子管辖范围: 器件级线束可拔插端 (板载 SOIC8 归网表域 device_graph, COIL_* 归桩)
_ELEC_UNIVERSE_KINDS = ("visual_shell_2p", "solder_pin")
# 气动边 kind 白名单: tube=软管段 / socket=承插直连 / ambient=大气开放 (无管)
_PNEU_KINDS = ("tube", "socket", "ambient")
# 电气边 kind 白名单: cable_2p=2 芯电缆 / lead_2p=阀引线+2P 壳桩 / wire=器件引线
_ELEC_KINDS = ("cable_2p", "lead_2p", "wire")
# R3 保压判据的压力边界节点 (通道口关断后不得可达)
_HOLD_BOUNDARY = ("ATM.open", "P1.CHG", "P1.SUCK", "S1.P1")

_INTERFACE_SECTIONS = (("pneumatic_ports", "pneumatic"),
                       ("electrical_terminals", "electrical"),
                       ("mech_mounts", "mechanical"))


# ---- 加载 --------------------------------------------------------------------
def load_connections(path=None):
    """connections.json → dict (坏 JSON 抛 ValueError 带路径, 缺文件 OSError 上抛)。"""
    p = path or CONNECTIONS_JSON
    with open(p, encoding="utf-8") as f:
        try:
            return json.load(f)
        except ValueError as e:
            raise ValueError("connections 非法 JSON: %s (%s)" % (p, e))


def load_pneumatic_devices(path=None):
    """devices.json → pneumatic_devices 原始块 (组结构保留, 供 NC 组判定)。"""
    p = path or DEVICES_JSON
    with open(p, encoding="utf-8") as f:
        return json.load(f)["pneumatic_devices"]


def load_devices(path=None):
    """pneumatic_devices → {位号: 条目} (组内 refs 展开; 重复位号=真值错误即红)。"""
    pn = load_pneumatic_devices(path)
    out = {}
    for g, ents in pn.items():
        if g.startswith("_"):
            continue
        for e in ents:
            for r in e.get("refs") or []:
                if r in out:
                    raise ValueError("devices.json 位号重复: %s" % r)
                out[r] = e
    return out


def nc_valve_refs(pn):
    """NC 阀位号集 (组驱动, 非硬编码): valves + valve_vacuum_master 全部 refs。"""
    return {r for g in _NC_GROUPS for e in pn.get(g, []) for r in e.get("refs") or []}


# ---- 端点解析 (R1 核心) --------------------------------------------------------
def resolve_endpoint(ep, devices, modules):
    """'A.B[#n]' → {kind, dia, inferred, reserved, where}; 解析失败抛 KeyError/ValueError。

    器件侧: B 依次匹配 pneumatic_ports.name / electrical_terminals.name /
    mech_mounts.kind (D1 数据 mounts 无 name, 以 kind 为名); 同名多个须 #序号消歧。
    模块侧: B 匹配 modules[A].faces[].name。
    """
    mod, sep, rest = ep.partition(".")
    if not mod or not sep or not rest:
        raise ValueError("端点语法非法: %r (须 <位号>.<接口面> 或 <模块>.<face>)" % ep)
    name, hsep, idx_s = rest.partition("#")
    idx = int(idx_s) if hsep else None
    if mod in devices:
        entry = devices[mod]
        geom = entry.get("geom3d") or entry       # D1 起接口面在 geom3d 块内
        for section, kind in _INTERFACE_SECTIONS:
            hits = [f for f in geom.get(section) or []
                    if (f.get("name") or f.get("kind")) == name]
            if not hits:
                continue
            if idx is not None:
                if idx >= len(hits):
                    raise KeyError("端点 %r: #序号 %d 越界 (%d 个同名)"
                                   % (ep, idx, len(hits)))
                f = hits[idx]
            elif len(hits) > 1:
                raise KeyError("端点 %r: %d 个同名接口面, 须 #序号消歧" % (ep, len(hits)))
            else:
                f = hits[0]
            return {"kind": kind, "dia": f.get("dia"),
                    "inferred": bool(f.get("inferred")), "reserved": f.get("reserved"),
                    "where": "device %s.%s" % (mod, section)}
        raise KeyError("器件 %s 无接口面 %r (geom3d 三面查无)" % (mod, name))
    if mod in modules:
        hits = [f for f in modules[mod].get("faces") or [] if f.get("name") == name]
        if not hits:
            raise KeyError("模块 %s 无 face %r" % (mod, name))
        if len(hits) > 1:
            raise KeyError("模块 %s face %r 重复定义" % (mod, name))
        f = hits[0]
        return {"kind": f.get("kind"), "dia": f.get("dia"),
                "inferred": bool(f.get("inferred")), "reserved": f.get("reserved"),
                "where": "module %s" % mod}
    raise KeyError("端点 %r 前缀 %r 既非器件位号亦非模块名" % (ep, mod))


# ---- R3 气动图 (BFS) -----------------------------------------------------------
def _node(ep, nc):
    """BFS 节点归并: NC 阀的双端口并入一个可关断节点 'V:<位号>'
    (阀=串在气路中的开关); 其余端点自为节点 —— 传感双口 (S1.P1/P2) 与泵双口
    (P1.CHG/SUCK) 不归并 (传感器双腔独立/泵为源汇非导体)。"""
    ref = ep.split(".", 1)[0]
    return "V:%s" % ref if ref in nc else ep


def build_pneu_adj(edges, nc):
    """气动边 → 邻接表 (无向: 开阀与管段双向导通)。"""
    adj = {}
    for e in edges:
        a, b = _node(e["from"], nc), _node(e["to"], nc)
        adj.setdefault(a, set()).add(b)
        adj.setdefault(b, set()).add(a)
    return adj


def reach(adj, start, blocked=frozenset()):
    """BFS 可达集 (blocked 节点不可落脚 —— 关断阀即气路阻断)。"""
    seen = {start}
    dq = deque([start])
    while dq:
        n = dq.popleft()
        for m in adj.get(n, ()):
            if m not in seen and m not in blocked:
                seen.add(m)
                dq.append(m)
    return seen


def check_actions(edges, nc):
    """六动作语义路通 (R3): 阀态与 flowio.twin.scenarios SCENARIOS 同源。

    充 single_inflate: VS+Vi 开, P1.CHG → Main.CH{i};
    吸 single_vacuum: VV+Vi 开, Main.CH{i} → P1.SUCK;
    排 single_release: VF+Vi 开, Main.CH{i} → ATM.open;
    测 (3=1× 分时): Vi 开, Main.CH{i} → S1.P1;
    保 single_hold: 全 NC 阀关断 (割集), Main.CH{i} 与大气/泵/传感 隔离。
    """
    adj = build_pneu_adj(edges, nc)
    valve_nodes = {"V:%s" % r for r in nc}
    channels = ["Main.CH%d" % i for i in range(1, 9)]
    rep = {}

    def path_ok(start, goal, openset):
        return goal in reach(adj, start, valve_nodes - set(openset))

    ch_res = {}
    for i, ch in enumerate(channels, 1):
        vi = "V:V%d" % i
        ch_res[i] = {
            "inflate": path_ok("P1.CHG", ch, ("V:VS", vi)),
            "vacuum": path_ok(ch, "P1.SUCK", ("V:VV", vi)),
            "release": path_ok(ch, "ATM.open", ("V:VF", vi)),
            "measure": path_ok(ch, "S1.P1", (vi,)),
        }
    for act in ("inflate", "vacuum", "release", "measure"):
        rep[act] = {"ok": all(ch_res[i][act] for i in ch_res),
                    "desc": _ACT_DESC[act], "ch": {i: ch_res[i][act] for i in ch_res}}

    # 保 = 割集判据: 全阀关断后通道口不得触及压力边界 (大气/泵双口/传感)
    blocked = valve_nodes
    ch_hold = {}
    for ch in channels:
        seen = reach(adj, ch, blocked)
        ch_hold[ch] = not (seen & set(_HOLD_BOUNDARY))
    rep["hold"] = {"ok": all(ch_hold.values()), "desc": _ACT_DESC["hold"],
                   "ch": {i: ch_hold["Main.CH%d" % i] for i in ch_res}}
    return rep


_ACT_DESC = {
    "inflate": "充: 泵→S→M→Vi→通道 (阀态 VS+Vi; scenarios single_inflate 同源)",
    "vacuum": "吸: 通道→Vi→M→VV→泵吸口 (阀态 VV+Vi; single_vacuum 同源)",
    "release": "排: 通道→Vi→M→VF→大气 (阀态 VF+Vi; single_release 同源)",
    "measure": "测: 通道→Vi→M→测压支路→S1.P1 (分时 Vi; 决策 3=1×)",
    "hold": "保: 全 NC 阀关断割集 —— 通道口与 大气/泵/传感 隔离 (single_hold 同源)",
}


# ---- 主校验 --------------------------------------------------------------------
def validate(conn=None, conn_path=None, devices_path=None):
    """四条校验 → {"ok", "fail", "warn", "stats", "actions"} (fail/warn 均机器可读串)。"""
    conn = conn if conn is not None else load_connections(conn_path)
    devices = load_devices(devices_path)
    pn = load_pneumatic_devices(devices_path)
    nc = nc_valve_refs(pn)
    modules = conn.get("modules") or {}
    fail, warn = [], []
    resolved = {}

    def res(ep):
        if ep not in resolved:
            resolved[ep] = resolve_endpoint(ep, devices, modules)
        return resolved[ep]

    edge_lists = [(cls, conn.get(cls + "_edges") or [])
                  for cls in ("pneumatic", "electrical", "mechanical")]
    counts = {}
    for cls, edges in edge_lists:
        counts[cls + "_edges"] = len(edges)

    # ---- R1 端点存在 + 轻量 schema ----
    clean = {}                                    # 类 → 端点解析成功的边 (R2/R3 用)
    for cls, edges in edge_lists:
        base = cls                              # pneumatic/electrical/mechanical
        ok_edges = []
        for i, e in enumerate(edges):
            tag = "%s[%d] %s→%s" % (cls + "_edges", i, e.get("from"), e.get("to"))
            if not isinstance(e.get("from"), str) or not isinstance(e.get("to"), str):
                fail.append("R1端点 %s: from/to 缺失或非字符串" % tag)
                continue
            if e["from"] == e["to"]:
                fail.append("R1自环 %s" % tag)
                continue
            if not isinstance(e.get("kind"), str) or not e["kind"]:
                fail.append("R1schema %s: 缺 kind" % tag)
            infos = []
            for ep in (e["from"], e["to"]):
                try:
                    info = res(ep)
                except (KeyError, ValueError) as exc:
                    fail.append("R1端点 %s: %s" % (tag, exc))
                    info = None
                infos.append(info)
                if info and info["kind"] != base:
                    fail.append("R1类别 %s: 端点 %s 类别 %s ≠ 边类 %s"
                                % (tag, ep, info["kind"], base))
                if info and info.get("inferred"):
                    warn.append("WARN[inferred] 端点 %s (%s, %s) — 边 %s→%s; D1 占位, "
                                "BRINGUP 实测校正" % (ep, info["where"], ep, e["from"], e["to"]))
            if e.get("inferred"):
                warn.append("WARN[inferred] 边 %s→%s 整边标注 inferred" % (e["from"], e["to"]))
            if all(infos):
                if base == "pneumatic":
                    kind = e.get("kind")
                    if kind not in _PNEU_KINDS:
                        fail.append("R1schema %s: 气动 kind %r 不在 %s"
                                    % (tag, kind, _PNEU_KINDS))
                    if e.get("tube") is None and kind not in ("socket", "ambient"):
                        fail.append("R1schema %s: 管边须带 tube (socket/ambient 除外)" % tag)
                    if e.get("tube") is not None \
                            and not isinstance(e["tube"].get("id"), (int, float)):
                        fail.append("R1schema %s: tube.id 缺失或非数值" % tag)
                elif base == "electrical":
                    if e["kind"] not in _ELEC_KINDS:
                        fail.append("R1schema %s: 电气 kind %r 不在 %s"
                                    % (tag, e["kind"], _ELEC_KINDS))
                    if e["kind"] in ("cable_2p", "lead_2p") \
                            and not isinstance(e.get("len_mm"), (int, float)):
                        fail.append("R1schema %s: %s 须带数值 len_mm (wire 可 null)"
                                    % (tag, e["kind"]))
                ok_edges.append(e)
        clean[base] = ok_edges

    # ---- R2 口径匹配 (嘴径 ≥ 管 id; 承插孔 ≥ 嘴径; fit_pending 降级 WARN) ----
    for e in clean["pneumatic"]:
        tag = "气边 %s→%s" % (e["from"], e["to"])
        tube = e.get("tube")
        if tube is not None:
            for ep, bore in ((e["from"], tube["id"]),
                             (e["to"], tube.get("id_to", tube["id"]))):
                dia = res(ep).get("dia")
                if dia is None:
                    continue
                if bore > dia:
                    if e.get("fit_pending"):
                        warn.append("WARN[fit_pending] %s: tube.id %g > 端点 %s 嘴径 %g "
                                    "(%s) — registry §6 到货试装定档"
                                    % (tag, bore, ep, dia, e["fit_pending"]))
                    else:
                        fail.append("R2口径 %s: tube.id %g > 端点 %s 嘴径 %g "
                                    "(引用 geom3d dia)" % (tag, bore, ep, dia))
        elif e.get("socket_dia") is not None:
            for ep in (e["from"], e["to"]):
                info = res(ep)
                dia = info.get("dia")
                # 承插=器件嘴插入孔 (模块腔面非插入端, 不判)
                if info["where"].startswith("device") and dia is not None \
                        and dia > e["socket_dia"]:
                    fail.append("R2承插 %s: 端点 %s 嘴径 %g > 承口 ⌀%g"
                                % (tag, ep, dia, e["socket_dia"]))

    # ---- R3 六动作语义路通 (仅用端点解析成功的气动边) ----
    actions = check_actions(clean["pneumatic"], nc)
    for act, a in actions.items():
        if not a["ok"]:
            bad = sorted(i for i, ok in a["ch"].items() if not ok)
            fail.append("R3%s: %s (失败通道: %s)" % (act, a["desc"], bad or "-"))

    # ---- R4 悬空端点 ----
    universe = set()
    for ref, entry in devices.items():
        geom = entry.get("geom3d") or entry       # 接口面单源: geom3d 块 (D1)
        for f in geom.get("pneumatic_ports") or []:
            universe.add("%s.%s" % (ref, f.get("name")))
        for f in geom.get("electrical_terminals") or []:
            if f.get("kind") in _ELEC_UNIVERSE_KINDS:
                universe.add("%s.%s" % (ref, f.get("name")))
    for mname, m in modules.items():
        for f in m.get("faces") or []:
            universe.add("%s.%s" % (mname, f.get("name")))
    connected = set(resolved)                 # 任一类边成功引用的端点
    reserved = set()
    for mname, m in modules.items():
        for f in m.get("faces") or []:
            if f.get("reserved"):
                reserved.add("%s.%s" % (mname, f.get("name")))
    for r in conn.get("reserved") or []:
        reserved.add(r if isinstance(r, str) else r.get("endpoint"))
    for ep in sorted(universe - connected - reserved):
        fail.append("R4悬空 %s: 接口面无任何边连接且无 reserved 标注" % ep)

    stats = dict(counts)
    stats["endpoints_resolved"] = len(resolved)
    stats["modules"] = len(modules)
    return {"ok": not fail, "fail": fail, "warn": warn,
            "stats": stats, "actions": actions}
