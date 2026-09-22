"""ml_export_ei.py — Stage 5: Edge Impulse 上传格式导出（ML-PLAN Task 5，路径 A 辅助）

输出: dataset/edgeimpulse/{train,test}/{normal,leakminor,leakmajor}/window_NNNN.csv
每类每 split 最多 50 条（Edge Impulse 免费档单类上限）。
手动步骤: edgeimpulse.com → 新建项目 → Data acquisition → Upload CSV → 训练 1D CNN → 导出 Arduino 库
"""
import numpy as np
from pathlib import Path

CLASS_NAMES = ["normal", "leakminor", "leakmajor"]
FEATURES_FILE = Path(r"E:\FLOWIO\firmware\twin\dataset\features.npz")
EI_DIR = Path(r"E:\FLOWIO\firmware\twin\dataset\edgeimpulse")


def main():
    data = np.load(FEATURES_FILE)
    for split, X, y in [("train", data["X_train"], data["y_train"]),
                        ("test",  data["X_test"],  data["y_test"])]:
        for ci, cname in enumerate(CLASS_NAMES):
            class_dir = EI_DIR / split / cname
            class_dir.mkdir(parents=True, exist_ok=True)
            mask = y == ci
            for j, x in enumerate(X[mask][:50]):     # 每类 ≤50 条（免费档限制）
                csv_line = ",".join(f"{v:.3f}" for v in x)
                (class_dir / f"window_{j:04d}.csv").write_text(csv_line + "\n", encoding="utf-8")
        print(f"  {split}: {np.bincount(y, minlength=3)} → 每类最多 50 条已导出")

    print(f"已导出至 {EI_DIR}")
    print("→ edgeimpulse.com → 新建项目 → Data acquisition → Upload data（CSV）")


if __name__ == "__main__":
    main()
