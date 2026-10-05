# -*- coding: utf-8 -*-
"""test_fwgen — flowio M3 三语参数 codegen TDD 测试 (spec v2.1 §3.5, D1=B)。

红/绿纪律: 本文件先行 (红 = flowio.fwgen 未实现时 import 即败), 实现后全绿。
运行: python flowio/tests/test_fwgen.py   (任意 cwd, stdlib-only)

覆盖:
  1. gen_types_h  — D1=B 语义等价三件套:
     a) 模板段 (拓扑常量块/状态字+枚举尾段/阀保持溯源注释块) 与手写备份逐字节一致;
     b) #define 名集与值域与手写版相等 (值零改动);
     c) 真值映射段 (PN_HOLD_DEFAULT_DUTY/DELAY_MS) 值 = devices.json 视图推导;
  2. 溯源完整性 — 注释行数 ≥ 手写版; 事故出处锚点 ("170/~500ms"/"已对齐") 在场;
  3. gen_params_js — ES module 形态 + hold_duty_255 与 C 侧同推导同值 (三方对拍);
  4. fail-loud — 真值缺 drive_policy → TruthError (禁静默兜底);
  5. CLI 入口 — python -m flowio fwgen 可执行 (--help rc=0);
  6. 库内生成物与重生成一致 (生成落地后的常绿锚)。
"""
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from flowio import TruthError, TruthSource                       # noqa: E402

# 红: flowio.fwgen 未实现时, 下行 import 即 ModuleNotFoundError (TDD 红形态)
from flowio.fwgen import (PARAMS_JS_REL, TYPES_H_REL,            # noqa: E402
                          gen_params_js, gen_types_h, render_all)
from flowio.fwgen.c_gen import hold_duty_byte                     # noqa: E402
from flowio.truth import drive_policy                             # noqa: E402

TRUTH = TruthSource()
HANDWRITTEN_BAK = ROOT / "docs" / "mod-baseline" / "types.h.handwritten.bak"
KEY_HOLD_DUTY = "pneumatic_devices._meta.drive_policy.valve.full_open_hold"
KEY_HOLD_DELAY = "pneumatic_devices._meta.drive_policy.valve.pull_in"


# ---- 检查工具 (与 tools/check_codegen.py 同语义的最小内联版) -------------------
DEFINE_RE = re.compile(r"^#define\s+(\w+)\s+(.+?)\s*(?:/\*.*)?$")


def _defines(text):
    """#define NAME VALUE 表 (值 = 行内注释前部分, 空白归零后比较)。"""
    out = {}
    for line in text.splitlines():
        m = DEFINE_RE.match(line)
        if m:
            out[m.group(1)] = re.sub(r"\s+", "", m.group(2))
    return out


def _region(text, start, end=None):
    """行级切片: 从含 start 的行到含 end 的行 (end=None → 文件尾), 逐行原文。"""
    lines = text.splitlines(keepends=True)
    s = next(i for i, ln in enumerate(lines) if start in ln)
    if end is None:
        return "".join(lines[s:])
    e = next(i for i, ln in enumerate(lines[s:], s) if end in ln)
    return "".join(lines[s:e + 1])


def _comment_lines(text):
    return sum(1 for ln in text.splitlines()
               if ln.lstrip().startswith(("/*", "*", "//")))


# ══════════ 1. gen_types_h: D1=B 语义等价 ══════════
def test_gen_types_h_banner_and_shape():
    """生成形态: DO NOT EDIT 头 + #pragma once + 手写版全部段落骨架在场。"""
    t = gen_types_h(TRUTH)
    assert "DO NOT EDIT" in "\n".join(t.splitlines()[:8]), "文件头须含 DO NOT EDIT 生成告示"
    assert "#pragma once" in t
    for kw in ("pn_err_t", "pn_config_t", "pn_valve_t", "pn_cl_status_t",
               "pn_event_t", "PN_SW_ERROR", "extern \"C\""):
        assert kw in t, kw


def test_gen_types_h_template_regions_byte_identical():
    """a) 模板段三区 (拓扑常量/阀保持溯源注释/状态字+枚举尾段) 与手写备份逐字节一致。"""
    got, bak = gen_types_h(TRUTH), HANDWRITTEN_BAK.read_text(encoding="utf-8")
    regions = [
        ("拓扑常量块", "/* ---- 常量 ---- */", "#define PN_SENSOR_COUNT   2"),
        ("阀保持溯源注释", "/* 阀保持电压节能", "已对齐。 */"),
        ("状态字+枚举尾段", "/* ---- 32 位状态字", None),
    ]
    for name, s, e in regions:
        assert _region(got, s, e) == _region(bak, s, e), "模板段 [%s] 须逐字节一致" % name


def test_gen_types_h_define_set_and_values_unchanged():
    """b) #define 名集与值与手写版全等 (值零改动, 无增无删)。"""
    got, bak = _defines(gen_types_h(TRUTH)), _defines(
        HANDWRITTEN_BAK.read_text(encoding="utf-8"))
    assert set(got) == set(bak), "名集差异: +%s -%s" % (
        sorted(set(got) - set(bak)), sorted(set(bak) - set(got)))
    for k in bak:
        assert got[k] == bak[k], "%s: 手写=%s 生成=%s (值零改动被破坏)" % (k, bak[k], got[k])


