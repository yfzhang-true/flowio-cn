# -*- coding: utf-8 -*-
"""FLOWIO-P1 流拓扑同源生成 — pos.csv → webapp/flows.json + hotspots.json.

运行: python make_flows.py   (纯标准库, 无 FreeCAD 依赖)
输出: firmware/twin/webapp/{flows.json,hotspots.json}

坐标系: 与 S3 make_meshes.py 完全一致 (壳坐标系, 底壳原点):
    x = PosX + OX,  y = -PosY + OX,  OX = 2.9 (WALL+CLR)
    顶面器件 z = WALL + PCB_T = 4.0 (板面)
Y 方向语义 (KiCad Y 轴向下): "沿 -Y" = PosY 减小 = 壳 y 增大 = 穿出端子侧开孔
(make_case.py side_cut("B",...) 在高 y 壁, TY=68.5) → 气流弧线朝执行器向外延伸。

拓扑数据源: fab/flowio-p1-pos.csv (器件坐标) + 引脚表 (走线顺序, 写死于 ELEC/AIR)。
任一 ref 在 pos.csv 查不到 → 报错列出全部缺失, 不许静默跳过。
"""
import csv
import json
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import case_geom as G          # 装配常量单一真相源 (2026-10-03: Z_TOP 4.0 -> 9.0)

ROOT = HERE.parents[2]
POSCSV = ROOT / "hardware" / "flowio-p1" / "fab" / "flowio-p1-pos.csv"
OUTDIR = ROOT / "firmware" / "twin" / "webapp"

Z_TOP = G.Z_TOP                # 顶面器件所在板面 z (板坐铜柱顶, 见 case_geom)

# ---------- 拓扑表 (板坐标 ref 序列; 数据源 = pos.csv + 引脚表) ----------
ELEC = [
    ("vin_dc",  "#e8b64c", ["J1", "D1", "C1"],  "rail_5v.load_a"),
    ("vin_usb", "#e8b64c", ["J2", "D2", "C17"], "rail_5v.load_a"),
    ("buck_in", "#e8b64c", ["C1", "U3", "L1"],  "rail_3v3.load_a"),
    ("rail3v3", "#7ee2b8", ["L1", "C8", "U1"],  "rail_3v3.load_a"),
] + [(f"gate{i + 1}", "#6aa9ff", ["U1", f"R{39 + i}", f"Q{3 + i}", f"J{10 + i}"],
      f"valves[{i}].i_A") for i in range(8)]

DESC = {
    "vin_dc":  "DC 输入→SS34 整流→5V 轨",
    "vin_usb": "USB-C→SS34 整流→5V 轨",
    "buck_in": "5V→TPS54331 buck→功率电感",
    "rail3v3": "电感→100uF→ESP32 (3V3 轨)",
}

AIR_LEN = 25.0    # 端子向外延伸定长 (spec §3.2 ~25mm; 旧 9mm 假设废弃)
AIR_CTRL = 14.0   # QuadraticBezier 控制点离端子距离
AIR = [(f"port{i + 1}", f"J{10 + i}") for i in range(8)]

# ---------- hotspots: 精选 6 器件 (ref → 盒体/中文名/live 映射) ----------
# live 字段路径 = /api/board/state telemetry (board_model.py 契约)。
HOTSPOTS = [
    ("U1", "主控 ESP32-S3", [
        ("3.3V 轨", "rail_3v3.v", "V"),
        ("CPU 结温", "temp_est_c.cpu", "℃"),
        ("运行时长", "uptime_s", "s")]),
    ("U3", "降压 TPS54331 (buck)", [
        ("输入 5V", "rail_5v.v", "V"),
        ("输出 3.3V", "rail_3v3.v", "V"),
        ("效率", "rail_3v3.buck_eff", "%"),
        ("结温", "temp_est_c.buck", "℃")]),
    ("Q3", "阀 1 驱动 MOSFET", [
        ("阀 1 电流", "valves[0].i_A", "A"),
        ("阀 1 功率", "valves[0].p_w", "W"),
        ("MOS 结温", "temp_est_c.mos", "℃")]),
    ("J1", "DC 电源输入座", [
        ("5V 轨", "rail_5v.v", "V"),
        ("负载", "rail_5v.load_a", "A"),
        ("功率", "rail_5v.p_w", "W")]),
    ("J10", "阀 1 端子", [
        ("阀 1 电流", "valves[0].i_A", "A"),
        ("阀 1 功率", "valves[0].p_w", "W")]),
    ("U2", "I2C 扩展 TCA9548A", [
        ("3.3V 轨", "rail_3v3.v", "V"),
        ("逻辑电流", "rail_3v3.load_a", "A")]),
]

# Package 尺寸表 → case_geom.dims_for (与 parts_f.stl 盒体逐面重合, 单一来源)

def dims_for(pkg):
    return G.dims_for(pkg)


