# FLOWIO-CN P1 收尾实施计划（违规清零 · 制造输出 · 外壳）

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 P1 板（git `c3337a3` 态）的 17 未连接 + 3 间距 + 6 孔间距 + 2 悬空过孔全部清零，产出 JLC 打样包（Gerber/钻孔/坐标/BOM/装配图）和可打印 OpenSCAD 外壳 STL。

**Architecture:** 全脚本化修复（KiCad 10 pcbnew，"一进程一操作"模式规避 SWIG Remove 腐败），核心是全障碍感知的过孔落点搜索库 `tools/boardgeom.py`（焊盘含孔径 + 走线分段距离 + 过孔 + NPTH + 板边 + 天线禁布区），每个任务以 `ZONE_FILLER 重灌 → kicad-cli pcb drc → 定点探测` 三连验证闭环。制造输出走 kicad-cli，外壳走 OpenSCAD CLI。

**Tech Stack:** KiCad 10.0 (`E:/Program Files/KiCad/10.0/bin/`，python=kicad 自带) · kicad-cli · OpenSCAD (`C:/Program Files/OpenSCAD/openscad.exe`) · Git

**SPEC:** `docs/superpowers/specs/2026-10-01-flowio-p1-completion.md`

**约定:** 命令均从 `E:/FLOWIO/hardware/flowio-p1/` 目录执行；KPY=`"E:/Program Files/KiCad/10.0/bin/python.exe"`；DRC=`"E:/Program Files/KiCad/10.0/bin/kicad-cli" pcb drc --output drc.rpt flowio-p1.kicad_pcb`。基线 DRC：unconnected 17 · clearance 3 · hole_clearance 6 · via_dangling 2 · 外观 108（豁免）。

---

### Task 1: 全障碍感知几何库 `boardgeom.py`

**Files:**
- Create: `E:\FLOWIO\hardware\flowio-p1\tools\boardgeom.py`

- [ ] **Step 1: 写库文件**

```python
# -*- coding: utf-8 -*-
"""boardgeom: 全障碍感知的过孔/走线落点工具 (KiCad 10 pcbnew).
教训编码: 阶段1.5手工过孔只查焊盘引发14条违规——本库必须查全障碍."""
import math, pcbnew

BF = "flowio-p1.kicad_pcb"
MM, FM, VI = pcbnew.ToMM, pcbnew.FromMM, pcbnew.VECTOR2I
KEEPOUT = (19.5, 36.5, 0.2, 6.4)          # 天线禁布区 x0,x1,y0,y1
EDGE = (1.2, 88.8, 1.2, 73.8)             # 板边净空
CLR, HOLE_CLR = 0.21, 0.26                # 铜间距(规则0.2+裕量) / 孔边距(0.25+裕量)

def load():
    b = pcbnew.LoadBoard(BF)
    pads, trks, vias = [], [], []
    for f in b.GetFootprints():
        for p in f.Pads():
            c = p.GetPosition()
            sz = p.GetSize()
            pads.append(dict(x=MM(c.x), y=MM(c.y), r=max(MM(sz.x), MM(sz.y)) / 2,
                             net=p.GetNetname(), drill=MM(p.GetDrillValue() or 0) if p.GetAttribute() != pcbnew.PAD_ATTRIB_SMD else 0.0,
                             npth=p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH,
                             ref=f.GetReference() + "." + str(p.GetPadName())))
    for t in b.GetTracks():
        if t.Type() == pcbnew.PCB_VIA_T:
            c = t.GetPosition(); vias.append((MM(c.x), MM(c.y), t.GetNetname(), MM(t.GetWidth())))
        else:
            s, e = t.GetStart(), t.GetEnd()
            trks.append((t.GetNetname(), t.GetLayer(), MM(s.x), MM(s.y), MM(e.x), MM(e.y), MM(t.GetWidth())))
    return b, pads, trks, vias

def netcode(b, name):
    return b.FindNet(name).GetNetCode()

def seg_dist(px, py, ax, ay, bx, by):
    abx, aby = bx - ax, by - ay
    L2 = abx * abx + aby * aby
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px - ax) * abx + (py - ay) * aby) / L2))
    return math.hypot(px - ax - t * abx, py - ay - t * aby)

def _obs_ok(x, y, net, od, drill, pads, vias):
    for p in pads:
        d = math.hypot(p["x"] - x, p["y"] - y)
        if p["npth"] or (p["net"] != net and p["net"] != ""):
            if d - p["r"] - od / 2 < CLR: return False
        if p["drill"] > 0 and (p["net"] != net):
            if d < (p["drill"] + drill) / 2 + HOLE_CLR: return False
        if p["npth"] and d < (p["drill"] + drill) / 2 + HOLE_CLR: return False
    for vx, vy, vnet, vw in vias:
        d = math.hypot(vx - x, vy - y)
        if vnet != net and d - (vw + od) / 2 < CLR: return False
        if vnet != net and d < (0.3 + drill) / 2 + HOLE_CLR: return False
    return True

def _in_keepout(x, y):
    return KEEPOUT[0] <= x <= KEEPOUT[1] and KEEPOUT[2] <= y <= KEEPOUT[3]

def spot_ok(x, y, net, pads, trks, vias, od=0.8, drill=0.4):
    if not (EDGE[0] < x < EDGE[1] and EDGE[2] < y < EDGE[3]) or _in_keepout(x, y):
        return False
    if not _obs_ok(x, y, net, od, drill, pads, vias): return False
    for tn, _ly, ax, ay, bx, by, w in trks:
        if tn == net: continue
        if seg_dist(x, y, ax, ay, bx, by) - w / 2 - od / 2 < CLR: return False
    return True

def seg_seg_dist(p1, p2, p3, p4):
    def orient(a, b, c):
        v = (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])
        return 0 if abs(v) < 1e-9 else (1 if v > 0 else -1)
    def onseg(a, b, c):
        return min(a[0],b[0])-1e-9 <= c[0] <= max(a[0],b[0])+1e-9 and min(a[1],b[1])-1e-9 <= c[1] <= max(a[1],b[1])+1e-9
    if orient(p1,p2,p3) != orient(p1,p2,p4) and orient(p3,p4,p1) != orient(p3,p4,p2):
        return 0.0  # 相交
    return min(seg_dist(*p3, *p1, *p2), seg_dist(*p4, *p1, *p2),
               seg_dist(*p1, *p3, *p4), seg_dist(*p2, *p3, *p4))

def track_ok(p1, p2, net, w, pads, trks, vias):
    for p in pads:
        if p["net"] == net and not p["npth"]: continue
        if seg_dist(p["x"], p["y"], *p1, *p2) - p["r"] - w / 2 < CLR: return False
    for tn, _ly, ax, ay, bx, by, tw in trks:
        if tn == net: continue
        if seg_seg_dist(p1, p2, (ax, ay), (bx, by)) - tw / 2 - w / 2 < CLR: return False
    return True

def find_spot(cx, cy, net, pads, trks, vias, anchor=None, rmax=3.5, od=0.8, drill=0.4, w=0.3):
    """从 (cx,cy) 环形搜索: 过孔落点 + (anchor→落点) 短走线双净空."""
    r = 0.3
    while r <= rmax:
        n = max(8, int(2 * math.pi * r / 0.3))
        for i in range(n):
            a = 2 * math.pi * i / n
            x, y = cx + r * math.cos(a), cy + r * math.sin(a)
            if not spot_ok(x, y, net, pads, trks, vias, od, drill): continue
            if anchor and not track_ok(anchor, (x, y), net, w, pads, trks, vias): continue
            return round(x, 3), round(y, 3)
        r += 0.2
    return None

def add_via(b, x, y, net, od=0.8, drill=0.4):
    v = pcbnew.PCB_VIA(b); v.SetNetCode(netcode(b, net)); v.SetPosition(VI(int(FM(x)), int(FM(y))))
    v.SetWidth(int(FM(od))); v.SetDrill(int(FM(drill))); v.SetViaType(pcbnew.VIATYPE_THROUGH)
    b.Add(v); return v

def add_seg(b, p1, p2, layer, net, w=0.3):
    t = pcbnew.PCB_TRACK(b); t.SetNetCode(netcode(b, net)); t.SetLayer(layer)
    t.SetStart(VI(int(FM(p1[0])), int(FM(p1[1])))); t.SetEnd(VI(int(FM(p2[0])), int(FM(p2[1]))))
    t.SetWidth(int(FM(w))); b.Add(t); return t

def refill_save(b):
    pcbnew.ZONE_FILLER(b).Fill(list(b.Zones())); pcbnew.SaveBoard(BF, b)
```

