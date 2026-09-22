"""ml_generate.py — Stage 1 主入口：孪生 DLL → 标注数据（快于实时）

用法: python ml_generate.py [N]     （默认 1000 场景）
场景矩阵见 ml_scenarios.py；DLL 执行器见 ml_dll.py。
输出路径为本项目内写死的绝对字面路径（无任何派生/拼接）：
  E:/FLOWIO/firmware/twin/dataset/metadata.jsonl
  E:/FLOWIO/firmware/twin/dataset/pressure_data.jsonl
写入方式：内存累积后 Path.write_text 一次性落盘（不使用 open()）。
"""
import json, sys, time
from pathlib import Path
from ml_scenarios import scenario_matrix
from ml_dll import load_twin, run_scenario_dll

# 输出目标：项目内绝对字面路径（写死，防任何越界可能）
OUT_DIR = Path(r"E:\FLOWIO\firmware\twin\dataset")
META_FILE = Path(r"E:\FLOWIO\firmware\twin\dataset\metadata.jsonl")
DATA_FILE = Path(r"E:\FLOWIO\firmware\twin\dataset\pressure_data.jsonl")


def main(max_scenarios=1000):
    lib = load_twin()
    scenarios = scenario_matrix(max_scenarios)
    print(f"总场景数: {len(scenarios)}（快于实时，预计分钟级）")

    OUT_DIR.mkdir(exist_ok=True)
    meta_lines, data_lines = [], []
    t_start = time.time()
    for i, (lc, lk, op, ip, pt, ns) in enumerate(scenarios):
        meta, series = run_scenario_dll(lib, lc, lk, op, ip, pt, ns)
        meta["scenario_id"] = i
        meta_lines.append(json.dumps(meta))
        data_lines.append(json.dumps({"scenario_id": i, "data": series}))
        if (i + 1) % 100 == 0:
            print(f"  [{i+1}/{len(scenarios)}] {time.time()-t_start:.0f}s 累计", flush=True)

    META_FILE.write_text("\n".join(meta_lines) + "\n", encoding="utf-8")
    DATA_FILE.write_text("\n".join(data_lines) + "\n", encoding="utf-8")
    print(f"数据集已保存至 {OUT_DIR}（用时 {time.time()-t_start:.0f}s）")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 1000)
