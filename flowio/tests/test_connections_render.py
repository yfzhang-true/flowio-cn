# -*- coding: utf-8 -*-
"""test_connections_render — D4 渲染 payload 几何层 TDD (质量审缺口 2, plan D4 审修)。

红/绿纪律: 本文件先行 (红 = payload 路径/锚定/副本同步任一判据破), 实现后全绿;
对 _tube_path 肘点错位类变异必翻红 (自变异证据见提交信息)。
运行: python flowio/tests/test_connections_render.py   (任意 cwd, stdlib-only)

覆盖 (质量审合并修复清单 A/B, 每条判据均可独立翻红):
  P1 首末点=锚 — 每条管/线边渲染 path 首末点 == 对应 anchor 端点 (引线桩 from 侧按
                CONN_2P↔ESCAPE 别名), 另抽 V5.N2 / Main.CH5 两锚自 devices.json
                geom3d + case_geom 常量独立重算 (不经 CR 辅助函数, 防同错互证);
  P2 可行性   — 每条管边折线段长和 ≤ 下料长 tube.len_mm (超长不可布管 = 红);
  P3 锚定部件 — payload 引用的全部 anchor 部件 id ∈ assembly.json parts (无幽灵部件);
  P4 双解析器 — payload 锚点全集 ↔ connections.resolve_endpoint 可解析集合 一致
                (render 层未复用 resolve 是职责分工, 端点全集漂移必红);
  P5 已知边钉扎 — V5.N2→Main.CH5 肘点数与关键坐标带钉死 (渲染层布局约定值, 非
                物理真值; 交织序横行 38mm 即变异 "肘点错位 38mm" 的靶点);
  S1 副本同步 — webapp/site 的 connections.json 与真值字节等同, connections_scene.json
                webapp↔site 等同且与 build_render_payload() 现值逐字节一致 (生成副本
                陈旧必红); 真值 _meta.copies 副本声明在场 (质量审缺口 1)。

WARN 豁免 (显式留证, 非漏洞): ATM.open = 大气非实体节点 (conventions.atm_node),
无几何无锚; Main.M_tap = payload 内部别名 (同点位 Main.M)。mech 边无几何, 不入 P1/P4。
"""
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

# ---- TDD 红: payload 管线或副本未落地时以下 import 与加载即败 -------------------
from flowio.geom import case_geom as G                                    # noqa: E402
from flowio.twin import connections as C                                  # noqa: E402
from flowio.twin import connections_render as CR                          # noqa: E402
from flowio.twin.devices3d import load_geom3d                             # noqa: E402

CONN = C.load_connections()          # 真值连接图谱 (缺文件/坏 JSON = 红)
PAYLOAD = CR.build_render_payload()  # 渲染 payload (D4)

WEBAPP = ROOT / "firmware" / "twin" / "webapp"
SITE = ROOT / "site"

# 真值边计数锚点 (对齐 test_connections 纪律): 58 边 = 16 管 + 14 线 + 28 无几何
# (11 承插 + 2 ambient + 15 mech; render 层 socket/ambient/mech 均无几何)
N_EDGES, N_TUBE, N_WIRE, N_NONE = 58, 16, 14, 28


# ---- 小工具 ------------------------------------------------------------------
def _tube_len_mm():
    """真值管边 (from,to) → len_mm (P2 判据的下游真值)。"""
    return {(e["from"], e["to"]): e["tube"]["len_mm"]
            for e in CONN["pneumatic_edges"] if e.get("tube")}


def _seg_len_sum(path):
    return sum(math.dist(path[i], path[i + 1]) for i in range(len(path) - 1))


def _anchor_index():
    """CR 锚点索引重建 (P1/P4 判据源; 与 build_render_payload 内部同参同源)。"""
    pos = CR.load_pos()
    return CR._anchor_index(CR.valve_places(), CR.pump_place(),
                            CR.sensor_place(pos), pos)


