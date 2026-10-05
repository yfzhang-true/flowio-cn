# -*- coding: utf-8 -*-
"""test_cli — flowio M5 全域 CLI TDD 测试 (spec v2.1 §2 单入口命令树)。

红/绿纪律: 本文件先行 (红 = truth/hw/geom/flows/twin/test/rebuild 子命令
未实现时 argparse 报 unknown command SystemExit 2); 实现后全绿。
运行: python flowio/tests/test_cli.py   (任意 cwd, stdlib-only)

覆盖 (M5 验收分段):
  1. 命令树形态 — 顶层 --help 列全域; 每子命令 --help 齐全; 未知命令拒 (2);
     codegen = fwgen 别名 (同参同义);
  2. truth  — check (document_problems 聚合: 默认真值 rc=0 / 坏真值 rc=1)
     + show (摘要: 型号/组/refs/rail);
  3. hw     — 产物守门: gen-pcb/route 默认拒绝 (rc=2, 提示
     --i-know-this-erases-routing), gen-sch 默认拒绝 (uuid churn 提示);
     放行后经 KiCad python 子进程派发 (派发表单测, 不真跑 —— 产物零改动);
  4. geom   — FreeCAD 专用解释器子进程派发 (父进程重入 -m flowio geom,
     子进程 runpy 直执行生成器脚本; 派发表 + 环境标记, 不真跑);
  5. flows  — make (纯 stdlib 生成器) / graph (venv-cad networkx) 派发;
  6. twin   — electrical 场景矩阵 12 行 (--json 机器可读);
  7. test   — 分层入口 schema/core/twin/fwgen/blind/l5/quick (派发目标正确,
     CAD 段委托 run_tests.sh 的说明在 --help);
  8. rebuild— SOP 重建矩阵消费: --after <key> 有序重跑链 / 未知键 rc=2 /
     默认概览列全键 (docs/sop/rebuild-matrix.json 机读兑现)。

单测不真跑生成器 (hw/geom/flows-make/venv 层均 patch _spawn 派发记录) —— 
M5 纪律: 产物零改动 (pcb 含 T4 布线, sch 重跑 uuid churn)。
"""
import io
import json
import os
import sys
import tempfile
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from flowio import cli                                        # noqa: E402


class _Rec:
    """_spawn 记录器 (替身派发): 记 argv/kwargs, 返回注入的 int rc。"""

    def __init__(self, rc=0):
        self.calls = []
        self.rc = rc

    def __call__(self, argv, **kw):
        self.calls.append((list(argv), kw))
        return self.rc


def _call(argv, patch_spawn=None, ok_interp=False):
    """main(argv) + stdout 捕获。

    patch_spawn: 替换 cli._spawn (派发记录, 不真跑);
    ok_interp:   同时替换 cli._require_interp 恒 True —— 让派发目标断言不依赖
                 本机是否装有 KiCad/FreeCAD/venv-cad (存在性守门另行单测)。
    """
    buf = io.StringIO()
    old = cli._spawn
    old_ri = cli._require_interp
    if patch_spawn is not None:
        cli._spawn = patch_spawn
    if ok_interp:
        cli._require_interp = lambda py, what, env_var: True
    try:
        with redirect_stdout(buf):
            rc = cli.main(list(argv))
    finally:
        cli._spawn = old
        cli._require_interp = old_ri
    return rc, buf.getvalue()


def _help(argv):
    """--help 期望 SystemExit(0), 返回帮助文本 (argparse 打印到 stdout)。"""
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            cli.main(list(argv) + ["--help"])
    except SystemExit as e:
        assert e.code in (0, None), "help 退出码 %r" % e.code
        return buf.getvalue()
    raise AssertionError("--help 应 SystemExit(0): %s" % argv)


def _runpy_stub(geom_scripts_seen):
    old = cli.runpy.run_path
    def _stub(path, run_name=None):
        geom_scripts_seen.append(Path(path).name)
        return None
    cli.runpy.run_path = _stub
    return old


