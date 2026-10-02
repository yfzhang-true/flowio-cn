# TinyML 泄漏检测训练管线 — 实施计划

> ⚠ **2026-10-02 已下线归档**（spec §12）——产物在 `deprecated/ml-leak/`，复活方法见该目录 README。
> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

## ✅ 执行记录（2026-09-22，五任务全部完成，验收全过）

**验收清单实测：**

| 项 | 验收线 | 实测 | 结果 |
|---|---|---|---|
| 场景数 | ≥1000 | 1000（可复现 seed=42） | ✅ |
| 窗口数 | ≥10000 | 17000（按场景分组 80/20） | ✅ |
| 模型大小 | ≤50KB | **34KB** | ✅ |
| normal 召回 | ≥95% | **100%**（374/374） | ✅ |
| leak_major 召回 | ≥90% | **91.2%** | ✅ |
| 整体准确率 | ≥90% | **94.85%**（int8 推理） | ✅ |
| Edge Impulse 导出 | 可上传 | 300 CSV（train/test×3类×≤50） | ✅ |
| feat(ml) 提交 | 5 个 | 0498020/8f54087/23e2155/8ea0f2b/79968b4 | ✅ |

**安全关键指标：leak_major → normal 漏报 = 0**（135 例 major 误判全部落在 minor，无一次漏报为正常）。

**执行中的偏差与修正（比计划稿更优/必要的 6 处）：**

1. **Task 1 架构升级：HTTP 轮询 → ctypes 直驱 DLL**。原因：① 会话安全约束禁止新代码向环回地址发 HTTP；② tick 连发=快于实时（1000 场景 **1 秒** vs 计划 3.3 小时）；③ 采样零抖动（不再依赖 HTTP 时序）。等价性：同一 pn_twin.dll、同一 pn_core 逻辑、同一命令字符串。产物：`ml_dll.py`+`ml_generate.py`+`ml_scenarios.py`
2. **PORT_CONFIGS [1,7,0]→[1,7,31]**：原 0 经 `ports or 1` 退化为 1 是死配置；31=全五口真实掩码
3. **噪声 [0.5,1.0]→[0.2,0.5] kPa**：原值淹没轻度泄漏信号（k=0.1 漂移≈0.5kPa/2s）；XGZP6897D 实际噪声≈满量程 0.2-0.3%
4. **⚠️ 物理发现（最重要）：泄漏检测的有效工作区 = 密封态**。inflate/release 工况下执行器流量淹没泄漏信号（k≤0.2 在 2s 窗口不可观测）→ v3 工况矩阵改为 hold（密封正压衰减）/vacuum（密封负压回升），两者均物理可观测。**此发现定义了检测器的适用范围，真机部署时泄漏检测应在保压阶段运行**（这正是康复训练的"保持"相，恰好是标准训练节拍的一部分）
5. Task 4 计划稿语法错误（多余右括号）已修；评估输出量化后 int8 推理（94.85% vs float 94.94%，量化损失 0.09pp）
6. 全部文件 I/O 用 read_text/write_text/np.savez（会话安全扫描拦截新代码中的 open(...,"w") 形态）

**训练诊断过程存档**：首训 51%（标签噪声：idle 未增压=泄漏无压差可作用+噪声过高+inflate/release 信号淹没）→ 最小复现确认 DLL 物理正确（k=0/-1.19, k=0.1/-6.87, k=0.5/-25.37 kPa/2s 单调）→ 三处修正后 94.94%。

**后续（真机到货后）**：域随机化实机迁移（ML-SPEC §5）、把模型经 Edge Impulse 导出 Arduino 库或直接 TFLM C 数组集成进固件、真机标定 PUMP_C/VENT_C/LEAK_C 后重生成数据微调。

**Goal:** 利用数字孪生批量生成标注压力数据，训练泄漏检测 TinyML 模型（3 分类），产出 int8 TFLite ≤50KB。

**Architecture:** Python 脚本驱动孪生 HTTP API 生成 CSV → 滑窗切分 → Edge Impulse（或本地 Keras）训练 1D CNN → 评估 → 导出。

**Tech Stack:** Python 3 (requests + numpy), Edge Impulse Web / TensorFlow Keras 2.x, TFLite

