# tools/fix_d10.py — D10.1 (+5V) 全净空重连: 短走线+过孔落 In2 +5V 底带
import sys; sys.path.insert(0, "tools")
import pcbnew, boardgeom as G
b, pads, trks, vias = G.load()
d10 = next(p for p in pads if p["ref"] == "D10.1")
spot = G.find_spot(d10["x"], d10["y"], "+5V", pads, trks, vias, anchor=(d10["x"], d10["y"]), rmax=3.0, w=0.4, od=0.9, drill=0.45)
assert spot, "D10 无落点"
assert 53.0 <= spot[1] <= 74.5, f"落点不在5V底带: {spot}"
path = G.plan_route((d10["x"], d10["y"]), spot, "+5V", 0.4, pads, trks, vias)
assert path, "路由规划失败"
G.add_via(b, spot[0], spot[1], "+5V", od=0.9, drill=0.45)
print("segments:", G.add_route(b, path, pcbnew.F_Cu, "+5V", 0.4), "path:", path)
G.refill_save(b)
print(f"D10 +5V via @ {spot}")
