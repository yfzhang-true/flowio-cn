"""ml_export_c.py — Stage 5: int8 tflite → C 权重数组（固件部署，零依赖推理器）

输入: model/leak_model_int8.tflite
输出: ../components/pn_ml/src/leak_model_data.c（权重 + 量化参数，机器生成勿手改）

模型拓扑（ml_train.py build_model，TFLite 转换后实测 2026-09-23）：
  input[80] int8 → CONV_2D(24,k7,relu) → MAXPOOL4 → CONV_2D(24,k5,relu) → MAXPOOL4
  → CONV_2D(32,k3,relu) → Flatten → FC(24,relu) → FC(3) → softmax
Conv1D 被 TFLite 编译为 [out,1,k,in] 的 CONV_2D（H=1），权重按该布局原样导出。
"""
import numpy as np
from pathlib import Path
from tensorflow.lite.python.interpreter import Interpreter
from tensorflow.lite.python import schema_py_generated as sch

TFLITE = Path(r"E:\FLOWIO\firmware\twin\model\leak_model_int8.tflite")
OUT_C = Path(r"E:\FLOWIO\firmware\components\pn_ml\src\leak_model_data.c")

# 拓扑锚点（tensor 索引，由 _get_ops_details 实测；模型结构变更时须重探）
T = {
    "in": 0, "out": 47,
    "conv1_w": 21, "conv1_b": 20, "conv1_out": 27,
    "pool1_out": 30,
    "conv2_w": 19, "conv2_b": 18, "conv2_out": 33,
    "pool2_out": 36,
    "conv3_w": 17, "conv3_b": 16, "conv3_out": 39,
    "fc1_w": 15, "fc1_b": 14, "fc1_out": 45,
    "fc2_w": 13, "fc2_b": 12, "fc2_out": 46,
}


def load_flatbuffer():
    """schema 直解：常量权重的 quantization 在 Interpreter details 里恒为 (0,0)（2026-09-23 踩坑），
    只能从 flatbuffer 的 Tensor.Quantization() 表拿。"""
    buf = TFLITE.read_bytes()
    m = sch.Model.GetRootAsModel(buf, 0)
    return m, m.Subgraphs(0)


def fb_tensor(sub, model, idx):
    """返回 (ndarray 数据, scales[ndarray], zps[ndarray])。
    本模型全部权重 per-channel 量化（quant_dim=0=输出通道，2026-09-23 探测）；
    常量权重的 quantization 在 Interpreter details 里恒为 (0,0)，只能 flatbuffer 直解。"""
    t = sub.Tensors(idx)
    q = t.Quantization()
    assert q is not None and q.ScaleLength() >= 1, f"t{idx} 无量化表"
    data = np.frombuffer(model.Buffers(t.Buffer()).DataAsNumpy(), dtype=np.int8)
    scales = np.array([q.Scale(i) for i in range(q.ScaleLength())], dtype=np.float64)
    zps = np.array([q.ZeroPoint(i) for i in range(q.ZeroPointLength())], dtype=np.int64)
    return data, scales, zps