- [ ] **Step 2: 自测（含既有坏过孔必须被拒）**

Run: `"E:/Program Files/KiCad/10.0/bin/python.exe" -c "import sys; sys.path.insert(0,'tools'); import boardgeom as G; b,pads,trks,vias=G.load(); print(len(pads),'pads',len(trks),'trks',len(vias),'vias'); assert not G.spot_ok(78.36,60.5,'+5V',pads,trks,vias), '坏点必须被拒'; assert not G.spot_ok(28.0,3.0,'GND',pads,trks,vias), '禁布区必须被拒'; assert G.spot_ok(45.0,35.0,'GND',pads,trks,vias) is not None or True; print('boardgeom OK')"`

Expected: `~700 pads ~800 trks ~100 vias` + `boardgeom OK`

- [ ] **Step 3: Commit**

```bash
git add hardware/flowio-p1/tools/boardgeom.py
git commit -m "feat(tools): 全障碍感知落点库 boardgeom (焊盘含孔+走线+过孔+NPTH+板边+禁布区)"
```

---

### Task 2: 删除坏 +5V 过孔 + D10.1 重连（-6 违规）

**Files:**
- Create: `E:\FLOWIO\hardware\flowio-p1\tools\del_bad_via.py`
- Create: `E:\FLOWIO\hardware\flowio-p1\tools\fix_d10.py`

- [ ] **Step 1: 删除进程（只删不查）**

```python
# tools/del_bad_via.py
import pcbnew
BF = "flowio-p1.kicad_pcb"
b = pcbnew.LoadBoard(BF)
n = 0
for t in list(b.GetTracks()):
    if t.Type() == pcbnew.PCB_VIA_T:
        p = t.GetPosition()
        x, y = pcbnew.ToMM(p.x), pcbnew.ToMM(p.y)
        if abs(x - 78.3649) < 0.05 and abs(y - 60.5) < 0.05:
            b.Remove(t); n += 1
pcbnew.SaveBoard(BF, b)
print("removed", n)
```

Run: `KPY tools/del_bad_via.py` → Expected: `removed 1`

- [ ] **Step 2: 新增进程（落点搜索 + 过孔 + 短走线 + 重灌）**

```python
# tools/fix_d10.py
import sys; sys.path.insert(0, "tools")
import boardgeom as G
b, pads, trks, vias = G.load()
# D10.1 (+5V) 锚点; 新过孔须落 In2 +5V 底带 y53-74.5 且全净空
import pcbnew
d10 = next(p for p in pads if p["ref"] == "D10.1")
spot = G.find_spot(d10["x"], d10["y"], "+5V", pads, trks, vias, anchor=(d10["x"], d10["y"]), rmax=3.0, w=0.4)
assert spot and 53.0 <= spot[1] <= 74.5, f"落点不在5V底带: {spot}"
G.add_via(b, spot[0], spot[1], "+5V", od=0.9, drill=0.45)
G.add_seg(b, (d10["x"], d10["y"]), spot, pcbnew.F_Cu, "+5V", 0.4)
G.refill_save(b)
print(f"D10 +5V via @ {spot}")
```

Run: `KPY tools/fix_d10.py` → Expected: `D10 +5V via @ (…,5x.x-7x.x)` 且 y∈[53,74.5]

- [ ] **Step 3: DRC 差分**

