# flowio_sdk — FLOWIO-CN 上位机 Python SDK

0xA5 二进制帧协议的 Python 实现，编解码与固件 `firmware/components/pn_core/src/proto.c` **同向量**（测试向量共享，见 `tests/vectors.json`）。

```bash
pip install pyserial                      # 可选依赖（仅串口传输需要；SDK 本体 stdlib-only）
python examples/hello_glove.py COM3       # 充→保→释→抽 一个来回
```

```python
from flowio_sdk import FlowIO
io = FlowIO("COM3")          # 或 FlowIO(transport=自备对象) 离线测试
io.inflate(1, 180)           # '+' 端口1 充气 180/255
io.hold(1); io.release(1)    # '!' 保压 / '^' 释放
print(io.state())            # 'S' 读状态字（str）
```

协议真源与帧格式：`firmware/components/pn_core/include/pn_core/proto.h` —— 5 字节帧 `[0xA5][cmd][ports][pwm][crc8]`，cmd 为 ASCII 动作码（`! + - ^ o c ? S R`），ports 为 bit0..4 端口掩码，CRC-8 poly=0x07 init=0x00 覆盖前 4 字节。

测试：`python tests/test_protocol.py`（8 组固件同向量双向校验，通过输出 `sdk protocol tests OK`）。
