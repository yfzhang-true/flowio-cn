# -*- coding: utf-8 -*-
"""FLOWIO-CN P1 原理图生成器 v2 (P1.1: 11 阀+泵+XGZP+USB-C 供电)
单一真值源: PARTS 表同时供原理图与 PCB 生成使用。
教训固化:
  - MCP 符号引脚 y 在放置时取反(符号库 y 向上, 图纸 y 向下)
  - 器件原点须对齐 1.27mm 连接网格
  - lib_id 与嵌入符号名须带库前缀 "JLC-MCP:"
  - unspecified 引脚嵌入时改 passive(避免 pin_to_pin 类型矩阵警告)
  - 引线端点须防撞(不同网络不得共点/落线)
用法: "E:/Program Files/KiCad/10.0/bin/python.exe" flowio/hw/sch_gen.py
M1 迁移 (2026-10): tools/gen_sch.py -> flowio/hw/sch_gen.py (代码逻辑零改动,
仅输出路径改为经包定位解析到 hardware/flowio-p1/, 不再依赖运行 cwd)。
注意: pcb_gen.py / tools/make_bom.py 以受限 ast 从**本文件源码**提取 PARTS
(文件名即契约, 重命名须同步二者读源路径)。
"""
import re, os, glob, uuid as _uuid

# 产物目录: 仓库根/hardware/flowio-p1 (M1 前为 cwd 相对路径, 现经包定位, cwd 无关)
HWDIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "hardware", "flowio-p1")

LIBDIR = r"C:/Users/yuefe/Documents/KiCad/9.0/3rdparty/jlc_mcp/symbols"
ROOT_UUID = "7f1a2c34-0000-4000-8000-5a6b7c8d9e0f"
PROJ = "flowio-p1"
SCH_VERSION = "20250114"

def U(): return str(_uuid.uuid4())

def snap(v):
    return round(v / 1.27) * 1.27

def fnum(v):
    s = f"{v:.3f}".rstrip("0").rstrip(".")
    return s if s not in ("", "-0") else "0"

# ---------------------------------------------------------------- 符号库解析
def load_libs():
    libs = {}
    for f in glob.glob(os.path.join(LIBDIR, "*.kicad_sym")):
        txt = open(f, encoding="utf-8").read()
        for m in re.finditer(r'\n\t\(symbol "([^"]+)"\n', txt):
            name = m.group(1)
            depth, i = 0, txt.index("(", m.start())
            while i < len(txt):
                if txt[i] == "(":
                    depth += 1
                elif txt[i] == ")":
                    depth -= 1
                    if depth == 0:
                        break
                i += 1
            blk = txt[m.start()+1: i+1]
            pins = []
            for et, x, y, ang, nm, num in re.findall(
                    r'\(pin (\w+) \w+\s*\(at ([-\d.]+) ([-\d.]+) (\d+)\)\s*\(length [\d.]+\)\s*'
                    r'\(name "([^"]+)"[\s\S]*?\(number "([^"]+)"', blk):
                pins.append(dict(num=num, name=nm, x=float(x), y=float(y),
                                 ang=int(ang), etype=et))
            xs, ys = [], []
            for rx, ry in re.findall(r'\(xy ([-\d.]+) ([-\d.]+)', blk):
                xs.append(float(rx)); ys.append(float(ry))
            for rsx, rsy, rex, rey in re.findall(
                    r'\(rectangle\s*\(start ([-\d.]+) ([-\d.]+)\)\s*\(end ([-\d.]+) ([-\d.]+)\)', blk):
                xs += [float(rsx), float(rex)]; ys += [float(rsy), float(rey)]
            for cx, cy, cr in re.findall(r'\(circle\s*\(center ([-\d.]+) ([-\d.]+)\)\s*\(radius ([-\d.]+)', blk):
                xs += [float(cx)-float(cr), float(cx)+float(cr)]
                ys += [float(cy)-float(cr), float(cy)+float(cr)]
            bbox = (min(xs), min(ys), max(xs), max(ys)) if xs else (-5.08, -5.08, 5.08, 5.08)
            libs[name] = dict(text=blk.rstrip(), pins=pins, bbox=bbox)
    return libs

LIBS = load_libs()

def pin_dir(sym, p):
    """最终规则: 图形包围盒判据(x 优先) + 引脚角度兜底(0:L/180:R/90:D/270:U, 显示系)。
    质心法对共线引脚(XH 连接器/端子)会整体误判, 已废弃。"""
    if "bbox" in sym:
        x0, y0, x1, y1 = sym["bbox"]
        px, py = p["x"], -p["y"]
        if px <= x0 + 0.05:
            return "L"
        if px >= x1 - 0.05:
            return "R"
        if py <= y0 + 0.05:
            return "U"
        if py >= y1 - 0.05:
            return "D"
    return {0: "L", 180: "R", 90: "D", 270: "U"}.get(p.get("ang", 0), "L")

# ---------------------------------------------------------------- 电源符号

def power_sym_def(net, kind):
    if kind == "flag":
        return _FLAG_FALLBACK
    if net == "GND":
        return _GND_FALLBACK
    if net == "+3V3":
        return _R3V3_FALLBACK
    return _R5V_FALLBACK.replace("+5V", net)

_GND_FALLBACK = """	(symbol "power:GND"
		(power)
		(pin_numbers (hide yes))
		(pin_names (offset 0) (hide yes))
		(exclude_from_sim no)
		(in_bom yes)
		(on_board yes)
		(property "Reference" "#PWR" (at 0 -3.81 0) (hide yes) (effects (font (size 1.27 1.27))))
		(property "Value" "GND" (at 0 3.556 0) (effects (font (size 1.27 1.27))))
		(property "Footprint" "" (at 0 0 0) (hide yes) (effects (font (size 1.27 1.27))))
		(property "Datasheet" "" (at 0 0 0) (hide yes) (effects (font (size 1.27 1.27))))
		(property "ki_keywords" "global power" (at 0 0 0) (hide yes) (effects (font (size 1.27 1.27))))
		(symbol "GND_0_1"
			(polyline (pts (xy 0 0) (xy 0 -1.27) (xy 1.27 -1.27) (xy 0 -2.54) (xy -1.27 -1.27) (xy 0 -1.27))
				(stroke (width 0) (type default)) (fill (type none)))
		)
		(symbol "GND_1_1"
			(pin power_in line (at 0 0 270) (length 0)
				(name "~" (effects (font (size 1.27 1.27))))
				(number "1" (effects (font (size 1.27 1.27))))
			)
		)
		(embedded_fonts no)
	)"""