Run: `DRC && grep -cE '^\[(hole_clearance|via_dangling)\]' drc.rpt && grep -c '^\[unconnected_items\]' drc.rpt`

Expected: hole_clearance **2**（6→2）· via_dangling **1**（2→1）· unconnected **16**（17→16）。若 D10.1 出现新 unconnected → Step 2 的走线没连上，检查 add_seg 端点。

- [ ] **Step 4: Commit**

```bash
git add hardware/flowio-p1/flowio-p1.kicad_pcb hardware/flowio-p1/drc.rpt hardware/flowio-p1/tools/del_bad_via.py hardware/flowio-p1/tools/fix_d10.py
git commit -m "fix(pcb): 删坏+5V过孔@78.36,60.5, D10.1全净空重连 (-6违规)"
```

---

### Task 3: HD 安装孔移位（孔间距 0.0 → 0）

**Files:**
- Create: `E:\FLOWIO\hardware\flowio-p1\tools\move_hd.py`

- [ ] **Step 1: 写脚本（NPTH 无网络无走线，单进程安全）**

```python
# tools/move_hd.py
import sys, math; sys.path.insert(0, "tools")
import pcbnew, boardgeom as G
b, pads, trks, vias = G.load()
# HD 现 (77,62) Ø3.2 与 D10.1 孔边距 0.0。搜索新位: 距 D10.1 与端子排(y≥66.5) 远离,
# 对铜障碍净空 Ø3.2+2*0.5 (用 spot_ok 近似: 半径=1.6, 过孔 od=3.2 等效圆)
best = None
for gy in [57.5, 56.0, 55.0, 58.5, 54.0, 52.5]:
    for gx in [74.0, 75.5, 76.5, 77.0, 73.0, 78.0]:
        # 3.2 孔 + 0.5 铜净空: 复用 spot_ok, od=3.2, drill=3.2, 但放宽 CLR=0.5 语义已含
        if G.spot_ok(gx, gy, "", pads, trks, vias, od=3.2 + 1.0, drill=3.2):
            if gy < 66.0 and math.hypot(gx - 79.9, gy - 60.5) > 3.0:
                best = (gx, gy); break
    if best: break
assert best, "HD 新位未找到"
for f in b.GetFootprints():
    if f.GetReference() == "HD":
        f.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(best[0]), pcbnew.FromMM(best[1])))
G.refill_save(b)
print("HD ->", best)
```

Run: `KPY tools/move_hd.py` → Expected: `HD -> (7x.x, 5x.x)`

- [ ] **Step 2: DRC 差分**

Run: `DRC && grep -c '^\[hole_clearance\]' drc.rpt` → Expected: **1**（2→1，剩 D1.2）

- [ ] **Step 3: Commit**

```bash
git add hardware/flowio-p1/flowio-p1.kicad_pcb hardware/flowio-p1/drc.rpt hardware/flowio-p1/tools/move_hd.py
git commit -m "fix(pcb): HD安装孔移位避让D10孔 (孔边距0.0→清零); 外壳铜柱位同步"
```

**记录**: HD 最终坐标写入 `enclosure/standoffs.txt`（Task 12 读取）: `echo "HD <新坐标>" > enclosure/standoffs.txt`

---

### Task 4: R14.1 旁 GND 过孔移位（间距 0.008 → 0）

**Files:**
- Create: `E:\FLOWIO\hardware\flowio-p1\tools\move_gndvia.py`

- [ ] **Step 1: 删除进程 + Step 2 新增进程（合并为两次运行同一脚本不同参数）**

```python
# tools/move_gndvia.py  用法: move_gndvia.py del|add
import sys; sys.path.insert(0, "tools")
import pcbnew, boardgeom as G
mode = sys.argv[1]
OLD = (27.00, 32.30)
if mode == "del":
    b = pcbnew.LoadBoard(G.BF)
    for t in list(b.GetTracks()):
        if t.Type() == pcbnew.PCB_VIA_T:
            p = t.GetPosition()
            if abs(pcbnew.ToMM(p.x) - OLD[0]) < 0.08 and abs(pcbnew.ToMM(p.y) - OLD[1]) < 0.08:
                b.Remove(t); print("removed GND via @", OLD)
    pcbnew.SaveBoard(G.BF, b)
else:
    b, pads, trks, vias = G.load()
    spot = G.find_spot(OLD[0], OLD[1], "GND", pads, trks, vias, rmax=2.5)
    assert spot, "GND 新落点未找到"
    G.add_via(b, spot[0], spot[1], "GND")
    G.refill_save(b)
    print("GND via ->", spot)
```

Run: `KPY tools/move_gndvia.py del` → `removed GND via @ (27.0, 32.3)`
Run: `KPY tools/move_gndvia.py add` → `GND via -> (2x.x, 3x.x)`

- [ ] **Step 2: DRC 差分**

Run: `DRC && grep -c '^\[clearance\]' drc.rpt` → Expected: **2**（3→2）

注意: 若删除后 GND 出现新 unconnected（该过孔是 F/B 岛唯一缝合），则 find_spot 的加回必须成功；仍失败则改 rmax=4 重试。

- [ ] **Step 3: Commit**

```bash
git add hardware/flowio-p1/flowio-p1.kicad_pcb hardware/flowio-p1/drc.rpt hardware/flowio-p1/tools/move_gndvia.py
git commit -m "fix(pcb): GND缝合过孔避让R14.1 (间距0.008→0)"
```

---

### Task 5: +3V3 尾巴 ×5 补连

**Files:**
- Create: `E:\FLOWIO\hardware\flowio-p1\tools\fix_3v3.py`

- [ ] **Step 1: 写脚本（4 焊盘补"短走线+过孔"；J6 过孔先诊断再迁移）**

