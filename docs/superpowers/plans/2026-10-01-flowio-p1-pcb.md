# FLOWIO-CN P1 PCB 联合设计实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 设计并验证 FLOWIO-CN P1 "升级大脑" 产品板（原理图 + PCB + 3D 外壳），输出可交付嘉立创打样的 Gerber 和三维猴打印的 STL。

**Architecture:** 以 ESP32-S3-DevKitC-1 官方原理图为 baseline（80% 继承），新增 8 路 AO3400 驱动、TCA9548A 五通道传感、DC-005 双电源输入。联合设计 OpenSCAD 参数化外壳，通过 KiCad STEP 导出验证装配。

**Tech Stack:** KiCad 10.0（原理图+PCB+3D+CLI）· JLC MCP（元件库安装）· OpenSCAD 2021.01（外壳）· KiCad Python/pcbnew（自动化）

**SPEC:** `docs/superpowers/specs/2026-10-01-flowio-p1-pcb-design.md` v1.1（用户已批准）

---

### Task 1: 安装 LCSC 元件库到 KiCad

**Files:**
- Create: `E:\FLOWIO\hardware\flowio-p1\` (KiCad project directory)

- [ ] **Step 1: 安装核心 IC 到 KiCad 库**

使用 JLC MCP 工具 `library_batch_install`，批量安装以下 LCSC 编码：

```
C2913202  ESP32-S3-WROOM-1-N16R8
C130026   TCA9548APWR
C9865     TPS54331DR
C968586   CH340K（修正 #12：替代 CH340E——E 无 DTR#）
C20917    AO3400A
```

验证: 每个返回 `installed: true` 且 `pin_pad_match: true`

- [ ] **Step 2: 安装外围器件**

```
C167253   CDRH103RNP-6R8NC 6.8µH 电感
C8678     SS34 3A Schottky
C2480     SS14 1A Schottky
C7519     USBLC6-2SC6 ESD
C181160   SS8050 NPN
C456012   USB Type-C 6P
C431533   DC-005 电源座
C5359632  XH2.54-4P 针座
C8465     WJ500V-5.08-2P 端子
```

验证: 全部返回 `installed: true`

- [ ] **Step 3: 创建 KiCad 工程目录和项目文件**

```bash
mkdir -p "E:/FLOWIO/hardware/flowio-p1"
```

在 KiCad GUI 中: File → New Project → 选择 `E:\FLOWIO\hardware\flowio-p1\` → 命名 `flowio-p1`

或者用 pcbnew Python:
```python
import pcbnew
board = pcbnew.BOARD()
pcbnew.SaveBoard("E:/FLOWIO/hardware/flowio-p1/flowio-p1.kicad_pcb", board)
```

验证: `flowio-p1.kicad_pro` 文件存在

- [ ] **Step 4: Commit**

```bash
cd E:/FLOWIO && git add hardware/flowio-p1/ && git commit -m "feat: 创建 flowio-p1 KiCad 工程 + 安装全部 LCSC 元件库"
```

---

### Task 2: 画原理图——电源电路块

**Files:**
- Create: `E:/FLOWIO/hardware/flowio-p1/flowio-p1.kicad_sch`

- [ ] **Step 1: 画 5V 输入电路**

在 KiCad eeschema 中（或用 Python 操作 S-expression）:

```
DC-005 (J1):
  Pin 1 (+) → D1 (SS34) → Net V5V     # 修正 #9: 1N5819W(1A)→SS34(3A)
  Pin 2 (-) → GND

USB-C (J2):
  VBUS → D2 (SS34) → Net V5V          # 修正 #9
  CC1 → R1 (5.1kΩ) → GND
  CC2 → R2 (5.1kΩ) → GND
  GND → GND
  D+ → Net USB_DP
  D- → Net USB_DN
