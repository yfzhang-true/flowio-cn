"""flowio_sdk.transport — 串口传输层。

设计约束：
* SDK 本体 stdlib-only —— ``pyserial`` 为**可选依赖**，import 延迟到实例化，
  缺失时给出可操作的安装指引而不是 ImportError 裸崩；
* 固件 console 为 115200-8N1、按行文本回显（参考 firmware/serial_monitor.py
  与 main.c 的 uart_vfs 桥接），故读回以行为单位。
"""

from __future__ import annotations

import typing as _t

_PIP_HINT = "pip install pyserial"


def _import_serial():
    try:
        import serial  # noqa: F401 —— 仅探测
    except ImportError as exc:  # 给出清晰、可操作的错误
        raise RuntimeError(
            "未安装 pyserial（flowio_sdk 的串口传输为可选依赖）。"
            f"请先执行: {_PIP_HINT}"
        ) from exc
    import serial
    return serial


class SerialTransport:
    """极简串口传输：``send(bytes)`` / ``readline() -> str``。

    :param port:   串口名，如 ``"COM3"`` 或 ``"/dev/ttyUSB0"``
    :param baud:   波特率，默认 115200（固件 console 同款）
    :param timeout: 读写超时秒数；``readline`` 超时返回 ``""``

    用法::

        t = SerialTransport("COM3")
        t.send(encode("+", 1, 180))
        print(t.readline())
        t.close()

    也支持 ``with SerialTransport("COM3") as t:``。
    """

    def __init__(self, port: str, baud: int = 115200, timeout: float = 1.0) -> None:
        self.port = port
        self.baud = baud
        self.timeout = timeout
        serial = _import_serial()  # 延迟 import：没有 pyserial 也能 import 本模块
        # dtr/rts 拉低，避免打开瞬间复位 ESP32（serial_monitor.py 同款经验）
        self._ser = serial.Serial()
        self._ser.port = port
        self._ser.baudrate = baud
        self._ser.timeout = timeout
        self._ser.dtr = False
        self._ser.rts = False
        self._ser.open()

    # ---- 基本 IO ----------------------------------------------------------
    def send(self, data: bytes) -> int:
        """发送原始字节（通常已是 protocol.encode 的 5 字节帧），返回写入数。"""
        if isinstance(data, str):  # 宽容：str 按 UTF-8 编码
            data = data.encode("utf-8")
        return self._ser.write(bytes(data))

    def readline(self) -> str:
        """读一行（去掉 ``\\r\\n``）；超时返回空串。"""
        raw = self._ser.readline()
        return raw.decode("utf-8", errors="replace").rstrip("\r\n")

    def read_lines(self, idle: float = 0.2, max_lines: int = 64) -> _t.List[str]:
        """批量读到静默 ``idle`` 秒或 ``max_lines`` 为止（收启动横幅/状态回包用）。"""
        import time

        lines: _t.List[str] = []
        deadline_silence = time.monotonic() + idle
        while len(lines) < max_lines and time.monotonic() < deadline_silence:
            line = self.readline()
            if line:
                lines.append(line)
                deadline_silence = time.monotonic() + idle
            else:
                break
        return lines

    # ---- 生命周期 ----------------------------------------------------------
    def close(self) -> None:
        if getattr(self, "_ser", None) is not None and self._ser.is_open:
            self._ser.close()

    def __enter__(self) -> "SerialTransport":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # ---- 端口发现 ----------------------------------------------------------
    @staticmethod
    def list_ports() -> _t.List[str]:
        """列出可用串口名。

        优先 ``serial.tools.list_ports``（pyserial 自带）；pyserial 缺失时
        Windows 下退化为扫 ``COM1..COM255`` 探测（``os.path.exists``——仅
        Windows 文件系统语义成立），其余平台/仍无则返回 ``[]``。
        """
        try:
            from serial.tools import list_ports

            return [p.device for p in list_ports.comports()]
        except ImportError:
            pass
        import os
        import sys

        if sys.platform.startswith("win"):
            found = []
            for i in range(1, 256):
                name = f"COM{i}"
                if os.path.exists(name):
                    found.append(name)
            return found
        return []