def _rail_def(net):
    return """	(symbol "power:__NET__"
		(power)
		(pin_numbers (hide yes))
		(pin_names (offset 0) (hide yes))
		(exclude_from_sim no)
		(in_bom yes)
		(on_board yes)
		(property "Reference" "#PWR" (at 0 -3.81 0) (hide yes) (effects (font (size 1.27 1.27))))
		(property "Value" "__NET__" (at 0 3.556 0) (effects (font (size 1.27 1.27))))
		(property "Footprint" "" (at 0 0 0) (hide yes) (effects (font (size 1.27 1.27))))
		(property "Datasheet" "" (at 0 0 0) (hide yes) (effects (font (size 1.27 1.27))))
		(property "ki_keywords" "global power" (at 0 0 0) (hide yes) (effects (font (size 1.27 1.27))))
		(symbol "__SUB___0_1"
			(polyline (pts (xy -0.762 1.27) (xy 0 2.54)) (stroke (width 0) (type default)) (fill (type none)))
			(polyline (pts (xy 0 2.54) (xy 0.762 1.27)) (stroke (width 0) (type default)) (fill (type none)))
			(polyline (pts (xy 0 0) (xy 0 2.54)) (stroke (width 0) (type default)) (fill (type none)))
		)
		(symbol "__SUB___1_1"
			(pin power_in line (at 0 0 90) (length 0)
				(name "~" (effects (font (size 1.27 1.27))))
				(number "1" (effects (font (size 1.27 1.27))))
			)
		)
		(embedded_fonts no)
	)""".replace("__NET__", net).replace("__SUB__", net)

_R3V3_FALLBACK = _rail_def("+3V3")
_R5V_FALLBACK = _rail_def("+5V")

_FLAG_FALLBACK = """	(symbol "power:PWR_FLAG"
		(power global)
		(pin_numbers (hide yes))
		(pin_names (offset 0) (hide yes))
		(exclude_from_sim no)
		(in_bom yes)
		(on_board yes)
		(property "Reference" "#FLG" (at 0 -3.81 0) (hide yes) (effects (font (size 1.27 1.27))))
		(property "Value" "PWR_FLAG" (at 0 3.556 0) (effects (font (size 1.27 1.27))))
		(property "Footprint" "" (at 0 0 0) (hide yes) (effects (font (size 1.27 1.27))))
		(property "Datasheet" "" (at 0 0 0) (hide yes) (effects (font (size 1.27 1.27))))
		(property "ki_keywords" "flag power" (at 0 0 0) (hide yes) (effects (font (size 1.27 1.27))))
		(symbol "PWR_FLAG_0_1"
			(polyline (pts (xy 0 0) (xy 0 -2.54) (xy -1.27 -2.032) (xy 0 -1.524))
				(stroke (width 0) (type default)) (fill (type none)))
		)
		(symbol "PWR_FLAG_0_0"
			(pin power_out line (at 0 0 270) (length 0)
				(name "" (effects (font (size 1.27 1.27))))
				(number "1" (effects (font (size 1.27 1.27))))
			)
		)
		(embedded_fonts no)
	)"""

_TP_FALLBACK = """	(symbol "Mechanical:TestPoint"
		(pin_numbers (hide yes))
		(pin_names (offset 1.016))
		(exclude_from_sim no)
		(in_bom yes)
		(on_board yes)
		(property "Reference" "TP" (at 0 -3.81 0) (effects (font (size 1.27 1.27))))
		(property "Value" "TestPoint" (at 0 3.81 0) (effects (font (size 1.27 1.27))))
		(property "Footprint" "TestPoint:TestPoint_Pad_D1.0mm" (at 0 0 0) (hide yes) (effects (font (size 1.27 1.27))))
		(property "Datasheet" "" (at 0 0 0) (hide yes) (effects (font (size 1.27 1.27))))
		(symbol "TestPoint_0_1"
			(circle (center 0 0) (radius 1.27) (stroke (width 0.254) (type default)) (fill (type background)))
		)
		(symbol "TestPoint_1_1"
			(pin passive line (at 0 0 270) (length 0)
				(name "1" (effects (font (size 1.27 1.27))))
				(number "1" (effects (font (size 1.27 1.27))))
			)
		)
	)"""

TP_DEF = _TP_FALLBACK

# ---------------------------------------------------------------- 自建符号 (P1.1)
# 本地 JLC-MCP 库缺以下符号, 按需内嵌生成 (pin 坐标=连接点, 本体外延 2.54):
#   WAFER-XH2_54-2PZZ  XH2.54-2P 卧贴插座 (footprint=C7429671 真件, 焊盘 3/4 壳
#                      体定位片无网 → 符号只建模信号 1/2)
#   XGZP6897D  板载压力传感 宽体 SOP-8 (2=VDD 6=SDA 7=SCL 8=GND, 其余 NC)
# 注: TYPE-C-31-M-12 曾为自建, T3 装 C165948 后 JLC 库有真符号 (引脚名与封装
# 焊盘一一对应: A1B12/A4B9/B1A12/B4A9/EH1-4) → 改用库符号, 防遮蔽断言放行。

# P1.1 选型定案 (T3): XH2.54-2P 卧贴插座 = Megastar ZX-XH2.54-2PWT (C7429671,
# jlcpcb MCP 已装入全局 KiCad 库; 库存 13.9 万, 经济装配, SMD 右贴 3A/250V,
# 本体 10.0×7.8×6.2mm; footprint 焊盘 1/2=信号(口侧) + 3/4=壳体定位焊片(背侧, 不布网))。
FP_XH2P = "JLC-MCP:CONN-SMD_2P-P2.54_MEGASTAR_ZX-XH2.54-2PWT"
LCSC_XH2P = "C7429671"

def _mk_custom(name, ref_prefix, val, fp, pin_tab, rect, keywords=""):
    body = []
    a = body.append
    a('\t(symbol "%s"' % name)
    a('\t\t(exclude_from_sim no)')
    a('\t\t(in_bom yes)')
    a('\t\t(on_board yes)')
    a('\t\t(property "Reference" "%s" (at 1.27 %s 0) (effects (font (size 1.27 1.27))))'
      % (ref_prefix, fnum(rect[3] + 2.54)))
    a('\t\t(property "Value" "%s" (at 1.27 %s 0) (effects (font (size 1.27 1.27))))'
      % (val, fnum(rect[1] - 2.54)))
    a('\t\t(property "Footprint" "%s" (at 0 0 0) (hide yes) (effects (font (size 1.27 1.27))))' % fp)
    a('\t\t(property "Datasheet" "" (at 0 0 0) (hide yes) (effects (font (size 1.27 1.27))))')
    if keywords:
        a('\t\t(property "ki_keywords" "%s" (at 0 0 0) (hide yes) (effects (font (size 1.27 1.27))))'
          % keywords)
    a('\t\t(symbol "%s_0_1"' % name)
    a('\t\t\t(rectangle (start %s %s) (end %s %s)'
      % (fnum(rect[0]), fnum(rect[1]), fnum(rect[2]), fnum(rect[3]))
      + ' (stroke (width 0.254) (type default)) (fill (type background)))')
    a('\t\t)')
    a('\t\t(symbol "%s_1_1"' % name)
    pins = []
    for num, pname, px, py, ang in pin_tab:
        a('\t\t\t(pin passive line (at %s %s %d) (length 2.54)'
          % (fnum(px), fnum(py), ang))
        a('\t\t\t\t(name "%s" (effects (font (size 1.27 1.27))))' % pname)
        a('\t\t\t\t(number "%s" (effects (font (size 1.27 1.27))))' % num)
        a('\t\t\t)')
        pins.append(dict(num=num, name=pname, x=px, y=py, ang=ang, etype="passive"))
    a('\t\t)')
    a('\t)')
    bbox = (min(rect[0], rect[2]), min(rect[1], rect[3]),
            max(rect[0], rect[2]), max(rect[1], rect[3]))
    # 防 JLC 库将来装入同名符号后被自建定义静默遮蔽 (遮蔽即 ERC 语义漂移)
    assert name not in LIBS, name
    LIBS[name] = dict(text="\n".join(body), pins=pins, bbox=bbox)