def main():
    interp = Interpreter(model_path=str(TFLITE))
    interp.allocate_tensors()
    td = interp.get_tensor_details()
    model, sub = load_flatbuffer()

    def q(idx):   # 激活张量：interpreter details 有量化
        s, zp = td[idx]["quantization"]
        assert s not in (0.0, 1.0) or zp != 0, f"t{idx} 未量化"
        return s, zp

    def w(idx):   # 常量权重：只能 flatbuffer 直解（details 对常量恒 (0,0)）；per-channel
        a, scales, zps = fb_tensor(sub, model, idx)
        assert a.size > 0, f"t{idx} 无常量数据"
        assert np.all(zps == 0), f"t{idx} 权重 zp 非全 0，推理器按对称量化实现——需改 leak_infer.c"
        shape = tuple(int(d) for d in td[idx]["shape"])
        assert len(scales) == shape[0], f"t{idx} per-channel scale 数 {len(scales)} ≠ 输出通道 {shape[0]}"
        return a.reshape(shape), scales

    shapes = {k: list(td[v]["shape"]) for k, v in T.items()}
    print("拓扑校验：", {k: s for k, s in shapes.items() if k.endswith(("_w", "_b", "in", "out"))})

    conv1_w, sw1 = w(T["conv1_w"])
    conv2_w, sw2 = w(T["conv2_w"])
    conv3_w, sw3 = w(T["conv3_w"])
    fc1_w, swf1 = w(T["fc1_w"])
    fc2_w, swf2 = w(T["fc2_w"])
    conv1_b = fb_tensor(sub, model, T["conv1_b"])[0].view(np.int32)
    conv2_b = fb_tensor(sub, model, T["conv2_b"])[0].view(np.int32)
    conv3_b = fb_tensor(sub, model, T["conv3_b"])[0].view(np.int32)
    fc1_b = fb_tensor(sub, model, T["fc1_b"])[0].view(np.int32)
    fc2_b = fb_tensor(sub, model, T["fc2_b"])[0].view(np.int32)
    # 断言与 Keras 结构一致（防 ml_train 结构变更后锚点漂移）
    assert conv1_w.shape == (24, 1, 7, 1), conv1_w.shape
    assert conv2_w.shape == (24, 1, 5, 24), conv2_w.shape
    assert conv3_w.shape == (32, 1, 3, 24), conv3_w.shape
    fc1_in = fc1_w.shape[1]
    assert fc2_w.shape == (3, 24), fc2_w.shape
    assert min(sw1.min(), sw2.min(), sw3.min(), swf1.min(), swf2.min()) > 0, "权重 scale 必须 >0（曾因 details 恒 0 踩坑）"

    si, zi = q(T["in"])
    s_o = {k: q(T[k]) for k in ("conv1_out", "conv2_out", "conv3_out", "fc1_out", "fc2_out", "out")}

    def arr(name, a, dtype="int8_t"):
        flat = np.asarray(a).astype(np.int64).ravel()
        body = ",".join(str(x) for x in flat)
        return f"const {dtype} {name}[{len(flat)}] = {{{body}}};\n"

    lines = [
        "/* leak_model_data.c — 机器生成（ml_export_c.py），勿手改\n"
        f" * 源: twin/model/leak_model_int8.tflite（重训后重跑导出）\n"
        f" * 拓扑: in[80]→conv(24,7)→pool4→conv(24,5)→pool4→conv(32,3)→fc({fc1_in})→fc(3)→softmax */\n"
        '#include "pn_ml/leak_model_data.h"\n\n',
        arr("w_conv1", conv1_w), arr("b_conv1_i32", conv1_b, "int32_t"),
        arr("w_conv2", conv2_w), arr("b_conv2_i32", conv2_b, "int32_t"),
        arr("w_conv3", conv3_w), arr("b_conv3_i32", conv3_b, "int32_t"),
        arr("w_fc1", fc1_w), arr("b_fc1_i32", fc1_b, "int32_t"),
        arr("w_fc2", fc2_w), arr("b_fc2_i32", fc2_b, "int32_t"),
    ]
    qs = (f"const pn_ml_quant_t pn_ml_q_in   = {{ {si!r}f, {zi} }};\n"
          f"const pn_ml_quant_t pn_ml_q_conv1 = {{ {s_o['conv1_out'][0]!r}f, {s_o['conv1_out'][1]} }};\n"
          f"const pn_ml_quant_t pn_ml_q_conv2 = {{ {s_o['conv2_out'][0]!r}f, {s_o['conv2_out'][1]} }};\n"
          f"const pn_ml_quant_t pn_ml_q_conv3 = {{ {s_o['conv3_out'][0]!r}f, {s_o['conv3_out'][1]} }};\n"
          f"const pn_ml_quant_t pn_ml_q_fc1   = {{ {s_o['fc1_out'][0]!r}f, {s_o['fc1_out'][1]} }};\n"
          f"const pn_ml_quant_t pn_ml_q_fc2   = {{ {s_o['fc2_out'][0]!r}f, {s_o['fc2_out'][1]} }};\n"
          f"const pn_ml_quant_t pn_ml_q_out  = {{ {s_o['out'][0]!r}f, {s_o['out'][1]} }};\n")
    def farr(name, vals):
        body = ",".join(f"{float(v)!r}f" for v in np.asarray(vals, dtype=np.float64).ravel())
        return f"const float {name}[{len(np.asarray(vals).ravel())}] = {{{body}}};\n"

    sw = (farr("pn_ml_s_w_conv1", sw1) + farr("pn_ml_s_w_conv2", sw2) +
          farr("pn_ml_s_w_conv3", sw3) + farr("pn_ml_s_w_fc1", swf1) +
          farr("pn_ml_s_w_fc2", swf2))
    header = (
        f"const int PN_ML_FC1_IN = {fc1_in};\n"
        f"const int PN_ML_FLAT = {fc1_in};\n")
    OUT_C.parent.mkdir(parents=True, exist_ok=True)
    OUT_C.write_text("".join(lines) + "\n" + qs + "\n" + sw + "\n" + header, encoding="utf-8")
    total = sum(np.asarray(x).size for x in (conv1_w, conv1_b, conv2_w, conv2_b, conv3_w, conv3_b, fc1_w, fc1_b, fc2_w, fc2_b))
    print(f"✓ {OUT_C}（权重+偏置共 {total} 参数）")
    print(f"  输入 scale={si:.6g} zp={zi}；FC1 in={fc1_in}")


if __name__ == "__main__":
    main()
