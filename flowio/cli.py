# -*- coding: utf-8 -*-
"""flowio.cli — 包级全域命令行入口 (M5: spec v2.1 §2 单入口命令树)。

命令树 (python -m flowio <域> <子命令>):
    truth  check|show      真值 schema 校验 (document_problems 聚合) / 摘要
    hw     gen-sch|gen-pcb|route   硬件生成器 (⚠ 产物守门: 默认拒绝)
    geom   case|manifold|pump-module|meshes|assembly   FreeCAD 结构生成器
    flows  make|graph      流拓扑生成 (pos.csv→flows.json) / 器件关系图
    twin   electrical      场景矩阵 (12 场景母线电气解, --json 机器可读)
    test   schema|core|twin|fwgen|blind|l5|quick      分层测试入口
    rebuild [--after KEY]  SOP 重建矩阵消费 (docs/sop/rebuild-matrix.json)
    fwgen  [--check]       三语参数 codegen (codegen = 本命令别名)

入口选择 (M3 裁定维持): 包内 `python -m flowio`, 不设独立脚本 —— 单入口零漂移。

专用解释器 (docs/sop/SKILL.md §0 三环境路径表; 环境变量可覆盖):
    FLOWIO_KICAD_PY   KiCad python (pcbnew 绑定; hw gen-pcb/route)
    FLOWIO_FREECAD_PY FreeCAD python (几何内核绑定; geom 全部)
    FLOWIO_VENV_CAD   venv-cad (networkx/trimesh; flows graph / test l5)

geom 子进程重入机制 (任务裁定说明): FreeCAD 绑定只能在专用解释器内 import,
故父进程 (任意 python) 检测到 geom 子命令时, 以 subprocess 调
`<FreeCAD python> -m flowio geom <sub>` 重入本 CLI (cwd=仓库根, 环境标记
FLOWIO_GEOM_CHILD=1 防无限递归); 子进程内识别标记后经 runpy 直执行
flowio/geom/<生成器>.py (脚本形态保持 M1 迁移语义, import 即执行)。hw 同理
经 KiCad python 子进程执行, 但脚本自足无需重入 (直接跑脚本文件)。

产物零改动纪律 (M5): hw 三生成器默认拒绝执行 —— pcb/route 重写含 T4 布线
的 flowio-p1.kicad_pcb, sch 重写嵌入符号 (uuid4 全换 = 产物漂移); 须显式
携带确认旗标方派发。geom/flows-make 可确定性重生成 (SOP 重跑链成员)。

rc 约定 (全域统一, 调用方 CI/脚本按此分级处置): 0=绿 / 1=数据问题
(truth check 违例, fwgen --check 漂移, test 子套件失败) / 2=环境或拒绝
(专用解释器缺失, hw 产物守门拒绝, 未知命令/变更键; argparse 误用同 SystemExit 2)。

webgen 裁定注记 (M5): spec §2 的 webgen 域并入 fwgen —— params_gen.js 由
fwgen.ts_gen 单 codegen 内核生成 (三语一份模板源); 第三介质出现前不拆独立域/子命令。
"""
from __future__ import annotations

import argparse
import json
import os
import runpy
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]            # 仓库根 (flowio/ 的上级)

# ---- geom 子命令 → 生成器脚本 (模块级表: 测试/派发/文档共用) ------------------
GEOM_SCRIPTS = {
    "case": "make_case.py",
    "manifold": "make_manifold.py",
    "pump-module": "make_pump_module.py",
    "meshes": "make_meshes.py",
    "assembly": "make_assembly.py",
}
GEOM_CHILD_ENV = "FLOWIO_GEOM_CHILD"                  # 子进程重入标记 (防递归)

REBUILD_MATRIX = ROOT / "docs" / "sop" / "rebuild-matrix.json"


# ---- 专用解释器定位 (默认值 = SKILL §0 路径表; env 可覆盖) --------------------
def kicad_python() -> str:
    return os.environ.get("FLOWIO_KICAD_PY",
                          "E:/Program Files/KiCad/10.0/bin/python.exe")


