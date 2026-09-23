"""ml_features.py — Stage 2: 滑窗切分 → 训练/测试集（ML-PLAN Task 2）

输入: dataset/metadata.jsonl + pressure_data.jsonl（ml_generate.py 产出）
输出: dataset/features.npz（X_train/y_train/X_test/y_test，按场景分组划分防泄漏）
窗口 2s×50Hz=100 点，步长 0.5s=25 点；标签: 0=normal 1=leak_minor(k≤0.1) 2=leak_major
读写全部用 read_text/np.savez（不经 open()）。
"""
import json
import numpy as np
from pathlib import Path
from sklearn.model_selection import GroupShuffleSplit
from ml_scenarios import SAMPLE_HZ   # 20Hz：1 点/tick(50ms)，单一事实来源

OUT_DIR = Path(r"E:\FLOWIO\firmware\twin\dataset")
META_FILE = Path(r"E:\FLOWIO\firmware\twin\dataset\metadata.jsonl")
DATA_FILE = Path(r"E:\FLOWIO\firmware\twin\dataset\pressure_data.jsonl")
FEATURES_FILE = Path(r"E:\FLOWIO\firmware\twin\dataset\features.npz")

WINDOW_S = 4.0      # 窗口 4 秒（v4：H 诊断保压端口连通容积变大，泄漏压降率 ~减半，
                    #       2s 窗口信噪比不足训练诊断；4s 窗口趋势估计误差按 T^1.5 收敛）
STEP_S = 0.5        # 步长 0.5 秒
SAMPLE_HZ_LOCAL = SAMPLE_HZ  # 兼容引用


def label_for(meta, series):
    """v5 物理可观测标签（宪法第 12 条）：
    0 = 无泄漏（或低于检测下限）
    1 = 可测轻度泄漏（超额衰减 Δ∈[0.25, 1.2) kPa/s；0.15→0.25 加宽死区压训练方差）
    2 = 重度泄漏（Δ ≥ 1.2 kPa/s）
    Δ = |窗口线性斜率| − |窗口均压|×1%（基线密封微漏，PHYSICS-SPEC）
    依据：k 定义的类别跨工况物理重叠（k=0.5@20kPa/31口 Δ≈0.2 与 normal 不可分；
    k=0.05@低压 Δ≈0.02 天然低于噪声底）——检测器只能对可观测物分级。"""
    if meta["leak_component"] >= 7:
        return 0
    arr = np.asarray(series, dtype=np.float64)
    t = np.arange(len(arr)) / SAMPLE_HZ                  # 采样间距 = 1/SAMPLE_HZ 秒
    slope = abs(np.polyfit(t, arr, 1)[0])              # kPa/s
    base = abs(arr.mean()) * 0.01                      # 基线密封微漏
    excess = slope - base
    if excess < 0.25:
        return 0
    return 1 if excess < 1.2 else 2


def main():
    metas = [json.loads(l) for l in META_FILE.read_text(encoding="utf-8").splitlines()]
    datas = [json.loads(l) for l in DATA_FILE.read_text(encoding="utf-8").splitlines()]
    assert len(metas) == len(datas) and len(metas) > 0, "数据集为空，先跑 ml_generate.py"

    window_n = int(WINDOW_S * SAMPLE_HZ)
    step_n = int(STEP_S * SAMPLE_HZ)

    X, y, groups = [], [], []   # groups=scenario_id：同场景窗口不跨 train/test（防泄漏）
    for meta, data in zip(metas, datas):
        series = data["data"]
        label = label_for(meta, series)
        for start in range(0, len(series) - window_n + 1, step_n):
            X.append(series[start:start + window_n])
            y.append(label)
            groups.append(meta["scenario_id"])

    X = np.array(X, dtype=np.float32)
    y = np.array(y, dtype=np.int32)
    groups = np.array(groups)
    print(f"窗口总数: {len(X)}, 形状: {X.shape}, 类别分布: {np.bincount(y)}")

    gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
    train_idx, test_idx = next(gss.split(X, y, groups))
    print(f"Train: {len(train_idx)}, Test: {len(test_idx)}（按场景分组 80/20）")

    np.savez_compressed(FEATURES_FILE,
                        X_train=X[train_idx], y_train=y[train_idx],
                        X_test=X[test_idx],  y_test=y[test_idx])
    print(f"已保存至 {FEATURES_FILE}")


if __name__ == "__main__":
    main()
