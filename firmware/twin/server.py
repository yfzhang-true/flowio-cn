"""FlowIO P0 数字孪生服务：pn_twin.dll (真实逻辑层) + 本地 Web UI  [API v1.2]

启动:  python server.py   然后浏览器打开 http://127.0.0.1:8000
依赖:  仅 Python 标准库 + pn_twin.dll（本目录，由 gcc 编译）

v1.2 新增 (S1/S2 孪生平台扩展):
  GET  /api/board/state[?since=s]     板级电气孪生快照 (board_model, 600s 历史)
  GET  /api/board/sim/presets         仿真参数域表 (前端动态表单)
  GET  /api/board/assembly            3D 装配 (meshes/assembly.json)
  GET  /api/board/history/export      历史四通道 CSV 导出
  GET  /lib/*.js /meshes/*.stl        静态资源 (echarts / three.min / OrbitControls / STLLoader)
  POST /api/board/sim                 参数化电路仿真重算 (buck/dior/valve/i2c)
  POST /api/time                      时间控制 (暂停/倍速/单步)
  POST /api/record | /api/record/replay  命令录制与回放
"""
import concurrent.futures
import ctypes
import json
import os
import re
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).parent
PORT = int(os.environ.get("TWIN_PORT", "8000"))

sys.path.insert(0, str(ROOT))
import board_model   # noqa: E402  (S2 板级电气孪生纯模型)
import sim_engine    # noqa: E402  (S1 参数化仿真引擎)

API_VER = "1.2"
BOARD = board_model.BoardModel()
REC = {"on": False, "buf": []}                       # 命令录制 (wall-clock 时间戳)
TIMECTL = {"paused": False, "speed": 1.0, "step_once": False}   # 时间控制
CARRY = 0.0                                          # 分数倍速累加器 (tick_loop 专用)
SIM_POOL = concurrent.futures.ThreadPoolExecutor(1)  # 仿真超时保护 (单工位串行)

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
lib.pn_twin_leak_detect.restype = ctypes.c_int
lib.pn_twin_leak_detect.argtypes = [ctypes.POINTER(ctypes.c_float)]
lib.pn_twin_ml_samples.restype = ctypes.c_int

CL_NAMES = {0: "IDLE", 1: "RUNNING", 2: "DONE", 3: "TIMEOUT", 4: "ERR"}


def _board_step(dt):
    """板级电气孪生步进 (duty 为 c_uint8 无符号, >0 即激励)。"""
    BOARD.step(dt, [lib.pn_twin_valve_duty(i) > 0 for i in range(8)],
               lib.pn_twin_pump_duty() > 0)


