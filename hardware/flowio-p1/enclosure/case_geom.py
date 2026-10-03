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
BW, BH, PCB_T = 90.0, 75.0, 1.6  # 板宽/深/厚 (mm)
OX = WALL + CLR                  # 2.9 板原点在壳内偏移
OW, OH = BW + 2 * OX, BH + 2 * OX  # 95.8 x 80.8 壳外廓

# ---------- 装配栈 (唯一真相) ----------
PH = 5.0                         # 铜柱高 (自腔底)
PD = 2.8                         # 铜柱 M3 自攻底孔径 (4.2 无咬丝, 2026-10-03 修正)
BOSS_RING = 1.75                 # 铜柱壁厚 -> 柱外径 = PD + 2*BOSS_RING = 6.3
SCREW_D = 3.4                    # 顶盖 M3 过孔
ST = [(4.0, 4.0), (3.0, 37.0), (86.0, 13.0), (68.0, 65.0)]  # 铜柱(板系); 与 fab 钻孔 T9 (NPTH 3.2) 四孔 Δ=0.00
Z_FLOOR = WALL                   # 2.4 腔底面
Z_BOARD = WALL + PH              # 7.4 板底面 = 铜柱顶
Z_TOP = Z_BOARD + PCB_T          # 9.0 板面 = 顶面器件基面
TALLEST = 17.5                   # 最高器件 J10..J17 端子 WJ500V (KiCad 3D 模型实测 raw z 1.61..19.11)
CEIL_CLR = 0.6                   # 天花板下净空
Z_CEIL = Z_TOP + TALLEST + CEIL_CLR  # 27.1 内腔顶面 = 下壳壁顶 = 顶盖天花下表面
OUTER_H = Z_CEIL + WALL          # 29.5 总高
SKIRT = 7.0                      # 顶盖裙边下沉深度
SKIRT_Z0 = Z_CEIL - SKIRT        # 20.1 裙边下端
SKIRT_INSET = WALL + 0.4         # 2.8 裙环外缘离壳外缘 (贴入下壳腔, 与壁 0.4 间隙)
SKIRT_T = 2.0                    # 裙环壁厚 (环带 2.8..4.8)

# ---------- 侧开槽 [面, 板系pos, 宽, z_lo, z_hi] ----------
# z 带统一以板面 Z_TOP 为基准 (z_lo = Z_TOP-0.2 起线), 高度 = 所服务器件高 + 0.2。
# L@27 宽 11.2: J1 盒体 y 向 10.9 全覆盖 (旧 10 偏窄)。
# 槽深穿透范围含下壳壁 (0..2.4) 与顶盖裙环 (2.8..4.8), 见 SLOT_DEPTH。
SLOT_DEPTH = SKIRT_INSET + SKIRT_T + 1.6   # 6.4: 自壳外缘 -1.2 起贯穿两层壁
# XY 已对拍: J1⊂L@27, J2⊂R@6, J5/6/7⊂R@22/32.5/46, J8⊂L@46, J9/J18/J19⊂T, J10..J17⊂B。
SLOT_LO = Z_TOP - 0.2            # 8.8
CUTS = [
    ("L", 27.0, 11.2, SLOT_LO, Z_TOP + 15.3),   # J1 DC005 (模型实测 h15.1, 板边外伸)
    ("L", 46.0, 8.0,  SLOT_LO, Z_TOP + 10.7),   # J8 4P (模型实测 h10.4)
    ("R", 6.0,  10.0, SLOT_LO, Z_TOP + 3.4),    # J2 TYPE-C (h3.2, 外伸 1.15)
    ("R", 22.0, 8.0,  SLOT_LO, Z_TOP + 10.7),   # J5 4P
    ("R", 32.5, 8.0, SLOT_LO, Z_TOP + 10.7),    # J6 4P
    ("R", 46.0, 8.0,  SLOT_LO, Z_TOP + 10.7),   # J7 4P
    ("T", 46.0, 8.5,  SLOT_LO, Z_TOP + 10.7),   # J9 4P
    ("T", 59.5, 8.5,  SLOT_LO, Z_TOP + 10.7),   # J18 4P
    ("T", 73.0, 8.5,  SLOT_LO, Z_TOP + 10.7),   # J19 4P
]
TERM_X = [6.5 + 11 * i for i in range(8)]       # 底边 8 端子 J10..J17
TY = 68.5                                        # 端子排板系 y
TERM_SLOT = (10.8, SLOT_LO, Z_TOP + TALLEST + 0.2)  # (宽, z_lo, z_hi); 盒宽实测 10.7
# 角部 relief: 端子排两端体宽 10.7@11 节距 -> 首末体探入裙角柱 (x<4.8 / x>91.0),
# 真实 KiCad 模型 (+3.15 偏移) 在 J17 侧更甚。后壁两端开贯穿缺口 (壁+裙柱)。
TERM_RELIEF = (5.6, 64.9, 77.9)     # (x 深自外缘, y_lo, y_hi) 壳系

# ---------- 器件盒尺寸 (Package 关键字 -> w,d,h; make_meshes/make_flows/test 共用) ----------
H = {
    "CONN-TH_2P": (10.7, 10.0, 17.5),   # WJ500V 2P (KiCad 模型实测)
    "TYPE-C":     (8.0, 10.3, 3.2),
    "WROOM":      (18.0, 25.5, 3.1),
    "XH":         (6.5, 13.3, 8.5),
    "CONN-TH_4P": (6.0, 12.4, 10.5),    # 6173868 4P (模型实测 h10.4)
    "SOT-23":     (2.9, 2.4, 1.2),
    "C_0603":     (1.6, 0.8, 0.9),
    "C1206":      (3.2, 1.6, 0.8),
    "C_1206":     (3.2, 1.6, 6.5),
    "SOP":        (4.9, 3.9, 1.75),
    "MSOP":       (3.0, 5.0, 1.1),
    "CDRH":       (10.0, 10.0, 4.0),
    "DC005":      (9.8, 14.0, 15.1),    # DC005 (模型实测; 板边外伸朝 -X)
    "TestPoint":  (1.0, 1.0, 0.5),
    "R0603":      (1.6, 0.8, 0.6),
    "SMA":        (4.3, 2.6, 1.1),
    "SW-SMD":     (6.1, 3.8, 2.0),
}
ALIAS = {"IND-SMD": "CDRH", "SOIC": "SOP"}
DEFAULT_DIM = (2.2, 2.2, 1.5)
_KW = [(k, H[k]) for k in H] + [(a, H[b]) for a, b in ALIAS.items()]

# ---------- 孪生爆炸视图契约 ----------
BBOX_MM = [OW, OH, OUTER_H]      # [95.8, 80.8, 29.5]
EXPLODE = {
    "case_top":    [0, 0, 38],
    "parts_F":     [0, 0, 18],
    "pcb":         [0, 0, 0],
    "case_bottom": [0, 0, -22],
}

# ---------- 映射与锚点 ----------
def board_to_case(x, y):
    """KiCad 板系 (PosX, PosY, y∈[-75,0]) -> 壳系."""
    return (x + OX, -y + OX)

ANCHORS = [  # (ref, PosX, PosY) -> 期望壳系坐标 (已人工对拍槽位)
    ("J10", 6.5, -68.5, 9.4, 71.4),
    ("J2", 86.0, -6.0, 88.9, 8.9),
    ("J1", 5.5, -27.0, 8.4, 29.9),
]

def dims_for(pkg):
    for k, d in _KW:
        if k in pkg:
            return d
    return DEFAULT_DIM

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
