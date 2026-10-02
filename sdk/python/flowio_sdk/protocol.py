"""flowio_sdk.protocol — 0xA5 二进制帧编解码（与 firmware/components/pn_core/src/proto.c 同向量）。

帧格式（5 字节，proto.h v1）::

    [0xA5][cmd][ports][pwm][crc8]

* ``cmd``   ASCII 动作码，见 CMD_* 常量（命令表逐条抄自 proto.h）；
* ``ports`` 端口位掩码 bit0..bit4（bit0=端口1 ... bit4=端口5，PN_PORT_MASK_ALL=0x1F）；
* ``pwm``   占空比参数 0-255（QUERY 帧复用为传感器号）；
* ``crc8``  CRC-8/ATM：多项式 0x07、初值 0x00、MSB 先行、无反射、无异或输出，
  覆盖前 4 字节 —— 与 proto.c pn_proto_crc8() 逐位一致。

自检锚点：crc8(b"123456789") == 0xF4（CRC-8/ATM 标准检查值）。
仅依赖 stdlib。
"""

from __future__ import annotations

import typing as _t

# ---- 帧常量（proto.h） ----------------------------------------------------
PN_PROTO_MAGIC = 0xA5  # proto.h: #define PN_PROTO_MAGIC 0xA5
FRAME_LEN = 5          # proto.c: #define PN_FRAME_LEN 5
PORT_MASK_ALL = 0x1F   # actions.h: PN_PORT_MASK_ALL，bit0=端口1..bit4=端口5

# ---- 命令字节表（抄自 proto.h 动作码定义，注释含原语义） ------------------
CMD_STOP = 0x21     # '!' 停止/保压      (proto.h PN_CMD_STOP)
CMD_INFLATE = 0x2B  # '+' 充气           (proto.h PN_CMD_INFLATE)
CMD_VACUUM = 0x2D   # '-' 抽气           (proto.h PN_CMD_VACUUM)
CMD_RELEASE = 0x5E  # '^' 释放           (proto.h PN_CMD_RELEASE)
CMD_OPEN = 0x6F     # 'o' 只开端口阀     (proto.h PN_CMD_OPEN)
CMD_CLOSE = 0x63    # 'c' 只关端口阀     (proto.h PN_CMD_CLOSE)
CMD_QUERY = 0x3F    # '?' 读压力（pwm 字段=传感器号）(proto.h PN_CMD_QUERY)
CMD_STATE = 0x53    # 'S' 回传状态字（pwm 字段忽略）(proto.h PN_CMD_STATE)
CMD_RESET = 0x52    # 'R' 闭环复位       (proto.h PN_CMD_RESET)

#: 命令字节 -> 助记名（便于日志/示例）
CMD_NAMES: _t.Dict[int, str] = {
    CMD_STOP: "STOP",
    CMD_INFLATE: "INFLATE",
    CMD_VACUUM: "VACUUM",
    CMD_RELEASE: "RELEASE",
    CMD_OPEN: "OPEN",
    CMD_CLOSE: "CLOSE",
    CMD_QUERY: "QUERY",
    CMD_STATE: "STATE",
    CMD_RESET: "RESET",
}


class ProtocolError(ValueError):
    """帧不合法（长度/魔数/CRC）。"""


def _to_byte(value: int, name: str) -> int:
    """把 int 收紧到 0..255，越界即抛 ValueError（宁可拒发也不静默截断）。"""
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{name} 必须是 int，得到 {type(value).__name__}")
    if not 0 <= value <= 0xFF:
        raise ValueError(f"{name} 超出单字节范围: {value}")
    return value


def _cmd_to_byte(cmd: _t.Union[str, int]) -> int:
    if isinstance(cmd, str):
        if len(cmd) != 1:
            raise ValueError(f"cmd 必须是单字符，得到 {cmd!r}")
        return ord(cmd)
    return _to_byte(cmd, "cmd")


def crc8(data: bytes) -> int:
    """CRC-8/ATM（poly=0x07, init=0x00, MSB 先行，无反射/无异或输出）。

    与 proto.c ``pn_proto_crc8`` 位级一致；自检锚点 ``crc8(b"123456789")==0xF4``。
    """
    crc = 0x00
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = ((crc << 1) ^ 0x07) & 0xFF if (crc & 0x80) else (crc << 1) & 0xFF
    return crc


def encode(cmd: _t.Union[str, int], ports: int = 0, pwm: int = 0) -> bytes:
    """构造 5 字节帧（等价 proto.c ``pn_proto_build``）。

    :param cmd:   单字符 str（如 ``'+'``）或命令字节 int（如 :data:`CMD_INFLATE`）
    :param ports: 端口位掩码 0x00..0xFF（有效位 0x1F，超出仅透传不校验）
    :param pwm:   占空比 0..255（QUERY 帧语义为传感器号）
    """
    frame = bytearray(FRAME_LEN)
    frame[0] = PN_PROTO_MAGIC
    frame[1] = _cmd_to_byte(cmd)
    frame[2] = _to_byte(ports, "ports")
    frame[3] = _to_byte(pwm, "pwm")
    frame[4] = crc8(bytes(frame[:4]))  # 覆盖前 4 字节（proto.c ST_CRC 分支同款）
    return bytes(frame)


def decode(frame: _t.Union[bytes, bytearray]) -> _t.Dict[str, _t.Any]:
    """校验并解析 5 字节帧，返回 ``{"cmd": str, "cmd_byte": int, "ports": int, "pwm": int}``。

    长度不为 5、魔数非 0xA5、CRC 不符分别抛 :class:`ProtocolError`
    （固件侧对应流式状态机丢弃+重同步，SDK 侧在调用点显式报错）。
    """
    if isinstance(frame, str) or not isinstance(frame, (bytes, bytearray)):
        raise TypeError(f"frame 需要 bytes/bytearray，得到 {type(frame).__name__}")
    data = bytes(frame)
    if len(data) != FRAME_LEN:
        raise ProtocolError(f"帧长 {len(data)} != {FRAME_LEN}")
    if data[0] != PN_PROTO_MAGIC:
        raise ProtocolError(f"魔数 0x{data[0]:02X} != 0x{PN_PROTO_MAGIC:02X}")
    expect = crc8(data[:4])
    if expect != data[4]:
        raise ProtocolError(f"CRC 不符: 收到 0x{data[4]:02X}, 期望 0x{expect:02X}")
    return {
        "cmd": chr(data[1]),
        "cmd_byte": data[1],
        "cmd_name": CMD_NAMES.get(data[1], "UNKNOWN"),
        "ports": data[2],
        "pwm": data[3],
    }
