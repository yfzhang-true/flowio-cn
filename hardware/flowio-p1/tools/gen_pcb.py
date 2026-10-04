# -*- coding: utf-8 -*-
"""FLOWIO-CN P1 PCB 生成器
从 gen_sch.py 的 PARTS 单一真值源生成 4 层板。
布局 (P1.1 T3): 100×80mm · 天线朝板顶边(板外净空) · 左上 USB-C 电源 · 右上USB调试
  · 底边 J10-J17 阀带 · 右边 J20-J23 主阀/泵带 · 左边 J1/J8/J6 + 顶边 J9/J18/J19/J7
用法: "E:/Program Files/KiCad/10.0/bin/python.exe" gen_pcb.py
"""
import os, re, sys
import pcbnew

MM = pcbnew.FromMM
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

# ---- 从 gen_sch.py 提取 PARTS(共享真值源; ast 受限解释, 禁 exec) ----
import ast
_src = open(os.path.join(HERE, "gen_sch.py"), encoding="utf-8").read()
_tree = ast.parse(_src)

CONSTS = {}
PARTS = []

def _lit(n, env=None):
    env = env or {}
    if isinstance(n, ast.Constant):
        return n.value
    if isinstance(n, ast.Name):
        if n.id in env: return env[n.id]
        return CONSTS[n.id]
    if isinstance(n, ast.Subscript):
        return _lit(n.value, env)[_lit(n.slice, env)]
    if isinstance(n, ast.List):
        return [_lit(e, env) for e in n.elts]
    if isinstance(n, ast.Tuple):
        return tuple(_lit(e, env) for e in n.elts)
    if isinstance(n, ast.Dict):
        return {_lit(k, env): _lit(v, env) for k, v in zip(n.keys, n.values)}
    if isinstance(n, ast.IfExp):
        return _lit(n.body, env) if _lit(n.test, env) else _lit(n.orelse, env)
    if isinstance(n, ast.Compare):
        import operator as _op
        _cmps = {ast.Eq: _op.eq, ast.NotEq: _op.ne, ast.Lt: _op.lt,
                 ast.LtE: _op.le, ast.Gt: _op.gt, ast.GtE: _op.ge}
        left = _lit(n.left, env)
        for op, cmp in zip(n.ops, n.comparators):
            left = _cmps[type(op)](left, _lit(cmp, env))
        return left
    if isinstance(n, ast.BinOp):
        import operator as _op
        _ops = {ast.Add: _op.add, ast.Sub: _op.sub, ast.Mult: _op.mul,
                ast.Div: _op.truediv, ast.FloorDiv: _op.floordiv, ast.Mod: _op.mod}
        if type(n.op) in _ops:
            return _ops[type(n.op)](_lit(n.left, env), _lit(n.right, env))
    if isinstance(n, ast.JoinedStr):                       # f-string
        return "".join(str(_lit(v, env)) for v in n.values)
    if isinstance(n, ast.FormattedValue):
        return _lit(n.value, env)
    raise SystemExit(f"PARTS 依赖不支持的节点: {type(n).__name__} @line {getattr(n, 'lineno', '?')}")

def _iterable(node, env=None):
    env = env or {}
    it = node.iter
    if isinstance(it, ast.Call) and isinstance(it.func, ast.Name) and it.func.id == "range":
        return range(*[_lit(a, env) for a in it.args])
    if isinstance(it, ast.Call) and isinstance(it.func, ast.Name) and it.func.id == "enumerate":
        return enumerate(_lit(it.args[0], env))
    return _lit(it, env)

def _pcall(call, env=None):
    env = env or {}
    if not (isinstance(call, ast.Call) and isinstance(call.func, ast.Name) and call.func.id == "P"):
        return None
    names = ["ref", "sym", "val", "fp", "lcsc", "x", "y", "nets"]
    kw = {}
    for i, a in enumerate(call.args):
        kw[names[i]] = _lit(a, env)
    for a in call.keywords:
        kw[a.arg] = _lit(a.value, env)
    return kw

def _collect_partlist(val, env=None):
    env = env or {}
    out = []
    if isinstance(val, (ast.List, ast.Tuple)):
        for e in val.elts:
            d = _pcall(e, env)
            if d: out.append(d)
    elif isinstance(val, ast.Call):
        d = _pcall(val, env)
        if d: out.append(d)
    return out

def _targets(node):
    return node.targets if isinstance(node, ast.Assign) else [node.target]

def _unpack(tgt, item, env):
    """递归解包 for 目标 (支持嵌套元组, 如 `for i, (a, b) in enumerate(...)`)."""
    if isinstance(tgt, ast.Name):
        env[tgt.id] = item
    elif isinstance(tgt, (ast.Tuple, ast.List)):
        for _t, _v in zip(tgt.elts, item):
            _unpack(_t, _v, env)

