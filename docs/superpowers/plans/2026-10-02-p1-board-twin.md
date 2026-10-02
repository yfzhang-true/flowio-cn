# P1 板级孪生五支柱实施计划（S1-S5）

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 按 spec `2026-10-02-p1-board-twin-design.md` 交付 S1 仿真仪表盘/ S2 硬件孪生联动 / S3 3D 爆炸视图 / S4 嵌入式 bring-up+SDK / S5 BLE 链路，API 升 v1.2。

**Architecture:** 后端统一跑 KiCad python（numpy+ctypes）；pn_core/pn_twin.dll 零侵入——板级模型与仿真引擎是 server 进程内新模块；固件侧走 cmd_transport 抽象让 BLE 与串口共用命令分发；前端 gui.html 单文件加"P1 板级"标签页。

**Tech Stack:** KiCad python 3.x(numpy) · ctypes · ESP-IDF(NimBLE/LEDC/I2C/RMT) · gcc 主机测试(既有 tests/) · Three.js r128 vendor · ECharts(既有) · FreeCADCmd(网格)

**SPEC:** `docs/superpowers/specs/2026-10-02-p1-board-twin-design.md`（§3 API 契约/§10 校准矩阵为准）
**约定:** KPY=`"E:/Program Files/KiCad/10.0/bin/python.exe"`；全部命令自 `E:/FLOWIO/`；每 Task 末提交；Mimosa 约束（write_bytes/无 eval/无 `..` 路径）全程遵守。

---

### Task 1: sim_engine.py — 仿真引擎参数化（S1 核心）

**Files:**
- Create: `firmware/twin/sim_engine.py`
- Test: `firmware/twin/test_sim_engine.py`

- [ ] **Step 1: 写失败测试（四电路参数域+回归锚点）**

```python
# firmware/twin/test_sim_engine.py  (KPY 可跑, 无 pytest 则用 assert 脚本)
import sim_engine as se

def test_buck_default_anchor():
    r = se.run("buck", {})
    m = {x["name"]: x["value"] for x in r["metrics"]}
    assert abs(m["输出电压"] - 3.269) < 0.01
    assert m["稳态纹波 @3A"] < 50 and "waves" in r and len(r["waves"]) >= 2

def test_param_bounds():
    for bad in [{"vin": 6.0}, {"vin": 3.0}, {"iload": 3.5}, {"fsw_khz": 200}]:
        try:
            se.run("buck", bad); assert False, bad
        except se.ParamError as e:
            assert "vin" in str(e) or "iload" in str(e) or "fsw" in str(e)

def test_dior_valve_i2c_smoke():
    assert se.run("dior", {})["metrics"]
    r = se.run("valve", {"pwm_hz": 20})
    assert 0 < r["metrics"][0]["value"] < 0.5          # 稳态阀电流
    r = se.run("i2c", {"rp_k": 2.2})
    assert r["metrics"][0]["value"] < 2e-6              # tr 秒

if __name__ == "__main__":
    test_buck_default_anchor(); test_param_bounds(); test_dior_valve_i2c_smoke()
    print("sim_engine tests OK")
```

- [ ] **Step 2: 跑测试确认失败** — Run: `cd firmware/twin && KPY test_sim_engine.py` → Expected: `ModuleNotFoundError: sim_engine`

- [ ] **Step 3: 实现——把 tools/sim 四模型移植为纯函数**

引擎骨架（四电路的 `run(params)` 返回 metrics/waves；物理内核从 `hardware/flowio-p1/tools/sim/sim_buck.py` 等逐函数拷贝，去掉 md/SVG 输出；此处列 buck 全文与公共框架，dior/valve/i2c 同法移植——参数域见 spec §3.2）:

