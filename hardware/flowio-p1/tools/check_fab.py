# -*- coding: utf-8 -*-
# tools/check_fab.py — fab 制造包完整性守门 (T5, 纯 stdlib, 只读):
#   ① 14 层 Gerber 齐全非空 (header+M02 收尾)  ② Edge.Cuts bbox = 100x80mm
#   ③ JLC zip 13 文件与散件逐字节一致          ④ 钻孔 450 (NPTH 6 = 4xM3 + 2x0.6)
#   ⑤ pos 行数  ⑥ gbrjob 4 层/尺寸             全绿 exit 0, 任一红 exit 1。
# 用法: python tools/check_fab.py   (cwd = hardware/flowio-p1)
# 全绿 exit 0 (22 断言 = 14 Gerber + Edge 1 + zip 2 + 钻孔 3 + pos 1 + gbrjob 1);
# 挂 rebuild-matrix place_layout / footprint_rules 链尾 (fab 重出后必跑, 见 fab/README-fab)。
import re
import sys
import zipfile
from pathlib import Path

FAB = Path(__file__).resolve().parent.parent / "fab"
GERBERS = ["F_Cu.gtl", "In1_Cu.g1", "In2_Cu.g2", "B_Cu.gbl",
           "F_Paste.gtp", "B_Paste.gbp", "F_Silkscreen.gto", "B_Silkscreen.gbo",
           "F_Mask.gts", "B_Mask.gbs", "Edge_Cuts.gm1",
           "F_Courtyard.gbr", "B_Courtyard.gbr", "Margin.gbr"]
ZIP_FILES = ["flowio-p1-F_Cu.gtl", "flowio-p1-In1_Cu.g1", "flowio-p1-In2_Cu.g2",
             "flowio-p1-B_Cu.gbl", "flowio-p1-F_Paste.gtp", "flowio-p1-B_Paste.gbp",
             "flowio-p1-F_Silkscreen.gto", "flowio-p1-B_Silkscreen.gbo",
             "flowio-p1-F_Mask.gts", "flowio-p1-B_Mask.gbs", "flowio-p1-Edge_Cuts.gm1",
             "flowio-p1-job.gbrjob", "flowio-p1.drl"]

fails = []


def check(name, ok, detail=""):
    print("[%s] %s%s" % ("PASS" if ok else "FAIL", name, "  | " + detail if detail else ""))
    if not ok:
        fails.append(name)


# ① Gerber 齐全非空
for g in GERBERS:
    p = FAB / ("flowio-p1-" + g)
    ok = p.exists() and p.stat().st_size > 100
    txt = p.read_text(encoding="utf-8", errors="replace") if ok else ""
    check("gerber %s 非空且 M02 收尾" % g, ok and txt.rstrip().endswith("M02*"),
          "%dB" % p.stat().st_size if ok else "missing")

# ② Edge.Cuts bbox
txt = (FAB / "flowio-p1-Edge_Cuts.gm1").read_text()
xs = [int(m) / 1e6 for m in re.findall(r"X(-?\d+)", txt)]
ys = [int(m) / 1e6 for m in re.findall(r"Y(-?\d+)", txt)]
w, h = max(xs) - min(xs), max(ys) - min(ys)
check("Edge.Cuts 板框 %.3f x %.3f mm = 100x80" % (abs(w), abs(h)),
      abs(abs(w) - 100.0) < 0.01 and abs(abs(h) - 80.0) < 0.01,
      "X[%.2f,%.2f] Y[%.2f,%.2f]" % (min(xs), max(xs), min(ys), max(ys)))

# ③ zip 与散件一致
z = zipfile.ZipFile(FAB / "flowio-p1-jlc.zip")
names = sorted(i.filename for i in z.infolist())
check("JLC zip 文件清单 13 项", names == sorted(ZIP_FILES), "%d 项" % len(names))
same = all(z.read(n) == (FAB / n).read_bytes() for n in names)
check("zip 内容与散件逐字节一致", same)

# ④ 钻孔
sys.path.insert(0, str(FAB))
import drl  # noqa: E402
holes = drl.holes()
npth = drl.npth_holes()
m3 = [(round(x, 1), round(y, 1)) for x, y, d in npth if abs(d - 3.2) < 0.01]
check("钻孔总数 450 (含布线过孔 416)", len(holes) == 450, "实测 %d" % len(holes))
check("NPTH 6 (4xM3-Ø3.2 + 2xØ0.6)", len(npth) == 6,
      "M3@%s Ø0.6×%d" % (m3, sum(1 for x, y, d in npth if abs(d - 0.6) < 0.01)))
check("M3 孔位=铜柱 ST", sorted(m3) == sorted([(3.0, 28.0), (3.4, 3.4),
                                                (73.5, 55.7), (83.0, 12.5)]))

# ⑤ pos 行数
pos = (FAB / "flowio-p1-pos.csv").read_text().strip().splitlines()
check("pos.csv 位号行 147 (含表头 148)", len(pos) == 148, "%d 行" % len(pos))

# ⑥ gbrjob
job = (FAB / "flowio-p1-job.gbrjob").read_text()
check("gbrjob: 4 层 / 100.1x80.1 / 板厚 1.6",
      '"LayerNumber": 4' in job and '"X": 100.1' in job and '"Y": 80.1' in job
      and '"BoardThickness": 1.6' in job)

print("CHECK_FAB", "PASS" if not fails else "FAIL (%s)" % fails)
sys.exit(0 if not fails else 1)
