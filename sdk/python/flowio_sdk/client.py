"""flowio_sdk.client — 高层 API。

命令字节全部抄自 firmware/components/pn_core/include/pn_core/proto.h
动作码定义（见 protocol.py 的 CMD_* 常量，注释逐条对应）；语义参考
actions.c：inflate=开进气阀+开端口阀+泵起（pwm=0 时固件自替 255）、
vacuum=开排气位+开端口阀+泵起、release=停泵+关进气+开端口+开排气（被动放气）、
hold('!')=泵停+进出全关+端口保持。

固件回包：0xA5 帧协议的 handler 尚未在 main.c 接线（S4 骨架先行），
故 ``read_reply`` 默认 False，仅 state()/query() 这类天生要回包的动作
默认尝试读回一行（超时得空串，不致命）。
"""

from __future__ import annotations

import typing as _t

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
    PORT_MASK_ALL,
    encode,
)

#: 端口号 -> 位掩码（actions.h: bit0=端口1 ... bit4=端口5）
PORT1 = 0x01
PORT2 = 0x02
PORT3 = 0x04
PORT4 = 0x08
PORT5 = 0x10
ALL_PORTS = PORT_MASK_ALL


def port_mask(*ports: int) -> int:
    """端口号(1..5)列表转位掩码：``port_mask(1,3) -> 0b01001``。"""
    mask = 0
    for p in ports:
        if not 1 <= p <= 5:
            raise ValueError(f"端口号需 1..5，得到 {p}")
        mask |= 1 << (p - 1)
    return mask


class FlowIO:
    """FlowIO 上位机会话。

    :param port: 串口名（如 ``"COM3"``）。传 ``None`` 且不给 ``transport``
                 可构造"离线"实例（仅用于构造帧，不发不收）。
    :param baud: 波特率，默认 115200。
    :param transport: 自备传输对象（测试注入口），只需实现
                      ``send(bytes)`` 与 ``readline() -> str``。

    用法::

        io = FlowIO("COM3")
        io.inflate(1, 180)   # 端口 1 以 180/255 占空比充气
        io.state()           # -> "S 0000 ..." 状态行（str）
    """

    def __init__(
        self,
        port: _t.Optional[str] = None,
        baud: int = 115200,
        transport: _t.Optional[object] = None,
    ) -> None:
        self._transport = transport
        if transport is None and port is not None:
            from .transport import SerialTransport  # 延迟：pyserial 可选

            self._transport = SerialTransport(port, baud=baud)

    # ---- 核心：发帧 + 可选读回 ---------------------------------------------
    def _cmd(
        self,
        cmd: _t.Union[str, int],
        ports: int = 0,
        pwm: int = 0,
        read_reply: bool = False,
    ) -> _t.Optional[str]:
        """发一帧，可选读回一行回包。

        :returns: ``read_reply=True`` 时返回回包行（超时为 ``""``），否则 ``None``。
        """
        frame = encode(cmd, ports, pwm)
        if self._transport is None:
            raise RuntimeError("FlowIO 无传输层：构造时传 port= 或 transport=")
        self._transport.send(frame)
        if read_reply:
            return self._transport.readline()
        return None

    # ---- 高层动作（命令字节来源：proto.h 动作码定义） ----------------------
    def inflate(self, port: int = 1, pwm: int = 255) -> None:
        """充气：``'+'`` (PN_CMD_INFLATE)。pn_start_inflation——pwm=0 固件自替 255。"""
        self._cmd(CMD_INFLATE, ports=port_mask(port), pwm=pwm)

    def vacuum(self, pwm: int = 255, ports: int = ALL_PORTS) -> None:
        """抽气：``'-'`` (PN_CMD_VACUUM)。pn_start_vacuum。"""
        self._cmd(CMD_VACUUM, ports=ports, pwm=pwm)

    def hold(self, port: int = 1) -> None:
        """保压/停：``'!'`` (PN_CMD_STOP)。pn_stop_action——全阀关+泵停。"""
        self._cmd(CMD_STOP, ports=port_mask(port))

    def release(self, port: int = 1) -> None:
        """释放：``'^'`` (PN_CMD_RELEASE)。pn_start_release——被动放气，pwm 忽略。"""
        self._cmd(CMD_RELEASE, ports=port_mask(port))

    def open_ports(self, ports: int) -> None:
        """只开端口阀：``'o'`` (PN_CMD_OPEN)。"""
        self._cmd(CMD_OPEN, ports=ports)

    def close_ports(self, ports: int) -> None:
        """只关端口阀：``'c'`` (PN_CMD_CLOSE)。"""
        self._cmd(CMD_CLOSE, ports=ports)

    def query(self, sensor: int = 0) -> str:
        """读压力：``'?'`` (PN_CMD_QUERY)，pwm 字段复用为传感器号（proto.h）。"""
        return self._cmd(CMD_QUERY, ports=0, pwm=sensor, read_reply=True) or ""

    def state(self) -> str:
        """读状态字：``'S'`` (PN_CMD_STATE)。返回回包行 str（超时为空串）。"""
        return self._cmd(CMD_STATE, ports=0, pwm=0, read_reply=True) or ""

    def reset(self) -> None:
        """闭环复位：``'R'`` (PN_CMD_RESET)。"""
        self._cmd(CMD_RESET)

    # ---- 便捷 ---------------------------------------------------------------
    def close(self) -> None:
        close = getattr(self._transport, "close", None)
        if close is not None:
            close()

    def __enter__(self) -> "FlowIO":
        return self

    def __exit__(self, *exc) -> None:
        self.close()