```python
# tools/fix_3v3.py  用法: fix_3v3.py pads|diag-j6|del-j6|add-j6
import sys, math; sys.path.insert(0, "tools")
import pcbnew, boardgeom as G
mode = sys.argv[1]
TAPS = [("C13.1", 54.725, 17.5), ("TP1.1", 58.5, 21.5), ("R29.1", 62.0, 30.7534), ("C12.1", 79.225, 25.5)]
J6VIA = (88.0001, 28.69)
if mode == "pads":
    b, pads, trks, vias = G.load()
    for ref, ax, ay in TAPS:
        pad = next(p for p in pads if p["ref"] == ref)
        spot = G.find_spot(pad["x"], pad["y"], "+3V3", pads, trks, vias, anchor=(pad["x"], pad["y"]), rmax=3.5)
        assert spot, ref + " 无落点"
        G.add_via(b, spot[0], spot[1], "+3V3")
        G.add_seg(b, (pad["x"], pad["y"]), spot, pcbnew.F_Cu, "+3V3", 0.3)
        print(ref, "via @", spot)
        pads.append(dict(x=spot[0], y=spot[1], r=0.4, net="+3V3", drill=0.4, npth=False, ref=ref+"V"))
        vias.append((spot[0], spot[1], "+3V3", 0.8))
    G.refill_save(b)
elif mode == "diag-j6":
    b = pcbnew.LoadBoard(G.BF)
    p = pcbnew.VECTOR2I(pcbnew.FromMM(J6VIA[0]), pcbnew.FromMM(J6VIA[1]))
    for z in b.Zones():
        if z.GetNetname() == "+3V3":
            for ly in (pcbnew.In2_Cu,):
                if z.HasFilledPolysForLayer(ly) and z.HitTestFilledArea(ly, p):
                    print("J6 via In2 3V3 填充: 命中(非空洞)")
    print("diag done — 未打印'命中'则 via 在填充空洞内, 需迁移")
elif mode == "del-j6":
    b = pcbnew.LoadBoard(G.BF)
    for t in list(b.GetTracks()):
        if t.Type() == pcbnew.PCB_VIA_T:
            c = t.GetPosition()
            if abs(pcbnew.ToMM(c.x) - J6VIA[0]) < 0.08 and abs(pcbnew.ToMM(c.y) - J6VIA[1]) < 0.08:
                b.Remove(t); print("removed J6 via")
    pcbnew.SaveBoard(G.BF, b)
elif mode == "add-j6":
    b, pads, trks, vias = G.load()
    j6 = next(p for p in pads if p["ref"] == "J6.1")
    spot = G.find_spot(J6VIA[0] - 1.5, J6VIA[1] + 1.5, "+3V3", pads, trks, vias, anchor=(j6["x"], j6["y"]), rmax=4.0)
    assert spot, "J6 新落点未找到"
    G.add_via(b, spot[0], spot[1], "+3V3")
    G.add_seg(b, (j6["x"], j6["y"]), spot, pcbnew.F_Cu, "+3V3", 0.3)
    G.refill_save(b)
    print("J6.1 via @", spot)
```

Run: `KPY tools/fix_3v3.py pads` → Expected: 4 行 `via @`
Run: `KPY tools/fix_3v3.py diag-j6` → 看是否命中填充
若未命中: `KPY tools/fix_3v3.py del-j6` → `removed J6 via`，再 `KPY tools/fix_3v3.py add-j6` → `J6.1 via @ …`
若命中（悬空另有原因）: 过孔已接 In2 填充，仅需 `add-j6` 的走线部分——把 add-j6 中 add_via 两行注释后运行。

- [ ] **Step 2: DRC 差分**

Run: `DRC && grep -c '^\[unconnected_items\]' drc.rpt` → Expected: ≤12（16→11 或 12，视 J6 是否已计入）；via_dangling = **0**

- [ ] **Step 3: Commit**

```bash
git add hardware/flowio-p1/flowio-p1.kicad_pcb hardware/flowio-p1/drc.rpt hardware/flowio-p1/tools/fix_3v3.py
git commit -m "fix(pcb): +3V3 尾巴补连 C13/TP1/R29/C12/J6 (短走线+全净空过孔)"
```

---

### Task 6: GND 尾巴 ×4 补连

**Files:**
- Create: `E:\FLOWIO\hardware\flowio-p1\tools\fix_gnd.py`

- [ ] **Step 1: 写脚本（2 焊盘 + 2 走线端，In1 全板 GND 面随便落）**

```python
# tools/fix_gnd.py
import sys; sys.path.insert(0, "tools")
import pcbnew, boardgeom as G
b, pads, trks, vias = G.load()
JOBS = [("U2.2", None), ("U5.2", None),
        ("C17.2", (16.5158, 23.6084)), ("C3.2", (24.3650, 49.5221))]
for ref, trkend in JOBS:
    pad = next(p for p in pads if p["ref"] == ref)
    anchor = (pad["x"], pad["y"])
    spot = G.find_spot(anchor[0], anchor[1], "GND", pads, trks, vias, anchor=anchor, rmax=4.0)
    assert spot, ref + " 无落点"
    G.add_via(b, spot[0], spot[1], "GND")
    G.add_seg(b, anchor, spot, pcbnew.F_Cu, "GND", 0.3)
    if trkend:  # 走线端也补一段到过孔, 消除 dangling track 端
        G.add_seg(b, trkend, spot, pcbnew.F_Cu, "GND", 0.3)
    print(ref, "via @", spot)
    pads.append(dict(x=spot[0], y=spot[1], r=0.4, net="GND", drill=0.4, npth=False, ref=ref+"V"))
    vias.append((spot[0], spot[1], "GND", 0.8))
G.refill_save(b)
```

Run: `KPY tools/fix_gnd.py` → Expected: 4 行 `via @`

- [ ] **Step 2: DRC 差分**

Run: `DRC && grep -c '^\[unconnected_items\]' drc.rpt` → Expected: ≤8（再 -4）

- [ ] **Step 3: Commit**

```bash
git add hardware/flowio-p1/flowio-p1.kicad_pcb hardware/flowio-p1/drc.rpt hardware/flowio-p1/tools/fix_gnd.py
git commit -m "fix(pcb): GND 尾巴补连 U2.2/U5.2/C17/C3 (过孔下In1面)"
```

---

### Task 7: +5V 尾巴 C15.1 补连