# ════════ 1. 命令树形态 ════════
def test_top_help_lists_all_domains():
    """顶层 --help 必列全域子命令 (spec §2 单入口命令树)。"""
    txt = _help([])
    for cmd in ("truth", "hw", "geom", "flows", "twin",
                "test", "rebuild", "fwgen"):
        assert cmd in txt, "顶层 help 缺 %s" % cmd


def test_subcommand_help_complete():
    """每 (域, 子命令) --help 齐全 (含关键选项说明)。"""
    cases = [
        (["truth", "check"], "--truth"),
        (["truth", "show"], "--truth"),
        (["hw", "gen-sch"], "--i-know"),
        (["hw", "gen-pcb"], "--i-know-this-erases-routing"),
        (["hw", "route"], "--stage"),
        (["geom", "case"], "FreeCAD"),
        (["geom", "manifold"], "FreeCAD"),
        (["geom", "pump-module"], "FreeCAD"),
        (["geom", "meshes"], "FreeCAD"),
        (["geom", "assembly"], "FreeCAD"),
        (["flows", "make"], "flows.json"),
        (["flows", "graph"], "networkx"),
        (["twin", "electrical"], "--json"),
        (["test", "quick"], "run_tests.sh"),
        (["rebuild"], "--after"),
        (["fwgen"], "--check"),
    ]
    for argv, kw in cases:
        txt = _help(argv)
        assert kw in txt, "%s --help 缺关键说明 %r" % (argv, kw)


def test_unknown_command_rejected():
    """未知命令 → argparse SystemExit(2) (fail-loud, 非静默)。

    stderr 一并捕获: usage 错误走 stderr (argparse 契约), 不捕获则
    污染测试输出 (argparse noise); 顺带断言错误文本含拒收命令名。
    """
    out, err = io.StringIO(), io.StringIO()
    try:
        with redirect_stdout(out), redirect_stderr(err):
            cli.main(["bogus-cmd"])
    except SystemExit as e:
        assert e.code == 2
        assert "bogus-cmd" in err.getvalue(), "stderr 应含 invalid choice 报告"
        return
    raise AssertionError("未知命令应 SystemExit(2)")


def test_codegen_is_fwgen_alias():
    """codegen = fwgen 别名: 同参 (--check) 同义 (rc=0, 输出同构)。"""
    rc_a, out_a = _call(["fwgen", "--check"])
    rc_b, out_b = _call(["codegen", "--check"])
    assert rc_a == 0 and rc_b == 0
    assert out_a == out_b, "别名输出必须与 fwgen 全等"


# ════════ 2. truth ════════
def test_truth_check_default_ok():
    """默认真值 document_problems 空 → rc=0。"""
    rc, out = _call(["truth", "check"])
    assert rc == 0, out
    assert "OK" in out


def test_truth_check_bad_doc_rc1():
    """坏真值 (devices 段缺失) → 问题清单打印 + rc=1。"""
    bad = {"devices": [], "pneumatic_devices": {}}   # 两段皆违例
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "bad.json"
        p.write_text(json.dumps(bad), encoding="utf-8")
        rc, out = _call(["truth", "check", "--truth", str(p)])
    assert rc == 1, out
    assert "devices" in out


def test_truth_show_summary():
    """show 摘要: 组计数/型号/rail_v 关键信息在场。"""
    rc, out = _call(["truth", "show"])
    assert rc == 0, out
    for kw in ("F0520D", "F0520B", "ZR370", "rail_v", "5.0"):
        assert kw in out, "show 摘要缺 %r" % kw


# ════════ 3. hw (产物守门 + 派发) ════════
def test_hw_gen_pcb_guard_default_refuse():
    """gen-pcb 默认拒绝 (rc=2 + 提示显式确认旗标), 不触发任何派发。"""
    rec = _Rec()
    rc, out = _call(["hw", "gen-pcb"], patch_spawn=rec)
    assert rc == 2, out
    assert "--i-know-this-erases-routing" in out
    assert not rec.calls, "拒绝路径不得派发子进程"


