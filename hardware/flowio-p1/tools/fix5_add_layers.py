# -*- coding: utf-8 -*-
# tools/fix5_add_layers.py — 板层栈补全 (T5, 幂等): 把 Mask/SilkS/Paste 六个技术层
# 写回 (layers ...) 块。根因: gen_pcb.py 生成板时只写了 8 层最小层栈 (4 铜层 +
# Edge/Margin/双 Courtyard), kicad-cli pcb export gerbers -l 按层栈表名匹配, 表外
# 技术层静默跳过 → Mask/Silk/Paste Gerber 无法导出 (P1 包 ×11 声明从未真正兑现)。
# 行格式对齐 KiCad10 官方模板 (API_Series-500.kicad_pcb): 技术层 type 一律 "user",
# 如 (13 "F.Paste" user) / (5 "F.SilkS" user "F.Silkscreen"); 幂等 = 已存在则跳过。
import re
import sys
from pathlib import Path

BF = Path(__file__).resolve().parent.parent / "flowio-p1.kicad_pcb"
DRY = "--report" in sys.argv

# (idx, canonical, user_name) — KiCad10 层枚举: F.Mask=1 B.Mask=3 F.SilkS=5
# B.SilkS=7 F.Paste=13 B.Paste=15 (与板内 In1=4/In2=6 同一真值, 见 GetLayerName 枚举)
MISSING = [
    (1, "F.Mask", None),
    (3, "B.Mask", None),
    (5, "F.SilkS", "F.Silkscreen"),
    (7, "B.SilkS", "B.Silkscreen"),
    (13, "F.Paste", None),
    (15, "B.Paste", None),
]

text = BF.read_text(encoding="utf-8")
m = re.search(r"\t\(layers\n(.*?)\n\t\)\n", text, re.S)
if not m:
    sys.exit("layers block not found")
block = m.group(1)
have = {ln.strip().split()[0].strip("()") for ln in block.splitlines() if ln.strip()}
add = []
for idx, canon, uname in MISSING:
    if str(idx) in have:
        continue
    row = '\t\t(%d "%s" user' % (idx, canon)
    if uname:
        row += ' "%s"' % uname
    row += ")"
    add.append((idx, row))
if not add:
    print("layers block complete, no-op")
    sys.exit(0)
rows = list(block.splitlines())
n_copper = 0
for ln in rows:
    if " signal)" in ln or " power)" in ln:
        n_copper += 1
# 铁律 (实测): KiCad10 解析器要求铜层行先于 user 行 —— 追加到块尾, 铜层块不动
# (排序插入会让 (2 "B.Cu") 落到 (1 "F.Mask") 之后 → "不是一个有效的层" 解析失败)
new_rows = rows[:n_copper] + [r for _, r in sorted(add)] + rows[n_copper:]
new_block = "\n".join(new_rows)
new_text = text[:m.start(1)] + new_block + text[m.end(1):]
for i, r in add:
    print("ADD", r)
if DRY:
    print("dry-run, no write")
else:
    BF.write_bytes(new_text.encode("utf-8"))
    print("wrote %d layer rows" % len(add))
