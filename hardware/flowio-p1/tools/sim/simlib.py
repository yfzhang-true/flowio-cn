# -*- coding: utf-8 -*-
"""simlib: 零依赖电路仿真支撑 (RK4 状态机 + SVG 绘图).
运行解释器: KiCad 自带 python (含 numpy). 不依赖 ngspice/matplotlib.
模型级别: 行为级开关模型 — 注明局限, 关键数值 (纹波/过冲/损耗) 量级可信."""
import numpy as np

# ---------- SVG 绘图 ----------
def plot_svg(traces, fname, title, xlabel="t (ms)", ylabel="", w=900, h=420,
             xscale=1e-3, notes=None):
    """traces: [(name, t[], y[], color)], xscale 把 t 换算到显示单位."""
    ml, mr, mt, mb = 70, 15, 42, 46
    pw, ph = w-ml-mr, h-mt-mb
    allx = np.concatenate([np.asarray(t)*xscale for _, t, _, _ in traces])
    ally = np.concatenate([np.asarray(y) for _, _, y, _ in traces])
    x0, x1 = allx.min(), allx.max(); y0, y1 = ally.min(), ally.max()
    if y1-y0 < 1e-12: y1 = y0+1
    pad = (y1-y0)*0.08; y0 -= pad; y1 += pad
    def X(x): return ml + (x-x0)/(x1-x0+1e-15)*pw
    def Y(y): return mt + (1-(y-y0)/(y1-y0+1e-15))*ph
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" font-family="Consolas,monospace">']
    s.append(f'<rect width="{w}" height="{h}" fill="white"/>')
    s.append(f'<text x="{ml}" y="24" font-size="15" font-weight="bold">{title}</text>')
    # 网格
    for k in range(6):
        yy = y0 + (y1-y0)*k/5
        s.append(f'<line x1="{ml}" y1="{Y(yy):.1f}" x2="{w-mr}" y2="{Y(yy):.1f}" stroke="#e0e0e0"/>')
        s.append(f'<text x="{ml-6}" y="{Y(yy)+4:.1f}" font-size="11" text-anchor="end">{yy:.4g}</text>')
    for k in range(6):
        xx = x0 + (x1-x0)*k/5
        s.append(f'<line x1="{X(xx):.1f}" y1="{mt}" x2="{X(xx):.1f}" y2="{h-mb}" stroke="#e0e0e0"/>')
        s.append(f'<text x="{X(xx):.1f}" y="{h-mb+16}" font-size="11" text-anchor="middle">{xx:.4g}</text>')
    s.append(f'<text x="{ml+pw/2}" y="{h-8}" font-size="12" text-anchor="middle">{xlabel}</text>')
    s.append(f'<text x="14" y="{mt+ph/2}" font-size="12" text-anchor="middle" transform="rotate(-90 14 {mt+ph/2})">{ylabel}</text>')
    for name, t, y, c in traces:
        pts = " ".join(f"{X(ti*xscale):.1f},{Y(v):.1f}" for ti, v in zip(t, y))
        s.append(f'<polyline points="{pts}" fill="none" stroke="{c}" stroke-width="1.3"/>')
    lg = 0
    for name, t, y, c in traces:
        s.append(f'<rect x="{ml+8+lg*150}" y="{mt+6}" width="10" height="4" fill="{c}"/>')
        s.append(f'<text x="{ml+22+lg*150}" y="{mt+11}" font-size="11">{name}</text>')
        lg += 1
    if notes:
        ny = mt+30
        for nline in notes:
            s.append(f'<text x="{ml+8}" y="{ny}" font-size="11" fill="#444">{nline}</text>')
            ny += 14
    s.append('</svg>')
    open(fname, 'w', encoding='utf-8').write("\n".join(s))

# ---------- 二极管指数模型 ----------
def diode_i(v, Is=1e-7, n=1.2, vt=0.02585):
    x = v/(n*vt)
    if x > 40: return Is*np.exp(40)*(1+(x-40))
    return Is*(np.exp(np.clip(x, 0, 40))-1)