# ══════════ payload 形状 + 计数钉扎 ══════════
def test_payload_schema_and_counts_pinned():
    """payload 形状齐 + 边计数钉死 (静默丢边/丢几何必翻红)。"""
    assert set(PAYLOAD) >= {"meta", "devices", "edges", "counts"}, PAYLOAD.keys()
    for k in ("coord", "source", "generated_by"):
        assert PAYLOAD["meta"].get(k), "meta 缺 %s" % k
    edges = PAYLOAD["edges"]
    assert len(edges) == N_EDGES, len(edges)
    kinds = {"tube": N_TUBE, "wire": N_WIRE, "none": N_NONE}
    got = {k: sum(1 for e in edges if e["render"] == k) for k in kinds}
    assert got == kinds, "render 计数漂移: %r" % got
    for i, e in enumerate(edges):
        assert e["i"] == i, "边序号断裂 @%d" % i
        for k in ("cls", "kind", "from", "to", "render", "follow", "fit_pending", "desc"):
            assert k in e, "边 %d 缺 %s" % (i, k)
        if e["render"] != "none":
            assert e["path"] and e["anchors"] and len(e["path"]) == len(e["anchors"]), \
                "渲染边 %d path/anchors 缺失或不对齐" % i
    assert set(PAYLOAD["counts"]) == set(PAYLOAD["devices"]), "counts 与 devices 键漂移"


# ══════════ P1 首末点 = 锚端点 ══════════
def test_path_endpoints_match_anchors():
    """每条管/线边 path 首末点 == 对应 anchor 端点 (引线 from 侧 CONN_2P→ESCAPE 别名)。"""
    a = _anchor_index()
    n = 0
    for e in PAYLOAD["edges"]:
        if e["render"] == "none":
            continue
        fk = e["from"].replace(".CONN_2P", ".ESCAPE") \
            if e["kind"] == "lead_2p" else e["from"]
        assert e["path"][0] == a[fk][0], \
            "边 %s→%s 首点 ≠ from 锚: %r vs %r" % (e["from"], e["to"], e["path"][0], a[fk][0])
        assert e["path"][-1] == a[e["to"]][0], \
            "边 %s→%s 末点 ≠ to 锚" % (e["from"], e["to"])
        n += 1
    assert n == N_TUBE + N_WIRE, "受检渲染边数漂移: %d" % n


def test_two_anchors_independently_rederived():
    """锚独立重算 (不经 CR 辅助): V5.N2 嘴端 (geom3d pos/dir/len + case_geom 阀阵位)
    与 Main.CH5 壁孔 (case_geom 单源常量) —— 防 CR 内部与测试同错互证。"""
    a = _anchor_index()
    gm = load_geom3d()["valves"]
    q = next(p for p in gm["pneumatic_ports"] if p["name"] == "N2")
    oz = CR.VALVE_ORIGIN_Z_D                                     # D 阀 origin z (21.5)
    tip = [G.V_COLS[0], G.V_ROWS[0],                             # V5 = 后行第 1 列 (20, 45)
           oz + q["pos"][2] + q["dir"][2] * q["len"]]
    assert a["V5.N2"][0] == tip, "V5.N2 锚 ≠ geom3d 独立重算: %r vs %r" % (a["V5.N2"][0], tip)
    ch5 = [G.CH_PORT_X[4], G.OH, G.PORT_Z_CH]                    # B 壁 CH5 过孔 @x58
    assert a["Main.CH5"][0] == ch5, "Main.CH5 锚 ≠ case_geom 常量: %r" % (a["Main.CH5"][0],)


# ══════════ P2 管边折线可行性 ══════════
def test_tube_polyline_within_cut_length():
    """每条管边折线段长和 ≤ 下料长 len_mm (D4-A 可行性判据; 差值即布管余量)。"""
    lens = _tube_len_mm()
    n = 0
    for e in PAYLOAD["edges"]:
        if e["render"] != "tube":
            continue
        s = _seg_len_sum(e["path"])
        lm = lens[(e["from"], e["to"])]
        assert s <= lm, "管边 %s→%s 折线段长和 %.1f > 下料长 %d (不可布管)" \
            % (e["from"], e["to"], s, lm)
        n += 1
    assert n == N_TUBE, "受检管边数漂移: %d" % n


