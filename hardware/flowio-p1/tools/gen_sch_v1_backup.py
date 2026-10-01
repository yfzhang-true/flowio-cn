# -*- coding: utf-8 -*-
"""FLOWIO-CN P1 原理图生成器
单一真值源: PARTS 表同时供 gen_sch.py(原理图) 与 gen_pcb.py(PCB) 使用。
连接方式: 每个引脚一根短引线 + 网络标号(平铺标签式); 电源网络辅以电源符号。
用法: "E:/Program Files/KiCad/10.0/bin/python.exe" gen_sch.py
"""
import re, os, glob, uuid as _uuid

LIBDIR = r"C:/Users/yuefe/Documents/KiCad/9.0/3rdparty/jlc_mcp/symbols"
OUT    = os.path.join(os.path.dirname(__file__), "..", "flowio-p1.kicad_sch")
ROOT_UUID = "7f1a2c34-0000-4000-8000-5a6b7c8d9e0f"
PROJ = "flowio-p1"
SCH_VERSION = "20250114"

def U(): return str(_uuid.uuid4())

# ---------------------------------------------------------------- 符号库解析
def load_libs():
    libs = {}
    for f in glob.glob(os.path.join(LIBDIR, "*.kicad_sym")):
        txt = open(f, encoding="utf-8").read()
        for m in re.finditer(r'\n\t\(symbol "([^"]+)"\n', txt):
            name = m.group(1)
            # 括号配平扫描: 块在深度归零处结束
            depth, i, start = 0, txt.index("(", m.start()), m.start()
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
                pins.append(dict(num=num, name=nm, x=float(x), y=float(y), ang=int(ang), etype=et))
            xs, ys = [], []
            for rx, ry in re.findall(r'\(xy ([-\d.]+) ([-\d.]+)', blk):
                xs.append(float(rx)); ys.append(float(ry))
            for cx, cy, cr in re.findall(r'\(circle\s*\(center ([-\d.]+) ([-\d.]+)\)\s*\(radius ([-\d.]+)', blk):
                xs += [float(cx)-float(cr), float(cx)+float(cr)]; ys += [float(cy)-float(cr), float(cy)+float(cr)]
            bbox = (min(xs), min(ys), max(xs), max(ys)) if xs else (-5.08, -5.08, 5.08, 5.08)
            libs[name] = dict(text=blk.rstrip(), pins=pins, bbox=bbox)
    return libs

LIBS = load_libs()

def snap(v):
    """对齐 1.27mm 连接网格"""
    return round(v / 1.27) * 1.27

def pin_dir(sym, p):
    """引脚引出方向: 相对符号几何包围盒向外。"""
    x0, y0, x1, y1 = sym["bbox"]
    px, py = p["x"], -p["y"]          # 显示坐标系(y 向下)
    if px <= x0 + 0.05: return "L"
    if px >= x1 - 0.05: return "R"
    if py <= y0 + 0.05: return "U"
    if py >= y1 - 0.05: return "D"
    return {0: "L", 180: "R", 90: "D", 270: "U"}.get(p.get("ang", 0), "L")

# ---------------------------------------------------------------- 电源符号(手写)
def power_sym_def(net, kind):
    """官方 power 符号结构(逐字对照 v20250114 模板): 引脚位于原点, 名称 ~。"""
    if kind == "gnd":
        gfx = """			(symbol "{n}_0_1"
				(polyline
					(pts
						(xy 0 0) (xy 0 -1.27) (xy 1.27 -1.27) (xy 0 -2.54) (xy -1.27 -1.27) (xy 0 -1.27)
					)
					(stroke
						(width 0)
						(type default)
					)
					(fill
						(type none)
					)
				)
			)""".replace("{n}", net)
        pangle = 270
    else:
        gfx = """			(symbol "{n}_0_1"
				(polyline
					(pts
						(xy -0.762 1.27) (xy 0 2.54)
					)
					(stroke
						(width 0)
						(type default)
					)
					(fill
						(type none)
					)
				)
				(polyline
					(pts
						(xy 0 2.54) (xy 0.762 1.27)
					)
					(stroke
						(width 0)
						(type default)
					)
					(fill
						(type none)
					)
				)
				(polyline
					(pts
						(xy 0 0) (xy 0 2.54)
					)
					(stroke
						(width 0)
						(type default)
					)
					(fill
						(type none)
					)
				)
			)""".replace("{n}", net)
        pangle = 90
    return """	(symbol "power:{n}"
		(power)
		(pin_numbers
			(hide yes)
		)
		(pin_names
			(offset 0)
			(hide yes)
		)
		(exclude_from_sim no)
		(in_bom yes)
		(on_board yes)
		(property "Reference" "#PWR"
			(at 0 -3.81 0)
			(effects
				(font
					(size 1.27 1.27)
				)
				(hide yes)
			)
		)
		(property "Value" "{n}"
			(at 0 3.556 0)
			(effects
				(font
					(size 1.27 1.27)
				)
			)
		)
		(property "Footprint" ""
			(at 0 0 0)
			(effects
				(font
					(size 1.27 1.27)
				)
				(hide yes)
			)
		)
		(property "Datasheet" ""
			(at 0 0 0)
			(effects
				(font
					(size 1.27 1.27)
				)
				(hide yes)
			)
		)
		(property "ki_keywords" "global power"
			(at 0 0 0)
			(effects
				(font
					(size 1.27 1.27)
				)
				(hide yes)
			)
		)
{g}
		(symbol "{n}_1_1"
			(pin power_in line
				(at 0 0 {pa})
				(length 0)
				(name "~"
					(effects
						(font
							(size 1.27 1.27)
						)
					)
				)
				(number "1"
					(effects
						(font
							(size 1.27 1.27)
						)
					)
				)
			)
		)
		(embedded_fonts no)
	)""".replace("{n}", net).replace("{g}", gfx).replace("{pa}", str(pangle))

