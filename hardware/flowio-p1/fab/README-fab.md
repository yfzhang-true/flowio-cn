# FLOWIO-P1 嘉立创打样参数

| 项 | 值 |
|---|---|
| 层数/尺寸 | 4 层 90×75mm 矩形 |
| 板厚 | 1.6mm |
| 最小线宽/间距 | 0.2/0.2mm |
| 最小过孔 | 0.3mm 孔 / 0.6mm 盘 (个别 0.45/0.9 电源孔) |
| 阻焊 | 过孔覆盖 (Gerber 已 subtract-soldermask) |
| 表面处理 | 建议 ENIG (XH 插件可焊性) |
| 丝印 | 白色 |
| 工艺边 | 无需 |

## 文件清单
- Gerber ×11 (F/In1/In2/B.Cu + F/B.Paste + F/B.Silk + F/B.Mask + Edge.Cuts) + .gbrjob
- 钻孔 flowio-p1.drl + drl_map
- 坐标 flowio-p1-pos.csv (mm, 原点=钻孔原点)
- BOM flowio-p1-bom.csv
- 装配图 assembly-top/bottom.pdf

## 已知遗留 (打样不受影响, 回板后 GUI 补线或飞线)
DRC 剩余 6 处未连接: R13/R29 strap 供电簇、C3-U3.2 buck 输入簇×2、
GND/3V3 平面岛对 — 均为 freerouting 三轮 + 脚本攻坚后仍存在的死角,
建议 KiCad GUI 手工补 6 条短走线 (或首版直接飞线验证功能)。