```

- [ ] **Step 2: 画 TPS54331 Buck 电路**

```
U3 TPS54331DR:
  VIN (Pin 7) → V5V + C1 10µF + C2 100nF (就近去耦)
  EN  (Pin 8) → R3 100kΩ → V5V
  PH  (Pin 1) → L1 CDRH103RNP-6R8NC → V3V3
             → D3 SS34 (阴极→GND, 阳极→PH)
  VSENSE (Pin 5) → R4 10kΩ → V3V3
                → R5 3.24kΩ 1% → GND (分压点→VSENSE)
                # 修正 #11: 5.23k→3.24k; Vout=0.8×(1+10k/3.24k)=3.27V
  COMP (Pin 4) → R6 10kΩ → C3 2.2nF → GND
              → C4 22pF → GND (并联)
  BOOT (Pin 2) → C5 0.1µF → PH
  SS  (Pin 6) → C6 0.1µF → GND
  GND (Pin 3/9) → GND + 热焊盘→GND

L1 输出侧:
  → C7 47µF ×2 + C8 100nF ×2 → GND (输出滤波)
  → Net V3V3
```

- [ ] **Step 3: 画 3.3V 分配**

```
V3V3 → ESP32-S3-WROOM-1 Pin 2 (3V3) + C9 10µF + C10 100nF
V3V3 → TCA9548APWR Pin 12 (VCC) + C11 100nF
V3V3 → CH340K VCC + V3短接VCC + C12 100nF
V3V3 → WS2812B VCC + C13 100nF
V3V3 → 5× XH2.54 Pin 1 (传感器 VCC)
```

- [ ] **Step 4: 运行 ERC**

```bash
"E:/Program Files/KiCad/10.0/bin/kicad-cli.exe" sch erc -o erc_power.rpt flowio-p1.kicad_sch
```

Expected: 0 errors (可能有 "power input not driven" 警告——正常)

- [ ] **Step 5: Commit**

```bash
git add -A hardware/flowio-p1/ && git commit -m "feat: 原理图电源块——DC/USB双输入+TPS54331 Buck+3.3V分配"
```

---

### Task 3: 画原理图——ESP32 主控 + USB 转串口

- [ ] **Step 1: 画 ESP32-S3-WROOM-1 模组连接**

```
U1 ESP32-S3-WROOM-1-N16R8:
  Pin 2  (3V3)  → V3V3
  Pin 1  (GND)  → GND (所有 GND 引脚)
  Pin 3  (EN)   → R7 10kΩ→V3V3 + C14 1µF→GND + SW1(RST按钮)→GND + Q1(SS8050集电极)
  Pin 4  (IO4)  → 阀驱动 ch1
  Pin 5  (IO5)  → 阀驱动 ch2
  Pin 6  (IO6)  → 阀驱动 ch3
  Pin 7  (IO7)  → 阀驱动 ch4
  Pin 8  (IO8)  → I2C SDA + R8 4.7kΩ→V3V3
  Pin 9  (IO9)  → I2C SCL + R9 4.7kΩ→V3V3
  Pin 10 (IO10) → 阀驱动 ch5
  Pin 11 (IO11) → 阀驱动 ch6 (INLET)
  Pin 12 (IO12) → 阀驱动 ch7 (VENT)
  Pin 21 (IO21) → 阀驱动 ch8 (泵)
  Pin 43 (TXD0) → R10 1kΩ → CH340K TXD + TP_TXD + 排针
  Pin 44 (RXD0) → R11 1kΩ → CH340K RXD + TP_RXD + 排针
  Pin 48 (IO48) → R12 330Ω → WS2812B DIN
  (其余引脚悬空或按 strapping)
