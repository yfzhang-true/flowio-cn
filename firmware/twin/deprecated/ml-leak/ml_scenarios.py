"""ml_scenarios.py — ML-PLAN Task 1 工况矩阵与常量

场景执行器见 ml_dll.py（ctypes 直驱 DLL，快于实时）。
修订 vs 计划稿：PORT_CONFIGS 0→31（0 经 ports-or-1 退化为 1 是死配置；改为真实掩码 1/7/31）。
"""
import itertools
import numpy as np

SAMPLE_HZ = 20          # 有效采样率 = 1 点/tick（tick=50ms）。
                        # 2026-09-22 重大修正：原标 50Hz 是错的——ml_dll 每 tick 采一点，
                        # 物理分辨率即 20Hz；按 50Hz 算时间轴会把所有斜率虚高 2.5 倍
DURATION_S = 10         # 每场景采样时长
NOISE_SIGMAS = [0.2, 0.5]  # kPa 高斯噪声（2026-09-22 修正：原[0.5,1.0]淹没轻度泄漏信号，
                           # XGZP6897D 实际噪声约满量程 0.2-0.3%）

# 工况矩阵（ML-SPEC §3.1，2026-09-22 v3 修订）
LEAK_COMPONENTS = list(range(8))       # 0-6=元件 7=无泄漏
LEAK_KS         = [0.05, 0.1, 0.2, 0.5]
# v3：inflate/release 从矩阵移除——主动充/放气时执行器流量淹没泄漏信号
# （k≤0.2 在 2s 窗口不可观测，训练诊断实测），保留物理可观测的两种密封态：
OPERATIONS      = ["hold", "vacuum"]   # hold=密封正压衰减 / vacuum=密封负压回升
INIT_PRESSURES  = [20, 40, 60]          # kPa 目标（vacuum 取负）
PORT_CONFIGS    = [1, 7, 31]            # 端口掩码：单口 / 三口 / 全五口


def scenario_matrix(max_scenarios=1000):
    """v5 类平衡采样：normal/minor/major 各约 1/3（v4 的均匀组合里 comp=7 仅 ~12%，
    类先验失衡导致模型放弃 normal 类——2026-09-22 训练诊断）。
    minor=k≤0.1（含 0.05）、major=k≥0.2；同组合可重复（噪声流独立）。seed=42 可复现。"""
    import itertools
    base = list(itertools.product(
        range(8), LEAK_KS, ["hold", "vacuum"], INIT_PRESSURES, PORT_CONFIGS, NOISE_SIGMAS))
    normal_pool = [c for c in base if c[0] == 7]
    minor_pool = [c for c in base if c[0] < 7 and c[1] <= 0.1]
    major_pool = [c for c in base if c[0] < 7 and c[1] >= 0.2]
    rng = np.random.default_rng(42)
    n_each = max_scenarios // 3
    picked = ([normal_pool[i] for i in rng.integers(0, len(normal_pool), n_each)]
              + [minor_pool[i] for i in rng.integers(0, len(minor_pool), n_each)]
              + [major_pool[i] for i in rng.integers(0, len(major_pool), max_scenarios - 2 * n_each)])
    picked = [tuple(c) for c in picked]
    rng.shuffle(picked)
    return picked[:max_scenarios]