for _node in _tree.body:
    if isinstance(_node, (ast.Assign, ast.AugAssign)):
        _t0 = _targets(_node)[0]
        _val = _node.value
        if isinstance(_t0, ast.Name) and _t0.id == "PARTS":
            try:
                PARTS.extend(_collect_partlist(_val))
            except SystemExit:
                raise SystemExit("PARTS 块含不可解析节点 (仅允许 P() 与字面量)")
        elif isinstance(_t0, ast.Tuple):
            for _t, _v in zip(_t0.elts, _val.elts):
                try:
                    CONSTS[_t.id] = _lit(_v)
                except SystemExit:
                    pass
        elif isinstance(_t0, ast.Name):
            try:
                CONSTS[_t0.id] = _lit(_val)
            except SystemExit:
                pass  # 非 P 依赖的复杂定义 (函数/调用) 跳过
    elif isinstance(_node, ast.For):                        # for ...: PARTS.append(P(...)) / PARTS += [...]
        _touches_parts = any(
            (isinstance(s, ast.Expr) and isinstance(s.value, ast.Call)
             and isinstance(s.value.func, ast.Attribute) and s.value.func.attr == "append"
             and isinstance(s.value.func.value, ast.Name) and s.value.func.value.id == "PARTS")
            or (isinstance(s, ast.AugAssign) and isinstance(s.target, ast.Name) and s.target.id == "PARTS")
            for s in _node.body)
        if not _touches_parts:
            continue
        try:
            for _item in _iterable(_node):
                _env = {}
                _unpack(_node.target, _item, _env)
                for _stmt in _node.body:
                    if isinstance(_stmt, ast.Expr) and isinstance(_stmt.value, ast.Call):
                        _c = _stmt.value
                        if (isinstance(_c.func, ast.Attribute) and _c.func.attr == "append"
                                and isinstance(_c.func.value, ast.Name) and _c.func.value.id == "PARTS"):
                            _d = _pcall(_c.args[0], _env)
                            if _d: PARTS.append(_d)
                    elif isinstance(_stmt, ast.AugAssign) and isinstance(_stmt.target, ast.Name) and _stmt.target.id == "PARTS":
                        PARTS.extend(_collect_partlist(_stmt.value, _env))
                    elif isinstance(_stmt, ast.Assign) and isinstance(_stmt.targets[0], ast.Name):
                        _env[_stmt.targets[0].id] = _lit(_stmt.value, _env)
                    elif isinstance(_stmt, ast.AugAssign) and isinstance(_stmt.target, ast.Name):
                        _env[_stmt.target.id] = _env.get(_stmt.target.id, 0) + _lit(_stmt.value, _env) \
                            if isinstance(_stmt.op, ast.Add) else _env[_stmt.target.id]
        except SystemExit as _e:
            raise SystemExit(f"PARTS 循环块不可解析: {_e}")

BY_REF = {p["ref"]: p for p in PARTS}

JLC = r"C:/Users/yuefe/Documents/KiCad/9.0/3rdparty/jlc_mcp/footprints/JLC-MCP.pretty"
STD = r"E:/Program Files/KiCad/10.0/share/kicad/footprints"

# 封装库路由: fp 字段 "LIB:NAME" -> 目录
def load_fp(fp):
    if fp.startswith("JLC-MCP:"):
        return pcbnew.FootprintLoad(JLC, fp.split(":")[1])
    if fp.startswith("LOCAL:"):                 # 手建封装 (U6 XGZP6897D, T3)
        return _mk_xgzp6897d()
    if fp.startswith("Capacitor_SMD:"):
        return pcbnew.FootprintLoad(os.path.join(STD, "Capacitor_SMD.pretty"), fp.split(":")[1])
    if fp.startswith("TestPoint:"):
        return pcbnew.FootprintLoad(os.path.join(STD, "TestPoint.pretty"), fp.split(":")[1])
    if fp.startswith("Connector:"):
        return pcbnew.FootprintLoad(os.path.join(STD, "Connector.pretty"), fp.split(":")[1])
    raise ValueError(fp)