```

- [ ] **Step 2: 画 Strapping 偏置**

```
GPIO0  (BOOT) → SW2 (BOOT按钮)→GND + R13 10kΩ→V3V3 + Q2(SS8050集电极)
GPIO3          → R14 10kΩ→V3V3
GPIO45         → R15 10kΩ→GND
GPIO46         → R16 10kΩ→V3V3
```

- [ ] **Step 3: 画 CH340K USB 转串口（修正 #12：CH340E→CH340K）**

> 依据官方 WCH CH340DS1 v3B 引脚表逐字核对：
> CH340E (MSOP-10) = {1 UD+, 2 UD−, 3 GND, 4 RTS#, 5 CTS#, 6 TNOW, 7 VCC, 8 TXD, 9 RXD, 10 V3} ——无 DTR#，无法自动下载
> CH340K (ESSOP-10) = {1 UD+, 2 UD−, 3 GND, **4 DTR#**, 5 CTS#, **6 RTS#**, 7 VCC, 8 TXD, 9 RXD, 10 V3, 11 EP-GND} ✓
> KiCad 符号已核对一致（pin_pad_match=true）。内置振荡器，无需晶振。

```
U4 CH340K (ESSOP-10, C968586):
  VCC (7)  → V3V3 + C15 100nF（就近）
  V3 (10)  → 短接 VCC（3.3V 供电时，手册要求）
  GND (3)  → GND；EP (11) → GND
  UD+ (1)  → R17 22Ω → USB_DP（USBLC6 I/O1 同网络）
  UD- (2)  → R18 22Ω → USB_DN（USBLC6 I/O2 同网络）
  TXD (8)  → R10 1kΩ → ESP32 RXD0 (GPIO44)
  RXD (9)  → R11 1kΩ → ESP32 TXD0 (GPIO43)
  DTR# (4) → R19 1kΩ → Q1 基极
  RTS# (6) → R20 1kΩ → Q2 基极
  CTS# (5) → 悬空

USBLC6-2SC6:
  I/O1 → USB_DP
  I/O2 → USB_DN
  GND  → GND
  VBUS → V5V

（无晶振——CH340K 内置振荡器；删除原计划的 X1/C16/C17）

