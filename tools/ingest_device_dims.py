# -*- coding: utf-8 -*-
"""ingest_device_dims.py — devices_raw.json (jlcpcb MCP 快照) + curated 尺寸/端口语义
-> enclosure/devices.json (器件几何单一数据层, plan T1).

curated 来源: JLC 描述/属性字段优先 (Height Above Board / Body Height / Z-Height /
尺寸), 缺者取 datasheet 公称值; 端口 dir_local 由 17 连接器与侧槽吻合反推并经
槽位真值交叉验证 (推导: KiCad rot 为 y-down 系 CCW, 板系 y-up 需取 -rot).

用法: python tools/ingest_device_dims.py   (纯标准库, 任意 python 可跑)
"""
import csv
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent                                # worktree 根 (tools/ 的上级)
ENC = REPO / "hardware" / "flowio-p1" / "enclosure"
BOM = REPO / "hardware" / "flowio-p1" / "fab" / "flowio-p1-bom-jlc.csv"

# lcsc -> (dims w/d/h mm; placement; pkg_keywords; port?)
# h = 板上高度 (above board). 端口 exit_z 相对板面 Z_TOP 的 [lo, hi].
CURATED = {
    "C13585":  dict(dims=(3.2, 1.6, 1.6),  placement="INTERNAL", pkg=["C1206", "CL31A106"]),
    "C15008":  dict(dims=(3.2, 1.6, 1.6),  placement="INTERNAL", pkg=["C_1206", "CL31A107"]),
    "C1591":   dict(dims=(1.6, 0.8, 0.8),  placement="INTERNAL", pkg=["C_0603", "CL10B104"]),
    "C33353":  dict(dims=(1.6, 0.8, 0.8),  placement="INTERNAL", pkg=["CL10C222"]),
    "C1653":   dict(dims=(1.6, 0.8, 0.8),  placement="INTERNAL", pkg=["CL10C220"]),
    "C15849":  dict(dims=(1.6, 0.8, 0.8),  placement="INTERNAL", pkg=["CL10A105"]),
    "C8678":   dict(dims=(4.3, 2.6, 2.1),  placement="INTERNAL", pkg=["SMA"]),
    "C2480":   dict(dims=(4.3, 2.6, 2.1),  placement="INTERNAL", pkg=["SMA"]),
    "C456012": dict(dims=(8.0, 10.3, 3.2), placement="EDGE_OUT", pkg=["TYPE-C"],
                    port=dict(type="usb", dir_local=[0, -1], exit_z=[0.0, 3.2])),
    "C167253": dict(dims=(10.2, 10.2, 3.0), placement="SURFACE", pkg=["CDRH", "IND-SMD"]),
    "C2843785":dict(dims=(5.0, 5.0, 1.6),  placement="SURFACE", pkg=["WS2812", "5050"]),
    "C2286":   dict(dims=(1.6, 0.8, 0.8),  placement="INTERNAL", pkg=["LED", "KT-0603R"]),
    "C2288":   dict(dims=(1.6, 0.8, 0.8),  placement="INTERNAL", pkg=["KT-0603B"]),
    "C125100": dict(dims=(1.6, 0.8, 0.8),  placement="INTERNAL", pkg=["LTST-C191"]),
    "C20917":  dict(dims=(2.9, 2.4, 1.2),  placement="INTERNAL", pkg=["SOT-23", "AO3400"]),
    "C181160": dict(dims=(2.9, 2.4, 1.2),  placement="INTERNAL", pkg=["SOT-23", "SS8050"]),
    "C23186":  dict(dims=(1.6, 0.8, 0.5),  placement="INTERNAL", pkg=["R0603", "0603WAF5101"]),
    "C14675":  dict(dims=(1.6, 0.8, 0.5),  placement="INTERNAL", pkg=["RC0603"]),
    "C25804":  dict(dims=(1.6, 0.8, 0.5),  placement="INTERNAL", pkg=["0603WAF1002"]),
    "C22994":  dict(dims=(1.6, 0.8, 0.5),  placement="INTERNAL", pkg=["0603WAF3241"]),
    "C23162":  dict(dims=(1.6, 0.8, 0.5),  placement="INTERNAL", pkg=["0603WAF4701"]),
    "C21190":  dict(dims=(1.6, 0.8, 0.5),  placement="INTERNAL", pkg=["0603WAF1001"]),
    "C23138":  dict(dims=(1.6, 0.8, 0.5),  placement="INTERNAL", pkg=["0603WAF3300"]),
    "C23345":  dict(dims=(1.6, 0.8, 0.5),  placement="INTERNAL", pkg=["0603WAF220"]),
    "C589191": dict(dims=(4.0, 3.0, 2.0),  placement="SURFACE", pkg=["SW-SMD", "ST-1185"]),
    "C2913202":dict(dims=(18.0, 25.5, 3.1), placement="SURFACE", pkg=["WROOM", "ESP32-S3"]),
    "C130026": dict(dims=(7.8, 4.4, 1.1),  placement="INTERNAL", pkg=["TSSOP", "TCA9548"]),
    "C9865":   dict(dims=(4.9, 3.9, 1.75), placement="INTERNAL", pkg=["SOP", "TPS54331", "SOIC"]),
    "C968586": dict(dims=(4.9, 3.9, 1.75), placement="INTERNAL", pkg=["ESSOP", "CH340"]),
    "C7519":   dict(dims=(2.9, 2.4, 1.1),  placement="INTERNAL", pkg=["SOT-23-6", "USBLC6"]),
    # ── 对外连接器 (端口本地方向经槽位真值交叉验证) ──
    "C5359632":dict(dims=(5.9, 12.5, 7.0), placement="EDGE_OUT", pkg=["CONN-TH_4P", "6173868"],
                    port=dict(type="electrical", dir_local=[0, -1], exit_z=[0.0, 7.0])),
    # P1.1 T3 新增 (JLC 属性页真值):
    "C165948": dict(dims=(8.94, 7.35, 3.26), placement="EDGE_OUT", pkg=["TYPE-C", "TYPE-C-31-M-12"],
                    port=dict(type="usb", dir_local=[0, -1], exit_z=[0.0, 3.26])),
    "C7429671":dict(dims=(10.0, 7.8, 6.2), placement="EDGE_OUT",
                    pkg=["CONN-SMD_2P", "ZX-XH2.54"],
                    port=dict(type="pneumatic_wire", dir_local=[0, -1], exit_z=[0.0, 6.2])),
}

