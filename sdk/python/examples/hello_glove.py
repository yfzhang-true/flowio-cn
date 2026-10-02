"""hello_glove.py — FlowIO 上位机最小示例（充→保→释→抽一个来回）。

用法::

    python hello_glove.py COM3            # 指定串口
    python hello_glove.py                 # 无参数时列出可用串口后退出

前置：固件已烧录并运行 0xA5 帧协议；未装 pyserial 时 pip install pyserial。
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # sdk/python 入包路径

from flowio_sdk import FlowIO, encode  # noqa: E402


def main() -> int:
    if len(sys.argv) < 2:
        from flowio_sdk import SerialTransport

        ports = SerialTransport.list_ports()
        print("用法: python hello_glove.py <COM口>   如: python hello_glove.py COM3")
        print("可用串口:", ports if ports else "(未检测到；请安装 pyserial 或检查连接)")
        return 1

    port = sys.argv[1]
    cycles = int(sys.argv[2]) if len(sys.argv) > 2 else 1

    with FlowIO(port) as io:
        print(f"[hello_glove] {port} 已连接，{cycles} 个循环：充→保→释，最后抽一次")

        for i in range(cycles):
            print(f"-- cycle {i + 1}/{cycles}")
            print("  inflate(1,180) ->", encode("+", 1, 180).hex())
            io.inflate(1, 180)          # 端口 1 充气，180/255 占空比
            time.sleep(2.0)

            print("  hold(1)        ->", encode("!", 1, 0).hex())
            io.hold(1)                  # 保压（停泵关阀）
            time.sleep(1.0)

            print("  release(1)     ->", encode("^", 1, 0).hex())
            io.release(1)               # 释放（被动放气）
            time.sleep(1.0)

        print("  vacuum(180)    ->", encode("-", 0x1F, 180).hex())
        io.vacuum(180)                  # 全端口抽气一次

        reply = io.state()              # 读一次状态字
        print("  state()        ->", repr(reply) or "(无回包——固件 0xA5 handler 接线后即有)")

        print("[hello_glove] 完成")
    return 0


if __name__ == "__main__":
    sys.exit(main())