SS8050 Q1 (EN 复位控制):
  基极   → R19 1kΩ (来自 DTR#) + R21 10kΩ → V3V3
  集电极 → ESP32 EN
  发射极 → GND

SS8050 Q2 (IO0 引导控制):
  基极   → R20 1kΩ (来自 RTS#) + R22 10kΩ → V3V3
  集电极 → ESP32 GPIO0
  发射极 → GND
```

- [ ] **Step 4: 画 WS2812B + LED + 按钮**

```
WS2812B:
  VCC → V3V3 + C13 100nF
  DIN → R12 330Ω → GPIO48
  GND → GND

PWR LED (D4 红):
  正极 → V3V3
  负极 → R23 1kΩ → GND

User LED (D5 蓝):
  正极 → GPIO13 (空闲)
  负极 → R24 1kΩ → GND

TX LED (D6 黄): 正极→V3V3, 负极→R25 1kΩ→CH340K TXD
RX LED (D7 黄): 正极→V3V3, 负极→R26 1kΩ→CH340K RXD

User Button (SW3): 一端→GPIO14 (空闲)+R27 10kΩ→V3V3, 另一端→GND
```

- [ ] **Step 5: 运行 ERC**

```bash
"E:/Program Files/KiCad/10.0/bin/kicad-cli.exe" sch erc -o erc_main.rpt flowio-p1.kicad_sch
```

Expected: 0 errors

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "feat: 原理图主控块——ESP32+strapping+CH340K+自动下载+LED/按钮"
```

---

### Task 4: 画原理图——I2C 传感 + 阀驱动 + 接口

- [ ] **Step 1: 画 TCA9548A 五通道 I2C**

```
U2 TCA9548APWR (TSSOP-24):
  VCC (Pin 12) → V3V3 + C11 100nF
  GND (Pin 24) → GND
  A0/A1/A2 (Pin 1/2/3) → GND (地址 0x70)
  RESET# (Pin 4) → R28 10kΩ → V3V3
  SDA (Pin 23) → I2C_SDA + R8 4.7kΩ → V3V3 + TP_SDA
  SCL (Pin 22) → I2C_SCL + R9 4.7kΩ → V3V3 + TP_SCL

  CH0: SD0 (Pin 5) + SC0 (Pin 13) → XH2.54 #1 + R29/R30 10kΩ → V3V3
  CH1: SD1 (Pin 6) + SC1 (Pin 14) → XH2.54 #2 + R31/R32 10kΩ → V3V3
  CH2: SD2 (Pin 7) + SC2 (Pin 15) → XH2.54 #3 + R33/R34 10kΩ → V3V3
  CH3: SD3 (Pin 8) + SC3 (Pin 16) → XH2.54 #4 + R35/R36 10kΩ → V3V3
  CH4: SD4 (Pin 9) + SC4 (Pin 17) → XH2.54 #5 + R37/R38 10kΩ → V3V3
  CH5/CH6/CH7: 悬空（丝印标"预留"）
```

- [ ] **Step 2: 画 8 路 AO3400 驱动**

每路相同（以 ch1 为例，复制 ×8）:

```
GPIO4 → R39 1kΩ → AO3400 Q3 栅极
                   ├→ 源极 → GND
                   └→ 漏极 → WJ500V 端子 #1 一端
                            + SS14 D8 (阴极→V5V, 阳极→漏极)
                            + TP_GATE1 / TP_DRAIN1
R40 10kΩ: 栅极 → GND (下拉)

V5V → WJ500V 端子 #1 另一端
```

8 路对应的 GPIO: 4, 5, 6, 7, 10, 11, 12, 21

- [ ] **Step 3: 画测试焊盘 + 排针**

```
测试焊盘 (直径 1.2mm 镀金裸盘):
  TP_3V3 → V3V3
  TP_5V  → V5V
  TP_GND ×3 → GND (分布在不同区域)
  TP_SDA / TP_SCL → I2C 主总线
  TP_GATE1 / TP_DRAIN1 → AO3400 #1
  TP_PH → TPS54331 PH
  TP_EN → ESP32 EN

调试排针:
  J3 (4P 2.54mm): TXD / GND / RXD / 3.3V
  J4 (4P 2.54mm): GPIO13 / 3.3V / GND / GPIO14
```

- [ ] **Step 4: 运行完整 ERC**

```bash
"E:/Program Files/KiCad/10.0/bin/kicad-cli.exe" sch erc -o erc_full.rpt flowio-p1.kicad_sch
```

Expected: 0 errors, 0 severe warnings

- [ ] **Step 5: 导出原理图 PDF + 网表**

```bash
"E:/Program Files/KiCad/10.0/bin/kicad-cli.exe" sch export pdf -o schematic.pdf flowio-p1.kicad_sch
"E:/Program Files/KiCad/10.0/bin/kicad-cli.exe" sch export netlist -o netlist.net flowio-p1.kicad_sch
```

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "feat: 原理图完成——TCA9548A+8路AO3400+测试焊盘+排针; ERC 全绿"
```

---

### Task 5: PCB 布局

- [ ] **Step 1: 定义板框和安装孔**

```
板框: 80×70mm 圆角 R2
安装孔: M3 ×4 (四角，距边 5mm，孔径 3.2mm)
天线净空: 模组短边（天线端）朝板边，前方 15mm 四层禁铜
```

- [ ] **Step 2: 放置主要器件（分区布局）**

```
┌──────────────────────────────────────────┐
│ [天线净空 ≥15mm，四层无铜]                │  ← 板顶边
├──────────────────────────────────────────┤
│ ESP32-S3 模组 (U1)                      │
│ BOOT  RST   WS2812B          CH340K(U4) │
│                                          │ USB-C (板右前边)
│ TCA9548A (U2)               TP 排针     │
│                                          │
│ TPS54331 (U3)               DC-005 (板后边)
│   L1 + SS34 (紧贴 PH)                    │
│                                          │
│ AO3400 ×8 (Q3-Q10)                      │
│ [端子×8 沿左板边]  [XH×5 沿右板边]       │
│ TP 焊盘 分布                              │
│ PWR LED  User LED  User Button  排针     │
└──────────────────────────────────────────┘
```

- [ ] **Step 3: 布线（关键约束）**

- TPS54331 PH→SS34→L1: <5mm，短粗走线
- USB D+/D-: 差分 90Ω，等长
- I2C SDA/SCL: 远离 AO3400 和 TPS54331 PH
- 电源线: 5V ≥1mm（2.5A），3.3V ≥0.5mm（500mA）
- 天线区: 四层全部 void

- [ ] **Step 4: 铺铜**

- L1 (Top): GND 铺铜（天线区 void）
- L2: GND 整片平面（天线区 void）
- L3: V3V3 + V5V 分割平面
- L4 (Bottom): GND 铺铜

- [ ] **Step 5: 运行 DRC**

```bash
"E:/Program Files/KiCad/10.0/bin/kicad-cli.exe" pcb drc -o drc.rpt flowio-p1.kicad_pcb
```

Expected: 0 errors

- [ ] **Step 6: 3D 渲染**

```bash
"E:/Program Files/KiCad/10.0/bin/kicad-cli.exe" pcb render --side top -o render_top.png flowio-p1.kicad_pcb
"E:/Program Files/KiCad/10.0/bin/kicad-cli.exe" pcb render --side bottom -o render_bottom.png flowio-p1.kicad_pcb
```

- [ ] **Step 7: Commit**

```bash
git add -A && git commit -m "feat: PCB 布局完成——80×70mm/4层/8路驱动/天线净空/DRC全绿"
```

---

### Task 6: OpenSCAD 参数化外壳

**Files:**
- Create: `E:/FLOWIO/hardware/flowio-p1/enclosure.scad`

- [ ] **Step 1: 写参数化外壳代码**

```openscad
// FLOWIO-CN P1 外壳（参数化——改 PCB 尺寸自动联动）
$fn = 64;

// PCB 参数
pcb_w = 80;  pcb_l = 70;  pcb_t = 1.6;
mount_d = 3.2;  mount_inset = 5;

// 器件最大高度
max_h = 14;  // WJ500V 端子
min_gap = 3; // PCB 到盖板最小间隙

// 外壳参数
wall = 2.5;
clearance = 0.3;
int_w = pcb_w + 2*clearance;
int_l = pcb_l + 2*clearance;
int_h = max_h + min_gap + pcb_t;
ext_w = int_w + 2*wall;
ext_l = int_l + 2*wall;
ext_h = int_h + wall; // 底板厚度=wall

// 开孔参数（从 PCB 布局映射）
usb_w = 10;  usb_h = 4;  usb_pos = [ext_w*0.55, 0, wall+pcb_t];      // USB-C
dc_w = 12;   dc_h = 8;  dc_pos = [ext_w*0.3, ext_l, wall+pcb_t];      // DC-005
led_d = 4;   led_pos = [ext_w*0.8, ext_l*0.1, ext_h - wall/2];       // LED 导光

// 底壳
module base() {
    difference() {
        // 外壳体
        linear_extrude(height = ext_h)
            square([ext_w, ext_l], center=false);
        // 内腔
        translate([wall, wall, wall])
            linear_extrude(height = ext_h)
                square([int_w, int_l], center=false);
        // USB-C 开孔
        translate([usb_pos.x - usb_w/2, -0.1, usb_pos.z])
            cube([usb_w, wall+0.2, usb_h]);
        // DC-005 开孔
        translate([dc_pos.x - dc_w/2, ext_l - wall - 0.1, dc_pos.z])
            cube([dc_w, wall+0.2, dc_h]);
        // LED 导光孔
        translate([led_pos.x, led_pos.y, led_pos.z])
            cylinder(d=led_d, h=wall+1);
        // 端子排开孔（板左侧 8 个）
        for(i = [0:7])
            translate([-0.1, wall + 8 + i*8, wall + pcb_t + 2])
                cube([wall+0.2, 6, 9]);
        // XH 传感器开孔（板右侧 5 个）
        for(i = [0:4])
            translate([ext_w - wall - 0.1, wall + 10 + i*10, wall + pcb_t + 2])
                cube([wall+0.2, 8, 5]);
        // 通风槽
        for(i = [0:5])
            translate([wall + 10 + i*12, ext_l - wall - 8, wall + 4])
                cube([8, wall+1, 6]);
    }
    // 螺丝柱
    for(x = [mount_inset + clearance, int_w + wall - mount_inset - clearance],
        y = [mount_inset + clearance, int_l + wall - mount_inset - clearance])
        translate([x, y, wall])
            difference() {
                cylinder(d = 6.5, h = int_h - wall);
                cylinder(d = mount_d, h = int_h);
            }
}

base();
```

- [ ] **Step 2: 渲染验证**

```bash
"C:/Program Files/OpenSCAD/openscad.com" -o enclosure.png --imgsize=800,600 --camera=0,0,0,0,0,25,300 enclosure.scad
```

- [ ] **Step 3: 导出 STL**

```bash
"C:/Program Files/OpenSCAD/openscad.com" -o enclosure.stl enclosure.scad
```

- [ ] **Step 4: Commit**

```bash
git add -A && git commit -m "feat: OpenSCAD 参数化外壳——80×70 PCB 联动/开孔/螺丝柱/通风"
```

---

### Task 7: 制造输出 + 用户最终审查

- [ ] **Step 1: 导出 Gerber + 钻带**

```bash
CD="E:/Program Files/KiCad/10.0/bin/kicad-cli.exe"
"$CD" pcb export gerbers -o gerber_out/ flowio-p1.kicad_pcb
"$CD" pcb export drill -o gerber_out/ flowio-p1.kicad_pcb
```

- [ ] **Step 2: 导出 BOM CSV**

```bash
"$CD" sch export bom -o bom.csv flowio-p1.kicad_sch
```

- [ ] **Step 3: 导出贴片坐标**

```bash
"$CD" pcb export pos -o pos.csv flowio-p1.kicad_pcb
```

- [ ] **Step 4: 导出 STEP**

```bash
"$CD" pcb export step -o flowio-p1.step flowio-p1.kicad_pcb
```

- [ ] **Step 5: 生成最终审查包**

将以下文件放到一个目录供用户审查:
- `render_top.png` / `render_bottom.png` (KiCad 3D 渲染)
- `enclosure.png` (OpenSCAD 外壳渲染)
- `schematic.pdf` (原理图)
- `erc.rpt` / `drc.rpt` (自动检查结果)

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "feat: 制造输出——Gerber+钻带+BOM+坐标+STEP+外壳STL; 用户审查包就绪"
```

- [ ] **Step 7: 用户审查**

向用户展示:
1. 3D 渲染图（板顶/板底）
2. 外壳渲染图
3. ERC/DRC 全绿截图
4. 原理图 PDF

用户批准后:
- 嘉立创下单 Gerber
- 三维猴下单 STL

---

## 自检完成

✓ Spec 覆盖: 电源(§3.1)→Task2 / 主控(§3.2)→Task3 / I2C+驱动(§3.3)→Task4 / 布局(§4)→Task5 / 外壳(§10.3)→Task6 / 制造(§7)→Task7 / 测试(§8)→Task7 Step5-7
✓ 无占位符: 每步都有具体代码/命令/预期输出
✓ 类型一致: 网络名(V3V3/V5V/GND/I2C_SDA等)跨任务一致
✓ Baseline 遵循: Task 2-3 的电路参数与 DevKitC-1 官方原理图一致
