# -*- coding: utf-8 -*-
"""sim_export — sim_engine `--export` 离线交付物生成 (纯 stdlib SVG + markdown).

数据唯一真源是 sim_engine.run() 默认参数; 本模块不自带任何物理内核,
只负责把 {metrics, waves, notes} 渲染为旧版式交付物:
  - plot_svg(): 900x420 折线图 (坐标轴/5x5 网格/图例/notes), 视觉规格对照
    旧 hardware/flowio-p1/tools/sim/simlib.plot_svg (已归档
    firmware/twin/deprecated/sim-legacy, 依赖 KiCad python+numpy)——此处
    移植为纯 stdlib, 无 numpy。
  - export_all(out_dir): 四电路 → buck_startup/buck_ripple/dior_share/
    valve_pwm/i2c_rise 共 5 张 SVG + sim-report.md, Path.write_bytes 落盘。

旧版 buck_loadstep.svg 不再生成: 引擎参数域为恒定负载 (iload 0.1~3A 可扫),
时变负载激励属归档工具专有, 等价检查由前端重算页 iload 参数扫描覆盖。
"""
import datetime
from pathlib import Path

import sim_engine as se

C1, C2 = "#d62728", "#1f77b4"     # 旧版配色: 红=电压/主量, 蓝=电流/次量

_W, _H = 900, 420                  # 画布 (同旧 simlib)
_ML, _MR, _MT, _MB = 70, 15, 42, 46


def _esc(s):
    """SVG 文本节点最小转义."""
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def plot_svg(traces, fname, title, xlabel="t (ms)", ylabel="", xscale=1.0,
             notes=None, w=_W, h=_H):
    """纯 stdlib SVG 折线图. traces: [(name, t[], y[], color)];
    xscale 把 x 数据换算到显示单位 (1e3: s→ms, 1e6: s→µs, 1: 原单位).
    直接 Path.write_bytes 落盘, 返回写入字节数."""
    ml, mr, mt, mb = _ML, _MR, _MT, _MB
    pw, ph = w - ml - mr, h - mt - mb
    xs = [float(tv) * xscale for _n, t, _y, _c in traces for tv in t]
    ys = [float(v) for _n, _t, y, _c in traces for v in y]
    if not xs or not ys:
        raise ValueError("plot_svg: 空波形")
    x0, x1 = min(xs), max(xs)
    y0, y1 = min(ys), max(ys)
    if y1 - y0 < 1e-12:
        y1 = y0 + 1.0
    if x1 - x0 < 1e-15:
        x1 = x0 + 1.0
    pad = (y1 - y0) * 0.08
    y0 -= pad
    y1 += pad

    def X(x):
        return ml + (x - x0) / (x1 - x0) * pw

    def Y(y):
        return mt + (1.0 - (y - y0) / (y1 - y0)) * ph

    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
         f'font-family="Consolas,monospace">']
    s.append(f'<rect width="{w}" height="{h}" fill="white"/>')
    s.append(f'<text x="{ml}" y="24" font-size="15" font-weight="bold">{_esc(title)}</text>')
    for k in range(6):                                   # 横向网格 + y 刻度
        yy = y0 + (y1 - y0) * k / 5.0
        s.append(f'<line x1="{ml}" y1="{Y(yy):.1f}" x2="{w - mr}" y2="{Y(yy):.1f}" stroke="#e0e0e0"/>')
        s.append(f'<text x="{ml - 6}" y="{Y(yy) + 4:.1f}" font-size="11" text-anchor="end">{yy:.4g}</text>')
    for k in range(6):                                   # 纵向网格 + x 刻度
        xx = x0 + (x1 - x0) * k / 5.0
        s.append(f'<line x1="{X(xx):.1f}" y1="{mt}" x2="{X(xx):.1f}" y2="{h - mb}" stroke="#e0e0e0"/>')
        s.append(f'<text x="{X(xx):.1f}" y="{h - mb + 16}" font-size="11" text-anchor="middle">{xx:.4g}</text>')
    s.append(f'<text x="{ml + pw / 2:.1f}" y="{h - 8}" font-size="12" text-anchor="middle">{_esc(xlabel)}</text>')
    s.append(f'<text x="14" y="{mt + ph / 2:.1f}" font-size="12" text-anchor="middle" '
             f'transform="rotate(-90 14 {mt + ph / 2:.1f})">{_esc(ylabel)}</text>')
    for name, t, y, c in traces:                         # 数据折线
        pts = " ".join(f"{X(ti * xscale):.1f},{Y(v):.1f}" for ti, v in zip(t, y))
        s.append(f'<polyline points="{pts}" fill="none" stroke="{c}" stroke-width="1.3"/>')
    for lg, (name, _t, _y, c) in enumerate(traces):      # 图例
        s.append(f'<rect x="{ml + 8 + lg * 150}" y="{mt + 6}" width="10" height="4" fill="{c}"/>')
        s.append(f'<text x="{ml + 22 + lg * 150}" y="{mt + 11}" font-size="11">{_esc(name)}</text>')
    if notes:                                            # 左上注释块
        ny = mt + 30
        for nline in notes:
            s.append(f'<text x="{ml + 8}" y="{ny}" font-size="11" fill="#444">{_esc(nline)}</text>')
            ny += 14
    s.append('</svg>')
    return Path(fname).write_bytes("\n".join(s).encode("utf-8"))