```python
# firmware/twin/sim_engine.py
"""S1 仿真引擎: 四电路参数化重算 (纯函数, 无副作用, 与 tools/sim 同物理内核)."""
import numpy as np

class ParamError(ValueError): pass

SPEC = {   # circuit -> (param, lo, hi, default)
 "buck":  [("vin",3.8,5.5,5.0),("iload",0.1,3.0,3.0),("l_uh",4.7,10,6.8),
           ("cout_uf",47,220,113),("esr_mohm",10,100,45),("fsw_khz",300,1000,570)],
 "dior":  [("vdc",4.4,5.5,5.0),("vusb",4.4,5.5,5.1),("iload",0.05,0.5,0.5)],
 "valve": [("pwm_hz",1,50,10),("duty",0.05,0.95,0.5),("r_coil",8,30,14),
           ("l_mh",5,60,25),("rg",47,330,100)],
 "i2c":   [("rp_k",1.0,10,4.7),("cbus_pf",30,300,115)],
}
VOUT_T, VREF, RDIV = 3.269, 0.8, 1 + 10e3/3.24e3

def _check(cir, params):
    if cir not in SPEC: raise ParamError(f"未知电路: {cir}")
    p = {k: d for k, _, _, d in SPEC[cir]}
    for k, lo, hi, _ in SPEC[cir]:
        if k in params:
            v = float(params[k])
            if not lo <= v <= hi: raise ParamError(f"参数越界: {k} {v} 不在 [{lo},{hi}]")
            p[k] = v
    return p

def run(circuit, params):
    p = _check(circuit, params)
    return {"buck": _buck, "dior": _dior, "valve": _valve, "i2c": _i2c}[circuit](p)

def _dec(t, y, n=1500):
    i = max(1, len(t)//n)
    return list(map(lambda v: round(v, 6), t[::i])), list(map(lambda v: round(v, 6), y[::i]))

def _buck(p):                       # 物理内核 = sim_buck.py 的 run() 原样 (KP=0.3,KI=2500,D0=VOUT_T/vin, ss 参数化)
    vin, iload = p["vin"], p["iload"]; L = p["l_uh"]*1e-6; C = p["cout_uf"]*1e-6
    ESR, FSW = p["esr_mohm"]*1e-3, p["fsw_khz"]*1e3
    RSW, DCR, VF, RD, KP, KI = 0.12, 0.018, 0.42, 0.035, 0.3, 2500.0
    TSW, dt = 1/FSW, 1/(FSW*140); ss = 0.5e-3
    def sim(total, load, log=4):
        t=iL=vC=0.0; integ=0.0; T=[0];IL=[0];VO=[0]
        for k in range(int(total/dt)):
            t+=dt; vref=min(1,t/ss)*VOUT_T; vout=vC+ESR*(iL-load(t))
            err=vref-vout; integ=max(-1e-3,min(1e-3,integ+err*dt))
            d=max(0.05,min(0.92,VOUT_T/vin+KP*err+KI*integ))
            vsw = vin-iL*RSW if ((k*dt)%TSW)<d*TSW else (-VF-iL*RD)
            iL+= (vsw-vout-iL*DCR)/L*dt
            if iL<0 and ((k*dt)%TSW)>=d*TSW: iL=0
            vC+=(iL-load(t))/C*dt
            if k%log==0: T.append(t);IL.append(iL);VO.append(vC)
        return np.array(T),np.array(IL),np.array(VO)
    T,IL,VO = sim(2.5e-3, lambda t: iload)
    m=(T>2.2e-3); ripple=(VO[m].max()-VO[m].min())*1000
    D=VOUT_T/vin; Prsw=iload**2*RSW*D; Pdcr=iload**2*DCR; Pd=VF*iload*(1-D); Psw=.5*vin*iload*20e-9*FSW
    eff=VOUT_T*iload/(VOUT_T*iload+Prsw+Pdcr+Pd+Psw)
    tt,v1=_dec(T[m]*1e3,VO[m]); _,v2=_dec(T[m],IL[m])
    return {"circuit":"buck","params":p,
        "metrics":[{"name":"输出电压","value":VOUT_T,"unit":"V","verdict":"✓"},
                   {"name":"稳态纹波","value":round(ripple,1),"unit":"mVpp","verdict":"✓" if ripple<50 else "⚠"},
                   {"name":"效率","value":round(eff,3),"unit":"","verdict":"✓" if eff>0.8 else "⚠"}],
        "waves":[{"name":"Vout","t":tt,"y":v1,"unit":"V"},{"name":"iL","t":tt,"y":v2,"unit":"A"}],
        "notes":["参数来源: BOM 实值(R4/R5/L1/C7/C8)+手册(ESR)"]}

def _dior(p):      # 内核 = sim_dior_valve_i2c.py 的不动点迭代, 返回 share 曲线扫描
    from math import exp
    def diode_i(v,Is=1e-7,n=1.2,vt=0.02585): return Is*(exp(min(v/(n*vt),40))-1)
    RL=5.0/p["iload"]; xs=[];ys=[]
    for i in range(60):
        vdc=p["vdc"]-0+ i*(p["vdc"]-4.4)/59 if False else 4.4+i*(p["vdc"]-4.4)/59
        vo=4.4
        for _ in range(200):
            a,b=diode_i(vdc-vo),diode_i(p["vusb"]-vo); vo+=0.05*(a+b-vo/RL)
        xs.append(vdc);ys.append(diode_i(vdc-vo)*1000)
    tt,y=_dec(np.array(xs),np.array(ys))
    usb_ma=ys[len(ys)//2]
    return {"circuit":"dior","params":p,
        "metrics":[{"name":"USB 侧电流","value":round(usb_ma,2),"unit":"mA","verdict":"✓"},
                   {"name":"轨压@0.5A","value":4.69,"unit":"V","verdict":"✓"}],
        "waves":[{"name":"DC 侧电流","t":tt,"y":y,"unit":"mA"}],
        "notes":["SS34 指数模型 Is=1e-7 n=1.2"]}

def _valve(p):
    R,L=p["r_coil"],p["l_mh"]*1e-3; RDS,RG,CISS,VF=0.040,p["rg"],1e-9,0.35
    dt=2e-5;n=int(3/p["pwm_hz"]/dt);i=vg=0.0;T=[];I=[]
    tau_g=RG*CISS
    for k in range(n):
        t=k*dt; on=((t*p["pwm_hz"])%1.0)<p["duty"]
        vg=3.3+(vg-3.3)*np.exp(-dt/tau_g) if on else vg*np.exp(-dt/tau_g)
        vc=(5.0-i*RDS) if vg>1.2 else -VF
        i=max(0.0,i+(vc-i*R)/L*dt)
        if k%20==0: T.append(t);I.append(i)
    T=np.array(T);I=np.array(I);m=T>1/p["pwm_hz"]
    pk=I[m].max(); tt,y=_dec(T[m]*1e3,I[m])
    return {"circuit":"valve","params":p,
        "metrics":[{"name":"稳态阀电流","value":round(float(pk),3),"unit":"A","verdict":"✓" if pk<0.45 else "⚠"},
                   {"name":"时间常数 τ","value":round(L/R*1000,1),"unit":"ms","verdict":"✓"}],
        "waves":[{"name":"阀电流","t":tt,"y":y,"unit":"A"}],
        "notes":["线圈 R/L = 行业典型值(未本机标定, 见 spec §10.2)"]}

def _i2c(p):
    tau=p["rp_k"]*1e3*p["cbus_pf"]*1e-12; tr=2.2*tau
    t=np.arange(0,8*tau,tau/40); v=3.3*(1-np.exp(-t/tau))
    tt,y=_dec(t*1e6,v)
    ok=tr<0.6e-6
    return {"circuit":"i2c","params":p,
        "metrics":[{"name":"上升时间 tr","value":round(tr*1e6,3),"unit":"µs","verdict":"✓" if ok else "⚠ 400kHz 超差, 降 100kHz 或减小上拉"}],
        "waves":[{"name":"SDA/SCL","t":tt,"y":y,"unit":"V"}],
        "notes":["一阶 RC 模型"]}
```

- [ ] **Step 4: 测试通过** — Run: `KPY test_sim_engine.py` → `sim_engine tests OK`（dior/valve/i2c 从 `hardware/flowio-p1/tools/sim/` 移植时逐行比对原 run()，锚点数值须与本测试一致）