_mk_custom("WAFER-XH2_54-2PZZ", "J", "XH 2P",
           FP_XH2P,
           [("1", "1", -5.08, 1.27, 0), ("2", "2", -5.08, -1.27, 0)],
           (-2.54, 3.81, 2.54, -3.81))

_mk_custom("XGZP6897D", "U", "XGZP6897D",
           "LOCAL:XGZP6897D-SOP8-W7.96-P2.54",
           [("1", "NC", -7.62, 3.81, 0), ("2", "VDD", -7.62, 1.27, 0),
            ("3", "NC", -7.62, -1.27, 0), ("4", "NC", -7.62, -3.81, 0),
            ("5", "NC", 7.62, -3.81, 180), ("6", "SDA", 7.62, -1.27, 180),
            ("7", "SCL", 7.62, 1.27, 180), ("8", "GND", 7.62, 3.81, 180)],
           (-5.08, 5.08, 5.08, -5.08))

# ---------------------------------------------------------------- 器件清单

P = lambda ref, sym, val, fp, lcsc, x, y, nets: dict(
    ref=ref, sym=sym, val=val, fp=fp, lcsc=lcsc, x=x, y=y, nets=nets)

R1k, R10k, R22, R330, R47K, R51K, R324K, R100K = (
    "0603WAF1001T5E", "0603WAF1002T5E", "0603WAF220JT5E", "0603WAF3300T5E",
    "0603WAF4701T5E", "0603WAF5101T5E", "0603WAF3241T5E", "RC0603FR-07100KL")
C100N, C1U, C10U, C100U, C2N2, C22P = (
    "CL10B104KB8NNNC", "CL10A105KB8NNNC", "CL31A106KBHNNNE",
    "CL31A107MQHNNNE", "CL10C222JB8NNNC", "CL10C220JB8NNNC")
FR = "JLC-MCP:R0603"; FC0603 = "Capacitor_SMD:C_0603_1608Metric"; FC1206 = "JLC-MCP:C1206"

LCSC = {R1k: "C21190", R10k: "C25804", R22: "C23345", R330: "C23138", R47K: "C23162",
        R51K: "C23186", R324K: "C22994", R100K: "C14675", C100N: "C1591", C1U: "C15849",
        C10U: "C13585", C100U: "C15008", C2N2: "C33353", C22P: "C1653"}


VALVE_GPIO = ["IO4", "IO5", "IO6", "IO7", "IO10", "IO11", "IO12", "IO21"]

