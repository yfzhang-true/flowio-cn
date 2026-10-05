# -*- coding: utf-8 -*-
"""flowio.fwgen — 固件域参数 codegen (M3, spec v2.1 §3.5 三语生成)。

devices.json 单一真值 → 两介质落盘 (第三语 = python 直接 import TruthSource,
无需生成物):
  * firmware/components/pn_core/include/pn_core/types.h  (C, D1=B 全文件生成)
  * firmware/twin/webapp/js/params_gen.js                (TS/ES module)

用法 (M3 最小 CLI):
  python -m flowio fwgen            # 写盘两生成物
  python -m flowio fwgen --check    # 只校验 (漂移 rc=1) —— CI 门语义
守门: tools/check_codegen.py (语义等价三查 + --ci 重生成 diff)。
"""
from __future__ import annotations

from pathlib import Path

from flowio.core.truth import TruthSource
from flowio.fwgen.c_gen import gen_types_h
from flowio.fwgen.ts_gen import gen_params_js

ROOT = Path(__file__).resolve().parents[2]

TYPES_H_REL = "firmware/components/pn_core/include/pn_core/types.h"
PARAMS_JS_REL = "firmware/twin/webapp/js/params_gen.js"


def render_all(truth: TruthSource | None = None) -> dict:
    """真值 → {相对路径: 文本} 两生成物 (纯函数, 不落盘)。"""
    truth = truth if truth is not None else TruthSource()
    return {
        TYPES_H_REL: gen_types_h(truth),
        PARAMS_JS_REL: gen_params_js(truth),
    }


def write_all(truth: TruthSource | None = None, root: Path | None = None) -> list:
    """渲染并写盘 (原子覆盖), 返回写入的绝对路径列表。"""
    root = Path(root) if root is not None else ROOT
    written = []
    for rel, text in sorted(render_all(truth).items()):
        out = root / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8", newline="\n")
        written.append(out)
    return written


def check_artifacts(root: Path | None = None,
                    truth: TruthSource | None = None) -> dict:
    """库内生成物 vs 重渲染 → {相对路径: 是否全等} (漂移即 False)。"""
    root = Path(root) if root is not None else ROOT
    out = {}
    for rel, text in sorted(render_all(truth).items()):
        f = root / rel
        out[rel] = f.is_file() and f.read_text(encoding="utf-8") == text
    return out