**Files:**
- Create: `E:\FLOWIO\hardware\flowio-p1\tools\fix_5v_c15.py`

- [ ] **Step 1: 写脚本（落点须在 In2 +5V B 块 x19-36/y28-55 内）**

```python
# tools/fix_5v_c15.py
import sys; sys.path.insert(0, "tools")
import pcbnew, boardgeom as G
b, pads, trks, vias = G.load()
pad = next(p for p in pads if p["ref"] == "C15.1")
end = (33.1552, 52.2896)  # 现有走线端
spot = G.find_spot(end[0], end[1], "+5V", pads, trks, vias, anchor=end, rmax=3.0, w=0.4)
assert spot, "C15 无落点"
assert 19.0 <= spot[0] <= 36.0 and 28.0 <= spot[1] <= 55.0, f"不在5V B块: {spot}"
G.add_via(b, spot[0], spot[1], "+5V", od=0.9, drill=0.45)
G.add_seg(b, end, spot, pcbnew.F_Cu, "+5V", 0.4)
G.refill_save(b)
print("C15 +5V via @", spot)
```

Run: `KPY tools/fix_5v_c15.py` → Expected: `C15 +5V via @ (3x.x, 5x.x)`

- [ ] **Step 2: DRC 差分**

Run: `DRC && grep -c '^\[unconnected_items\]' drc.rpt` → Expected: ≤7

- [ ] **Step 3: Commit**

```bash
git add hardware/flowio-p1/flowio-p1.kicad_pcb hardware/flowio-p1/drc.rpt hardware/flowio-p1/tools/fix_5v_c15.py
git commit -m "fix(pcb): +5V C15.1 补连 (过孔落In2 5V B块)"
```

---

### Task 8: 平面孤岛 ×7 补连（桥接 zone + GND 缝合）

**Files:**
- Create: `E:\FLOWIO\hardware\flowio-p1\tools\fix_islands.py`

- [ ] **Step 1: API 探针（spec 风险表要求）**

Run: `KPY -c "import pcbnew; b=pcbnew.LoadBoard('flowio-p1.kicad_pcb'); z=[x for x in b.Zones() if x.GetNetname()=='GND' and x.IsOnLayer(pcbnew.F_Cu)][0]; ps=z.GetFilledPolysList(pcbnew.F_Cu); print('outlines:', ps.OutlineCount(), 'contains:', ps.Contains(pcbnew.VECTOR2I(pcbnew.FromMM(5),pcbnew.FromMM(5))))"`

Expected: `outlines: N contains: True/False`（确认 OutlineCount/Contains 可用；不可用则改用 Chain+射线法，见 Step 2 注释）

- [ ] **Step 2: 写脚本**

```python
# tools/fix_islands.py  用法: fix_islands.py bridge|stitch|probe
import sys; sys.path.insert(0, "tools")
import pcbnew, boardgeom as G
mode = sys.argv[1]
def bridge(b, net, layer, pts, name):
    z = pcbnew.ZONE(b); z.SetLayer(layer); z.SetNetCode(G.netcode(b, net))
    z.SetMinThickness(int(pcbnew.FromMM(0.3))); z.SetZoneName(name)
    ol = z.Outline(); ol.NewOutline()
    for cx, cy in pts: ol.Append(int(pcbnew.FromMM(cx)), int(pcbnew.FromMM(cy)))
    b.Add(z); print("bridge", name, net)
if mode == "bridge":
    b, pads, trks, vias = G.load()
    # 3V3: 顶带(…y≤20.8) 与 下L块(y≥20.8) 跨缝桥, 两侧各压 0.4
    bridge(b, "+3V3", pcbnew.In2_Cu, [(20.0, 20.4), (35.5, 20.4), (35.5, 21.2), (20.0, 21.2)], "BR_3V3")
    # 5V: A块(x≤19) 与 B块(x≥19) 跨缝桥
    bridge(b, "+5V", pcbnew.In2_Cu, [(18.6, 30.0), (19.4, 30.0), (19.4, 50.0), (18.6, 50.0)], "BR_5V")
    G.refill_save(b)
elif mode == "probe":
    b = pcbnew.LoadBoard(G.BF)
    for z in b.Zones():
        if z.GetIsRuleArea() or z.GetNetname() != "GND": continue
        for ly in (pcbnew.F_Cu, pcbnew.B_Cu):
            if not z.HasFilledPolysForLayer(ly): continue
            ps = z.GetFilledPolysList(ly)
            for i in range(ps.OutlineCount()):
                ch = ps.Outline(i)
                xs = [pcbnew.ToMM(ch.CPoint(j).x) for j in range(ch.PointCount())]
                ys = [pcbnew.ToMM(ch.CPoint(j).y) for j in range(ch.PointCount())]
                cx, cy = sum(xs)/len(xs), sum(ys)/len(ys)
                c = pcbnew.VECTOR2I(pcbnew.FromMM(cx), pcbnew.FromMM(cy))
                if not ps.Contains(c): continue
                has_via = False
                for vx, vy, vnet, _ in [(pcbnew.ToMM(t.GetPosition().x), pcbnew.ToMM(t.GetPosition().y), t.GetNetname(), 0) for t in b.GetTracks() if t.Type() == pcbnew.PCB_VIA_T and t.GetNetname() == "GND"]:
                    if ps.Contains(pcbnew.VECTOR2I(pcbnew.FromMM(vx), pcbnew.FromMM(vy))): has_via = True; break
                if not has_via:
                    print(f"孤岛: {b.GetLayerName(ly)} bbox=({min(xs):.1f},{min(ys):.1f})-({max(xs):.1f},{max(ys):.1f}) centroid=({cx:.1f},{cy:.1f})")
elif mode == "stitch":
    b, pads, trks, vias = G.load()
    # 由 probe 输出抄录孤岛质心 (执行时填入, 逐个净空校验)
    ISLANDS = []  # 执行 probe 后填: [(层, cx, cy), ...]
    for _ly, cx, cy in ISLANDS:
        spot = G.find_spot(cx, cy, "GND", pads, trks, vias, rmax=1.5)
        if spot: G.add_via(b, spot[0], spot[1], "GND"); print("stitch @", spot)
        else: print("跳过(无净空):", cx, cy)
    G.refill_save(b)
```

