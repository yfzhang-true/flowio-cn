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

# ---------- P1.1 过渡位姿表 (T3 重生成 pos.csv 后由 csv 覆盖, 届时删除) ----------
# 背景: P1.1 原理图已加 J20-J23/R55-58/Q13-16 (S/V/F 主阀 + 泵), 但 PCB/pos.csv
# 尚为 P1.0 版本 (T3 重布局后才含新 ref)。为让 flows 拓扑先行, 按既有 8 通道
# 端子排 (J10-J17: x=6.5+11k, Q/R 列 x=4.1+11k) 向右延伸的过渡坐标生成;
# load_pos 中 pos.csv 行优先, T3 重跑 make_flows 即自动切换为真实布局。
def _p11_row(refs, x0, y, rot, pkg):
    return {ref: {"pkg": pkg, "x": x0 + 11 * k, "y": y, "rot": rot, "side": "top"}
            for k, ref in enumerate(refs)}

POS_P11 = {}
POS_P11.update(_p11_row(["J20", "J21", "J22", "J23"], 94.5, -68.5, 180,
                        "CONN-TH_2P-P2.54_XH-2P"))
POS_P11.update(_p11_row(["Q13", "Q14", "Q15", "Q16"], 92.1, -60.5, 0,
                        "SOT-23-3_L2.9-W1.3-P1.90-LS2.4-BR"))
POS_P11.update(_p11_row(["R55", "R56", "R57", "R58"], 92.1, -55.5, 90, "R0603"))

# ---------- 拓扑表 (板坐标 ref 序列; 数据源 = pos.csv + 引脚表) ----------
# 电源段语义说明: +5V/+3V3/USB_VBUS 均被 device_graph.netlist 判为电源网而不进
# electrical_edges, 电源流 (vin_pwr/vin_usb/buck_in/rail3v3) 的相邻对沿用既有
# 惯例 —— 按 power 路径上的真实器件链表述, 依赖网表粗粒度解析通过校验;
# 信号段 (gate*) 相邻对全部为非电源网真实电气边。
# P1.1: vin_dc(DC005+D1, 已删) → vin_pwr(USB-C J1 直挂 5V); 新增 S/V/F 主阀 + 泵。
# live 字段: gateS/V/F 用 valves[8..10].i_A (固件 N_VALVES 扩至 11 后点亮,
#   现值缺省 0 底光, 无害); 泵无独立遥测字段, 借 rail_5v.load_a (泵为 5V 主负载)。
ELEC = [
    ("vin_pwr", "#e8b64c", ["J1", "C17", "C1"], "rail_5v.load_a"),
    ("vin_usb", "#e8b64c", ["J2", "D2", "C17"], "rail_5v.load_a"),
    ("buck_in", "#e8b64c", ["C1", "U3", "L1"],  "rail_3v3.load_a"),
    ("rail3v3", "#7ee2b8", ["L1", "C8", "U1"],  "rail_3v3.load_a"),
] + [(f"gate{i + 1}", "#6aa9ff", ["U1", f"R{39 + i}", f"Q{3 + i}", f"J{10 + i}"],
      f"valves[{i}].i_A") for i in range(8)] + [
    ("gateS", "#6aa9ff", ["U1", "R55", "Q13", "J20"], "valves[8].i_A"),
    ("gateV", "#6aa9ff", ["U1", "R56", "Q14", "J21"], "valves[9].i_A"),
    ("gateF", "#6aa9ff", ["U1", "R57", "Q15", "J22"], "valves[10].i_A"),
    ("pump",   "#6aa9ff", ["U1", "R58", "Q16", "J23"], "rail_5v.load_a"),
]

DESC = {
    "vin_pwr": "USB-C 电源口 (J1, 5A)→5V 输入电容→5V 轨",
    "vin_usb": "USB-C 调试口→SS34 或门→5V 轨",
    "buck_in": "5V→TPS54331 buck→功率电感",
    "rail3v3": "电感→100uF→ESP32 (3V3 轨)",
    "gateS": "ESP32→栅极电阻→MOSFET→S 充气主阀座 (1f-β)",
    "gateV": "ESP32→栅极电阻→MOSFET→V 真空主阀座 (1f-β)",
    "gateF": "ESP32→栅极电阻→MOSFET→F 排气主阀座 (1f-β)",
    "pump": "ESP32→栅极电阻→MOSFET→泵模块接口 (分装式)",
}

AIR_LEN = 25.0    # 端子向外延伸定长 (spec §3.2 ~25mm; 旧 9mm 假设废弃)
AIR_CTRL = 14.0   # QuadraticBezier 控制点离端子距离
# id 须为 portN (webapp flows.js: parseInt(id.slice(4))-1 → pnu.valves[n])
AIR = [(f"port{i + 1}", f"J{10 + i}") for i in range(8)] + [
    ("port9", "J20"), ("port10", "J21"), ("port11", "J22"), ("port12", "J23")]
AIR_DESC = {
    "port9": "S 充气主阀→歧管 (1f-β)",
    "port10": "V 真空主阀→泵模块真空管 (双管之一)",
    "port11": "F 排气主阀→消音器/大气",
    "port12": "泵模块供压管 (V/S 主阀公共源, 双管之二)",
}

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
    ("J1", "USB-C 电源输入口 (5A)", [
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
    """pos.csv → {ref: row}; 仅读, 不写。P1.1: 新 ref 由 POS_P11 过渡表补,
    pos.csv 行优先 (T3 重生成含新 ref 的 csv 后过渡表自动失效)。"""
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
    stale = sorted(set(POS_P11) & set(parts))
    if stale:
        print("[p11] pos.csv 已覆盖过渡表 ref: %s — 可删除 POS_P11" % ", ".join(stale))
    parts.update({k: v for k, v in POS_P11.items() if k not in parts})
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
            "desc": AIR_DESC.get(pid, "端子→执行器"),
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


if __name__ == "__main__":
    main()
