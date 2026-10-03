# FLOWIO-CN — Open Pneumatic Soft-Robotics Control Platform

An independently engineered, fully open-source alternative to MIT's FlowIO:
a complete "brain upgrade" for pneumatic soft robots, built around ESP32-S3.

## What it is

- **4-layer PCB (90×75 mm)** designed in KiCad, DRC-clean, with a JLC-ready
  SMT manufacturing package (107 parts, 100% LCSC-coded BOM, economic assembly)
- **ESP-IDF / FreeRTOS firmware** with a platform-independent C core
  (`pn_core`): 8-channel PWM proportional-valve drive, TCA9548A I2C mux,
  WS2812 status LEDs via RMT, and NimBLE GATT services (Command / Telemetry /
  Config / DeviceInfo) — browser Web Bluetooth console included, no app needed
- **Python SDK** implementing the 0xA5 binary protocol with CRC-8, verified
  against the firmware's own test vectors for cross-language consistency
- **Web digital twin**: Three.js exploded view with live airflow and current
  visualization, a 4-circuit physics simulation (buck / valve drive / diode-OR /
  I2C), and telemetry replay from CSV recordings
- **Five-layer test automation**: 181 cases, 200+ assertions (host unit / web /
  API / E2E / protocol conformance)
- **94-page LaTeX book** (31 references) documenting the entire build, from
  pneumatic theory to bring-up acceptance tickets

## Why it matters

Soft robotics needs an affordable, hackable controller. FLOWIO-CN delivers a
complete, manufacturable control platform for rehabilitation gloves, lab
research, and embodied-AI data collection — at a kit price of ¥300–500
(about $45–70), closer to a dinner than a grant.

> B2B note: targeting white-label rehabilitation-glove manufacturers as the
> primary commercial path; the reference design doubles as a research/edu kit.

## Where everything lives

- **Source of truth**: github.com/yfzhang-true/flowio-cn (200+ commits,
  spec → plan → review workflow, fully traceable)
- **Firmware**: ESP32-S3, `idf.py` build, host-testable `pn_core` (33 unit
  tests) decoupled from the HAL
- **Manufacturing**: Gerbers + drill + position + BOM under
  `hardware/flowio-p1/fab/`, ready for JLC standard assembly (5 boards,
  assemble 2)

## Licenses

- Code: **MIT**
- Hardware: **CERN OHL-S**

## Status

Hardware at fab-package stage (board bring-up pending delivery); firmware,
SDK, digital twin, and test automation complete and regression-green.