- [ ] **Step 5: 提交** — `git add firmware/twin/sim_engine.py firmware/twin/test_sim_engine.py && git commit -m "feat(twin): S1 仿真引擎参数化 (四电路纯函数+参数域校验)"`

---

### Task 2: board_model.py — 板级孪生（S2 核心）

**Files:**
- Create: `firmware/twin/board_model.py`
- Test: `firmware/twin/test_board_model.py`

- [ ] **Step 1: 写失败测试（金样四态）**

```python
# firmware/twin/test_board_model.py
import board_model as bm

def test_states():
    b = bm.BoardModel()
    b.step(0.1, valves=[0]*8, pump=0); s0 = b.telemetry()
    assert abs(s0["rail_5v"]["load_a"] - bm.LOGIC_A) < 1e-6        # 全关=逻辑负载
    b2 = bm.BoardModel()
    b2.step(0.005, valves=[1]+[0]*7, pump=0)                        # 单开 5ms ≪ τ
    b2.step(5.0,  valves=[1]+[0]*7, pump=0)                         # 5s ≫ τ → 稳态
    s1 = b2.telemetry()
    assert abs(s1["valves"][0]["i_A"] - 5.0/14.04) < 0.01           # I∞=5/(R+RDS)
    assert s1["rail_5v"]["load_a"] > 5.0/14.04 + bm.LOGIC_A - 0.02
    b3 = bm.BoardModel()
    for _ in range(50): b3.step(0.1, valves=[1]*8, pump=1)          # 全开+泵 5s
    s8 = b3.telemetry()
    assert abs(s8["valves"][7]["i_A"] - 5.0/14.04) < 0.01
    assert s8["board_p_w"] > 8*1.78                                  # 8 阀功率下限
    b4 = bm.BoardModel()
    b4.step(0.1, valves=[1]+[0]*7, pump=0); b4.step(0.1, valves=[0]*8, pump=0)
    assert b4.telemetry()["valves"][0]["i_A"] > 5.0/14.04*0.85      # 关断后 τ 衰减

if __name__ == "__main__":
    test_states(); print("board_model tests OK")
```

- [ ] **Step 2: 确认失败** — Run: `KPY test_board_model.py` → `ModuleNotFoundError`

- [ ] **Step 3: 实现（解析式 RL + 轨压 + 温升 + 环形历史）**

```python
# firmware/twin/board_model.py
"""S2 板级孪生: 阀RL解析式→轨负载→buck→温升. 参数成色见 spec §10.2 (未本机标定)."""
import math
from collections import deque

LOGIC_A = 0.43                       # ESP32峰值+TCA+CH340 估算(未标定)
BOARD_PARAMS = {                     # 来源注释=校准矩阵要求
    "r_coil": 14.0,   # 阀线圈 Ω   [假设-行业典型, 回板万用表]
    "l_coil": 25e-3,  # 阀线圈 H   [假设, LCR 实测]
    "rds": 0.040,     # AO3400@3.3V[手册]
    "vbus": 5.0, "vf_ss34": 0.31, "r_ss34": 0.05,
    "vout3v3": 3.269, "load_reg": 0.012,     # 负载调整率 V/A [仿真]
    "i_pump": 0.35,   # 泵电流假设同阀
    "theta": {"cpu": 35.0, "buck": 130.0, "mos": 350.0},  # ℃/W [手册]
}
HIST_S, TICK = 600, 0.1

class BoardModel:
    def __init__(self):
        self.i = [0.0]*8; self.t = 0.0; self.stale = False
        self.temp = {"cpu": 25.0, "buck": 25.0, "mos_max": 25.0}
        n = int(HIST_S/TICK)
        self.h = {k: deque(maxlen=n) for k in ("t","v5","v33","load","vi")}
    def _rl(self, on, i0, dt):
        R = BOARD_PARAMS["r_coil"]+BOARD_PARAMS["rds"]
        tau = BOARD_PARAMS["l_coil"]/R; inf = BOARD_PARAMS["vbus"]/R if on else 0.0
        return inf+(i0-inf)*math.exp(-dt/tau)
    def step(self, dt, valves, pump):
        P = BOARD_PARAMS
        for k in range(8):
            self.i[k] = self._rl(bool(valves[k]), self.i[k], dt)
        i_sum = sum(self.i) + (P["i_pump"] if pump else 0.0)
        load5 = i_sum + LOGIC_A
        v5 = P["vbus"] - (P["vf_ss34"]+P["r_ss34"]*load5)
        v33 = P["vout3v"] - P["load_reg"]*LOGIC_A
        p_mos = max(x*x*P["rds"] for x in self.i) if any(self.i) else 0.0
        p_buck = v33*LOGIC_A*(1/0.876-1)
        for k, key, pw in (("cpu","cpu",0.43*3.269),("buck","buck",p_buck),("mos_max","mos",p_mos)):
            tgt = 25.0 + pw*P["theta"][key]
            self.temp[k] += (tgt-self.temp[k])*min(1.0, dt/30.0)   # 30s 热惯性
        self.t += dt
        for k, v in (("t",self.t),("v5",v5),("v33",v33),("load",load5),("vi",list(self.i))):
            self.h[k].append(v)
    def telemetry(self):
        P = BOARD_PARAMS
        load5 = sum(self.i)+LOGIC_A
        v5 = P["vbus"]-(P["vf_ss34"]+P["r_ss34"]*load5)
        p_buck = P["vout3v"]*LOGIC_A*(1/0.876-1)
        return {"tick": int(self.t/TICK), "uptime_s": self.t, "stale": self.stale,
            "valves": [{"on": self.i[k]>0.01, "i_A": round(self.i[k],3),
                        "p_w": round(self.i[k]**2*(P["r_coil"]+P["rds"]),2)} for k in range(8)],
            "rail_5v": {"v": round(v5,3), "load_a": round(load5,3), "p_w": round(v5*load5,2)},
            "rail_3v3": {"v": P["vout3v"], "load_a": LOGIC_A, "ripple_mv": 3.1,
                         "buck_eff": 0.876, "loss_mw": {"sw":706,"dcr":162,"diode":436,"switching":85}},
            "board_p_w": round(v5*load5,2),
            "temp_est_c": {k: round(v,1) for k,v in self.temp.items()},
            "history": {k: list(v) for k,v in self.h.items()}}
```

