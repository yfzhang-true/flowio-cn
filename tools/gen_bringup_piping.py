# -*- coding: utf-8 -*-
"""gen_bringup_piping — BRINGUP「模块间连接与管路下料」章节机器生成 (DX 收官, 2026-10-05)。

从 connections.json 真值 + connections_render 渲染折线 (与 webapp/connections_scene.json
同一单源) 提取, 整段替换 docs/bringup-checklist.md 的标记块 (幂等, 可重跑):

    python tools/gen_bringup_piping.py        # 仓库根执行 (或任意 cwd, 路径自定位)

纪律:
  · 禁止手抄数字/手改标记块内内容 —— 真值变更后重跑本脚本再生成;
  · 不改 connections.json / devices.json 真值本体 (只读消费);
  · 下料口径 = scene meta bend_note: 折线段长和 ≤ 下料真值 len_mm, 差值即布管余量;
    采购/下料以 len_mm 为准 (脚本对 16 条管边逐条断言该不等式, 超长即红);
  · WARN 边清单取自 flowio.twin.connections.validate() 现值 (单一校验源, 不重实现);
  · 电气 14 边与 bringup §C 通道表 J 座映射一致性由本脚本断言 (口径冲突检查机械化)。
"""
import datetime
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from flowio.twin import connections_render as CR            # noqa: E402  折线单源 (纯 stdlib)
from flowio.twin.connections import validate                # noqa: E402  WARN/校验单源

DOC = ROOT / "docs" / "bringup-checklist.md"
BEGIN = "<!-- BEGIN GENERATED:bringup-piping (tools/gen_bringup_piping.py; 禁手改, 重跑再生) -->"
END = "<!-- END GENERATED:bringup-piping -->"

# bringup §C 通道表 J 座映射 (口径一致性断言靶; 与 tools/gen_sch.py 真值一致)
C_MAP = {"V1": "J10", "V2": "J11", "V3": "J12", "V4": "J13", "V5": "J14",
         "V6": "J15", "V7": "J16", "V8": "J17", "VS": "J20", "VV": "J21",
         "VF": "J22"}


