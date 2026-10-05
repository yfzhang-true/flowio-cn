# -*- coding: utf-8 -*-
"""test_connections — D2 连接图谱 TDD (spec 2026-10-05 §3 连接图谱/§4 模块接口, plan D2)。

红/绿纪律: 本文件先行 (红 = flowio.twin.connections 校验器与 connections.json 未落地时
import 即败), 实现后全绿。
运行: python flowio/tests/test_connections.py   (任意 cwd, stdlib-only)

覆盖 (spec §3 四条校验, 每条规则 绿例 + 红例):
  0. 数据合法  — connections.json / devices.json json.load 合法; 真值全量校验过四条
                (三类边计数钉死 29/14/15 —— 静默丢边必翻红);
  R1 端点存在  — 每边两端点解析到 devices geom3d 接口面或 modules face, 且边类=端点类;
                红例: 幽灵位号 V9 / 幽灵面 Main.X99 / 类别错配 (气边插电面) / 自环 / 坏 JSON;
  R2 口径匹配  — 管边 tube.id(及异径 id_to) ≤ 端点嘴径; 承插边 socket_dia ≥ 嘴径;
                红例: 通道管 ID3.5 / 承口 3.2 收 B 阀嘴 4.6 / 异径端倒挂;
                WARN 例: fit_pending (registry §6 到货试装条款) 倒挂降级 WARN 不 FAIL;
  R3 六动作路通 — 充/吸/排/测 阀态 BFS 可达 (8 通道逐一); 开阀集↔SCENARIOS 漂移守卫
                (充/吸/排 逐通道程序化比对 single_* 阀集, 两处手改漂移必红); 保 = 阀关断
                割集 (真源: pneumatic-diagram §4 保行 "全关"; SCENARIOS single_hold 是
                V1 economy 电气策略非同源, 显式留证);
                红例: S/V 干管对调 (充+吸翻红 —— diagram §3 "不可对调"的机器化) /
                删 F→大气边 (排红) / 删测压管 (测红) / 阀旁通直连 (保红);
  R4 悬空端点  — 器件气动口 + {2P 壳, 焊片}端子 + 模块面 全部有边连接或显式 reserved;
                红例: 删 S1.P2→ATM 边 (P2 悬空); reserved 机制绿例 + 无标注红例;
  CLI         — python -m flowio connections --check (rc 0=绿 / 1=违例 / 2=文件错)。

WARN 清单纪律 (不 FAIL, 机器可读): 端点/边引用 inferred 接口面 (D1 占位: VV.N2 /
VV.mount_hole, BRINGUP 实测校正); fit_pending 口径倒挂 (泵 ⌀4.2 嘴 × ID5 管, registry §6
"到货试装 4/5 取一") —— 未知真值挂警告可见, 不静默不放假红。
"""
import copy
import json
import os
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

# ---- TDD 红: 校验器/图谱未落地时以下 import 与加载即败 -----------------------
from flowio import cli                                                    # noqa: E402
from flowio.twin import connections as C                                  # noqa: E402

CONN = C.load_connections()          # 真值连接图谱 (缺文件/坏 JSON = 红)

# 真值边计数锚点 (plan D2 全量覆盖: 11 承插+3 主阀外侧管+1 排大气+8 通道+2 跳管
# +2 模块间干管+2 测压支路 = 29 气; 11 阀引线+1 泵电缆+2 电机引线 = 14 电;
# 2 支架环+10 D 阀翻边+1 B 阀孔+1 传感回流+1 歧管支腿 = 15 机)
N_PNEU, N_ELEC, N_MECH = 29, 14, 15


# ---- 小工具 ------------------------------------------------------------------
def _edge(conn, frm, to, cls="pneumatic_edges"):
    return next(e for e in conn[cls] if e["from"] == frm and e["to"] == to)


def _mut(fn):
    conn = copy.deepcopy(CONN)
    fn(conn)
    return conn


def _rep(conn):
    return C.validate(conn=conn)


def _must_fail(conn, needle=None):
    rep = _rep(conn)
    assert not rep["ok"], "期望翻红, 实得 fail=%r" % rep["fail"]
    assert rep["fail"], "红例必须给出 FAIL 明细"
    if needle:
        hits = [f for f in rep["fail"] if needle in f]
        assert hits, "FAIL 明细须含 %r, 实得 %r" % (needle, rep["fail"])
    return rep


