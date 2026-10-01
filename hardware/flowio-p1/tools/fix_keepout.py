# -*- coding: utf-8 -*-
"""恢复 ESP32 天线禁布区 (rule area) 并重灌所有平面。

目视检查发现: route_pcb.py 阶段1 删除全部 zones 重建时, 把 gen_pcb.py 的
天线禁布区一并删除, 导致 F/In1/B 层 GND 填充与 In2 层 +3V3 填充直接
铺进天线正下方, 会使 ESP32-S3 板载天线失配。
本脚本: 新建全铜层 rule area (禁填充/禁走线/禁过孔), 重灌, 存盘。
"""
import pcbnew

BF = "flowio-p1.kicad_pcb"
MM = pcbnew.FromMM

board = pcbnew.LoadBoard(BF)

# 天线区: x 19.5-36.5, y 0.2-6.4 (原 gen_pcb 定义 20.5-35.5/<6.4, 外扩 1mm 裕量)
X0, Y0, X1, Y1 = 19.5, 0.2, 36.5, 6.4

z = pcbnew.ZONE(board)
z.SetIsRuleArea(True)
z.SetDoNotAllowZoneFills(True)
z.SetDoNotAllowTracks(True)
z.SetDoNotAllowVias(True)
z.SetDoNotAllowPads(False)        # 模块自身焊盘不在区内, 无所谓
z.SetDoNotAllowFootprints(False)  # U1 模块本体压在区上, 必须允许
ls = pcbnew.LSET()
for lyr in (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu):
    ls.AddLayer(lyr)
z.SetLayerSet(ls)
z.SetZoneName("ANT_KEEPOUT")
ol = z.Outline()
ol.NewOutline()
for cx, cy in [(X0, Y0), (X1, Y0), (X1, Y1), (X0, Y1)]:
    ol.Append(int(MM(cx)), int(MM(cy)))
board.Add(z)
print("[keepout] rule area ANT_KEEPOUT added, layers F/In1/In2/B")

filler = pcbnew.ZONE_FILLER(board)
filler.Fill(list(board.Zones()))
pcbnew.SaveBoard(BF, board)
print("[keepout] zones refilled, board saved")