def freecad_python() -> str:
    return os.environ.get("FLOWIO_FREECAD_PY", "E:/FreeCAD/bin/python.exe")


def venv_cad_python() -> str:
    """venv-cad 解释器 (networkx/trimesh); 探测不到返回 '' (调用方自行 SKIP/拒)。"""
    env = os.environ.get("FLOWIO_VENV_CAD")
    if env:
        return env
    for cand in (ROOT / "tools" / "venv-cad" / "Scripts" / "python.exe",
                 Path("E:/FLOWIO/tools/venv-cad/Scripts/python.exe")):
        if cand.exists():
            return str(cand)
    return ""


# ---- 子进程派发 (单测 patch 点: 不真跑生成器) ---------------------------------
def _spawn(argv, cwd=None, env=None) -> int:
    """同步子进程, 返回退出码 (stderr 直通, rc 透传)。"""
    r = subprocess.run(argv, cwd=cwd, env=env)
    return int(r.returncode)


def _require_interp(py: str, what: str, env_var: str):
    """解释器存在性守门 (空串=未探测到, 同缺失); 缺失打印 FATAL 并返回 False。"""
    if py and Path(py).exists():
        return True
    print("FATAL: 未找到 %s python (%s) —— %s 需专用解释器绑定"
          % (what, py, what))
    print("       (docs/sop/SKILL.md §0 三环境路径表; %s 环境变量可覆盖)" % env_var)
    return False


# ═══════════════════ truth ═══════════════════
def _cmd_truth_check(args) -> int:
    """truth check: document_problems 聚合校验 (与 TruthSource._validate 同源)。"""
    from flowio.core.truth import TruthSource
    from flowio.truth import document_problems

    src = TruthSource(args.truth)                     # 路径解析单源 (FLOWIO_TRUTH)
    try:
        doc = json.loads(src.path.read_text(encoding="utf-8"))
    except OSError as e:
        print("FATAL: 真值文件不可读: %s (%s)" % (src.path, e))
        return 2
    except ValueError as e:
        print("FATAL: 真值非合法 JSON: %s (%s)" % (src.path, e))
        return 2
    problems = document_problems(doc)
    for p in problems:
        print("[FAIL] %s" % p)
    if problems:
        print("truth check: %d 问题 → %s" % (len(problems), src.path))
        return 1
    print("[OK] truth check: 0 问题 → %s" % src.path)
    return 0


def _cmd_truth_show(args) -> int:
    """truth show: 真值摘要 (组计数/型号/驱动策略/线圈推导)。"""
    from flowio.core.truth import TruthSource
    from flowio.truth import drive_policy, pump_spec, sensor_spec, valve_specs

    src = TruthSource(args.truth)
    devs, pn = src.devices, src.pneumatic_devices
    dp = drive_policy(pn)
    print("truth: %s" % src.path)
    print("devices: %d 条目 / %d 位号 (PCB 贴装)"
          % (len(devs), sum(len(e.get("refs") or []) for e in devs)))
    for g in ("valves", "valve_vacuum_master", "pump", "sensor"):
        ents = pn.get(g) or []
        refs = sum(len(e.get("refs") or []) for e in ents)
        models = ", ".join(sorted({str(e.get("model", "?")) for e in ents})) or "-"
        print("pneumatic %-20s %d 条目 / %2d 位号: %s" % (g, len(ents), refs, models))
    print("drive_policy: rail_v=%s duties=%s pull_in_ms=%s pump_max_duty=%s"
          % (dp.rail_v, dp.duties, dp.pull_in_ms, dp.pump_max_duty))
    print("r_coil (rated_v/i 推导): %s"
          % ", ".join("%s=%gΩ" % (s.model, s.r_coil) for s in valve_specs(pn)))
    ps = pump_spec(pn)
    print("pump: %s load=%gA flow=%glpm" % (ps.model, ps.load_current_a, ps.flow_lpm))
    ss = sensor_spec(pn)
    print("sensor: %s i2c=%s" % (ss.model, ss.i2c_addr))
    return 0


