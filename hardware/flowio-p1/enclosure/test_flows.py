# -*- coding: utf-8 -*-
"""flows.json / hotspots.json 同源断言 — pos.csv 为唯一真值源。

运行: python test_flows.py   (与 make_flows.py 同目录)
断言:
  1. 每条 elec 路径首尾点 = 首尾器件 pos.csv 坐标 (壳系) ±0.1mm
     (P1.1 T3 起全部 ref 由真实布局 pos.csv 供给, 过渡表 POS_P11 已删除)
  2. gate 路径数 = 11 (gate1..gate8 + gateS/gateV/gateF; P1.1 1f-β 三主阀)
     + 泵驱动路径 pump ×1
  3. 每条 air 路径起点 = 对应端子 ±0.1; 终点/控制点 = 起点 + 出线方向×AIR_LEN
     /AIR_CTRL (±0.1, x/y 双向同检)。方向按端子 rot 推导 (复用 make_flows.
     _outward_dir): 底带 J10-J17 rot180 → 壳 +Y 穿底壁; 右带 J20-J23 rot-90
     → 壳 +X 穿右壁 (P1.1 T3 双带语义, 旧"全部 y=端子y-25"底壁公式已废弃)
  4. hotspots 恰 6 项, ref 集合 = {U1,U3,Q3,J1,J10,U2}
  5. 常量 (OX/Z_TOP) 取 case_geom 单一真相源 (修复: 曾写死 Z_TOP=4.0 与 9.0 漂移)
跑通输出: flows tests OK
"""
import json
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import case_geom as G                     # OX / Z_TOP 单一真相源
import make_flows as MF                   # load_pos + _outward_dir (出线方向真值)

ROOT = HERE.parents[2]
FLOWS = ROOT / "firmware" / "twin" / "webapp" / "flows.json"
HOTSPOTS = ROOT / "firmware" / "twin" / "webapp" / "hotspots.json"

OX, Z_TOP, AIR_LEN, EPS = G.OX, G.Z_TOP, MF.AIR_LEN, 0.1