# ══════════ 0. 数据合法 + 真值全量校验 ══════════
def test_truth_json_loadable():
    """connections.json / devices.json 均 json.load 合法; 三类边数组与 modules 块齐。"""
    with open(C.CONNECTIONS_JSON, encoding="utf-8") as f:
        raw = json.load(f)
    for k in ("modules", "pneumatic_edges", "electrical_edges", "mechanical_edges"):
        assert k in raw, "缺顶层块 %s" % k
    with open(C.DEVICES_JSON, encoding="utf-8") as f:
        json.load(f)
    assert set(raw["modules"]) == {"Main", "PMod", "ATM"}


def test_real_truth_passes_all_rules():
    """真值全量校验: 四条规则零 FAIL; 边计数钉死 (静默丢边必翻红)。"""
    rep = _rep(CONN)
    assert rep["fail"] == [], "真值不许带 FAIL: %r" % rep["fail"]
    assert rep["ok"] is True
    s = rep["stats"]
    assert s["pneumatic_edges"] == N_PNEU, s
    assert s["electrical_edges"] == N_ELEC, s
    assert s["mechanical_edges"] == N_MECH, s
    # R3 五类动作全通 (真值路通 = 六动作语义图谱的绿证)
    for act in ("inflate", "vacuum", "release", "hold", "measure"):
        assert rep["actions"][act]["ok"], "%s 必须路通: %r" % (act, rep["actions"][act])


def test_real_warn_inventory():
    """WARN 清单: inferred 端点 (VV.N2 / VV.mount_hole) + fit_pending ×2 (泵跳管)。"""
    rep = _rep(CONN)
    assert any("VV.N2" in w and "inferred" in w for w in rep["warn"]), rep["warn"]
    assert any("VV.mount_hole" in w and "inferred" in w for w in rep["warn"]), rep["warn"]
    fp = [w for w in rep["warn"] if "fit_pending" in w]
    assert len(fp) == 2, "泵跳管 fit_pending 恰 2 条 (CHG/SUCK): %r" % fp



# ══════════ R1 端点存在 ══════════
def test_r1_endpoint_missing_red():
    """红例: 幽灵位号 / 幽灵模块面 / 边类-端点类错配 / 自环 各必翻红。"""
    _must_fail(_mut(lambda c: c["pneumatic_edges"].append(
        {"from": "V9.N1", "to": "Main.M", "kind": "socket", "tube": None,
         "socket_dia": 3.2})), "V9")
    _must_fail(_mut(lambda c: c["pneumatic_edges"].append(
        {"from": "V1.N1", "to": "Main.X99", "kind": "socket", "tube": None,
         "socket_dia": 3.2})), "Main.X99")
    # 气动边插电气面 (Main.J10) = 类别错配
    _must_fail(_mut(lambda c: c["pneumatic_edges"].append(
        {"from": "V1.N1", "to": "Main.J10", "kind": "socket", "tube": None,
         "socket_dia": 3.2})), "J10")
    _must_fail(_mut(lambda c: c["pneumatic_edges"].append(
        {"from": "V1.N1", "to": "V1.N1", "kind": "socket", "tube": None,
         "socket_dia": 3.2})), "V1.N1")


def test_r1_bad_json_red():
    """红例: 坏 JSON load 必抛 ValueError (带文件路径, 禁静默)。"""
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                     encoding="utf-8") as f:
        f.write("{oops 不是 JSON")
        bad = f.name
    try:
        try:
            C.load_connections(bad)
            raise AssertionError("坏 JSON 必须抛 ValueError")
        except ValueError as e:
            assert bad in str(e), "异常须带路径: %s" % e
    finally:
        os.remove(bad)



# ══════════ R2 口径匹配 ══════════
def test_r2_tube_dia_red():
    """红例: 通道管 ID3.5 > 阀嘴 ⌀3.0 / 异径端 id_to 倒挂 / 承插孔收不下嘴。"""
    def bump_ch(c):
        _edge(c, "V1.N2", "Main.CH1")["tube"]["id"] = 3.5
    _must_fail(_mut(bump_ch), "R2")

    def bump_idto(c):
        _edge(c, "Main.S_wall", "VS.N2")["tube"]["id_to"] = 3.5
    _must_fail(_mut(bump_idto), "R2")

    def small_socket(c):
        _edge(c, "VV.N1", "Main.M")["socket_dia"] = 3.2   # ⌀4.6 嘴塞不进 ⌀3.2 承口
    _must_fail(_mut(small_socket), "R2")