def test_gen_types_h_truth_mapping():
    """c) 真值映射段: 230/100 由 devices.json 视图推导, 且注释含 registry 键路径。"""
    t = gen_types_h(TRUTH)
    dp = drive_policy(TRUTH.pneumatic_devices)
    assert hold_duty_byte(dp) == 230          # 255×90% 四舍五入 (90.2% → 4.51V@5V 轨)
    assert int(dp.pull_in_ms) == 100
    got = _defines(t)
    assert got["PN_HOLD_DEFAULT_DUTY"] == str(hold_duty_byte(dp))
    assert got["PN_HOLD_DEFAULT_DELAY_MS"] == str(int(dp.pull_in_ms))
    assert KEY_HOLD_DUTY in t and KEY_HOLD_DELAY in t, "参数段注释须含出处 registry 键路径"


def test_gen_types_h_deterministic():
    assert gen_types_h(TRUTH) == gen_types_h(TRUTH)


# ══════════ 2. 溯源注释完整性 (禁丢事故出处) ══════════
def test_provenance_comments_not_lost():
    """注释行数 ≥ 手写版; -58→230 事故叙事锚点逐条在场。"""
    got, bak = gen_types_h(TRUTH), HANDWRITTEN_BAK.read_text(encoding="utf-8")
    assert _comment_lines(got) >= _comment_lines(bak), (
        "注释行 %d < 手写 %d (溯源注释丢失)" % (_comment_lines(got), _comment_lines(bak)))
    for anchor in ("170/~500ms", "已对齐", "T7 2026-10-03 同步",
                   "pneumatic_devices._meta.drive_policy.valve"):
        assert anchor in got, "事故/溯源锚点丢失: %s" % anchor


# ══════════ 3. gen_params_js: TS/ES module 侧 ══════════
def test_gen_params_js_shape_and_truth_values():
    """ES module 导出 FLOWIO_PARAMS; 锚点值与真值/派生一致; DO NOT EDIT 头。"""
    j = gen_params_js(TRUTH)
    dp = drive_policy(TRUTH.pneumatic_devices)
    assert "export const FLOWIO_PARAMS" in j
    assert "DO NOT EDIT" in j
    assert "Object.freeze" in j, "导出须冻结 (只读参数快照)"
    assert re.search(r"rail_v:\s*5\.0\b", j), "rail_v 须为真值 5.0"
    hold = int(re.search(r"hold_duty_255:\s*(\d+)", j).group(1))
    delay = int(re.search(r"hold_delay_ms:\s*(\d+)", j).group(1))
    assert hold == hold_duty_byte(dp) == 230       # 与 C 侧 PN_HOLD_DEFAULT_DUTY 同值
    assert delay == int(dp.pull_in_ms) == 100
    assert re.search(r"p_min_kpa:\s*-60\.0\b", j), "泵真空死头须为 registry -60"
    assert re.search(r"p_max_kpa:\s*120\.0\b", j), "泵正压死头须为 registry 120"


def test_gen_params_js_deterministic():
    assert gen_params_js(TRUTH) == gen_params_js(TRUTH)


# ══════════ 4. fail-loud ══════════
def test_broken_truth_raises_truth_error():
    """真值缺 drive_policy (schema 或视图层) → TruthError, 禁静默兜底。"""
    doc = json.loads((ROOT / TRUTH.path.relative_to(ROOT)).read_text(encoding="utf-8"))
    del doc["pneumatic_devices"]["_meta"]["drive_policy"]
    with tempfile.TemporaryDirectory() as td:
        bad = Path(td) / "devices.json"
        bad.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
        bad_truth = TruthSource(bad)
        for fn in (gen_types_h, gen_params_js):
            try:
                fn(bad_truth)
            except TruthError:
                pass
            else:
                raise AssertionError("%s: 坏真值应抛 TruthError" % fn.__name__)


# ══════════ 5. CLI 入口 ══════════
def test_cli_module_entry():
    """python -m flowio fwgen 可执行 (无参 usage 红 / --help 绿)。"""
    r = subprocess.run([sys.executable, "-m", "flowio", "fwgen", "--help"],
                       capture_output=True, text=True, cwd=str(ROOT))
    assert r.returncode == 0, r.stderr
    assert "fwgen" in r.stdout
    r2 = subprocess.run([sys.executable, "-m", "flowio"], capture_output=True,
                        text=True, cwd=str(ROOT))
    assert r2.returncode != 0


# ══════════ 6. 库内生成物一致 (生成落地后常绿) ══════════
def test_committed_artifacts_in_sync():
    """库内 types.h/params_gen.js 与重渲染全等 (check_codegen --ci 同语义)。"""
    rendered = render_all(TRUTH)
    assert set(rendered) == {TYPES_H_REL, PARAMS_JS_REL}
    for rel, want in rendered.items():
        have = (ROOT / rel).read_text(encoding="utf-8")
        assert have == want, "%s 与重生成不一致 (手编生成物?)" % rel


# ══════════ runner ══════════
def main():
    tests = [v for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
    n_ok = 0
    for t in tests:
        try:
            t()
            print("  PASS %s" % t.__name__)
            n_ok += 1
        except AssertionError as e:
            print("  FAIL %s: %s" % (t.__name__, e))
        except Exception as e:                                  # noqa: BLE001
            print("  ERROR %s: %s: %s" % (t.__name__, type(e).__name__, e))
    n = len(tests)
    print("%s test_fwgen %d/%d" % ("PASS" if n_ok == n else "FAIL", n_ok, n))
    return 0 if n_ok == n else 1


if __name__ == "__main__":
    sys.exit(main())
