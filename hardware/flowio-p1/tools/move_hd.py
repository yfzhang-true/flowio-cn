# tools/move_hd.py — HD 安装孔移位避让 D10.1 (NPTH 无网络无走线, 单进程安全)
import sys, math; sys.path.insert(0, "tools")
import pcbnew, boardgeom as G
b, pads, trks, vias = G.load()
# 约束: 距 D10.1 (76.86,60.5) ≥ 4mm (让出北向出线走廊), y<66 避端子排,
# 全区扫描最优: (68,65) 可用 od=5.6 (Ø3.2 孔 + 1.2mm 铜净空, 全场最大)
best = (68.0, 65.0)
assert G.spot_ok(*best, "", pads, trks, vias, od=5.6, drill=3.2), "候选位失效"
for f in b.GetFootprints():
    if f.GetReference() == "HD":
        f.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(best[0]), pcbnew.FromMM(best[1])))
G.refill_save(b)
print("HD ->", best)