# ---------------------------------------------------------------- 报告小工具
def _g(v):
    """紧凑数值 (md 表格用, 去尾零)."""
    return "%.6g" % float(v)


def _fmt_val(value, unit):
    """指标值友好化: s→µs/ms, 无单位比值→百分比, 其余 4 位有效数字."""
    v = float(value)
    if unit == "s":
        return ("%.3f ms" % (v * 1e3)) if abs(v) >= 1e-3 else ("%.3f µs" % (v * 1e6))
    if unit == "":
        return "%.1f%%" % (v * 100.0)
    return "%.4g %s" % (v, unit)


def _wv(res, name):
    """按名取波形 → (t, y)."""
    for wv in res["waves"]:
        if wv["name"] == name:
            return wv["t"], wv["y"]
    raise KeyError("波形 %r 不存在, 可选 %s" % (name, [w["name"] for w in res["waves"]]))


def _window(t, y, t_min):
    """取 t>t_min 的稳态窗 (返回两个 list)."""
    xs = [(tv, yv) for tv, yv in zip(t, y) if tv > t_min]
    return [p[0] for p in xs], [p[1] for p in xs]


def _mmap(res):
    return {m["name"]: m for m in res["metrics"]}


# ---------------------------------------------------------------- 导出主体
_TITLES = {                       # 电路 → 报告小节标题 (与旧版对应)
    "buck":  "TPS54331 Buck 5V→3.27V (L=6.8µH, Cout=113µF, fsw=570kHz)",
    "dior":  "双 SS34 二极管-或输入 (DC-005 ‖ USB-C VBUS)",
    "valve": "AO3400A 低边阀驱动 (PWM 10Hz/50%, 线圈 14Ω/25mH)",
    "i2c":   "I2C 总线 (TCA9548A + 5×传感器, 4.7k 上拉, Cbus≈115pF)",
}
_SVGS = {                         # 电路 → 本节引用的 SVG 文件名
    "buck":  ["buck_startup.svg", "buck_ripple.svg"],
    "dior":  ["dior_share.svg"],
    "valve": ["valve_pwm.svg"],
    "i2c":   ["i2c_rise.svg"],
}