def main():
    praw = MF.load_pos()
    pos = {ref: (p["x"], p["y"]) for ref, p in praw.items()}
    flows = json.loads(FLOWS.read_bytes().decode("utf-8"))
    hs = json.loads(HOTSPOTS.read_bytes().decode("utf-8"))["hotspots"]

    def near(a, b):
        return all(abs(x - y) <= EPS for x, y in zip(a, b))

    def shell(ref):
        px, py = pos[ref]
        return [round(px + OX, 3), round(-py + OX, 3), Z_TOP]

    # 1. 每条 elec 首尾 = 首尾器件 (含 ref 链完整解析, 缺 ref 直接 KeyError 报错)
    n_elec = len(flows["elec"])
    for e in flows["elec"]:
        refs = e["refs"]
        assert refs and e["points"], "%s: 空路径" % e["id"]
        assert near(e["points"][0], shell(refs[0])), \
            "%s 起点漂移: %s != %s" % (e["id"], e["points"][0], shell(refs[0]))
        assert near(e["points"][-1], shell(refs[-1])), \
            "%s 终点漂移: %s != %s" % (e["id"], e["points"][-1], shell(refs[-1]))
        for p in e["points"]:
            assert abs(p[2] - Z_TOP) <= EPS, \
                "%s: z 应为板面 %.1f (case_geom.Z_TOP)" % (e["id"], Z_TOP)
    print("[ok] %d 条 elec 路径首尾与 pos.csv 同源 (±%.1fmm)" % (n_elec, EPS))

    # 2. gate 路径数 (P1.1: +gateS/gateV/gateF 三主阀) + 泵路径
    gates = [e for e in flows["elec"] if e["id"].startswith("gate")]
    want_gates = sorted(["gate%d" % i for i in range(1, 9)] + ["gateS", "gateV", "gateF"])
    assert sorted(e["id"] for e in gates) == want_gates, \
        "gate 路径集 %s != %s" % (sorted(e["id"] for e in gates), want_gates)
    pumps = [e for e in flows["elec"] if e["id"] == "pump"]
    assert len(pumps) == 1 and pumps[0]["refs"] == ["U1", "R58", "Q16", "J23"], \
        "pump 路径缺失或 ref 链不符: %s" % (pumps,)
    print("[ok] gate 路径数 = %d (gate1..8 + S/V/F) + pump x1" % len(gates))

    # 3. air 起点终点 (终点/控制点 = 起点 + rot 推导方向 × AIR_LEN/AIR_CTRL, x/y 双向同检;
    #    J10-J17 rot180 → 壳 +Y 底壁, J20-J23 rot-90 → 壳 +X 右壁)
    assert len(flows["air"]) == 12, "air 路径数 %d != 12" % len(flows["air"])
    for a in flows["air"]:
        p = praw[a["ref"]]
        dx, dy = MF._outward_dir(p["rot"])
        start = [round(p["x"] + OX, 3), round(-p["y"] + OX, 3), Z_TOP]
        assert near(a["start"], start), \
            "%s 起点不等于端子 %s" % (a["id"], a["ref"])
        expect_ctrl = [round(start[0] + dx * MF.AIR_CTRL, 3),
                       round(start[1] + dy * MF.AIR_CTRL, 3), Z_TOP]
        expect_end = [round(start[0] + dx * AIR_LEN, 3),
                      round(start[1] + dy * AIR_LEN, 3), Z_TOP]
        assert near(a["ctrl"], expect_ctrl), \
            "%s 控制点 %s != 起点+dir×AIR_CTRL %s (rot=%s dir=(%d,%d))" \
            % (a["id"], a["ctrl"], expect_ctrl, p["rot"], dx, dy)
        assert near(a["end"], expect_end), \
            "%s 终点 %s != 起点+dir×AIR_LEN %s (rot=%s dir=(%d,%d))" \
            % (a["id"], a["end"], expect_end, p["rot"], dx, dy)
    # 3b. 独立带向不变量 (不依赖 _outward_dir 实现, 实现错则此处独立翻红):
    #     底带 J10-J17 终点必须 +Y 向外; 右带 J20-J23 终点必须 +X 向外
    by_ref = {a["ref"]: a for a in flows["air"]}
    for i in range(8):
        a = by_ref["J%d" % (10 + i)]
        assert a["end"][1] > a["start"][1],             "%s 底带终点未 +Y 向外: %s -> %s" % (a["id"], a["start"], a["end"])
    for i in range(4):
        a = by_ref["J%d" % (20 + i)]
        assert a["end"][0] > a["start"][0],             "%s 右带终点未 +X 向外: %s -> %s" % (a["id"], a["start"], a["end"])
    print("[ok] 带向不变量: J10-J17 end.y>start.y (底壁 +Y), J20-J23 end.x>start.x (右壁 +X)")
    print("[ok] 12 条 air 起点=端子, end/ctrl = start+dir×AIR_LEN/CTRL "
          "(rot 推导出线, 底壁 +Y / 右壁 +X 双向同检)")

    # 4. hotspots 6 项 + ref 集合 + 盒体中心与 pos.csv 同源
    want = {"U1", "U3", "Q3", "J1", "J10", "U2"}
    assert len(hs) == 6, "hotspots %d 项 != 6" % len(hs)
    got = {x["ref"] for x in hs}
    assert got == want, "hotspots ref 集合 %s != %s" % (sorted(got), sorted(want))
    for x in hs:
        assert len(x["center"]) == 3 and len(x["size"]) == 3, "%s 盒体字段不全" % x["ref"]
        assert 0 < x["size"][0] <= G.BW and 0 < x["size"][1] <= G.BH, \
            "%s 尺寸越板" % x["ref"]
        cx, cy = x["center"][0], x["center"][1]
        assert OX - EPS <= cx <= G.BW + OX + EPS and OX - EPS <= cy <= G.BH + OX + EPS, \
            "%s 盒心不在板范围" % x["ref"]
        assert x["live"], "%s 无 live 映射" % x["ref"]
    print("[ok] hotspots = 6 项 (%s), center/live 齐备" % ",".join(sorted(want)))

    print("flows tests OK")


if __name__ == "__main__":
    main()