def test_r2_fit_pending_warn_not_fail():
    """泵嘴 ⌀4.2 × ID5 管: 无 fit_pending=FAIL; 挂 fit_pending (registry §6 试装)=WARN。"""
    def bump_no_flag(c):
        _edge(c, "P1.CHG", "PMod.S_panel")["tube"]["id"] = 6.0
        del _edge(c, "P1.CHG", "PMod.S_panel")["fit_pending"]
    _must_fail(_mut(bump_no_flag), "R2")

    def bump_with_flag(c):
        _edge(c, "P1.CHG", "PMod.S_panel")["tube"]["id"] = 6.0   # fit_pending 仍在
    rep = _rep(_mut(bump_with_flag))
    assert rep["ok"] is True and rep["fail"] == []
    assert any("P1.CHG" in w and "fit_pending" in w for w in rep["warn"])


# ══════════ R3 六动作语义路通 ══════════
def test_r3_swap_sv_tubes_red():
    """红例: S/V 干管对调 —— diagram §3 "S=充/V=吸 不可对调" 的机器化 (充+吸翻红)。"""
    def swap(c):
        a = _edge(c, "Main.S_wall", "VS.N2")
        b = _edge(c, "Main.V_wall", "VV.N2")
        a["from"], b["from"] = b["from"], a["from"]
    rep = _must_fail(_mut(swap))
    assert not rep["actions"]["inflate"]["ok"], "充路必断"
    assert not rep["actions"]["vacuum"]["ok"], "吸路必断"
    assert rep["actions"]["release"]["ok"] and rep["actions"]["measure"]["ok"] \
        and rep["actions"]["hold"]["ok"], "排/测/保不受对调影响"


def test_r3_release_path_red():
    """红例: 删 F 壁孔→大气边 → 排气路断 (全通道翻红)。"""
    def drop(c):
        c["pneumatic_edges"] = [e for e in c["pneumatic_edges"]
                                if (e["from"], e["to"]) != ("Main.F_wall", "ATM.open")]
    rep = _must_fail(_mut(drop), "R3")
    assert not rep["actions"]["release"]["ok"]
    assert rep["actions"]["inflate"]["ok"], "充路不受排气边缺失影响"


def test_r3_measure_path_red():
    """红例: 删测压支路 (M→S1.P1) → 测量路断。"""
    def drop(c):
        c["pneumatic_edges"] = [e for e in c["pneumatic_edges"]
                                if (e["from"], e["to"]) != ("Main.M", "S1.P1")]
    rep = _must_fail(_mut(drop), "R3")
    assert not rep["actions"]["measure"]["ok"]
    assert rep["actions"]["inflate"]["ok"]


def test_r3_hold_cut_red():
    """红例: M→CH1 阀旁通直连 = 保压割集破坏 (全阀关断后 CH1 仍通传感/大气)。"""
    def bypass(c):
        c["pneumatic_edges"].append(
            {"from": "Main.M", "to": "Main.CH1", "kind": "tube",
             "tube": {"id": 3.0, "od": 7.0, "len_mm": 10.0, "bend": 0},
             "desc": "坏例: 旁通", "src": "test fixture"})
    rep = _must_fail(_mut(bypass), "R3")
    assert not rep["actions"]["hold"]["ok"]
    assert rep["actions"]["inflate"]["ok"], "旁通不破坏充路可达性 (保是割集判据)"


def test_r3_opensets_parity_with_scenarios():
    """守卫: R3 opensets (connections._R3_OPENS) ↔ twin.scenarios SCENARIOS 阀集
    程序化比对 —— 充/吸/排 逐通道一致, 任一侧手改漂移必红 (两审共同 Minor)。
    测 = 决策 3=1× 分时 (无 SCENARIOS 对应场景, 单独钉形状); 保 = diagram §4 保行
    "全关" 割集, 与 single_hold (V1 economy 电气策略) 非同源, 显式留证不比对。"""
    from flowio.twin.scenarios import SCENARIOS
    pair = {"inflate": "single_inflate", "vacuum": "single_vacuum",
            "release": "single_release"}
    for act, scen in pair.items():
        sc_open = {r for r, st in SCENARIOS[scen]["valves"].items()
                   if st in ("full_open", "pull_in")}
        chans = {r for r in sc_open if r[1:].isdigit()}       # 通道阀 V1..V8
        mains = {"V:" + r for r in sc_open - chans}           # 主阀 (VS/VV/VF)
        assert chans == {"V1"}, \
            "%s 须恰含通道阀 V1 + 主阀 (单通道语义): %r" % (scen, sc_open)
        for i in range(1, 9):
            opens = {s.format(i=i) for s in C._R3_OPENS[act]}
            assert opens == mains | {"V:V%d" % i}, \
                "R3 %s openset 与 %s 阀集漂移 (i=%d): %r vs %r" % (act, scen, i, opens, mains)
    for i in range(1, 9):                                         # 测: 恰一个通道阀, 无主阀
        assert {s.format(i=i) for s in C._R3_OPENS["measure"]} == {"V:V%d" % i}
    assert SCENARIOS["single_hold"]["valves"] == {"V1": "economy"}, \
        "single_hold 语义漂移: R3 保判据真源是 diagram §4 '全关', 不随 single_hold 变"