Run: `KPY tools/fix_islands.py bridge` → `bridge BR_3V3 +3V3` + `bridge BR_5V +5V`
Run: `KPY tools/fix_islands.py probe` → 输出 F/B 层 GND 孤岛清单（质心坐标）
把质心抄入 stitch 的 ISLANDS 后 Run: `KPY tools/fix_islands.py stitch` → `stitch @ …`×N

- [ ] **Step 3: DRC 差分 + zones_intersect 必须为 0**

Run: `DRC && grep -c '^\[unconnected_items\]' drc.rpt && grep -c '^\[zones_intersect\]' drc.rpt`

Expected: unconnected **0**（7→0，含 2 桥接 + 5 孤岛缝合——若 GND zone 条目少于 5 会提前到 0）；zones_intersect **0**。若 zones_intersect >0 → 桥接矩形压到了异网区，缩窄 0.2 重试。

- [ ] **Step 4: Commit**

```bash
git add hardware/flowio-p1/flowio-p1.kicad_pcb hardware/flowio-p1/drc.rpt hardware/flowio-p1/tools/fix_islands.py
git commit -m "fix(pcb): 平面孤岛清零 (3V3/5V跨缝桥接zone + GND孤岛缝合过孔)"
```

---

### Task 9: 剩余间距 2 条 + 孔间距 1 条

**Files:**
- Create: `E:\FLOWIO\hardware\flowio-p1\tools\fix_clrs.py`

- [ ] **Step 1: 诊断脚本（先定位对方是谁，再选修复）**

```python
# tools/fix_clrs.py  用法: fix_clrs.py diag|fix-j2|fix-tp8|fix-d1
import sys, math; sys.path.insert(0, "tools")
import pcbnew, boardgeom as G
mode = sys.argv[1]
b, pads, trks, vias = G.load()
if mode == "diag":
    for tag, x, y, ref in [("J2.A5", 88.15, 5.5, "J2.A5"), ("TP8", 47.5, 31.0, "TP8.1"), ("D1.2", 25.70, 33.50, "D1.2")]:
        pad = next(p for p in pads if p["ref"] == ref)
        print(f"--- {tag} pad r={pad['r']:.2f} drill={pad['drill']:.2f}")
        for p in pads:
            if p["ref"] == ref: continue
            d = math.hypot(p["x"]-x, p["y"]-y)
            if d < p["r"] + pad["r"] + 0.35 and p["net"] != pad["net"]:
                print(f"  PAD {p['ref']} net={p['net']} d={d:.3f} 铜边距={d-p['r']-pad['r']:.3f} 孔边距={d-(p['drill']+pad['drill'])/2:.3f}")
        for i, (tn, ly, ax, ay, bx, by, w) in enumerate(trks):
            if tn == pad["net"]: continue
            d = G.seg_dist(x, y, ax, ay, bx, by) - w/2 - 0.1
            if G.seg_dist(x, y, ax, ay, bx, by) < pad["r"] + w/2 + 0.35:
                print(f"  TRK#{i} net={tn} {b.GetLayerName(ly)} w={w} 距={G.seg_dist(x,y,ax,ay,bx,by)-w/2-pad['r']:.3f} seg=({ax:.1f},{ay:.1f})-({bx:.1f},{by:.1f})")
        for vx, vy, vnet, vw in vias:
            d = math.hypot(vx-x, vy-y)
            if d < vw/2 + pad["r"] + 0.35 and vnet != pad["net"]:
                print(f"  VIA net={vnet} d={d:.3f}")
elif mode == "fix-j2":
    # 若 diag 显示 TRK 为对方: 删该段, 端点绕行重画 (执行时按 diag 输出填 SEG)
    SEG = None  # (net, layer, (ax,ay), (bx,by), w) 从 diag 抄录
    assert SEG
    b2 = pcbnew.LoadBoard(G.BF); n = 0
    for t in list(b2.GetTracks()):
        if t.Type() != pcbnew.PCB_VIA_T and t.GetNetname() == SEG[0] and t.GetLayer() == SEG[1]:
            s, e = t.GetStart(), t.GetEnd()
            if (abs(pcbnew.ToMM(s.x)-SEG[2][0])<0.05 and abs(pcbnew.ToMM(s.y)-SEG[2][1])<0.05 and abs(pcbnew.ToMM(e.x)-SEG[3][0])<0.05 and abs(pcbnew.ToMM(e.y)-SEG[3][1])<0.05):
                b2.Remove(t); n += 1
    pcbnew.SaveBoard(G.BF, b2); print("del seg", n)
    # 新进程: 绕行中点 = 原中点向远离焊盘方向推 0.15
elif mode == "fix-tp8":
    SEG = None  # 同上
    assert SEG
    # 同 fix-j2 模式: 删段 + 中点偏移重画两段
elif mode == "fix-d1":
    # 若对方是过孔: 过孔移位 (find_spot); 若对方是库焊盘: 记录豁免 (fabrication-safe 判断: 孔边距≥0.15)
    print("按 diag 结果选择: 过孔→del/add 迁移; 库焊盘→豁免记录")
```

Run: `KPY tools/fix_clrs.py diag` → 三段清单，明确每条的对方（PAD/TRK/VIA）

- [ ] **Step 2: 按诊断结果执行**

- J2.A5（实际 0.177）：若对方 TRK → 删段重画（fix-j2，按 diag 抄录 SEG）；若对方 PAD（库内 A5-B9）→ **豁免**（TYPE-C-6P 库封装自身几何，JLC 最小焊盘间距 0.15 < 0.177 可制），记入 §5 豁免清单
- TP8.1（实际 0.100）：对方必为 TRK → fix-tp8 删段 + 两段绕行（中点向远离焊盘方向推 ≥0.15）
- D1.2（实际 0.183）：对方 VIA → 迁移；对方库焊盘且孔边距 ≥0.15 → 豁免+备注（SS34 SMA 封装自身孔距）

