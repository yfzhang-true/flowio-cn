"""ml_evaluate.py — Stage 4: 混淆矩阵 / 每类指标 / 模型大小（ML-PLAN Task 4）

验收: normal R≥0.95, leak_major R≥0.90, 整体 acc≥0.90, 模型 ≤50KB
（计划稿此处有一处多余右括号语法错误，已修）
"""
import numpy as np
from pathlib import Path
import tensorflow as tf

CLASS_NAMES = ["normal", "leak_minor", "leak_major"]
FEATURES_FILE = Path(r"E:\FLOWIO\firmware\twin\dataset\features.npz")
MODEL_FILE = Path(r"E:\FLOWIO\firmware\twin\model\leak_model_int8.tflite")


def main():
    data = np.load(FEATURES_FILE)
    X_test, y_test = data["X_test"], data["y_test"]

    interpreter = tf.lite.Interpreter(model_path=str(MODEL_FILE))
    interpreter.allocate_tensors()
    input_detail = interpreter.get_input_details()[0]
    output_detail = interpreter.get_output_details()[0]

    scale = input_detail["quantization"][0] if input_detail["quantization"] else 1.0
    zero = input_detail["quantization"][1] if input_detail["quantization"] else 0

    predictions = []
    for x in X_test:
        xq = np.clip(np.round(x / scale + zero), -128, 127).astype(np.int8)
        interpreter.set_tensor(input_detail["index"], xq.reshape(1, -1))
        interpreter.invoke()
        output = interpreter.get_tensor(output_detail["index"])
        predictions.append(np.argmax(output))
    predictions = np.array(predictions)

    cm = tf.math.confusion_matrix(y_test, predictions, num_classes=3).numpy()
    acc = np.trace(cm) / cm.sum()
    print("混淆矩阵:")
    print(f"{'':>12} " + " ".join(f"{c:>12}" for c in CLASS_NAMES))
    for i, row in enumerate(cm):
        print(f"{CLASS_NAMES[i]:>12} " + " ".join(f"{v:>12}" for v in row))

    ok = True
    for i, name in enumerate(CLASS_NAMES):
        tp = cm[i, i]
        fp = cm[:, i].sum() - tp
        fn = cm[i, :].sum() - tp
        precision = tp / (tp + fp) if tp + fp > 0 else 0
        recall = tp / (tp + fn) if tp + fn > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall > 0 else 0
        print(f"  {name:>11}: P={precision:.3f} R={recall:.3f} F1={f1:.3f}")

    thresholds = {"normal": 0.95, "leak_minor": 0.0, "leak_major": 0.90}
    for i, name in enumerate(CLASS_NAMES):
        tp, fn = cm[i, i], cm[i, :].sum() - cm[i, i]
        recall = tp / (tp + fn) if tp + fn > 0 else 0
        if recall < thresholds[name]:
            print(f"  ✗ {name} R={recall:.3f} < 验收线 {thresholds[name]}")
            ok = False

    model_size = MODEL_FILE.stat().st_size
    print(f"\n整体 acc={acc:.4f}（≥0.90）  模型 {model_size // 1024}KB（≤50KB）")
    if acc < 0.90 or model_size > 50 * 1024:
        ok = False
    print("✓ 全部验收通过" if ok else "✗ 未达验收线")


if __name__ == "__main__":
    main()