def load_pos():
    """pos.csv → {ref: row}; 仅读, 不写。"""
    parts = {}
    with open(POSCSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            ref = (row["Ref"] or "").strip()
            parts[ref] = {
                "pkg": (row["Package"] or "").strip(),
                "x": float(row["PosX"]),
                "y": float(row["PosY"]),      # KiCad Y (向下为负)
                "rot": float(row["Rot"]),
                "side": (row["Side"] or "").strip().lower(),
            }
    return parts


def shell_xy(p):
    """板→壳坐标 (case_geom 定稿映射: x=PosX+OX, y=-PosY+OX)。"""
    return G.board_to_case(p["x"], p["y"])


def require_refs(pos, refs):
    """任一 ref 缺失即整体报错 (列出全部缺失, 不许静默跳过)。"""
    missing = sorted({r for r in refs if r not in pos})
    if missing:
        raise SystemExit("[flows] FATAL: pos.csv 缺 ref: %s" % ", ".join(missing))


def manhattan_pts(refs, pos):
    """相邻器件焊盘间曼哈顿折线 (先 x 后 y): 每段折 1 个中点 → 段数=中点数+1。"""
    pts = []
    prev = None
    for r in refs:
        x, y = shell_xy(pos[r])
        if prev is not None:
            mx, my = x, prev[1]              # 先走 x 到目标列, 再走 y 到目标行
            if (mx, my) != prev:
                pts.append((mx, my))
            if (x, y) != (mx, my):
                pts.append((x, y))
        else:
            pts.append((x, y))
        prev = (x, y)
    return [(round(x, 3), round(y, 3), Z_TOP) for x, y in pts]


def build_elec(pos):
    out = []
    for pid, color, refs, live in ELEC:
        out.append({
            "id": pid,
            "color": color,
            "points": manhattan_pts(refs, pos),
            "desc": DESC.get(pid, "ESP32→栅极电阻→MOSFET→端子 %s" % pid[-1]),
            "live": live,
            "refs": list(refs),
        })
    return out


def build_air(pos):
    """端子中心出发的 QuadraticBezier: 沿 -Y (KiCad 系) = 壳 +Y 向外至执行器方向。"""
    out = []
    for pid, ref in AIR:
        x, y = shell_xy(pos[ref])
        out.append({
            "id": pid,
            "ref": ref,
            "curve": "quadratic",
            "start": [round(x, 3), round(y, 3), Z_TOP],
            "ctrl": [round(x, 3), round(y + AIR_CTRL, 3), Z_TOP],
            "end": [round(x, 3), round(y + AIR_LEN, 3), Z_TOP],
            "desc": "端子→执行器",
            "live": "valve_duty[%s]" % pid[4:],   # /api/state 阀 duty (0-255)
            "pressure": "/api/state p 符号",       # 正压青 / 真空琥珀
        })
    return out


def build_hotspots(pos):
    out = []
    for ref, name, live in HOTSPOTS:
        p = pos[ref]
        w, d, h = dims_for(p["pkg"])
        if int(round(p["rot"])) % 180 == 90:      # 90 度旋转交换 w/d
            w, d = d, w
        assert p["side"] == "top", "hotspot %s 应为顶面器件" % ref
        cx, cy = shell_xy(p)
        out.append({
            "ref": ref,
            "name": name,
            "center": [round(cx, 3), round(cy, 3), round(Z_TOP + h / 2.0, 3)],
            "size": [w, d, h],
            "live": [{"label": lb, "field": fd, "unit": un} for lb, fd, un in live],
        })
    return out


def main():
    pos = load_pos()
    all_refs = [r for _pid, _c, refs, _l in ELEC for r in refs] + [r for _p, r in AIR] \
        + [ref for ref, _n, _l in HOTSPOTS]
    require_refs(pos, all_refs)
    print("[pos] %d refs resolved, 0 missing" % len(set(all_refs)))

    flows = {
        "meta": {
            "coord": "shell: x=PosX+2.9, y=-PosY+2.9 (S3 make_meshes 同源)",
            "z_top": Z_TOP,
            "air_frame": "-Y 为 KiCad/PosY 系 (壳 +Y, 穿端子侧开孔向外)",
            "source": "hardware/flowio-p1/fab/flowio-p1-pos.csv",
        },
        "elec": build_elec(pos),
        "air": build_air(pos),
    }
    hotspots = {"hotspots": build_hotspots(pos)}

    OUTDIR.mkdir(parents=True, exist_ok=True)
    (OUTDIR / "flows.json").write_bytes(
        json.dumps(flows, ensure_ascii=False, indent=1).encode("utf-8"))
    (OUTDIR / "hotspots.json").write_bytes(
        json.dumps(hotspots, ensure_ascii=False, indent=1).encode("utf-8"))
    print("[out] flows.json: %d elec + %d air" % (len(flows["elec"]), len(flows["air"])))
    print("[out] hotspots.json: %d" % len(hotspots["hotspots"]))
    print("FLOWS OK ->", OUTDIR)


main()