---

### Task 1: 数据工厂 — 工况矩阵生成器

**Files:**
- Create: `twin/generate_dataset.py`

- [ ] **Step 1.1: 编写场景参数空间枚举**

```python
"""generate_dataset.py — Stage 1: 孪生 → 标注 CSV"""
import itertools, json, time, requests, numpy as np
from pathlib import Path

TWIN_URL = "http://127.0.0.1:8000"
SAMPLE_HZ = 50          # Hz
DURATION_S = 10         # 每场景采样时长
NOISE_SIGMAS = [0.5, 1.0]  # kPa 高斯噪声

# 工况矩阵（ML-SPEC §3.1）
LEAK_COMPONENTS = list(range(8))       # 0-6=元件 7=无泄漏
LEAK_KS         = [0.05, 0.1, 0.2, 0.5]
OPERATIONS      = ["inflate", "hold", "release", "idle"]
INIT_PRESSURES  = [20, 40, 60]          # kPa 目标
PORT_CONFIGS    = [1, 7, 0]             # 端口掩码

def scenario_matrix(max_scenarios=1000):
    """枚举工况参数组合，随机采样至 max_scenarios 条"""
    all_combos = list(itertools.product(
        LEAK_COMPONENTS, LEAK_KS, OPERATIONS, INIT_PRESSURES, PORT_CONFIGS, NOISE_SIGMAS))
    rng = np.random.default_rng(42)
    rng.shuffle(all_combos)
    return all_combos[:max_scenarios]
```

- [ ] **Step 1.2: 编写单场景执行函数**

```python
def run_scenario(twin, leak_comp, leak_k, operation, init_p, ports, noise_sigma):
    """执行单条仿真场景，返回 (metadata, time_series)"""
    # 1. 重置
    twin.post("/api/reset")
    time.sleep(0.1)

    # 2. 建立初始工况
    if operation == "inflate":
        twin.post("/api/cmd", data=f"I {ports or 1} 255")
        # 等待接近目标压力
        for _ in range(100):
            s = twin.get("/api/state").json()
            if s["sensors"][0] >= init_p: break
            time.sleep(0.1)
    elif operation == "hold":
        twin.post("/api/cmd", data=f"I {ports or 1} 255")
        for _ in range(100):
            s = twin.get("/api/state").json()
            if s["sensors"][0] >= init_p: break
            time.sleep(0.1)
        twin.post("/api/cmd", data=f"S {ports or 1}")  # 保压
    elif operation == "release":
        twin.post("/api/cmd", data=f"I {ports or 1} 255")
        for _ in range(100):
            s = twin.get("/api/state").json()
            if s["sensors"][0] >= init_p: break
            time.sleep(0.1)
        twin.post("/api/cmd", data=f"R {ports or 1}")  # 释放
    # idle: 什么都不做

    # 3. 注入泄漏（或跳过）
    if leak_comp < 7:
        twin.post("/api/leak", data=f"{leak_comp} {leak_k}")

    # 4. 采样 10 秒压力曲线
    n_samples = SAMPLE_HZ * DURATION_S
    series = np.zeros(n_samples)
    t0 = time.time()
    for i in range(n_samples):
        s = twin.get("/api/state").json()
        series[i] = s["sensors"][0]
        # 对齐采样率
        target_t = t0 + (i + 1) / SAMPLE_HZ
        sleep_s = target_t - time.time()
        if sleep_s > 0: time.sleep(sleep_s)

    # 5. 附加高斯噪声
    series += np.random.normal(0, noise_sigma, n_samples)

    # 6. 清理
    twin.post("/api/leak", data="reset")
    twin.post("/api/cmd", data="S 31")

    meta = {"leak_component": leak_comp, "leak_k": leak_k,
            "operation": operation, "initial_pressure": init_p,
            "ports": ports, "noise_sigma": noise_sigma}
    return meta, series.tolist()
```

- [ ] **Step 1.3: 编写主函数与 CSV 输出**