PARTS = []
# ---- 电源输入 USB-C 5A (左上, P1.1: DC005 移除, 仅 USB-C 供电) ----------------
# J1 VBUS 直挂 +5V (5A 路径, 无 OR 二极管); CC1/CC2 各 5.1k Rd 下拉 (免 PD 取 5V/3A)
# D1(DC_IN OR) 随 DC005 一并移除; D2(调试口 OR) 保留 — 反向阻断, 仅调试单线供电时馈 +5V
PARTS += [
    P("J1", "TYPE-C-31-M-12", "USB-C PWR", "JLC-MCP:USB-C_SMD-TYPE-C-31-M-12_1",
      "C165948", 50, 55,
      # JLC 库符号引脚名=封装焊盘名 (A1B12/A4B9/B1A12/B4A9 合并焊盘 + EH1-4 屏蔽腿);
      # DP/DN/SBU 本板不用 (电源口), NC 悬空
      {"A1B12": "GND", "A4B9": "+5V", "B1A12": "GND", "B4A9": "+5V",
       "A5": "P5_CC1", "B5": "P5_CC2",
       "B8": None, "B7": None, "A6": None, "A7": None, "B6": None, "A8": None,
       "1": "GND", "2": "GND", "3": "GND", "4": "GND"}),
    P("C17", C10U, "10uF", FC1206, LCSC[C10U], 75, 55, {"1": "+5V", "2": "GND"}),
    P("R63", R51K, "5.1k", FR, LCSC[R51K], 100, 42, {"1": "P5_CC1", "2": "GND"}),
    P("R64", R51K, "5.1k", FR, LCSC[R51K], 100, 68, {"1": "P5_CC2", "2": "GND"}),
    P("U7", "USBLC6-2SC6", "USBLC6-2SC6",
      "JLC-MCP:SOT-23-6_L2.9-W1.6-P0.95-LS2.8-BL", "C7519", 135, 55,
      {"1": "P5_CC1", "2": "GND", "3": "P5_CC2", "4": "P5_CC2", "5": "+5V",
       "6": "P5_CC1"}),
    P("D2", "SS34_C8678", "SS34", "JLC-MCP:SMA_L4.3-W2.6-LS5.2-RD", "C8678", 100, 130,
      {"2": "USB_VBUS", "1": "+5V"}),
    P("J2", "TYPE-C_6P", "USB-C", "JLC-MCP:TYPE-C-SMD_TYPE-C-6P_1", "C456012", 50, 130,
      {"A12": "GND", "A9": "USB_VBUS", "A5": "CC1", "B5": "CC2", "B9": "USB_VBUS",
       "B12": "GND", "7": "GND"}),
    P("R1", R51K, "5.1k", FR, LCSC[R51K], 25, 120, {"1": "CC1", "2": "GND"}),
    P("R2", R51K, "5.1k", FR, LCSC[R51K], 25, 150, {"1": "CC2", "2": "GND"}),
]
# ---- TPS54331 Buck (中上) ---------------------------------------------------
PARTS += [
    P("U3", "TPS54331DR", "TPS54331DR", "JLC-MCP:SOIC-8_L5.0-W4.0-P1.27-LS6.0-BL", "C9865",
      185, 70,
      {"1": "BOOT", "2": "+5V", "3": "BUCK_EN", "4": "BUCK_SS", "5": "FB", "6": "COMP",
       "7": "GND", "8": "PH"}),
    P("R3", R100K, "100k", FR, LCSC[R100K], 150, 40, {"1": "+5V", "2": "BUCK_EN"}),
    P("C6", C100N, "100nF", FC0603, LCSC[C100N], 125, 60, {"1": "BUCK_SS", "2": "GND"}),
    P("C1", C10U, "10uF", FC1206, LCSC[C10U], 125, 90, {"1": "+5V", "2": "GND"}),
    P("C2", C100N, "100nF", FC0603, LCSC[C100N], 150, 90, {"1": "+5V", "2": "GND"}),
    P("R6", R10k, "10k", FR, LCSC[R10k], 100, 90, {"1": "COMP", "2": "COMP_RC"}),
    P("C3", C2N2, "2.2nF", FC0603, LCSC[C2N2], 85, 120, {"1": "COMP_RC", "2": "GND"}),
    P("C4", C22P, "22pF", FC0603, LCSC[C22P], 130, 112, {"1": "COMP_RC", "2": "GND"}),
    P("L1", "CDRH103RNP-6R8NC-B", "6.8uH", "JLC-MCP:IND-SMD_L10.2-W10.0", "C167253",
      240, 55, {"1": "PH", "2": "+3V3"}),
    P("D3", "SS34_C8678", "SS34", "JLC-MCP:SMA_L4.3-W2.6-LS5.2-RD", "C8678", 240, 100,
      {"2": "GND", "1": "PH"}),
    P("C5", C100N, "100nF", FC0603, LCSC[C100N], 265, 70, {"1": "BOOT", "2": "PH"}),
    P("R4", R10k, "10k", FR, LCSC[R10k], 290, 40, {"1": "+3V3", "2": "FB"}),
    P("R5", R324K, "3.24k", FR, LCSC[R324K], 290, 70, {"1": "FB", "2": "GND"}),
    P("C7", C100U, "100uF", FC1206, LCSC[C100U], 320, 40, {"1": "+3V3", "2": "GND"}),
    P("C8", C100U, "100uF", FC1206, LCSC[C100U], 320, 70, {"1": "+3V3", "2": "GND"}),
    P("C9", C10U, "10uF", FC1206, LCSC[C10U], 320, 100, {"1": "+3V3", "2": "GND"}),
    P("C10", C100N, "100nF", FC0603, LCSC[C100N], 320, 130, {"1": "+3V3", "2": "GND"}),
]
# ---- USB-UART CH340K + 自动下载 (右上) --------------------------------------
PARTS += [
    P("U5", "USBLC6-2SC6", "USBLC6-2SC6", "JLC-MCP:SOT-23-6_L2.9-W1.6-P0.95-LS2.8-BL",
      "C7519", 150, 130,
      {"1": "USB_DP", "2": "GND", "3": "USB_DN", "4": "USB_DN", "5": "USB_VBUS",
       "6": "USB_DP"}),
    P("R17", R22, "22R", FR, LCSC[R22], 120, 125, {"1": "USB_DP", "2": "USB_DP_CH"}),
    P("R18", R22, "22R", FR, LCSC[R22], 120, 155, {"1": "USB_DN", "2": "USB_DN_CH"}),
    P("U4", "CH340K", "CH340K", "JLC-MCP:ESOP-10_L4.9-W3.9-P1.00-LS6.2-BL-EP", "C968586",
      200, 130,
      {"1": "USB_DP_CH", "2": "USB_DN_CH", "3": "GND", "4": "DTR", "5": None,
       "6": "RTS", "7": "+3V3", "8": "CH_TX", "9": "CH_RX", "10": "+3V3", "11": "GND"}),
    P("C12", C100N, "100nF", FC0603, LCSC[C100N], 230, 100, {"1": "+3V3", "2": "GND"}),
    P("R10", R1k, "1k", FR, LCSC[R1k], 250, 90, {"1": "CH_TX", "2": "UART_RX"}),
    P("R11", R1k, "1k", FR, LCSC[R1k], 250, 115, {"1": "CH_RX", "2": "UART_TX"}),
    P("LED4", "LTST-C191KSKT", "TX", "JLC-MCP:LED0603-RD-YELLOW", "C125100", 285, 85,
      {"1": "+3V3", "2": "LED_TX_K"}),
    P("R25", R1k, "1k", FR, LCSC[R1k], 285, 110, {"1": "LED_TX_K", "2": "CH_TX"}),
    P("LED5", "LTST-C191KSKT", "RX", "JLC-MCP:LED0603-RD-YELLOW", "C125100", 315, 85,
      {"1": "+3V3", "2": "LED_RX_K"}),
    P("R26", R1k, "1k", FR, LCSC[R1k], 315, 110, {"1": "LED_RX_K", "2": "CH_RX"}),
    P("R19", R1k, "1k", FR, LCSC[R1k], 160, 175, {"1": "DTR", "2": "DTR_R"}),
    P("R20", R1k, "1k", FR, LCSC[R1k], 160, 205, {"1": "RTS", "2": "RTS_R"}),
    P("R21", R10k, "10k", FR, LCSC[R10k], 195, 175, {"1": "+3V3", "2": "DTR_R"}),
    P("R22", R10k, "10k", FR, LCSC[R10k], 195, 205, {"1": "+3V3", "2": "RTS_R"}),
    P("Q11", "SS8050_C181160", "SS8050", "JLC-MCP:SOT-23-3_L3.0-W1.3-P1.90-LS2.5-BR",
      "C181160", 230, 175, {"1": "DTR_R", "2": "GND", "3": "EN"}),
    P("Q12", "SS8050_C181160", "SS8050", "JLC-MCP:SOT-23-3_L3.0-W1.3-P1.90-LS2.5-BR",
      "C181160", 230, 205, {"1": "RTS_R", "2": "GND", "3": "BOOT"}),
]
# ---- ESP32-S3 主控 + strapping (左中) ---------------------------------------
# P1.1: 引脚 8/9/10/11 (IO15/16/17/18) → S/V/F 主阀 + 泵 驱动 (非 STRAP, 未占用)
ESP_NETS = {
    "1": "GND", "2": "+3V3", "3": "EN", "4": "IO4", "5": "IO5", "6": "IO6", "7": "IO7",
    "8": "IO15", "9": "IO16", "10": "IO17", "11": "IO18",
    "12": "I2C_SDA", "17": "I2C_SCL", "18": "IO10", "19": "IO11", "20": "IO12",
    "23": "IO21", "36": "UART_RX", "37": "UART_TX", "25": "IO48", "27": "BOOT",
    "15": "STRAP3", "26": "STRAP45", "16": "STRAP46", "21": "LED_USER", "22": "BTN_USER",
    "13": None, "14": None,
    "24": None, "28": None, "29": None, "30": None, "31": None, "32": None,
    "33": None, "34": None, "35": None, "38": None, "39": None,
    "40": "GND", "41": "GND",
}
PARTS += [
    P("U1", "ESP32-S3-WROOM-1_N16R8_", "ESP32-S3-WROOM-1-N16R8",
      "JLC-MCP:WIRELM-SMD_ESP32-S3-WROOM-1", "C2913202", 100, 260, ESP_NETS),
    P("R7", R10k, "10k", FR, LCSC[R10k], 50, 250, {"1": "+3V3", "2": "EN"}),
    P("C14", C1U, "1uF", FC0603, LCSC[C1U], 50, 285, {"1": "EN", "2": "GND"}),
    P("SW1", "ST-1185S", "RST", "JLC-MCP:SW-SMD_ST-1185S", "C589191", 50, 320,
      {"1": "EN", "2": "GND"}),
    P("R8", R47K, "4.7k", FR, LCSC[R47K], 130, 240, {"1": "+3V3", "2": "I2C_SDA"}),
    P("R9", R47K, "4.7k", FR, LCSC[R47K], 130, 270, {"1": "+3V3", "2": "I2C_SCL"}),
    P("SW2", "ST-1185S", "BOOT", "JLC-MCP:SW-SMD_ST-1185S", "C589191", 160, 250,
      {"1": "BOOT", "2": "GND"}),
    P("R12", R330, "330R", FR, LCSC[R330], 150, 300, {"1": "IO48", "2": "RGB_R"}),
    P("LED1", "XL-5050RGBC-WS2812B", "WS2812B",
      "JLC-MCP:LED-SMD_4P-L5.0-W5.0-BL_XL-5050RGBC", "C2843785", 195, 300,
      {"1": "+3V3", "2": None, "3": "GND", "4": "RGB_R"}),
    P("C13", C100N, "100nF", FC0603, LCSC[C100N], 235, 300, {"1": "+3V3", "2": "GND"}),
    P("R13", R10k, "10k", FR, LCSC[R10k], 50, 360, {"1": "+3V3", "2": "BOOT"}),
    P("R14", R10k, "10k", FR, LCSC[R10k], 80, 360, {"1": "+3V3", "2": "STRAP3"}),
    P("R15", R10k, "10k", FR, LCSC[R10k], 110, 360, {"1": "GND", "2": "STRAP45"}),
    P("R16", R10k, "10k", FR, LCSC[R10k], 140, 350, {"1": "+3V3", "2": "STRAP46"}),
    P("R27", R10k, "10k", FR, LCSC[R10k], 170, 360, {"1": "+3V3", "2": "BTN_USER"}),
    P("SW3", "ST-1185S", "USER", "JLC-MCP:SW-SMD_ST-1185S", "C589191", 205, 380,
      {"1": "BTN_USER", "2": "GND"}),
    P("LED2", "KT-0603R", "PWR", "JLC-MCP:LED-SMD_L1.6-W0.8-R-RD", "C2286", 235, 250,
      {"1": "+3V3", "2": "LED_PWR_K"}),
    P("R23", R1k, "1k", FR, LCSC[R1k], 235, 215, {"1": "LED_PWR_K", "2": "GND"}),
    P("LED3", "Blue_light_0603", "USER", "JLC-MCP:LED0603-RD", "C2288", 265, 250,
      {"1": "LED_USER", "2": "LED_USER_K"}),
    P("R24", R1k, "1k", FR, LCSC[R1k], 265, 215, {"1": "LED_USER_K", "2": "GND"}),
]
# ---- TCA9548A 五通道 I2C (右中) ----------------------------------------------
TCA_NETS = {
    "1": "GND", "2": "GND", "3": "TCA_RST",
    "4": "S1_SDA", "5": "S1_SCL", "6": "S2_SDA", "7": "S2_SCL",
    "8": "S3_SDA", "9": "S3_SCL", "10": "S4_SDA", "11": "S4_SCL",
    "12": "GND", "13": "S5_SDA", "14": "S5_SCL",
    "15": None, "16": None, "17": None, "18": None, "19": None, "20": None,
    "21": "GND", "22": "I2C_SCL", "23": "I2C_SDA", "24": "+3V3",
}
PARTS += [P("U2", "TCA9548APWR", "TCA9548APWR",
            "JLC-MCP:TSSOP-24_L7.8-W4.4-P0.65-LS6.4-BL", "C130026", 330, 260, TCA_NETS),
          P("R28", R10k, "10k", FR, LCSC[R10k], 260, 300, {"1": "+3V3", "2": "TCA_RST"}),
          P("C11", C100N, "100nF", FC0603, LCSC[C100N], 295, 300, {"1": "+3V3", "2": "GND"})]