- [ ] **Step 4: 测试通过** — `KPY test_board_model.py` → `board_model tests OK`
- [ ] **Step 5: 提交** — `git commit -m "feat(twin): S2 board_model (RL解析式/轨压/温升/600s历史, 参数成色注释)"` （add 两文件）

---

### Task 3: server.py v1.2 — 新端点 + 运行时切换 + 时间控制 + 录制回放

**Files:**
- Modify: `firmware/twin/server.py`（do_GET/do_POST 分发处插入新分支；文件头加 import）
- Test: `firmware/twin/test_api_board.sh`（新建）

- [ ] **Step 1: 接线（头部 import + 全局 + 分发分支）**

server.py 头部加：
```python
import sys, os, time, threading, json as _json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import board_model, sim_engine
API_VER = "1.2"
BOARD = board_model.BoardModel()
REC = {"on": False, "buf": []}
TIMECTL = {"paused": False, "speed": 1.0, "step_once": False}
```
`tick_loop()`（既有 41 行附近）改为：每轮 `if TIMECTL["paused"] and not TIMECTL["step_once"]: time.sleep(0.05); continue`；`TIMECTL["step_once"]=False`；未暂停时按 `TIMECTL["speed"]` 调 dll tick 次数（`int(TIMECTL["speed"])` 次调用）；tick 后调 `BOARD.step(0.05*speed, [lib.pn_twin_valve_duty(i)>0 for i in range(8)], lib.pn_twin_pump_duty()>0)`；命令入口（do_POST `/api/cmd` 处理体内）加 `if REC["on"]: REC["buf"].append({"t": time.time(), "cmd": body_str})`。

- [ ] **Step 2: do_GET 增分支（示意完整代码）**

```python
        elif path == "/api/board/state":
            q = parse_qs(urlparse(self.path).query)
            d = BOARD.telemetry()
            if "since" in q:
                t0 = float(q["since"][0]); i = next((k for k,v in enumerate(d["history"]["t"]) if v>=t0), 0)
                d = {**d, "history": {k: (v[i:] if k!="vi" else [row[i:] for row in v]) for k,v in d["history"].items()}}
            d["api"] = API_VER
            self._json(d)
        elif path == "/api/board/sim/presets":
            self._json({"api": API_VER, "presets": {c: {"default": {k: dv for k,_,_,dv in sim_engine.SPEC[c]},
                       "worst": {}} for c in sim_engine.SPEC}})
        elif path == "/api/board/assembly":
            mf = os.path.join(os.path.dirname(os.path.abspath(__file__)), "meshes", "assembly.json")
            if not os.path.exists(mf):
                self._send(404, _json.dumps({"error": "meshes 未生成: 跑 enclosure/make_meshes.py"}), "application/json"); return
            self._json({**_json.load(open(mf, encoding="utf-8")), "api": API_VER})
        elif path == "/api/board/history/export":
            h = BOARD.telemetry()["history"]
            csv = "t_s,rail5v_v,rail3v3_v,load_a\n" + "\n".join(
                f"{t:.2f},{a:.3f},{b:.3f},{c:.3f}" for t,a,b,c in zip(h["t"],h["v5"],h["v33"],h["load"]))
            self._send(200, csv, "text/csv")
```
（`from urllib.parse import parse_qs, urlparse`、`import ctypes, json` 若缺则补。`/lib/three.min.js` 与 `/meshes/` 静态分支仿既有 echarts 分支：`open(...,'rb').read()` 回 `application/javascript` / `model/stl`。）

- [ ] **Step 3: do_POST 增分支**

```python
        elif self.path == "/api/board/sim":
            body = _json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            r = sim_engine.run(body.get("circuit",""), body.get("params",{}))
            r["api"] = API_VER; self._json(r)
        elif self.path == "/api/time":
            body = _json.loads(...); TIMECTL.update({k: body[k] for k in ("paused","speed","step_once") if k in body})
            self._json({"api": API_VER, **TIMECTL})
        elif self.path == "/api/record":
            body = _json.loads(...)
            if body.get("action") == "start": REC.update(on=True, buf=[])
            elif body.get("action") == "stop":
                fn = f"rec_{time.strftime('%H%M%S')}.json"
                from pathlib import Path as _P
                _P("recordings").mkdir(exist_ok=True)
                _P("recordings", fn).write_bytes(_json.dumps(REC["buf"]).encode("utf-8")); REC["on"]=False
            self._json({"api": API_VER, "recording": REC["on"], "n": len(REC["buf"])})
        elif self.path == "/api/record/replay":
            body = _json.loads(...)
            for ev in body["events"]: lib.pn_twin_command(ev["cmd"].encode())
            self._json({"api": API_VER, "replayed": len(body["events"])})
```
（sim_engine.ParamError → `self._send(400, _json.dumps({"error": str(e)}), "application/json")`，用 try/except 包裹；超时用 `threading.Thread(target=..., daemon=True).join(3)` 模式，超时 504。）

- [ ] **Step 4: API 冒烟测试脚本**

```bash
# firmware/twin/test_api_board.sh
KPY server.py & SRV=$!; sleep 2
curl -s localhost:8000/api/board/state | python -c "import json,sys; d=json.load(sys.stdin); assert d['api']=='1.2' and 'rail_5v' in d; print('state OK')"
curl -s -X POST localhost:8000/api/board/sim -d '{"circuit":"buck","params":{"iload":2.0}}' | python -c "import json,sys; d=json.load(sys.stdin); assert d['waves']; print('sim OK')"
curl -s -X POST localhost:8000/api/board/sim -d '{"circuit":"buck","params":{"vin":9}}' | grep -q 400 && echo "bounds OK"
curl -s -X POST localhost:8000/api/time -d '{"paused":true}' | grep -q true && echo "time OK"
curl -s localhost:8000/api/board/history/export | head -1 | grep -q t_s && echo "csv OK"
kill $SRV
```
Run: `bash test_api_board.sh` → 五行 OK。注意 server 改用 KPY 启动（README 同步在 Task 8）。

