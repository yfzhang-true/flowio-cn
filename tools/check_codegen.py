# -*- coding: utf-8 -*-
"""tools/check_codegen.py — M3 三语 codegen 对拍门 (D1=B 验收, spec v2.1 §3.5)。

三查 (每次运行全做, 对象 = 库内生成物):
  a) 模板段逐字节 —— 生成版 types.h 的拓扑常量块/阀保持溯源注释/状态字+枚举尾段
     与手写备份 (docs/mod-baseline/types.h.handwritten.bak @49af3bf) 逐字节一致;
  b) #define 值等价 —— 手写版全部 #define 在生成版同名同值 (值零改动, 无增无删);
  c) 真值映射一致 —— 参数段值 = devices.json 视图推导; params_gen.js 锚点
     (hold_duty_255/hold_delay_ms/rail_v) 与 C 侧/真值三方对拍。
  +) 溯源完整性 —— 注释行数 ≥ 手写版, 事故出处锚点在场。

CI 门 (--ci): 真值重渲染两生成物 → 与库内逐字节 diff (diff --exit-code 语义);
手编生成物立即红。负测试: 手改 types.h 一处值 → 本脚本红 → 还原 → 绿。

用法:
  python tools/check_codegen.py          # 三查 + 溯源完整性
  python tools/check_codegen.py --ci     # + 重生成 diff 门 (CI 挂钩形态)
退出码: 0 = 全绿; 1 = 有红。
"""
import argparse
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from flowio import fwgen                                    # noqa: E402
from flowio.core.truth import TruthSource                   # noqa: E402
from flowio.fwgen import templates as T                     # noqa: E402
from flowio.fwgen.c_gen import hold_duty_byte               # noqa: E402
from flowio.truth import drive_policy                       # noqa: E402

HANDWRITTEN_BAK = ROOT / "docs" / "mod-baseline" / "types.h.handwritten.bak"
DEFINE_RE = re.compile(r"^#define\s+(\w+)\s+(.+?)\s*(?:/\*.*)?$")
PROVENANCE_ANCHORS = ("170/~500ms", "已对齐", "T7 2026-10-03 同步")


def _defines(text):
    """#define NAME VALUE 表 (行内注释剥离, 值空白归零 → 稳定比较)。"""
    out = {}
    for line in text.splitlines():
        m = DEFINE_RE.match(line)
        if m:
            out[m.group(1)] = re.sub(r"\s+", "", m.group(2))
    return out


def _region(text, start, end=None):
    """行级原文切片: 含 start 的行 → 含 end 的行 (end=None → 文件尾)。"""
    lines = text.splitlines(keepends=True)
    s = next(i for i, ln in enumerate(lines) if start in ln)
    if end is None:
        return "".join(lines[s:])
    e = next(i for i, ln in enumerate(lines[s:], s) if end in ln)
    return "".join(lines[s:e + 1])


def _comment_lines(text):
    return sum(1 for ln in text.splitlines()
               if ln.lstrip().startswith(("/*", "*", "//")))


# ══════════ a) 模板段逐字节 ══════════
def check_template_regions(gen_text, bak_text):
    rows = []
    for name, s, e in (("拓扑常量块", T.TOPOLOGY_START, T.TOPOLOGY_END),
                       ("阀保持溯源注释", T.HOLD_COMMENT_START, T.HOLD_COMMENT_END),
                       ("状态字+枚举尾段", T.STATUS_START, None)):
        got, want = _region(gen_text, s, e), _region(bak_text, s, e)
        rows.append(("a.模板段逐字节:" + name, got == want, len(got), len(want)))
    return rows


# ══════════ b) #define 值等价 ══════════
def check_defines(gen_text, bak_text):
    got, want = _defines(gen_text), _defines(bak_text)
    rows = [("b.#define 名集全等", set(got) == set(want),
             sorted(set(want)), sorted(set(got)))]
    for k in sorted(want):
        rows.append(("b.#define 值:" + k, got.get(k) == want[k], want[k], got.get(k)))
    return rows