for ch in range(5):
    yy = 175 + ch * 25
    PARTS.append(P(f"R{29+ch}", R10k, "10k", FR, LCSC[R10k], 220, yy,
                   {"1": "+3V3", "2": f"S{ch+1}_SDA"}))
    PARTS.append(P(f"R{34+ch}", R10k, "10k", FR, LCSC[R10k], 248, yy,
                   {"1": "+3V3", "2": f"S{ch+1}_SCL"}))
    PARTS.append(P(f"J{5+ch}", "WAFER-XH2_54-4PZZ", "XH-4P",
                   "JLC-MCP:CONN-TH_4P-P2.54_6173868", "C5359632", 400, 160 + ch * 30,
                   {"1": "+3V3", "2": "GND", "3": f"S{ch+1}_SDA", "4": f"S{ch+1}_SCL"}))
# ---- 8 路 AO3400 阀驱动 (底部) -------------------------------------------------
for i in range(8):
    x0 = 40 + i * 36
    PARTS += [
        P(f"R{39+i}", R1k, "1k", FR, LCSC[R1k], x0, 310,
          {"1": VALVE_GPIO[i], "2": f"GATE{i+1}"}),
        P(f"R{47+i}", R10k, "10k", FR, LCSC[R10k], x0, 335,
          {"1": f"GATE{i+1}", "2": "GND"}),
        P(f"Q{3+i}", "AO3400A", "AO3400A", "JLC-MCP:SOT-23-3_L2.9-W1.3-P1.90-LS2.4-BR",
          "C20917", x0, 365,
          {"1": f"GATE{i+1}", "2": "GND", "3": f"DRV{i+1}"}),
        P(f"D{4+i}", "SS14", "SS14", "JLC-MCP:SMA_L4.2-W2.6-LS5.0-RD_1", "C2480",
          x0 + 16, 365, {"2": f"DRV{i+1}", "1": "+5V"}),
        P(f"J{10+i}", "WAFER-XH2_54-2PZZ", "VALVE",
          FP_XH2P, LCSC_XH2P, x0, 400,
          {"1": "+5V", "2": f"DRV{i+1}"}),
    ]
# ---- P1.1: 3 路主阀 (S充气/V真空/F排气, 1f-β 公共歧管) + 1 路泵驱动 (底部右段) --
# 编号连续: 栅阻 R55-R58 / 下拉 R59-R62 / Q13-Q16 / D12-D15 / J20-J23
MAIN_CH = [("S", "IO15"), ("V", "IO16"), ("F", "IO17"), ("PUMP", "IO18")]
for k, (tag, gpio) in enumerate(MAIN_CH):
    x0 = 328 + k * 36
    PARTS += [
        P(f"R{55+k}", R1k, "1k", FR, LCSC[R1k], x0, 310,
          {"1": gpio, "2": f"GATE_{tag}"}),
        P(f"R{59+k}", R10k, "10k", FR, LCSC[R10k], x0, 335,
          {"1": f"GATE_{tag}", "2": "GND"}),
        P(f"Q{13+k}", "AO3400A", "AO3400A", "JLC-MCP:SOT-23-3_L2.9-W1.3-P1.90-LS2.4-BR",
          "C20917", x0, 365,
          {"1": f"GATE_{tag}", "2": "GND", "3": f"DRV_{tag}"}),
        P(f"D{12+k}", "SS14", "SS14", "JLC-MCP:SMA_L4.2-W2.6-LS5.0-RD_1", "C2480",
          x0 + 16, 365, {"2": f"DRV_{tag}", "1": "+5V"}),
        P(f"J{20+k}", "WAFER-XH2_54-2PZZ", "VALVE" if tag != "PUMP" else "PUMP",
          FP_XH2P, LCSC_XH2P, x0, 400,
          {"1": "+5V", "2": f"DRV_{tag}"}),
    ]
