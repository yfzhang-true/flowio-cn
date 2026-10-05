# -*- coding: utf-8 -*-
"""export_webapp_meshes — devices3d 精确器件 → 孪生 webapp STL 资产 批导出入口 (D4)。

运行: E:/FreeCAD/bin/python.exe flowio/twin/devices3d/export_webapp_meshes.py
等效: E:/FreeCAD/bin/python.exe flowio/geom/make_meshes.py (同一管线, 本脚本是
devices3d 域的语义入口 —— 网格化/装配/写盘单一实现全在 make_meshes, 禁第二份)。

产物 (幂等, 重跑覆盖且逐字节稳定):
  firmware/twin/meshes/{valves,pump,parts_f}.stl   devices3d 精确模型 ( datasheet 直推)
  firmware/twin/meshes/assembly.json               10 件双体清单 (tubes 件 kind=connections)
  firmware/twin/webapp/connections_scene.json      connections.json → 渲染折线 (D4-A/D2-A)
  firmware/twin/webapp/connections.json            连接图谱真值原文副本 (点击高亮索引)
  (case/manifold/brackets/tubes 等结构件沿用既有产物, 见 make_meshes)

器件装配位置数据源 (逐器件, 与 connections_render 同一单源):
  阀阵 11 只   case_geom.valve_grid() 位 (x,y) + 装配锚: F0520D 底面坐盖顶 TOWER_Z0
               (devices.json install "1a 竖装 13×15 底面着板方向"); F0520B/VV origin
               z=MAN_Z0-28=16.0 (N1 ⌀4.6 充满 ⌀4.8 承口带 —— 歧管承插悬置态);
  泵 ZR370     make_pump_module 装配位式 (轴沿 X @z=PUMP_AXIS_Z, 头端面 x=PMOD_OFF+T+CLR);
  传感 XGZP    pos.csv U6 焊盘中心 board_to_case(44,-22) 贴板面 z=Z_TOP, 航向 -90°
               (跨距 7.96 沿壳系 X, 与旧盒朝向一致; P1 倒钩落天花过孔邻位);
  引线桩/管路  connections.json 边端点解析 (devices.json geom3d + 上述放置), 见
               flowio/twin/connections_render.py (折线路径含逐边出处可溯)。
"""
import sys
from pathlib import Path

_ROOT = str(Path(__file__).resolve().parents[3])
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from flowio.geom import make_meshes as MM      # noqa: E402  管线单一实现 (D4 段升级)


def main():
    MM.main()
    # 每器件 STL 顶点/面数摘要 (验收自检项)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    print("\n── devices3d 资产摘要 (facets/顶点) ──")
    for name in ("valves.stl", "pump.stl", "parts_f.stl"):
        p = MM.OUT / name
        n, verts = G_parse(p)
        print("  %-12s facets=%-6d verts=%-6d size=%.1f KB"
              % (name, n, len(verts), p.stat().st_size / 1024.0))


def G_parse(path):
    """二进制 STL 计数 (case_geom.parse_stl 复用; 兼容二进制/ASCII)."""
    from flowio.geom import case_geom as G
    return G.parse_stl(str(path))


if __name__ == "__main__":
    main()
