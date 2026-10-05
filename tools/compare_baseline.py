# -*- coding: utf-8 -*-
"""compare_baseline.py — 重构对拍器 (基线: docs/mod-baseline/baseline.json @7885c62)。

用途 (spec v2.1 §5 各期验收的统一对拍入口):
  * M0/M2 孪生数值对拍 —— 12 场景 (总电流 i_total_a + 告警集 alarms + 超限标志
    over_limit) 逐值相等 (冻结于基线冻结 commit);
  * M1 产物字节对拍 (--products): 11 生成产物 (尺寸 + sha256 前 12 位) 逐一致
    (uuid 归一化由产物生成侧负责, 本工具只比最终文件);
  * M3 参数对拍 (--params): 三语常量三方对拍 —— devices.json 真值 ↔ C 侧
    types.h (D1=B 生成) ↔ TS/ES 侧 params_gen.js 共有锚点逐值相等
    (生成物漂移细查另有 tools/check_codegen.py --ci 重生成 diff 门)。

用法 (任意 cwd):
  python tools/compare_baseline.py                # 12 场景对拍 (M0/M2 验收门)
  python tools/compare_baseline.py --products     # + 11 产物字节对拍 (M1 验收门)
  python tools/compare_baseline.py --params       # + 三语参数对拍 (M3 验收门)
  python tools/compare_baseline.py --json         # 机器可读输出 (CI/后续期复用)
退出码: 0 = 全等; 1 = 有差异 (CI 守门可直接挂)。
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "docs" / "mod-baseline" / "baseline.json"

sys.path.insert(0, str(ROOT / "firmware" / "twin"))
import electrical_sim as es  # noqa: E402


def load_baseline(path=None):
    src = Path(path) if path else BASELINE
    return json.loads(src.read_text(encoding="utf-8"))


# ══════════ 场景数值对拍 (M0/M2) ══════════
def compare_scenarios(base):
    """12 场景 (i_total_a, alarms, over_limit) 逐值对拍 → (rows, n_ok, n_bad)。"""
    rows = [dict(r) for r in es.run_matrix()]          # 每次全量跑 (无缓存语义)
    got = {r["name"]: (r["i_total_a"], list(r["alarms"]), bool(r["over_limit"]))
           for r in rows}
    want = base.get("scenarios") or {}
    out, n_ok, n_bad = [], 0, 0
    if set(got) != set(want):                          # 场景集本身必须一致
        out.append({"scenario": "<matrix>", "field": "scenario_set",
                    "expected": sorted(want), "got": sorted(got), "ok": False})
        n_bad += 1
    for name in want:                                  # 基线序逐场景逐值
        if name not in got:
            continue
        w_i, w_alarms, w_over = want[name]
        g_i, g_alarms, g_over = got[name]
        ok = (g_i == w_i and g_alarms == w_alarms and g_over == w_over)
        n_ok, n_bad = (n_ok + 1, n_bad) if ok else (n_ok, n_bad + 1)
        out.append({"scenario": name, "expected": [w_i, w_alarms, w_over],
                    "got": [g_i, g_alarms, g_over], "ok": ok})
    return out, n_ok, n_bad


# ══════════ 产物字节对拍 (M1) ══════════
def compare_products(base):
    """11 产物 (字节数 + sha256[:12]) 对拍 → (rows, n_ok, n_bad)。"""
    out, n_ok, n_bad = [], 0, 0
    for rel, (w_size, w_sha) in (base.get("products") or {}).items():
        f = ROOT / rel
        if not f.is_file():
            ok, g_size, g_sha = False, None, None
        else:
            data = f.read_bytes()
            g_size, g_sha = len(data), hashlib.sha256(data).hexdigest()[:12]
            ok = (g_size == w_size and g_sha == w_sha)
        n_ok, n_bad = (n_ok + 1, n_bad) if ok else (n_ok, n_bad + 1)
        out.append({"product": rel, "expected": [w_size, w_sha],
                    "got": [g_size, g_sha], "ok": ok})
    return out, n_ok, n_bad


def _fmt(v):
    return json.dumps(v, ensure_ascii=False)


# ══════════ 三语参数对拍 (M3) ══════════
def compare_params(_base=None):
    """devices.json ↔ types.h ↔ params_gen.js 三方共有锚点逐值对拍 → (rows, n_ok, n_bad)。

    C 侧锚点 = types.h 参数段 #define; JS 侧锚点 = FLOWIO_PARAMS 字段; 真值 =
    flowio 视图推导 (hold_duty_byte 与 C/JS 生成同推导)。rail_v 在 C 侧无对应
    #define (协议层无此常量), 以 "-" 参与两方对拍。
    """
    from flowio import fwgen
    from flowio.core.truth import TruthSource
    from flowio.fwgen.c_gen import hold_duty_byte
    from flowio.truth import drive_policy

    dp = drive_policy(TruthSource().pneumatic_devices)
    types_h = (ROOT / fwgen.TYPES_H_REL).read_text(encoding="utf-8")
    params_js = (ROOT / fwgen.PARAMS_JS_REL).read_text(encoding="utf-8")

    def c_def(name):
        m = re.search(r"^#define\s+%s\s+(\d+)" % name, types_h, re.M)
        return int(m.group(1)) if m else None

    def js_num(key):
        m = re.search(r"%s:\s*(-?\d+(?:\.\d+)?)" % key, params_js)
        return float(m.group(1)) if m else None

    anchors = [
        ("valve_hold_duty_255", float(hold_duty_byte(dp)),
         float(c_def("PN_HOLD_DEFAULT_DUTY")), js_num("hold_duty_255")),
        ("valve_hold_delay_ms", dp.pull_in_ms,
         float(c_def("PN_HOLD_DEFAULT_DELAY_MS")), js_num("hold_delay_ms")),
        ("rail_v (C 侧无此 define)", dp.rail_v, "-", js_num("rail_v")),
    ]
    out, n_ok, n_bad = [], 0, 0
    for name, want, c_val, js_val in anchors:
        ok = (("-" in (c_val, js_val)) or (c_val == want)) and js_val == want
        n_ok, n_bad = (n_ok + 1, n_bad) if ok else (n_ok, n_bad + 1)
        out.append({"anchor": name, "expected": want, "c_types_h": c_val,
                    "js_params_gen": js_val, "ok": ok})
    return out, n_ok, n_bad


def main(argv=None):
    ap = argparse.ArgumentParser(description="重构对拍器 (baseline.json 统一基准)")
    ap.add_argument("--baseline", default=str(BASELINE), help="基线文件路径")
    ap.add_argument("--products", action="store_true",
                    help="追加 M1 产物字节对拍 (11 产物 size+sha)")
    ap.add_argument("--params", action="store_true",
                    help="追加 M3 三语参数对拍 (devices.json↔types.h↔params_gen.js)")
    ap.add_argument("--json", action="store_true", help="机器可读 JSON 输出")
    args = ap.parse_args(argv)

    base = load_baseline(args.baseline)
    sc_rows, sc_ok, sc_bad = compare_scenarios(base)
    pr_rows, pr_ok, pr_bad = ([], 0, 0)
    if args.products:
        pr_rows, pr_ok, pr_bad = compare_products(base)
    pa_rows, pa_ok, pa_bad = ([], 0, 0)
    if args.params:
        pa_rows, pa_ok, pa_bad = compare_params(base)

    if args.json:
        print(json.dumps({
            "baseline_commit": base.get("frozen_at_commit"),
            "scenarios": {"rows": sc_rows, "ok": sc_ok, "bad": sc_bad},
            "products": ({"rows": pr_rows, "ok": pr_ok, "bad": pr_bad}
                         if args.products else None),
            "params": ({"rows": pa_rows, "ok": pa_ok, "bad": pa_bad}
                       if args.params else None),
            "all_ok": (sc_bad == 0 and pr_bad == 0 and pa_bad == 0),
        }, ensure_ascii=False, indent=1))
    else:
        print("对拍基线: %s (frozen @%s)" % (args.baseline, base.get("frozen_at_commit")))
        print("── 场景数值 (i_total_a / alarms / over_limit) %d 项 ──" % len(sc_rows))
        for r in sc_rows:
            mark = "PASS" if r["ok"] else "FAIL"
            print("[%-4s] %-28s want=%s got=%s"
                  % (mark, r["scenario"], _fmt(r["expected"]), _fmt(r["got"])))
        if args.products:
            print("── 产物字节 (size / sha256[:12]) %d 项 ──" % len(pr_rows))
            for r in pr_rows:
                mark = "PASS" if r["ok"] else "FAIL"
                print("[%-4s] %-46s want=%s got=%s"
                      % (mark, r["product"], _fmt(r["expected"]), _fmt(r["got"])))
        if args.params:
            print("── 三语参数 (truth / C types.h / JS params_gen.js) %d 锚点 ──" % len(pa_rows))
            for r in pa_rows:
                mark = "PASS" if r["ok"] else "FAIL"
                print("[%-4s] %-28s truth=%s C=%s JS=%s"
                      % (mark, r["anchor"], r["expected"],
                         r["c_types_h"], r["js_params_gen"]))
        print("── 合计: %d ok / %d bad ──" % (sc_ok + pr_ok + pa_ok, sc_bad + pr_bad + pa_bad))
    return 0 if (sc_bad == 0 and pr_bad == 0 and pa_bad == 0) else 1


if __name__ == "__main__":
    sys.exit(main())