def test_hw_route_guard_default_refuse():
    """route 同保护: 默认拒绝 (rc=2), stage 透传字段在提示里。"""
    rec = _Rec()
    rc, out = _call(["hw", "route", "--stage", "4"], patch_spawn=rec)
    assert rc == 2, out
    assert "--i-know-this-erases-routing" in out
    assert not rec.calls


def test_hw_gen_sch_guard_default_refuse():
    """gen-sch 默认拒绝 (重写 .kicad_sch = uuid churn, 产物漂移)。"""
    rec = _Rec()
    rc, out = _call(["hw", "gen-sch"], patch_spawn=rec)
    assert rc == 2, out
    assert "--i-know" in out
    assert not rec.calls


def test_hw_dispatch_after_explicit_ack():
    """显式确认旗标后: KiCad python 子进程派发三个生成器 (记录不真跑)。"""
    rec = _Rec()
    rc, out = _call(["hw", "gen-sch", "--i-know-this-rewrites-products"],
                    patch_spawn=rec, ok_interp=True)
    assert rc == 0 and len(rec.calls) == 1
    argv, _kw = rec.calls[0]
    assert argv[1].endswith("flowio\\hw\\sch_gen.py") or \
        argv[1].endswith("flowio/hw/sch_gen.py"), argv

    rec = _Rec()
    rc, out = _call(["hw", "gen-pcb", "--i-know-this-erases-routing"],
                    patch_spawn=rec, ok_interp=True)
    assert rc == 0 and len(rec.calls) == 1
    argv, _kw = rec.calls[0]
    assert ("pcb_gen.py" in argv[1]) and ("KiCad" in argv[0] or
                                          "kicad" in argv[0].lower()), argv

    rec = _Rec()
    rc, out = _call(["hw", "route", "--stage", "4",
                     "--i-know-this-erases-routing"], patch_spawn=rec,
                    ok_interp=True)
    assert rc == 0 and len(rec.calls) == 1
    argv, _kw = rec.calls[0]
    assert ("route_pcb.py" in argv[1]) and argv[2] == "4", argv


def test_hw_missing_interpreter_rc2():
    """KiCad python 缺失 → 清晰报错 rc=2 (不 spawn)。"""
    old = cli.kicad_python
    cli.kicad_python = lambda: "Z:/missing/kicad-python.exe"
    rec = _Rec()
    try:
        rc, out = _call(["hw", "gen-pcb", "--i-know-this-erases-routing"],
                        patch_spawn=rec)
    finally:
        cli.kicad_python = old
    assert rc == 2 and not rec.calls
    assert "KiCad" in out


# ════════ 4. geom (FreeCAD 专用解释器派发) ════════
def test_geom_dispatch_table():
    """geom 派发表: 五子命令 → flowio/geom/ 下真实生成器脚本。"""
    assert set(cli.GEOM_SCRIPTS) == {"case", "manifold", "pump-module",
                                     "meshes", "assembly"}
    for sub, script in cli.GEOM_SCRIPTS.items():
        p = Path(cli.ROOT) / "flowio" / "geom" / script
        assert p.is_file(), "geom %s 缺脚本 %s" % (sub, p)


def test_geom_parent_reruns_via_freecad_python():
    """父进程: FreeCAD python -m flowio geom <sub> 重入 + 子进程标记 + cwd=仓库根。"""
    rec = _Rec()
    rc, out = _call(["geom", "case"], patch_spawn=rec, ok_interp=True)
    assert rc == 0 and len(rec.calls) == 1, out
    argv, kw = rec.calls[0]
    assert argv[1:] == ["-m", "flowio", "geom", "case"], argv
    assert "FreeCAD" in argv[0] or "freecad" in argv[0].lower(), argv
    assert kw.get("env", {}).get(cli.GEOM_CHILD_ENV) == "1", "缺子进程标记"
    assert Path(kw.get("cwd", "")).resolve() == Path(cli.ROOT).resolve()


