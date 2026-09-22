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


def build_model(input_len=100, n_classes=3):
    model = tf.keras.Sequential([
        tf.keras.layers.Reshape((input_len, 1), input_shape=(input_len,)),
        tf.keras.layers.Conv1D(16, 3, activation="relu"),
        tf.keras.layers.Dropout(0.2),
        tf.keras.layers.Conv1D(16, 3, activation="relu"),
        tf.keras.layers.Dropout(0.2),
        tf.keras.layers.MaxPooling1D(2),
        tf.keras.layers.Flatten(),
        tf.keras.layers.Dense(32, activation="relu"),
        tf.keras.layers.Dropout(0.2),
        tf.keras.layers.Dense(n_classes, activation="softmax"),
    ])
    model.compile(optimizer="adam", loss="sparse_categorical_crossentropy", metrics=["accuracy"])
    return model


def main():
    data = np.load(FEATURES_FILE)
    X_train, y_train = data["X_train"], data["y_train"]
    X_test, y_test = data["X_test"], data["y_test"]

    model = build_model(X_train.shape[1])
    model.summary()

    early_stop = tf.keras.callbacks.EarlyStopping(patience=5, restore_best_weights=True)
    model.fit(X_train, y_train, validation_split=0.15,
              epochs=30, batch_size=32, callbacks=[early_stop], verbose=1)

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
