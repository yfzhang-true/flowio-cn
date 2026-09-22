"""ml_scenarios.py — ML-PLAN Task 1 工况矩阵与常量

场景执行器见 ml_dll.py（ctypes 直驱 DLL，快于实时）。
修订 vs 计划稿：PORT_CONFIGS 0→31（0 经 ports-or-1 退化为 1 是死配置；改为真实掩码 1/7/31）。
"""
import itertools
import numpy as np

SAMPLE_HZ = 50          # Hz
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
    """枚举工况参数组合，随机采样至 max_scenarios 条（seed=42 可复现）"""
    all_combos = list(itertools.product(
        LEAK_COMPONENTS, LEAK_KS, OPERATIONS, INIT_PRESSURES, PORT_CONFIGS, NOISE_SIGMAS))
    rng = np.random.default_rng(42)
    rng.shuffle(all_combos)
    return all_combos[:max_scenarios]