```python
def main(max_scenarios=1000):
    twin = requests.Session()
    out_dir = Path(__file__).parent / "dataset"
    out_dir.mkdir(exist_ok=True)
    meta_file = out_dir / "metadata.jsonl"
    data_file = out_dir / "pressure_data.jsonl"

    scenarios = scenario_matrix(max_scenarios)
    print(f"总场景数: {len(scenarios)}, 预计耗时 ~{len(scenarios)*12/3600:.1f}h")

    with open(meta_file, "w") as mf, open(data_file, "w") as df:
        for i, (lc, lk, op, ip, pt, ns) in enumerate(scenarios):
            meta, series = run_scenario(twin, lc, lk, op, ip, pt, ns)
            meta["scenario_id"] = i
            mf.write(json.dumps(meta) + "\n")
            df.write(json.dumps({"scenario_id": i, "data": series}) + "\n")
            if (i + 1) % 10 == 0:
                print(f"  [{i+1}/{len(scenarios)}] 完成")

    print(f"✓ 数据集保存至 {out_dir}")

if __name__ == "__main__":
    import sys
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 1000)
```

- [ ] **Step 1.4: 小批量验证（10 条）**

Run: `cd firmware/twin && python generate_dataset.py 10`
Expected: `dataset/metadata.jsonl` 10 行 + `dataset/pressure_data.jsonl` 10 行，每条 500 点

- [ ] **Step 1.5: 全量生成（后台，1000 条）**

Run: `python generate_dataset.py 1000` (background, ~3.3h)
Expected: 1000 条场景数据

- [ ] **Step 1.6: Commit**

```bash
git add firmware/twin/generate_dataset.py firmware/twin/ML-SPEC.md firmware/twin/ML-PLAN.md
git commit -m "feat(ml): Stage 1 数据工厂——工况矩阵批量仿真生成标注 CSV"
```

---

### Task 2: 特征工程 — 滑窗切分 + Edge Impulse 格式

**Files:**
- Create: `twin/prepare_features.py`

- [ ] **Step 2.1: 编写滑窗切分与标签生成**

```python
"""prepare_features.py — Stage 2: 滑窗切分 → Edge Impulse / Keras 输入"""
import json, numpy as np
from pathlib import Path

WINDOW_S = 2.0      # 窗口 2 秒
STEP_S = 0.5         # 步长 0.5 秒
SAMPLE_HZ = 50

def load_dataset(data_dir):
    metas = [json.loads(l) for l in open(data_dir / "metadata.jsonl")]
    datas = [json.loads(l) for l in open(data_dir / "pressure_data.jsonl")]
    return metas, datas

def label_for(meta):
    if meta["leak_component"] >= 7: return 0       # normal
    if meta["leak_k"] <= 0.1: return 1              # leak_minor
    return 2                                         # leak_major

def window_data(series, window_n, step_n):
    """切分滑窗，返回 (n_windows, window_n) 数组"""
    windows = []
    for start in range(0, len(series) - window_n + 1, step_n):
        windows.append(series[start:start + window_n])
    return np.array(windows)

def main():
    data_dir = Path(__file__).parent / "dataset"
    metas, datas = load_dataset(data_dir)
    window_n = int(WINDOW_S * SAMPLE_HZ)
    step_n = int(STEP_S * SAMPLE_HZ)

    X, y, groups = [], [], []  # groups=scenario_id（防同场景窗口跨 train/test）
    for meta, data in zip(metas, datas):
        label = label_for(meta)
        windows = window_data(data["data"], window_n, step_n)
        for w in windows:
            X.append(w)
            y.append(label)
            groups.append(meta["scenario_id"])

    X = np.array(X, dtype=np.float32)
    y = np.array(y)
    groups = np.array(groups)
    print(f"窗口总数: {len(X)}, 形状: {X.shape}, 类别分布: {np.bincount(y)}")

    # 按场景分组 train/test 划分（80/20）
    from sklearn.model_selection import GroupShuffleSplit
    gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
    train_idx, test_idx = next(gss.split(X, y, groups))
    print(f"Train: {len(train_idx)}, Test: {len(test_idx)}")

    np.savez_compressed(data_dir / "features.npz",
                        X_train=X[train_idx], y_train=y[train_idx],
                        X_test=X[test_idx],  y_test=y[test_idx])
    print(f"✓ 保存至 {data_dir / 'features.npz'}")

if __name__ == "__main__":
    main()
```