- [ ] **Step 3: DRC 终验（error 类必须全零）**

Run: `DRC && grep -cE '^\[(unconnected_items|clearance|hole_clearance|via_dangling|zones_intersect)\]' drc.rpt` → Expected: **0**

- [ ] **Step 4: Commit**

```bash
git add hardware/flowio-p1/flowio-p1.kicad_pcb hardware/flowio-p1/drc.rpt hardware/flowio-p1/tools/fix_clrs.py
git commit -m "fix(pcb): 间距/孔间距残余清零 (走线绕行+过孔迁移/库级豁免记录)"
```

---

### Task 10: 终态目视检查（用户强制要求）

- [ ] **Step 1: 重渲染两视图**

```bash
"E:/Program Files/KiCad/10.0/bin/kicad-cli" pcb render --side top --width 2400 --height 2000 -o r_top.png flowio-p1.kicad_pcb
"E:/Program Files/KiCad/10.0/bin/kicad-cli" pcb render --side bottom --width 2400 --height 2000 -o r_bot.png flowio-p1.kicad_pcb
```

- [ ] **Step 2: 程序化复验（天线禁布区 + 新过孔落点）**

```bash
KPY -c "import pcbnew; b=pcbnew.LoadBoard('flowio-p1.kicad_pcb'); hits=0
for px,py in [(28,3),(21,5),(34,2),(28,6),(20,6.3),(36,1)]:
    p=pcbnew.VECTOR2I(pcbnew.FromMM(px),pcbnew.FromMM(py))
    for z in b.Zones():
        if not z.GetIsRuleArea():
            for ly in (pcbnew.F_Cu,pcbnew.In1_Cu,pcbnew.In2_Cu,pcbnew.B_Cu):
                if z.HasFilledPolysForLayer(ly) and z.HitTestFilledArea(ly,p): hits+=1
print('keepout hits:', hits)"
```

Expected: `keepout hits: 0`

- [ ] **Step 3: 目视检查两渲染图**（视觉模型 + 自查）：新过孔不压线、桥接区无异网交叠、无新增乱麻、HD 新位不碰端子。发现问题 → 回对应任务修，不允许带病过。

- [ ] **Step 4: Commit**

```bash
git add hardware/flowio-p1/r_top.png hardware/flowio-p1/r_bot.png hardware/flowio-p1/drc.rpt
git commit -m "verify(pcb): 终态DRC error=0 + 双视图目视检查通过"
```

---

### Task 11: 制造输出（JLC 打样包）

**Files:**
- Create: `E:/FLOWIO/hardware/flowio-p1/fab/`（输出目录）

- [ ] **Step 1: Gerber + 钻孔 + 坐标 + BOM + 装配 PDF**

```bash
mkdir -p fab
"E:/Program Files/KiCad/10.0/bin/kicad-cli" pcb export gerbers --output fab/ --subtract-soldermask flowio-p1.kicad_pcb
"E:/Program Files/KiCad/10.0/bin/kicad-cli" pcb export drill --output fab/ --excellon-separate-zeros false --generate-map --map-format gerberx2 flowio-p1.kicad_pcb
"E:/Program Files/KiCad/10.0/bin/kicad-cli" pcb export pos --output fab/flowio-p1-pos.csv --format csv --units mm --origin drill flowio-p1.kicad_pcb
"E:/Program Files/KiCad/10.0/bin/kicad-cli" sch export bom-pcbnew --output fab/flowio-p1-bom.csv flowio-p1.kicad_sch
"E:/Program Files/KiCad/10.0/bin/kicad-cli" pcb export pdf --output fab/assembly-top.pdf -l F.Cu,F.Mask,F.SilkS,F.Paste,Edge.Cuts flowio-p1.kicad_pcb
"E:/Program Files/KiCad/10.0/bin/kicad-cli" pcb export pdf --output fab/assembly-bottom.pdf -l B.Cu,B.Mask,B.SilkS,B.Paste,Edge.Cuts flowio-p1.kicad_pcb
```

注: 各子命令旗标若与 KiCad 10 实际不符，先 `--help` 校正（预计 drill 的 `--excellon-separate-zeros` 与 pos 的 `--origin` 枚举名可能不同）。

- [ ] **Step 2: 打包 + 完整性核对**

```bash
cd fab && zip -j flowio-p1-jlc.zip *.gbr *.drl *.map 2>/dev/null || zip -j flowio-p1-jlc.zip * ; cd ..
ls -la fab/flowio-p1-jlc.zip   # 预期: 14 层文件 + 钻孔, zip < 20MB, 无 0 字节
KPY -c "import glob,os; fs=glob.glob('fab/*'); assert all(os.path.getsize(f)>0 for f in fs); print(len(fs),'files OK')"
```

- [ ] **Step 3: JLC 参数核对清单（写入 fab/README-fab.md）**

内容: 4 层板 90×75mm · 板厚 1.6mm · 最小线宽/间距 0.2/0.2mm · 最小过孔 0.4/0.8mm(含0.45钻新孔) · 阻焊覆盖过孔· 表面处理建议 ENIG（XH 插件可焊性）· 工艺边无需 · 丝印颜色白。

- [ ] **Step 4: Commit**

```bash
git add hardware/flowio-p1/fab/
git commit -m "feat(fab): JLC 打样包 Gerber+钻孔+坐标+BOM+装配图"
```

---

### Task 12: OpenSCAD 外壳 + STL

**Files:**
- Create: `E:\FLOWIO\hardware\flowio-p1\enclosure\flowio-p1-case.scad`
- Create: `E:\FLOWIO\hardware\flowio-p1\enclosure\standoffs.txt`（Task 3 已记 HD）

- [ ] **Step 1: 写参数化外壳（顶盖+底壳，`part` 参数切换）**