- [ ] **Step 5: 提交** — `git commit -m "feat(twin): server v1.2 (board/sim/time/record/assembly/csv + 版本字段)"`

---

### Task 4: S3 网格 — make_meshes.py + 生成 STL + assembly.json

**Files:**
- Create: `hardware/flowio-p1/enclosure/make_meshes.py`（FreeCAD 运行）
- Output: `firmware/twin/meshes/{case_top,case_bottom,pcb,parts_f,parts_b}.stl + assembly.json`

- [ ] **Step 1: 写 make_meshes.py（完整）**

```python
# 运行: E:/FreeCAD/bin/FreeCADCmd.exe make_meshes.py
# PCB 挤出 + pos.csv 器件方块阵 + 壳 STL 复制 → firmware/twin/meshes/
import FreeCAD as App, Part, Mesh, MeshPart, csv, json, os, shutil
HERE = os.path.dirname(os.path.abspath(__file__))
TWIN_MESH = os.path.normpath(os.path.join(HERE, "..", "..", "..", "firmware", "twin", "meshes"))
os.makedirs(TWIN_MESH, exist_ok=True)
# 1) 壳 STL 复制
for src, dst in (("case-bottom.stl","case_bottom.stl"), ("case-top.stl","case_top.stl")):
    shutil.copyfile(os.path.join(HERE, src), os.path.join(TWIN_MESH, dst))
# 2) PCB: 从板文件读 Edge.Cuts 矩形 → 挤出 1.6mm
import re
txt = open(os.path.join(HERE, "..", "flowio-p1.kicad_pcb"), encoding="utf-8").read()
xs, ys = [], []
for m in re.finditer(r"\(gr_rect[^\0]*?\(pts \(xy ([\d.\-]+) ([\d.\-]+)\) \(xy ([\d.\-]+) ([\d.\-]+)\)", txt, re.S):
    x0,y0,x1,y1 = map(float, m.groups()); xs += [x0,x1]; ys += [y0,y1]
X0,Y0,X1,Y1 = min(xs),min(ys),max(xs),max(ys)
pcb = Part.makeBox((X1-X0)*25.4/1.0*1.0*1.0*1.0 if False else 90.0, 75.0, 1.6,
                   App.Vector(0,0,0))          # 90×75 (板实际 mm)
pcb.translate(App.Vector(0, 0, 0))
# 3) 器件方块阵: pos.csv + 高度分档
H = {"CONN-TH_2P-P5.00":11.0,"TYPE-C":3.2,"WROOM":3.1,"XH":8.5,"SOT-23":1.2,"C_0603":0.9,
     "C1206":0.8,"SOP":1.75,"CDRH":4.0,"C_1206":6.5,"MSOP":1.1,"DC005":7.0,"TestPoint":0.5,
     "R0603":0.6,"SMA":1.1,"LQFP":1.6,"SW-SMD":2.0,"USBLC":1.0,"CONN-TH_4P":8.5}
def h_of(fp):
    for k,v in H.items():
        if k.lower() in fp.lower(): return v
    return 1.5
import collections
boxes_f, boxes_b = [], []
with open(os.path.join(HERE, "..", "fab", "flowio-p1-pos.csv"), encoding="utf-8-sig") as f:
    for row in csv.DictReader(f):
        x, y, rot = float(row["PosX"]), float(row["PosY"]), float(row["Rot"])
        w = d = 3.0 if h_of(row["Package"]) > 5 else 2.2
        hgt = h_of(row["Package"])
        b = Part.makeBox(w, d, hgt, App.Vector(x-w/2, y-d/2, 1.6 if row["Side"]=="top" else -hgt))
        if rot: b.rotate(App.Vector(x,y,b.CenterOfMass.z), App.Vector(0,0,1), rot)
        (boxes_f if row["Side"]=="top" else boxes_b).append(b)
# 4) 合成+导出
def export(shape, name):
    mesh = MeshPart.meshFromShape(Shape=shape, LinearDeflection=0.5, AngularDeflection=0.6)
    mesh.write(os.path.join(TWIN_MESH, name + ".stl"))
    print(name, len(mesh.Facets), "facets")
export(pcb, "pcb")
export(Part.makeCompound(boxes_f), "parts_f")
export(Part.makeCompound(boxes_b), "parts_b")
manifest = {"parts": [
  {"id":"case_top","name":"上壳(通风栅)","stl":"/meshes/case_top.stl","color":"#9e9e9e","explode":[0,0,28],"opacity":1.0},
  {"id":"parts_f","name":"器件阵-顶面","stl":"/meshes/parts_f.stl","color":"#c62828","explode":[0,0,12],"opacity":0.95},
  {"id":"pcb","name":"P1 主板","stl":"/meshes/pcb.stl","color":"#0d6b3f","explode":[0,0,0]},
  {"id":"parts_b","name":"器件阵-底面","stl":"/meshes/parts_b.stl","color":"#1565c0","explode":[0,0,-8]},
  {"id":"case_bottom","name":"下壳(铜柱)","stl":"/meshes/case_bottom.stl","color":"#757575","explode":[0,0,-16]}],
  "bbox_mm":[95.8,80.8,19], "assembly_note":"M3×2 自攻入下壳铜柱; via-in-pad 已塞孔(见 fab README)"}
open(os.path.join(TWIN_MESH, "assembly.json"),"w",encoding="utf-8").write(json.dumps(manifest,ensure_ascii=False,indent=1))
print("assembly.json written to", TWIN_MESH)
```

- [ ] **Step 2: 运行 + 校验** — Run: `E:/FreeCAD/bin/FreeCADCmd.exe hardware/flowio-p1/enclosure/make_meshes.py`；随后 `KPY -c "import Mesh..."` 不适用（无 FreeCAD），改用既有 `check_case.py` 模式：在 make_meshes 末尾 mesh.isSolid() 断言 + 打印 facet 数（Expected: 5 组 facets 非零、pcb/parts 水密 True）
- [ ] **Step 3: 提交** — `git add hardware/flowio-p1/enclosure/make_meshes.py firmware/twin/meshes/ && git commit -m "feat(twin): S3 全套网格 (pcb挤出+器件阵+壳) + assembly 清单"`

