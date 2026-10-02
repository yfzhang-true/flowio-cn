"""flowio_sdk — FLOWIO-CN 上位机 Python SDK（0xA5 协议，与固件 proto.c 同向量）。

快速上手::

    from flowio_sdk import FlowIO
    io = FlowIO("COM3")
    io.inflate(1, 180)
    io.hold(1)
    io.release(1)
    print(io.state())
    io.close()

协议真源：``firmware/components/pn_core/src/proto.c`` 与
``firmware/components/pn_core/include/pn_core/proto.h``（帧 5 字节
``[0xA5][cmd][ports][pwm][crc8]``，CRC-8 poly=0x07 init=0x00）。
"""

from .client import ALL_PORTS, PORT1, PORT2, PORT3, PORT4, PORT5, FlowIO, port_mask
from .protocol import (
    CMD_CLOSE,
    CMD_INFLATE,
    CMD_OPEN,
    CMD_QUERY,
    CMD_RELEASE,
    CMD_RESET,
    CMD_STATE,
    CMD_STOP,
    CMD_VACUUM,
    FRAME_LEN,
    PN_PROTO_MAGIC,
    PORT_MASK_ALL,
    ProtocolError,
    crc8,
    decode,
    encode,
)
from .transport import SerialTransport

__version__ = "0.1.0"

__all__ = [
    "FlowIO",
    "SerialTransport",
    "encode",
    "decode",
    "crc8",
    "ProtocolError",
    "PN_PROTO_MAGIC",
    "FRAME_LEN",
    "PORT_MASK_ALL",
    "ALL_PORTS",
    "PORT1",
    "PORT2",
    "PORT3",
    "PORT4",
    "PORT5",
    "port_mask",
    "CMD_STOP",
    "CMD_INFLATE",
    "CMD_VACUUM",
    "CMD_RELEASE",
    "CMD_OPEN",
    "CMD_CLOSE",
    "CMD_QUERY",
    "CMD_STATE",
    "CMD_RESET",
]
