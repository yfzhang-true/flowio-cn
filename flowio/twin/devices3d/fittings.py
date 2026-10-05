# -*- coding: utf-8 -*-
"""fittings — 管路连接件参数化建模 (D1, spec §2.1; D4 裁定 A 关键弯折点折线; FreeCAD Part)。

三族 (通用连接件, 非器件实例 —— 无 devices.json 条目, 参数即本模块 DEFAULTS):
    硅胶管段   ID3×OD7 (阀/传感侧) / ID5×OD7 (泵侧) —— 空腔贯通, 路径 = 关键弯折点折线
               (D4-A: 每段长度可核算 = 下料长度直喂采购; 不做样条, registry §6 + 硅胶管.pdf 🅱)
    Kamoer 直通  1/8 档 倒钩 ⌀3.5/颈 ⌀2.0 ×25 长, 六角 ⌀8 ("1/8 直通 适用软管内径 1.6-3.2mm",
               透明转接头.pdf p1 图册 🅰) —— 3mm ID 管对接
    Kamoer 变径  1/8↔1/4 档 ⌀4.9/⌀2 ↔ ⌀5/⌀3.8 ×30.7, 六角 ⌀14 (同图册);
               registry: "3↔4.5mm 档, 精确规格 T6 按嘴径实测定" → 参数化待定型
    三通      T 形 (直通段 + 垂直支口), 同店通用件无一手图纸 [inferred] —— 按 1/8 直通同
               参数档参数化, 采购定型后校正
所有接口 = 倒钩口两端 (D2 连接边端点: 口径/位置由 connections.json 消费)。
"""
import sys
from pathlib import Path

import FreeCAD as App
import Part

_ROOT = str(Path(__file__).resolve().parents[3])
if _ROOT not in sys.path:                                    # FreeCAD python 免安装导入 (防重 guard)
    sys.path.insert(0, _ROOT)

# 参数出处见模块 docstring; 结构: 组名 -> 尺寸 dict (mm)
DEFAULTS = {
    "tube": {"id_valve": 3.0, "od_valve": 7.0, "id_pump": 5.0, "od_pump": 7.0},
    "straight_barb": {"dia": 3.5, "neck": 2.0, "len": 25.0, "collar_d": 8.0, "collar_t": 2.0},
    "reducing_barb": {"dia_a": 4.9, "neck_a": 2.0, "dia_b": 5.0, "neck_b": 3.8,
                      "len": 30.7, "collar_d": 14.0, "collar_t": 2.0},
    # 三通: 同店通用件无一手图纸 [inferred] —— inferred=true 供 D2 图谱程序化过滤待实测边
    "tee": {"dia": 3.5, "neck": 2.0, "run_len": 25.0, "stem_len": 12.0, "collar_d": 8.0,
            "inferred": True},
}


def _V(*a):
    return App.Vector(*a)


def _seg(p0, p1, r):
    """两点间 ⌀2r 圆柱段 (axis-aligned 或斜线一律两点放样, 对齐 pneu_geom.tube 模式)."""
    d = p1.sub(p0)
    return Part.makeCylinder(r, d.Length, p0, d.normalize())


def _polyline_fused(points, r):
    """折线放样体 (熔接单 Solid): 各段圆柱 + 折点球 (视觉连续圆角); 输入 [x,y,z] 列表."""
    pts = [_V(*p) for p in points]
    sol = _seg(pts[0], pts[1], r)
    for i in range(1, len(pts) - 1):
        sol = sol.fuse(_seg(pts[i], pts[i + 1], r))
        sol = sol.fuse(Part.makeSphere(r, pts[i]))
    return sol.removeSplitter()


