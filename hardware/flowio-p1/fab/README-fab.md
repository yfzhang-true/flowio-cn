# FLOWIO-P1.1 嘉立创打样参数（T5 重出 · 布线终态 2026-10-05）

| 项 | 值 |
|---|---|
| 层数/尺寸 | 4 层 **100×80mm** 矩形（Edge.Cuts 实测 100.000×80.000） |
| 板厚 | 1.6mm |
| 最小线宽/间距 | **实测 0.200/0.200mm**（1867 铜线宽谱 0.2×1179 / 0.25×502 / 0.3×90 / 0.4×18 / 0.5-1.0×78；铜净空设计规则 0.20，DRC 0 违例 → 实测间距 ≥0.20） |
| 最小过孔 | 信号 0.3 孔/0.6 盘 ×232 · 电源 0.35 孔/0.7 盘 ×184（环宽均 0.15/边） |
| 阻焊 | **过孔覆盖**（板设置 tenting front/back=yes，导出附 `--subtract-soldermask` 丝印裁切） |
| 表面处理 | 建议 **ENIG**（XH 端子与 13 处 via-in-pad 塞孔封帽可焊性） |
| 丝印 | 白色 |
| 工艺边 | 无需（100×80 ≥ 常规夹持尺寸） |

## 文件清单（check_fab.py 21 断言全绿）

| 文件 | 说明 |
|---|---|
| Gerber ×11（JLC 集） | F/In1/In2/B.Cu + F/B.Paste + F/B.Silkscreen + F/B.Mask + Edge.Cuts（Protel 扩展名 .gtl/.g1/.g2/.gbl/.gtp/.gbp/.gto/.gbo/.gts/.gbs/.gm1） |
| Gerber ×3（参考层） | F/B.Courtyard + Margin（装配核对用，不入 JLC zip） |
| flowio-p1-job.gbrjob | 4 层 / 100.1×80.1 / 板厚 1.6 |
| 钻孔 | flowio-p1.drl（合并 450 孔）+ -PTH/-NPTH.drl 分体 + -drl_map.gbr |
| 坐标 | flowio-p1-pos.csv（mm，钻孔原点，147 位号全 top）+ -jlc 注释版 |
| BOM | flowio-p1-bom.csv（原理图通用版，LCSC 列实填）+ -jlc.csv（39 行：SMT 36 行 139 件 + THT 3 行 7 件） |
| 装配图 | assembly-top/bottom.pdf（Fab+CrtYd+Edge） |
| flowio-p1-jlc.zip | **13 文件**（11 Gerber+gbrjob+drl；旧 P1 包仅 4Cu+Edge+drl 6 文件，Mask/Silk 缺失为隐患，已修复） |
| flowio-p1.step | 20.7MB（按需再生不入库；`KICAD9_3RD_PARTY=C:/Users/yuefe/Documents/KiCad/9.0/3rdparty`） |

钻孔谱：450 = 232×Ø0.3(信号孔) + 184×Ø0.35(电源孔) + 28×Ø0.9(XH-4P 插件孔) + 4×Ø3.2 NPTH(M3 铜柱孔，@ST 四角) + 2×Ø0.6 NPTH(J1 USB-C 外壳定位孔)。

## via-in-pad 清单（IPC-4761 Type VII，13 处 · tools/scan_fab.py 重扫）

孔中心落于 SMD 焊盘 bbox 内、全部**同网**（电源/地取流与 EP 散热孔，非误布）：

| # | 位号.焊盘 | 网 | 孔径/盘径 | 坐标 |
|---|---|---|---|---|
| 1-4 | J20.1 / J21.1 / J22.1 / J23.1 | +5V | 0.35/0.7 | x≈96.3 右壁 XH-2P 电源馈入 |
| 5 | C2.1 | +5V | 0.30/0.6 | (29.2, 38.5) |
| 6 | U3.2 | +5V | 0.30/0.6 | (24.4, 46.8) |
| 7 | U5.2 | GND | 0.30/0.6 | (74.3, 15.0) EP |
| 8 | U4.3 | GND | 0.30/0.6 | (74.4, 23.7) EP |
| 9 | R4.1 | +3V3 | 0.30/0.6 | (52.5, 42.8) |
| 10 | LED1.1 | +3V3 | 0.30/0.6 | (51.0, 16.5) |
| 11 | R16.1 | +3V3 | 0.30/0.6 | (38.2, 31.0) |
| 12 | C9.1 | +3V3 | 0.30/0.6 | (63.0, 56.6) |
| 13 | R29.2 | S1_SDA | 0.30/0.6 | (60.0, 29.3) |

