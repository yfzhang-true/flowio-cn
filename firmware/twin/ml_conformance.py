"""ml_conformance.py — 生成 C 推理器一致性测试向量（C vs TFLite 数值对齐的证据）

输入: model/leak_model_int8.tflite + dataset/features.npz（测试窗）
输出: ml_conformance_vectors.h（N 窗 × 80 点 + TFLite 参考类别/概率）
用法: D:/MiniConda/python.exe ml_conformance.py
之后: build_twin.sh 编译 ml_conformance.c 并运行（断言类别全对齐 + 概率差 < 0.02）
"""
import numpy as np
from pathlib import Path
from tensorflow.lite.python.interpreter import Interpreter

TFLITE = Path(r"E:\FLOWIO\firmware\twin\model\leak_model_int8.tflite")
FEAT = Path(r"E:\FLOWIO\firmware\twin\dataset\features.npz")
OUT = Path(r"E:\FLOWIO\firmware\twin\ml_conformance_vectors.h")
N_PER_CLASS = 7


def main():
    interp = Interpreter(model_path=str(TFLITE))
    interp.allocate_tensors()
    ii, oo = interp.get_input_details()[0], interp.get_output_details()[0]
    s_i, zp_i = ii["quantization"]
    s_o, zp_o = oo["quantization"]

    data = np.load(FEAT)
    X_test, y_test = data["X_test"], data["y_test"]

    rows = []
    rng = np.random.default_rng(7)
    for cls in range(3):
        idxs = np.where(y_test == cls)[0]
        for k in rng.choice(idxs, N_PER_CLASS, replace=False):
            x = X_test[k].astype(np.float32)
            q_in = np.clip(np.round(x / s_i) + zp_i, -128, 127).astype(np.int8)
            interp.set_tensor(ii["index"], q_in.reshape(1, 80))
            interp.invoke()
            q_out = interp.get_tensor(oo["index"])[0]
            prob = (q_out.astype(np.float32) - zp_o) * s_o
            rows.append((x, int(np.argmax(prob)), float(np.max(prob))))

    lines = [
        "/* ml_conformance_vectors.h — 机器生成（ml_conformance.py），勿手改\n"
        f" * {len(rows)} 窗 × 80 点；参考类别/概率来自 TFLite Interpreter（重训后重新生成） */\n"
        "#define ML_CONF_N %d\n"
        "static const float ml_conf_x[ML_CONF_N][80] = {\n" % len(rows)
    ]
    for x, _, _ in rows:
        lines.append("  {" + ",".join(f"{v:.4f}" for v in x) + "},\n")
    lines.append("};\nstatic const int ml_conf_cls[ML_CONF_N] = {" +
                 ",".join(str(c) for _, c, _ in rows) + "};\n")
    lines.append("static const float ml_conf_p[ML_CONF_N] = {" +
                 ",".join(f"{p:.4f}" for _, _, p in rows) + "};\n")
    OUT.write_text("".join(lines), encoding="utf-8")
    print(f"✓ {OUT}（{len(rows)} 向量，类别分布 " +
          str([sum(1 for _, c, _ in rows if c == i) for i in range(3)]) + "）")


if __name__ == "__main__":
    main()