def build_silicone_tube(points, id_mm=None, od_mm=None):
    """硅胶管段: 关键弯折点折线放样, 内腔 ⌀id 贯通 (空腔管, 两端开口)。

    points: 折线顶点序列 [[x,y,z], ...] (D4-A, ≥2 点; 3 点 = 单弯, 4 点 = 三点弯两段);
    默认 ID3×OD7 (阀/传感侧), 泵侧传 id_mm=5.0。返回 Part.Shape (单一 Solid)。
    """
    d = DEFAULTS["tube"]
    id_mm = d["id_valve"] if id_mm is None else id_mm
    od_mm = d["od_valve"] if od_mm is None else od_mm
    # 内腔沿首末腿方向外延贯通 (两端开口) —— 延伸段沿腿向, 非端点连线 (斜 shortcuts 会挖穿弯头)
    p0, p1 = _V(*points[0]), _V(*points[-1])
    u0 = _V(*points[1]).sub(p0).normalize()
    u1 = p1.sub(_V(*points[-2])).normalize()
    ext = [list(p0.sub(u0.multiply(2.0)))] + [list(p) for p in points] + \
        [list(p1.add(u1.multiply(2.0)))]
    outer = _polyline_fused(points, od_mm / 2.0)
    bore = _polyline_fused(ext, id_mm / 2.0)
    return outer.cut(bore).removeSplitter()


def _barb_run(x0, x1, dia, neck):
    """沿 +X 的倒钩段: 大端 x0 (⌀dia) 收至小端 x1 (⌀neck)."""
    return Part.makeCone(dia / 2.0, neck / 2.0, abs(x1 - x0), _V(x0, 0, 0), _V(1, 0, 0))


def build_straight_barb(**over):
    """Kamoer 倒钩直通 (1/8 档): 两端倒钩 + 中央六角 ⌀8 (视觉圆柱), 总长 25。"""
    p = dict(DEFAULTS["straight_barb"])
    p.update(over or {})
    half = (p["len"] - p["collar_t"]) / 2.0
    barb_a = _barb_run(0.0, half, p["dia"], p["neck"])                     # 大端 x=0 → 颈 x=half
    collar = Part.makeCylinder(p["collar_d"] / 2, p["collar_t"], _V(half, 0, 0), _V(1, 0, 0))
    barb_b = Part.makeCone(p["dia"] / 2, p["neck"] / 2, half,
                           _V(p["len"], 0, 0), _V(-1, 0, 0))               # 大端 x=len → 颈
    return Part.makeCompound([barb_a, collar, barb_b]).removeSplitter()


def build_reducing_barb(**over):
    """Kamoer 倒钩变径 (1/8↔1/4 档): 大端 ⌀4.9/颈2 ↔ 小端 ⌀5/颈3.8, 总长 30.7。"""
    p = dict(DEFAULTS["reducing_barb"])
    p.update(over or {})
    half = (p["len"] - p["collar_t"]) / 2.0
    barb_a = _barb_run(0.0, half, p["dia_a"], p["neck_a"])
    collar = Part.makeCylinder(p["collar_d"] / 2, p["collar_t"], _V(half, 0, 0), _V(1, 0, 0))
    barb_b = Part.makeCone(p["dia_b"] / 2, p["neck_b"] / 2, half,
                           _V(p["len"], 0, 0), _V(-1, 0, 0))
    return Part.makeCompound([barb_a, collar, barb_b]).removeSplitter()


def build_tee(**over):
    """三通: 直通段 (双倒钩, 沿 X) + 垂直支口 (沿 +Z, 基座落于六角鼓面, 尖朝上)。"""
    p = dict(DEFAULTS["tee"])
    p.update(over or {})
    run = build_straight_barb(dia=p["dia"], neck=p["neck"], len=p["run_len"],
                              collar_d=p["collar_d"])
    z0 = p["collar_d"] / 2.0                                   # 支口基座 = 六角鼓面 (免共体穿插)
    stem = Part.makeCone(p["dia"] / 2, p["neck"] / 2, p["stem_len"] - z0,
                         _V(p["run_len"] / 2, 0, z0), _V(0, 0, 1))
    return Part.makeCompound([run, stem]).removeSplitter()


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    for nm, fn in (("tube_id3", lambda: build_silicone_tube([[0, 0, 0], [40, 0, 0]])),
                   ("tube_bend", lambda: build_silicone_tube([[0, 0, 0], [30, 0, 0], [30, 0, 25]])),
                   ("straight", build_straight_barb), ("reducing", build_reducing_barb),
                   ("tee", build_tee)):
        sh = fn()
        print("[fittings] %-10s bbox=%s solids=%d" % (nm, sh.BoundBox, len(sh.Solids)))