**处置声明**：13 处均需下单备注 **IPC-4761 Type VII（树脂塞孔+电镀封帽）**，否则焊膏流入孔桶造成虚焊。塞孔孔径 0.30/0.35 ∈ JLC 环氧塞孔支持窗（孔径 0.15–0.55，见工艺复核表）。移孔评估结论：U4.3/U5.2 为 EP 散热孔（必须保留）；J20-J23 为端子直取流（移离焊盘需重布右壁逃线）；其余 7 处信号/退耦孔移离焊盘须连带移动终止轨道（closed 布线高回归风险）——统一塞孔处置，性价比与风险均优于移孔。P1 基线 8 处 → P1.1 布线终态 13 处（J22.1/J23.1 各原有双孔，T5a 去重后各存一）。

另有 2 处**过孔叠 PTH 焊盘**（J18.1 UART_TX、J2.7 GND，同网、钻孔同心被 Ø0.9/1.3 孔吸收）——非 SMD 不入塞孔清单，DRC holes_co_located 2 条 warning 记录在案。

## hole_to_hole 处置（T5a，DRC 142→127 关键项）

布线终态曾存在 15 对超距孔（14 对物理重叠 wall −0.062~−0.297 + 1 对 +0.064，全部 freerouting/stitch 撞孔伪影）——超出 JLC 过孔孔距 0.2mm 限值且重叠孔会被钻孔 DFM 拒收。`tools/fix5_dedup_vias.py` 按线段+宽度铜交叠模型逐对判定冗余后删除 15 孔（16 端点吸附保留孔中心，zone 全板重填），门禁：未连 0 保持 · DRC warning 142→127 净减 · check_route 双绿。**去重后全板最小孔壁距 0.274mm（4 对信号孔 0.274~0.292）≥ JLC 限值，无需进一步处置。**

## DRC 终态与三重验证

- DRC：**0 错误 / 0 未连 / 222 warning**（track_dangling 55 + silk_overlap 95 + silk_over_copper 49 + silk_edge_clearance 13 + via_dangling 7 + holes_co_located 2 + lib_footprint 1）。silk_overlap 95 条为 T5b 层栈补全（Mask/SilkS/Paste 入层栈表）后丝印-丝印检查首次激活所致，全部为 refdes 压邻件轮廓外观类，零制造影响（丝印对丝印无电气/工艺约束）。
- 连通性三重验证：① KiCad DRC 未连 0 ② `tools/check_route.py` 铜级守门（ratsnest 0 + 无过孔钻铜柱环）双绿 ③ L5 T4 钻孔避让（test_device_geom all 13/0，对 T5 重出 drl 450 孔全绿）。

## JLC 工艺复核表（实测 vs 嘉立创能力页 jlcpcb.com/capabilities/pcb-capabilities，2026-10 查证）

