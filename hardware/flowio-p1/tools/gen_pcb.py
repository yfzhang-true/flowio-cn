# -*- coding: utf-8 -*-
"""FLOWIO-CN P1 PCB 生成器
从 gen_sch.py 的 PARTS 单一真值源生成 4 层板。
布局: 80×70mm · 天线朝板顶边(板外净空) · 左下电源 · 右上USB · 底部8路驱动
用法: "E:/Program Files/KiCad/10.0/bin/python.exe" gen_pcb.py
"""
import os, re, sys
import pcbnew

MM = pcbnew.FromMM
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

# ---- 从 gen_sch.py 提取 PARTS(共享真值源) ----
_src = open(os.path.join(HERE, "gen_sch.py"), encoding="utf-8").read()
_seg = _src[_src.index("PARTS = []"):_src.index("# ---------------------------------------------------------------- 几何收集与防撞")]
_pre = _src[_src.index("P = lambda"):_src.index("PARTS = []")]
_ns = {}
exec(_pre + _seg, _ns)
PARTS = _ns["PARTS"]
BY_REF = {p["ref"]: p for p in PARTS}

JLC = r"C:/Users/yuefe/Documents/KiCad/9.0/3rdparty/jlc_mcp/footprints/JLC-MCP.pretty"
STD = r"E:/Program Files/KiCad/10.0/share/kicad/footprints"

# 封装库路由: fp 字段 "LIB:NAME" -> 目录
def load_fp(fp):
    if fp.startswith("JLC-MCP:"):
        return pcbnew.FootprintLoad(JLC, fp.split(":")[1])
    if fp.startswith("Capacitor_SMD:"):
        return pcbnew.FootprintLoad(os.path.join(STD, "Capacitor_SMD.pretty"), fp.split(":")[1])
    if fp.startswith("TestPoint:"):
        return pcbnew.FootprintLoad(os.path.join(STD, "TestPoint.pretty"), fp.split(":")[1])
    if fp.startswith("Connector:"):
        return pcbnew.FootprintLoad(os.path.join(STD, "Connector.pretty"), fp.split(":")[1])
    raise ValueError(fp)

board = pcbnew.BOARD()
board.SetFileName(os.path.join(HERE, "..", "flowio-p1.kicad_pcb"))

# ---- 层叠 4 层 ----
board.SetLayerName(pcbnew.In1_Cu, "GND")
board.SetLayerName(pcbnew.In2_Cu, "PWR")
board.SetEnabledLayers(pcbnew.LSET.AllCuMask(4))

# ---- 设计规则 ----
ds = board.GetDesignSettings()
ds.m_TrackMinWidth, ds.m_ViasMinSize, ds.m_ViasMinDrill = MM(0.2), MM(0.6), MM(0.3)
ds.m_MinClearance = MM(0.2)
ds.m_TrackWidthList = pcbnew.intVector([int(MM(w)) for w in (0.25, 0.5, 0.8, 1.2, 2.0)])
ds.SetCopperLayerCount(4)
try:
    nc = board.GetNetClasses().GetDefault()
    nc.SetTrackWidth(int(MM(0.25)))
    nc.SetViaDiameter(int(MM(0.6)))
    nc.SetViaDrill(int(MM(0.3)))
    nc.SetClearance(int(MM(0.2)))
except AttributeError:
    pass  # 默认网络类由设计规则字段覆盖

# ---- 板框 90×75 (P1 直角, 简单可靠) ----
W, H = MM(90), MM(75)
def add_seg(x1, y1, x2, y2, layer=pcbnew.Edge_Cuts):
    s = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(pcbnew.VECTOR2I(int(x1), int(y1)))
    s.SetEnd(pcbnew.VECTOR2I(int(x2), int(y2)))
    s.SetLayer(layer)
    board.Add(s)
add_seg(0, 0, W, 0)
add_seg(W, 0, W, H)
add_seg(W, H, 0, H)
add_seg(0, H, 0, 0)

# ---- 网络 ----
NETCODES = {}
def netcode(name):
    if name not in NETCODES:
        ni = pcbnew.NETINFO_ITEM(board, name)
        board.Add(ni)
        NETCODES[name] = ni.GetNetCode()   # Add 后读回真实网络码
    return NETCODES[name]
for pt in PARTS:
    for net in pt["nets"].values():
        if net:
            netcode(net)