TP_DEF = '''	(symbol "Mechanical:TestPoint"
		(pin_numbers
			(hide yes)
		)
		(pin_names
			(offset 1.016)
		)
		(exclude_from_sim no)
		(in_bom yes)
		(on_board yes)
		(property "Reference" "TP"
			(at 0 -3.81 0)
			(effects
				(font
					(size 1.27 1.27)
				)
			)
		)
		(property "Value" "TestPoint"
			(at 0 3.81 0)
			(effects
				(font
					(size 1.27 1.27)
				)
			)
		)
		(property "Footprint" "TestPoint:TestPoint_Pad_D1.0mm"
			(at 0 0 0)
			(hide yes)
			(effects
				(font
					(size 1.27 1.27)
				)
			)
		)
		(property "Datasheet" ""
			(at 0 0 0)
			(hide yes)
			(effects
				(font
					(size 1.27 1.27)
				)
			)
		)
		(symbol "TestPoint_0_1"
			(circle
				(center 0 0)
				(radius 1.27)
				(stroke
					(width 0.254)
					(type default)
				)
				(fill
					(type background)
				)
			)
		)
		(symbol "TestPoint_1_1"
			(pin passive line
				(at 0 0 270)
				(length 0)
				(name "1"
					(effects
						(font
							(size 1.27 1.27)
						)
					)
				)
				(number "1"
					(effects
						(font
							(size 1.27 1.27)
						)
					)
				)
			)
		)
	)'''

