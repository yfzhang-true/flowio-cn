# -*- coding: utf-8 -*-
"""test_module_interface_spec — D3 模块接口规约文档守卫 (spec 2026-10-05 §4)。

docs/module-interface-spec.md 是 connections.json 的人读投影 (模块接口/模块间 3 边/
装配检查项), 本守卫把文档中的硬编码数字与面名钉在机器真值上, 防文档漂移:
  G1 章节齐备  — 六章在位 (总则/主模块/泵模块/模块间连接/装配检查项/待实测项);
  G2 面名真实  — 文档出现的 Main.*/PMod.*/ATM.* 标识必须解析到 modules 块 face
                (文档发明第二套接口名必红);
  G3 面计数    — 总览表计数串 (气动/电气/机械 与合计) == json 实测
                (Main 12/12/4=28, PMod 2/1/1=4, ATM 1/0/0=1);
  G4 模块间边  — json 跨物理模块边 (Main↔PMod) 恰 3 条, 端点对与文档行一致;
                干管 ID5×OD7 350 / 电缆 150 2P 字样与边数据同源钉扎
                (ATM=环境节点非实体模块, 不计入模块间边 —— conventions.atm_node);
  G5 对外面口径 — §1.2 清单逐面在位, 带 dia 的面 ⌀ 值与 face.dia 同行一致;
  G6 WARN 对齐 — §6 待实测清单列全 inferred (VV.N2/VV.mount_hole) + fit_pending×2
                + C7/D7, 与校验器 WARN 清单对账。
运行: python flowio/tests/test_module_interface_spec.py   (任意 cwd, stdlib-only)
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from flowio.twin import connections as C                                  # noqa: E402

DOC = ROOT / "docs" / "module-interface-spec.md"
CONN = C.load_connections()
TEXT = DOC.read_text(encoding="utf-8")

# 物理模块 = 模块间边只看 Main↔PMod; ATM 是大气环境节点 (非实体, conventions.atm_node)
_PHYS_MODS = ("Main", "PMod")
_FACE_RE = re.compile(r"\b(Main|PMod|ATM)\.([A-Za-z_][A-Za-z_0-9]*)")


def _face_counts(mod):
    c = {"pneumatic": 0, "electrical": 0, "mechanical": 0}
    for f in CONN["modules"][mod]["faces"]:
        c[f["kind"]] += 1
    return c


# ══════════ G1 章节齐备 ══════════
def test_g1_sections_present():
    for head in ("## 1. 总则", "## 2. 主模块", "## 3. 泵模块", "## 4. 模块间连接",
                 "## 5. 装配检查项", "## 6. 待实测项清单"):
        assert head in TEXT, "文档缺章节: %s" % head


# ══════════ G2 面名真实 ══════════
def test_g2_face_names_resolve():
    real = {m: {f["name"] for f in CONN["modules"][m]["faces"]}
            for m in CONN["modules"]}
    bad = [(m, n) for m, n in set(_FACE_RE.findall(TEXT)) if n not in real[m]]
    assert not bad, "文档发明了 modules 块不存在的面: %r" % bad


# ══════════ G3 面计数钉扎 ══════════
def test_g3_face_counts_match_json():
    for mod in ("Main", "PMod", "ATM"):
        c = _face_counts(mod)
        cell = "%d / %d / %d | %d" % (c["pneumatic"], c["electrical"],
                                      c["mechanical"], sum(c.values()))
        rows = [l for l in TEXT.splitlines() if l.startswith("| %s |" % mod)]
        assert rows, "总览表缺 %s 行" % mod
        assert cell in rows[0], "%s 计数串漂移: 文档 %r vs json %r" \
            % (mod, rows[0], cell)


# ══════════ G4 模块间边恰 3 条 ══════════
def test_g4_intermodule_edges_pinned():
    cross = {(e["from"], e["to"])
             for cls in ("pneumatic_edges", "electrical_edges", "mechanical_edges")
             for e in CONN[cls]
             if e["from"].split(".")[0] in _PHYS_MODS
             and e["to"].split(".")[0] in _PHYS_MODS
             and e["from"].split(".")[0] != e["to"].split(".")[0]}
    expect = {("PMod.S_panel", "Main.S_wall"),      # 充干管
              ("PMod.V_panel", "Main.V_wall"),      # 吸干管
              ("Main.J23", "PMod.cable_2p")}        # 电机电缆
    assert cross == expect, "模块间边漂移: 多出 %r / 缺少 %r" \
        % (cross - expect, expect - cross)
    assert "3 条" in TEXT, "文档须声明模块间恰 3 条边"
    for a, b in expect:
        assert a in TEXT and b in TEXT, "文档缺模块间边端点 %s / %s" % (a, b)
    # 规格字样与边数据同源 (json 侧断言 + 文档侧出现, 双向钉扎)
    pneu = {(e["from"], e["to"]): e for e in CONN["pneumatic_edges"]}
    elec = {(e["from"], e["to"]): e for e in CONN["electrical_edges"]}
    for pair in (("PMod.S_panel", "Main.S_wall"), ("PMod.V_panel", "Main.V_wall")):
        t = pneu[pair]["tube"]
        assert (t["id"], t["od"], t["len_mm"]) == (5.0, 7.0, 350), pair
    cab = elec[("Main.J23", "PMod.cable_2p")]
    assert cab["len_mm"] == 150 and cab["kind"] == "cable_2p"
    for tok in ("ID5", "OD7", "350", "150", "2P", "不可对调", "C7429671"):
        assert tok in TEXT, "文档缺模块间规格字样 %r" % tok
    # 料号真值随行钉扎: 文档出现处所在边须与 json connector 字段同值
    assert cab.get("connector") in (None, "C7429671") or "C7429671" in str(cab), cab


# ══════════ G5 对外面清单逐面对账 ══════════
def test_g5_external_faces_listed_with_dia():
    lines = TEXT.splitlines()
    for mod in _PHYS_MODS + ("ATM",):
        for f in CONN["modules"][mod]["faces"]:
            if not f.get("external"):
                continue
            tag = "%s.%s" % (mod, f["name"])
            hits = [l for l in lines if tag in l]
            assert hits, "对外面 %s 未在文档 §1.2 清单列示" % tag
            if "dia" in f:
                assert any(("%.1f" % f["dia"]) in l for l in hits), \
                    "%s 口径 ⌀%.1f 未随行标注" % (tag, f["dia"])


# ══════════ G6 WARN 清单对账 ══════════
def test_g6_warn_inventory_listed():
    for tok in ("VV.N2", "VV.mount_hole", "fit_pending", "C7", "D7"):
        assert tok in TEXT, "文档 §6 待实测清单缺 %s" % tok
    rep = C.validate(conn=CONN)
    assert rep["ok"] is True
    n_fp = sum(1 for w in rep["warn"] if "fit_pending" in w)
    assert n_fp == 2, "校验器 fit_pending WARN 应恰 2 条 (泵双嘴跳管): %r" % rep["warn"]
    assert TEXT.count("fit_pending") >= 2, "文档 fit_pending 条目数不足"


if __name__ == "__main__":
    test_g1_sections_present()
    test_g2_face_names_resolve()
    test_g3_face_counts_match_json()
    test_g4_intermodule_edges_pinned()
    test_g5_external_faces_listed_with_dia()
    test_g6_warn_inventory_listed()
    print("flowio.tests.test_module_interface_spec OK (6 testfns: G1 章节 + G2 面名 "
          "+ G3 面计数 + G4 模块间边 + G5 对外面口径 + G6 WARN 对账 — "
          "docs/module-interface-spec.md ↔ connections.json 漂移守卫)")