# ══════════ P3 锚定部件无幽灵 ══════════
def test_anchor_parts_in_assembly():
    """payload 引用的全部 anchor 部件 id ∈ assembly.json parts (scene offsetPts
    按 anchors[i] 查部件位移, 幽灵 id = 跟随静默失效)。"""
    asm = json.loads((ROOT / "firmware" / "twin" / "meshes" / "assembly.json")
                     .read_text(encoding="utf-8"))
    ids = {p["id"] for p in asm["parts"]}
    used = set()
    for e in PAYLOAD["edges"]:
        if e["anchors"]:
            used |= set(e["anchors"])
        if e["render"] != "none":                                # 渲染边 follow 亦为部件 id
            used |= set(e["follow"])
    ghosts = used - ids
    assert not ghosts, "幽灵部件 id (不在 assembly.json): %r" % ghosts


# ══════════ P4 双解析器一致性 ══════════
def test_endpoint_universe_parity():
    """payload 锚点全集 ↔ resolve_endpoint 可解析集合 一致 (双解析器钉扎):
    正向: 每条气动/电气真值边端点必可 resolve 且 base 形态在锚索引 (ATM.open 豁免:
    大气非实体节点 conventions.atm_node, 无几何无锚);
    反向: 锚索引每键 (M_tap 内部别名豁免, ESCAPE→CONN_2P 归一) 必可 resolve 且
    类别匹配 —— devices.json/modules 改名任一侧漂移必红。"""
    devs = C.load_devices()
    mods = CONN["modules"]
    a = _anchor_index()

    # 正向: 真值边端点全覆盖
    miss = []
    for cls in ("pneumatic_edges", "electrical_edges"):
        for e in CONN[cls]:
            for ep in (e["from"], e["to"]):
                base = ep.split("#")[0]
                if base == "ATM.open":
                    continue
                key = base.replace(".CONN_2P", ".ESCAPE") \
                    if base.endswith(".CONN_2P") else base
                if key not in a:
                    miss.append("%s: %s" % (cls, ep))
                C.resolve_endpoint(ep, devs, mods)               # 解析失败即抛 (R1 同源)
    assert not miss, "真值端点无锚 (渲染层漏解析): %r" % miss

    # 反向: 锚键无幽灵, 类别一致
    for key in a:
        if key == "Main.M_tap":                                  # payload 内部别名 (同 M)
            continue
        truth_key = key.replace(".ESCAPE", ".CONN_2P") \
            if key.endswith(".ESCAPE") else key
        info = C.resolve_endpoint(truth_key, devs, mods)
        assert info["kind"] in ("pneumatic", "electrical"), \
            "锚键 %s 解析为 %s (render 域外, 幽灵锚)" % (key, info["kind"])


# ══════════ P5 已知边肘点钉扎 ══════════
def test_known_edge_v5_ch5_elbow_pinned():
    """V5.N2→Main.CH5 折线钉扎 (渲染层布局约定值, D4 现值; 非物理真值):
    4 点 = 嘴端 + 竖落肘 + 横行肘 + 壁孔; 横行段沿后行阀列 y=45 自 x20 横跨 38mm 至
    CH5 孔 x58 (交织序, README "已知视觉限制"§4 核闭段即此边) —— 肘点错位变异必红。"""
    e = next(e for e in PAYLOAD["edges"]
             if (e["from"], e["to"]) == ("V5.N2", "Main.CH5"))
    assert e["render"] == "tube" and e["radius"] == 7.0 / 2.0, (e["render"], e["radius"])
    pth = e["path"]
    assert len(pth) == 4, "肘点数漂移 (期望嘴端+2 肘+壁孔 4 点): %d" % len(pth)
    eps = 1e-6

    def near(p, q, tag):
        assert all(abs(p[i] - q[i]) < eps for i in range(3)), \
            "%s 漂移: %r vs 钉扎值 %r" % (tag, p, q)

    near(pth[0], [20.0, 45.0, 18.5], "首点 V5.N2 嘴端 (阀列 x20/后行 y45)")     # P1 锚同验
    near(pth[1], [20.0, 45.0, 17.25], "竖落肘 z=过孔带 PORT_Z_CH")
    near(pth[2], [58.0, 45.0, 17.25], "横行肘 (x20→58 交织横行 38mm, y=阀行)")
    near(pth[3], [58.0, 85.8, 17.25], "末点 B 壁 CH5 孔 (x=CH_PORT_X[4], y=OH)")
    assert e["anchors"] == ["valves", "valves", "case_bottom", "case_bottom"], \
        "逐点锚归属漂移: %r" % e["anchors"]