# ---------------------------------------------------------------- 器件清单
# (ref, 符号, 值, 封装, LCSC, x, y, {引脚号: 网络}  None=NC)
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
# ---- 电源输入 + Diode-OR --------------------------------------------------
PARTS += [
    P("J1", "DC005_C431533", "DC-005", "JLC-MCP:DC-IN-TH_DC005", "C431533", 50, 52,
      {"1": "DC_IN", "2": "GND", "3": None}),
    P("D1", "SS34_C8678", "SS34", "JLC-MCP:SMA_L4.3-W2.6-LS5.2-RD", "C8678", 95, 52,
      {"2": "DC_IN", "1": "+5V"}),
    P("D2", "SS34_C8678", "SS34", "JLC-MCP:SMA_L4.3-W2.6-LS5.2-RD", "C8678", 95, 92,
      {"2": "USB_VBUS", "1": "+5V"}),
    P("J2", "TYPE-C_6P", "USB-C", "JLC-MCP:TYPE-C-SMD_TYPE-C-6P_1", "C456012", 50, 100,
      {"A12": "GND", "A9": "USB_VBUS", "A5": "CC1", "B5": "CC2", "B9": "USB_VBUS",
       "B12": "GND", "EH": "GND"}),
    P("R1", R51K, "5.1k", FR, LCSC[R51K], 27, 94, {"1": "CC1", "2": "GND"}),
    P("R2", R51K, "5.1k", FR, LCSC[R51K], 27, 108, {"1": "CC2", "2": "GND"}),
]
# ---- TPS54331 Buck ---------------------------------------------------------
PARTS += [
    P("U3", "TPS54331DR", "TPS54331DR", "JLC-MCP:SOIC-8_L5.0-W4.0-P1.27-LS6.0-BL", "C9865",
      175, 60,
      {"1": "BOOT", "2": "+5V", "3": "BUCK_EN", "4": "BUCK_SS", "5": "FB", "6": "COMP",
       "7": "GND", "8": "PH"}),
    P("L1", "CDRH103RNP-6R8NC-B", "6.8uH", "JLC-MCP:IND-SMD_L10.2-W10.0", "C167253",
      220, 45, {"1": "PH", "2": "+3V3"}),
    P("D3", "SS34_C8678", "SS34", "JLC-MCP:SMA_L4.3-W2.6-LS5.2-RD", "C8678", 220, 80,
      {"2": "GND", "1": "PH"}),
    P("R3", R100K, "100k", FR, LCSC[R100K], 140, 40, {"1": "+5V", "2": "BUCK_EN"}),
    P("C5", C100N, "100nF", FC0603, LCSC[C100N], 245, 60, {"1": "BOOT", "2": "PH"}),
    P("C6", C100N, "100nF", FC0603, LCSC[C100N], 130, 78, {"1": "BUCK_SS", "2": "GND"}),
    P("R6", R10k, "10k", FR, LCSC[R10k], 118, 100, {"1": "COMP", "2": "COMP_RC"}),
    P("C3", C2N2, "2.2nF", FC0603, LCSC[C2N2], 140, 108, {"1": "COMP_RC", "2": "GND"}),
    P("C4", C22P, "22pF", FC0603, LCSC[C22P], 160, 108, {"1": "COMP_RC", "2": "GND"}),
    P("C1", C10U, "10uF", FC1206, LCSC[C10U], 140, 90, {"1": "+5V", "2": "GND"}),
    P("C2", C100N, "100nF", FC0603, LCSC[C100N], 160, 90, {"1": "+5V", "2": "GND"}),
    P("C17", C10U, "10uF", FC1206, LCSC[C10U], 74, 60, {"1": "+5V", "2": "GND"}),
    P("R4", R10k, "10k", FR, LCSC[R10k], 250, 40, {"1": "+3V3", "2": "FB"}),
    P("R5", R324K, "3.24k", FR, LCSC[R324K], 250, 62, {"1": "FB", "2": "GND"}),
    P("C7", C100U, "100uF", FC1206, LCSC[C100U], 268, 38, {"1": "+3V3", "2": "GND"}),
    P("C8", C100U, "100uF", FC1206, LCSC[C100U], 268, 60, {"1": "+3V3", "2": "GND"}),
    P("C9", C10U, "10uF", FC1206, LCSC[C10U], 268, 82, {"1": "+3V3", "2": "GND"}),
    P("C10", C100N, "100nF", FC0603, LCSC[C100N], 268, 100, {"1": "+3V3", "2": "GND"}),
]
# ---- USB-UART CH340K + 自动下载 -------------------------------------------
PARTS += [
    P("U5", "USBLC6-2SC6", "USBLC6-2SC6", "JLC-MCP:SOT-23-6_L2.9-W1.6-P0.95-LS2.8-BL",
      "C7519", 355, 52,
      {"1": "USB_DP", "2": "GND", "3": "USB_DN", "4": "USB_DN", "5": "USB_VBUS",
       "6": "USB_DP"}),
    P("R17", R22, "22R", FR, LCSC[R22], 388, 44, {"1": "USB_DP", "2": "USB_DP_CH"}),
    P("R18", R22, "22R", FR, LCSC[R22], 388, 62, {"1": "USB_DN", "2": "USB_DN_CH"}),
    P("U4", "CH340K", "CH340K", "JLC-MCP:ESOP-10_L4.9-W3.9-P1.00-LS6.2-BL-EP", "C968586",
      425, 55,
      {"1": "USB_DP_CH", "2": "USB_DN_CH", "3": "GND", "4": "DTR", "5": None,
       "6": "RTS", "7": "+3V3", "8": "CH_TX", "9": "CH_RX", "10": "+3V3", "11": "GND"}),
    P("C12", C100N, "100nF", FC0603, LCSC[C100N], 400, 78, {"1": "+3V3", "2": "GND"}),
    P("R19", R1k, "1k", FR, LCSC[R1k], 400, 100, {"1": "DTR", "2": "DTR_R"}),
    P("R20", R1k, "1k", FR, LCSC[R1k], 400, 118, {"1": "RTS", "2": "RTS_R"}),
    P("R21", R10k, "10k", FR, LCSC[R10k], 425, 100, {"1": "+3V3", "2": "DTR_R"}),
    P("R22", R10k, "10k", FR, LCSC[R10k], 425, 118, {"1": "+3V3", "2": "RTS_R"}),
    P("Q11", "SS8050_C181160", "SS8050", "JLC-MCP:SOT-23-3_L3.0-W1.3-P1.90-LS2.5-BR",
      "C181160", 452, 100, {"1": "DTR_R", "2": "GND", "3": "EN"}),
    P("Q12", "SS8050_C181160", "SS8050", "JLC-MCP:SOT-23-3_L3.0-W1.3-P1.90-LS2.5-BR",
      "C181160", 452, 118, {"1": "RTS_R", "2": "GND", "3": "BOOT"}),
    P("R10", R1k, "1k", FR, LCSC[R1k], 480, 44, {"1": "CH_TX", "2": "UART_RX"}),
    P("R11", R1k, "1k", FR, LCSC[R1k], 480, 62, {"1": "CH_RX", "2": "UART_TX"}),
    P("LED4", "LTST-C191KSKT", "TX", "JLC-MCP:LED0603-RD-YELLOW", "C125100", 515, 44,
      {"1": "+3V3", "2": "LED_TX_K"}),
    P("R25", R1k, "1k", FR, LCSC[R1k], 515, 60, {"1": "LED_TX_K", "2": "CH_TX"}),
    P("LED5", "LTST-C191KSKT", "RX", "JLC-MCP:LED0603-RD-YELLOW", "C125100", 540, 44,
      {"1": "+3V3", "2": "LED_RX_K"}),
    P("R26", R1k, "1k", FR, LCSC[R1k], 540, 60, {"1": "LED_RX_K", "2": "CH_RX"}),
]
# ---- ESP32-S3 主控 + strapping --------------------------------------------
ESP_NETS = {
    "1": "GND", "2": "+3V3", "3": "EN", "4": "IO4", "5": "IO5", "6": "IO6", "7": "IO7",
    "12": "I2C_SDA", "17": "I2C_SCL", "18": "IO10", "19": "IO11", "20": "IO12", "23": "IO21",
    "36": "UART_RX", "37": "UART_TX", "25": "IO48", "27": "BOOT", "15": "STRAP3",
    "26": "STRAP45", "16": "STRAP46", "21": "LED_USER", "22": "BTN_USER",
    "8": None, "9": None, "10": None, "11": None, "13": None, "14": None,
    "24": None, "28": None, "29": None, "30": None, "31": None, "32": None,
    "33": None, "34": None, "35": None, "38": None, "39": None,
    "40": "GND", "41": "GND",
}
PARTS += [
    P("U1", "ESP32-S3-WROOM-1_N16R8_", "ESP32-S3-WROOM-1-N16R8",
      "JLC-MCP:WIRELM-SMD_ESP32-S3-WROOM-1", "C2913202", 120, 195, ESP_NETS),
    P("R7", R10k, "10k", FR, LCSC[R10k], 62, 180, {"1": "+3V3", "2": "EN"}),
    P("C14", C1U, "1uF", FC0603, LCSC[C1U], 40, 196, {"1": "EN", "2": "GND"}),
    P("SW1", "ST-1185S", "RST", "JLC-MCP:SW-SMD_ST-1185S", "C589191", 62, 214,
      {"1": "EN", "2": "GND"}),
    P("R8", R47K, "4.7k", FR, LCSC[R47K], 168, 168, {"1": "+3V3", "2": "I2C_SDA"}),
    P("R9", R47K, "4.7k", FR, LCSC[R47K], 186, 168, {"1": "+3V3", "2": "I2C_SCL"}),
    P("SW2", "ST-1185S", "BOOT", "JLC-MCP:SW-SMD_ST-1185S", "C589191", 168, 190,
      {"1": "BOOT", "2": "GND"}),
    P("R12", R330, "330R", FR, LCSC[R330], 168, 214, {"1": "IO48", "2": "RGB_R"}),
    P("LED1", "XL-5050RGBC-WS2812B", "WS2812B",
      "JLC-MCP:LED-SMD_4P-L5.0-W5.0-BL_XL-5050RGBC", "C2843785", 195, 214,
      {"1": "+3V3", "2": None, "3": "GND", "4": "RGB_R"}),
    P("C13", C100N, "100nF", FC0603, LCSC[C100N], 195, 196, {"1": "+3V3", "2": "GND"}),
    P("R13", R10k, "10k", FR, LCSC[R10k], 62, 262, {"1": "+3V3", "2": "BOOT"}),
    P("R14", R10k, "10k", FR, LCSC[R10k], 88, 262, {"1": "+3V3", "2": "STRAP3"}),
    P("R15", R10k, "10k", FR, LCSC[R10k], 114, 262, {"1": "GND", "2": "STRAP45"}),
    P("R16", R10k, "10k", FR, LCSC[R10k], 140, 262, {"1": "+3V3", "2": "STRAP46"}),
    P("R27", R10k, "10k", FR, LCSC[R10k], 168, 262, {"1": "+3V3", "2": "BTN_USER"}),
    P("SW3", "ST-1185S", "USER", "JLC-MCP:SW-SMD_ST-1185S", "C589191", 196, 262,
      {"1": "BTN_USER", "2": "GND"}),
    P("LED2", "KT-0603R", "PWR", "JLC-MCP:LED-SMD_L1.6-W0.8-R-RD", "C2286", 224, 190,
      {"1": "+3V3", "2": "LED_PWR_K"}),
    P("R23", R1k, "1k", FR, LCSC[R1k], 224, 208, {"1": "LED_PWR_K", "2": "GND"}),
    P("LED3", "Blue_light_0603", "USER", "JLC-MCP:LED0603-RD", "C2288", 224, 232,
      {"1": "LED_USER", "2": "LED_USER_K"}),
    P("R24", R1k, "1k", FR, LCSC[R1k], 224, 250, {"1": "LED_USER_K", "2": "GND"}),
]
# ---- TCA9548A 五通道 I2C ---------------------------------------------------
TCA_NETS = {
    "1": "GND", "2": "GND", "3": "TCA_RST",
    "4": "S1_SDA", "5": "S1_SCL", "6": "S2_SDA", "7": "S2_SCL",
    "8": "S3_SDA", "9": "S3_SCL", "10": "S4_SDA", "11": "S4_SCL",
    "12": "GND", "13": "S5_SDA", "14": "S5_SCL",
    "15": None, "16": None, "17": None, "18": None, "19": None, "20": None,
    "21": "GND", "22": "I2C_SCL", "23": "I2C_SDA", "24": "+3V3",
}
PARTS += [P("U2", "TCA9548APWR", "TCA9548APWR",
            "JLC-MCP:TSSOP-24_L7.8-W4.4-P0.65-LS6.4-BL", "C130026", 330, 215, TCA_NETS),
          P("R28", R10k, "10k", FR, LCSC[R10k], 300, 190, {"1": "+3V3", "2": "TCA_RST"}),
          P("C11", C100N, "100nF", FC0603, LCSC[C100N], 330, 190, {"1": "+3V3", "2": "GND"})]
