"""FlowIO P0 数字孪生服务：pn_twin.dll (真实逻辑层) + 本地 Web UI

启动:  python server.py   然后浏览器打开 http://127.0.0.1:8000
依赖:  仅 Python 标准库 + pn_twin.dll（本目录，由 gcc 编译）
"""
import ctypes
import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).parent
PORT = int(os.environ.get("TWIN_PORT", "8000"))

lib = ctypes.CDLL(str(ROOT / "pn_twin.dll"))
lib.pn_twin_state.restype = ctypes.c_uint32
lib.pn_twin_sensor.restype = ctypes.c_float
lib.pn_twin_sensor.argtypes = [ctypes.c_uint8]
lib.pn_twin_valve_duty.restype = ctypes.c_uint8
lib.pn_twin_valve_duty.argtypes = [ctypes.c_uint8]
lib.pn_twin_pump_duty.restype = ctypes.c_uint8
lib.pn_twin_cl_status.restype = ctypes.c_int
lib.pn_twin_command.argtypes = [ctypes.c_char_p]
lib.pn_twin_set_sensor.argtypes = [ctypes.c_uint8, ctypes.c_float]
lib.pn_twin_set_leak.argtypes = [ctypes.c_uint8, ctypes.c_float]
lib.pn_twin_leak.restype = ctypes.c_float
lib.pn_twin_leak.argtypes = [ctypes.c_uint8]
lib.pn_twin_port_pressure.restype = ctypes.c_float
lib.pn_twin_port_pressure.argtypes = [ctypes.c_uint8]

CL_NAMES = {0: "IDLE", 1: "RUNNING", 2: "DONE", 3: "TIMEOUT", 4: "ERR"}


def tick_loop():
    while True:
        lib.pn_twin_tick()
        time.sleep(0.05)


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype):
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(data)

    def _json(self, obj):
        self._send(200, json.dumps(obj, ensure_ascii=False), "application/json; charset=utf-8")

    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/", "/index.html", "/gui", "/gui.html"):
            self._send(200, (ROOT / "gui.html").read_bytes(), "text/html; charset=utf-8")
        elif path == "/lib/echarts.min.js":
            self._send(200, (ROOT / "lib" / "echarts.min.js").read_bytes(),
                       "application/javascript; charset=utf-8")
        elif path == "/api/state":
            self._json({
                "state": lib.pn_twin_state(),
                "valves": [lib.pn_twin_valve_duty(i) for i in range(7)],
                "pump": lib.pn_twin_pump_duty(),
                "sensors": [round(lib.pn_twin_sensor(i), 2) for i in range(2)],
                "ports_p": [round(lib.pn_twin_port_pressure(i), 2) for i in range(5)],
                "cl": CL_NAMES.get(lib.pn_twin_cl_status(), "?"),
                "err": 1 if (lib.pn_twin_state() & 0x8000) else 0,
                "leaks": [round(lib.pn_twin_leak(i), 3) for i in range(7)],
            })
        else:
            self._send(404, '{"error":"not found"}', "application/json")

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(n).decode("utf-8", errors="replace")
        if self.path == "/api/cmd":
            lib.pn_twin_command(body.strip().encode("utf-8"))
            self._json({"ok": True})
        elif self.path == "/api/reset":
            # 虚拟断电重启：超压等错误位是固件安全锁存（set 后不复位），
            # 真机需断电重启；孪生用 re-init 等效模拟这一动作。
            lib.pn_twin_init()
            self._json({"ok": True})
        elif self.path == "/api/sim":
            try:
                idx, kpa = (float(x) for x in body.strip().split())
                lib.pn_twin_set_sensor(int(idx), kpa)
                self._json({"ok": True})
            except ValueError:
                self._json({"ok": False})
        elif self.path == "/api/leak":
            # TinyML Phase 0：泄漏注入（SPEC 15）。body: "<idx 0-6> <k 0-1>" 或 "reset"
            try:
                parts = body.strip().split()
                if len(parts) == 1 and parts[0] == "reset":
                    for i in range(7):
                        lib.pn_twin_set_leak(i, 0.0)
                    self._json({"ok": True})
                elif len(parts) == 2:
                    idx, k = int(parts[0]), float(parts[1])
                    if 0 <= idx <= 6 and 0.0 <= k <= 1.0:
                        lib.pn_twin_set_leak(idx, k)
                        self._json({"ok": True})
                    else:
                        self._json({"ok": False})
                else:
                    self._json({"ok": False})
            except ValueError:
                self._json({"ok": False})
        else:
            self._send(404, '{"error":"not found"}', "application/json")

    def log_message(self, fmt, *args):
        pass


if __name__ == "__main__":
    lib.pn_twin_init()
    threading.Thread(target=tick_loop, daemon=True).start()
    print(f"FlowIO P0 数字孪生服务 → http://127.0.0.1:{PORT}")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