def test_geom_child_executes_generator_script():
    """子进程 (标记环境): runpy 直执行 flowio/geom/<生成器> (免二次派发)。"""
    seen = []
    old = _runpy_stub(seen)
    os.environ[cli.GEOM_CHILD_ENV] = "1"
    try:
        rc, out = _call(["geom", "manifold"])
    finally:
        del os.environ[cli.GEOM_CHILD_ENV]
        cli.runpy.run_path = old
    assert rc == 0, out
    assert seen == ["make_manifold.py"], seen


def test_geom_missing_interpreter_rc2():
    old = cli.freecad_python
    cli.freecad_python = lambda: "Z:/missing/freecad-python.exe"
    rec = _Rec()
    try:
        rc, out = _call(["geom", "meshes"], patch_spawn=rec)
    finally:
        cli.freecad_python = old
    assert rc == 2 and not rec.calls
    assert "FreeCAD" in out


# ════════ 5. flows ════════
def test_flows_make_dispatch():
    """flows make: 纯 stdlib 生成器, 当前解释器派发 make_flows.py。"""
    rec = _Rec()
    rc, out = _call(["flows", "make"], patch_spawn=rec)
    assert rc == 0 and len(rec.calls) == 1, out
    argv, _kw = rec.calls[0]
    assert "make_flows.py" in argv[1] and argv[0] == sys.executable, argv


def test_flows_graph_dispatch_venv():
    """flows graph: networkx → venv-cad python 派发 device_graph.py。"""
    old = cli.venv_cad_python
    cli.venv_cad_python = lambda: "X:/fake/venv-cad/python.exe"
    rec = _Rec()
    try:
        rc, out = _call(["flows", "graph"], patch_spawn=rec, ok_interp=True)
    finally:
        cli.venv_cad_python = old
    assert rc == 0 and len(rec.calls) == 1, out
    argv, _kw = rec.calls[0]
    assert argv[0] == "X:/fake/venv-cad/python.exe"
    assert "device_graph.py" in argv[1]


def test_flows_graph_missing_venv_rc2():
    old = cli.venv_cad_python
    cli.venv_cad_python = lambda: ""
    rec = _Rec()
    try:
        rc, out = _call(["flows", "graph"], patch_spawn=rec)   # 真 _require_interp
    finally:
        cli.venv_cad_python = old
    assert rc == 2 and not rec.calls
    assert "venv-cad" in out


# ════════ 6. twin ════════
def test_twin_electrical_matrix():
    """twin electrical: 12 场景全跑 + 关键锚点 (single_inflate=1.375A)。"""
    rc, out = _call(["twin", "electrical"])
    assert rc == 0, out
    assert "worst_9v_hold_pump" in out and "OVER" in out


def test_twin_electrical_json():
    """--json 机器可读: 12 行, single_inflate i_total=1.375 (0.45×2+0.475)。"""
    rc, out = _call(["twin", "electrical", "--json"])
    assert rc == 0, out
    rows = json.loads(out)
    assert len(rows) == 12
    by = {r["name"]: r for r in rows}
    assert abs(by["single_inflate"]["i_total_a"] - 1.375) < 1e-9
    assert by["worst_9v_hold_pump"]["over_limit"] is True