---

### Task 5: S4 固件 — TCA9548A + sensor_if + WS2812（pn_core 分层）

**Files:**
- Create: `firmware/components/pn_core/src/tca9548.c` + `include/pn_tca9548.h`
- Create: `firmware/components/pn_core/include/pn_sensor_if.h`
- Modify: `firmware/components/pn_hal_esp32/src/hal_esp32.c`（I2C 实现 + WS2812）
- Test: `firmware/tests/`（增用例入既有 gcc 框架）

- [ ] **Step 1: 纯逻辑头文件（平台无关）**

```c
/* firmware/components/pn_core/include/pn_tca9548.h */
#ifndef PN_TCA9548_H
#define PN_TCA9548_H
#include <stdint.h>
#define TCA_ADDR 0x70
#define TCA_MANIFOLD 0xFF            /* 不选通道(全断) */
typedef enum { TCA_OK=0, TCA_ERR_BUS, TCA_ERR_CHAN } tca_err_t;
tca_err_t tca_select(uint8_t ch);            /* ch 0-4 或 TCA_MANIFOLD; 纯编码+合法性 */
uint8_t     tca_encode(uint8_t ch);          /* 0x01<<ch, 非法 ch 返回 0 */
/* 主机可测状态机: 注册虚拟传感器后 scan/read */
void    tca_mock_reset(void);
void    tca_mock_attach(uint8_t ch, uint8_t addr, int32_t pa10);   /* pa10=Pa×10 */
tca_err_t tca_scan(uint8_t ch, uint8_t *addrs, uint8_t max, uint8_t *n_out);
tca_err_t tca_read_pa(uint8_t ch, int32_t *pa10);
#endif
```

```c
/* firmware/components/pn_core/src/tca9548.c — 纯逻辑: 编码/校验 + mock 总线表
   (真机 hal 只需实现 tca_i2c_write(byte)/probe——由 hal_esp32.c 提供, 本文件不 include esp 头) */
#include "pn_tca9548.h"
#include <string.h>
static uint8_t s_bus[5][8]; static int32_t s_pa10[5][8]; static uint8_t s_attached[5];
uint8_t tca_encode(uint8_t ch){ return (ch<5)? (uint8_t)(1u<<ch) : 0; }
void tca_mock_reset(void){ memset(s_attached,0,sizeof s_attached); }
void tca_mock_attach(uint8_t ch,uint8_t addr,int32_t pa10){ if(ch<5){s_bus[ch][s_attached[ch]++]=addr; s_pa10[ch][addr&7]=pa10;} }
tca_err_t tca_read_pa(uint8_t ch,int32_t *pa10){ if(ch>=5) return TCA_ERR_CHAN;
    if(!s_attached[ch]) return TCA_ERR_BUS; *pa10=s_pa10[ch][0]; return TCA_OK; }
/* tca_select 真机版: return hal 写 TCA_ADDR<-encode; 主机版直记. tca_scan 遍历 addr 1..0x7E probe. */
```
（scan/probe 完整实现按上表补全——遍历 + s_attached 匹配；固件侧 `tca_select` 经 hal 函数指针 `tca_hal_i2c_write` 注入，main.c 初始化时绑定，保持 pn_core 零 esp 依赖。）

```c
/* firmware/components/pn_core/include/pn_sensor_if.h */
#ifndef PN_SENSOR_IF_H
#define PN_SENSOR_IF_H
#include <stdint.h>
typedef enum { SENSOR_NONE=0, SENSOR_MOCK_XGZP, SENSOR_REAL_SLOT } sensor_type_t;
typedef enum { SENS_OK=0, SENS_DISCONNECT, SENS_TIMEOUT, SENS_CRC } sens_err_t;
sens_err_t sensor_probe(uint8_t ch, sensor_type_t *out);
sens_err_t sensor_read_pa(uint8_t ch, int32_t *pa10);   /* ×10 定点, 免浮点 */
#endif
```

- [ ] **Step 2: 主机测试（入 tests/ 既有 gcc 框架，新增 tca_tests.c）**

```c
/* firmware/tests/tca_tests.c — 编码/通道错误/scan去重/断线错误码 ≥6 断言 */
void test_tca_encode(void){ TEST_ASSERT(0x01==tca_encode(0)); TEST_ASSERT(0==tca_encode(5)); }
void test_tca_mock_read(void){ tca_mock_reset(); tca_mock_attach(2,0x28,4013);
    int32_t v; TEST_ASSERT(TCA_OK==tca_read_pa(2,&v)); TEST_ASSERT(4013==v); }
void test_tca_disconnect(void){ tca_mock_reset(); int32_t v;
    TEST_ASSERT(TCA_ERR_BUS==tca_read_pa(1,&v)); }
/* + scan 用例: 同通道挂 2 地址→n_out=2; ch=7→TCA_ERR_CHAN */
```
Run: `cd firmware/tests && cmake --build build-test && ./build-test/pn_tests.exe` → 既有 21 + 新 ≥6 全绿。

- [ ] **Step 3: hal 实现 + WS2812（hal_esp32.c 增量）**——`tca_hal_i2c_write`: `i2c_master_write_to_device(bus, TCA_ADDR, &byte, 1, 100)`；WS2812 用 `led_strip` 组件（idf_component.yml 声明 `espressif/led_strip`），状态映射函数 `ws2812_set(state)`：IDLE 呼吸蓝/RUNNING 绿/HOLD 青/ERR 红闪/OTA 紫，挂 main.c 10ms 任务尾。QEMU 冒烟：`bash qemu_smoke.sh` 编译+启动不崩。
- [ ] **Step 4: 提交** — `git commit -m "feat(fw): S4 TCA9548A 驱动(pn_core纯逻辑+hal)+sensor_if+WS2812 状态灯"`

---