# ═══════════════════ hw (产物守门) ═══════════════════
_HW_HAZARD = {
    "gen-pcb": ("重写 flowio-p1.kicad_pcb 裸板骨架 —— 板内含 T4 全部布线成果 "
                "(338 缺陷清零) 且 fab 产物已下单就绪, 重跑=毁布线 (M1 禁令)",
                "--i-know-this-erases-routing"),
    "route": ("直接改写 flowio-p1.kicad_pcb (布线/收尾阶段) —— 同 gen-pcb 禁令, "
              "T4 布线成果不可再生", "--i-know-this-erases-routing"),
    "gen-sch": ("重写 flowio-p1.kicad_sch —— 嵌入符号 uuid4 全换 (uuid churn), "
                "与库内提交版漂移 (M5 产物零改动纪律)",
                "--i-know-this-rewrites-products"),
}


def _cmd_hw(args) -> int:
    sub = args.hw_sub
    hazard, flag = _HW_HAZARD[sub]
    ack = bool(getattr(args, "ack", False))
    if not ack:
        print("⛔ 拒绝: hw %s %s" % (sub, hazard))
        print("   确需重建: python -m flowio hw %s %s%s"
              % (sub, flag,
                 " --stage %d" % args.stage if sub == "route" else ""))
        return 2
    py = kicad_python()
    if not _require_interp(py, "KiCad", "FLOWIO_KICAD_PY"):
        return 2
    scripts = {"gen-sch": "sch_gen.py", "gen-pcb": "pcb_gen.py",
               "route": "route_pcb.py"}
    argv = [py, str(ROOT / "flowio" / "hw" / scripts[sub])]
    if sub == "route":
        argv.append(str(args.stage))                  # stage 透传 (累积, 3=布线 4=SES 后收尾)
    print("→ %s (KiCad python 子进程; 产物守门已显式确认)" % " ".join(argv))
    return _spawn(argv)


# ═══════════════════ geom (FreeCAD 专用解释器重入) ═══════════════════
def _cmd_geom(args) -> int:
    sub = args.geom_sub
    script = ROOT / "flowio" / "geom" / GEOM_SCRIPTS[sub]
    if os.environ.get(GEOM_CHILD_ENV) == "1":         # 子进程重入: 直执行生成器
        runpy.run_path(str(script))
        return 0
    py = freecad_python()
    if not _require_interp(py, "FreeCAD", "FLOWIO_FREECAD_PY"):
        return 2
    env = dict(os.environ, **{GEOM_CHILD_ENV: "1"})
    print("→ %s -m flowio geom %s  (FreeCAD 绑定需专用解释器, 子进程重入执行 %s)"
          % (py, sub, script.name))
    return _spawn([py, "-m", "flowio", "geom", sub], cwd=str(ROOT), env=env)


# ═══════════════════ flows ═══════════════════
def _cmd_flows(args) -> int:
    if args.flows_sub == "make":
        print("→ 生成 firmware/twin/webapp/{flows.json,hotspots.json} "
              "(确定性重生成; 对拍门: python tools/compare_baseline.py --products)")
        return _spawn([sys.executable, str(ROOT / "flowio" / "flows" / "make_flows.py")])
    venv = venv_cad_python()
    if not _require_interp(venv, "venv-cad", "FLOWIO_VENV_CAD"):
        return 2
    print("→ %s device_graph.py (networkx: 电气边+空间边+21↔21 匹配+flows 交叉校验)"
          % venv)
    return _spawn([venv, str(ROOT / "flowio" / "flows" / "device_graph.py")])


