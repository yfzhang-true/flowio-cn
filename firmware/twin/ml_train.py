"""ml_train.py — Stage 3B: 本地 Keras 1D CNN → TFLite int8（ML-PLAN Task 3）

输入: dataset/features.npz（ml_features.py 产出）
输出: model/leak_model_int8.tflite（全 int8 量化，目标 ≤50KB）
验收: Test accuracy ≥ 0.90，模型 ≤ 50KB
"""
import numpy as np
from pathlib import Path
import tensorflow as tf

FEATURES_FILE = Path(r"E:\FLOWIO\firmware\twin\dataset\features.npz")
MODEL_FILE = Path(r"E:\FLOWIO\firmware\twin\model\leak_model_int8.tflite")


def build_model(input_len=200, n_classes=3):
    """v5.1：池化+Flatten（GAP 丢失时序斜率信息致 50% 准确率的教训），
    两级 ×4 池化控住 200 点窗口的展开尺寸。目标 int8 ≤50KB。"""
    model = tf.keras.Sequential([
        tf.keras.layers.Reshape((input_len, 1), input_shape=(input_len,)),
        tf.keras.layers.Conv1D(24, 7, activation="relu"),
        tf.keras.layers.MaxPooling1D(4),
        tf.keras.layers.Conv1D(24, 5, activation="relu"),
        tf.keras.layers.MaxPooling1D(4),
        tf.keras.layers.Conv1D(32, 3, activation="relu"),
        tf.keras.layers.Flatten(),
        tf.keras.layers.Dense(24, activation="relu"),
        tf.keras.layers.Dropout(0.3),
        tf.keras.layers.Dense(n_classes, activation="softmax"),
    ])
    model.compile(optimizer="adam", loss="sparse_categorical_crossentropy", metrics=["accuracy"])
    return model


def main():
    import random
    random.seed(42)
    np.random.seed(42)
    tf.random.set_seed(42)   # 可复现训练（normal 召回曾在 92.7↔99.9% 间摆动——训练方差）
    data = np.load(FEATURES_FILE)
    X_train, y_train = data["X_train"], data["y_train"]
    X_test, y_test = data["X_test"], data["y_test"]

    model = build_model(X_train.shape[1])
    model.summary()

    early_stop = tf.keras.callbacks.EarlyStopping(patience=8, restore_best_weights=True)
    model.fit(X_train, y_train, validation_split=0.15,
              epochs=60, batch_size=32, callbacks=[early_stop], verbose=1)

    test_loss, test_acc = model.evaluate(X_test, y_test, verbose=0)
    print(f"\nTest accuracy: {test_acc:.4f}（验收线 ≥0.90）")

    # TFLite 全 int8 量化（代表集 = 训练窗前 200 条）
    def representative_dataset():
        for i in range(min(200, len(X_train))):
            yield [X_train[i:i + 1].astype(np.float32)]

    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    converter.representative_dataset = representative_dataset
    converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
    converter.inference_input_type = tf.int8
    converter.inference_output_type = tf.int8
    tflite_model = converter.convert()

    MODEL_FILE.parent.mkdir(exist_ok=True)
    MODEL_FILE.write_bytes(tflite_model)
    print(f"TFLite int8 模型: {MODEL_FILE} ({len(tflite_model) // 1024}KB，验收线 ≤50KB)")
    if test_acc < 0.90 or len(tflite_model) > 50 * 1024:
        raise SystemExit("✗ 未达验收线")


if __name__ == "__main__":
    main()