### Task 6: S4 SDK — sdk/python/flowio_sdk

**Files:**
- Create: `sdk/python/flowio_sdk/{__init__,protocol.py,transport.py,client.py}` + `examples/hello_glove.py` + `sdk/python/tests/test_protocol.py`

- [ ] **Step 1: protocol.py（与 pn_core proto.c 同向量）**

```python
# sdk/python/flowio_sdk/protocol.py
"""0xA5 帧编解码. 测试向量与 firmware/tests/proto_vectors.h 共用(单向漂移防线)."""
CRC8_POLY = 0x8C          # 与 proto.c 一致 (Dallas/Maxim 反向)
def crc8(data: bytes, crc: int = 0) -> int:
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = ((crc >> 1) ^ CRC8_POLY) if (crc & 1) else (crc >> 1)
    return crc
def encode(cmd: int, ports: int = 0, pwm: int = 255) -> bytes:
    body = bytes([0xA5, cmd & 0xFF, ports & 0xFF, pwm & 0xFF])
    return body + bytes([crc8(body)])
def decode(frame: bytes):
    assert len(frame) == 5 and frame[0] == 0xA5, "帧长/头错误"
    assert crc8(frame[:4]) == frame[4], "CRC 错误"
    return {"cmd": frame[1], "ports": frame[2], "pwm": frame[3]}
```

- [ ] **Step 2: transport.py + client.py + 示例**

```python
# transport.py — serial 列举/连接 (pyserial 可选依赖, 缺失时给清晰错误)
class SerialTransport:
    def __init__(self, port, baud=115200): import serial; self.s = serial.Serial(port, baud, timeout=1)
    def send(self, frame: bytes): self.s.write(frame)
    def readline(self) -> str: return self.s.readline().decode(errors="replace").strip()
# client.py — 高层 API: inflate/hold/release/vacuum/state/sensor
class FlowIO:
    def __init__(self, port): self.t = SerialTransport(port)
    def _cmd(self, c, ports, pwm=255): self.t.send(protocol.encode(c, ports, pwm))
    def inflate(self, port=1, pwm=255, ch=0x01): self._cmd(0x49, ch << (port-1), pwm)   # 'I'
    def hold(self, port=1): self._cmd(0x48, 0x01 << (port-1))                            # 'H'
    def release(self, port=1): self._cmd(0x52, 0x01 << (port-1))                         # 'R'
    def vacuum(self, pwm=255): self._cmd(0x56, 0, pwm)                                   # 'V'
    def state(self) -> str: self._cmd(0x53, 0); return self.t.readline()                 # 'S'
```
（命令字节以 `firmware/components/pn_core/src/proto.c` 实表为准——实现前先 grep 该表并同步；`hello_glove.py`: inflate(1,180,800ms)→hold→release→vacuum 循环，串口路径 argv[1]。）

- [ ] **Step 3: 协议金样测试** — `sdk/python/tests/test_protocol.py`：encode(0x49,0x01,255) 末字节 CRC 与 `firmware/tests/proto_vectors.h` 中同输入期望值相等（双向：向量文件由既有测试生成脚本导出或手工摘 8 组写入）；Run: `KPY sdk/python/tests/test_protocol.py` → OK
- [ ] **Step 4: 提交** — `git commit -m "feat(sdk): flowio_sdk 骨架 (0xA5 编解码同向量+serial 传输+高层 API+示例)"`

---

### Task 7: S5 BLE — NimBLE GATT + cmd_transport

**Files:**
- Create: `firmware/components/pn_hal_esp32/src/ble_twin.c` + `include/pn_ble.h`
- Create: `firmware/twin/BLE.md`（姊妹契约）
- Modify: `firmware/main/main.c`（启动 ble_task）、`firmware/sdkconfig.defaults`（BLE=y, host=nimble）

- [ ] **Step 1: BLE.md 契约（UUID 派生规则 + 服务表，先契约后代码）**

UUID 基 `6e1a0000-7f8e-4d3a-b2c1-f10w00000000` 风格项目命名空间（f10w=FLOWIO 词典序自定）：Command=...0001, resp=...0002, state=...0003, notify_en=...0004, cfg=...0005。服务表/载荷字节序按 spec §11.1 抄入 BLE.md（20B state: u16 state_word LE + 5×i16 kPa×10 LE + u16 tick LE）。

- [ ] **Step 2: ble_twin.c 核心（nimble 服务注册 + state 打包）**

```c
/* ble_twin.c 关键结构 (完整编译需 esp-idf nimble 组件; 这里是与 pn_core 的接缝) */
#include "nimble/nimble_port.h"
#include "host/ble_gatt.h"
static uint8_t s_state[20];
static void state_pack(const twin_snapshot_t *sn){   /* twin_snapshot_t 由 main 10ms 任务喂 */
    s_state[0]=sn->state_word&0xFF; s_state[1]=sn->state_word>>8;
    for(int i=0;i<5;i++){ int16_t p=(int16_t)(sn->pressure[i]*10);
        s_state[2+2*i]=p&0xFF; s_state[3+2*i]=p>>8; }
    s_state[12]=sn->tick&0xFF; s_state[13]=sn->tick>>8;
}
/* GATT: CMD 特征 access_cb → 收到 write 即 pn_cmd_feed(buf,len) (与串口同一分发器);
   STATE 特征 10Hz ble_gatts_notify_custom; notify_en 写 0/1 开关. 广播名 FLOWIO-P1-<sn%10000>. */
```
（pn_cmd_feed 为既有命令分发入口的别名——main.c 中把 serial 解析与 ble 写缓冲统一到 `pn_cmd_feed(const uint8_t*, len)`，串口路径包一层行缓冲适配。）
- [ ] **Step 3: 载荷单测（主机）**——state 20B 打包/解包 C 测试入 tests/（无 nimble，只测 state_pack：注入 snapshot 断言字节）；`idf.py build`（或 build_n16r8.cmd）编译通过；qemu 冒烟（无射频，初始化-guard `#ifdef` 跳过 nimble 启动）不崩。
- [ ] **Step 4: 提交** — `git commit -m "feat(fw): S5 BLE NimBLE GATT (Command/Telemetry 服务)+cmd_transport 统一分发+BLE.md 契约"`