# ═══════════════════ twin ═══════════════════
def _cmd_twin_electrical(args) -> int:
    from flowio.twin.electrical import load_params
    from flowio.twin.scenarios import run_matrix

    params = load_params(args.truth) if args.truth else None
    rows = run_matrix(params=params)
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=1))
        return 0
    for r in rows:
        flag = "OVER" if r["over_limit"] else "ok"
        print("[%-4s] %-28s %8.3f A  %s"
              % (flag, r["name"], r["i_total_a"], r["desc"]))
    over = sum(1 for r in rows if r["over_limit"])
    print("twin electrical: %d 场景 / %d 超限 (--json 机器可读)" % (len(rows), over))
    return 0


# ═══════════════════ test 分层入口 ═══════════════════
_TEST_GEOM = ROOT / "hardware" / "flowio-p1" / "enclosure" / "test_device_geom.py"
_TESTDIR = ROOT / "flowio" / "tests"


def _layer_suites(layer):
    """层名 → [(python, 脚本, 额外参数)]; 探测失败返回 None (调用方 rc=2)。"""
    venv = venv_cad_python()
    if layer == "schema":                             # T1 谓词层 stdlib-only, venv 缺则回落
        return [[venv or sys.executable, str(_TEST_GEOM), ["schema"]]]
    if layer in ("core", "twin", "fwgen", "blind"):
        fname = {"core": "test_core.py", "twin": "test_twin.py",
                 "fwgen": "test_fwgen.py", "blind": "test_blind_extension.py"}[layer]
        return [[sys.executable, str(_TESTDIR / fname), []]]
    if layer == "l5":                                 # L5 全档需 networkx/trimesh
        if not venv:
            print("FATAL: 未探测到 venv-cad (L5 需 networkx/trimesh; "
                  "FLOWIO_VENV_CAD 可覆盖; SKILL §0 路径表)")
            return None
        return [[venv, str(_TEST_GEOM), ["all"]]]
    if layer == "quick":                              # = 全部 python 侧 (无 CAD)
        return (_layer_suites("schema") + _layer_suites("core")
                + _layer_suites("twin") + _layer_suites("fwgen")
                + _layer_suites("blind"))
    return None


def _cmd_test(args) -> int:
    suites = _layer_suites(args.layer)
    if not suites:
        print("FATAL: 未知测试层 %r" % args.layer)
        return 2
    rc = 0
    for py, script, extra in suites:
        print("══ %s %s ══" % (Path(script).name, " ".join(extra)))
        rc = rc or _spawn([py, script] + extra)
    if rc:
        print("test %s: FAIL (rc=%d)" % (args.layer, rc))
    return rc


# ═══════════════════ rebuild (SOP 矩阵机读消费) ═══════════════════
def _cmd_rebuild(args) -> int:
    data = json.loads(REBUILD_MATRIX.read_text(encoding="utf-8"))
    changes = data.get("changes", {})
    if not args.after:
        print("SOP 重建矩阵概览 (%s):" % REBUILD_MATRIX)
        for key, row in changes.items():
            print("  %-26s %s" % (key, row.get("trigger", "")))
        print("有序重跑链: python -m flowio rebuild --after <change-key>")
        return 0
    if args.after not in changes:
        print("FATAL: 未知变更键 %r; 可用键:" % args.after)
        for key in changes:
            print("  - %s  (%s)" % (key, changes[key].get("trigger", "")))
        return 2
    row = changes[args.after]
    print("变更链 [%s]: %s" % (args.after, row.get("trigger", "")))
    print("重跑 (按序):")
    for i, step in enumerate(row.get("rerun", []), 1):
        print("  %d. %s" % (i, step))
    sync = row.get("sync", [])
    if sync:
        print("同步更新面:")
        for s in sync:
            print("  - %s" % s)
    return 0


# ═══════════════════ fwgen / codegen (M3, 别名) ═══════════════════
def _cmd_fwgen(args) -> int:
    from flowio import fwgen
    from flowio.core.truth import TruthSource

    truth = TruthSource(args.truth)
    if args.check:
        sync = fwgen.check_artifacts(args.out_root, truth)
        for rel, ok in sorted(sync.items()):
            print("[%s] %s" % ("OK  " if ok else "DRIFT", rel))
        drifted = [r for r, ok in sorted(sync.items()) if not ok]
        if drifted:
            print("fwgen --check: %d 生成物漂移 → 重生成: python -m flowio fwgen"
                  % len(drifted))
            return 1
        print("fwgen --check: %d/%d 生成物与真值渲染全等" % (len(sync), len(sync)))
        return 0
    for p in fwgen.write_all(truth, args.out_root):
        print("written %s" % p)
    return 0