# ---- P1.1: U6 XGZP6897D 板载压力传感 (宽体 SOP-8, +3V3 域 I2C 直挂主控) --------
# LCSC 无 CFSensor 现货 (仅 JLC 扩展件 C99xxx 零库存无资料) → 淘宝件 (CFSensor
# 深圳闽芯店, 见 devices.json pneumatic_devices.sensor), 不入 JLC BOM; footprint
# 按 datasheet 手建 (LOCAL: 前缀, gen_pcb.py 内联生成): 排距 7.96 / 节距 2.54 /
# 焊盘 0.9×2.0 / 本体 10.6×7.6。
PARTS += [
    P("U6", "XGZP6897D", "XGZP6897D", "LOCAL:XGZP6897D-SOP8-W7.96-P2.54", "",
      # TODO(采购): 淘宝件 XGZP6897D100KPDPN (量程 -100~100kPa, I2C 0x6D) — 不入 JLC BOM
      185, 240, {"2": "+3V3", "6": "I2C_SDA", "7": "I2C_SCL", "8": "GND",
                 "1": None, "3": None, "4": None, "5": None}),
    P("C18", C100N, "100nF", FC0603, LCSC[C100N], 215, 240, {"1": "+3V3", "2": "GND"}),
]
PARTS += [
    P("C15", C100N, "100nF", FC0603, LCSC[C100N], 40, 160, {"1": "+5V", "2": "GND"}),
    P("C16", C100N, "100nF", FC0603, LCSC[C100N], 292, 160, {"1": "+5V", "2": "GND"}),
]
# ---- 调试排针 + 测试点 (右中/右下; P1.1 让位主阀通道列右移至此) -----------------
PARTS += [
    P("J18", "WAFER-XH2_54-4PZZ", "DEBUG-UART", "JLC-MCP:CONN-TH_4P-P2.54_6173868",
      "C5359632", 505, 160, {"1": "UART_TX", "2": "GND", "3": "UART_RX", "4": "+3V3"}),
    P("J19", "WAFER-XH2_54-4PZZ", "DEBUG-GPIO", "JLC-MCP:CONN-TH_4P-P2.54_6173868",
      "C5359632", 505, 200, {"1": "LED_USER", "2": "+3V3", "3": "GND", "4": "BTN_USER"}),
]
TP_NETS = ["+3V3", "+5V", "GND", "GND", "GND", "GND", "I2C_SDA", "I2C_SCL",
           "GATE1", "DRV1", "PH", "EN", "DRV_PUMP"]