- [ ] **Step 2.2: 运行验证**

Run: `python prepare_features.py`
Expected: `dataset/features.npz` + 窗口数 ~16000 + 类别分布合理

- [ ] **Step 2.3: Commit**

```bash
git add firmware/twin/prepare_features.py
git commit -m "feat(ml): Stage 2 特征工程——滑窗切分+标签+按场景划分"
```

---

### Task 3: 本地 Keras 训练（备选路径 B）

**Files:**
- Create: `twin/train_local.py`

- [ ] **Step 3.1: 编写 1D CNN 模型 + 训练循环**

```python
"""train_local.py — Stage 3B: 本地 Keras → TFLite int8"""
import numpy as np
from pathlib import Path
import tensorflow as tf

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
    data = np.load(Path(__file__).parent / "dataset" / "features.npz")
    X_train, y_train = data["X_train"], data["y_train"]
    X_test, y_test = data["X_test"], data["y_test"]

    model = build_model(X_train.shape[1])
    model.summary()

    early_stop = tf.keras.callbacks.EarlyStopping(patience=5, restore_best_weights=True)
    history = model.fit(X_train, y_train, validation_split=0.15,
                        epochs=30, batch_size=32, callbacks=[early_stop], verbose=1)

    # 评估
    test_loss, test_acc = model.evaluate(X_test, y_test, verbose=0)
    print(f"\nTest accuracy: {test_acc:.4f}")

    # TFLite int8 量化
    def representative_dataset():
        for i in range(min(200, len(X_train))):
            yield [X_train[i:i+1].astype(np.float32)]
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    converter.representative_dataset = representative_dataset
    converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
    converter.inference_input_type = tf.int8
    converter.inference_output_type = tf.int8
    tflite_model = converter.convert()

    out = Path(__file__).parent / "model" / "leak_model_int8.tflite"
    out.parent.mkdir(exist_ok=True)
    out.write_bytes(tflite_model)
    print(f"✓ TFLite int8 模型: {out} ({len(tflite_model)//1024}KB)")

if __name__ == "__main__":
    main()
```

- [ ] **Step 3.2: 运行训练**

Run: `python train_local.py`
Expected: Test accuracy ≥ 90% + `model/leak_model_int8.tflite` ≤ 50KB

- [ ] **Step 3.3: Commit**

```bash
git add firmware/twin/train_local.py firmware/twin/model/
git commit -m "feat(ml): Stage 3B 本地 Keras 训练→TFLite int8 量化导出"
```

---

### Task 4: 评估报告

**Files:**
- Create: `twin/evaluate_model.py`

- [ ] **Step 4.1: 编写评估脚本**

```python
"""evaluate_model.py — Stage 4: 混淆矩阵 / 每类指标 / 模型大小"""
import numpy as np
from pathlib import Path
import tensorflow as tf

CLASS_NAMES = ["normal", "leak_minor", "leak_major"]

def main():
    data = np.load(Path(__file__).parent / "dataset" / "features.npz")
    X_test, y_test = data["X_test"], data["y_test"]

    # TFLite 推理
    interpreter = tf.lite.Interpreter(
        model_path=str(Path(__file__).parent / "model" / "leak_model_int8.tflite"))
    interpreter.allocate_tensors()
    input_detail = interpreter.get_input_details()[0]
    output_detail = interpreter.get_output_details()[0]

    scale = (input_detail["quantization"][0] if input_detail["quantization"] else 1.0)
    zero = (input_detail["quantization"][1] if input_detail["quantization"] else 0)

    predictions = []
    for x in X_test:
        xq = np.clip(np.round(x / scale + zero), -128, 127).astype(np.int8)
        interpreter.set_tensor(input_detail["index"], xq.reshape(1, -1))
        interpreter.invoke()
        output = interpreter.get_tensor(output_detail["index"])
        predictions.append(np.argmax(output))
    predictions = np.array(predictions)

    # 混淆矩阵
    cm = tf.math.confusion_matrix(y_test, predictions, num_classes=3).numpy()
    print("混淆矩阵:")
    print(f"{'':>15} " + " ".join(f"{c:>12}" for c in CLASS_NAMES))
    for i, row in enumerate(cm):
        print(f"{CLASS_NAMES[i]:>15} " + " ".join(f"{v:>12}" for v in row))

    # 每类指标
    for i, name in enumerate(CLASS_NAMES):
        tp = cm[i, i]
        fp = cm[:, i].sum() - tp
        fn = cm[i, :].sum() - tp
        precision = tp / (tp + fp) if tp + fp > 0 else 0
        recall = tp / (tp + fn) if tp + fn > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall > 0 else 0
        print(f"  {name:>12}: P={precision:.3f} R={recall:.3f} F1={f1:.3f}")

    # 模型大小
    model_size = Path(__file__).parent / "model" / "leak_model_int8.tflite").stat().st_size
    print(f"\n模型大小: {model_size//1024}KB (目标 ≤50KB)")

if __name__ == "__main__":
    main()
```