def _mk_xgzp6897d():
    """U6 XGZP6897D 宽体 SOP-8 手建封装 (LCSC 无 CFSensor 现货, 淘宝件)。
    datasheet 真值 (devices.json pneumatic_devices.sensor.mount 同源):
      排距 7.96 / 节距 2.54 / 焊盘 0.9×2.0 / 本体 7.6×10.6。
    坐标系: 引脚排沿 Y (4×2.54), 行在 x=±3.98; pin1 左上 (文件系 y 向下)。"""
    fp = pcbnew.FOOTPRINT(board)
    try:
        fp.SetFPID(pcbnew.LIB_ID("LOCAL", "XGZP6897D-SOP8-W7.96-P2.54"))
    except Exception:
        pass
    ls = pcbnew.LSET()
    for lay in (pcbnew.F_Cu, pcbnew.F_Mask, pcbnew.F_Paste):
        ls.AddLayer(lay)
    for num, px, py in [("1", -3.98, -3.81), ("2", -3.98, -1.27),
                        ("3", -3.98, 1.27), ("4", -3.98, 3.81),
                        ("5", 3.98, 3.81), ("6", 3.98, 1.27),
                        ("7", 3.98, -1.27), ("8", 3.98, -3.81)]:
        pad = pcbnew.PAD(fp)
        pad.SetNumber(num)
        pad.SetAttribute(pcbnew.PAD_ATTRIB_SMD)
        pad.SetShape(pcbnew.PAD_SHAPE_RECT)
        pad.SetSize(pcbnew.VECTOR2I(MM(2.0), MM(0.9)))
        # 封装未上板原点在 (0,0): 绝对坐标=封装本地坐标, 上板后随 SetPosition 平移
        pad.SetPosition(pcbnew.VECTOR2I(MM(px), MM(py)))
        pad.SetLayerSet(ls)
        fp.Add(pad)
    # 本体丝印/装配框 + 焊盘排外框 + courtyard (body 7.6×10.6 + 0.5)
    def _rect(x1, y1, x2, y2, layer, w):
        s = pcbnew.PCB_SHAPE(fp, pcbnew.SHAPE_T_RECT)
        s.SetStart(pcbnew.VECTOR2I(MM(x1), MM(y1)))
        s.SetEnd(pcbnew.VECTOR2I(MM(x2), MM(y2)))
        s.SetLayer(layer)
        s.SetWidth(int(MM(w)))
        fp.Add(s)
    _rect(-3.8, -5.3, 3.8, 5.3, pcbnew.F_SilkS, 0.15)
    _rect(-5.0, -5.8, 5.0, 5.8, pcbnew.F_CrtYd, 0.05)
    c = pcbnew.PCB_SHAPE(fp, pcbnew.SHAPE_T_CIRCLE)
    c.SetStart(pcbnew.VECTOR2I(MM(-3.0), MM(-4.6)))
    c.SetEnd(pcbnew.VECTOR2I(MM(-2.5), MM(-4.6)))
    c.SetLayer(pcbnew.F_SilkS)
    c.SetWidth(int(MM(0.15)))
    fp.Add(c)
    return fp

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
ds.m_CopperEdgeClearance = MM(0.3)   # 板边铜净空 (JLC ≥0.3)
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

# ---- 板框 100×80 (P1.1 T3: 底边 12 插座带 + 右边主阀带需要扩板) ----
W, H = MM(100), MM(80)
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

