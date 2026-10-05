# -*- coding: utf-8 -*-
"""pump_zr370 — ZR370-03PM 微型真空泵参数化建模 (D1 立式校正核心, spec §2.1; FreeCAD Part)。

几何 (datasheet literature/ZR370-03PM.pdf p2 图纸直推, devices.json pump[0].geom3d 单源):
    轴向分段 (E1 校正: 泵 = 头+电机两段, 非旧"单圆柱"): 泵头 ⌀24±0.3 ×27.3±0.5 (白, 隔膜腔)
    + 电机 ⌀27.0±0.5 ×30.8 (=58.1±0.5 总长 - 头长; 端面图 ⌀27, 灰金属壳);
    顶置双嘴 2-⌀4.2±0.3 ×7.5±0.4 于头段圆柱面 (z=24), 垂直于泵轴 (+Z 顶置, 图纸标注
    出气口/进气口; 嘴位 x=15/25, 嘴距 10.0 = 实物照估值, 对齐 enclosure PUMP_NOZ_DX);
    电机端面焊片正/负极 (图纸标注, 焊 380°C≤2s); 硅胶支架环位 ×2 = mech_mounts 数据
    (环 ⌀23/⌀26, 脚距 46, 支架实体由 geom/make_pump_module 消费, 此处不重复建模)。
器件自身原点 = 泵头端面轴心投影且泵体最低点 z=0 (轴 z=12.0); +X = 轴向(头→电机)。
[spec 偏差] §2.1 行文 "电机 ⌀24×31" vs 图纸端面 ⌀27.0±0.5 / 58.1-27.3=30.8 —— 默认按图纸。
"""
import sys
from pathlib import Path

import FreeCAD as App
import Part

_ROOT = str(Path(__file__).resolve().parents[3])
if _ROOT not in sys.path:                                    # FreeCAD python 免安装导入 (防重 guard)
    sys.path.insert(0, _ROOT)
from flowio.twin.devices3d import device_geom3d               # noqa: E402  单一真相源

_PIN_DIA, _PIN_LEN = 0.6, 3.0    # 电机端面焊片视觉径/长 (端面图焊片, 非尺寸标注件)


def _params(over=None):
    gm = device_geom3d("pump")
    p = {
        "body": dict(gm["body"]),                                # head_dia24 head_len27.3 motor_dia27 motor_len30.8 total_len58.1 axis_z12 noz_dx[15,25]
        "ports": {q["name"]: q for q in gm["pneumatic_ports"]},  # CHG/SUCK 顶置双嘴
        "terms": {t["name"]: t for t in gm["electrical_terminals"]},
    }
    if over:
        for k, v in over.items():
            if k == "body":
                p["body"].update(v)
            else:
                p[k] = v
    return p


DEFAULTS = _params()


def parts(**over):
    """分件 -> {"head","motor","CHG","SUCK","MOTOR_POS","MOTOR_NEG"} (器件自身原点系)。"""
    P = _params(over)
    b = P["body"]
    r_head, r_motor = b["head_dia"] / 2.0, b["motor_dia"] / 2.0
    hl, ml, az = b["head_len"], b["motor_len"], b["axis_z"]
    ax = App.Vector(1, 0, 0)

    head = Part.makeCylinder(r_head, hl, App.Vector(0, 0, az), ax)          # 泵头 (隔膜腔, 白)
    motor = Part.makeCylinder(r_motor, ml, App.Vector(hl, 0, az), ax)       # 电机 (灰金属壳)

    solids = {"head": head, "motor": motor}
    for nm, q in P["ports"].items():                                        # 顶置双嘴 ⊥ 泵轴
        qx, qy, qz = q["pos"]
        solids[nm] = Part.makeCylinder(q["dia"] / 2, q["len"],
                                       App.Vector(qx, qy, qz), App.Vector(0, 0, 1))
    for nm in ("MOTOR_POS", "MOTOR_NEG"):                                   # 电机端面焊片
        t = P["terms"][nm]
        tx, ty, tz = t["pos"]
        solids[nm] = Part.makeCylinder(_PIN_DIA / 2, _PIN_LEN,
                                       App.Vector(tx, ty, tz), App.Vector(1, 0, 0))
    return solids


def build(**over):
    """ZR370 泵器件 -> Part Compound (器件自身原点系; 嘴顶 z=31.5=devices dims.h 交叉验证)。"""
    return Part.makeCompound(list(parts(**over).values()))


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    sh = build()
    print("[pump_zr370] bbox=%s solids=%d" % (sh.BoundBox, len(sh.Solids)))