| # | 检查项 | 本板实测 | JLC 限值（4 层档） | 判定 |
|---|---|---|---|---|
| 1 | 最小线宽（外层，1oz） | 0.200 | 0.09（3.5mil） | **通过**（余量 2.2×） |
| 2 | 最小铜间距 | ≥0.200（规则 0.2，DRC 0 违例） | 0.09 | **通过** |
| 3 | 最小过孔 | 0.3 孔/0.6 盘 | 0.15 孔/0.25 盘（盘≥孔+0.1） | **通过**（0.6≥0.3+0.1） |
| 4 | 电源过孔 | 0.35 孔/0.7 盘 | 同上 | **通过** |
| 5 | 最大孔 | Ø3.2 NPTH ×4（M3 铜柱） | —（常规） | **通过** |
| 6 | 过孔孔距（壁距） | 最小 0.274（去重后 4 对 0.274~0.292） | 0.2 | **通过**（原 15 对超距已 T5a 去重清零） |
| 7 | 焊盘孔距（PTH） | holes_co_located 2 处同网叠孔（同心被大孔吸收） | 0.45（异孔壁距） | **豁免**（同心钻吸收非异孔对；同网无断路风险） |
| 8 | 阻焊桥 | XH-2P 2.54 节距 → 桥宽 ≈0.9-1.0 | 白色 0.13（1oz） | **通过** |
| 9 | 阻焊过孔覆盖 | tenting 全开（0 开窗于过孔） | 支持掩模塞孔（盘径≤0.5 全盖） | **通过**（0.6/0.7 盘 tented 为常规覆盖工艺） |
| 10 | 板边铜净空 | 规则 0.3，DRC 0 违例 | ≥0.2（铣边） | **通过** |
| 11 | 开槽 | 无 | 金属化 ≥0.35 / NPTH ≥1.0 | **不适用** |
| 12 | 半孔/邮票孔 | 无 | — | **不适用** |
| 13 | 工艺边 | 无（单板 100×80） | — | **不适用** |
| 14 | 板厚 | 1.6（gbrjob 真值） | ±10% | **通过** |
| 15 | via-in-pad 塞孔 | 13 处，孔径 0.30/0.35 | 环氧塞孔+封帽孔径 0.15–0.55 | **通过**（按孔径；订单页若按盘径 0.55 卡 0.6/0.7 盘，改备注沟通——塞孔约束通行按孔径） |
| 16 | 表面处理 | 建议 ENIG | ENIG 常规可选（多层 BGA/塞孔封帽推荐） | **通过** |
| 17 | 最小环宽 | 0.15/边（0.6 盘−0.3 孔） | 0.05（按 0.15/0.25 最小过孔推） | **通过**（3×） |
| 18 | 孔位公差依赖 | M3 孔 vs 铜柱环避让 | 孔位 ±0.075 | **通过**（L5 T4 断言 +0.2 裕量） |

## 工艺注意事项

- **12× XH-2P（C7429671）为 SMD 卧贴**（J10-J17 底壁 + J20-J23 右壁），回流焊，无波峰焊依赖；7× XH-4P（C5359632）为 THT 代插（J5-J9/J18/J19）。
- 下单留言栏：13 处 via-in-pad 需 IPC-4761 Type VII（见上清单）；表面处理 ENIG。
- `tools/check_fab.py` 为 fab 完整性守门（21 断言），任何 fab 重出后必须全绿。

## 再生命令（cwd = hardware/flowio-p1）

```bash
python tools/fix5_add_layers.py   # 幂等：层栈补全（若 gen_pcb 再生后需先跑）
"E:/Program Files/KiCad/10.0/bin/kicad-cli.exe" pcb export gerbers --output fab/ --subtract-soldermask \
  -l F.Cu,In1.Cu,In2.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts,F.Courtyard,B.Courtyard,Margin flowio-p1.kicad_pcb
"E:/Program Files/KiCad/10.0/bin/kicad-cli.exe" pcb export drill --output fab/ --generate-map --map-format gerberx2 flowio-p1.kicad_pcb
"E:/Program Files/KiCad/10.0/bin/kicad-cli.exe" pcb export drill --output fab/ --excellon-separate-th flowio-p1.kicad_pcb
"E:/Program Files/KiCad/10.0/bin/kicad-cli.exe" pcb export pos --output fab/flowio-p1-pos.csv --format csv --units mm --use-drill-file-origin flowio-p1.kicad_pcb
"E:/Program Files/KiCad/10.0/bin/kicad-cli.exe" sch export bom --fields LCSC,Value,Footprint,QUANTITY,Reference --labels LCSC,Value,Footprint,Qty,Refs --group-by LCSC,Value,Footprint --output fab/flowio-p1-bom.csv flowio-p1.kicad_sch
"E:/Program Files/KiCad/10.0/bin/kicad-cli.exe" pcb export pdf --output fab/assembly-top.pdf -l F.Fab,F.Courtyard,Edge.Cuts flowio-p1.kicad_pcb
"E:/Program Files/KiCad/10.0/bin/kicad-cli.exe" pcb export pdf --output fab/assembly-bottom.pdf -l B.Fab,B.Courtyard,Edge.Cuts flowio-p1.kicad_pcb
(cd tools && python make_bom.py)          # bom-jlc + pos-jlc 注释版
(cd fab && zip -j flowio-p1-jlc.zip <11 Gerber> flowio-p1-job.gbrjob flowio-p1.drl)
KICAD9_3RD_PARTY=C:/Users/yuefe/Documents/KiCad/9.0/3rdparty kicad-cli pcb export step --output fab/flowio-p1.step --force flowio-p1.kicad_pcb
python tools/check_fab.py                 # 21 断言守门
"E:/Program Files/KiCad/10.0/bin/python.exe" tools/check_route.py   # 双绿守门
```
