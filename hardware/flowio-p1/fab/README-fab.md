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

## 工艺注意事项 (2026-10-01 终版)
- **via-in-pad ×8** (TP1.1/C12.1/LED2.1/U5.2/R24/Q11.2/D10.1/C16.1):
  需 **IPC-4761 Type VII** (树脂塞孔+电镀封帽), 请在下单备注或 Gerber 附注声明,
  否则焊膏流入孔桶造成虚焊
- **min_hole_clearance 0.25→0.20mm**: 布线终态采用 0.20 (JLC 经济档标准支持),
  若需回到 0.25 请告知重布
- DRC 终态: 未连接 0 · error 类 0 · 仅外观类豁免 (丝印压铜/库封装 courtyard)
- 连通性三重验证: KiCad DRC + KRT 铜级连图 (75 网全通, refill 交叉核对一致) + 天线禁布区 8 点探测 0 命中
