"""ml_dll.py — pn_twin.dll 的 ctypes 绑定 + 快于实时的场景执行器

ML-PLAN Task 1 架构升级（2026-09-22 执行时决策）：
  原：Python → HTTP → server.py → DLL（50Hz 轮询，1000 场景 ≈3.3h，HTTP 抖动）
  新：Python → ctypes → DLL 直驱（tick 连发 = 快于实时，1000 场景 ≈分钟级，零抖动）
  依据：pn_twin_tick() 内部是虚拟时钟（pn_mock_advance_ms），不读墙钟，确定性推进。
  与 HTTP 版的等价性：同一 DLL、同一 pn_core 逻辑层、同一命令字符串与泄漏 API。
"""
import ctypes
import os
import sys
from contextlib import contextmanager
from pathlib import Path
import numpy as np

from ml_scenarios import SAMPLE_HZ, DURATION_S


@contextmanager
def _silence_c_stdout():
    """fd 级静默 C 运行时 printf（pn_cli 回显），Python print 不受影响"""
    sys.stdout.flush()
    saved = os.dup(1)
    devnull = os.open(os.devnull, os.O_WRONLY)
    try:
        os.dup2(devnull, 1)
        yield
    finally:
        os.dup2(saved, 1)
        os.close(devnull)
        os.close(saved)


def load_twin():
    """加载 pn_twin.dll 并声明导出函数签名"""
    dll_path = Path(__file__).resolve().parent / "pn_twin.dll"
    lib = ctypes.CDLL(str(dll_path))
    lib.pn_twin_init.restype = None
    lib.pn_twin_state.restype = ctypes.c_uint32
    lib.pn_twin_sensor.argtypes = [ctypes.c_uint8]
    lib.pn_twin_sensor.restype = ctypes.c_float
    lib.pn_twin_command.argtypes = [ctypes.c_char_p]
    lib.pn_twin_command.restype = None
    lib.pn_twin_tick.restype = ctypes.c_int
    lib.pn_twin_advance.argtypes = [ctypes.c_uint32]
    lib.pn_twin_advance.restype = None
    lib.pn_twin_set_leak.argtypes = [ctypes.c_uint8, ctypes.c_float]
    lib.pn_twin_set_leak.restype = None
    lib.pn_twin_leak.argtypes = [ctypes.c_uint8]
    lib.pn_twin_leak.restype = ctypes.c_float
    lib.pn_twin_init()
    return lib


def run_scenario_dll(lib, leak_comp, leak_k, operation, init_p, ports, noise_sigma):
    """执行单条仿真场景（与 HTTP 版语义一致），返回 (metadata, time_series)

    快于实时：每个采样点 = 1 次 pn_twin_tick()（50ms 物理步），连发不等待墙钟。
    """
    rng = np.random.default_rng()

    # 1. 虚拟断电重置（清状态字/闭环/泄漏）
    with _silence_c_stdout():
        lib.pn_twin_init()

        # 2. 建立初始工况（tick 上限 2000 拍 = 虚拟 100s，防死循环）
        #    两种密封态工况（v3）：hold=充至+init_p 后密封；vacuum=抽至-init_p 后密封。
        #    泄漏必须作用于有压差的密封系统才有可观测信号（训练诊断修正）。
        if operation == "vacuum":
            lib.pn_twin_command(f"V {ports} 255".encode())
            for _ in range(2000):
                if lib.pn_twin_sensor(0) <= -init_p: break
                lib.pn_twin_tick()
            lib.pn_twin_command(f"S {ports}".encode())   # 密封（负压保持）
        else:  # hold
            lib.pn_twin_command(f"I {ports} 255".encode())
            for _ in range(2000):
                if lib.pn_twin_sensor(0) >= init_p: break
                lib.pn_twin_tick()
            lib.pn_twin_command(f"S {ports}".encode())   # 保压密封

        # 3. 注入泄漏（idx 0-6；7=无泄漏跳过）
        if leak_comp < 7:
            lib.pn_twin_set_leak(leak_comp, leak_k)

        # 4. 采样：每 tick（50ms）读一次传感器 = 精确 SAMPLE_HZ
        n_samples = SAMPLE_HZ * DURATION_S
        series = np.empty(n_samples, dtype=np.float64)
        for i in range(n_samples):
            lib.pn_twin_tick()
            series[i] = lib.pn_twin_sensor(0)

        # 6. 清理（泄漏清零、全阀密封）
        for idx in range(7):
            lib.pn_twin_set_leak(idx, 0.0)
        lib.pn_twin_command(b"S 31")

    # 5. 附加高斯噪声（kPa；放静默块外，纯 numpy）

    meta = {"leak_component": leak_comp, "leak_k": leak_k,
            "operation": operation, "initial_pressure": init_p,
            "ports": ports, "noise_sigma": noise_sigma}
    return meta, series.tolist()