# ════════ 7. test 分层入口 ════════
def test_test_layer_dispatch():
    """分层派发: core→test_core.py / l5→venv-cad all / quick=python 侧全五套。"""
    rec = _Rec()
    rc, out = _call(["test", "core"], patch_spawn=rec)
    assert rc == 0 and len(rec.calls) == 1
    assert rec.calls[0][0] == [sys.executable,
                               str(Path(cli.ROOT) / "flowio" / "tests" / "test_core.py")]

    old = cli.venv_cad_python
    cli.venv_cad_python = lambda: "X:/fake/venv-cad/python.exe"
    rec = _Rec()
    try:
        rc, out = _call(["test", "l5"], patch_spawn=rec, ok_interp=True)
    finally:
        cli.venv_cad_python = old
    assert rc == 0 and len(rec.calls) == 1
    argv, _kw = rec.calls[0]
    assert argv[0] == "X:/fake/venv-cad/python.exe"
    assert argv[1].endswith("test_device_geom.py") and argv[2] == "all"

    rec = _Rec()
    rc, out = _call(["test", "quick"], patch_spawn=rec)
    assert rc == 0 and len(rec.calls) == 5, [c[0] for c in rec.calls]
    names = [Path(c[0][1]).name for c in rec.calls]
    assert names == ["test_device_geom.py"] + \
        ["test_core.py", "test_twin.py", "test_fwgen.py", "test_blind_extension.py"], names
    assert rec.calls[0][0][2] == "schema"       # quick 里 L5 只跑 schema 层


def test_test_layer_aggregate_rc():
    """分层聚合: 任一子套件 rc=1 → 整层 rc=1 (fail-loud 透传)。"""
    rec = _Rec(rc=1)
    rc, out = _call(["test", "fwgen"], patch_spawn=rec)
    assert rc == 1, out


# ════════ 8. rebuild (SOP 矩阵机读兑现) ════════
def test_rebuild_after_known_key():
    """--after devices_json_pcb → 有序重跑链 + 同步更新面 (含序号)。"""
    rc, out = _call(["rebuild", "--after", "devices_json_pcb"])
    assert rc == 0, out
    assert "1." in out and "make_case.py" in out
    assert "ingest_device_dims" in out
    assert "同步" in out and "component-registry" in out


def test_rebuild_after_unknown_key_rc2():
    rc, out = _call(["rebuild", "--after", "bogus_change"])
    assert rc == 2, out
    for key in ("devices_json_pcb", "case_geom", "place_layout"):
        assert key in out, "未知键提示应列可用键 %s" % key


def test_rebuild_default_overview():
    """默认 (无 --after): 概览列全 9 变更键 + 触发条件。"""
    rc, out = _call(["rebuild"])
    assert rc == 0, out
    for key in ("devices_json_pcb", "devices_json_pneumatic", "gen_sch_electrical",
                "place_layout", "case_geom", "new_device_jlc", "new_device_taobao",
                "firmware_twin", "gen_pcb_footprint_rules"):
        assert key in out, "概览缺 %s" % key


if __name__ == "__main__":
    test_top_help_lists_all_domains()
    test_subcommand_help_complete()
    test_unknown_command_rejected()
    test_codegen_is_fwgen_alias()
    test_truth_check_default_ok()
    test_truth_check_bad_doc_rc1()
    test_truth_show_summary()
    test_hw_gen_pcb_guard_default_refuse()
    test_hw_route_guard_default_refuse()
    test_hw_gen_sch_guard_default_refuse()
    test_hw_dispatch_after_explicit_ack()
    test_hw_missing_interpreter_rc2()
    test_geom_dispatch_table()
    test_geom_parent_reruns_via_freecad_python()
    test_geom_child_executes_generator_script()
    test_geom_missing_interpreter_rc2()
    test_flows_make_dispatch()
    test_flows_graph_dispatch_venv()
    test_flows_graph_missing_venv_rc2()
    test_twin_electrical_matrix()
    test_twin_electrical_json()
    test_test_layer_dispatch()
    test_test_layer_aggregate_rc()
    test_rebuild_after_known_key()
    test_rebuild_after_unknown_key_rc2()
    test_rebuild_default_overview()
    print("flowio cli tests OK (26 testfns: 命令树×4 + truth×3 + hw×5 + geom×4 "
          "+ flows×3 + twin×2 + test×2 + rebuild×3)")