# ══════════ S1 生成副本同步守卫 (质量审缺口 1) ══════════
def test_webapp_site_copies_sync():
    """字节等同守卫: webapp/site 的 connections.json 与真值逐字节一致 (make_meshes
    D4 段拷贝 + build_site.py 拷贝), connections_scene.json webapp↔site 等同且与
    build_render_payload() 现值一致 (改渲染代码不重生成必红); 真值 _meta.copies
    副本声明在场。手改副本 = 违反单一真相, 直接翻红。"""
    truth = (ROOT / "hardware" / "flowio-p1" / "enclosure" / "connections.json").read_bytes()
    assert (WEBAPP / "connections.json").read_bytes() == truth, \
        "webapp/connections.json 与真值漂移 (须由 make_meshes 拷贝, 禁手改)"
    assert (SITE / "connections.json").read_bytes() == truth, \
        "site/connections.json 与真值漂移 (须由 build_site.py 同步)"
    scene = (WEBAPP / "connections_scene.json").read_bytes()
    assert (SITE / "connections_scene.json").read_bytes() == scene, \
        "site/connections_scene.json 与 webapp 产物漂移"
    fresh = json.dumps(CR.build_render_payload(),
                       ensure_ascii=False, indent=1).encode("utf-8")   # make_meshes 同式
    assert scene == fresh, \
        "webapp/connections_scene.json 陈旧 (与 build_render_payload 现值不一致) —— " \
        "重跑 make_meshes D4 段或按同式重生成"
    meta = json.loads(truth.decode("utf-8"))["_meta"]
    assert "copies" in meta and "真值以 hardware/flowio-p1/enclosure" in meta["copies"], \
        "真值 _meta.copies 副本声明缺失 (webapp/site 副本文件头注记随之缺失)"


# ══════════ 摘要: python flowio/twin/connections_render.py 可跑 ══════════
def test_render_module_summary_runs():
    """__main__ 摘要模式可执行 (子进程直跑, 对齐 test_connections CLI 冒烟惯例)。"""
    import subprocess
    r = subprocess.run([sys.executable, str(ROOT / "flowio" / "twin" / "connections_render.py")],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       cwd=str(ROOT))
    assert r.returncode == 0, r.stderr[:300]
    assert "[connections_render]" in r.stdout and "rendered=30" in r.stdout, r.stdout[:200]


if __name__ == "__main__":
    test_payload_schema_and_counts_pinned()
    test_path_endpoints_match_anchors()
    test_two_anchors_independently_rederived()
    test_tube_polyline_within_cut_length()
    test_anchor_parts_in_assembly()
    test_endpoint_universe_parity()
    test_known_edge_v5_ch5_elbow_pinned()
    test_webapp_site_copies_sync()
    test_render_module_summary_runs()
    print("flowio.twin.connections_render tests OK (9 testfns: 形状计数×1 + P1 首末锚×2 "
          "+ P2 可行性×1 + P3 幽灵部件×1 + P4 双解析器×1 + P5 肘点钉扎×1 + S1 副本同步×1 "
          "+ 摘要冒烟×1)")