# ═══════════════════ 命令树构建 ═══════════════════
def _build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="python -m flowio",
        description="FLOWIO-CN 数字孪生内核 CLI (M5 全域: 真值单源到五域介质的"
                    "统一入口; 各域专用解释器经子进程派发, 见 SKILL §0)",
        epilog="专用解释器环境变量: FLOWIO_KICAD_PY / FLOWIO_FREECAD_PY / "
               "FLOWIO_VENV_CAD / FLOWIO_TRUTH (真值路径覆盖)")
    sub = ap.add_subparsers(dest="cmd", required=True, metavar="<域>")

    # ---- truth ----
    truth = sub.add_parser("truth", help="真值域: devices.json 校验/摘要")
    tsub = truth.add_subparsers(dest="truth_sub", required=True, metavar="<子命令>")
    tc = tsub.add_parser("check", help="schema 校验 (document_problems 聚合; "
                                       "问题清单 rc=1, 文件级错误 rc=2)")
    tc.add_argument("--truth", default=None, metavar="PATH",
                    help="devices.json 路径 (默认仓库真值, FLOWIO_TRUTH 可覆盖)")
    ts = tsub.add_parser("show", help="摘要: 组计数/型号/驱动策略/线圈推导")
    ts.add_argument("--truth", default=None, metavar="PATH",
                    help="devices.json 路径 (默认仓库真值, FLOWIO_TRUTH 可覆盖)")

    # ---- hw (产物守门) ----
    hw = sub.add_parser("hw", help="硬件域: sch/pcb/route 生成器 "
                                   "(⚠ 默认拒绝 —— 产物零改动守门)")
    hsub = hw.add_subparsers(dest="hw_sub", required=True, metavar="<子命令>")
    hs = hsub.add_parser("gen-sch", help="原理图生成 (KiCad python 子进程; "
                                         "重写 .kicad_sch = uuid churn)")
    hs.add_argument("--i-know-this-rewrites-products", dest="ack",
                    action="store_true",
                    help="显式确认重写 .kicad_sch 产物 (uuid 归一化对比后方可提交)")
    hp = hsub.add_parser("gen-pcb", help="PCB 裸板骨架生成 (KiCad python; "
                                         "⛔ 重跑=毁 T4 布线)")
    hp.add_argument("--i-know-this-erases-routing", dest="ack",
                    action="store_true",
                    help="显式确认擦除 flowio-p1.kicad_pcb 全部布线 (M1 禁令)")
    hr = hsub.add_parser("route", help="布线器阶段执行 (KiCad python; "
                                       "⛔ 同 gen-pcb 禁令)")
    hr.add_argument("--stage", type=int, default=3, metavar="N",
                    help="累积阶段 (3=布线 4=SES 后收尾; 默认 3, 透传 route_pcb.py)")
    hr.add_argument("--i-know-this-erases-routing", dest="ack",
                    action="store_true",
                    help="显式确认改写 flowio-p1.kicad_pcb (M1 禁令)")

    # ---- geom (FreeCAD 专用解释器) ----
    geom = sub.add_parser("geom", help="结构域: FreeCAD 参数化生成器 "
                                       "(FreeCAD python 子进程重入执行)")
    gsub = geom.add_subparsers(dest="geom_sub", required=True, metavar="<子命令>")
    for name, script in GEOM_SCRIPTS.items():
        desc = "%s 结构生成 (FreeCAD 绑定需专用解释器, 父进程经 FreeCAD python " \
               "子进程重入执行 flowio/geom/%s)" % (name, script)
        gsub.add_parser(name, help=desc, description=desc)

    # ---- flows ----
    flows = sub.add_parser("flows", help="气路流拓扑域: 流向图生成/器件关系图")
    fsub = flows.add_subparsers(dest="flows_sub", required=True, metavar="<子命令>")
    fmk = fsub.add_parser(
        "make", help="pos.csv → flows.json + hotspots.json (确定性重生成)",
        description="pos.csv → firmware/twin/webapp/{flows.json,hotspots.json} "
                    "(确定性重生成, 纯 stdlib; 产物对拍门: "
                    "python tools/compare_baseline.py --products)")
    fgr = fsub.add_parser(
        "graph", help="器件关系图 (venv-cad networkx)",
        description="器件关系图 (venv-cad networkx): 电气边(网表) + 空间边"
                    "(端口→槽) + 21↔21 完美匹配 + flows.json 交叉校验 (只读)")

    # ---- twin ----
    twin = sub.add_parser("twin", help="孪生域: 电气/热/气动仿真模型入口")
    twsub = twin.add_subparsers(dest="twin_sub", required=True, metavar="<子命令>")
    te = twsub.add_parser("electrical", help="12 场景母线电气解矩阵 "
                                             "(worst=4.525A 超限锚点)")
    te.add_argument("--truth", default=None, metavar="PATH",
                    help="devices.json 路径 (默认仓库真值, FLOWIO_TRUTH 可覆盖)")
    te.add_argument("--json", action="store_true",
                    help="机器可读输出 (rows JSON; CI/对拍复用)")

    # ---- test 分层 ----
    test = sub.add_parser("test", help="分层测试入口 (python 侧; CAD 装配 L1-L4 段 "
                                       "委托 firmware/twin/run_tests.sh)")
    test.add_argument("layer",
                      choices=["schema", "core", "twin", "fwgen", "blind", "l5",
                               "quick"],
                      help="schema=T1 谓词 / core,twin,fwgen,blind=flowio 单套 "
                           "/ l5=venv-cad 全档 / quick=全部 python 侧 (无 CAD; "
                           "CAD 段走 run_tests.sh)")

    # ---- rebuild ----
    rb = sub.add_parser("rebuild", help="SOP 重建矩阵消费 "
                                        "(docs/sop/rebuild-matrix.json 机读)")
    rb.add_argument("--after", default=None, metavar="KEY",
                    help="变更键 (如 devices_json_pcb) → 打印有序重跑链+同步更新面")

    # ---- fwgen / codegen ----
    fw = sub.add_parser("fwgen", aliases=["codegen"],
                        help="固件/前端参数生成 (M3): types.h + params_gen.js "
                             "(codegen = 本命令别名)")
    fw.add_argument("--truth", default=None, metavar="PATH",
                    help="devices.json 路径 (默认仓库真值, FLOWIO_TRUTH 可覆盖)")
    fw.add_argument("--check", action="store_true",
                    help="只校验不写盘: 重渲染与库内全等 rc=0, 漂移 rc=1")
    fw.add_argument("--out-root", default=None, metavar="DIR",
                    help="输出根目录 (默认仓库根; 预览/测试用)")
    return ap


def main(argv=None) -> int:
    args = _build_parser().parse_args(argv)

    if args.cmd == "truth":
        return _cmd_truth_show(args) if args.truth_sub == "show" \
            else _cmd_truth_check(args)
    if args.cmd == "hw":
        return _cmd_hw(args)
    if args.cmd == "geom":
        return _cmd_geom(args)
    if args.cmd == "flows":
        return _cmd_flows(args)
    if args.cmd == "twin":
        return _cmd_twin_electrical(args)
    if args.cmd == "test":
        return _cmd_test(args)
    if args.cmd == "rebuild":
        return _cmd_rebuild(args)
    if args.cmd in ("fwgen", "codegen"):              # codegen 别名 (argparse
        return _cmd_fwgen(args)                       # 存调用名而非主名)
    return 2                                          # pragma: no cover


if __name__ == "__main__":
    sys.exit(main())