# ---- 器件放置表 (ref: x_mm, y_mm, 旋转°) — P1.1 T3 布局 ------------------------
# 变更要点 (对 P1.0):
#   缺陷修复: C9 移出 J9 XH 壳体投影 / R3 移出 U1 WROOM 禁布(+3mm) / HD 移 (75,55.9)
#             避 J15/J16 · Q-D 列距 ±2.4→±3.5 (SMA/SOT courtyard 修复) · WJ500V→XH-2P
#   P1.1 新增: J20-J23 右边缘带 + Q13-16/D12-15/R55-64 驱动列 + U6/C18 + U7/R63/R64 + TP13
#   传感带重排: J5→右壁, J6→左壁, J7→顶右角 (给主阀带让出右边缘)
PLACE = {
    # ===== ESP32 主控(天线朝顶边, 净空 x20.5-35.5/y<6.4) =====
    "U1": (28, 16.5, 0),
    "C9": (63, 55, 90), "C10": (43, 14, 0),
    "SW1": (8, 8.5, 0), "SW2": (15, 10.5, 0), "C14": (6.5, 13, 0), "R7": (16.5, 19, 0),
    "R13": (24, 31, 0), "R14": (28.5, 31, 0),
    "R15": (34, 31, 0), "R16": (39, 31, 0),
    "R8": (52, 27, 0), "R9": (56.5, 27, 0),
    "LED1": (52.5, 14, 0), "R12": (52.5, 20.5, 90), "C13": (58, 17.5, 0),
    "R27": (45.5, 34.5, 90), "SW3": (48, 51, 0),
    "LED2": (56, 30.5, 90), "R23": (56, 35, 90),
    "LED3": (50.5, 30, 90), "R24": (48.5, 35, 90),
    # ===== U6 XGZP6897D 板载压力传感 (I2C 主控区, 倒钩管朝上) =====
    "U6": (44, 22, 0), "C18": (42, 29, 0),
    # ===== 顶边: 传感 J9 + 调试排针 J18/J19 + 传感 J7 =====
    "J9": (44.8, 4, 0), "J18": (58.1, 4, 0), "J19": (71.4, 4, 0), "J7": (84.7, 4, 0),
    # ===== USB 右上 =====
    "J2": (96.4, 6, 270),
    "R1": (90.5, 9, 90), "R2": (83, 19, 90),
    "U5": (74.5, 14, 0), "R17": (69, 12.5, 90), "R18": (69, 16.5, 90),
    "U4": (74.5, 21.5, 0), "C12": (79.5, 27, 0),
    "R10": (76.5, 30, 90), "R11": (76.5, 34.5, 90),
    "R19": (62, 22, 0), "R20": (66.5, 22, 0),
    "R21": (62, 26, 0), "R22": (66.5, 26, 0),
    "Q11": (72, 28, 90), "Q12": (72, 34, 90),
    "LED4": (68, 34, 90), "R25": (68, 39, 90),
    "LED5": (68, 44, 90), "R26": (68, 53, 90),
    # ===== 传感连接器 (P1.1 重排: J5 底右角避 J23/J17 挤压, J8/J6 左壁) =====
    "J5": (94.5, 74, 180),
    "J8": (5, 38.5, 90), "J6": (5, 52, 90),
    # ===== 电源 左壁 USB-C 5A (P1.1: DC005 移除) =====
    "J1": (4.5, 19, 90),
    "U7": (12.5, 19, 0), "R63": (11, 14.5, 90), "R64": (11, 23.5, 90),
    "C17": (16, 24, 90),
    "R3": (21, 34, 90),
    "D2": (24, 38.5, 0), "C1": (30, 33.5, 0), "C2": (30, 38.5, 0),
    "U3": (25, 45, 0),
    "C6": (18.5, 45, 90), "R6": (18.5, 50, 90),
    "C5": (31.8, 41.5, 90),
    "L1": (41, 43, 0), "D3": (40, 51.5, 0),
    "R4": (52.5, 42, 90), "R5": (52.5, 47, 90),
    "C3": (22, 53, 0), "C4": (27, 54, 0),
    "C7": (56, 40.5, 90), "C8": (56, 47.5, 90),
    # ===== TCA + 上拉梯 =====
    "U2": (73.5, 44, 0), "C11": (77, 51.5, 0), "R28": (57, 57, 90),
    "C15": (34.5, 51.5, 90), "C16": (81.5, 60.5, 0),
}
for i in range(5):
    PLACE[f"R{29+i}"] = (60, 30 + i * 4.8, 90)
    PLACE[f"R{34+i}"] = (64, 30 + i * 4.8, 90)
# ===== ch1-8 阀通道 底边带 (R 行 y61 / Q-D 行 y66 / 插座 y74) =====
BOT_X = [5.4 + i * 11 for i in range(8)]
for i in range(8):
    x = BOT_X[i]
    PLACE[f"R{39+i}"] = (x - 3.5, 61, 90)
    PLACE[f"R{47+i}"] = (x + 3.5, 61, 90)
    PLACE[f"Q{3+i}"] = (x - 3.0, 66, 0)
    PLACE[f"D{4+i}"] = (x + 2.5, 66, 180)
    PLACE[f"J{10+i}"] = (x, 74, 180)
# ===== P1.1: S/V/F 主阀 + 泵 右边缘带 (J20-J23 口朝 +X; 驱动列同域延伸) =====
MAIN_Y = [17.5 + 11 * k for k in range(4)]
for k in range(4):
    PLACE[f"R{55+k}"] = (80, 18.5 + 11 * k, 90)
    PLACE[f"R{59+k}"] = (86.5, 18.5 + 11 * k, 90)
    PLACE[f"Q{13+k}"] = (86, 23 + 11 * k, 0)
    PLACE[f"D{12+k}"] = (81, 23 + 11 * k, 180)
    PLACE[f"J{20+k}"] = (94, MAIN_Y[k], 270)
# ===== 测试点 =====
for i, (tx, ty) in enumerate([(58.5, 21.5), (14, 33), (34, 57.5), (45, 57.5), (82, 63),
                              (48.5, 47.5), (43.5, 31.5), (47, 31.5), (12, 57.5), (14.5, 57),
                              (37, 55), (2.8, 11), (90.5, 63)]):
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

# ---- 安装孔 (P1.1 T3: HA 避 SW1 courtyard / HB 让左壁 J 带 / HD 避 J15/J16+D9) ----
for hx, hy in [(3.4, 3.4), (83, 12.5), (3, 28), (73.5, 55.7)]:
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
