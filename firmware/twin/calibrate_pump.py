"""calibrate_pump.py — 到货泵标定协议（真机实测 → 孪生常数）

背景（2026-09-22）：孪生泵参数当前 = 370 规格书死点(-58) + FlowIO 实测借值(61/9e-8)。
到货后跑下面三个实验，用本脚本拟合，把常数换成**本机实测值**。

实验步骤（P0 装配完成、共地确认后）：
  实验A 充气死点：堵死充气口(或全密封)，I 31 255 连续 30s，每秒记录 sensors[0]
  实验B 真空死点：堵死气路，V 31 255 连续 30s，每秒记录
  实验C 升压曲线：接实际执行器容积，I 1 255 从 0 充到死点，每 0.5s 记录
  记录格式：CSV 两列（time_s,pressure_kPa），无表头

用法：
  python calibrate_pump.py deadhead_inflate.csv   → 拟合 PUMP_P_MAX + PUMP_C（近似）
  python calibrate_pump.py deadhead_vacuum.csv    → 拟合 PUMP_P_MIN
输出：建议的 #define 修改（直接对照 twin_api.c）
"""
import sys
import numpy as np
from pathlib import Path


def load_csv(name):
    p = Path(name)
    if not p.is_absolute():
        p = Path(__file__).resolve().parent / name
    rows = [l.split(",") for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
    t = np.array([float(r[0]) for r in rows])
    y = np.array([float(r[1]) for r in rows])
    return t, y


def fit_asymptote(t, y):
    """一阶渐近 y(t)=y_inf·(1-e^(-t/tau)) 的 y_inf 估计（末端 5 点中位 + 检查收敛）"""
    tail = np.median(y[-max(5, len(y) // 10):])
    tail_var = np.std(y[-max(5, len(y) // 10):])
    converged = abs(tail_var) < 0.5  # kPa，末端抖动小于 0.5 视为已到死点
    return tail, converged


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    t, y = load_csv(sys.argv[1])
    y_inf, converged = fit_asymptote(t, y)
    print(f"数据点 {len(t)} 个，时程 {t[-1]:.1f}s")
    print(f"渐近压力（末端中位）: {y_inf:.2f} kPa   末端抖动 {'<0.5 已收敛' if converged else '≥0.5 未收敛——实验时长不足，加长到抖动平稳'}")
    if y_inf < 0:
        print(f"\n建议：#define PUMP_P_MIN_KPA ({y_inf:.1f}f)   /* 实测真空死点 {sys.argv[1]} */")
    else:
        print(f"\n建议：#define PUMP_P_MAX_KPA ({y_inf:.1f}f)   /* 实测充气死点 {sys.argv[1]} */")
        # 早期平均升压率（供 PUMP_C 人工比对；精确拟合需记录容积）
        early = y[(t >= 1) & (t <= 4)]
        te = t[(t >= 1) & (t <= 4)]
        if len(early) > 3:
            rate = np.polyfit(te, early, 1)[0]
            print(f"1-4s 平均升压率: {rate:.2f} kPa/s（对照 FlowIO 标定 2s→19/4s→35 ≈ 8-9 kPa/s，"
                  f"若明显更快说明 PUMP_C 需上调）")
    print("\n改完常数后：bash build_twin.sh && bash run_tests.sh（110 项须全绿）+ 重新生成 ML 数据集")


if __name__ == "__main__":
    main()
