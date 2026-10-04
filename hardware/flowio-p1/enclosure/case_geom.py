# -*- coding: utf-8 -*-
"""FLOWIO-P1 装配几何单一真相源 — 所有 make_*/test_* 必须从这里取常量, 禁止本地复制.

背景 (2026-10-03 装配逻辑修复): 此前四个生成源各自复制常量并选择了互相矛盾的
板高基准 (make_meshes/make_flows 取"板趴腔底 z=2.4", make_assembly 取"板坐铜柱
z=7.4", make_case 注释与内腔高度计算自相矛盾), 且顶盖被建模成带底板的方盒。
机械真相唯一: M3 螺丝穿 PCB 孔自攻入铜柱 -> 板坐在铜柱顶。

坐标系: 壳系, 下壳外角为原点 (x→右, y→上, z→高)。
KiCad pos.csv/STEP -> 壳系映射: x = PosX + OX, y = -PosY + OX
  (锚点验证: J10 (6.5,-68.5)->(9.4,71.4) 贴底边槽; J2 (86,-6)->(88.9,8.9) 贴右壁槽;
   J1 (5.5,-27)->(8.4,29.9) 贴左壁槽; "-PosY+75" 假设已被三锚点证伪)
纯 Python (无 FreeCAD 依赖), FreeCADCmd 与测试均可 import。
"""
import struct

# ---------- 基本参数 ----------
WALL, CLR = 2.4, 0.5            # 壁厚 / 板-壁间隙
BW, BH, PCB_T = 100.0, 80.0, 1.6  # 板宽/深/厚 (mm) — P1.1 T3: 90x75 扩板容 12 阀座带
OX = WALL + CLR                  # 2.9 板原点在壳内偏移
OW, OH = BW + 2 * OX, BH + 2 * OX  # 105.8 x 85.8 壳外廓

# ---------- 装配栈 (唯一真相) ----------
PH = 5.0                         # 铜柱高 (自腔底)
PD = 2.8                         # 铜柱 M3 自攻底孔径 (4.2 无咬丝, 2026-10-03 修正)
BOSS_RING = 1.75                 # 铜柱壁厚 -> 柱外径 = PD + 2*BOSS_RING = 6.3
SCREW_D = 3.4                    # 顶盖 M3 过孔
# 铜柱(板系) = PCB 安装孔 (T3: HA 避 SW1 / HB 让左壁 J 带 / HC / HD 避 J15/J16+D9);
# 与 fab 钻孔 Ø3.2 四孔 Δ=0.00 (L2 测试钻孔对拍守门)
ST = [(3.4, 3.4), (3.0, 28.0), (83.0, 12.5), (73.5, 55.7)]
Z_FLOOR = WALL                   # 2.4 腔底面
Z_BOARD = WALL + PH              # 7.4 板底面 = 铜柱顶
Z_TOP = Z_BOARD + PCB_T          # 9.0 板面 = 顶面器件基面
CEIL_CLR = 0.6                   # 天花板下净空


