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

OUT_DIR = Path(r"E:\FLOWIO\firmware\twin\dataset")
META_FILE = Path(r"E:\FLOWIO\firmware\twin\dataset\metadata.jsonl")
DATA_FILE = Path(r"E:\FLOWIO\firmware\twin\dataset\pressure_data.jsonl")
FEATURES_FILE = Path(r"E:\FLOWIO\firmware\twin\dataset\features.npz")

WINDOW_S = 2.0      # 窗口 2 秒
STEP_S = 0.5        # 步长 0.5 秒
SAMPLE_HZ = 50


def label_for(meta):
    if meta["leak_component"] >= 7: return 0   # normal
    if meta["leak_k"] <= 0.1: return 1         # leak_minor
    return 2                                    # leak_major


def main():
    metas = [json.loads(l) for l in META_FILE.read_text(encoding="utf-8").splitlines()]
    datas = [json.loads(l) for l in DATA_FILE.read_text(encoding="utf-8").splitlines()]
    assert len(metas) == len(datas) and len(metas) > 0, "数据集为空，先跑 ml_generate.py"

    window_n = int(WINDOW_S * SAMPLE_HZ)
    step_n = int(STEP_S * SAMPLE_HZ)

    X, y, groups = [], [], []   # groups=scenario_id：同场景窗口不跨 train/test（防泄漏）
    for meta, data in zip(metas, datas):
        label = label_for(meta)
        series = data["data"]
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