for ch in range(5):
    yy = 158 + ch * 14
    PARTS.append(P(f"R{29+ch}", R10k, "10k", FR, LCSC[R10k], 268, yy,
                   {"1": "+3V3", "2": f"S{ch+1}_SDA"}))
    PARTS.append(P(f"R{34+ch}", R10k, "10k", FR, LCSC[R10k], 284, yy,
                   {"1": "+3V3", "2": f"S{ch+1}_SCL"}))
    PARTS.append(P(f"J{5+ch}", "WAFER-XH2_54-4PZZ", "XH-4P",
                   "JLC-MCP:CONN-TH_4P-P2.54_6173868", "C5359632", 425, 152 + ch * 20,
                   {"1": "+3V3", "2": "GND", "3": f"S{ch+1}_SDA", "4": f"S{ch+1}_SCL"}))
# ---- 8 路 AO3400 阀驱动 ----------------------------------------------------
for i in range(8):
    x0 = 42 + i * 36
    PARTS += [
        P(f"R{39+i}", R1k, "1k", FR, LCSC[R1k], x0, 300,
          {"1": VALVE_GPIO[i], "2": f"GATE{i+1}"}),
        P(f"R{47+i}", R10k, "10k", FR, LCSC[R10k], x0, 318,
          {"1": f"GATE{i+1}", "2": "GND"}),
        P(f"Q{3+i}", "AO3400A", "AO3400A", "JLC-MCP:SOT-23-3_L2.9-W1.3-P1.90-LS2.4-BR",
          "C20917", x0, 348,
          {"1": f"GATE{i+1}", "2": "GND", "3": f"DRV{i+1}"}),
        P(f"D{4+i}", "SS14", "SS14", "JLC-MCP:SMA_L4.2-W2.6-LS5.0-RD_1", "C2480",
          x0 + 14, 348, {"2": f"DRV{i+1}", "1": "+5V"}),
        P(f"J{10+i}", "WJ500V-5_08-2P-14-00A", "VALVE",
          "JLC-MCP:CONN-TH_2P-P5.00_WJ500V-5.08-2P", "C8465", x0, 385,
          {"1": "+5V", "2": f"DRV{i+1}"}),
    ]