def _load_device_dims():
    """devices.json -> (keyword 有序表, 最高器件). T5 真值切换: JLC 实测优先.
    匹配策略 (T6 修复): 关键词按长度降序 —— 最具体者优先。首匹配按 devices 列表序
    曾让 J2(pkg=TYPE-C-SMD_TYPE-C-6P_1) 误命中 J1 条目的泛关键词 "TYPE-C"
    (J1 条目按 lcsc 序在前), 盒尺寸 8.94x7.35x3.26 顶到 12.26 探入裙环带
    (SKIRT_Z0=12.1) 造成 L4 顶盖干涉 0.2945mm^3; J2 专有关键词 "TYPE-C-6P"
    (9 字符) 长于 "TYPE-C" (6), 长者先试即各归各位 (J1->TYPE-C-31-M-12 同理).
    失败回退内置兜底 (FreeCAD 无 devices.json 环境的鲁棒性)."""
    import json as _json
    try:
        dev = _json.loads((Path(__file__).parent / "devices.json").read_text(encoding="utf-8"))["devices"]
        kw = []
        for e in dev:
            for k in e["pkg_keywords"]:
                kw.append((k, (e["dims"]["w"], e["dims"]["d"], e["dims"]["h"])))
        kw.sort(key=lambda t: -len(t[0]))          # 最长 (最具体) 关键词优先
        return kw, max(e["dims"]["h"] for e in dev)
    except Exception:
        fb = {"CONN-SMD_2P": (10.0, 7.8, 6.2), "CONN-TH_4P": (5.9, 12.5, 7.0),
              "TYPE-C-6P": (8.0, 10.3, 3.2), "TYPE-C": (8.94, 7.35, 3.26),
              "XGZP6897D": (7.96, 10.6, 9.5),
              "WROOM": (18.0, 25.5, 3.1), "CDRH": (10.2, 10.2, 3.0),
              "SOT-23": (2.9, 2.4, 1.2), "SOP": (4.9, 3.9, 1.75),
              "TSSOP": (7.8, 4.4, 1.1), "ESSOP": (4.9, 3.9, 1.75),
              "C1206": (3.2, 1.6, 1.6), "C_1206": (3.2, 1.6, 1.6),
              "C_0603": (1.6, 0.8, 0.8), "SMA": (4.3, 2.6, 2.1),
              "WS2812": (5.0, 5.0, 1.6), "SW-SMD": (4.0, 3.0, 2.0),
              "R0603": (1.6, 0.8, 0.5), "0603WAF": (1.6, 0.8, 0.5),
              "LED": (1.6, 0.8, 0.8), "SOT-23-6": (2.9, 2.4, 1.1),
              "RC0603": (1.6, 0.8, 0.5), "XH": (5.9, 12.5, 7.0)}
        return sorted([(k, fb[k]) for k in fb], key=lambda t: -len(t[0])), 9.5


_KW_DIMS, TALLEST = _load_device_dims()   # TALLEST = 9.5 (XGZP6897D 倒钩管, P1.1 最高件;
# WJ500V 14.07 随端子排移除退役; 腔高随之 23.67 -> 19.1)
Z_CEIL = Z_TOP + TALLEST + CEIL_CLR  # 19.1 内腔顶面 = 下壳壁顶 = 顶盖天花下表面
OUTER_H = Z_CEIL + WALL          # 21.5 总高
SKIRT = 7.0                      # 顶盖裙边下沉深度
SKIRT_Z0 = Z_CEIL - SKIRT        # 12.1 裙边下端
SKIRT_INSET = WALL + 0.4         # 2.8 裙环外缘离壳外缘 (贴入下壳腔, 与壁 0.4 间隙)
SKIRT_T = 2.0                    # 裙环壁厚 (环带 2.8..4.8)

