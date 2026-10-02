#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""gen_tickets.py — 按 spec 2026-10-02-acceptance-book-design.md §2 三表批量生成 36 张验收工单。

36 行清单 = 真源：SW 六张（回板前软件侧，status=pass + 证据链接）+ HW 二十四张（BRINGUP 九章）
+ CAL 六张（孪生标定对拍）。notes 非空即预填 pass。自 E:/FLOWIO/ 运行。
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ticket

# (id, title, phase, bringup, book_ch, notes) —— notes 非空 => status=pass（证据已归档）
TICKETS = [
    # --- Phase SW 软件侧（回板前即可执行，6 张） ---
    ("A101", "孪生 v2 首屏装配叙事 + 爆炸滑杆", "sw", "-", 11, ["`firmware/twin/shots/v2_*.png` — 26 项目视记录已归档（v2_01_intro.png / v2_02_explode50.png 等，commit ec3cefa）"]),
    ("A102", "电流/气流联动：I/V/S 命令差分截图", "sw", "-", 11, ["`firmware/twin/shots/v2_03_inflate.png`（I 全充）/ `v2_05_vacuum.png`（V 抽真空）/ `v2_04_silent.png`（S 静默态）— 差分截图已归档"]),
    ("A103", "仿真实验室四电路重算（含 i2c ⚠ 案例）", "sw", "-", 9, ["`firmware/twin/shots/v2_08_simlab.png` 四电路重算 + `firmware/twin/test_webapp.js` 44 断言"]),
    ("A104", "SDK 协议向量双向 + hello_globe 冒烟", "sw", "-", 10, ["`sdk/python/tests/` 9 向量（`test_protocol.py` × `vectors.json` 双向编解码）+ hello_globe 冒烟"]),
    ("A105", "固件 QEMU 冒烟 + 主机 33 测试", "sw", "-", 7, ["`firmware/tests/` 主机 33 测试全绿 + `firmware/qemu_smoke.sh` QEMU 冒烟"]),
    ("A106", "BLE 契约载荷向量（nRF Connect 待真机，向量先验）", "sw", "-", 8, ["`firmware/twin/BLE.md` §4.1 cmd 0xA5 5B 帧 / §4.2 state 20B LE 载荷向量（真机验证回板后归 A209）"]),
    # --- Phase HW 回板后（BRINGUP 九章，24 张） ---
    ("A201", "首电三测（万用表）", "hw", "1", 11, None),
    ("A202", "CH340 烧录/自动复位", "hw", "1", 11, None),
    ("A203", "74HCT245 电平迁移（示波器）", "hw", "2", 11, None),
    ("A204", "MOS 触发栅极/Vds 波形（示波器）", "hw", "2", 11, None),
    ("A205", "WS2812 状态灯", "hw", "4", 11, None),
    ("A206", "TCA 五通道扫描", "hw", "3", 11, None),
    ("A207", "8 阀全功能（听声+电流）", "hw", "5", 11, None),
    ("A208", "I2C tr 实测（100/400kHz 裁决）", "hw", "6", 11, None),
    ("A209", "BLE 三步（扫描/写/订阅）", "hw", "8", 11, None),
    ("A210", "gui 真机模式（Web Bluetooth）", "hw", "8", 11, None),
    ("A211", "电气校准①阀线圈 R/L（万用表+LCR）", "hw", "7", 11, None),
    ("A212", "电气校准②AO3400 RDS（示波器反推）", "hw", "7", 11, None),
    ("A213", "电气校准③buck ESR/Cout（纹波反推）", "hw", "7", 11, None),
    ("A214", "电气校准④负载调整率/效率（4 线法）", "hw", "7", 11, None),
    ("A215", "电气校准⑤⑥θja 红外 + ESP32 电流钳", "hw", "7", 11, None),
    ("A216", "泵实验A 充气死点（calibrate_pump.py）", "hw", "9", 11, None),
    ("A217", "泵实验B 真空死点（calibrate_pump.py）", "hw", "9", 11, None),
    ("A218", "泵实验C 升压曲线（calibrate_pump.py）", "hw", "9", 11, None),
    ("A219", "闭环充气到目标 kPa", "hw", "9", 11, None),
    ("A220", "外壳装配（M3 自攻 + 端子开孔对位）", "hw", "9+", 11, None),
    ("A221", "整机气密（保压 60s）", "hw", "9+", 11, None),
    ("A222", "长跑温升", "hw", "9+", 11, None),
    ("A223", "8 阀轮巡", "hw", "9+", 11, None),
    ("A224", "满载纹波", "hw", "9+", 11, None),
    # --- Phase CAL 补充（孪生标定对拍，6 张，书稿第 12 章核心卖点） ---
    ("A301", "孪生对拍：阀驱动电流曲线（BOARD_PARAMS R/L 改后叠图）", "cal", "7", 12, None),
    ("A302", "孪生对拍：电源效率/纹波（4 线法实测叠图）", "cal", "7", 12, None),
    ("A303", "孪生对拍：热学温升（θja 修正后叠图）", "cal", "7", 12, None),
    ("A304", "孪生对拍：充气升压曲线（实验C CSV 叠图）", "cal", "9", 12, None),
    ("A305", "孪生对拍：真空死点曲线（实验B CSV 叠图）", "cal", "9", 12, None),
    ("A306", "孪生对拍：闭环精度 + 数字孪生精度报告", "cal", "9", 12, None),
]


def main():
    assert len(TICKETS) == 36, f"清单应为 36 张，得到 {len(TICKETS)}"
    ids = [t[0] for t in TICKETS]
    assert len(set(ids)) == 36, "工单 ID 重复"
    for tid, title, phase, bringup, book_ch, notes in TICKETS:
        ticket.new(tid, title, phase=phase, bringup=bringup, book_ch=book_ch,
                   root=".", status="pass" if notes else "pending", notes=notes)
    rep = ticket.report(root=".")
    print(rep)
    made = sorted(p.name for p in ticket.tickets_dir(".").glob("A*.yaml"))
    assert len(made) == 36, f"落盘 {len(made)} 张 ≠ 36"
    if "pass 6 · pending 30" not in rep:
        raise SystemExit("FAIL: 期望 pass 6 / pending 30")
    print(f"OK: 36 张工单落盘 book/tickets/（{made[0]} … {made[-1]}）")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    main()