PARTS += [
    P("C15", C100N, "100nF", FC0603, LCSC[C100N], 42, 365, {"1": "+5V", "2": "GND"}),
    P("C16", C100N, "100nF", FC0603, LCSC[C100N], 290, 365, {"1": "+5V", "2": "GND"}),
]
# ---- 调试排针 + 测试点 ------------------------------------------------------
PARTS += [
    P("J18", "WAFER-XH2_54-4PZZ", "DEBUG-UART", "JLC-MCP:CONN-TH_4P-P2.54_6173868",
      "C5359632", 395, 300, {"1": "UART_TX", "2": "GND", "3": "UART_RX", "4": "+3V3"}),
    P("J19", "WAFER-XH2_54-4PZZ", "DEBUG-GPIO", "JLC-MCP:CONN-TH_4P-P2.54_6173868",
      "C5359632", 395, 330, {"1": "LED_USER", "2": "+3V3", "3": "GND", "4": "BTN_USER"}),
]
TP_NETS = ["+3V3", "+5V", "GND", "GND", "GND", "GND", "I2C_SDA", "I2C_SCL",
           "GATE1", "DRV1", "PH", "EN"]
for i, net in enumerate(TP_NETS):
    PARTS.append(P(f"TP{i+1}", "Mechanical:TestPoint", net,
                   "TestPoint:TestPoint_Pad_D1.0mm", "",
                   460 + (i % 4) * 32, 300 + (i // 4) * 26, {"1": net}))

# ---------------------------------------------------------------- 生成
items = []          # wire / net_label / no_connect / symbol / power / text
lib_used = {}       # libname -> text (embedded)

def add_sym_embed(name):
    key = name
    if key not in lib_used:
        if name == "Mechanical:TestPoint":
            lib_used[key] = TP_DEF
        else:
            assert name in LIBS, f"symbol not found: {name}"
            lib_used[key] = LIBS[name]["text"].replace("(pin unspecified ", "(pin passive ")

def fnum(v):
    s = f"{v:.3f}".rstrip("0").rstrip(".")
    return s if s else "0"

# 电源符号安放点: (ref, pin, net, kind, elbow_dir) elbow_dir: 拐向
POWER_SPOTS = [
    ("Q11", "2", "GND", "gnd", None),       # CH340K EP 已有 GND;此处再补一个视觉地
    ("U4", "11", "GND", "gnd", None),       # EP 向下
    ("U1", "2", "+3V3", "rail", "U"),       # ESP32 3V3 左侧引脚, 左出后上拐
    ("D1", "1", "+5V", "rail", None),       # SS34 K 极向上
    ("L1", "1", "PH", "rail", None),        # 电感 pin1 向上
]
pwr_idx = 0

def emit_instance(pt, sym):
    global pwr_idx
    ref, name, x, y, nets = pt["ref"], pt["sym"], snap(pt["x"]), snap(pt["y"]), pt["nets"]
    add_sym_embed(name)
    symdef = TP_DEF if name == "Mechanical:TestPoint" else None
    if name == "Mechanical:TestPoint":
        pins = [dict(num="1", name="1", x=0.0, y=0.0, etype="passive")]
        bbox = (-1.27, -1.27, 1.27, 1.27)
    else:
        pins = sym["pins"]; bbox = sym["bbox"]
    h = bbox[3] - bbox[1]
    ref_y = y - h / 2 - 2.54
    val_y = y + h / 2 + 2.54
    s = []
    s.append('\t(symbol')
    lid = "Mechanical:TestPoint" if name == "Mechanical:TestPoint" else ("JLC-MCP:" + name)
    s.append(f'		(lib_id "{lid}")')
    s.append(f'\t\t(at {fnum(x)} {fnum(y)} 0)')
    s.append('\t\t(unit 1)')
    s.append('\t\t(exclude_from_sim no)')
    s.append('\t\t(in_bom yes)')
    s.append('\t\t(on_board yes)')
    s.append('\t\t(dnp no)')
    u = U()
    s.append(f'\t\t(uuid "{u}")')
    s.append(f'\t\t(property "Reference" "{ref}" (at {fnum(x)} {fnum(ref_y)} 0)')
    s.append('\t\t\t(effects (font (size 1.27 1.27)) (justify bottom)))')
    s.append(f'\t\t(property "Value" "{pt["val"]}" (at {fnum(x)} {fnum(val_y)} 0)')
    s.append('\t\t\t(effects (font (size 1.27 1.27)) (justify top)))')
    s.append(f'\t\t(property "Footprint" "{pt["fp"]}" (at {fnum(x)} {fnum(y)} 0)')
    s.append('\t\t\t(hide yes)')
    s.append('\t\t\t(effects (font (size 1.27 1.27))))')
    s.append(f'\t\t(property "Datasheet" "" (at {fnum(x)} {fnum(y)} 0)')
    s.append('\t\t\t(hide yes)')
    s.append('\t\t\t(effects (font (size 1.27 1.27))))')
    s.append(f'\t\t(property "Description" "" (at {fnum(x)} {fnum(y)} 0)')
    s.append('\t\t\t(hide yes)')
    s.append('\t\t\t(effects (font (size 1.27 1.27))))')
    if pt["lcsc"]:
        s.append(f'\t\t(property "LCSC" "{pt["lcsc"]}" (at {fnum(x)} {fnum(y)} 0)')
        s.append('\t\t\t(hide yes)')
        s.append('\t\t\t(effects (font (size 1.27 1.27))))')
    for p in pins:
        s.append(f'\t\t(pin "{p["num"]}" (uuid "{U()}"))')
    s.append('\t\t(instances')
    s.append(f'\t\t\t(project "{PROJ}"')
    s.append(f'\t\t\t\t(path "/{ROOT_UUID}"')
    s.append(f'\t\t\t\t\t(reference "{ref}")')
    s.append('\t\t\t\t\t(unit 1)')
    s.append('\t\t\t\t)')
    s.append('\t\t\t)')
    s.append('\t\t)')
    s.append('\t)')
    items.append("".join(s))

    # 引线 + 标号 / NC
    for p in pins:
        net = nets.get(p["num"], None)
        px, py = x + p["x"], y - p["y"]
        if net is None:
            items.append(f'\t(no_connect (at {fnum(px)} {fnum(py)}) (uuid "{U()}"))')
            continue
        d = pin_dir(sym if name != "Mechanical:TestPoint" else dict(bbox=bbox), p)
        dx, dy = {"L": (-5.08, 0), "R": (5.08, 0), "U": (0, -5.08), "D": (0, 5.08)}[d]
        ex, ey = px + dx, py + dy
        items.append('\t(wire (pts '
                     f'(xy {fnum(px)} {fnum(py)}) (xy {fnum(ex)} {fnum(ey)})) '
                     f'(stroke (width 0) (type default)) (uuid "{U()}"))')
        just = {"L": "right", "R": "left", "U": "left bottom", "D": "left top"}[d]
        items.append(f'\t(label "{net}" (at {fnum(ex)} {fnum(ey)} 0) '
                     f'(effects (font (size 1.27 1.27)) (justify {just})))')

    # 电源符号安放
    for ps_ref, ps_pin, ps_net, kind, elbow in POWER_SPOTS:
        if ps_ref != ref:
            continue
        p = next(pp for pp in pins if pp["num"] == ps_pin)
        px, py = x + p["x"], y - p["y"]
        net = nets.get(ps_pin)
        assert net == ps_net, f"power spot mismatch {ref}.{ps_pin}: {net} != {ps_net}"
        d = pin_dir(sym, p)
        dx, dy = {"L": (-5.08, 0), "R": (5.08, 0), "U": (0, -5.08), "D": (0, 5.08)}[d]
        ex, ey = px + dx, py + dy
        if elbow == "U":
            ex2, ey2 = ex, ey - 7.62
            items.append('\t(wire (pts '
                         f'(xy {fnum(ex)} {fnum(ey)}) (xy {fnum(ex2)} {fnum(ey2)})) '
                         f'(stroke (width 0) (type default)) (uuid "{U()}"))')
            ex, ey = ex2, ey2
        # 电源符号引脚在原点 -> 放在引线端点; gnd 图形在下方, rail 图形在上方
        pwr_idx += 1
        lib_used.setdefault(f"__pwr_{ps_net}_{kind}",
                            power_sym_def(ps_net.replace("+", "P_"), kind))
        libname = f"power:{ps_net.replace('+', 'P_')}" if False else None
        # 电源符号的 lib 名称: +3V3 -> P_3V3 不行——网络名必须精确!
        # 正确做法: 符号名 = 网络名原样
        libkey = f"power:{ps_net}"
        lib_used.setdefault(f"SYM:{libkey}", power_sym_def(ps_net, kind))
        s = []
        s.append('\t(symbol')
        s.append(f'\t\t(lib_id "{libkey}")')
        s.append(f'\t\t(at {fnum(ex)} {fnum(ey)} 0)')
        s.append('\t\t(unit 1)')
        s.append('\t\t(exclude_from_sim no)')
        s.append('\t\t(in_bom yes)')
        s.append('\t\t(on_board yes)')
        s.append('\t\t(dnp no)')
        s.append(f'\t\t(uuid "{U()}")')
        s.append(f'\t\t(property "Reference" "#PWR{pwr_idx:02d}" (at {fnum(ex)} {fnum(ey + (3.5 if kind=="gnd" else -3.5))} 0)')
        s.append('\t\t\t(effects (font (size 1.27 1.27)) (hide yes)))')
        s.append(f'\t\t(property "Value" "{ps_net}" (at {fnum(ex)} {fnum(ey + (4.5 if kind=="gnd" else -4.5))} 0)')
        s.append('\t\t\t(effects (font (size 1.27 1.27))))')
        s.append(f'\t\t(property "Footprint" "" (at {fnum(ex)} {fnum(ey)} 0)')
        s.append('\t\t\t(effects (font (size 1.27 1.27)) (hide yes)))')
        s.append(f'\t\t(property "Datasheet" "" (at {fnum(ex)} {fnum(ey)} 0)')
        s.append('\t\t\t(effects (font (size 1.27 1.27)) (hide yes)))')
        s.append('\t\t(pin "1" (uuid "{U()}"))')
        s.append('\t\t(instances')
        s.append(f'\t\t\t(project "{PROJ}"')
        s.append(f'\t\t\t\t(path "/{ROOT_UUID}"')
        s.append(f'\t\t\t\t\t(reference "#PWR{pwr_idx:02d}")')
        s.append('\t\t\t\t\t(unit 1)')
        s.append('\t\t\t\t)')
        s.append('\t\t\t)')
        s.append('\t\t)')
        s.append('\t)')
        items.append("".join(s).replace('"{U()}"', f'"{U()}"'))

# 区域标题
NOTES = [
    (30, 22, "FLOWIO-CN P1 电源输入 + TPS54331 Buck"),
    (340, 22, "USB-UART CH340K + SS8050 自动下载"),
    (30, 140, "ESP32-S3-WROOM-1-N16R8 主控 + Strapping"),
    (250, 140, "TCA9548A 五通道 I2C 传感链"),
    (30, 280, "8 路 AO3400A 阀/泵驱动 (IO4/5/6/7/10/11/12/21)"),
    (380, 280, "调试排针 + 测试点"),
]
for nx, ny, txt in NOTES:
    items.append(f'\t(text "{txt}" (exclude_from_sim no) (at {fnum(nx)} {fnum(ny)} 0) '
                 f'(effects (font (size 2.54 2.54)) (justify left bottom)) (uuid "{U()}"))')

_n = int(os.environ.get("BISECT", "0"))
if _n:
    PARTS = PARTS[:_n]
    print(f"[BISECT] only {_n} parts")

if os.environ.get("LIBSONLY"):
    for pt in PARTS:
        if pt["sym"] != "Mechanical:TestPoint":
            add_sym_embed(pt["sym"])
    for net, kind in [("+3V3", "rail"), ("+5V", "rail"), ("GND", "gnd"), ("PH", "rail")]:
        lib_used.setdefault(f"SYM:power:{net}", power_sym_def(net, kind))
    PARTS = []
    items.clear()
    print("[LIBSONLY] no items")
else:
    for pt in PARTS:
        sym = LIBS.get(pt["sym"])
        if sym is None and pt["sym"] != "Mechanical:TestPoint":
            raise SystemExit(f"符号缺失: {pt['sym']}")
        emit_instance(pt, sym)

# 装配 lib_symbols
lib_sym_blocks = []
for k, v in lib_used.items():
    if k.startswith("SYM:"):
        lib_sym_blocks.append(v)          # 电源符号 def 已带两页签缩进
    elif k == "Mechanical:TestPoint":
        lib_sym_blocks.append(v)
    else:
        lib_sym_blocks.append(v)
# 去重嵌入文本
seen, uniq = set(), []
for b in lib_sym_blocks:
    key = re.search(r'\(symbol "([^"]+)"', b).group(1)
    if key not in seen:
        if not (key.startswith("power:") or key.startswith("Mechanical:")):
            b = b.replace(f'(symbol "{key}"', f'(symbol "JLC-MCP:{key}"', 1)
        seen.add(key); uniq.append(b)

sch = []
sch.append("(kicad_sch")
sch.append(f'\t(version {SCH_VERSION})')
sch.append('\t(generator "eeschema")')
sch.append('\t(generator_version "9.0")')
sch.append(f'\t(uuid "{ROOT_UUID}")')
sch.append('\t(paper "A2")')
sch.append('\t(title_block')
sch.append('\t\t(title "FLOWIO-CN P1 升级大脑")')
sch.append('\t\t(date "2026-10-01")')
sch.append('\t\t(rev "1.0")')
sch.append('\t\t(company "FLOWIO-CN")')
sch.append('\t\t(comment 1 "ESP32-S3 + TCA9548A + 8x AO3400 + TPS54331 + CH340K")')
sch.append('\t)')
sch.append('\t(lib_symbols')
sch.append("\n".join(uniq))
sch.append('\t)')
sch.append("\n".join(items))
sch.append('\t(sheet_instances')
sch.append('\t\t(path "/"')
sch.append('\t\t\t(page "1")')
sch.append('\t\t)')
sch.append('\t)')
sch.append(")")

out = os.path.abspath(OUT)
with open(out, "w", encoding="utf-8", newline="\n") as f:
    f.write("\n".join(sch))
print(f"OK -> {out}")
print(f"parts={len(PARTS)} embedded_symbols={len(uniq)}")
