"""FlowIO P0 数字孪生服务：pn_twin.dll (真实逻辑层) + 本地 Web UI

启动:  python server.py   然后浏览器打开 http://127.0.0.1:8000
依赖:  仅 Python 标准库 + pn_twin.dll（本目录，由 gcc 编译）
"""
import ctypes
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).parent

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
        if path in ("/", "/index.html"):
            self._send(200, (ROOT / "index.html").read_bytes(), "text/html; charset=utf-8")
        elif path in ("/babylon", "/babylon.html"):
            self._send(200, (ROOT / "babylon.html").read_bytes(), "text/html; charset=utf-8")
        elif path == "/lib/babylon.min.js":
            self._send(200, (ROOT / "lib" / "babylon.min.js").read_bytes(),
                       "application/javascript; charset=utf-8")
        elif path == "/api/state":
            self._json({
                "state": lib.pn_twin_state(),
                "valves": [lib.pn_twin_valve_duty(i) for i in range(7)],
                "pump": lib.pn_twin_pump_duty(),
                "sensors": [round(lib.pn_twin_sensor(i), 2) for i in range(2)],
                "cl": CL_NAMES.get(lib.pn_twin_cl_status(), "?"),
                "err": 1 if (lib.pn_twin_state() & 0x8000) else 0,
            })
        else:
            self._send(404, '{"error":"not found"}', "application/json")

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(n).decode("utf-8", errors="replace")
        if self.path == "/api/cmd":
            lib.pn_twin_command(body.strip())
            self._json({"ok": True})
        elif self.path == "/api/sim":
            try:
                idx, kpa = (float(x) for x in body.strip().split())
                lib.pn_twin_set_sensor(int(idx), kpa)
                self._json({"ok": True})
            except ValueError:
                self._json({"ok": False})
        else:
            self._send(404, '{"error":"not found"}', "application/json")

    def log_message(self, fmt, *args):
        pass


if __name__ == "__main__":
    lib.pn_twin_init()
    threading.Thread(target=tick_loop, daemon=True).start()
    print("FlowIO P0 数字孪生服务 → http://127.0.0.1:8000")
    ThreadingHTTPServer(("127.0.0.1", 8000), Handler).serve_forever()