# ══════════ R4 悬空端点 ══════════
def test_r4_dangling_red():
    """红例: 删 S1.P2→ATM 边 → P2 悬空翻红 (大气开放是语义, 不是可丢边)。"""
    def drop(c):
        c["pneumatic_edges"] = [e for e in c["pneumatic_edges"]
                                if (e["from"], e["to"]) != ("S1.P2", "ATM.open")]
    _must_fail(_mut(drop), "S1.P2")


def test_r4_reserved_mechanism():
    """reserved 显式标注 = 悬空豁免: 带标注绿 / 无标注红 (模块预留面语义)。"""
    def add_reserved(c):
        c["modules"]["Main"]["faces"].append(
            {"name": "spare_port", "kind": "pneumatic", "dia": 3.4,
             "external": True, "reserved": "预留 (P2 扩展位)"})
    rep = _rep(_mut(add_reserved))
    assert rep["ok"] is True and rep["fail"] == []

    def add_unmarked(c):
        c["modules"]["Main"]["faces"].append(
            {"name": "spare_port", "kind": "pneumatic", "dia": 3.4,
             "external": True})
    _must_fail(_mut(add_unmarked), "spare_port")


# ══════════ CLI: python -m flowio connections --check ══════════
def _cli(argv):
    import io
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = cli.main(argv)
    return rc, buf.getvalue()


def test_cli_connections_check():
    """CLI 三档 rc: 默认真值 0 / 数据违例 1 / 文件缺失或坏 JSON 2。"""
    rc, out = _cli(["connections", "--check"])
    assert rc == 0 and "[OK]" in out, (rc, out)
    assert "29" in out and "14" in out and "15" in out, "摘要须含三类边计数"

    def broken(c):
        c["pneumatic_edges"].append(
            {"from": "V9.N1", "to": "Main.M", "kind": "socket", "tube": None,
             "socket_dia": 3.2})
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                     encoding="utf-8") as f:
        json.dump(_mut(broken), f, ensure_ascii=False)
        bad_data = f.name
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                     encoding="utf-8") as f:
        f.write("{oops")
        bad_json = f.name
    try:
        rc, out = _cli(["connections", "--check", "--conn", bad_data])
        assert rc == 1 and "V9" in out, (rc, out)
        rc, out = _cli(["connections", "--check", "--conn", bad_json])
        assert rc == 2, (rc, out)
        rc, out = _cli(["connections", "--check",
                        "--conn", str(Path(tempfile.gettempdir()) / "no-such-conn.json")])
        assert rc == 2, (rc, out)
    finally:
        os.remove(bad_data)
        os.remove(bad_json)


# ══════════ 摘要模式 (无 --check): 计数+动作表, 不作门 ══════════
def test_cli_connections_summary_mode():
    rc, out = _cli(["connections"])
    assert rc == 0 and "pneumatic" in out and "inflate" in out, out[:400]


if __name__ == "__main__":
    test_truth_json_loadable()
    test_real_truth_passes_all_rules()
    test_real_warn_inventory()
    test_r1_endpoint_missing_red()
    test_r1_bad_json_red()
    test_r2_tube_dia_red()
    test_r2_fit_pending_warn_not_fail()
    test_r3_swap_sv_tubes_red()
    test_r3_release_path_red()
    test_r3_measure_path_red()
    test_r3_hold_cut_red()
    test_r3_opensets_parity_with_scenarios()
    test_r4_dangling_red()
    test_r4_reserved_mechanism()
    test_cli_connections_check()
    test_cli_connections_summary_mode()
    print("flowio.twin.connections tests OK (16 testfns: 数据合法×3 + R1×2 + R2×2 "
          "+ R3×5 + R4×2 + CLI×2)")