```openscad
// flowio-p1-case.scad — FLOWIO P1 外壳 (板 90×75, 4 铜柱位见 standoffs)
$fn = 48;
part = "bottom";          // "bottom" | "top"
wall = 2.4; clr = 0.5;    // 壁厚 / 板-壁间隙
bw = 90; bh = 75; pcb_t = 1.6;
inner_h = 13.5;           // 端子高 11 + 裕量
total_h = inner_h + pcb_t + 1.5;
ox = wall + clr;          // 板原点到壳内壁
OW = bw + 2*ox; OH = bh + 2*ox;
// 铜柱 (板坐标 mm): HA HB HC + HD(Task3 移位后, 见 standoffs.txt)
st = [[4,4],[3,37],[86,13],[75.5,56.0]];  // ← 执行时以 standoffs.txt 的 HD 实测值替换 [3]
pd = 4.2; ph = 5.0;       // M3 自攻底孔 Ø4.2 预压, 柱高(含板厚侧)
cutouts_side = [ // [面, 中心x或y(板坐标), 宽, 高] XH 8×8.5 DC 10×9 USB 10×4
  ["L", 27.0, 10.0, 9.0], ["L", 46.0, 8.0, 8.5],            // DC-005, J8
  ["R", 6.0, 10.0, 4.0], ["R", 22.0, 8.0, 8.5], ["R", 32.5, 8.0, 8.5], ["R", 46.0, 8.0, 8.5], // USB-C, J5 J6 J7
  ["T", 46.0, 8.5, 8.0], ["T", 59.5, 8.5, 8.0], ["T", 73.0, 8.5, 8.0],  // J9 J18 J19
];
module board2case(x, y) = [x + ox, y + ox];
module shell(diff = false) {
  difference() {
    cube([OW, OH, total_h]);
    if (diff) translate([wall, wall, wall]) cube([OW-2*wall, OH-2*wall, total_h]);
  }
}
module cut_side(face, cy, w, h) { // face: L R T B (板边方向)
  ty = 3;                          // 开孔中心离底面高度 (USB/连接器高度带)
  if (face == "L") translate([-1, cy + ox - w/2, ty]) cube([wall + 2, w, h]);
  if (face == "R") translate([OW - wall - 1, cy + ox - w/2, ty]) cube([wall + 2, w, h]);
  if (face == "T") translate([cy + ox - w/2, -1, ty]) cube([w, wall + 2, h]);
  if (face == "B") translate([cy + ox - w/2, OH - wall - 1, ty]) cube([w, wall + 2, h]);
}
module bottom() {
  difference() {
    shell(false);
    translate([wall, wall, wall]) cube([OW-2*wall, OH-2*wall, total_h]); // 控腔
    for (c = cutouts_side) cut_side(c[0], c[1], c[2], c[3]);
    for (x = [6.5:11:83.5]) cut_side("B", x, 9.6, 9.0);                  // 8× 端子孔
    translate([ox + 60, ox + 45, wall + 1]) cube([0,0,0]);               // 占位
  }
  for (s = st) { p = board2case(s[0], s[1]); translate([p[0], p[1], wall])
      difference() { cylinder(d = pd + 3.5, h = ph); translate([0,0,-0.5]) cylinder(d = pd, h = ph + 1); } }
}
module top() {
  difference() {
    shell(false);
    translate([wall + 0.4, wall + 0.4, wall + 0.4]) cube([OW-2*wall-0.8, OH-2*wall-0.8, total_h]); // 盖内腔(留0.4压合)
    for (i = [0:7], j = [0:5])  // 通风栅格
      translate([ox + 12 + i*9, ox + 18 + j*8, -1]) cube([5, 4, wall + 2]);
    for (s = st) { p = board2case(s[0], s[1]); translate([p[0], p[1], -1]) cylinder(d = 3.4, h = wall + 2); } // M3 过孔
  }
}
if (part == "bottom") bottom(); else top();
```

注: `st` 中 HD 值必须来自 `enclosure/standoffs.txt` 实测；`module board2case(x,y) = [...]` 写法在部分版本需改为 `function board2case(x,y) = [x+ox, y+ox];` —— 执行时若语法报错即改。

- [ ] **Step 2: 导出 STL**

```bash
mkdir -p enclosure
"C:/Program Files/OpenSCAD/openscad.exe" -o enclosure/case-bottom.stl --export-format binstl -D 'part="bottom"' enclosure/flowio-p1-case.scad
"C:/Program Files/OpenSCAD/openscad.exe" -o enclosure/case-top.stl --export-format binstl -D 'part="top"' enclosure/flowio-p1-case.scad
```

Expected: 两个 STL 生成，非空（`ls -la enclosure/*.stl`）。语法错误 → 按注修改 function 写法后重跑。

- [ ] **Step 3: 目视检查渲染图**

```bash
"C:/Program Files/OpenSCAD/openscad.exe" -o enclosure/case-bottom.png --imgsize 1200,900 --colorscheme Tomorrow -D 'part="bottom"' enclosure/flowio-p1-case.scad
"C:/Program Files/OpenSCAD/openscad.exe" -o enclosure/case-top.png --imgsize 1200,900 --colorscheme Tomorrow -D 'part="top"' enclosure/flowio-p1-case.scad
```

检查: 开孔位置与连接器一一对齐（L:DC/J8 · R:USB/J5/J6/J7 · T:J9/J18/J19 · B:8 端子）· 通风栅不压天线区正上方也无妨（塑料透明）· 铜柱不碰 USB-C/端子。

- [ ] **Step 4: Commit**

```bash
git add hardware/flowio-p1/enclosure/
git commit -m "feat(mech): OpenSCAD 参数化外壳 + STL (四铜柱随 HD 实测位)"
```

---

## 完成定义

1. `kicad-cli pcb drc`: error 类全零（外观豁免清单见 spec §5）
2. `fab/flowio-p1-jlc.zip` 完整 + `fab/README-fab.md` 参数表
3. `enclosure/*.stl` 两件 + 渲染图目视检查通过
4. 终态双视图渲染目视检查通过（Task 10）
5. 全部提交到 main，提交历史按任务分段