def _polylen(path):
    """折线段长和 (mm)."""
    return sum(((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2) ** 0.5
               for a, b in zip(path, path[1:]))


def _domain(e):
    """管边气路域 (表分组列)."""
    f, t = e["from"], e["to"]
    if "Main.CH" in f or "Main.CH" in t:
        return "通道管"
    if "Main.M" in f or "Main.M" in t:
        return "测压支路"
    if f.startswith("P1.") or t.startswith("P1."):
        return "泵模块跳管"
    if "PMod" in f or "PMod" in t:
        return "模块间干管"
    return "主阀干管"


def _status(e, warn_edges):
    """状态列: fit_pending / inferred / — (与 spec §6 待实测清单对齐).
    WARN 归属取 validate() 现值映射 (端点级 inferred 也算到边上, 如 VV.N2)."""
    kinds = warn_edges.get((e["from"], e["to"]), {}).get("kinds", set())
    if "fit_pending" in kinds or e.get("fit_pending"):
        return "**fit_pending：到货试装 4/5 取一，ID4 备料**"
    if "inferred" in kinds or e.get("inferred"):
        return "**inferred：待实测**"
    return "—"


def build_section():
    payload = CR.build_render_payload()
    conn = json.loads(CR.CONNECTIONS_JSON.read_text(encoding="utf-8"))
    plen = {(e["from"], e["to"]): _polylen(e["path"])
            for e in payload["edges"] if e["render"] == "tube"}

    tubes = [e for e in conn["pneumatic_edges"] if e.get("tube")]
    assert len(plen) == len(tubes) == 16, "管边数漂移: payload %d / truth %d (期望 16)" \
        % (len(plen), len(tubes))

    # ---- WARN 边 (connections --check 单一校验源; 现值 0 FAIL / 4 WARN) ----
    rep = validate(conn)
    assert not rep["fail"], "真值校验 FAIL: %s" % rep["fail"]
    assert len(rep["warn"]) == 4, "WARN 数漂移: %d (期望 4 = 2 fit_pending + 2 inferred)" \
        % len(rep["warn"])
    warn_edges = {}
    for w in rep["warn"]:
        m = re.search(r"边 (\S+)→([^\s:；;,]+)", w)
        d = warn_edges.setdefault((m.group(1), m.group(2)), {"kinds": set(), "raw": []})
        d["kinds"].add("inferred" if "[inferred]" in w else "fit_pending")
        d["raw"].append(w)

    rows = []
    for i, e in enumerate(tubes, 1):
        tb = e["tube"]
        s = plen[(e["from"], e["to"])]
        margin = tb["len_mm"] - s
        assert margin >= -1e-6, "P2 可行性破: %s→%s 折线 %.1f > 下料 %d" \
            % (e["from"], e["to"], s, tb["len_mm"])
        spec = "ID%g×OD%g" % (tb["id"], tb["od"])
        if "id_to" in tb:
            spec = "ID%g→%g×OD%g 变径" % (tb["id"], tb["id_to"], tb["od"])
        rows.append("| %d | %s | `%s` → `%s` | %s | %d | %.1f | %.1f | %d | %s |"
                    % (i, _domain(e), e["from"], e["to"], spec, tb["len_mm"], s,
                       margin, tb["bend"], _status(e, warn_edges)))

    # ---- 口径一致性: 电气 14 边 J 座映射 vs bringup §C 通道表 ----
    elec = conn["electrical_edges"]
    leads = {e["from"].split(".")[0]: e["to"].split(".")[1]
             for e in elec if e["kind"] == "lead_2p"}
    assert leads == C_MAP, "§C 映射口径冲突: %s" % leads
    cable = next(e for e in elec if e["kind"] == "cable_2p")
    assert cable["to"] == "PMod.cable_2p" and cable["len_mm"] == 150
    n_wire_null = sum(1 for e in elec if e["kind"] == "wire" and e.get("len_mm") is None)
    n_lead = sum(1 for e in elec if e["kind"] == "lead_2p")
    lead_lens = {e["len_mm"] for e in elec if e["kind"] == "lead_2p"}
    n_pn, n_elec, n_me = (len(conn[k]) for k in
                          ("pneumatic_edges", "electrical_edges", "mechanical_edges"))
    assert n_wire_null == 2, "模块内电机引线 null 长度数漂移: %d (期望 2)" % n_wire_null
    assert len(lead_lens) == 1, "阀引线桩深不均一: %s" % lead_lens
    assert (n_pn, n_elec, n_me) == (29, 14, 15), \
        "边计数漂移: %d/%d/%d" % (n_pn, n_elec, n_me)

    # 生成日期取 UTC 日: 对齐项目工作日口径 (本地 UTC+8 已跨零点), 避免时区抖动
    today = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    fp = sorted(k for k, v in warn_edges.items() if "fit_pending" in v["kinds"])
    inf = sorted(k for k, v in warn_edges.items() if "inferred" in v["kinds"])
    assert len(fp) == 2 and len(inf) == 2, "WARN 分型漂移: fp=%s inf=%s" % (fp, inf)

    L = []
    a = L.append
    a(BEGIN)
    a("## I. 模块间连接与管路下料（机器生成 · connections.json 真值）")
    a("")
    a("> **生成**：`python tools/gen_bringup_piping.py` @ %s · 生成于 device-modeling DX 收官 ·" % today)
    a("> 真值源 `hardware/flowio-p1/enclosure/connections.json`（%d 气 + %d 电 + %d 机 = %d 边，只读）·"
      % (n_pn, n_elec, n_me, n_pn + n_elec + n_me))
    a("> 折线几何 = `flowio/twin/connections_render.py` 渲染单源（与 `webapp/connections_scene.json` 同源）·")
    a("> WARN 清单 = `flowio.twin.connections.validate()` 现值（`python -m flowio connections --check`：0 FAIL / 4 WARN）。")
    a("> **下料口径**（scene meta bend_note）：tube.bend=2 为采购下料名义值；渲染折线按最小几何弯折")
    a("> （2~4 点，壁孔过越/障碍让位）—— **折线段长和 ≤ 下料长 len_mm，差值即布管余量；采购/下料以")
    a("> len_mm（真值列）为准**，折线段长和仅为装配态最小路径参考。承插 11 边 + 大气 2 边无下料")
    a("> （器件嘴直插歧管承口 / 开放大气）。本节与 A~H 章无数字口径冲突（生成脚本已断言 §C J 座映射")
    a("> 一致性）；bend 列为下料名义弯数（真值），非渲染折线点数。模块间恰 3 边的缺失后果矩阵与装配")
    a("> 顺序见 [`docs/module-interface-spec.md`](module-interface-spec.md) §4/§5，待实测项关闭通道见其 §6。")
    a("")
    a("### I.1 管路下料表（16 条 tube 边 = 气路全量有几何边，序 = connections.json 真值序）")
    a("")
    a("| # | 域 | 管边 from→to | 规格 | 下料真值 len_mm | 折线段长和 | 余量 | 弯 | 状态 |")
    a("|---|----|--------------|------|----------------|-----------|------|----|------|")
    L.extend(rows)
    a("")
    a("### I.2 WARN 边清单（恰 4 条 = 2 fit_pending + 2 inferred，与 spec §6 待实测清单对齐；"
      "内容列 = validate() 原文）")
    a("")
    a("| WARN 类 | 边 | validate() 原文 | BRINGUP 关闭动作 |")
    a("|---------|----|----------------|------------------|")
    close_fit = "**到货试装 4/5 取一，ID4 备料**；勿强行扩口，定档回填 registry §6 / connections.json"
    close_map = {
        ("Main.V_wall", "VV.N2"): "卡尺实测校正（devices.json geom3d VV.N2 note；spec §6 行 1）",
        ("VV.mount_hole", "Main.valve_bracket"):
            "商家答复（procurement H4 / 问询 1/3）→ 支架图纸（spec §6 行 2）",
    }
    for edge, d in warn_edges.items():
        kind = "inferred" if "inferred" in d["kinds"] else "fit_pending"
        close = close_fit if kind == "fit_pending" else close_map[edge]
        a("| %s | `%s`→`%s` | %s | %s |" % (kind, edge[0], edge[1], "；".join(d["raw"]), close))
    a("")
    a("### I.3 电气线束（connections.json electrical_edges %d 边，桩深口径机器提取）" % n_elec)
    a("")
    a("- 阀引线 lead_2p ×%d：各 **%gmm** 2P 白壳→XH 座（§C 通道表 J 座映射一致性已由生成脚本断言："
      % (n_lead, sorted(lead_lens)[0]))
    a("  V1-V8→J10-J17 / VS→J20 / VV→J21 / VF→J22）；")
    a("- 泵电机电缆 cable_2p ×1：**%gmm**（%s ↔ %s，XH2.54-2P，spec §4 模块间 3 边之一）；"
      % (cable["len_mm"], cable["from"], cable["to"]))
    a("- 模块内电机引线 wire ×%d：len_mm=null **待实测**（D2-A 视觉桩深度，泵端焊片正/负极以图纸标注为准）。"
      % n_wire_null)
    a(END)
    return "\n".join(L)


def main():
    text = DOC.read_text(encoding="utf-8")
    body = build_section()          # 以 BEGIN 行开头、以 END 行结尾 (无尾换行)
    assert body.startswith(BEGIN) and body.endswith(END)
    if BEGIN in text:
        assert text.count(BEGIN) == 1 and text.count(END) == 1, "标记块重复"
        pre = text.split(BEGIN, 1)[0]
        post_rest = text.split(END, 1)[1]
        if post_rest.startswith("\r\n"):
            post_rest = post_rest[2:]
        elif post_rest.startswith("\n"):
            post_rest = post_rest[1:]
        new = pre + body + "\n" + post_rest
    else:
        anchor = "**收尾**："
        assert anchor in text, "插入锚点缺失 (收尾段)"
        new = text.replace(anchor, body + "\n\n" + anchor, 1)
    DOC.write_bytes(new.encode("utf-8"))
    print("[gen] %s 更新完成 (标记块 %d 处, %d 字节)"
          % (DOC.name, new.count(BEGIN), len(new.encode("utf-8"))))


if __name__ == "__main__":
    main()
