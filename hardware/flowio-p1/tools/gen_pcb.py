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

# ---- 板框 80×70 (圆角 R2 由 4 线+4 弧) ----
W, H, R = MM(80), MM(70), MM(2)
def add_seg(x1, y1, x2, y2, layer=pcbnew.Edge_Cuts):
    s = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(pcbnew.VECTOR2I(int(x1), int(y1)))
    s.SetEnd(pcbnew.VECTOR2I(int(x2), int(y2)))
    s.SetLayer(layer)
    board.Add(s)
def add_arc(cx, cy, r, a1, a2):
    import math
    a = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_ARC)
    a.SetCenter(pcbnew.VECTOR2I(int(cx), int(cy)))
    sx = cx + r * math.cos(math.radians(a1))
    sy = cy + r * math.sin(math.radians(a1))
    ex = cx + r * math.cos(math.radians(a2))
    ey = cy + r * math.sin(math.radians(a2))
    a.SetStart(pcbnew.VECTOR2I(int(sx), int(sy)))
    a.SetEnd(pcbnew.VECTOR2I(int(ex), int(ey)))
    a.SetLayer(pcbnew.Edge_Cuts)
    board.Add(a)
add_seg(R, 0, W - R, 0)
add_arc(W - R, R, R, 0, 90)
add_seg(W, R, W, H - R)
add_arc(W - R, H - R, R, 90, 180)
add_seg(W - R, H, R, H)
add_arc(R, H - R, R, 180, 270)
add_seg(0, H - R, 0, R)
add_arc(R, R, R, 270, 360)

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
    # ===== ESP32 主控(天线朝顶边, 净空 x18.5-33.5/y<6.4) =====
    "U1": (26, 16.5, 0),
    "C9": (40, 9, 0), "C10": (40, 14, 0),
    "SW1": (7, 8, 0), "SW2": (13, 8, 0), "C14": (7, 13.5, 0), "R7": (7, 18.5, 0),
    "R13": (17, 34, 90), "R14": (23, 34, 90),
    "R15": (29, 34, 90), "R16": (35, 34, 90),
    "R8": (44, 26, 0), "R9": (48, 26, 0),
    "LED1": (46, 14, 0), "R12": (46, 20.5, 90), "C13": (51.5, 17.5, 0),
    "R27": (46.5, 34.5, 90), "SW3": (45.5, 57, 0),
    "LED2": (57.5, 29, 90), "R23": (61.5, 29, 90),
    "LED3": (57.5, 34, 90), "R24": (61.5, 34, 90),
    # ===== 顶边: 5号传感器 + 调试排针 =====
    "J9": (42, 4, 0), "J18": (51.5, 4, 0), "J19": (64.5, 4, 0),
    # ===== USB 右上 =====
    "J2": (75.8, 7, 270),
    "R1": (70, 9.5, 90), "R2": (70, 13.5, 90),
    "U5": (66, 12, 0), "R17": (60.5, 11, 90), "R18": (60.5, 15, 90),
    "U4": (66, 21, 0), "C12": (71, 25, 0),
    "R10": (71, 30, 90), "R11": (71, 35, 90),
    "R19": (52, 21.5, 0), "R20": (56.5, 21.5, 0),
    "R21": (52, 25.5, 0), "R22": (56.5, 25.5, 0),
    "Q11": (60, 23.5, 0), "Q12": (60, 28.5, 0),
    "LED4": (66, 33, 90), "R25": (66, 38, 90),
    "LED5": (70.5, 33, 90), "R26": (70.5, 38, 90),
    # ===== 传感连接器 右边 =====
    "J5": (76.5, 19, 270), "J6": (76.5, 32.5, 270),
    "J7": (76.5, 46, 270), "J8": (76.5, 59, 270),
    # ===== 电源输入 左中 + BUCK 竖排 =====
    "J1": (4.5, 26, 270),
    "C17": (24, 29, 90), "R3": (26.5, 31, 90),
    "D1": (29, 38.5, 0), "C1": (35, 38.5, 0),
    "D2": (29, 43.5, 0), "C2": (35, 43.5, 0),
    "U3": (29, 49, 0),
    "C5": (34.5, 50, 90),
    "L1": (43, 45, 0), "D3": (43, 55, 0),
    "R4": (48, 47.5, 90), "R5": (48, 52.5, 90),
    "C6": (23.5, 49, 90), "R6": (23.5, 54, 90),
    "C3": (29, 57.5, 0), "C4": (33.5, 57.5, 0),
    "C7": (61, 41.5, 90), "C8": (65.5, 41.5, 90),
    # ===== TCA + 上拉梯 =====
    "U2": (64, 52, 0), "C11": (69, 46, 0), "R28": (58, 44, 90),
    # ===== ch7/ch8 左边带 =====
    "J16": (5.5, 39, 90), "J17": (5.5, 52.5, 90),
    "R45": (13, 36, 90), "R53": (18, 36, 90),
    "Q9": (13, 40.5, 0), "D10": (18.5, 40.5, 180),
    "R46": (13, 46.5, 90), "R54": (18, 46.5, 90),
    "Q10": (13, 51, 0), "D11": (18.5, 51, 180),
    "C15": (24.5, 44, 90), "C16": (22.5, 58, 90),
}
for i in range(5):
    PLACE[f"R{29+i}"] = (50.5, 28 + i * 6, 90)
    PLACE[f"R{34+i}"] = (55, 28 + i * 6, 90)
# ===== ch1-6 底部 =====
BOT_X = [5.75, 18.25, 30.75, 43.25, 55.75, 67]
for i in range(6):
    x = BOT_X[i]
    dx = 8 if i == 0 else 0   # ch1 右移避开 J17 庭院
    PLACE[f"R{39+i}"] = (x - 2.4 + dx, 51.5, 90)
    PLACE[f"R{47+i}"] = (x + 2.4 + dx, 51.5, 90)
    PLACE[f"Q{3+i}"] = (x - 2.4 + dx, 56.5, 0)
    PLACE[f"D{4+i}"] = (x + 2.4 + dx, 56.5, 180)
    PLACE[f"J{10+i}"] = (x, 66, 180)
# ===== 测试点 =====
for i, (tx, ty) in enumerate([(46, 32), (26, 29.5), (50, 63), (63.5, 58.5), (73, 66),
                              (58, 63), (54, 20), (58, 20), (37, 59), (48.5, 59.5),
                              (38, 59), (3, 14)]):
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
for hx, hy in [(4, 4), (76, 4), (3, 36), (77, 36)]:
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
for cx, cy in [(18.5, 0), (33.5, 0), (33.5, 6.4), (18.5, 6.4)]:
    ol.Append(int(MM(cx)), int(MM(cy)))
board.Add(ko)

pcbnew.SaveBoard(os.path.join(HERE, "..", "flowio-p1.kicad_pcb"), board)
print("PCB 骨架已生成:", len(board.GetFootprints()), "个封装")