# 淘宝件 (BOM 无 LCSC 码, 由 make_bom 排除; 几何真值进 devices 段供 L5 碰撞/贴边守门)
CURATED_NOPART = [
    dict(lcsc="", name="XGZP6897D (淘宝件 CFSensor 闽芯)", refs=["U6"],
         pkg=["XGZP6897D-SOP8"], dims=(7.96, 10.6, 9.5), placement="INTERNAL"),
]

DS = "https://www.lcsc.com/datasheet/lcsc_datasheet"


def main():
    raw = {p["id"]: p for p in json.loads((ENC / "devices_raw.json").read_text(encoding="utf-8"))["parts"]}
    rows = list(csv.DictReader(open(BOM, encoding="utf-8-sig")))

    refs_by_c = {}
    for r in rows:
        c = (r["LCSC Part #"] or "").strip()
        for ref in (r["Designator"] or "").split(","):
            ref = ref.strip()
            if ref:
                refs_by_c.setdefault(c, []).append(ref)

    devices = []
    for c in sorted(refs_by_c, key=lambda x: (x != "C7429671", x)):
        cur = CURATED[c]
        r = raw.get(c, {})
        e = {
            "lcsc": c,
            "name": r.get("name", "?"),
            "refs": sorted(refs_by_c[c], key=lambda s: (len(s), s)),
            "pkg_keywords": cur["pkg"],
            "dims": {"w": cur["dims"][0], "d": cur["dims"][1], "h": cur["dims"][2]},
            "placement": cur["placement"],
            "datasheet": r.get("datasheet", ""),
            "jlc_desc": r.get("desc", ""),
        }
        if "port" in cur:
            e["port"] = cur["port"]
        devices.append(e)
    # 淘宝件补段 (BOM 无码, 位姿仍来自 pos.csv; L5 dims_for 靠 pkg 关键词命中)
    for cur in CURATED_NOPART:
        devices.append({
            "lcsc": cur["lcsc"], "name": cur["name"], "refs": cur["refs"],
            "pkg_keywords": cur["pkg"],
            "dims": {"w": cur["dims"][0], "d": cur["dims"][1], "h": cur["dims"][2]},
            "placement": cur["placement"],
            "datasheet": "", "jlc_desc": "淘宝件不入 JLC BOM",
        })

    out = {
        "_meta": {
            "generated_by": "tools/ingest_device_dims.py",
            "provenance": "devices_raw.json (jlcpcb MCP) + curated datasheet dims",
            "conventions": {
                "dims": "w=封装rot0时X向, d=Y向, h=板上高度(above board), 单位mm",
                "port.dir_local": "rot=0 时端口开口方向(板系x右/y上, KiCad y-down 取 -rot 变换)",
                "port.exit_z": "相对板面 Z_TOP 的 [lo,hi] 开口z带",
            },
        },
        "devices": devices,
    }
    # 保留既有 pneumatic_devices 段 (T1 入库, 本工具不产出 — 无此守卫会被覆写丢失)
    old = ENC / "devices.json"
    if old.exists():
        try:
            pn = json.loads(old.read_text(encoding="utf-8")).get("pneumatic_devices")
            if pn:
                out["pneumatic_devices"] = pn
        except Exception:
            pass
    (ENC / "devices.json").write_bytes(json.dumps(out, ensure_ascii=False, indent=1).encode("utf-8"))
    edge = [d["lcsc"] for d in devices if d["placement"] == "EDGE_OUT"]
    print("[ingest] devices.json: %d 条 (唯一C号), EDGE_OUT=%d, refs=%d"
          % (len(devices), len(edge), sum(len(d["refs"]) for d in devices)))
    print("[ingest] OK ->", ENC / "devices.json")


if __name__ == "__main__":
    main()
