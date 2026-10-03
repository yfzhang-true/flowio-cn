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
CEIL_CLR = 0.6                   # 天花板下净空


def _load_device_dims():
    """devices.json -> (keyword 有序表, 最高器件). T5 真值切换: JLC 实测优先.
    失败回退内置兜底 (FreeCAD 无 devices.json 环境的鲁棒性)."""
    import json as _json
    try:
        dev = _json.loads((Path(__file__).parent / "devices.json").read_text(encoding="utf-8"))["devices"]
        kw = []
        for e in dev:
            for k in e["pkg_keywords"]:
                kw.append((k, (e["dims"]["w"], e["dims"]["d"], e["dims"]["h"])))
        return kw, max(e["dims"]["h"] for e in dev)
    except Exception:
        fb = {"CONN-TH_2P": (10.2, 10.0, 14.07), "CONN-TH_4P": (5.9, 12.5, 7.0),
              "TYPE-C": (8.0, 10.3, 3.2), "DC005": (9.9, 14.0, 10.9),
              "WROOM": (18.0, 25.5, 3.1), "CDRH": (10.2, 10.2, 3.0),
              "SOT-23": (2.9, 2.4, 1.2), "SOP": (4.9, 3.9, 1.75),
              "TSSOP": (7.8, 4.4, 1.1), "ESSOP": (4.9, 3.9, 1.75),
              "C1206": (3.2, 1.6, 1.6), "C_1206": (3.2, 1.6, 1.6),
              "C_0603": (1.6, 0.8, 0.8), "SMA": (4.3, 2.6, 2.1),
              "WS2812": (5.0, 5.0, 1.6), "SW-SMD": (4.0, 3.0, 2.0),
              "R0603": (1.6, 0.8, 0.5), "0603WAF": (1.6, 0.8, 0.5),
              "LED": (1.6, 0.8, 0.8), "SOT-23-6": (2.9, 2.4, 1.1),
              "RC0603": (1.6, 0.8, 0.5), "XH": (5.9, 12.5, 7.0)}
        return [(k, fb[k]) for k in fb], 14.07


_KW_DIMS, TALLEST = _load_device_dims()   # TALLEST = 14.07 (WJ500V, JLC Height Above Board)
Z_CEIL = Z_TOP + TALLEST + CEIL_CLR  # 23.67 内腔顶面 = 下壳壁顶 = 顶盖天花下表面
OUTER_H = Z_CEIL + WALL          # 26.07 总高
SKIRT = 7.0                      # 顶盖裙边下沉深度
SKIRT_Z0 = Z_CEIL - SKIRT        # 16.67 裙边下端
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
    ("L", 27.0, 11.2, SLOT_LO, Z_TOP + 11.1),   # J1 DC005 (JLC Body Height 10.9)
    ("L", 46.0, 8.0,  SLOT_LO, Z_TOP + 7.2),    # J8 4P (JLC Z-Height 7.0)
    ("R", 6.0,  10.0, SLOT_LO, Z_TOP + 3.4),    # J2 TYPE-C (h3.2 估, 外伸 1.15)
    ("R", 22.0, 8.0,  SLOT_LO, Z_TOP + 7.2),    # J5 4P
    ("R", 32.5, 8.0, SLOT_LO, Z_TOP + 7.2),     # J6 4P
    ("R", 46.0, 8.0,  SLOT_LO, Z_TOP + 7.2),    # J7 4P
    ("T", 46.0, 8.5,  SLOT_LO, Z_TOP + 7.2),    # J9 4P
    ("T", 59.5, 8.5,  SLOT_LO, Z_TOP + 7.2),    # J18 4P
    ("T", 73.0, 8.5,  SLOT_LO, Z_TOP + 7.2),    # J19 4P
]
TERM_X = [6.5 + 11 * i for i in range(8)]       # 底边 8 端子 J10..J17
TY = 68.5                                        # 端子排板系 y
TERM_SLOT = (10.8, SLOT_LO, Z_TOP + TALLEST + 0.2)  # (宽, z_lo, z_hi); 盒宽实测 10.7
# 角部 relief: 端子排两端体宽 10.7@11 节距 -> 首末体探入裙角柱 (x<4.8 / x>91.0),
# 真实 KiCad 模型 (+3.15 偏移) 在 J17 侧更甚。后壁两端开贯穿缺口 (壁+裙柱)。
TERM_RELIEF = (5.6, 64.9, 77.9)     # (x 深自外缘, y_lo, y_hi) 壳系

# ---------- 器件盒尺寸 (devices.json 单一数据层, T5 真值切换) ----------
DEFAULT_DIM = (2.2, 2.2, 1.5)


def dims_for(pkg):
    for k, d in _KW_DIMS:
        if k in pkg:
            return d
    return DEFAULT_DIM

# ---------- 映射与锚点 ----------
def board_to_case(x, y):
    """KiCad 板系 (PosX, PosY, y∈[-75,0]) -> 壳系."""
    return (x + OX, -y + OX)

ANCHORS = [  # (ref, PosX, PosY) -> 期望壳系坐标 (已人工对拍槽位)
    ("J10", 6.5, -68.5, 9.4, 71.4),
    ("J2", 86.0, -6.0, 88.9, 8.9),
    ("J1", 5.5, -27.0, 8.4, 29.9),
]

# ---------- 孪生爆炸视图契约 ----------
BBOX_MM = [OW, OH, OUTER_H]      # [95.8, 80.8, 26.07]
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