def tick_loop():
    global CARRY
    while True:
        if TIMECTL["paused"] and not TIMECTL["step_once"]:
            time.sleep(0.05)
            continue
        if TIMECTL["step_once"]:                 # 暂停下单步：执行一次 tick 后清标志
            lib.pn_twin_tick()
            TIMECTL["step_once"] = False
            _board_step(0.05)
        else:
            # 分数倍速累加器: n=本周期 dll tick 数, 可为 0 (speed<1 时隔周期才动)。
            # dll 与板级同进同停 (n tick ↔ 板级 0.05n s), 时间基严格一致;
            # 不再用 round 钳 1 —— 否则 speed<0.5 时 dll 仍 1× 而板级慢速, 两者发散。
            CARRY += TIMECTL["speed"]
            n = int(CARRY)
            CARRY -= n
            if n:
                for _ in range(n):
                    lib.pn_twin_tick()
                _board_step(0.05 * n)
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

    def _err(self, code, msg):
        self._send(code, json.dumps({"error": msg}, ensure_ascii=False), "application/json")

    def _query(self, key):
        """从 self.path 提取查询参数值 (无则 None)。"""
        qs = self.path.partition("?")[2]
        for kv in qs.split("&"):
            if kv.startswith(key + "="):
                return kv[len(key) + 1:]
        return None

    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/", "/index.html", "/gui", "/gui.html"):
            self._send(200, (ROOT / "gui.html").read_bytes(), "text/html; charset=utf-8")
        elif path == "/lib/echarts.min.js":
            self._send(200, (ROOT / "lib" / "echarts.min.js").read_bytes(),
                       "application/javascript; charset=utf-8")
        elif path.startswith("/lib/"):
            # 通用库路由: echarts / three.min / OrbitControls / STLLoader (防穿越: 白名单字符)
            name = path[len("/lib/"):]
            f = ROOT / "lib" / name
            if not re.fullmatch(r"[A-Za-z0-9_.-]+\.js", name) or not f.exists():
                self._err(404, f"lib 文件不存在: {name}")
            else:
                self._send(200, f.read_bytes(), "application/javascript; charset=utf-8")

        # ------------------------------------------------ v1.2 板级电气孪生
        elif path == "/api/board/state":
            tel = BOARD.telemetry()
            since = self._query("since")           # ?since=<秒>: 历史截取 t>=since
            if since is not None:
                try:
                    s = float(since)
                except ValueError:
                    s = None
                if s is not None:
                    h = tel["history"]
                    i0 = next((j for j, tv in enumerate(h["t"]) if tv >= s), len(h["t"]))
                    tel["history"] = {k: v[i0:] for k, v in h.items()}
            tel["api"] = API_VER
            self._json(tel)

        elif path == "/api/board/sim/presets":
            presets = {}
            for circuit, rows in sim_engine.SPEC.items():
                presets[circuit] = {
                    "default": {name: dflt for name, _lo, _hi, dflt in rows},
                    "bounds": {name: [lo, hi] for name, lo, hi, _d in rows},
                }
            self._json({"api": API_VER, "presets": presets})

        elif path == "/api/board/assembly":
            f = ROOT / "meshes" / "assembly.json"
            if not f.exists():
                self._err(404, "meshes 未生成: 跑 enclosure/make_meshes.py")
            else:
                try:
                    d = json.loads(f.read_bytes().decode("utf-8"))
                except ValueError:
                    self._err(500, "assembly.json 解析失败")
                    return
                d["api"] = API_VER
                self._json(d)

        elif path == "/api/board/history/export":
            h = BOARD.telemetry()["history"]
            lines = ["t_s,rail5v_v,rail3v3_v,load_a"]
            for t, a, b, c in zip(h["t"], h["v5"], h["v33"], h["load"]):
                lines.append(f"{t:.2f},{a:.3f},{b:.3f},{c:.3f}")
            self._send(200, "\n".join(lines), "text/csv")

        elif path.startswith("/meshes/"):
            name = path[len("/meshes/"):]          # 防穿越: 仅字母数字下划线点 + .stl
            if not (re.fullmatch(r"[A-Za-z0-9_.]+", name) and name.endswith(".stl")):
                self._err(404, "非法 mesh 路径")
                return
            f = ROOT / "meshes" / name
            if f.exists():
                self._send(200, f.read_bytes(), "model/stl")
            else:
                self._err(404, f"mesh 不存在: {name}")

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
                "ml": lib.pn_twin_ml_samples(),
            })
        else:
            self._send(404, '{"error":"not found"}', "application/json")

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(n).decode("utf-8", errors="replace")
        if self.path == "/api/cmd":
            cmd = body.strip()
            if REC["on"]:                          # 录制旁路：墙钟时间戳 + 命令字符串
                REC["buf"].append({"t": time.time(), "cmd": cmd})
            lib.pn_twin_command(cmd.encode("utf-8"))
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

        # ------------------------------------------------ v1.2 时间/仿真/录制
        elif self.path == "/api/board/sim":
            try:
                req = json.loads(body) if body.strip() else {}
            except ValueError:
                req = None
            if not isinstance(req, dict):
                req = {}
            try:
                fut = SIM_POOL.submit(sim_engine.run, req.get("circuit"), req.get("params"))
                r = fut.result(timeout=3)
            except sim_engine.ParamError as e:      # 未知电路/参数/超域 → 400
                self._send(400, json.dumps({"error": str(e)}, ensure_ascii=False),
                           "application/json")
                return
            except concurrent.futures.TimeoutError:
                self._err(504, "仿真超时 (>3s)")
                return
            r["api"] = API_VER
            self._json(r)

        elif self.path == "/api/time":
            try:
                req = json.loads(body) if body.strip() else {}
            except ValueError:
                req = None
            if not isinstance(req, dict):
                req = {}
            if "paused" in req:
                TIMECTL["paused"] = bool(req["paused"])
            if "speed" in req:
                try:
                    TIMECTL["speed"] = min(4.0, max(0.25, float(req["speed"])))
                except (TypeError, ValueError):
                    pass
            if "step_once" in req:
                TIMECTL["step_once"] = bool(req["step_once"])
            self._json({"api": API_VER, **TIMECTL})

        elif self.path == "/api/record":
            try:
                req = json.loads(body) if body.strip() else {}
            except ValueError:
                req = None
            if not isinstance(req, dict):
                req = {}
            action = req.get("action")
            if action == "start":
                REC["on"] = True
                REC["buf"] = []
            elif action == "stop":
                REC["on"] = False
                out = ROOT / "recordings" / f"rec_{time.strftime('%H%M%S')}.json"
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_bytes(json.dumps(REC["buf"], ensure_ascii=False).encode("utf-8"))
            self._json({"api": API_VER, "recording": REC["on"], "n": len(REC["buf"])})

        elif self.path == "/api/record/replay":
            try:
                req = json.loads(body) if body.strip() else {}
            except ValueError:
                req = None
            if not isinstance(req, dict):
                req = {}
            replayed = 0
            for ev in req.get("events") or []:
                if isinstance(ev, dict) and isinstance(ev.get("cmd"), str):
                    lib.pn_twin_command(ev["cmd"].encode("utf-8"))
                    replayed += 1
            self._json({"api": API_VER, "replayed": replayed})

        else:
            self._send(404, '{"error":"not found"}', "application/json")

    def log_message(self, fmt, *args):
        pass


if __name__ == "__main__":
    lib.pn_twin_init()
    threading.Thread(target=tick_loop, daemon=True).start()
    print(f"FlowIO P0 数字孪生服务 [API {API_VER}] → http://127.0.0.1:{PORT}")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
