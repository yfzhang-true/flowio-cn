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
M1-R2 (E② 修复): 补 pathlib 导入 —— 此前 _load_device_dims/_load_pneu 引用未导入的
Path, NameError 被宽 except 吞, 加载恒走内置兜底; 兜底对电子 3 键不等价 (L1/LED1/U3
的封装 IND-SMD/5050/SOIC 在兜底表无关键词, 退化 DEFAULT_DIM), 气动 14 键等价。
devices.json 落位裁定: **不拷贝** —— 加载路径经包定位指向 enclosure/ 原位单源
(与 flowio.core.truth.TruthSource 默认路径同一文件); 拷贝至 flowio/geom/ 即制造
第二份真值, 无 CI 守门必分叉。兜底表保留 (仓库外 FreeCAD 环境的降级鲁棒性, 原设计角色)。
"""
import struct
from pathlib import Path

# devices.json 单源 (enclosure/ 原位; 经包定位: flowio/geom -> 仓库根)
_DEVICES_JSON = (Path(__file__).resolve().parents[2] / "hardware" / "flowio-p1"
                 / "enclosure" / "devices.json")

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
        dev = _json.loads(_DEVICES_JSON.read_text(encoding="utf-8"))["devices"]
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

# ═══════════════ T6 气动结构 (1a 竖装 + 1f-β 歧管 + 1h 泵模块) ═══════════════
# 数据源 = devices.json pneumatic_devices 段 (T1 入库); 本段不参与壳高链
# (壳高由板上器件 TALLEST 决定, 阀阵/歧管为壳盖之上的开放塔)。
def _load_pneu():
    """pneumatic_devices -> 尺寸真值 dict (失败回退手抄真值, 与 devices.json 等价)."""
    import json as _json
    try:
        pn = _json.loads(_DEVICES_JSON.read_text(
            encoding="utf-8"))["pneumatic_devices"]
        vd = pn["valves"][0]                       # F0520D 通道阀+充/排主阀
        vb = pn["valve_vacuum_master"][0]          # F0520B 真空主阀
        pp = pn["pump"][0]                         # ZR370-03PM
        ps = pn["sensor"][0]                       # XGZP6897D
        return {
            "vd_w": vd["dims"]["w"], "vd_d": vd["dims"]["d"], "vd_h": vd["dims"]["h"],
            "vd_noz": vd["port"]["dia_mm"],
            "vb_w": vb["dims"]["w"], "vb_d": vb["dims"]["d"], "vb_h": vb["dims"]["h"],
            "vb_noz": vb["port"]["dia_mm"],
            "pump_l": pp["dims"]["w"], "pump_dia": pp["dims"]["d"], "pump_h": pp["dims"]["h"],
            "pump_noz": pp["ports"]["dia_mm"], "pump_tube": pp["ports"]["tube_id_mm"],
            "sens_noz": ps["port"]["dia_mm"],
        }
    except Exception:
        return {"vd_w": 15.0, "vd_d": 13.0, "vd_h": 20.5, "vd_noz": 3.0,
                "vb_w": 15.0, "vb_d": 13.0, "vb_h": 28.0, "vb_noz": 4.6,
                "pump_l": 58.1, "pump_dia": 24.0, "pump_h": 31.5,
                "pump_noz": 4.2, "pump_tube": 5.0, "sens_noz": 3.22}


_PNEU = _load_pneu()

# ---------- 气动塔 (主壳盖上, 1a 竖装 2×4 + 主阀 1×3) ----------
TOWER_Z0 = OUTER_H                   # 21.5 阀基面 = 壳盖顶 (阀吊装于歧管, 基面为基准)
NOZZLE_LEN = 6.0                     # 阀嘴伸出量: devices.json 仅总高, 6mm 为 F0520 系
#   实物照估值 (推导注释; 若到货实测不符, 改此一处的连带头)。
VD_BODY_H = _PNEU["vd_h"] - NOZZLE_LEN    # 14.5 F0520D 本体高 (总高 20.5 - 嘴 6)
VB_BODY_H = _PNEU["vb_h"] - NOZZLE_LEN    # 22.0 F0520B 本体高 (总高 28 - 嘴 6)
# 2×4 通道阀阵 V1-V8: 列 x 19mm 节距 (体宽 15 + 4 间隙), 行 y 25mm 节距 (体深 13+12);
# 阵面 72×38 ≈ spec 1a "76×38"。V1-V4 前行 (y=70, 近 B 壁, 上方 J10-J13),
# V5-V8 后行 (y=45, 上方 J14-J17) —— 引线跨前行折回底边 J 带 (软引线, 物理自由)。
V_COLS = [20.0, 39.0, 58.0, 77.0]
V_ROWS = [45.0, 70.0]
# 主阀 1×3 (VS/VV/VF): x=96 (体 88.5..103.5, 右缘带, 与通道阵 x 间距 4),
# y = J20/J21/J22 壳系 y (20.4/31.4/42.4) —— 引线垂直下落直插 R 壁三槽。
M_X, M_YS = 96.0, [20.4, 31.4, 42.4]

def valve_grid():
    """11 阀 (x, y, kind) 壳系坐标; kind: 'D'=F0520D (V1-V8 + VS/VF), 'B'=F0520B (VV).
    主阀序: (96,20.4)=VS 充气 / (96,31.4)=VV 真空 / (96,42.4)=VF 排气."""
    g = []
    for c in V_COLS:
        g.append((c, V_ROWS[1], "D"))           # V1-V4 前行
    for c in V_COLS:
        g.append((c, V_ROWS[0], "D"))           # V5-V8 后行
    g.append((M_X, M_YS[0], "D"))               # VS  充气主阀 (F0520D)
    g.append((M_X, M_YS[1], "B"))               # VV  真空主阀 (F0520B)
    g.append((M_X, M_YS[2], "D"))               # VF  排气主阀 (F0520D)
    return g

# ---------- 歧管 (1f-β 公共歧管 M: 8 通道口 + 3 主阀口 + 1 测压口 = 12 口) ----------
# 基座卡 2×4 阀阵顶部: F0520D 嘴尖 z = 21.5+14.5+6 = 42.0; F0520B 嘴尖 = 21.5+22+6 = 49.5。
# 歧管底面须高于最高阀体顶 (F0520B 43.5) → MAN_Z0 = 44.0 (0.5 间隙);
# F0520D 嘴 (36..42) 不及底面, 由下垂承插短管 (boss) 接至块底。
MAN_Z0 = TOWER_Z0 + VB_BODY_H + 0.5      # 44.0 块底 z
MAN_H = 13.0                              # 块厚 (公共腔+流道+变径腔)
MAN_Z1 = MAN_Z0 + MAN_H                   # 57.0 块顶 z
MAN_X0, MAN_X1 = 2.0, 105.0              # 覆 11 承口 + 4 支腿投影 (块底 z44 悬空, 腿接块)
MAN_Y0, MAN_Y1 = 4.0, 84.0               # 同上; 块界不触壳壁 (OW/OH 105.8/85.8)
SOCK_D_D = _PNEU["vd_noz"] + 0.2          # 3.2 F0520D 承口孔径 (嘴 3.0 + 0.2 间隙)
SOCK_D_B = _PNEU["vb_noz"] + 0.2          # 4.8 F0520B 承口孔径 (嘴 4.6 + 0.2 间隙)
SOCK_BOSS_D, SOCK_BOSS_Z1 = 6.2, 36.5     # D 阀承插短管: ⌀6.2 外径, 下端 z (嘴 36..42
#   与孔 36.5..46 重叠 5.5mm = 插入深度, 合 1f-β "5-10mm 插入" 约定)
SOCK_DEPTH_B = 6.0                        # B 阀承口深 (嘴 43.5..49.5 与孔 44..50 重叠 5.5)
RUN_D = SOCK_D_D                          # 3.2 内流道 ⌀ (走道截面 ≥ 阀孔径 3.0)
TAPER_IN_Z, TAPER_OUT_D = 50.0, RUN_D     # 变径腔: 真空侧 ⌀4.8 承口于 z50 收口至 ⌀3.2
#   (泵侧 5→3 收口内化, Kamoer 变径转接替代; 腔体 z 50..53 锥收)
PLENUM_Z = 54.5                           # 公共腔脊 z (块顶 57 - 2.5 壁)
# 测压口: 右面 ⌀3.2 嘴 (XGZP 接管), y 对齐壳 R 壁 XGZP 引压孔 (53.4) 供管垂直下行
SENS_TAP = (MAN_X1, 53.4, 50.0)           # (x, y, z) 嘴根心; 嘴伸出 5mm +X
# 支腿 4× 8×8 (z 21.5..44): 仅立于盖沿实体带 (避通风栅 x 14.9..82.9/y 20.9..62.9)、
# M3 螺丝头 (ST 壳系 ±2.5) 与阀足印 (通道阵 x 12.5..84.5 / 主阀 y 13.9..49.4)。
MAN_LEGS = [(6.0, 16.0), (6.0, 74.0), (98.0, 8.0), (98.0, 80.0)]

# ---------- 主壳壁气口阵列 (气路穿壁位, 位置按阀阵/主阀位推导) ----------
# B 壁 8 通道管过孔 ⌀3.4 (3mm 管 + 0.4 双隙): x = 后行阀列影 + 前行阀列影(+半节距 9.5),
#   z=17.25 = TERM 槽顶 15.4 与天花底 19.1 之间实体带中心 (⌀3.4 → 15.55..18.95,
#   双侧 0.15 余隙, 与 8 槽/天花板均不连通)。
PORT_D_CH, PORT_Z_CH = 3.4, 17.25
CH_PORT_X = [c for cx in V_COLS for c in (cx, cx + 9.5)]   # 20,29.5,39,48.5,58,67.5,77,86.5
# R 壁下带 (z=5.0, 槽底 8.8 之下/底板之上实体区): S/V 泵对接快插 ⌀5.6×2 (5mm 管) +
#   F 排气 ⌀4.8 + XGZP 引压 ⌀3.4; y 与 J20/J21/J22 一致 (20.4/31.4/42.4), XGZP
#   让 J23 槽带 (45..56) 下移至 53.4 (孔带 51.7..55.1 与槽 z 8.8..15.4 无叠)。
PORT_Z_LOW = 5.0
PORT_D_SV, PORT_D_F, PORT_D_SENS = 5.6, 4.8, 3.4
# PORT_D_F 来源: VF (F0520D) 排大气口, 通径真值 ⌀3.0 (pneumatic_devices valves.port.dia_mm)
#   —— 排大气无接管/无密封要求, 经验裕量取通道孔 ⌀3.4 大一级 (降排气背压), 非真值推导。
# 天花板 XGZP 测压管过孔 ⌀3.4 @ (48.5, 27.0): 落通风栅列隙 46.9..50.9 / 行隙 24.9..28.9
#   交叉实体点; 圆心到最近栅孔角 (46.9, 28.9) 距 2.48 → 孔缘余 ≈0.78mm 保证不并孔。
CEIL_SENS = (48.5, 27.0)

def wall_holes():
    """[(face, u 沿边坐标, z, dia, tag)] — 壁面圆孔阵列 (make_case 圆柱贯穿 cut)."""
    hs = [("B", x, PORT_Z_CH, PORT_D_CH, "CH%d" % (i + 1)) for i, x in enumerate(CH_PORT_X)]
    hs += [("R", 20.4, PORT_Z_LOW, PORT_D_SV, "S"),
           ("R", 31.4, PORT_Z_LOW, PORT_D_SV, "V"),
           ("R", 42.4, PORT_Z_LOW, PORT_D_F, "F"),
           ("R", 53.4, PORT_Z_LOW, PORT_D_SENS, "XGZP")]
    return hs

# ---------- 泵模块 (1h 分装式, 独立小盒) ----------
PMOD_WALL = 2.4                            # 壁厚 (与主壳同工艺)
PMOD_CLR = 2.0                             # 泵-壁装配间隙 (含嘴接管弯曲余量)
# 支架: 致荣硅胶环 ID23/OD26 (过盈夹持 ⌀24 泵体, devices.json bracket 真值);
# 孪生建模取 ID24.2 (+0.2 装配间隙) 令 FCL 干涉守门 0.000 —— 真值在 devices.json,
# 孪生是视觉件 (注释即推导)。脚距 46 = 两环 M3 脚沿泵轴间距, 环宽 8。
BKT_ID, BKT_OD, BKT_W, BKT_SPAN = 24.2, 26.0, 8.0, 46.0
BKT_FOOT_T = 3.0                            # 环下 M3 脚垫厚
PMOD_IN_L = _PNEU["pump_l"] + 2 * PMOD_CLR   # 62.1 内腔长 (X, 泵横躺轴向)
PMOD_IN_W = _PNEU["pump_dia"] + 2 * PMOD_CLR # 28.0 内腔宽
# 内腔高 = 腔底起: 脚垫 3 + 环外径半 13 (泵轴) + 轴上嘴顶 (总高 31.5 - ⌀24/2 = 19.5)
#   + 1.0 顶隙 = 36.5
PMOD_IN_H = BKT_FOOT_T + BKT_OD / 2.0 + (_PNEU["pump_h"] - _PNEU["pump_dia"] / 2.0) + 1.0
PMOD_L = PMOD_IN_L + 2 * PMOD_WALL           # 66.9 外长
PMOD_W = PMOD_IN_W + 2 * PMOD_WALL           # 32.8 外宽
PMOD_H = PMOD_IN_H + 2 * PMOD_WALL           # 41.3 外高
PUMP_AXIS_Z = PMOD_WALL + BKT_FOOT_T + BKT_OD / 2.0   # 18.4 泵轴 z (模块系: 腔底+脚+环)
PMOD_CX, PMOD_CY = PMOD_L / 2.0, PMOD_W / 2.0         # 33.45 / 16.4 泵位心 (模块系)
PUMP_NOZ_DX = [-14.0, -4.0]                 # 双顶嘴相对泵心 x 偏移 (头端 -X, 实物照估值)
# 面板 (X+ 端面): 双快插 ⌀5.6 (充/吸 5mm 管, 内接跳管至双顶嘴) + JST 2P 出线孔 ⌀5.0
PMOD_PORT_D, PMOD_PORT_DY, PMOD_WIRE_D = 5.6, 8.0, 5.0
PMOD_WIRE_Z = 6.0                           # 出线孔 z (腔底带, 电机引线端)
# 双体装配位姿 (孪生/装配契约): 泵模块置于主壳 +X 侧, 同桌面 z0=0, y 居中
PMOD_OFF = (OW + 30.0, (OH - PMOD_W) / 2.0, 0.0)   # (135.8, 26.5, 0)

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

# ---------- 孪生爆炸视图契约 (T6 双体: 主模块塔层 + 泵模块 X 向分离) ----------
# 主模块 z 分层 (爆炸后 z 带两两分离, L3 断言): bottom[-20..-0.9] < pcb[7.4..9] <
# parts_F[23..30.0] < case_top[42.1..51.5] < valves[52..89] < manifold[91.5..127]。
# (D4 2026-10-05: devices3d 精确阀阵 bbox 拉高为 z[13..50] —— VV 承插悬置态 N1 嘴尖
#  50.0 / N2 嘴 13.0 隐入腔内 ( datasheet 本体 28+嘴 6 直推)。提档两个动因, 如实区分:
#  ① valves 36.5→39: 旧阀带与 case_top 带交叠 4mm (属实), 提档让出净空;
#  ② manifold 68→70: 旧档 manifold 带 [89.5..125] 与旧阀带本无交叠, 提档是新阀带
#   [52..89] 位置联调所需 (让出层间 2.5mm 净空)。联调定档 valves 39 / case_top 30 /
#  manifold 70, 层间净空 0.5/2.5mm, L3 两两分离断言绿。)
# 泵模块 (装配位 x 135.8..202.7): 泵壳整体 +Z46 揭盖, 泵/支架留位 (环抱嵌套按设计,
# 固体间隙由 FCL 守门; 视觉气管 tubes 不爆)。
BBOX_MM = [PMOD_OFF[0] + PMOD_L, OH, MAN_Z1]   # 双体装配态并包 [202.7, 85.8, 57.0]
EXPLODE = {
    "manifold":    [0, 0, 70],
    "valves":      [0, 0, 39],
    "case_top":    [0, 0, 30],
    "parts_F":     [0, 0, 14],
    "pcb":         [0, 0, 0],
    "case_bottom": [0, 0, -20],
    "pump_case":   [0, 0, 46],
    "pump":        [0, 0, 0],
    "brackets":    [0, 0, 0],
    "tubes":       [0, 0, 0],
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