def export_all(out_dir=None):
    """四电路默认参数 → 5 张 SVG + sim-report.md. 返回产出文件 Path 列表."""
    out = Path(out_dir) if out_dir else Path(__file__).resolve().parent / "sim_out"
    out.mkdir(parents=True, exist_ok=True)
    files, results = [], {}
    for c in ("buck", "dior", "valve", "i2c"):
        results[c] = se.run(c, {})

    # ---- 1) buck: 启动全程 + 稳态纹波窗 (同一 run 的 waves 派生) ----
    rb = results["buck"]
    mb = _mmap(rb)
    tv, vv = _wv(rb, "Vout")
    _ti, il = _wv(rb, "iL")
    plot_svg([("Vout", tv, vv, C1), ("iL", tv, il, C2)],
             out / "buck_startup.svg",
             "TPS54331 启动+稳态 (软启动 0.5ms, 负载 3A, fsw 570kHz)",
             "t (ms)", "V / A", xscale=1e3,
             notes=[rb["notes"][0],
                    "稳态均值 %.3fV, 纹波 %.1fmVpp, 峰值电感电流 %.2fA"
                    % (mb["输出电压"]["value"], mb["稳态纹波"]["value"],
                       mb["电感电流纹波"]["value"])])
    files.append(out / "buck_startup.svg")
    tw_v, w_v = _window(tv, vv, 2.2e-3)               # T>2.2ms 稳态窗
    tw_i, w_i = _window(tv, il, 2.2e-3)
    plot_svg([("Vout", tw_v, w_v, C1), ("iL", tw_i, w_i, C2)],
             out / "buck_ripple.svg",
             "稳态纹波 @ 3A 负载 (T>2.2ms 稳态窗)",
             "t (ms)", "V / A", xscale=1e3,
             notes=["Vout 纹波 pp %.1fmV (指标表同源), iL pp %.2fApp"
                    % (mb["稳态纹波"]["value"], mb["电感电流纹波"]["value"]),
                    "折线为引擎 waves (1500 点) 稳态窗切片, 开关纹波呈包络"])
    files.append(out / "buck_ripple.svg")

    # ---- 2) dior: 分流 vs V_DC 扫描 ----
    rd = results["dior"]
    md_ = _mmap(rd)
    td, ddc = _wv(rd, "DC侧电流")
    _tu, usb = _wv(rd, "USB侧电流")
    plot_svg([("DC 侧电流 (mA)", td, ddc, C1), ("USB 侧电流 (mA)", td, usb, C2)],
             out / "dior_share.svg",
             "二极管-或 输入分流 vs DC 座电压 (USB=5.1V, 负载 0.5A)",
             "V_DC (V)", "mA", xscale=1.0,
             notes=["V_DC=5.0V 处: DC 供 %.0fmA, USB 供 %.0fmA"
                    % (md_["DC侧电流"]["value"] * 1e3, md_["USB分流@DC5V"]["value"] * 1e3)])
    files.append(out / "dior_share.svg")

    # ---- 3) valve: 末 2 周期 PWM ----
    rv = results["valve"]
    mv = _mmap(rv)
    tva, ival = _wv(rv, "阀电流")
    _tg, vg = _wv(rv, "Vgs")
    plot_svg([("i 阀电流 (A)", tva, ival, C1), ("Vgs (V)", tva, vg, C2)],
             out / "valve_pwm.svg",
             "AO3400A 驱动阀线圈 PWM 10Hz/50% (τ=L/R=1.8ms)",
             "t (ms)", "A / V", xscale=1e3,
             notes=["稳态峰值电流 %.3fA (阀额定 0.35A)" % mv["稳态阀电流"]["value"],
                    "关断续流由 SS14 钳位至 -0.35V, 无高压尖峰"])
    files.append(out / "valve_pwm.svg")

    # ---- 4) i2c: 上升沿 ----
    ri = results["i2c"]
    mi = _mmap(ri)
    ti, vi = _wv(ri, "SDA/SCL")
    plot_svg([("SDA/SCL (V)", ti, vi, C2)],
             out / "i2c_rise.svg",
             "I2C 总线上升沿 (4.7k 上拉, Cbus=115pF)",
             "t (µs)", "V", xscale=1e6,
             notes=[ri["notes"][0]])
    files.append(out / "i2c_rise.svg")

    # ---- 5) 汇总 sim-report.md ----
    today = datetime.date.today().isoformat()
    md = ["# FLOWIO 电路仿真报告 (sim_engine 离线导出)", "",
          "> 日期: %s · 真源: `firmware/twin/sim_engine.py` (纯 stdlib 参数化引擎) · "
          "再生成: `python sim_engine.py --export`" % today,
          "> 本文件与同目录 5 张 SVG 由 `sim_export.py` 生成 (无 numpy); 旧 "
          "`hardware/flowio-p1/tools/sim/` 已归档至 `firmware/twin/deprecated/sim-legacy/`, 仅存历史.",
          "",
          "> **模型级局限** (spec §10.3): 行为级状态机——半导体用简化开关/指数模型, "
          "控制环为行为级 PI; 数值量级可信, 非厂商 SPICE 精度.",
          "> **参数成色** (spec §10.3): 默认参数为 BOM 实值 (L1 6.8µH / C7+C8 100µF / "
          "R4 10k / R5 3.24k / SS34 / SS14 / AO3400A / R8 R9 4.7k), 是全项目电气参数中最硬一档 "
          "(buck 分压比即板上实阻); 手册/假设档参数及回板校准动线见 spec §10 校准矩阵.",
          ""]
    verdicts = []
    for i, c in enumerate(("buck", "dior", "valve", "i2c"), 1):
        r = results[c]
        md.append("### %d. %s" % (i, _TITLES[c]))
        md.append("")
        md.append("| 参数 | 默认值 | 允许范围 |")
        md.append("|---|---|---|")
        spec = {name: (lo, hi) for name, lo, hi, _d in se.SPEC[c]}
        for k in sorted(r["params"]):
            lo, hi = spec[k]
            md.append("| `%s` | %s | [%s, %s] |" % (k, _g(r["params"][k]), _g(lo), _g(hi)))
        md.append("")
        md.append("| 指标 | 仿真值 | 判定 |")
        md.append("|---|---|---|")
        for m in r["metrics"]:
            md.append("| %s | %s | %s |" % (m["name"], _fmt_val(m["value"], m["unit"]), m["verdict"]))
            verdicts.append("⚠" in m["verdict"])
        md.append("")
        for nline in r["notes"]:
            md.append("- %s" % nline)
        md.append("")
        md.append("波形: %s" % " / ".join("`%s`" % s for s in _SVGS[c]))
        md.append("")
    n_warn = sum(verdicts)
    md.append("## 汇总结论")
    md.append("")
    md.append("- 四电路共 %d 项指标, %s (数据源 `sim_engine.run` 默认参数, "
              "与前端 `/api/sim` 重算端点同一内核)."
              % (len(verdicts),
                 "全部在预算内" if n_warn == 0 else "%d 项告警 ⚠, 见上表" % n_warn))
    md.append("- 与旧版交付物差异: `buck_loadstep.svg` 不再生成——引擎参数域为恒定负载 "
              "(iload 0.1~3A 可扫), 时变负载激励属归档工具专有; 等价检查由前端重算页 "
              "iload 参数扫描覆盖. 其余 5 图命名与旧版一一对应.")
    md.append("- 待回板实测项: 效率, 纹波示波器对照, 阀线圈实际 L 值 (spec §10.4 校准动线).")
    files.append(out / "sim-report.md")
    (out / "sim-report.md").write_bytes("\n".join(md).encode("utf-8"))
    return files


if __name__ == "__main__":                    # 允许直接 python sim_export.py
    for f in export_all():
        print("写出", f)