# ---- 器件放置表 (ref: x_mm, y_mm, 旋转°) ----
PLACE = {
    # ===== ESP32 主控(天线朝顶边, 净空 x20.5-35.5/y<6.4) =====
    "U1": (28, 16.5, 0),
    "C9": (43, 9, 0), "C10": (43, 14, 0),
    "SW1": (9, 8.5, 0), "SW2": (13.5, 12.5, 0), "C14": (6.5, 13, 0), "R7": (14, 19, 0),
    "R13": (24, 31, 0), "R14": (28.5, 31, 0),
    "R15": (34, 31, 0), "R16": (39, 31, 0),
    "R8": (50, 27, 0), "R9": (54.5, 27, 0),
    "LED1": (50, 14, 0), "R12": (50, 20.5, 90), "C13": (55.5, 17.5, 0),
    "R27": (46.5, 34.5, 90), "SW3": (46.5, 51, 0),
    "LED2": (58.5, 29, 90), "R23": (58.5, 33.5, 90),
    "LED3": (48.5, 30, 90), "R24": (48.5, 35, 90),
    # ===== 顶边: 5号传感器 + 调试排针 =====
    "J9": (46, 4, 0), "J18": (59.5, 4, 0), "J19": (73, 4, 0),
    # ===== USB 右上 =====
    "J2": (86, 6, 270),
    "R1": (78.5, 10, 90), "R2": (78.5, 14, 90),
    "U5": (74.5, 12, 0), "R17": (70, 11, 90), "R18": (70, 15, 90),
    "U4": (75, 21.5, 0), "C12": (80, 25.5, 0),
    "R10": (78.5, 31, 90), "R11": (78.5, 36, 90),
    "R19": (62, 22, 0), "R20": (66.5, 22, 0),
    "R21": (62, 26, 0), "R22": (66.5, 26, 0),
    "Q11": (69.5, 23.5, 0), "Q12": (69.5, 28.5, 0),
    "LED4": (69.5, 34, 90), "R25": (69.5, 39, 90),
    "LED5": (69.5, 44, 90), "R26": (69.5, 48.5, 90),
    # ===== 传感连接器 右边 =====
    "J5": (86.5, 22, 270), "J6": (86.5, 32.5, 270),
    "J7": (86.5, 46, 270), "J8": (5, 46, 90),
    # ===== 电源 左列竖排 =====
    "J1": (5.5, 27, 270),
    "C17": (17, 24, 90), "R3": (21, 28, 90),
    "D1": (23.5, 33.5, 0), "C1": (30, 33.5, 0),
    "D2": (24, 38.5, 0), "C2": (30, 38.5, 0),
    "U3": (25, 45, 0),
    "C6": (18.5, 45, 90), "R6": (18.5, 50, 90),
    "C5": (31.8, 41.5, 90),
    "L1": (39.5, 43, 0), "D3": (48.5, 43, 0),
    "R4": (51.5, 39.5, 90), "R5": (51.5, 44.5, 90),
    "C3": (23, 50.5, 0), "C4": (27.5, 50.5, 0),
    "C7": (56, 40, 90), "C8": (56, 45.5, 90),
    # ===== TCA + 上拉梯 =====
    "U2": (74, 44, 0), "C11": (79.5, 50, 0), "R28": (56.5, 57.5, 90),
    "C15": (34.5, 51.5, 90), "C16": (78.5, 56.5, 90),
}
for i in range(5):
    PLACE[f"R{29+i}"] = (62, 30 + i * 4.8, 90)
    PLACE[f"R{34+i}"] = (66, 30 + i * 4.8, 90)
# ===== ch1-8 全部底部单排 =====
BOT_X = [6.5 + i * 11 for i in range(8)]
for i in range(8):
    x = BOT_X[i]
    PLACE[f"R{39+i}"] = (x - 2.4, 55.5, 90)
    PLACE[f"R{47+i}"] = (x + 2.4, 55.5, 90)
    PLACE[f"Q{3+i}"] = (x - 2.4, 60.5, 0)
    PLACE[f"D{4+i}"] = (x + 2.4, 60.5, 180)
    PLACE[f"J{10+i}"] = (x, 68.5, 180)
# ===== 测试点 =====
for i, (tx, ty) in enumerate([(58.5, 21.5), (14, 33), (34, 57.5), (45, 57.5), (81.5, 57.5),
                              (48.5, 47.5), (43.5, 31), (47.5, 31), (12, 63.5), (23.5, 59.5),
                              (40, 50.5), (2.8, 11)]):
    PLACE[f"TP{i+1}"] = (tx, ty, 0)

# ---- 放置封装并赋网络 ----
for pt in PARTS:
    ref = pt["ref"]
    if ref not in PLACE:
        raise SystemExit(f"未定义放置坐标: {ref}")
    x, y, rot = PLACE[ref]
    fp = load_fp(pt["fp"])
    fp.SetReference(ref)
    fp.SetValue(pt["val"])
    fp.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))
    fp.SetOrientation(pcbnew.EDA_ANGLE(rot, pcbnew.DEGREES_T))
    board.Add(fp)   # 先上板, 网络码才有效
    for pad in fp.Pads():
        nm = pad.GetPadName()
        net = pt["nets"].get(str(nm), None)
        if net:
            pad.SetNetCode(netcode(net))

# ---- 安装孔: 顶两角 + 中部两侧 ----
for hx, hy in [(4, 4), (86, 13), (3, 37), (77, 62)]:
    try:
        mh = pcbnew.FootprintLoad(os.path.join(STD, "MountingHole.pretty"),
                                  "MountingHole_3.2mm_M3")
        mh.SetReference(f"H{'ABCD'[(hx>40)*2+(hy>20)]}")
        mh.SetPosition(pcbnew.VECTOR2I(MM(hx), MM(hy)))
        board.Add(mh)
    except Exception as e:
        print("mounting hole fail:", e)

# ---- 天线净空区(模块顶部 9mm, 所有铜层禁铜/禁走线/禁过孔) ----
ko = pcbnew.ZONE(board)
ko.SetIsRuleArea(True)
ko.SetLayerSet(pcbnew.LSET.AllCuMask())
ko.SetDoNotAllowZoneFills(True)
ko.SetDoNotAllowTracks(True)
ko.SetDoNotAllowVias(True)
ol = ko.Outline()
ol.NewOutline()
for cx, cy in [(20.5, 0), (35.5, 0), (35.5, 6.4), (20.5, 6.4)]:
    ol.Append(int(MM(cx)), int(MM(cy)))
board.Add(ko)

pcbnew.SaveBoard(os.path.join(HERE, "..", "flowio-p1.kicad_pcb"), board)
print("PCB 骨架已生成:", len(board.GetFootprints()), "个封装")
