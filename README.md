# FLOWIO-CN

**Open-source pneumatic soft robotics control platform** — from 4-layer PCB to digital twin.

[![Live Demo](https://img.shields.io/badge/Live_Demo-GitHub_Pages-2ea44f.svg)](https://yfzhang-true.github.io/flowio-cn/)
[![License: MIT](https://img.shields.io/badge/Code-MIT-yellow.svg)](LICENSE)
[![License: CERN OHL-S](https://img.shields.io/badge/Hardware-CERN--OHL--S-blue.svg)](LICENSE)
[![License: CC BY-NC-ND 4.0](https://img.shields.io/badge/Docs-CC--BY--NC--ND--4.0-green.svg)](LICENSE)

## What is this?

FLOWIO-CN is a fully open-source, production-ready pneumatic soft robotics control platform. It's the Chinese domestic alternative to MIT's FlowIO, designed for B2B rehabilitation glove manufacturers (¥300-500/kit including board + firmware + SDK).

**One person, AI-driven, from zero to product in 3 days.**

## Architecture

```
┌─────────────────────────────────────────────────┐
│  Digital Twin (Web)                             │
│  3D exploded view · airflow/current viz        │
│  Real-time telemetry · simulation lab          │
├─────────────────────────────────────────────────┤
│  Python SDK · BLE GATT · Serial CLI            │
├─────────────────────────────────────────────────┤
│  ESP32-S3 Firmware (ESP-IDF + FreeRTOS)       │
│  pn_core (platform-independent C)              │
│  TCA9548A I2C mux · WS2812 · 8× valve PWM    │
├─────────────────────────────────────────────────┤
│  4-Layer PCB (90×75mm) · FreeCAD enclosure    │
│  JLC fab-ready · via-in-pad Type VII          │
└─────────────────────────────────────────────────┘
```

## Quick Start

### Digital Twin (no hardware needed)
```bash
cd firmware/twin
"E:/Program Files/KiCad/10.0/bin/python.exe" server.py
# Open http://localhost:8000
```

### Flash Firmware
```bash
cd firmware
idf.py flash monitor
```

### Python SDK
```python
from flowio_sdk import FlowIO
device = FlowIO("COM3")
device.inflate(port=1, pwm=180)
device.hold(port=1)
```

## Repository Structure

| Directory | Description |
|---|---|
| `firmware/` | ESP32-S3 firmware + digital twin + tests |
| `hardware/flowio-p1/` | KiCad PCB project + fab package |
| `sdk/python/` | flowio_sdk Python package |
| `book/` | LaTeX book source (94 pages, Chinese) |
| `docs/superpowers/` | Engineering specs & plans |
| `enclosure/` | FreeCAD parametric case |

## Key Metrics

| Metric | Value |
|---|---|
| PCB layers | 4 (F: signal · In1: GND · In2: power split · B: signal) |
| DRC violations | **0** (from 146 initial) |
| Host tests | 33/33 ✅ |
| Web app tests | 44/44 ✅ |
| API tests | 50/50 ✅ |
| BLE services | 4 (Command · Telemetry · Config · DeviceInfo) |
| Book | 94 pages · 14 chapters · 31 bib entries |

## Documentation

- [BRINGUP Guide](firmware/BRINGUP.md) — Hardware bring-up checklist
- [API v1.2](firmware/twin/API.md) — HTTP interface spec
- [BLE Interface](firmware/twin/BLE.md) — GATT service/characteristic spec
- [Book PDF](book/build/main.pdf) — 《气动软体机器人自研实战》(in progress)

## License

- **Code**: MIT License
- **Hardware (PCB/enclosure)**: CERN-OHL-S v2
- **Documentation/Book**: CC BY-NC-ND 4.0

## Author

**张越飞 (Zhang Yuefei)** — Embedded Software Engineer
- GitHub: [@yfzhang-true](https://github.com/yfzhang-true)
- Email: yuefeizzz@163.com

---

*Built with AI-driven development methodology. Every spec, plan, test, and commit is documented in `docs/superpowers/`.*