# ══════════ c) 真值映射三方对拍 ══════════
def check_truth_mapping(gen_types, gen_js, truth):
    pn = truth.pneumatic_devices
    dp = drive_policy(pn)
    exp_duty, exp_ms = str(hold_duty_byte(dp)), str(int(dp.pull_in_ms))
    d = _defines(gen_types)
    rows = [
        ("c.真值→C: PN_HOLD_DEFAULT_DUTY", d.get("PN_HOLD_DEFAULT_DUTY") == exp_duty,
         exp_duty, d.get("PN_HOLD_DEFAULT_DUTY")),
        ("c.真值→C: PN_HOLD_DEFAULT_DELAY_MS", d.get("PN_HOLD_DEFAULT_DELAY_MS") == exp_ms,
         exp_ms, d.get("PN_HOLD_DEFAULT_DELAY_MS")),
        ("c.真值→JS: hold_duty_255",
         _js_int(gen_js, "hold_duty_255") == hold_duty_byte(dp),
         hold_duty_byte(dp), _js_int(gen_js, "hold_duty_255")),
        ("c.真值→JS: hold_delay_ms",
         _js_int(gen_js, "hold_delay_ms") == int(dp.pull_in_ms),
         int(dp.pull_in_ms), _js_int(gen_js, "hold_delay_ms")),
        ("c.真值→JS: rail_v",
         _js_float(gen_js, "rail_v") == dp.rail_v, dp.rail_v, _js_float(gen_js, "rail_v")),
    ]
    return rows


def _js_int(js, key):
    m = re.search(r"%s:\s*(-?\d+)" % key, js)
    return int(m.group(1)) if m else None


def _js_float(js, key):
    m = re.search(r"%s:\s*(-?\d+(?:\.\d+)?)" % key, js)
    return float(m.group(1)) if m else None


# ══════════ d) 溯源完整性 ══════════
def check_provenance(gen_text, bak_text):
    rows = [("d.注释行数 ≥ 手写版", _comment_lines(gen_text) >= _comment_lines(bak_text),
             _comment_lines(bak_text), _comment_lines(gen_text))]
    for a in PROVENANCE_ANCHORS:
        rows.append(("d.事故锚点在场:" + a, a in gen_text, True, a in gen_text))
    return rows


# ══════════ --ci: 重生成 diff 门 ══════════
def check_ci(truth):
    """真值重渲染 → 临时区 → 与库内逐字节比对 (diff --exit-code 语义)。"""
    rows, tmp = [], tempfile.mkdtemp(prefix="fwgen_ci_")
    try:
        for rel, text in sorted(fwgen.render_all(truth).items()):
            Path(tmp, Path(rel).name).write_text(text, encoding="utf-8", newline="\n")
            repo = ROOT / rel
            got = repo.read_bytes() if repo.is_file() else None
            want = text.encode("utf-8")
            rows.append(("ci.重生成逐字节:" + rel, got == want, len(want),
                         len(got) if got is not None else "缺失"))
    finally:
        for f in Path(tmp).glob("*"):
            f.unlink()
        Path(tmp).rmdir()
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description="M3 三语 codegen 对拍门 (D1=B)")
    ap.add_argument("--ci", action="store_true",
                    help="追加重生成 diff 门 (手编生成物即红; CI 挂钩用)")
    ap.add_argument("--quiet", action="store_true", help="只输出红项与摘要")
    args = ap.parse_args(argv)

    truth = TruthSource()
    bak_text = HANDWRITTEN_BAK.read_text(encoding="utf-8")
    gen_types = (ROOT / fwgen.TYPES_H_REL).read_text(encoding="utf-8")
    gen_js = (ROOT / fwgen.PARAMS_JS_REL).read_text(encoding="utf-8")

    rows = []
    rows += check_template_regions(gen_types, bak_text)
    rows += check_defines(gen_types, bak_text)
    rows += check_truth_mapping(gen_types, gen_js, truth)
    rows += check_provenance(gen_types, bak_text)
    if args.ci:
        rows += check_ci(truth)

    n_bad = 0
    for name, ok, want, got in rows:
        if not ok or not args.quiet:
            print("[%-4s] %-58s want=%s got=%s" % ("PASS" if ok else "FAIL", name, want, got))
        n_bad += 0 if ok else 1
    print("── check_codegen 合计: %d ok / %d bad (模式: %s) ──"
          % (len(rows) - n_bad, n_bad, "--ci" if args.ci else "三查"))
    return 0 if n_bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