# ---------- 侧开槽 [面, 板系pos, 宽, z_lo, z_hi] ----------
# z 带统一以板面 Z_TOP 为基准 (z_lo = Z_TOP-0.2 起线), 高度 = 所服务器件高 + 0.2。
# P1.1 T3 (100x80 板): 13 侧槽 = L:J1(USB-C h3.26)/J8/J6 + R:J2(USB-C)/J20-J23(XH-2P)
#   + T:J9/J18/J19/J7(XH-4P) + B:J5(XH-4P); 底边 TERM 8 槽另计 (device_graph 21↔21)。
# 槽深穿透范围含下壳壁 (0..2.4) 与顶盖裙环 (2.8..4.8), 见 SLOT_DEPTH。
SLOT_DEPTH = SKIRT_INSET + SKIRT_T + 1.6   # 6.4: 自壳外缘 -1.2 起贯穿两层壁
# XY 对拍: J1⊂L@19, J2⊂R@6, J20-J23⊂R@17.5/28.5/39.5/50.5, J5⊂B@74, J6⊂L@52,
#          J8⊂L@38.5, J9/J18/J19/J7⊂T@44.8/58.1/71.4/84.7, J10..J17⊂B(TERM)。
SLOT_LO = Z_TOP - 0.2            # 8.8
CUTS = [
    ("L", 19.0, 10.0, SLOT_LO, Z_TOP + 3.5),   # J1 USB-C 31-M-12 (h3.26 估+0.2)
    ("L", 38.5, 8.0, SLOT_LO, Z_TOP + 7.2),    # J8 4P (JLC Z-Height 7.0)
    ("L", 52.0, 8.0, SLOT_LO, Z_TOP + 7.2),    # J6 4P
    ("R", 6.0, 10.0, SLOT_LO, Z_TOP + 3.5),    # J2 TYPE-C (h3.2 估, 外伸 1.15)
    ("R", 17.5, 11.0, SLOT_LO, Z_TOP + 6.4),   # J20 S 充气主阀 XH-2P (h6.2)
    ("R", 28.5, 11.0, SLOT_LO, Z_TOP + 6.4),   # J21 V 真空主阀
    ("R", 39.5, 11.0, SLOT_LO, Z_TOP + 6.4),   # J22 F 排气主阀
    ("R", 50.5, 11.0, SLOT_LO, Z_TOP + 6.4),   # J23 泵模块口
    ("T", 44.8, 8.5, SLOT_LO, Z_TOP + 7.2),    # J9 4P
    ("T", 58.1, 8.5, SLOT_LO, Z_TOP + 7.2),    # J18 4P
    ("T", 71.4, 8.5, SLOT_LO, Z_TOP + 7.2),    # J19 4P
    ("T", 84.7, 8.5, SLOT_LO, Z_TOP + 7.2),    # J7 4P
    ("B", 94.5, 8.5, SLOT_LO, Z_TOP + 7.2),    # J5 4P (S1 传感, 底右角)
]
TERM_X = [5.4 + 11 * i for i in range(8)]      # 底边 8 阀座 J10..J17 (11mm 节距)
TY = 74.0                                       # 阀座排板系 y (T3: 68.5→74)
TERM_SLOT = (10.8, SLOT_LO, Z_TOP + 6.4)  # (宽, z_lo, z_hi); XH-2P 本体宽 10.0
# 角部 relief: 阀座排两端体 (J10 左端 x 0.4 / J5 右端 99.45) 探入裙角柱带 (2.8..4.8),
# 后壁两端开贯穿缺口 (壁+裙柱)。y 带 = J 带+J5 本体 y (板系 68.8..76.55 → 壳 71.7..79.45)。
TERM_RELIEF = (5.6, 70.5, 80.8)     # (x 深自外缘, y_lo, y_hi) 壳系

# ---------- 器件盒尺寸 (devices.json 单一数据层, T5 真值切换) ----------
DEFAULT_DIM = (2.2, 2.2, 1.5)


def dims_for(pkg):
    for k, d in _KW_DIMS:
        if k in pkg:
            return d
    return DEFAULT_DIM

# ---------- 映射与锚点 ----------
def board_to_case(x, y):
    """KiCad 板系 (PosX, PosY, y∈[-80,0]) -> 壳系."""
    return (x + OX, -y + OX)

ANCHORS = [  # (ref, PosX, PosY) -> 期望壳系坐标 (已人工对拍槽位)
    ("J10", 5.4, -74.0, 8.3, 76.9),
    ("J2", 96.4, -6.0, 99.3, 8.9),
    ("J1", 4.5, -19.0, 7.4, 21.9),
]

# ---------- 孪生爆炸视图契约 ----------
BBOX_MM = [OW, OH, OUTER_H]      # 现值 [105.8, 85.8, 21.5] (派生自 OW/OH/OUTER_H, 随板改同步)
EXPLODE = {
    "case_top":    [0, 0, 32],
    "parts_F":     [0, 0, 14],
    "pcb":         [0, 0, 0],
    "case_bottom": [0, 0, -20],
}

# ---------- 纯 Python 二进制 STL 解析 (测试用, 无第三方依赖) ----------
def parse_stl(path):
    """返回 (n_facets, [(x,y,z)x3] 生成器已展开为顶点列表)."""
    b = open(path, "rb").read()
    if len(b) < 84:
        return 0, []
    n = struct.unpack("<I", b[80:84])[0]
    if 84 + n * 50 != len(b):
        raise ValueError("not a binary STL: %s" % path)
    verts = []
    for i in range(n):
        off = 84 + i * 50 + 12
        for j in range(3):
            verts.append(struct.unpack("<3f", b[off + j * 12: off + j * 12 + 12]))
    return n, verts

def stl_bbox(path):
    n, vs = parse_stl(path)
    xs = [v[0] for v in vs]; ys = [v[1] for v in vs]; zs = [v[2] for v in vs]
    return (n,
            (min(xs), max(xs)) if vs else None,
            (min(ys), max(ys)) if vs else None,
            (min(zs), max(zs)) if vs else None)