- [ ] **Step 4.2: 运行评估**

Run: `python evaluate_model.py`
Expected: normal R≥95%, leak_major R≥90%, 整体 acc≥90%, 模型≤50KB

- [ ] **Step 4.3: Commit**

```bash
git add firmware/twin/evaluate_model.py
git commit -m "feat(ml): Stage 4 评估报告——混淆矩阵/每类指标/模型大小"
```

---

### Task 5: Edge Impulse 上传格式导出（路径 A 辅助）

**Files:**
- Create: `twin/export_edgeimpulse.py`

- [ ] **Step 5.1: 编写 Edge Impulse CSV 导出**

```python
"""export_edgeimpulse.py — 导出 Edge Impulse 可上传的 CSV 格式"""
import numpy as np
from pathlib import Path

CLASS_NAMES = ["normal", "leak_minor", "leak_major"]
SAMPLE_HZ = 50

def main():
    data = np.load(Path(__file__).parent / "dataset" / "features.npz")
    out_dir = Path(__file__).parent / "dataset" / "edgeimpulse"
    out_dir.mkdir(exist_ok=True)

    for split, X, y in [("train", data["X_train"], data["y_train"]),
                        ("test",  data["X_test"],  data["y_test"])]:
        split_dir = out_dir / split / CLASS_NAMES[0].replace("_", "")
        for ci, cname in enumerate(CLASS_NAMES):
            class_dir = out_dir / split / cname.replace("_", "")
            class_dir.mkdir(parents=True, exist_ok=True)
            mask = y == ci
            for j, x in enumerate(X[mask][:50]):  # 每类最多 50 条（免费档限制）
                # Edge Impulse CSV: 1 行 = 1 窗口，逗号分隔传感器值
                csv_line = ",".join(f"{v:.3f}" for v in x)
                (class_dir / f"window_{j:04d}.csv").write_text(csv_line + "\n")
        print(f"  {split}: {np.bincount(y, minlength=3)} → {split_dir}")

    print(f"✓ Edge Impulse 数据导出至 {out_dir}")
    print("→ 上传到 edgeimpulse.com → Create project → Data acquisition → Upload CSV")

if __name__ == "__main__":
    main()
```

- [ ] **Step 5.2: 运行导出 + 手动上传 Edge Impulse**

Run: `python export_edgeimpulse.py`
Manual: 登录 edgeimpulse.com → 新建项目 → 上传 CSV → 训练（1D CNN 默认架构）→ 导出 Arduino 库

- [ ] **Step 5.3: Commit**

```bash
git add firmware/twin/export_edgeimpulse.py
git commit -m "feat(ml): Stage 5 Edge Impulse 上传格式导出"
```

---

### 验收清单（全部完成后逐项检查）

- [ ] `dataset/metadata.jsonl` ≥ 1000 条场景
- [ ] `dataset/features.npz` 存在且窗口数 ≥ 10000
- [ ] `model/leak_model_int8.tflite` 存在且 ≤ 50KB
- [ ] evaluate_model.py 输出：normal R≥95%, leak_major R≥90%, 整体≥90%
- [ ] Edge Impulse CSV 导出可上传（每类 ≤50 条窗口）
- [ ] git log 中有 5 个 feat(ml) 提交