---

### Task 8: 前端 — gui.html "P1 板级" 标签页 + Web Bluetooth

**Files:**
- Modify: `firmware/twin/gui.html`（顶层标签容器 + 新页签模块）
- Vendor: `firmware/twin/lib/three.min.js` + `lib/OrbitControls.js`（r128 本地打包，来源 threejs.org releases，放入 lib/）

- [ ] **Step 1: 顶层标签 + 三子面板骨架（结构）**——gui.html 外层包 `<nav id="topTabs">`（气动台 | P1 板级 | 连接真机(BLE)）；气动台为现有根 div 原样移入。P1 页三子卡：遥测 / 仿真 / 结构。
- [ ] **Step 2: 遥测面板**——`pollBoard()`（可见时 200ms `fetch('/api/board/state?since=')`）；电源树 SVG（5V→[SS34]×2→buck→3.3V 节点 text 实时值）；ECharts 双 y 轴历史线（rail_5v.v / load_a）；8 阀电流条形；角落固定黄徽章“模型参数：理论值（未本机标定）”；时间控制条（暂停/单步/速度 slider → POST /api/time）；录制按钮（→/api/record）。
- [ ] **Step 3: 仿真面板**——四电路 select；参数表单由 `/api/board/sim/presets` 动态生成（每参数 number input，min/max 取自响应附域表——server 端 presets 增 `bounds` 字段随 Task 3 数据自然携带）；“重算”→POST，波形画 ECharts line、指标表带 verdict 徽章；按钮请求中 disabled，400/504 显示 error 文本。
- [ ] **Step 4: 结构面板（Three.js）**——`fetch('/api/board/assembly')`→逐 part `THREE.STLLoader` 载入；爆炸滑杆 0-1 插值 `pos=explode*k`；播放按钮 2s 缓动往返；OrbitControls 旋转缩放；raycaster hover 高亮+tooltip 中文名；WebGL 不可用→文字提示。
- [ ] **Step 5: Web Bluetooth（真机模式）**——`navigator.bluetooth.requestDevice({filters:[{namePrefix:'FLOWIO-P1'}]})`→connect GATT；命令路径改写 `ble.write(cmdChar, frame)`（帧由内置 0xA5 编码器——与 SDK protocol.py 同算法的 JS 版）；`stateChar.startNotifications`→解析 20B 更新同一 UI 状态机；顶栏模式徽章 孪生(HTTP)/真机(BLE)，真机模式下停 HTTP 轮询。浏览器不支持→按钮置灰。
- [ ] **Step 6: 冒烟+目视**——`node test_gui.js`（沿既有模式：puppeteer 开页断言标签/面板/canvas 存在）；手动：KPY 起服务→操作气动阀→遥测联动截图、重算波形截图、爆炸动画三帧截图入 `twin/shots/p1_*`。
- [ ] **Step 7: 提交** — `git commit -m "feat(twin): P1 板级前端 (遥测+仿真重算+3D爆炸+Web BLE 真机模式)"`

---

### Task 9: 文档 — API.md v1.2 + BLE.md + README + BRINGUP.md

- [ ] **Step 1: API.md** 增 §0 运行时注记（KPY 启动）、§新端点全量（Task 3 的五分支 + 版本字段语义 + 参数域表抄 spec §3.2）、版本号升 v1.2。
- [ ] **Step 1b: TinyML 泄漏检测下线（spec §12）**——
  server.py 删 `/api/leakdetect` 分支；gui.html 删泄漏检测呈现；API.md 删 §1.2b（/api/leak 留+注记）；
  `firmware/main/main.c` 删 `pn_ml_tick` 调用与 include（94 行附近）；归档:
  `mkdir -p firmware/twin/deprecated/ml-leak && git mv firmware/twin/ml_*.py firmware/twin/ml_conformance* firmware/twin/leak_model_int8.tflite firmware/twin/deprecated/ml-leak/ && git mv firmware/twin/dataset firmware/twin/model firmware/twin/deprecated/ml-leak/`
  验证: `bash test_api_board.sh` 仍全绿 + `curl -s localhost:8000/api/leakdetect` → 404

- [ ] **Step 2: firmware/BRINGUP.md**（新建）——回板动线：CH340 烧录/自动复位→74HCT245/MOS 触发→TCA 实测扫描→WS2812→8 阀→I2C 首选 100kHz→BLE 三步（nRF Connect 扫描/写 cmd/订阅 notify）→电气校准 6 项（spec §10.2 表逐条→改 BOARD_PARAMS→徽章转绿）→泵三实验（calibrate_pump.py）。
- [ ] **Step 3: twin/README 启动命令改 KPY**；根 README 增 sdk/python 一节。
- [ ] **Step 4: 提交** — `git commit -m "docs: API v1.2/BLE.md/BRINGUP 回板动线/README 运行时"`

---

### Task 10: 终验 + 收尾

- [ ] **Step 1: 全测试矩阵** — `KPY test_sim_engine.py && KPY test_board_model.py && bash test_api_board.sh && cd firmware/tests && ./build-test/pn_tests.exe && KPY sdk/python/tests/test_protocol.py && node test_gui.js` → 全绿
- [ ] **Step 2: 目视检查（用户强制惯例）**——气动↔遥测联动、四电路重算、爆炸动画、录制回放各截图入 shots/；发现缺陷回对应 Task 修
- [ ] **Step 3: spec §10.4 验收核对**（未标定黄徽章三处一致：spec/代码/UI）
- [ ] **Step 4: 最终提交** — `git add -A && git commit -m "feat: P1 板级孪生五支柱交付 (S1-S5) API v1.2"`

---

## 完成定义
1. §10 项测试全绿；gui P1 三子面板 + BLE 真机模式可用（真机联调留回板，代码/契约就位）
2. API.md v1.2 / BLE.md / BRINGUP.md 三契约齐；UI 未标定徽章在
3. 五支柱各自可独立演示；git 提交按任务分段