for i, net in enumerate(TP_NETS):
    PARTS.append(P(f"TP{i+1}", "Mechanical:TestPoint", net,
                   "TestPoint:TestPoint_Pad_D1.0mm", "",
                   460 + (i % 4) * 32, 300 + (i // 4) * 26, {"1": net}))

# ---------------------------------------------------------------- 几何收集与防撞
STUBS, PINPTS = [], []
STUB_UNIT = {"L": (-1, 0), "R": (1, 0), "U": (0, -1), "D": (0, 1)}
# 电源符号安放点: (ref, pin, net, kind, elbow)
POWER_SPOTS = [
    ("Q11", "2", "GND", "gnd", None),
    ("U4", "11", "GND", "gnd", None),
    ("U1", "2", "+3V3", "rail", "U"),
    ("C17", "1", "+5V", "rail", None),   # P1.1: D1 移除, +5V 电源箭头挂输入电容
    ("L1", "1", "PH", "rail", None),
    # PWR_FLAG: power_out 引脚, 满足 ERC "电源网络须有驱动" (官方惯例)
    ("C7", "1", "+3V3", "flag", None),
    ("C1", "1", "+5V", "flag", None),
    ("D3", "1", "PH", "flag", None),
    ("C17", "2", "GND", "flag", None),
]

lib_used = {}

def add_sym_embed(name):
    if name in lib_used:
        return
    if name == "Mechanical:TestPoint":
        lib_used[name] = TP_DEF
    else:
        assert name in LIBS, f"symbol not found: {name}"
        lib_used[name] = LIBS[name]["text"].replace("(pin unspecified ", "(pin passive ")

def prepare_instance(pt, sym):
    ref, name = pt["ref"], pt["sym"]
    x, y = snap(pt["x"]), snap(pt["y"])
    nets = pt["nets"]
    if name == "Mechanical:TestPoint":
        pins = [dict(num="1", name="1", x=0.0, y=0.0, ang=0, etype="passive")]
        geod = dict(bbox=(-1.27, -1.27, 1.27, 1.27))
    else:
        pins = sym["pins"]
        geod = sym
    add_sym_embed(name)
    ps_pins = {ps[1] for ps in POWER_SPOTS if ps[0] == ref}
    row_ctr = {}   # 同方向引脚交替加长, 避免标签文字挤在同一行
    for pn in pins:
        net = nets.get(pn["num"], None)
        if net is None:
            continue
        px, py = x + pn["x"], y - pn["y"]
        d = pin_dir(geod, pn)
        PINPTS.append(dict(x=px, y=py, net=net))
        if pn["num"] in ps_pins:
            continue  # 电源位引脚由 POWER_SPOTS 引线接管
        STUBS.append(dict(x=px, y=py, d=d, ext=0, net=net))
    for ps_ref, ps_pin, ps_net, kind, elbow in POWER_SPOTS:
        if ps_ref != ref:
            continue
        pn = next(pp for pp in pins if pp["num"] == ps_pin)
        px, py = x + pn["x"], y - pn["y"]
        STUBS.append(dict(x=px, y=py, d=pin_dir(geod, pn), ext=5.08, net=ps_net,
                          pwr=(ps_net, kind, None), el=0))

PERP = {"L": (-1, 0), "R": (1, 0), "U": (0, -1), "D": (0, 1)}
# 拐肘方向: 竖直引线向左拐, 水平引线向上拐
ELBOW_DIR = {"U": "L", "D": "L", "L": "U", "R": "U"}

def stub_end(s):
    ux, uy = STUB_UNIT[s["d"]]
    L = 5.08 + s["ext"]
    ex, ey = s["x"] + ux * L, s["y"] + uy * L
    if s.get("el"):
        ed = s.get("eldir", ELBOW_PERP[s["d"]][0])
        px, py = STUB_UNIT[ed]
        ex, ey = ex + px * s["el"], ey + py * s["el"]
    return round(ex, 3), round(ey, 3)

def stub_path(s):
    """引线折线点列 [起点, 拐点?, 终点]"""
    ux, uy = STUB_UNIT[s["d"]]
    L = 5.08 + s["ext"]
    p1 = (round(s["x"] + ux * L, 3), round(s["y"] + uy * L, 3))
    end = stub_end(s)
    if s.get("el"):
        return [(round(s["x"], 3), round(s["y"], 3)), p1, end]
    return [(round(s["x"], 3), round(s["y"], 3)), end]

def _pt_on_seg(px, py, x1, y1, x2, y2):
    if min(x1, x2) - 0.01 > px or max(x1, x2) + 0.01 < px:
        return False
    if min(y1, y2) - 0.01 > py or max(y1, y2) + 0.01 < py:
        return False
    if abs(x2 - x1) < 0.01:
        return abs(px - x1) < 0.01
    if abs(y2 - y1) < 0.01:
        return abs(py - y1) < 0.01
    return False

def _segs_overlap(a1, a2, b1, b2):
    ax1, ay1 = a1; ax2, ay2 = a2; bx1, by1 = b1; bx2, by2 = b2
    if max(ax1, ax2) < min(bx1, bx2) - 0.01 or min(ax1, ax2) > max(bx1, bx2) + 0.01:
        return False
    if max(ay1, ay2) < min(by1, by2) - 0.01 or min(ay1, ay2) > max(by1, by2) + 0.01:
        return False
    d1 = (bx2-bx1)*(ay1-by1) - (by2-by1)*(ax1-bx1)
    d2 = (bx2-bx1)*(ay2-by1) - (by2-by1)*(ax2-bx1)
    d3 = (ax2-ax1)*(by1-ay1) - (ay2-ay1)*(bx1-ax1)
    d4 = (ax2-ax1)*(by2-ay1) - (ay2-ay1)*(bx2-ax1)
    return d1*d2 <= 0.01 and d3*d4 <= 0.01

def _verts_on_segs(pa, pb):
    """A 的任一顶点落在 B 的任一线段上(含交叉点)"""
    for vx, vy in pa:
        for k in range(len(pb) - 1):
            if _pt_on_seg(vx, vy, *pb[k], *pb[k+1]):
                return True
    return False

ELBOW_PERP = {"U": ("L", "R"), "D": ("L", "R"), "L": ("U", "D"), "R": ("U", "D")}

def _bump(s):
    # 克制策略: 先伸长(上限 10.16), 再小幅拐肘(上限 7.62), 之后放弃交给 ERC 警告
    if s["ext"] < 10.16:
        s["ext"] += 2.54
    elif s.get("el", 0) < 7.62:
        s["el"] = s.get("el", 0) + 2.54
        cur = s.get("eldir", ELBOW_PERP[s["d"]][0])
        pair = ELBOW_PERP[s["d"]]
        s["eldir"] = pair[1] if cur == pair[0] else pair[0]

def resolve_collisions():
    def collide(a, b):
        if a["net"] == b["net"]:
            return False
        pa, pb = stub_path(a), stub_path(b)
        if _verts_on_segs(pa, pb) or _verts_on_segs(pb, pa):
            return True
        for i in range(len(pa) - 1):
            for j in range(len(pb) - 1):
                if _segs_overlap(pa[i], pa[i+1], pb[j], pb[j+1]):
                    return True
        return False
    for rnd in range(40):
        hit = False
        for i in range(len(STUBS)):
            for j in range(i + 1, len(STUBS)):
                if collide(STUBS[i], STUBS[j]):
                    _bump(STUBS[i]); _bump(STUBS[j])
                    hit = True
        for s in STUBS:
            path = stub_path(s)
            for pp in PINPTS:
                if pp["net"] == s["net"]:
                    continue
                touched = False
                for k in range(len(path) - 1):
                    if _pt_on_seg(pp["x"], pp["y"], *path[k], *path[k+1]):
                        touched = True; break
                if touched:
                    _bump(s); hit = True
        if not hit:
            # 终扫: 不同网络端点不得重合(不受上限约束)
            fixed = True
            while fixed:
                fixed = False
                for i in range(len(STUBS)):
                    for j in range(i + 1, len(STUBS)):
                        if STUBS[i]["net"] != STUBS[j]["net"] and                            stub_end(STUBS[i]) == stub_end(STUBS[j]):
                            STUBS[j]["el"] = STUBS[j].get("el", 0) + 2.54
                            fixed = True
            print(f"[collisions] clean after {rnd} rounds")
            return
    print("[collisions] WARNING: unresolved after 40 rounds")

# ---------------------------------------------------------------- 输出
def inst_text(pt, sym):
    ref, name = pt["ref"], pt["sym"]
    x, y = snap(pt["x"]), snap(pt["y"])
    if name == "Mechanical:TestPoint":
        pins = [dict(num="1")]
        bb = (-1.27, -1.27, 1.27, 1.27)
    else:
        pins = sym["pins"]
        bb = sym["bbox"]
    h = bb[3] - bb[1]
    lid = "Mechanical:TestPoint" if name == "Mechanical:TestPoint" else "JLC-MCP:" + name
    s = []
    a = s.append
    a('\t(symbol')
    a(f'\t\t(lib_id "{lid}")')
    a(f'\t\t(at {fnum(x)} {fnum(y)} 0)')
    a('\t\t(unit 1)')
    a('\t\t(exclude_from_sim no)')
    a('\t\t(in_bom yes)')
    a('\t\t(on_board yes)')
    a('\t\t(dnp no)')
    a(f'\t\t(uuid "{U()}")')
    a(f'\t\t(property "Reference" "{ref}" (at {fnum(x)} {fnum(y - h/2 - 2.54)} 0)')
    a('\t\t\t(effects (font (size 1.27 1.27)) (justify bottom)))')
    a(f'\t\t(property "Value" "{pt["val"]}" (at {fnum(x)} {fnum(y + h/2 + 2.54)} 0)')
    a('\t\t\t(effects (font (size 1.27 1.27)) (justify top)))')
    a(f'\t\t(property "Footprint" "{pt["fp"]}" (at {fnum(x)} {fnum(y)} 0)')
    a('\t\t\t(hide yes)')
    a('\t\t\t(effects (font (size 1.27 1.27))))')
    a(f'\t\t(property "Datasheet" "" (at {fnum(x)} {fnum(y)} 0)')
    a('\t\t\t(hide yes)')
    a('\t\t\t(effects (font (size 1.27 1.27))))')
    a(f'\t\t(property "Description" "" (at {fnum(x)} {fnum(y)} 0)')
    a('\t\t\t(hide yes)')
    a('\t\t\t(effects (font (size 1.27 1.27))))')
    if pt["lcsc"]:
        a(f'\t\t(property "LCSC" "{pt["lcsc"]}" (at {fnum(x)} {fnum(y)} 0)')
        a('\t\t\t(hide yes)')
        a('\t\t\t(effects (font (size 1.27 1.27))))')
    for pn in pins:
        a(f'\t\t(pin "{pn["num"]}" (uuid "{U()}"))')
    a('\t\t(instances')
    a(f'\t\t\t(project "{PROJ}"')
    a(f'\t\t\t\t(path "/{ROOT_UUID}"')
    a(f'\t\t\t\t\t(reference "{ref}")')
    a('\t\t\t\t\t(unit 1)')
    a('\t\t\t\t)')
    a('\t\t\t)')
    a('\t\t)')
    a('\t)')
    return "".join(s)

def pwr_inst_text(x, y, net, kind, pref):
    dy = 3.5 if kind == "gnd" else -3.5
    lid = "power:PWR_FLAG" if kind == "flag" else f"power:{net}"
    val = "PWR_FLAG" if kind == "flag" else net
    b = []
    ab = b.append
    ab('\t(symbol')
    ab(f'\t\t(lib_id "{lid}")')
    ab(f'\t\t(at {fnum(x)} {fnum(y)} 0)')
    ab('\t\t(unit 1)')
    ab('\t\t(exclude_from_sim no)')
    ab('\t\t(in_bom yes)')
    ab('\t\t(on_board yes)')
    ab('\t\t(dnp no)')
    ab(f'\t\t(uuid "{U()}")')
    ab(f'\t\t(property "Reference" "{pref}" (at {fnum(x)} {fnum(y + dy)} 0)')
    ab('\t\t\t(hide yes)')
    ab('\t\t\t(effects (font (size 1.27 1.27))))')
    ab(f'\t\t(property "Value" "{val}" (at {fnum(x)} {fnum(y + dy*9/7)} 0)')
    ab('\t\t\t(effects (font (size 1.27 1.27))))')
    ab(f'\t\t(property "Footprint" "" (at {fnum(x)} {fnum(y)} 0)')
    ab('\t\t\t(hide yes)')
    ab('\t\t\t(effects (font (size 1.27 1.27))))')
    ab(f'\t\t(property "Datasheet" "" (at {fnum(x)} {fnum(y)} 0)')
    ab('\t\t\t(hide yes)')
    ab('\t\t\t(effects (font (size 1.27 1.27))))')
    ab(f'\t\t(pin "1" (uuid "{U()}"))')
    ab('\t\t(instances')
    ab(f'\t\t\t(project "{PROJ}"')
    ab(f'\t\t\t\t(path "/{ROOT_UUID}"')
    ab(f'\t\t\t\t\t(reference "{pref}")')
    ab('\t\t\t\t\t(unit 1)')
    ab('\t\t\t\t)')
    ab('\t\t\t)')
    ab('\t\t)')
    ab('\t)')
    return "".join(b)

NOTES = [
    (30, 22, "USB-C 5A 供电 (J1: Rd 5.1k x2 + U7 ESD) + TPS54331 Buck"),
    (340, 22, "USB-UART CH340K + SS8050 自动下载"),
    (30, 140, "ESP32-S3-WROOM-1-N16R8 主控 + Strapping"),
    (250, 140, "TCA9548A 五通道 I2C 传感链 + U6 XGZP6897D 板载压力传感"),
    (30, 280, "12 路 AO3400A 驱动: 8x 阀 + S/V/F 主阀 + 泵 (1f-β, XH-2P 插座 J10-J23)"),
    (380, 280, "调试排针 + 测试点"),
]

_n = int(os.environ.get("BISECT", "0"))
if _n:
    PARTS = PARTS[:_n]

items = []
if os.environ.get("LIBSONLY"):
    for pt in PARTS:
        if pt["sym"] != "Mechanical:TestPoint":
            add_sym_embed(pt["sym"])
    for net, kind in [("+3V3", "rail"), ("+5V", "rail"), ("GND", "gnd"), ("PH", "rail")]:
        lib_used[f"__pwrsym_{net}"] = power_sym_def(net, kind)
else:
    for pt in PARTS:
        prepare_instance(pt, LIBS.get(pt["sym"]))
    for pt in PARTS:
        items.append(inst_text(pt, LIBS.get(pt["sym"])))
    pwr_n = 0
    flg_n = 0
    # 同点汇合的多根引线 -> junction
    from collections import Counter
    ends = Counter()
    for s in STUBS:
        ex, ey = stub_end(s)
        ends[(ex, ey)] += 1
    for (jx, jy), cnt in ends.items():
        if cnt >= 2:
            items.append(f'\t(junction (at {fnum(jx)} {fnum(jy)}) (diameter 1.016) '
                         f'(color 0 0 0 0) (uuid "{U()}"))')
    for s in STUBS:
        path = stub_path(s)
        for k in range(len(path) - 1):
            items.append('\t(wire (pts '
                         f'(xy {fnum(path[k][0])} {fnum(path[k][1])}) '
                         f'(xy {fnum(path[k+1][0])} {fnum(path[k+1][1])})) '
                         f'(stroke (width 0) (type default)) (uuid "{U()}"))')
        ex, ey = stub_end(s)
        if "pwr" in s:
            net, kind, elbow = s["pwr"]
            if kind == "flag":
                flg_n += 1
                pref = f"#FLG{flg_n:02d}"
            else:
                pwr_n += 1
                pref = f"#PWR{pwr_n:02d}"
            if elbow == "U":
                ex2, ey2 = ex, ey - 7.62
                items.append('\t(wire (pts '
                             f'(xy {fnum(ex)} {fnum(ey)}) (xy {fnum(ex2)} {fnum(ey2)})) '
                             f'(stroke (width 0) (type default)) (uuid "{U()}"))')
                ex, ey = ex2, ey2
            lib_used[f"__pwrsym_{kind}_{net}"] = power_sym_def(net, kind)
            items.append(pwr_inst_text(ex, ey, net, kind, pref))
            if kind == "flag":
                # PWR_FLAG 不命名网络 —— 必须同时挂标签把它并入目标网络
                just = {"L": "right", "R": "left", "U": "left bottom", "D": "left top"}[s["d"]]
                items.append(f'\t(label "{net}" (at {fnum(ex)} {fnum(ey)} 0) '
                             f'(effects (font (size 1.27 1.27)) (justify {just})))')
        else:
            just = {"L": "right", "R": "left", "U": "left bottom", "D": "left top"}[s["d"]]
            items.append(f'\t(label "{s["net"]}" (at {fnum(ex)} {fnum(ey)} 0) '
                         f'(effects (font (size 1.27 1.27)) (justify {just})))')
    # NC 标记
    for pt in PARTS:
        if pt["sym"] == "Mechanical:TestPoint":
            continue
        for pn in LIBS[pt["sym"]]["pins"]:
            if pt["nets"].get(pn["num"], "__m__") is None:
                px = snap(pt["x"]) + pn["x"]
                py = snap(pt["y"]) - pn["y"]
                items.append(f'\t(no_connect (at {fnum(px)} {fnum(py)}) (uuid "{U()}"))')
    for nx, ny, txt in NOTES:
        items.append(f'\t(text "{txt}" (exclude_from_sim no) (at {fnum(nx)} {fnum(ny)} 0) '
                     f'(effects (font (size 2.54 2.54)) (justify left bottom)) (uuid "{U()}"))')

# 装配 lib_symbols
seen, uniq = set(), []
pwrsyms = [v for k, v in lib_used.items() if k.startswith("__pwrsym_")]
for b in pwrsyms:
    nm = re.search(r'\(symbol "power:([^"]+)"', b).group(1)
    if nm not in seen:
        seen.add(nm); uniq.append(b)
for key, b in list(lib_used.items()):
    if key.startswith("__pwrsym_"):
        continue
    m = re.search(r'\(symbol "([^"]+)"', b)
    orig = m.group(1)
    if orig in seen:
        continue
    if not (orig.startswith("power:") or orig.startswith("Mechanical:")):
        b = b.replace(f'(symbol "{orig}"', f'(symbol "JLC-MCP:{orig}"', 1)
    seen.add(orig)
    uniq.append(b)

sch = ["(kicad_sch",
       f'\t(version {SCH_VERSION})',
       '\t(generator "eeschema")',
       '\t(generator_version "9.0")',
       f'\t(uuid "{ROOT_UUID}")',
       '\t(paper "A2")',
       '\t(title_block',
       '\t\t(title "FLOWIO-CN P1 升级大脑")',
       '\t\t(date "2026-10-03")',
       '\t\t(rev "1.1")',
       '\t\t(company "FLOWIO-CN")',
       '\t\t(comment 1 "ESP32-S3 + 11x valve drv + pump + XGZP + USB-C power")',
       '\t)',
       '\t(lib_symbols',
       "\n".join(uniq),
       '\t)',
       "\n".join(items),
       '\t(sheet_instances',
       '\t\t(path "/"',
       '\t\t\t(page "1")',
       '\t\t)',
       '\t)',
       ")"]

from pathlib import Path as _P
_P(os.path.join(HWDIR, "flowio-p1.kicad_sch")).write_bytes("\n".join(sch).encode("utf-8"))
print("OK -> %s" % os.path.join(HWDIR, "flowio-p1.kicad_sch"))
print(f"parts={len(PARTS)} embedded_symbols={len(uniq)} stubs={len(STUBS)}")
